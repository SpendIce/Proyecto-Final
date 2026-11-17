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
- **La lista de cierre y la línea descriptiva se retienen sólo mientras el
  lote opera.** La purga diaria del canal web (`purgar_canal_web`, con el
  rol de mantenimiento) pone `personas` y `linea_descriptiva` en NULL en
  los lotes ya decididos; conserva cantidad, hashes, plantilla y la
  decisión con identidad, rol, origen y versión del agente. La muestra se
  genera al vuelo y no se persiste.
- **La web no emite.** Después de aprobar, la página informa si el lote
  puede emitir con las reglas vigentes —plantilla aprobada por hash (ADR
  0020) y firmas disponibles (R2 de #160)— y, si no, por qué. La emisión
  sigue siendo del circuito de certificados: acá no se manda ningún correo
  ni se toca Drive.
- **Un lote de demostración queda aislado del circuito institucional.**
  Se reconoce por el predicado inyectado `es_lote_demo` (su objeto es el
  canónico de la semilla ficticia): fuera del modo demostración no se
  puede decidir ni se ofrecen los controles, y su decisión vive sólo en
  `lotes_certificados` —nunca un `apruebo_lote` en el registro que lee la
  emisión—. Un lote real conserva el circuito y el puente de siempre.
- **Una sesión demo no ve lotes reales.** La visibilidad la decide sólo
  `sesion_puede_ver_lote`: lo que `es_lote_demo` no reconoce como demo
  es real —incluido un legacy `NULL` que no es la semilla— y la sesión
  demo recibe 404, sin
  distinguir un lote ajeno de uno inexistente. La bandeja usa el mismo
  predicado, así que tampoco lista sus nombres ni su cuenta.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

import psycopg
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg.types.json import Jsonb
from starlette.exceptions import HTTPException

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
from ..decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    DECISION_APRUEBO_LOTE,
    RESULTADO_REGISTRADA,
    ROL_ORIGEN_PADRON,
    TIPO_LINEA_DESCRIPTIVA,
    TIPO_LOTE,
    DecisionesFormError,
    RegistroDecisiones,
    ResultadoDecision,
)
from ..linea_descriptiva import objeto_id_linea_descriptiva
from ..plantillas_aprobadas import (
    PlantillaCorreo,
    id_version_plantilla,
    plantilla_version_registrada,
)
from .formularios import leer_formulario_acotado
from .sesiones import ORIGEN_DEMO, Sesion

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
CODIGO_REGISTRO_NO_DISPONIBLE = "registro_decisiones_no_disponible"
CODIGO_CONFIRMACION_REQUERIDA = "confirmacion_requerida"

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
    CODIGO_REGISTRO_NO_DISPONIBLE: (
        "La decisión quedó registrada, pero no se pudo asentar en el "
        "registro de decisiones: la emisión no la verá hasta reconciliarlo."
    ),
    CODIGO_CONFIRMACION_REQUERIDA: (
        "Para aprobar, marcá la casilla que confirma la línea "
        "descriptiva y la lista del lote."
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
        CODIGO_REGISTRO_NO_DISPONIBLE,
        CODIGO_CONFIRMACION_REQUERIDA,
    }
)

_ESTADOS_EMISION = {
    "SIN_PEDIDO": "Sin emisión pedida",
    "EN_COLA": "En cola",
    "EMITIENDO": "Emitiendo",
    "GENERADA_DEMO": "Generada · demostración",
    "EMITIDA": "Emitida · enviada",
    "EMITIDA_PARCIAL": "Emitida parcialmente",
    "BLOQUEADA": "Bloqueada",
    "FALLIDA": "Fallida",
    "EMISION_INDETERMINADA": "Emisión indeterminada",
}

# Códigos de bloqueo del servicio de emisión con su texto operativo: lo
# que la página dice es accionable (qué insumo falta), nunca una traza.
_BLOQUEOS_EMISION = {
    "identidad_no_verificada": "La emisión requiere una sesión y una aprobación con identidad Google verificada.",
    "lote_no_aprobado": "El lote todavía no está aprobado.",
    "no_es_generador": "La emisión la pide quien generó el lote.",
    "aprobador_no_es_generador": (
        "La emisión la pide quien generó el lote."
    ),
    "signature_resources_missing": "Faltan las firmas en custodia (R2).",
    "approved_template_missing": (
        "Falta la plantilla aprobada (ADR 0020)."
    ),
    "template_version_unapproved": (
        "La plantilla no tiene la aprobación registrada sobre su "
        "versión (ADR 0020)."
    ),
    "actividad_datos_incompletos": (
        "A la actividad le faltan datos en la fuente institucional "
        "(horario, modalidad u otros)."
    ),
    "linea_descriptiva_no_aprobada": (
        "La línea descriptiva no tiene la aprobación registrada."
    ),
    "personas_purgadas": (
        "La lista del lote se retiró por retención mínima."
    ),
    "emision_indeterminada": (
        "La emisión quedó indeterminada: no se reintenta en automático."
    ),
    "config_incompleta": (
        "La emisión no está habilitada en este despliegue."
    ),
}

_AVISOS_EMISION = {
    CODIGO_LOTE_OBSOLETO: _AVISOS_DECISION[CODIGO_LOTE_OBSOLETO],
    CODIGO_INEXISTENTE: _AVISOS_DECISION[CODIGO_INEXISTENTE],
    "no_es_generador": "La emisión la pide quien generó el lote.",
    "aprobador_no_es_generador": (
        "La emisión la pide quien generó el lote."
    ),
    "rol_no_autorizado": "El rol no habilita a pedir la emisión.",
    "sin_permiso": "El rol no habilita a pedir la emisión.",
    "lote_no_aprobado": "El lote todavía no está aprobado.",
    "duplicada": "Ya hay una emisión pedida para este lote.",
    "lote_no_demo": (
        "La descarga de demostración es sólo para lotes de demostración."
    ),
    "estado_invalido": (
        "La emisión todavía no está en un estado que lo permite."
    ),
}

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
    linea_descriptiva: str | None
    linea_descriptiva_hash: str
    plantilla_muestra: str
    estado: str
    generada_por_hash: str
    creada_en: datetime
    decidida_en: datetime | None = None
    decidida_por_hash: str | None = None
    rol_decision: str | None = None
    origen_identidad: str | None = None
    version_agente: str | None = None
    origen_creacion: str | None = None


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
        return not self.faltantes


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
        origen_creacion: str | None = None,
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
        if origen_creacion not in (None, "google", "demo"):
            raise LoteCertificadosError("origen_creacion_invalido")
        datos = {
            clave: str(actividad.get(clave, "") or "").strip()
            for clave in _REQUERIDOS_ACTIVIDAD
        }
        if not all(datos.values()):
            raise LoteCertificadosError("actividad_datos_incompletos")
        fecha_fin = str(actividad.get("fecha_fin", "") or "").strip()
        if fecha_fin:
            datos["fecha_fin"] = fecha_fin
        validadas = parsear_lista_cierre(
            [
                [p.nombre, p.apellido, p.dni, p.mail, p.tratamiento, p.condicion]
                for p in personas
            ]
        )
        if not linea_descriptiva or not str(linea_descriptiva).strip():
            raise LoteCertificadosError("linea_descriptiva_ausente")
        linea = str(linea_descriptiva).strip()
        hash_linea = hashlib.sha256(linea.encode("utf-8")).hexdigest()
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
                    " linea_descriptiva_hash, plantilla_muestra, estado,"
                    " generada_por_hash, origen_creacion,"
                    " creada_en) VALUES"
                    " (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
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
                        hash_linea,
                        plantilla,
                        ESTADO_PENDIENTE,
                        generada_por_hash,
                        origen_creacion,
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

    def purgar_cerrados(
        self,
        *,
        ahora: datetime | None = None,
        abandono_dias: int = 30,
    ) -> int:
        """Retira la lista y la línea de los lotes decididos.

        Corre con el rol de mantenimiento en la purga diaria, como
        `RepositorioWeb.purgar_prosa`: la app no puede tocar el contenido
        que la retención cerró. La cantidad, los hashes y la decisión
        (identidad, rol, origen y versión) quedan.

        Con la cola de emisión (#168) la regla se ordena por el trabajo,
        no por una bandera:

        - Un trabajo **activo o indeterminado** (`PENDIENTE`, `RESERVADA`,
          `ENVIANDO`, `INDETERMINADA`) retiene el snapshot siempre: la
          ejecución o la intervención humana lo necesitan íntegro.
        - Un trabajo **terminal** retiene hasta `retencion_hasta`: la
          descarga demo y la auditoría del resultado viven de él.
        - **Sin trabajo**, el lote nuevo pendiente o aprobado (`google` o
          `demo`) se conserva `abandono_dias` desde su creación o decisión: puede
          pedirse la emisión todavía. El legacy (`origen_creacion`
          `NULL`) y todo `DESCARTADA` purgan en el acto, como antes: un
          lote descartado no puede emitir nada y retenerlo no sirve.
        """
        ahora = ahora or datetime.now(timezone.utc)
        abandono = ahora - timedelta(days=abandono_dias)
        with self._conexion_factory() as conn:
            with conn.transaction():
                filas = conn.execute(
                    "UPDATE lotes_certificados SET personas = NULL,"
                    " linea_descriptiva = NULL, purgada_en = %s"
                    " WHERE personas IS NOT NULL"
                    "   AND (estado = ANY(%s) OR ("
                    "     estado = 'PENDIENTE_APROBACION'"
                    "     AND origen_creacion IS NOT NULL))"
                    "   AND NOT EXISTS ("
                    "     SELECT 1 FROM emisiones_certificados e"
                    "     WHERE e.id_lote = lotes_certificados.id_lote"
                    "       AND e.estado IN ("
                    "         'PENDIENTE', 'RESERVADA', 'ENVIANDO',"
                    "         'INDETERMINADA')"
                    "   )"
                    "   AND ("
                    "     EXISTS ("
                    "       SELECT 1 FROM emisiones_certificados e"
                    "       WHERE e.id_lote = lotes_certificados.id_lote"
                    "         AND e.retencion_hasta IS NOT NULL"
                    "         AND e.retencion_hasta <= %s"
                    "     )"
                    "     OR ("
                    "       NOT EXISTS ("
                    "         SELECT 1 FROM emisiones_certificados e"
                    "         WHERE e.id_lote = lotes_certificados.id_lote"
                    "       )"
                    "       AND ("
                    "         origen_creacion IS NULL"
                    "         OR estado = 'DESCARTADA'"
                    "         OR COALESCE(decidida_en, creada_en) <= %s"
                    "       )"
                    "     )"
                    "   ) RETURNING id_lote",
                    (
                        ahora,
                        [ESTADO_APROBADA, ESTADO_DESCARTADA],
                        ahora,
                        abandono,
                    ),
                ).fetchall()
        return len(filas)


_SELECT = (
    "SELECT id_lote, id_actividad, objeto_lote, hash_lista, actividad,"
    " personas, cantidad_personas, linea_descriptiva, linea_descriptiva_hash,"
    " plantilla_muestra, estado, generada_por_hash, creada_en,"
    " decidida_en, decidida_por_hash,"
    " rol_decision, origen_identidad, version_agente, origen_creacion"
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
        linea_descriptiva_hash=fila[8],
        plantilla_muestra=fila[9],
        estado=fila[10],
        generada_por_hash=fila[11],
        creada_en=fila[12],
        decidida_en=fila[13],
        decidida_por_hash=fila[14],
        rol_decision=fila[15],
        origen_identidad=fila[16],
        version_agente=fila[17],
        origen_creacion=fila[18],
    )


def estado_plantillas(
    condiciones: tuple[str, ...],
    *,
    plantillas_aprobadas: dict[str, PlantillaCorreo] | None = None,
    registro_decisiones: RegistroDecisiones | None = None,
) -> tuple[EstadoPlantilla, ...]:
    """Plantilla de cada condición y si su versión está habilitada.

    `aprobacion` compone el diseño institucional recibido (ADR 0017) y no
    depende de una decisión de contenido. `asistencia` exige la versión de
    `certificado_asistencia` con la `apruebo_contenido` registrada sobre su
    hash (ADR 0020): sin el archivo o sin el registro, la página informa
    que falta. La verificación final sigue siendo la del circuito.
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
            continue
        plantilla = (plantillas_aprobadas or {}).get("certificado_asistencia")
        if plantilla is None:
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
        elif plantilla_version_registrada(
            registro_decisiones,
            tipo="certificado_asistencia",
            plantilla=plantilla,
        ):
            resultado.append(
                EstadoPlantilla(
                    condicion=condicion,
                    nombre=id_version_plantilla(
                        "certificado_asistencia", plantilla
                    ),
                    estado="Versión con aprobación registrada (ADR 0020)",
                    aprobada=True,
                )
            )
        else:
            resultado.append(
                EstadoPlantilla(
                    condicion=condicion,
                    nombre=id_version_plantilla(
                        "certificado_asistencia", plantilla
                    ),
                    estado="Versión sin aprobación registrada (ADR 0020)",
                    aprobada=False,
                )
            )
    return tuple(resultado)


def estado_firmas(
    recursos: RecursosFirma | None, condiciones: tuple[str, ...]
) -> EstadoFirmas:
    """Qué recursos de firma exige el lote y cuáles faltan (R2 de #160).

    La custodia de imágenes (símbolo y firmas) sólo la exige el certificado
    de `aprobacion`, que compone el diseño SEU; el de `asistencia` lleva el
    bloque de firmantes en el texto y no consume imágenes.
    """
    if "aprobacion" not in condiciones:
        return EstadoFirmas(configuradas=recursos is not None, faltantes=())
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
    lote: LoteCertificados,
    recursos: RecursosFirma | None,
    *,
    plantillas_aprobadas: dict[str, PlantillaCorreo] | None = None,
    registro_decisiones: RegistroDecisiones | None = None,
) -> tuple[bool, str | None]:
    """¿Esta pantalla ve algún bloqueo para emitir y, si no, cuál es?

    Revisa lo que puede verificar: firmas disponibles (R2) y la plantilla
    de `asistencia` con su aprobación registrada (ADR 0020). No reemplaza
    la verificación del circuito de emisión —que además exige la plantilla
    de `correo_certificado` y la línea descriptiva aprobada—: devolver
    `True` significa «sin bloqueo conocido acá», nunca «emitido».
    """
    if not lote.personas:
        return False, "la lista del lote se retiró por retención mínima"
    condiciones = tuple(p.condicion for p in lote.personas)
    firmas = estado_firmas(recursos, condiciones)
    if not firmas.disponible:
        return False, "faltan firmas (R2)"
    plantillas = estado_plantillas(
        condiciones,
        plantillas_aprobadas=plantillas_aprobadas,
        registro_decisiones=registro_decisiones,
    )
    sin_aprobar = [p for p in plantillas if not p.aprobada]
    if sin_aprobar:
        return (
            False,
            "falta la plantilla aprobada de "
            + ", ".join(p.condicion for p in sin_aprobar)
            + " (ADR 0020)",
        )
    return True, None


def registrar_aprobacion_en_registro(
    registro: RegistroDecisiones | None,
    *,
    lote: LoteCertificados,
    validador_hash: str,
    rol: str,
    ahora: datetime | None = None,
) -> None:
    """Asienta la aprobación web en el registro que lee la emisión (#168).

    La emisión sigue consultando `revisar_aprobacion_lote` sobre
    `decisiones-procesadas.jsonl`: sin esta línea, aprobar en la web no
    habilitaría el lote. El asiento guarda solo hashes, como el resto del
    registro. El descarte no se escribe: el catálogo de `lote` sólo tiene
    `apruebo_lote`, y un descarte no habilita ninguna emisión.

    Cuando el lote nació del pedido web (`origen_creacion` declarado, no
    del lote sembrado por el circuito anterior) la misma aprobación
    asienta antes la `apruebo_contenido` sobre el objeto exacto de la
    línea descriptiva: quien genera el lote aprueba con un solo gesto la
    línea y la lista que está viendo (ADR 0018). En los lotes legacy la
    línea ya la aprobó el circuito previo y no se toca.
    """
    if (
        registro is None
        or lote.origen_identidad == ORIGEN_DEMO
        or getattr(lote, "origen_creacion", None) == ORIGEN_DEMO
    ):
        return
    ahora = ahora or datetime.now(timezone.utc)
    marca = ahora.isoformat()
    if (
        getattr(lote, "origen_creacion", None) is not None
        and lote.linea_descriptiva
    ):
        objeto_linea = objeto_id_linea_descriptiva(
            lote.id_actividad, lote.linea_descriptiva
        )
        registro.registrar(
            ResultadoDecision(
                id_respuesta=hashlib.sha256(
                    f"web_linea|{objeto_linea}|{validador_hash}|{marca}".encode(
                        "utf-8"
                    )
                ).hexdigest(),
                correo_hash=validador_hash,
                rol=rol,
                rol_origen=ROL_ORIGEN_PADRON,
                tipo=TIPO_LINEA_DESCRIPTIVA,
                objeto_id=objeto_linea,
                decision=DECISION_APRUEBO_CONTENIDO,
                resultado=RESULTADO_REGISTRADA,
                rechazo_codigo=None,
                marca_temporal_form=marca,
                timestamp=marca,
            )
        )
    id_respuesta = hashlib.sha256(
        f"web_lote|{lote.objeto_lote}|{validador_hash}|{marca}".encode(
            "utf-8"
        )
    ).hexdigest()
    registro.registrar(
        ResultadoDecision(
            id_respuesta=id_respuesta,
            correo_hash=validador_hash,
            rol=rol,
            rol_origen=ROL_ORIGEN_PADRON,
            tipo=TIPO_LOTE,
            objeto_id=lote.objeto_lote,
            decision=DECISION_APRUEBO_LOTE,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=marca,
            timestamp=marca,
        )
    )


class RepositorioLotesPuerto(Protocol):
    """Lo que la app necesita del repositorio; el fake de pruebas lo cumple."""

    def listar(self) -> list[LoteCertificados]: ...

    def obtener(self, id_lote: str) -> LoteCertificados | None: ...

    def decidir(self, **datos) -> ResultadoDecisionLote: ...


class EmisionCertificadosWebPuerto(Protocol):
    """El servicio durable de emisión del contrato (#168).

    Lo implementa `web.emision_certificados` del backend: la UI sólo lo
    consulta (GET) y le pide emisión (POST); el trabajo corre por fuera
    del HTTP. `ErrorEmisionWeb` del backend lleva `code` estable y se
    reconoce por atributo.
    """

    def consultar(self, id_lote: str, *, actor) -> object: ...

    def solicitar(
        self, id_lote: str, *, hash_lote: str, actor
    ) -> object: ...

    def descargar(self, id_lote: str, *, actor) -> bytes: ...


def sesion_puede_ver_lote(
    sesion: Sesion,
    lote: LoteCertificados,
    es_lote_demo: Callable[[LoteCertificados], bool],
) -> bool:
    """¿Esta sesión puede ver y operar este lote? (ADR 0019)

    Una sesión demo sólo accede a lotes de demostración según
    `es_lote_demo`: `origen_creacion = 'demo'` (migración 0012) o la
    semilla histórica sembrada antes de la columna, que la siembra
    idempotente vuelve a devolver. Todo lo demás —incluido un lote
    legacy `NULL` con datos que no son la semilla— es real y queda fuera
    del alcance de la sesión demo, que ni siquiera debe saber que existe.
    Una sesión con identidad verificada no cambia: ve todos los lotes.
    """
    if sesion.origen != ORIGEN_DEMO:
        return True
    return es_lote_demo(lote)


def lotes_para_bandeja(
    repositorio: RepositorioLotesPuerto,
    *,
    es_lote_demo: Callable[[LoteCertificados], bool] | None = None,
    puede_ver: Callable[[LoteCertificados], bool] | None = None,
) -> list[dict[str, object]]:
    """Filas de la sección «Lotes de certificados» de la bandeja."""
    lotes = repositorio.listar()
    if puede_ver is not None:
        lotes = [lote for lote in lotes if puede_ver(lote)]
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
            "demo": es_lote_demo(lote) if es_lote_demo else False,
        }
        for lote in lotes
    ]


Render = Callable[..., HTMLResponse]
Autorizar = Callable[[Request], Sesion | None]
RolDe = Callable[[Sesion], str | None]
CsrfOk = Callable[[Sesion, str | None], bool]
DestinoLogin = Callable[[], Response]


EsLoteDemo = Callable[[LoteCertificados], bool]
DemoVigente = Callable[[], bool]


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
    es_lote_demo: EsLoteDemo,
    demo_vigente: DemoVigente,
    recursos_firma: RecursosFirma | None = None,
    registro_decisiones: RegistroDecisiones | None = None,
    plantillas_aprobadas: dict[str, PlantillaCorreo] | None = None,
    emision_certificados: "EmisionCertificadosWebPuerto | None" = None,
) -> None:
    """Cablea las rutas finas del lote; la lógica vive en este módulo.

    `emision_certificados` es el servicio durable del contrato (lo
    implementa el backend): con él la página del lote enlaza a
    `/certificados/{id}/emision`, cuyo GET sólo consulta el estado y
    cuyo POST es la única vía que encola. Sin él (pruebas legacy) las
    rutas y el enlace no existen.
    """

    def _puede_decidir(sesion: Sesion) -> bool:
        return rol_de(sesion) == ROL_APROBADOR_CONTENIDO

    def _lote_visible(
        sesion: Sesion, id_lote: str
    ) -> LoteCertificados | None:
        """El lote, o `None` si no existe o la sesión no puede verlo.

        Las rutas devuelven el mismo 404 en ambos casos: la sesión demo no
        distingue un lote real de uno inexistente (ADR 0019).
        """
        lote = repositorio.obtener(id_lote)
        if lote is None or not sesion_puede_ver_lote(sesion, lote, es_lote_demo):
            return None
        return lote

    def _decision_bloqueada(lote: LoteCertificados) -> bool:
        """Lote demo fuera de la demostración: no se decide acá."""
        return es_lote_demo(lote) and not demo_vigente()

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
        condiciones = tuple(p.condicion for p in lote.personas)
        plantillas = estado_plantillas(
            condiciones,
            plantillas_aprobadas=plantillas_aprobadas,
            registro_decisiones=registro_decisiones,
        )
        firmas = estado_firmas(recursos_firma, condiciones)
        puede, motivo = (
            diagnostico_emision(
                lote,
                recursos_firma,
                plantillas_aprobadas=plantillas_aprobadas,
                registro_decisiones=registro_decisiones,
            )
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
                pendiente
                and rol == ROL_APROBADOR_CONTENIDO
                and generador
                and not _decision_bloqueada(lote)
            ),
            puede_descartar=(
                pendiente
                and rol == ROL_APROBADOR_CONTENIDO
                and not _decision_bloqueada(lote)
            ),
            decision_demo_bloqueada=_decision_bloqueada(lote),
            es_generador=generador,
            muestra_disponible=bool(lote.personas),
            registro_configurado=registro_decisiones is not None,
            requiere_confirmacion=(
                getattr(lote, "origen_creacion", None) is not None
            ),
            emision_disponible=emision_certificados is not None,
            csrf=sesion.csrf_token,
            aviso=aviso,
            aviso_error=aviso_error,
        )

    @app.get("/certificados/{id_lote}", response_class=HTMLResponse)
    def detalle_lote(request: Request, id_lote: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if not _puede_decidir(sesion):
            return render("sin_permiso.html", request, status_code=403)
        lote = _lote_visible(sesion, id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        return _render_lote(request, sesion, lote)

    @app.get("/certificados/{id_lote}/muestra.pdf")
    def muestra(request: Request, id_lote: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if not _puede_decidir(sesion):
            return render("sin_permiso.html", request, status_code=403)
        lote = _lote_visible(sesion, id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        if not lote.personas or lote.linea_descriptiva is None:
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
        if not _puede_decidir(sesion):
            return render("sin_permiso.html", request, status_code=403)
        lote = _lote_visible(sesion, id_lote)
        if lote is None:
            return render("sin_permiso.html", request, status_code=404)
        try:
            form = await leer_formulario_acotado(request, max_bytes=8192)
        except HTTPException as error:
            return Response("Formulario inválido o demasiado grande.", status_code=error.status_code)
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            return render("sin_permiso.html", request, status_code=403)
        es_demo = es_lote_demo(lote)
        if es_demo and not demo_vigente():
            return render("sin_permiso.html", request, status_code=403)
        if (
            str(form.get("accion", "")) == ACCION_APROBAR
            and getattr(lote, "origen_creacion", None) is not None
            and str(form.get("confirmar", "")) != "si"
        ):
            # El pedido nuevo exige la confirmación explícita de la
            # línea descriptiva y la lista antes de aprobar (ADR 0018).
            return _render_lote(
                request,
                sesion,
                lote,
                aviso=_AVISOS_DECISION[CODIGO_CONFIRMACION_REQUERIDA],
                aviso_error=True,
            )
        ahora = datetime.now(timezone.utc)
        resultado = repositorio.decidir(
            id_lote=id_lote,
            hash_lote=str(form.get("hash_lote", "")),
            accion=str(form.get("accion", "")),
            validador_hash=hash_correo(sesion.correo),
            rol=rol_de(sesion) or "",
            origen_identidad=sesion.origen,
            version_agente=version_agente,
            ahora=ahora,
        )
        if resultado.codigo == CODIGO_INEXISTENTE:
            return render("sin_permiso.html", request, status_code=404)
        actualizado = repositorio.obtener(id_lote) or lote
        aviso = _AVISOS_DECISION.get(resultado.codigo, resultado.codigo)
        aviso_error = resultado.codigo in _AVISOS_ERROR
        # El puente al registro institucional es sólo para lotes reales:
        # la decisión demo vive en la fila del lote y nada más.
        if (
            resultado.codigo == CODIGO_APROBADA
            and not es_demo
            and sesion.origen != ORIGEN_DEMO
            and not demo_vigente()
        ):
            try:
                registrar_aprobacion_en_registro(
                    registro_decisiones,
                    lote=actualizado,
                    validador_hash=hash_correo(sesion.correo),
                    rol=rol_de(sesion) or "",
                    ahora=ahora,
                )
            except DecisionesFormError:
                aviso = _AVISOS_DECISION[CODIGO_REGISTRO_NO_DISPONIBLE]
                aviso_error = True
        return _render_lote(
            request,
            sesion,
            actualizado,
            aviso=aviso,
            aviso_error=aviso_error,
        )

    # ---------- emisión (servicio durable del contrato) ----------

    if emision_certificados is not None:

        def _actor(sesion: Sesion):
            """Construye el actor desde la sesión y la configuración vigentes."""
            from .emision_certificados import ActorCertificadosWeb

            return ActorCertificadosWeb(
                solicitante_hash=hash_correo(sesion.correo),
                rol=rol_de(sesion) or "",
                origen_identidad=sesion.origen,
                modo_demo=demo_vigente(),
            )

        def _consultar_emision(
            request: Request, sesion: Sesion, id_lote: str
        ):
            """Estado para la pantalla, o `None` si el servicio rechaza."""
            try:
                return emision_certificados.consultar(
                    id_lote, actor=_actor(sesion)
                )
            except RuntimeError as error:
                if getattr(error, "code", None) is None:
                    raise
                return None

        def _render_emision(
            request: Request,
            sesion: Sesion,
            lote: LoteCertificados,
            estado,
            aviso: str | None = None,
            aviso_error: bool = False,
            status_code: int = 200,
        ) -> HTMLResponse:
            return render(
                "emision_certificados.html",
                request,
                sesion=sesion,
                lote=lote,
                emision=estado,
                estado_visible=(
                    _ESTADOS_EMISION.get(estado.estado, estado.estado)
                    if estado is not None
                    else None
                ),
                es_demo=(
                    es_lote_demo(lote)
                    or (estado.es_demo if estado is not None else False)
                ),
                bloqueos=(
                    [
                        {
                            "codigo": codigo,
                            "texto": _BLOQUEOS_EMISION.get(codigo),
                        }
                        for codigo in estado.bloqueos
                    ]
                    if estado is not None
                    else []
                ),
                csrf=sesion.csrf_token,
                aviso=aviso,
                aviso_error=aviso_error,
                status_code=status_code,
            )

        @app.get("/certificados/{id_lote}/emision", response_class=HTMLResponse)
        def estado_emision(request: Request, id_lote: str) -> Response:
            """La página de la emisión: sólo consulta, nunca encola."""
            sesion = autorizar(request)
            if sesion is None:
                return destino_login()
            if not _puede_decidir(sesion):
                return render("sin_permiso.html", request, status_code=403)
            lote = _lote_visible(sesion, id_lote)
            if lote is None:
                return render("sin_permiso.html", request, status_code=404)
            if es_lote_demo(lote) and not demo_vigente():
                return render("sin_permiso.html", request, status_code=403)
            estado = _consultar_emision(request, sesion, id_lote)
            if estado is None:
                return render("sin_permiso.html", request, status_code=403)
            return _render_emision(request, sesion, lote, estado)

        @app.post("/certificados/{id_lote}/emision")
        async def pedir_emision(request: Request, id_lote: str) -> Response:
            """La única vía que encola la emisión durable.

            El hash del lote viaja del formulario y se compara con el
            persistido: pedir con el hash viejo no encola nada. Un doble
            POST devuelve el trabajo existente: la reserva es del
            servicio, no de esta ruta.
            """
            sesion = autorizar(request)
            if sesion is None:
                return destino_login()
            if not _puede_decidir(sesion):
                return render("sin_permiso.html", request, status_code=403)
            lote = _lote_visible(sesion, id_lote)
            if lote is None:
                return render("sin_permiso.html", request, status_code=404)
            try:
                form = await leer_formulario_acotado(request, max_bytes=8192)
            except HTTPException as error:
                return Response("Formulario inválido o demasiado grande.", status_code=error.status_code)
            if not csrf_ok(sesion, str(form.get("csrf", ""))):
                return render("sin_permiso.html", request, status_code=403)
            if es_lote_demo(lote) and not demo_vigente():
                return render("sin_permiso.html", request, status_code=403)
            if str(form.get("hash_lote", "")) != lote.objeto_lote:
                estado = _consultar_emision(request, sesion, id_lote)
                return _render_emision(
                    request,
                    sesion,
                    lote,
                    estado,
                    aviso=_AVISOS_EMISION[CODIGO_LOTE_OBSOLETO],
                    aviso_error=True,
                    status_code=409,
                )
            try:
                estado = emision_certificados.solicitar(
                    id_lote,
                    hash_lote=lote.objeto_lote,
                    actor=_actor(sesion),
                )
            except RuntimeError as error:
                codigo = getattr(error, "code", None)
                if codigo is None:
                    raise
                estado = _consultar_emision(request, sesion, id_lote)
                return _render_emision(
                    request,
                    sesion,
                    lote,
                    estado,
                    aviso=_AVISOS_EMISION.get(
                        codigo,
                        f"No se pudo pedir la emisión ({codigo}).",
                    ),
                    aviso_error=True,
                )
            return RedirectResponse(
                f"/certificados/{id_lote}/emision", status_code=303
            )

        @app.get("/certificados/{id_lote}/emision/descargar")
        def descargar_emision(request: Request, id_lote: str) -> Response:
            """El ZIP de la emisión de demostración, tras GENERADA_DEMO."""
            sesion = autorizar(request)
            if sesion is None:
                return destino_login()
            if not _puede_decidir(sesion):
                return render("sin_permiso.html", request, status_code=403)
            lote = _lote_visible(sesion, id_lote)
            if lote is None:
                return render("sin_permiso.html", request, status_code=404)
            if es_lote_demo(lote) and not demo_vigente():
                return render("sin_permiso.html", request, status_code=403)
            try:
                contenido = emision_certificados.descargar(
                    id_lote, actor=_actor(sesion)
                )
            except RuntimeError as error:
                if getattr(error, "code", None) is None:
                    raise
                return render("sin_permiso.html", request, status_code=403)
            return Response(
                content=contenido,
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        "attachment; filename="
                        f'"certificados-demo-{lote.id_lote}.zip"'
                    )
                },
            )

__all__ = [
    "ACCION_APROBAR",
    "ACCION_DESCARTAR",
    "CODIGO_APROBADA",
    "CODIGO_CONFIRMACION_REQUERIDA",
    "CODIGO_DESCARTADA",
    "CODIGO_DUPLICADA",
    "CODIGO_INEXISTENTE",
    "CODIGO_LOTE_OBSOLETO",
    "CODIGO_NO_ES_GENERADOR",
    "CODIGO_ROL_NO_AUTORIZADO",
    "ESTADO_APROBADA",
    "ESTADO_DESCARTADA",
    "ESTADO_PENDIENTE",
    "EmisionCertificadosWebPuerto",
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
    "registrar_aprobacion_en_registro",
    "registrar_rutas_certificados",
    "sesion_puede_ver_lote",
]
