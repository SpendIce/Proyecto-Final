"""Adapter PostgreSQL del canal web (ADR 0016, issue #149).

Es la única fuente de verdad del canal: la solicitud nace durable, la
ejecución reservable es el trabajo del worker, la revisión de pieza guarda
número, hash y referencias del Doc, y la prosa transitoria (la única tabla
con texto) se vacía en la purga diaria posterior al cierre. Los eventos de
auditoría llevan hashes y metadatos, nunca prosa ni identidad en claro.

Las sesiones no viven acá: son memoria del proceso por diseño.

Decisiones que no se ven en el código:

- **La purga se reparte entre los dos roles de la base.** `agente1_app`
  corre `vencer_solicitudes` (marca `VENCIDA` a la inactiva: es un UPDATE
  de estado operativo) y `agente1_mantenimiento` corre `purgar_prosa` y el
  VACUUM (es dueño de `prosa_transitoria`). Así el rol que sirve la app
  no puede tocar el contenido que la retención ya cerró, y el rol de
  mantenimiento no escribe el ciclo de vida de la solicitud.
- **Los estados del predicado SQL no son literales sueltos**: viajan
  parametrizados desde `ESTADOS_ABIERTOS`/`ESTADOS_CIERRE`, la misma
  fuente que usa la interfaz para mostrar «abierta» o «cerrada».
- **`tomar_trabajo` devuelve cuántas reservas ya hubo** contando los
  eventos `reserva_tomada` del propio registro: el límite de reintentos
  del worker no necesita otra columna ni otro estado.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import psycopg

HU_WEB = "HU-010"
ESTADOS_ABIERTOS = ("EN_COLA", "GENERANDO", "LISTA", "ERROR")
ESTADOS_CIERRE = ("APROBADA", "DESCARTADA", "VENCIDA")
VENTANA_VENCIMIENTO_DIAS = 30

# Canales del canal web (ADR 0019): `web` es la entrada con identidad
# verificada por Google; `web-demo` la creada en modo demostración, que no
# verifica identidad. La bandeja, la reserva del worker y la retención las
# tratan igual — el origen sólo declara cómo entró la solicitud, nunca la
# esconde detrás del canal verificado.
CANAL_WEB = "web"
CANAL_WEB_DEMO = "web-demo"
CANALES_WEB = (CANAL_WEB, CANAL_WEB_DEMO)


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _prosa_de(filas: list) -> tuple[str | None, dict, str | None]:
    """Desarma las filas de `prosa_transitoria` en (descripción, campos, generado).

    Único lugar que conoce las clases de prosa: el detalle de la app y el
    trabajo del worker leen las tres clases con el mismo parseo.
    """
    descripcion = None
    campos: dict = {}
    generado = None
    for clase, texto in filas:
        if clase == "descripcion":
            descripcion = texto
        elif clase == "campos":
            campos = json.loads(texto)
        elif clase == "generado":
            generado = texto
    return descripcion, campos, generado


class ConflictoIdempotencia(ValueError):
    """La clave de idempotencia ya existía con otra firma de pedido."""

    code = "idempotency_conflict"


class RepositorioWebError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SolicitudCreada:
    id_solicitud: str
    id_ejecucion: str
    creada: bool


@dataclass(frozen=True)
class ItemBandeja:
    id_solicitud: str
    tipo_pieza: str
    actividad_ref: str | None
    estado_web: str
    titulo: str | None
    creada_en: datetime
    ultima_actividad_en: datetime


@dataclass(frozen=True)
class RevisionPieza:
    id_borrador: str
    numero_revision: int
    output_hash: str
    doc_ref: str | None
    head_revision_id: str | None
    creada_en: datetime
    origen: str | None = None


@dataclass(frozen=True)
class DetalleSolicitud:
    id_solicitud: str
    tipo_pieza: str
    actividad_ref: str | None
    estado_web: str
    rol: str
    solicitante_hash: str
    canal: str
    creada_en: datetime
    ultima_actividad_en: datetime
    descripcion: str | None
    campos: dict
    texto_generado: str | None
    revisiones: tuple[RevisionPieza, ...]
    doc_ref: str | None = None
    doc_url: str | None = None
    texto_vigente: str | None = None


@dataclass(frozen=True)
class ResultadoImportacion:
    """Lo que dejó «Traer cambios del Doc»: nada nuevo o revisión nueva."""

    codigo: str
    numero_revision: int | None = None
    id_borrador: str | None = None


@dataclass(frozen=True)
class ResultadoDecisionWeb:
    """Lo que dejó el POST de decisión: registrada o rechazada con código."""

    codigo: str
    id_borrador: str | None = None


@dataclass(frozen=True)
class TrabajoWeb:
    id_ejecucion: str
    id_solicitud: str
    tipo_pieza: str
    actividad_ref: str | None
    rol: str
    solicitante_hash: str
    descripcion: str | None
    campos: dict
    canal: str = CANAL_WEB
    intentos: int = 0


@dataclass(frozen=True)
class ResultadoPurga:
    vencidas: int
    purgadas: int


class ConexionFactory(Protocol):
    def __call__(self) -> psycopg.Connection: ...


def conectar(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, autocommit=False)


class RepositorioWeb:
    """Repositorio durable del canal web sobre el esquema del spike + 0004."""

    def __init__(self, conexion_factory: ConexionFactory) -> None:
        self._conexion_factory = conexion_factory

    # ---------- escritura del pedido ----------

    def crear_solicitud(
        self,
        *,
        idempotency_key: str,
        solicitante_hash: str,
        rol: str,
        tipo_pieza: str,
        actividad_ref: str | None,
        descripcion: str | None,
        campos: dict,
        canal: str = CANAL_WEB,
        ahora: datetime | None = None,
    ) -> SolicitudCreada:
        """Crea solicitud + ejecución + prosa + evento en una sola tx.

        La clave de idempotencia (UNIQUE en `ejecuciones`) absorbe doble
        clic y reenvío del formulario: la segunda entrega con la misma
        firma devuelve la solicitud ya creada; con otra firma, conflicto.
        `canal` registra el origen de la identidad (`web`/`web-demo`).
        """
        ahora = ahora or datetime.now(timezone.utc)
        id_solicitud = f"web-{uuid.uuid4().hex[:16]}"
        id_ejecucion = f"webe-{uuid.uuid4().hex[:16]}"
        campos_json = json.dumps(campos, ensure_ascii=False, sort_keys=True)
        # La descripción es opcional en el pedido: su hash se deriva de
        # cadena vacía, mientras la fila conserva NULL.
        desc_hash = _hash(descripcion or "")
        input_hash = _hash(
            f"{idempotency_key}|{solicitante_hash}|{tipo_pieza}|"
            f"{actividad_ref or ''}|{campos_json}|{desc_hash}"
        )
        try:
            with self._conexion_factory() as conn:
                with conn.transaction():
                    conn.execute(
                        "INSERT INTO solicitudes (id_solicitud, input_hash,"
                        " fuente_tipo, creada_en, canal, solicitante_hash,"
                        " rol, tipo_pieza, actividad_ref, estado_web,"
                        " ultima_actividad_en) VALUES"
                        " (%s,%s,'web',%s,%s,%s,%s,%s,%s,'EN_COLA',%s)",
                        (
                            id_solicitud, input_hash, ahora, canal,
                            solicitante_hash, rol, tipo_pieza, actividad_ref,
                            ahora,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO ejecuciones (id_ejecucion, id_solicitud,"
                        " idempotency_key, correlation_id, hu, input_hash,"
                        " estado, creada_en) VALUES"
                        " (%s,%s,%s,%s,%s,%s,'INICIADA',%s)",
                        (
                            id_ejecucion, id_solicitud, idempotency_key,
                            f"corr-{uuid.uuid4().hex[:16]}", HU_WEB,
                            input_hash, ahora,
                        ),
                    )
                    # La prosa `descripcion` sólo existe cuando el pedido
                    # la trae: `texto` NULL en esta tabla está reservado
                    # a la purga, nunca a la escritura.
                    if descripcion is not None:
                        conn.execute(
                            "INSERT INTO prosa_transitoria (id_solicitud,"
                            " id_ejecucion, clase, texto, texto_hash,"
                            " creada_en)"
                            " VALUES (%s,%s,'descripcion',%s,%s,%s)",
                            (
                                id_solicitud, id_ejecucion, descripcion,
                                desc_hash, ahora,
                            ),
                        )
                    conn.execute(
                        "INSERT INTO prosa_transitoria (id_solicitud,"
                        " id_ejecucion, clase, texto, texto_hash, creada_en)"
                        " VALUES (%s,%s,'campos',%s,%s,%s)",
                        (
                            id_solicitud, id_ejecucion, campos_json,
                            _hash(campos_json), ahora,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                        " ocurrido_en, evidencia_hash) VALUES"
                        " (%s,'solicitud_creada',%s,%s)",
                        (id_ejecucion, ahora, input_hash),
                    )
        except psycopg.errors.UniqueViolation:
            return self._solicitud_existente(
                idempotency_key, input_hash, solicitante_hash
            )
        return SolicitudCreada(
            id_solicitud=id_solicitud,
            id_ejecucion=id_ejecucion,
            creada=True,
        )

    def _solicitud_existente(
        self,
        idempotency_key: str,
        input_hash: str,
        solicitante_hash: str,
    ) -> SolicitudCreada:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                "SELECT e.id_ejecucion, e.id_solicitud, e.input_hash,"
                " s.solicitante_hash FROM ejecuciones e"
                " JOIN solicitudes s ON s.id_solicitud = e.id_solicitud"
                " WHERE e.idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
        if fila is None:
            raise RepositorioWebError("idempotency_lookup_missing")
        if fila[2] != input_hash or fila[3] != solicitante_hash:
            raise ConflictoIdempotencia()
        return SolicitudCreada(
            id_solicitud=fila[1], id_ejecucion=fila[0], creada=False
        )

    # ---------- lectura para la interfaz ----------

    def bandeja(self) -> list[ItemBandeja]:
        with self._conexion_factory() as conn:
            filas = conn.execute(
                "SELECT s.id_solicitud, s.tipo_pieza, s.actividad_ref,"
                " s.estado_web, s.creada_en, s.ultima_actividad_en,"
                " (SELECT p.texto::jsonb -> 'pieza' ->> 'titulo'"
                "   FROM prosa_transitoria p"
                "   WHERE p.id_solicitud = s.id_solicitud"
                "     AND p.clase = 'campos' AND p.texto IS NOT NULL"
                "   LIMIT 1) AS titulo"
                " FROM solicitudes s WHERE s.canal = ANY(%s)"
                " ORDER BY s.ultima_actividad_en DESC",
                (list(CANALES_WEB),),
            ).fetchall()
        return [
            ItemBandeja(
                id_solicitud=f[0], tipo_pieza=f[1], actividad_ref=f[2],
                estado_web=f[3], creada_en=f[4], ultima_actividad_en=f[5],
                titulo=f[6],
            )
            for f in filas
        ]

    def obtener(self, id_solicitud: str) -> DetalleSolicitud | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                "SELECT id_solicitud, tipo_pieza, actividad_ref, estado_web,"
                " rol, solicitante_hash, canal, creada_en,"
                " ultima_actividad_en, doc_ref, doc_url, revision_vigente"
                " FROM solicitudes"
                " WHERE id_solicitud = %s AND canal = ANY(%s)",
                (id_solicitud, list(CANALES_WEB)),
            ).fetchone()
            if fila is None:
                return None
            prosas = conn.execute(
                "SELECT clase, texto FROM prosa_transitoria"
                " WHERE id_solicitud = %s AND texto IS NOT NULL",
                (id_solicitud,),
            ).fetchall()
            revisiones = conn.execute(
                "SELECT id_borrador, numero_revision, output_hash, doc_ref,"
                " head_revision_id, creada_en, origen FROM borradores"
                " WHERE id_solicitud = %s ORDER BY numero_revision",
                (id_solicitud,),
            ).fetchall()
            vigente = conn.execute(
                "SELECT texto FROM prosa_transitoria"
                " WHERE id_solicitud = %s AND id_borrador = %s"
                "   AND texto IS NOT NULL",
                (id_solicitud, fila[11]),
            ).fetchone()
        descripcion, campos, generado = _prosa_de(prosas)
        return DetalleSolicitud(
            id_solicitud=fila[0], tipo_pieza=fila[1], actividad_ref=fila[2],
            estado_web=fila[3], rol=fila[4], solicitante_hash=fila[5],
            canal=fila[6],
            creada_en=fila[7], ultima_actividad_en=fila[8],
            descripcion=descripcion, campos=campos,
            texto_generado=generado,
            revisiones=tuple(
                RevisionPieza(
                    id_borrador=r[0], numero_revision=r[1], output_hash=r[2],
                    doc_ref=r[3], head_revision_id=r[4], creada_en=r[5],
                    origen=r[6],
                )
                for r in revisiones
            ),
            doc_ref=fila[9], doc_url=fila[10],
            texto_vigente=(
                vigente[0] if vigente is not None else generado
            ),
        )

    def estado_de(self, id_solicitud: str) -> str | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                "SELECT estado_web FROM solicitudes"
                " WHERE id_solicitud = %s AND canal = ANY(%s)",
                (id_solicitud, list(CANALES_WEB)),
            ).fetchone()
        return fila[0] if fila else None

    # ---------- trabajo del worker ----------

    def tomar_trabajo(
        self,
        *,
        worker_id: str,
        plazo_segundos: int = 300,
        ahora: datetime | None = None,
    ) -> TrabajoWeb | None:
        """Reserva la ejecución en cola más vieja, a prueba de carreras.

        `FOR UPDATE SKIP LOCKED` evita que dos workers tomen lo mismo; la
        reserva tiene plazo: si el worker cae, la ejecución vuelve a ser
        tomable cuando `reservada_hasta` vence (ADR 0016, prueba 1).
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "SELECT e.id_ejecucion, e.id_solicitud, s.tipo_pieza,"
                    " s.actividad_ref, s.rol, s.solicitante_hash, s.canal"
                    " FROM ejecuciones e"
                    " JOIN solicitudes s ON s.id_solicitud = e.id_solicitud"
                    " WHERE e.estado = 'INICIADA'"
                    "   AND (e.reservada_hasta IS NULL"
                    "        OR e.reservada_hasta < %s)"
                    " ORDER BY e.creada_en LIMIT 1"
                    " FOR UPDATE OF e SKIP LOCKED",
                    (ahora,),
                ).fetchone()
                if fila is None:
                    return None
                conn.execute(
                    "UPDATE ejecuciones SET reservada_hasta = %s,"
                    " reservada_por = %s WHERE id_ejecucion = %s",
                    (
                        ahora + timedelta(seconds=plazo_segundos),
                        worker_id, fila[0],
                    ),
                )
                conn.execute(
                    "UPDATE solicitudes SET estado_web = 'GENERANDO',"
                    " ultima_actividad_en = %s WHERE id_solicitud = %s",
                    (ahora, fila[1]),
                )
                conn.execute(
                    "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                    " ocurrido_en) VALUES (%s,'reserva_tomada',%s)",
                    (fila[0], ahora),
                )
                intentos = conn.execute(
                    "SELECT COUNT(*) FROM eventos_ejecucion"
                    " WHERE id_ejecucion = %s AND tipo = 'reserva_tomada'",
                    (fila[0],),
                ).fetchone()[0]
                prosas = conn.execute(
                    "SELECT clase, texto FROM prosa_transitoria"
                    " WHERE id_solicitud = %s AND texto IS NOT NULL",
                    (fila[1],),
                ).fetchall()
        descripcion, campos, _ = _prosa_de(prosas)
        return TrabajoWeb(
            id_ejecucion=fila[0], id_solicitud=fila[1], tipo_pieza=fila[2],
            actividad_ref=fila[3], rol=fila[4], solicitante_hash=fila[5],
            canal=fila[6],
            descripcion=descripcion, campos=campos, intentos=intentos,
        )

    def completar_trabajo(
        self,
        *,
        id_ejecucion: str,
        id_solicitud: str,
        texto_generado: str,
        referencia: str,
        doc_ref: str | None,
        head_revision_id: str | None,
        doc_url: str | None = None,
        texto_documento: str | None = None,
        compartido_con_hash: str | None = None,
        permiso_no_otorgado_hash: str | None = None,
        ahora: datetime | None = None,
    ) -> str:
        """Cierra la ejecución con su revisión de pieza, en una tx.

        Devuelve el id del borrador (la revisión vigente de la solicitud).

        `texto_documento` es el texto del Doc tal como quedó exportado al
        escribirlo: el `output_hash` de la revisión es el hash de ese
        texto, la base con la que «Traer cambios del Doc» compara (ADR
        0016 — la aprobación se ata al hash del Doc reimportado). El texto
        generado se conserva aparte en la prosa `generado`.

        `doc_url` es el enlace de edición del Doc (NULL con destinos que
        no son Google). `compartido_con_hash` es el hash del correo con el
        que el worker compartió el Doc; `permiso_no_otorgado_hash` deja
        asentado el intento fallido sin contar la generación como fallida
        —el Doc ya existe— y con el hash, nunca el correo en claro.
        """
        ahora = ahora or datetime.now(timezone.utc)
        output_hash = _hash(texto_generado)
        doc_hash = (
            _hash(texto_documento)
            if texto_documento is not None
            else output_hash
        )
        id_borrador = f"borr-{uuid.uuid4().hex[:16]}"
        with self._conexion_factory() as conn:
            with conn.transaction():
                numero = conn.execute(
                    "SELECT COALESCE(MAX(numero_revision), 0) + 1"
                    " FROM borradores WHERE id_solicitud = %s",
                    (id_solicitud,),
                ).fetchone()[0]
                conn.execute(
                    # El output durable de la ejecución es el Doc: la FK
                    # de 0002 ata (id_ejecucion, output_hash) entre
                    # ejecución y borrador, así que ambos guardan el hash
                    # del texto exportado — no el del texto generado, que
                    # queda sólo en la prosa `generado` y su texto_hash.
                    "UPDATE ejecuciones SET estado = 'PENDIENTE_VALIDACION',"
                    " resultado = 'borrador_generado', output_hash = %s,"
                    " finalizada_en = %s WHERE id_ejecucion = %s",
                    (doc_hash, ahora, id_ejecucion),
                )
                conn.execute(
                    "INSERT INTO borradores (id_borrador, id_ejecucion,"
                    " referencia_hash, output_hash, canal, estado, creada_en,"
                    " id_solicitud, numero_revision, doc_ref,"
                    " head_revision_id, origen) VALUES"
                    " (%s,%s,%s,%s,'gacetilla','PENDIENTE_VALIDACION',%s,"
                    " %s,%s,%s,%s,'generada')",
                    (
                        id_borrador, id_ejecucion, _hash(referencia),
                        doc_hash, ahora, id_solicitud, numero,
                        doc_ref, head_revision_id,
                    ),
                )
                conn.execute(
                    "INSERT INTO prosa_transitoria (id_solicitud,"
                    " id_ejecucion, clase, texto, texto_hash, creada_en,"
                    " id_borrador) VALUES (%s,%s,'generado',%s,%s,%s,%s)",
                    (id_solicitud, id_ejecucion, texto_generado,
                     output_hash, ahora, id_borrador),
                )
                conn.execute(
                    "UPDATE solicitudes SET estado_web = 'LISTA',"
                    " revision_vigente = %s, ultima_actividad_en = %s,"
                    " doc_ref = %s, doc_url = %s"
                    " WHERE id_solicitud = %s",
                    (id_borrador, ahora, doc_ref, doc_url, id_solicitud),
                )
                conn.execute(
                    "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                    " ocurrido_en, evidencia_hash) VALUES"
                    " (%s,'revision_generada',%s,%s)",
                    (id_ejecucion, ahora, doc_hash),
                )
                if compartido_con_hash is not None:
                    conn.execute(
                        "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                        " ocurrido_en, evidencia_hash) VALUES"
                        " (%s,'doc_compartido',%s,%s)",
                        (id_ejecucion, ahora, compartido_con_hash),
                    )
                if permiso_no_otorgado_hash is not None:
                    conn.execute(
                        "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                        " ocurrido_en, evidencia_hash) VALUES"
                        " (%s,'permiso_no_otorgado',%s,%s)",
                        (id_ejecucion, ahora, permiso_no_otorgado_hash),
                    )
        return id_borrador

    def fallar_trabajo(
        self,
        *,
        id_ejecucion: str,
        id_solicitud: str,
        resultado: str = "error_generacion",
        estado: str = "FALLIDA",
        error_code: str | None = None,
        ahora: datetime | None = None,
    ) -> None:
        """Cierra la ejecución sin borrador y marca la solicitud `ERROR`.

        `estado` es `FALLIDA` salvo que el pipeline haya respondido
        `INCOMPLETA`: el esquema exige `resultado='datos_incompletos'` en
        ese único caso, y acá el valor viaja con él.
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                conn.execute(
                    "UPDATE ejecuciones SET estado = %s,"
                    " resultado = %s, error_code = %s, finalizada_en = %s"
                    " WHERE id_ejecucion = %s",
                    (estado, resultado, error_code, ahora, id_ejecucion),
                )
                conn.execute(
                    "UPDATE solicitudes SET estado_web = 'ERROR',"
                    " ultima_actividad_en = %s WHERE id_solicitud = %s",
                    (ahora, id_solicitud),
                )
                conn.execute(
                    "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                    " ocurrido_en) VALUES (%s,'generacion_fallida',%s)",
                    (id_ejecucion, ahora),
                )

    # ---------- revisión y decisión del Doc (#153) ----------

    def importar_revision(
        self,
        *,
        id_solicitud: str,
        texto: str,
        head_revision_id: str | None = None,
        ahora: datetime | None = None,
    ) -> ResultadoImportacion:
        """Registra el texto reexportado del Doc si su hash cambió.

        Compara el hash del texto exportado con el de la revisión
        vigente: igual → `sin_cambios`; distinto → crea la revisión
        siguiente con origen `editada_docs`, guarda su texto en la prosa
        transitoria enlazada al borrador y la deja vigente, sin tocar las
        revisiones anteriores (ADR 0016, prueba 4).
        """
        ahora = ahora or datetime.now(timezone.utc)
        texto_hash = _hash(texto)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "SELECT revision_vigente, estado_web, doc_ref"
                    " FROM solicitudes"
                    " WHERE id_solicitud = %s AND canal = ANY(%s)"
                    " FOR UPDATE",
                    (id_solicitud, list(CANALES_WEB)),
                ).fetchone()
                if fila is None:
                    return ResultadoImportacion("inexistente")
                vigente, estado_web, doc_ref = fila
                if estado_web != "LISTA" or doc_ref is None:
                    return ResultadoImportacion("no_disponible")
                hash_vigente = conn.execute(
                    "SELECT output_hash FROM borradores"
                    " WHERE id_borrador = %s",
                    (vigente,),
                ).fetchone()[0]
                if hash_vigente == texto_hash:
                    conn.execute(
                        "UPDATE solicitudes SET ultima_actividad_en = %s"
                        " WHERE id_solicitud = %s",
                        (ahora, id_solicitud),
                    )
                    return ResultadoImportacion("sin_cambios")
                id_borrador = self._importar_en_tx(
                    conn,
                    id_solicitud=id_solicitud,
                    doc_ref=doc_ref,
                    texto=texto,
                    texto_hash=texto_hash,
                    head_revision_id=head_revision_id,
                    ahora=ahora,
                )
                numero = conn.execute(
                    "SELECT numero_revision FROM borradores"
                    " WHERE id_borrador = %s",
                    (id_borrador,),
                ).fetchone()[0]
        return ResultadoImportacion(
            "importada", numero_revision=numero, id_borrador=id_borrador
        )

    def registrar_decision(
        self,
        *,
        id_solicitud: str,
        id_borrador: str,
        decision: str,
        doc_hash: str,
        texto_doc: str | None,
        validador_hash: str,
        rol: str,
        origen_identidad: str,
        version_agente: str,
        head_revision_id: str | None = None,
        ahora: datetime | None = None,
    ) -> ResultadoDecisionWeb:
        """Registra la decisión sobre la revisión vigente, en una tx.

        `decision` es `APROBADA` o `RECHAZADA` (el vocabulario cerrado de
        `validaciones`: el descarte viaja como RECHAZADA, ADR 0016).
        Códigos de resultado:

        - `aprobada`/`descartada`: decisión registrada, solicitud cerrada.
        - `doc_cambiado`: el hash reexportado difiere del de la revisión
          mostrada; se asienta la revisión nueva y se rechaza.
        - `revision_obsoleta`: el borrador decidido ya no es el vigente.
        - `duplicada`: la revisión ya tiene una decisión registrada.
        - `cerrada`/`inexistente`: la solicitud ya cerró o no existe.

        `head_revision_id` es el `files.get` del Doc al momento de decidir.
        Si el exportador no lo provee queda NULL explícito: la decisión sigue
        atada al hash del texto (ADR 0016) y no se inventa una revisión de
        Drive.

        Todo ocurre en la misma transacción: una caída a la mitad no deja
        ni decisión parcial ni revisión colgada (ADR 0016, prueba 2).
        """
        ahora = ahora or datetime.now(timezone.utc)
        if decision not in ("APROBADA", "RECHAZADA"):
            raise RepositorioWebError("decision_fuera_de_catalogo")
        with self._conexion_factory() as conn:
            try:
                with conn.transaction():
                    fila = conn.execute(
                        "SELECT revision_vigente, estado_web, doc_ref"
                        " FROM solicitudes"
                        " WHERE id_solicitud = %s AND canal = ANY(%s)"
                        " FOR UPDATE",
                        (id_solicitud, list(CANALES_WEB)),
                    ).fetchone()
                    if fila is None:
                        return ResultadoDecisionWeb("inexistente")
                    vigente, estado_web, doc_ref = fila
                    if estado_web != "LISTA":
                        return ResultadoDecisionWeb("cerrada")
                    if id_borrador != vigente:
                        self._evento_rechazo_decision(
                            conn, id_solicitud, ahora, doc_hash
                        )
                        return ResultadoDecisionWeb("revision_obsoleta")
                    borrador = conn.execute(
                        "SELECT output_hash, creada_en FROM borradores"
                        " WHERE id_borrador = %s",
                        (vigente,),
                    ).fetchone()
                    if borrador[0] != doc_hash:
                        importacion = self._importar_en_tx(
                            conn,
                            id_solicitud=id_solicitud,
                            doc_ref=doc_ref,
                            texto=texto_doc or "",
                            texto_hash=doc_hash,
                            head_revision_id=head_revision_id,
                            ahora=ahora,
                        )
                        self._evento_rechazo_decision(
                            conn, id_solicitud, ahora, doc_hash
                        )
                        return ResultadoDecisionWeb(
                            "doc_cambiado",
                            id_borrador=importacion,
                        )
                    duplicada = conn.execute(
                        "SELECT 1 FROM validaciones WHERE id_borrador = %s",
                        (vigente,),
                    ).fetchone()
                    if duplicada is not None:
                        self._evento_rechazo_decision(
                            conn, id_solicitud, ahora, doc_hash
                        )
                        return ResultadoDecisionWeb("duplicada")
                    senal, proporcion, ajustes = self._senal_edicion(
                        conn,
                        id_solicitud=id_solicitud,
                        doc_hash=doc_hash,
                        texto_doc=texto_doc,
                    )
                    conn.execute(
                        "INSERT INTO validaciones (id_validacion,"
                        " id_borrador, decision, validador_ref_hash,"
                        " checklist_version, registrada_en,"
                        " borrador_creada_en, doc_hash,"
                        " senal, proporcion_cambiado, cantidad_ajustes,"
                        " rol, origen_identidad, version_agente,"
                        " head_revision_id) VALUES"
                        " (%s,%s,%s,%s,'decision_web_v1',%s,%s,%s,%s,%s,%s,"
                        " %s,%s,%s,%s)",
                        (
                            f"val-{uuid.uuid4().hex[:16]}", vigente,
                            decision, validador_hash, ahora, borrador[1],
                            doc_hash, senal, proporcion, ajustes,
                            rol, origen_identidad, version_agente,
                            head_revision_id,
                        ),
                    )
                    conn.execute(
                        "UPDATE borradores SET estado = %s"
                        " WHERE id_borrador = %s",
                        (
                            "APROBADO" if decision == "APROBADA"
                            else "RECHAZADO",
                            vigente,
                        ),
                    )
                    conn.execute(
                        "UPDATE solicitudes SET estado_web = %s,"
                        " ultima_actividad_en = %s"
                        " WHERE id_solicitud = %s",
                        (
                            "APROBADA" if decision == "APROBADA"
                            else "DESCARTADA",
                            ahora, id_solicitud,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO eventos_ejecucion (id_ejecucion,"
                        " tipo, ocurrido_en, evidencia_hash)"
                        " SELECT id_ejecucion, 'decision_registrada', %s, %s"
                        " FROM ejecuciones WHERE id_solicitud = %s"
                        " ORDER BY creada_en LIMIT 1",
                        (ahora, doc_hash, id_solicitud),
                    )
            except psycopg.errors.UniqueViolation:
                # Doble clic o reenvío concurrente: la otra tx ya asentó
                # la decisión — el rechazo es idempotente (prueba 3).
                return ResultadoDecisionWeb("duplicada")
        return ResultadoDecisionWeb(
            "aprobada" if decision == "APROBADA" else "descartada",
            id_borrador=vigente,
        )

    def _importar_en_tx(
        self,
        conn: psycopg.Connection,
        *,
        id_solicitud: str,
        doc_ref: str,
        texto: str,
        texto_hash: str,
        ahora: datetime,
        head_revision_id: str | None = None,
    ) -> str:
        """Alta de una revisión `editada_docs` dentro de la tx del llamador."""
        numero = conn.execute(
            "SELECT COALESCE(MAX(numero_revision), 0) + 1"
            " FROM borradores WHERE id_solicitud = %s",
            (id_solicitud,),
        ).fetchone()[0]
        id_borrador = f"borr-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO borradores (id_borrador, id_ejecucion,"
            " referencia_hash, output_hash, canal, estado, creada_en,"
            " id_solicitud, numero_revision, doc_ref, head_revision_id,"
            " origen) VALUES"
            " (%s,NULL,%s,%s,'gacetilla','PENDIENTE_VALIDACION',%s,"
            " %s,%s,%s,%s,'editada_docs')",
            (
                id_borrador, _hash(doc_ref), texto_hash, ahora,
                id_solicitud, numero, doc_ref, head_revision_id,
            ),
        )
        conn.execute(
            "INSERT INTO prosa_transitoria (id_solicitud, id_ejecucion,"
            " clase, texto, texto_hash, creada_en, id_borrador) VALUES"
            " (%s,NULL,'importado',%s,%s,%s,%s)",
            (id_solicitud, texto, texto_hash, ahora, id_borrador),
        )
        conn.execute(
            "UPDATE solicitudes SET revision_vigente = %s,"
            " ultima_actividad_en = %s WHERE id_solicitud = %s",
            (id_borrador, ahora, id_solicitud),
        )
        conn.execute(
            "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
            " ocurrido_en, evidencia_hash)"
            " SELECT id_ejecucion, 'revision_importada', %s, %s"
            " FROM ejecuciones WHERE id_solicitud = %s"
            " ORDER BY creada_en LIMIT 1",
            (ahora, texto_hash, id_solicitud),
        )
        return id_borrador

    def _evento_rechazo_decision(
        self,
        conn: psycopg.Connection,
        id_solicitud: str,
        ahora: datetime,
        evidencia_hash: str,
    ) -> None:
        conn.execute(
            "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
            " ocurrido_en, evidencia_hash)"
            " SELECT id_ejecucion, 'decision_rechazada', %s, %s"
            " FROM ejecuciones WHERE id_solicitud = %s"
            " ORDER BY creada_en LIMIT 1",
            (ahora, evidencia_hash, id_solicitud),
        )

    def _senal_edicion(
        self,
        conn: psycopg.Connection,
        *,
        id_solicitud: str,
        doc_hash: str,
        texto_doc: str | None,
    ) -> tuple[str | None, float | None, int]:
        """Señal de edición de la aprobación (ADR 0016).

        `sin_cambios` cuando el hash del Doc coincide con el de la
        revisión generada; `con_cambios` cuando se editó. La proporción
        es 1 menos la similitud entre el texto generado y el texto del
        Doc, y los ajustes son las revisiones `editada_docs` acumuladas.
        """
        base = conn.execute(
            "SELECT output_hash FROM borradores"
            " WHERE id_solicitud = %s AND numero_revision = 1",
            (id_solicitud,),
        ).fetchone()
        ajustes = conn.execute(
            "SELECT COUNT(*) FROM borradores"
            " WHERE id_solicitud = %s AND origen = 'editada_docs'",
            (id_solicitud,),
        ).fetchone()[0]
        if base is None:
            return None, None, ajustes
        senal = "sin_cambios" if base[0] == doc_hash else "con_cambios"
        if texto_doc is None:
            return senal, None, ajustes
        generado = conn.execute(
            "SELECT texto FROM prosa_transitoria"
            " WHERE id_solicitud = %s AND clase = 'generado'"
            "   AND texto IS NOT NULL",
            (id_solicitud,),
        ).fetchone()
        if generado is None:
            return senal, None, ajustes
        if senal == "sin_cambios":
            return senal, 0.0, ajustes
        ratio = difflib.SequenceMatcher(
            None, generado[0], texto_doc
        ).ratio()
        return senal, round(1.0 - ratio, 4), ajustes

    # ---------- retención ----------

    def vencer_solicitudes(
        self,
        *,
        ahora: datetime | None = None,
        ventana_dias: int = VENTANA_VENCIMIENTO_DIAS,
    ) -> int:
        """Pasa a `VENCIDA` toda web abierta sin actividad por la ventana.

        Corre con `agente1_app`: es un UPDATE del ciclo de vida operativo,
        no toca prosa ni la auditoría (sólo inserta el evento de marca).
        """
        ahora = ahora or datetime.now(timezone.utc)
        corte = ahora - timedelta(days=ventana_dias)
        with self._conexion_factory() as conn:
            with conn.transaction():
                filas = conn.execute(
                    "UPDATE solicitudes SET estado_web = 'VENCIDA',"
                    " ultima_actividad_en = %s"
                    " WHERE canal = ANY(%s)"
                    "   AND estado_web = ANY(%s)"
                    "   AND ultima_actividad_en < %s"
                    " RETURNING id_solicitud",
                    (ahora, list(CANALES_WEB), list(ESTADOS_ABIERTOS), corte),
                ).fetchall()
                for (id_solicitud,) in filas:
                    ejecucion = conn.execute(
                        "SELECT id_ejecucion FROM ejecuciones"
                        " WHERE id_solicitud = %s ORDER BY creada_en LIMIT 1",
                        (id_solicitud,),
                    ).fetchone()
                    if ejecucion is not None:
                        conn.execute(
                            "INSERT INTO eventos_ejecucion (id_ejecucion,"
                            " tipo, ocurrido_en) VALUES"
                            " (%s,'solicitud_vencida',%s)",
                            (ejecucion[0], ahora),
                        )
        return len(filas)

    def purgar_prosa(self, *, ahora: datetime | None = None) -> int:
        """Vacía la prosa transitoria de toda solicitud cerrada (ADR 0016).

        Corre con `agente1_mantenimiento`, dueño de `prosa_transitoria`:
        pone el texto en NULL conservando clase, hash y marcas, y asienta
        un solo evento `prosa_purgada` por solicitud. `evidencia_hash`
        compromete la cantidad de filas purgadas de esa solicitud. El
        VACUUM corre aparte, con `vaciar_prosa`.
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                purgadas = conn.execute(
                    "UPDATE prosa_transitoria p SET texto = NULL,"
                    " purgada_en = %s FROM solicitudes s"
                    " WHERE p.id_solicitud = s.id_solicitud"
                    "   AND p.purgada_en IS NULL"
                    "   AND s.canal = ANY(%s)"
                    "   AND s.estado_web = ANY(%s)"
                    " RETURNING p.secuencia, p.id_solicitud",
                    (ahora, list(CANALES_WEB), list(ESTADOS_CIERRE)),
                ).fetchall()
                por_solicitud: dict[str, int] = {}
                for _, id_solicitud in purgadas:
                    por_solicitud[id_solicitud] = (
                        por_solicitud.get(id_solicitud, 0) + 1
                    )
                for id_solicitud, filas in por_solicitud.items():
                    ejecucion = conn.execute(
                        "SELECT id_ejecucion FROM ejecuciones"
                        " WHERE id_solicitud = %s ORDER BY creada_en LIMIT 1",
                        (id_solicitud,),
                    ).fetchone()
                    if ejecucion is not None:
                        conn.execute(
                            "INSERT INTO eventos_ejecucion (id_ejecucion,"
                            " tipo, ocurrido_en, evidencia_hash) VALUES"
                            " (%s,'prosa_purgada',%s,%s)",
                            (
                                ejecucion[0],
                                ahora,
                                _hash(f"prosa_purgada:{filas}"),
                            ),
                        )
        return len(purgadas)

    def vencer_y_purgar(
        self,
        *,
        ahora: datetime | None = None,
        ventana_dias: int = VENTANA_VENCIMIENTO_DIAS,
    ) -> ResultadoPurga:
        """Atajo de la purga completa en una sola conexión (ensayos).

        Producción corre los dos pasos con roles distintos:
        `vencer_solicitudes` como `agente1_app` y `purgar_prosa` más
        `vaciar_prosa` como `agente1_mantenimiento` (ver el docstring del
        módulo). Este atajo existe para las pruebas de desarrollo que
        usan un solo DSN.
        """
        ahora = ahora or datetime.now(timezone.utc)
        vencidas = self.vencer_solicitudes(
            ahora=ahora, ventana_dias=ventana_dias
        )
        purgadas = self.purgar_prosa(ahora=ahora)
        return ResultadoPurga(vencidas=vencidas, purgadas=purgadas)

    @staticmethod
    def vaciar_prosa(dsn: str) -> None:
        """VACUUM de la prosa purgada: fuera de tx, con rol de mantenimiento."""
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("VACUUM prosa_transitoria")
