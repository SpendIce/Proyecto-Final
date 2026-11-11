"""Adapter PostgreSQL del canal web (ADR 0016, issue #149).

Es la única fuente de verdad del canal: la solicitud nace durable, la
ejecución reservable es el trabajo del worker, la revisión de pieza guarda
número, hash y referencias del Doc, y la prosa transitoria (la única tabla
con texto) se vacía en la purga diaria posterior al cierre. Los eventos de
auditoría llevan hashes y metadatos, nunca prosa ni identidad en claro.

Las sesiones no viven acá: son memoria del proceso por diseño.
"""

from __future__ import annotations

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


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


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


@dataclass(frozen=True)
class DetalleSolicitud:
    id_solicitud: str
    tipo_pieza: str
    actividad_ref: str | None
    estado_web: str
    rol: str
    solicitante_hash: str
    creada_en: datetime
    ultima_actividad_en: datetime
    descripcion: str | None
    campos: dict
    texto_generado: str | None
    revisiones: tuple[RevisionPieza, ...]


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
        descripcion: str,
        campos: dict,
        ahora: datetime | None = None,
    ) -> SolicitudCreada:
        """Crea solicitud + ejecución + prosa + evento en una sola tx.

        La clave de idempotencia (UNIQUE en `ejecuciones`) absorbe doble
        clic y reenvío del formulario: la segunda entrega con la misma
        firma devuelve la solicitud ya creada; con otra firma, conflicto.
        """
        ahora = ahora or datetime.now(timezone.utc)
        id_solicitud = f"web-{uuid.uuid4().hex[:16]}"
        id_ejecucion = f"webe-{uuid.uuid4().hex[:16]}"
        campos_json = json.dumps(campos, ensure_ascii=False, sort_keys=True)
        input_hash = _hash(
            f"{idempotency_key}|{solicitante_hash}|{tipo_pieza}|"
            f"{actividad_ref or ''}|{campos_json}|{_hash(descripcion)}"
        )
        try:
            with self._conexion_factory() as conn:
                with conn.transaction():
                    conn.execute(
                        "INSERT INTO solicitudes (id_solicitud, input_hash,"
                        " fuente_tipo, creada_en, canal, solicitante_hash,"
                        " rol, tipo_pieza, actividad_ref, estado_web,"
                        " ultima_actividad_en) VALUES"
                        " (%s,%s,'web',%s,'web',%s,%s,%s,%s,'EN_COLA',%s)",
                        (
                            id_solicitud, input_hash, ahora, solicitante_hash,
                            rol, tipo_pieza, actividad_ref, ahora,
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
                    conn.execute(
                        "INSERT INTO prosa_transitoria (id_solicitud,"
                        " id_ejecucion, clase, texto, texto_hash, creada_en)"
                        " VALUES (%s,%s,'descripcion',%s,%s,%s)",
                        (
                            id_solicitud, id_ejecucion, descripcion,
                            _hash(descripcion), ahora,
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
                " FROM solicitudes s WHERE s.canal = 'web'"
                " ORDER BY s.ultima_actividad_en DESC"
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
                " rol, solicitante_hash, creada_en, ultima_actividad_en"
                " FROM solicitudes WHERE id_solicitud = %s AND canal = 'web'",
                (id_solicitud,),
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
                " head_revision_id, creada_en FROM borradores"
                " WHERE id_solicitud = %s ORDER BY numero_revision",
                (id_solicitud,),
            ).fetchall()
        descripcion = None
        campos: dict = {}
        generado = None
        for clase, texto in prosas:
            if clase == "descripcion":
                descripcion = texto
            elif clase == "campos":
                campos = json.loads(texto)
            elif clase == "generado":
                generado = texto
        return DetalleSolicitud(
            id_solicitud=fila[0], tipo_pieza=fila[1], actividad_ref=fila[2],
            estado_web=fila[3], rol=fila[4], solicitante_hash=fila[5],
            creada_en=fila[6], ultima_actividad_en=fila[7],
            descripcion=descripcion, campos=campos,
            texto_generado=generado,
            revisiones=tuple(
                RevisionPieza(
                    id_borrador=r[0], numero_revision=r[1], output_hash=r[2],
                    doc_ref=r[3], head_revision_id=r[4], creada_en=r[5],
                )
                for r in revisiones
            ),
        )

    def estado_de(self, id_solicitud: str) -> str | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                "SELECT estado_web FROM solicitudes"
                " WHERE id_solicitud = %s AND canal = 'web'",
                (id_solicitud,),
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
                    " s.actividad_ref, s.rol, s.solicitante_hash"
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
                prosas = conn.execute(
                    "SELECT clase, texto FROM prosa_transitoria"
                    " WHERE id_solicitud = %s AND texto IS NOT NULL",
                    (fila[1],),
                ).fetchall()
        descripcion = None
        campos: dict = {}
        for clase, texto in prosas:
            if clase == "descripcion":
                descripcion = texto
            elif clase == "campos":
                campos = json.loads(texto)
        return TrabajoWeb(
            id_ejecucion=fila[0], id_solicitud=fila[1], tipo_pieza=fila[2],
            actividad_ref=fila[3], rol=fila[4], solicitante_hash=fila[5],
            descripcion=descripcion, campos=campos,
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
        ahora: datetime | None = None,
    ) -> str:
        """Cierra la ejecución con su revisión de pieza, en una tx.

        Devuelve el id del borrador (la revisión vigente de la solicitud).
        """
        ahora = ahora or datetime.now(timezone.utc)
        output_hash = _hash(texto_generado)
        id_borrador = f"borr-{uuid.uuid4().hex[:16]}"
        with self._conexion_factory() as conn:
            with conn.transaction():
                numero = conn.execute(
                    "SELECT COALESCE(MAX(numero_revision), 0) + 1"
                    " FROM borradores WHERE id_solicitud = %s",
                    (id_solicitud,),
                ).fetchone()[0]
                conn.execute(
                    "UPDATE ejecuciones SET estado = 'PENDIENTE_VALIDACION',"
                    " resultado = 'borrador_generado', output_hash = %s,"
                    " finalizada_en = %s WHERE id_ejecucion = %s",
                    (output_hash, ahora, id_ejecucion),
                )
                conn.execute(
                    "INSERT INTO borradores (id_borrador, id_ejecucion,"
                    " referencia_hash, output_hash, canal, estado, creada_en,"
                    " id_solicitud, numero_revision, doc_ref,"
                    " head_revision_id) VALUES"
                    " (%s,%s,%s,%s,'gacetilla','PENDIENTE_VALIDACION',%s,"
                    " %s,%s,%s,%s)",
                    (
                        id_borrador, id_ejecucion, _hash(referencia),
                        output_hash, ahora, id_solicitud, numero,
                        doc_ref, head_revision_id,
                    ),
                )
                conn.execute(
                    "INSERT INTO prosa_transitoria (id_solicitud,"
                    " id_ejecucion, clase, texto, texto_hash, creada_en)"
                    " VALUES (%s,%s,'generado',%s,%s,%s)",
                    (id_solicitud, id_ejecucion, texto_generado,
                     output_hash, ahora),
                )
                conn.execute(
                    "UPDATE solicitudes SET estado_web = 'LISTA',"
                    " revision_vigente = %s, ultima_actividad_en = %s"
                    " WHERE id_solicitud = %s",
                    (id_borrador, ahora, id_solicitud),
                )
                conn.execute(
                    "INSERT INTO eventos_ejecucion (id_ejecucion, tipo,"
                    " ocurrido_en, evidencia_hash) VALUES"
                    " (%s,'revision_generada',%s,%s)",
                    (id_ejecucion, ahora, output_hash),
                )
        return id_borrador

    def fallar_trabajo(
        self,
        *,
        id_ejecucion: str,
        id_solicitud: str,
        resultado: str = "error_generacion",
        error_code: str | None = None,
        ahora: datetime | None = None,
    ) -> None:
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                conn.execute(
                    "UPDATE ejecuciones SET estado = 'FALLIDA',"
                    " resultado = %s, error_code = %s, finalizada_en = %s"
                    " WHERE id_ejecucion = %s",
                    (resultado, error_code, ahora, id_ejecucion),
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

    # ---------- retención ----------

    def vencer_y_purgar(
        self,
        *,
        ahora: datetime | None = None,
        ventana_dias: int = VENTANA_VENCIMIENTO_DIAS,
    ) -> ResultadoPurga:
        """Purga diaria (ADR 0016): vence inactivas y vacía la prosa.

        Primero pasa a `VENCIDA` toda solicitud abierta sin actividad por la
        ventana; después pone en NULL el texto de la prosa transitoria de
        toda solicitud cerrada (aprobada, descartada o vencida), conservando
        clase, hash y marcas. El VACUUM corre aparte, con `vaciar_prosa`.
        """
        ahora = ahora or datetime.now(timezone.utc)
        corte = ahora - timedelta(days=ventana_dias)
        with self._conexion_factory() as conn:
            with conn.transaction():
                vencidas = conn.execute(
                    "UPDATE solicitudes SET estado_web = 'VENCIDA'"
                    " WHERE canal = 'web'"
                    "   AND estado_web IN ('EN_COLA','GENERANDO','LISTA','ERROR')"
                    "   AND ultima_actividad_en < %s"
                    " RETURNING id_solicitud",
                    (corte,),
                ).fetchall()
                purgadas = conn.execute(
                    "UPDATE prosa_transitoria p SET texto = NULL,"
                    " purgada_en = %s FROM solicitudes s"
                    " WHERE p.id_solicitud = s.id_solicitud"
                    "   AND p.purgada_en IS NULL"
                    "   AND s.canal = 'web'"
                    "   AND s.estado_web IN ('APROBADA','DESCARTADA','VENCIDA')"
                    " RETURNING p.secuencia, p.id_solicitud",
                    (ahora,),
                ).fetchall()
                for _, id_solicitud in purgadas:
                    ejecucion = conn.execute(
                        "SELECT id_ejecucion FROM ejecuciones"
                        " WHERE id_solicitud = %s ORDER BY creada_en LIMIT 1",
                        (id_solicitud,),
                    ).fetchone()
                    if ejecucion is not None:
                        conn.execute(
                            "INSERT INTO eventos_ejecucion (id_ejecucion,"
                            " tipo, ocurrido_en) VALUES"
                            " (%s,'prosa_purgada',%s)",
                            (ejecucion[0], ahora),
                        )
        return ResultadoPurga(
            vencidas=len(vencidas), purgadas=len(purgadas)
        )

    @staticmethod
    def vaciar_prosa(dsn: str) -> None:
        """VACUUM de la prosa purgada: fuera de tx, con rol de mantenimiento."""
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("VACUUM prosa_transitoria")

    # ---------- lectura para pruebas y trazabilidad ----------

    def prosa_textos(self, id_solicitud: str) -> list[str | None]:
        with self._conexion_factory() as conn:
            return [
                f[0]
                for f in conn.execute(
                    "SELECT texto FROM prosa_transitoria"
                    " WHERE id_solicitud = %s ORDER BY secuencia",
                    (id_solicitud,),
                ).fetchall()
            ]

    def ejecucion_estado(self, id_ejecucion: str) -> tuple | None:
        with self._conexion_factory() as conn:
            return conn.execute(
                "SELECT estado, resultado, reservada_hasta, output_hash"
                " FROM ejecuciones WHERE id_ejecucion = %s",
                (id_ejecucion,),
            ).fetchone()
