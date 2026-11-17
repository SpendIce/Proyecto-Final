"""Lote de certificados de HU-014 en la web del Agente 1 (#168, ADR 0018).

El canal web reemplaza el correo al aprobador con enlace al Form de
decisiones: quien genera el lote lo evalúa y lo decide en la web, sobre la
lista de cierre y un certificado de muestra marcado como borrador. El
circuito de emisión (`certificados_emision`) no cambia: acá se guarda el
lote, se muestra y se registra la decisión atada al hash.

Decisiones que no se ven en el código:

- **El lote se identifica por el hash canónico de la lista.** El id es
  `lote-<primeros 16 del objeto>` y la columna `objeto_lote` es única: el
  mismo lote reenviado no crea una fila nueva, y cualquier edición de la
  lista (alta, baja, condición o reorden) produce otro objeto. El objeto es
  exactamente `certificados_emision.objeto_lote_cierre`, el mismo que
  consulta `linea_descriptiva.revisar_aprobacion_lote`.
- **La decisión es una sola y terminal.** `SELECT … FOR UPDATE` sobre la
  fila —el patrón de `RepositorioWeb.registrar_decision`— serializa doble
  clic y reenvío concurrente: la segunda decisión ve el estado terminal y
  se rechaza `duplicada`. El hash que llega en el POST tiene que ser el que
  se mostró; si cambió se rechaza `lote_obsoleto` sin tocar el lote.
- **Aprobar lo hace quien generó el lote** (ADR 0018): el rol tiene que ser
  `APROBADOR_CONTENIDO` y el hash de la identidad tiene que coincidir con
  el del generador. Descartar sólo exige el rol: no habilita ninguna
  emisión, así que no necesita la autoría. Los códigos de rechazo son los
  mismos que enumera `revisar_aprobacion_lote`.
- **La lista de cierre se retiene sólo mientras el lote opera.** La purga
  diaria del canal web (`purgar_canal_web`) pone `personas` en NULL en los
  lotes ya decididos y conserva cantidad, hashes, plantilla y la decisión
  con identidad, rol, origen y versión del agente. La muestra se genera al
  vuelo y no se persiste.
- **La web no emite.** Después de aprobar, la página informa si el lote
  puede emitir con las reglas vigentes —plantilla aprobada por hash (ADR
  0020) y firmas disponibles (R2 de #160)— y, si no, por qué. La emisión
  sigue siendo del circuito de certificados: acá no se manda ningún correo
  ni se toca Drive.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

import psycopg
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from psycopg.types.json import Jsonb

from ..canal_form import hash_correo
from ..certificados_emision import (
    CONDICIONES_CIERRE,
    FIRMANTES_DECLARADOS,
    TEMPLATE_VERSION,
    PersonaCierre,
    generar_pdf_muestra_lote,
    hash_lista_cierre,
    objeto_lote_cierre,
    parsear_lista_cierre,
)
from ..certificados_plantilla_seu import (
    FIRMANTES_SEU,
    RECURSOS_IMAGEN,
    TEMPLATE_VERSION_SEU,
    RecursosFirma,
)
from ..confirmaciones import ROL_APROBADOR_CONTENIDO
from .sesiones import Sesion

HU = "HU-014"

ESTADO_PENDIENTE = "PENDIENTE_APROBACION"
ESTADO_APROBADA = "APROBADA"
ESTADO_DESCARTADA = "DESCARTADA"

ACCION_APROBAR = "aprobar"
ACCION_DESCARTAR = "descartar"
ACCIONES = (ACCION_APROBAR, ACCION_DESCARTAR)

CODIGO_APROBADA = "aprobada"
CODIGO_DESCARTADA = "descartada"
CODIGO_LOTE_OBSOLETO = "lote_obsoleto"
CODIGO_DUPLICADA = "duplicada"
CODIGO_INEXISTENTE = "inexistente"
CODIGO_DECISION_FUERA_DE_CATALOGO = "decision_fuera_de_catalogo"
CODIGO_ROL_NO_AUTORIZADO = "aprobador_rol_no_autorizado"
CODIGO_NO_ES_GENERADOR = "aprobador_no_es_generador"

_ESTADOS_VISIBLES = {
    ESTADO_PENDIENTE: "Pendiente de aprobación",
    ESTADO_APROBADA: "Aprobado",
    ESTADO_DESCARTADA: "Descartado",
}

_AVISOS_DECISION = {
    CODIGO_APROBADA: "Lote aprobado.",
    CODIGO_DESCARTADA: "Lote descartado. No se emite ningún certificado.",
    CODIGO_LOTE_OBSOLETO: (
        "El hash del lote no coincide con el que se mostró. "
        "Recargá la página y volvé a decidir."
    ),
    CODIGO_DUPLICADA: "La decisión ya estaba registrada.",
    CODIGO_INEXISTENTE: "El lote no existe.",
    CODIGO_DECISION_FUERA_DE_CATALOGO: (
        "La decisión no pertenece al catálogo del lote."
    ),
    CODIGO_ROL_NO_AUTORIZADO: (
        "El rol no habilita la decisión del lote."
    ),
    CODIGO_NO_ES_GENERADOR: (
        "El lote lo aprueba quien lo generó: la identidad de la sesión "
        "no coincide con la del generador."
    ),
}

_AVISOS_ERROR = frozenset(
    {
        CODIGO_LOTE_OBSOLETO,
        CODIGO_DUPLICADA,
        CODIGO_INEXISTENTE,
        CODIGO_DECISION_FUERA_DE_CATALOGO,
        CODIGO_ROL_NO_AUTORIZADO,
        CODIGO_NO_ES_GENERADOR,
    }
)

_REQUERIDOS_ACTIVIDAD = (
    "titulo",
    "duracion_horas",
    "modalidad",
    "fecha_inicio",
    "organiza",
)


class LoteCertificadosError(RuntimeError):
    """Contrato del lote roto. `code` es el código auditable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LoteCertificados:
    """El lote tal como quedó guardado, con su decisión si ya la tiene."""

    id_lote: str
    id_actividad: str
    objeto_lote: str
    hash_lista: str
    actividad: dict[str, str]
    personas: tuple[PersonaCierre, ...]
    cantidad_personas: int
    linea_descriptiva: str
    plantilla_muestra: str
    estado: str
    generada_por_hash: str
    creada_en: datetime
    decidida_en: datetime | None = None
    decidida_por_hash: str | None = None
    rol_decision: str | None = None
    origen_identidad: str | None = None
    version_agente: str | None = None


@dataclass(frozen=True)
class ResultadoDecisionLote:
    """Lo que dejó el POST de decisión: código y lote afectado."""

    codigo: str
    id_lote: str | None = None


@dataclass(frozen=True)
class EstadoPlantilla:
    """Plantilla que usa una condición y si su versión está habilitada."""

    condicion: str
    nombre: str
    estado: str
    aprobada: bool


@dataclass(frozen=True)
class EstadoFirmas:
    """Los recursos de firma que la emisión real necesita (R2 de #160)."""

    configuradas: bool
    faltantes: tuple[str, ...]

    @property
    def disponible(self) -> bool:
        return self.configuradas and not self.faltantes


def _json(valor) -> object:
    """JSONB del driver como objeto Python, admitiendo el texto crudo."""
    if isinstance(valor, (dict, list)):
        return valor
    return json.loads(valor)


def _personas_desde_json(valor) -> tuple[PersonaCierre, ...]:
    if valor is None:
        return ()
    return tuple(
        PersonaCierre(
            nombre=str(fila["nombre"]),
            apellido=str(fila["apellido"]),
            dni=str(fila["dni"]),
            mail=str(fila["mail"]),
            tratamiento=str(fila["tratamiento"]),
            condicion=str(fila["condicion"]),
        )
        for fila in _json(valor)
    )


def _personas_a_json(personas: tuple[PersonaCierre, ...]) -> list[dict]:
    return [
        {
            "nombre": p.nombre,
            "apellido": p.apellido,
            "dni": p.dni,
            "mail": p.mail,
            "tratamiento": p.tratamiento,
            "condicion": p.condicion,
        }
        for p in personas
    ]


class RepositorioLotes:
    """Persistencia del lote de certificados sobre el esquema de 0010."""

    def __init__(self, conexion_factory: Callable[[], psycopg.Connection]) -> None:
        self._conexion_factory = conexion_factory

    def crear(
        self,
        *,
        id_actividad: str,
        actividad: dict[str, str],
        personas: tuple[PersonaCierre, ...],
        linea_descriptiva: str,
        generada_por_hash: str,
        ahora: datetime | None = None,
    ) -> LoteCertificados:
        """Crea el lote o devuelve el que ya existe para esa lista.

        La lista pasa por `parsear_lista_cierre`, el mismo contrato de la
        emisión: filas completas, mail válido, condición exacta y sin
        duplicados. El hash canónico y el objeto salen de las funciones del
        circuito, no de una copia local.
        """
        ahora = ahora or datetime.now(timezone.utc)
        id_actividad = (id_actividad or "").strip()
        if not id_actividad:
            raise LoteCertificadosError("actividad_id_invalida")
        datos = {
            clave: str(actividad.get(clave, "") or "").strip()
            for clave in _REQUERIDOS_ACTIVIDAD
        }
        if not all(datos.values()):
            raise LoteCertificadosError("actividad_datos_incompletos")
        validadas = parsear_lista_cierre(
            [
                [p.nombre, p.apellido, p.dni, p.mail, p.tratamiento, p.condicion]
                for p in personas
            ]
        )
        if not linea_descriptiva or not str(linea_descriptiva).strip():
            raise LoteCertificadosError("linea_descriptiva_ausente")
        linea = str(linea_descriptiva).strip()
        hash_lista = hash_lista_cierre(validadas)
        objeto = objeto_lote_cierre(id_actividad, hash_lista)
        id_lote = f"lote-{objeto[:16]}"
        plantilla = (
            TEMPLATE_VERSION_SEU
            if validadas[0].condicion == "aprobacion"
            else TEMPLATE_VERSION
        )
        with self._conexion_factory() as conn:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO lotes_certificados (id_lote, id_actividad,"
                    " objeto_lote, hash_lista, actividad, personas,"
                    " cantidad_personas, linea_descriptiva,"
                    " plantilla_muestra, estado, generada_por_hash,"
                    " creada_en) VALUES"
                    " (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    " ON CONFLICT (objeto_lote) DO NOTHING",
                    (
                        id_lote,
                        id_actividad,
                        objeto,
                        hash_lista,
                        Jsonb(datos),
                        Jsonb(_personas_a_json(validadas)),
                        len(validadas),
                        linea,
                        plantilla,
                        ESTADO_PENDIENTE,
                        generada_por_hash,
                        ahora,
                    ),
                )
        creado = self._por_objeto(objeto)
        if creado is None:
            raise LoteCertificadosError("lote_no_persistido")
        return creado

    def obtener(self, id_lote: str) -> LoteCertificados | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                f"{_SELECT} WHERE id_lote = %s",
                (id_lote,),
            ).fetchone()
        return _lote_desde_fila(fila) if fila is not None else None

    def listar(self) -> list[LoteCertificados]:
        with self._conexion_factory() as conn:
            filas = conn.execute(
                f"{_SELECT} ORDER BY"
                " (estado = 'PENDIENTE_APROBACION') DESC, creada_en DESC"
            ).fetchall()
        return [_lote_desde_fila(fila) for fila in filas]

    def _por_objeto(self, objeto_lote: str) -> LoteCertificados | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                f"{_SELECT} WHERE objeto_lote = %s",
                (objeto_lote,),
            ).fetchone()
        return _lote_desde_fila(fila) if fila is not None else None

    def decidir(
        self,
        *,
        id_lote: str,
        hash_lote: str,
        accion: str,
        validador_hash: str,
        rol: str,
        origen_identidad: str,
        version_agente: str,
        ahora: datetime | None = None,
    ) -> ResultadoDecisionLote:
        """Registra la decisión terminal del lote, en una sola transacción.

        El `FOR UPDATE` serializa las decisiones concurrentes sobre la misma
        fila. El orden de rechazo es estructural primero (existe, pendiente,
        acción) y autorización después (rol, hash, autoría): un formulario
        alterado no necesita mirar la identidad para saber que no vale.
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "SELECT objeto_lote, estado, generada_por_hash"
                    " FROM lotes_certificados WHERE id_lote = %s"
                    " FOR UPDATE",
                    (id_lote,),
                ).fetchone()
                if fila is None:
                    return ResultadoDecisionLote(CODIGO_INEXISTENTE)
                objeto_lote, estado, generada_por_hash = fila
                if estado != ESTADO_PENDIENTE:
                    return ResultadoDecisionLote(CODIGO_DUPLICADA)
                if accion not in ACCIONES:
                    return ResultadoDecisionLote(
                        CODIGO_DECISION_FUERA_DE_CATALOGO
                    )
                if rol != ROL_APROBADOR_CONTENIDO:
                    return ResultadoDecisionLote(CODIGO_ROL_NO_AUTORIZADO)
                if hash_lote != objeto_lote:
                    return ResultadoDecisionLote(CODIGO_LOTE_OBSOLETO)
                if (
                    accion == ACCION_APROBAR
                    and validador_hash != generada_por_hash
                ):
                    return ResultadoDecisionLote(CODIGO_NO_ES_GENERADOR)
                conn.execute(
                    "UPDATE lotes_certificados SET estado = %s,"
                    " decidida_en = %s, decidida_por_hash = %s,"
                    " rol_decision = %s, origen_identidad = %s,"
                    " version_agente = %s WHERE id_lote = %s",
                    (
                        ESTADO_APROBADA
                        if accion == ACCION_APROBAR
                        else ESTADO_DESCARTADA,
                        ahora,
                        validador_hash,
                        rol,
                        origen_identidad,
                        version_agente,
                        id_lote,
                    ),
                )
        return ResultadoDecisionLote(
            CODIGO_APROBADA
            if accion == ACCION_APROBAR
            else CODIGO_DESCARTADA,
            id_lote=id_lote,
        )

    def purgar_cerrados(self, *, ahora: datetime | None = None) -> int:
        """Retira la lista de los lotes decididos; conserva la trazabilidad.

        Corre con el rol de la app en la purga diaria, como
        `RepositorioWeb.purgar_prosa`: el lote es estado operativo y la
        lista de personas es el único texto que retiene. La cantidad, los
        hashes y la decisión (identidad, rol, origen y versión) quedan.
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                filas = conn.execute(
                    "UPDATE lotes_certificados SET personas = NULL,"
                    " purgada_en = %s WHERE personas IS NOT NULL"
                    "   AND estado = ANY(%s) RETURNING id_lote",
                    (ahora, [ESTADO_APROBADA, ESTADO_DESCARTADA]),
                ).fetchall()
        return len(filas)


_SELECT = (
    "SELECT id_lote, id_actividad, objeto_lote, hash_lista, actividad,"
    " personas, cantidad_personas, linea_descriptiva, plantilla_muestra,"
    " estado, generada_por_hash, creada_en, decidida_en, decidida_por_hash,"
    " rol_decision, origen_identidad, version_agente"
    " FROM lotes_certificados"
)


def _lote_desde_fila(fila) -> LoteCertificados:
    return LoteCertificados(
        id_lote=fila[0],
        id_actividad=fila[1],
        objeto_lote=fila[2],
        hash_lista=fila[3],
        actividad=dict(_json(fila[4])),
        personas=_personas_desde_json(fila[5]),
        cantidad_personas=fila[6],
        linea_descriptiva=fila[7],
        plantilla_muestra=fila[8],
        estado=fila[9],
        generada_por_hash=fila[10],
        creada_en=fila[11],
        decidida_en=fila[12],
        decidida_por_hash=fila[13],
        rol_decision=fila[14],
        origen_identidad=fila[15],
        version_agente=fila[16],
    )


def estado_plantillas(
    condiciones: tuple[str, ...],
) -> tuple[EstadoPlantilla, ...]:
    """Plantilla que corresponde a cada condición del lote y su estado.

    `aprobacion` compone el diseño institucional recibido (ADR 0017) y no
    depende de una decisión de contenido; `asistencia` sigue con la
    plantilla provisional porque su variante institucional no llegó y en
    producción exige la versión de `certificado_asistencia` aprobada por
    hash (ADR 0020). Esta pantalla no tiene el registro de decisiones: la
    verificación que habilita la emisión sigue siendo la del circuito.
    """
    resultado: list[EstadoPlantilla] = []
    for condicion in sorted(set(condiciones)):
        if condicion not in CONDICIONES_CIERRE:
            continue
        if condicion == "aprobacion":
            resultado.append(
                EstadoPlantilla(
                    condicion=condicion,
                    nombre=TEMPLATE_VERSION_SEU,
                    estado="Diseño institucional recibido (ADR 0017)",
                    aprobada=True,
                )
            )
        else:
            resultado.append(
                EstadoPlantilla(
                    condicion=condicion,
                    nombre=TEMPLATE_VERSION,
                    estado=(
                        "Provisional: falta la plantilla aprobada de "
                        "asistencia (ADR 0020)"
                    ),
                    aprobada=False,
                )
            )
    return tuple(resultado)


def estado_firmas(recursos: RecursosFirma | None) -> EstadoFirmas:
    """Qué recursos de firma resuelve la custodia configurada (R2 de #160)."""
    requeridos = set(RECURSOS_IMAGEN) | {
        f.recurso for f in FIRMANTES_SEU if f.recurso is not None
    }
    faltantes = tuple(
        nombre
        for nombre in sorted(requeridos)
        if recursos is None or recursos.leer(nombre) is None
    )
    return EstadoFirmas(
        configuradas=recursos is not None, faltantes=faltantes
    )


def diagnostico_emision(
    lote: LoteCertificados, recursos: RecursosFirma | None
) -> tuple[bool, str | None]:
    """¿El lote puede emitir con las reglas vigentes y, si no, por qué?

    Devuelve `(puede, motivo)` con el motivo en el vocabulario del circuito:
    plantilla aprobada por hash (ADR 0020) y firmas disponibles (R2). No
    emite nada: la pantalla sólo informa.
    """
    if not lote.personas:
        return False, "la lista del lote se retiró por retención mínima"
    plantillas = estado_plantillas(
        tuple(p.condicion for p in lote.personas)
    )
    sin_aprobar = [p for p in plantillas if not p.aprobada]
    if sin_aprobar:
        return (
            False,
            "falta la plantilla aprobada de "
            + ", ".join(p.condicion for p in sin_aprobar)
            + " (ADR 0020)",
        )
    firmas = estado_firmas(recursos)
    if not firmas.disponible:
        return False, "faltan firmas (R2)"
    return True, None


class RepositorioLotesPuerto(Protocol):
    """Lo que la app necesita del repositorio; el fake de pruebas lo cumple."""

    def listar(self) -> list[LoteCertificados]: ...

    def obtener(self, id_lote: str) -> LoteCertificados | None: ...

    def decidir(self, **datos) -> ResultadoDecisionLote: ...


def lotes_para_bandeja(
    repositorio: RepositorioLotesPuerto,
) -> list[dict[str, object]]:
    """Filas de la sección «Lotes de certificados» de la bandeja."""
    return [
        {
            "id": lote.id_lote,
            "actividad": lote.actividad.get("titulo", lote.id_actividad),
            "id_actividad": lote.id_actividad,
            "cantidad": lote.cantidad_personas,
            "estado": lote.estado,
            "estado_visible": _ESTADOS_VISIBLES.get(
                lote.estado, lote.estado
            ),
            "creada": lote.creada_en.strftime("%d/%m/%Y %H:%M"),
        }
        for lote in repositorio.listar()
    ]


Render = Callable[..., HTMLResponse]
Autorizar = Callable[[Request], Sesion | None]
RolDe = Callable[[Sesion], str | None]
CsrfOk = Callable[[Sesion, str | None], bool]
DestinoLogin = Callable[[], Response]


def registrar_rutas_certificados(
    app: FastAPI,
    *,
    repositorio: RepositorioLotesPuerto,
    autorizar: Autorizar,
    render: Render,
    rol_de: RolDe,
    csrf_ok: CsrfOk,
    destino_login: DestinoLogin,
    version_agente: str,
    recursos_firma: RecursosFirma | None = None,
) -> None:
    """Cablea las rutas finas del lote; la lógica vive en este módulo."""

    def _render_lote(
        request: Request,
        sesion: Sesion,
        lote: LoteCertificados,
        aviso: str | None = None,
        aviso_error: bool = False,
    ) -> HTMLResponse:
        rol = rol_de(sesion)
        generador = hash_correo(sesion.correo) == lote.generada_por_hash
        pendiente = lote.estado == ESTADO_PENDIENTE
        plantillas = estado_plantillas(
            tuple(p.condicion for p in lote.personas)
        )
        firmas = estado_firmas(recursos_firma)
        puede, motivo = (
            diagnostico_emision(lote, recursos_firma)
            if lote.estado == ESTADO_APROBADA
            else (False, None)
        )
        return render(
            "lote_certificados.html",
            request,
            sesion=sesion,
            lote=lote,
            estado_visible=_ESTADOS_VISIBLES.get(lote.estado, lote.estado),
            plantillas=plantillas,
            firmas=firmas,
            puede_emitir=puede,
            motivo_no_emite=motivo,
            puede_aprobar=(
                pendiente and rol == ROL_APROBADOR_CONTENIDO and generador
            ),
            puede_descartar=(
                pendiente and rol == ROL_APROBADOR_CONTENIDO
            ),
            es_generador=generador,
            muestra_disponible=bool(lote.personas),
            csrf=sesion.csrf_token,
            aviso=aviso,
            aviso_error=aviso_error,
        )

    @app.get("/certificados/{id_lote}", response_class=HTMLResponse)
    def detalle_lote(request: Request, id_lote: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        lote = repositorio.obtener(id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        return _render_lote(request, sesion, lote)

    @app.get("/certificados/{id_lote}/muestra.pdf")
    def muestra(request: Request, id_lote: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        lote = repositorio.obtener(id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        if not lote.personas:
            return Response(
                "La lista del lote se retiró por retención mínima.",
                status_code=409,
                media_type="text/plain; charset=utf-8",
            )
        pdf = generar_pdf_muestra_lote(
            persona=lote.personas[0],
            actividad=dict(lote.actividad),
            linea_descriptiva=lote.linea_descriptiva,
            recursos_firma=recursos_firma,
            firmantes=FIRMANTES_DECLARADOS,
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{lote.id_lote}-muestra.pdf"'
                )
            },
        )

    @app.post("/certificados/{id_lote}/decidir")
    async def decidir(request: Request, id_lote: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        form = await request.form()
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            return render("sin_permiso.html", request, status_code=403)
        lote = repositorio.obtener(id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        resultado = repositorio.decidir(
            id_lote=id_lote,
            hash_lote=str(form.get("hash_lote", "")),
            accion=str(form.get("accion", "")),
            validador_hash=hash_correo(sesion.correo),
            rol=rol_de(sesion) or "",
            origen_identidad=sesion.origen,
            version_agente=version_agente,
            ahora=datetime.now(timezone.utc),
        )
        if resultado.codigo == CODIGO_INEXISTENTE:
            return render("sin_permiso.html", request, status_code=404)
        actualizado = repositorio.obtener(id_lote) or lote
        return _render_lote(
            request,
            sesion,
            actualizado,
            aviso=_AVISOS_DECISION.get(resultado.codigo, resultado.codigo),
            aviso_error=resultado.codigo in _AVISOS_ERROR,
        )


__all__ = [
    "ACCION_APROBAR",
    "ACCION_DESCARTAR",
    "CODIGO_APROBADA",
    "CODIGO_DESCARTADA",
    "CODIGO_DUPLICADA",
    "CODIGO_INEXISTENTE",
    "CODIGO_LOTE_OBSOLETO",
    "CODIGO_NO_ES_GENERADOR",
    "CODIGO_ROL_NO_AUTORIZADO",
    "ESTADO_APROBADA",
    "ESTADO_DESCARTADA",
    "ESTADO_PENDIENTE",
    "EstadoFirmas",
    "EstadoPlantilla",
    "LoteCertificados",
    "LoteCertificadosError",
    "RepositorioLotes",
    "ResultadoDecisionLote",
    "diagnostico_emision",
    "estado_firmas",
    "estado_plantillas",
    "lotes_para_bandeja",
    "registrar_rutas_certificados",
]
