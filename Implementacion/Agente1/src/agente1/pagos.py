"""Corrida de control de pagos de HU-012: comprobantes, cuotas, novedades.

En cada corrida el agente recalcula la situación de pagos de cada preinscripto
a partir de las fuentes del diseño — el plan de pago de la actividad, el padrón,
su propio buzón (ADR 0004) y las novedades de pago que carga el Departamento
(§6.2) — sin guardar un estado de pago por persona (ADR 0003). La única
interfaz pública de la corrida es `correr_control_pagos`: una función pura en
el sentido que el diseño exige — sin reloj (el día entra por parámetro), sin
red y sin persistencia — porque todo lo que toca llega por puertos inyectados
y nada de lo que deriva se escribe. El buzón que ve es el que el llamante le
da: la cuenta técnica en vivo, una carpeta `.eml` o el fake.

Qué hace la corrida, en el orden de §4.2 y §6.2 del diseño:

1. **Asocia respuestas.** El asunto normalizado (se quitan los prefijos de
   respuesta `Re:`/`RV:`, se colapsan espacios y se compara sin mayúsculas ni
   acentos) tiene que coincidir con el `asunto_preinscripcion` del plan, y el
   remitente con el `email_destinatario` de una sola fila del padrón — o con
   una dirección alternativa que el Departamento haya cargado como novedad
   `EMAIL_ALTERNATIVO`. Sin coincidencia — o con más de una — la respuesta va
   a «no asociadas» con su motivo. Nunca se asocia por nombre ni por
   similitud: lo que no encaja lo resuelve una persona.
2. **Cuenta comprobantes.** Una respuesta asociada con al menos un adjunto PDF
   o imagen cuenta como comprobante presentado (D13, sin OCR). Los comprobantes
   se distinguen por el sha256 del adjunto: la misma captura enviada dos veces
   cuenta una sola vez.
3. **Asigna cuotas.** Los comprobantes distintos de cada persona se asignan en
   orden cronológico a las cuotas no bonificadas, de la 1 a la N; los que
   exceden quedan informados como comprobantes sin cuota.
4. **Deriva estados.** `BONIFICADA` si la persona está bonificada (columna del
   padrón o novedad `BONIFICADO`); `COMPROBANTE_PRESENTADO` si la cuota recibió
   comprobante; `PENDIENTE` en caso contrario. «Vencida» no es un estado: se
   deriva de `PENDIENTE` más `hoy` pasada la fecha de referencia.
5. **Aplica novedades.** Las novedades del Departamento se aplican después de
   lo derivado del buzón y tienen precedencia sobre esa derivación (§6.2):
   `CONFIRMADO_FUNDACION` es el único origen posible de `PAGO_CONFIRMADO` (D1),
   `COMPROBANTE_RECHAZADO` devuelve la cuota a `PENDIENTE`,
   `COMPROBANTE_CUBRE_N_CUOTAS` extiende el primer comprobante a N cuotas y
   `BONIFICADO` marca todas las cuotas de la persona. Una novedad con tipo
   desconocido, `id_inscripcion` inexistente, valor mal formado o efecto
   incoherente con lo derivado se informa como error de la novedad: no se
   ignora en silencio ni se aplica.

El plan se lee de un CSV en formato largo — una fila por dato, cada uno con su
procedencia declarada — conforme al contrato versionado
`contracts/plan_pagos_actividad_v1.json`. El padrón es el CSV exportado del
origen de inscripción (D10) y las novedades replican la pestaña «Novedades de
pago» de la planilla D2 según `contracts/novedades_pago_v1.json`. Los tres
loaders fallan cerrado: lo que el contrato no contempla se rechaza con código,
no se ignora. Las mismas tres fuentes pueden leerse de las pestañas de la
planilla D2 para la demo en vivo — `pagos_sheets.GoogleSheetsFuentePagos` —
porque la interpretación de las filas está separada del soporte y es la misma
para los dos caminos.

Lo que falta para el alcance completo de HU-012 pagos: el lote diario de
recordatorios con su plantilla preaprobada. Esta interfaz lo recibirá como
salida adicional cuando entre.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from importlib.resources import files
from pathlib import Path
import re
from typing import Sequence
import unicodedata

from .buzon import BuzonPropio, MensajeBuzon


CONTRATO_PLAN = json.loads(
    files("agente1")
    .joinpath("contracts", "plan_pagos_actividad_v1.json")
    .read_text(encoding="utf-8")
)

CONTRATO_NOVEDADES = json.loads(
    files("agente1")
    .joinpath("contracts", "novedades_pago_v1.json")
    .read_text(encoding="utf-8")
)

CONTRACT_VERSION = CONTRATO_PLAN["x-contract-version"]
STATUS = CONTRATO_PLAN["x-status"]
NOVEDADES_CONTRACT_VERSION = CONTRATO_NOVEDADES["x-contract-version"]
PROCEDENCIAS_DATO = frozenset(CONTRATO_PLAN["procedencia_dato"])
CAMPOS_ACTIVIDAD = frozenset(CONTRATO_PLAN["campos_actividad"])
CAMPOS_CUOTA = frozenset(CONTRATO_PLAN["campos_cuota"])
ESTADOS_CUOTA = frozenset(CONTRATO_PLAN["estados_derivados_cuota"])
MOTIVOS_NO_ASOCIADA = frozenset(CONTRATO_PLAN["motivos_no_asociada"])
TIPOS_NOVEDAD = frozenset(CONTRATO_NOVEDADES["tipos_novedad"])
MOTIVOS_NOVEDAD_INVALIDA = frozenset(
    CONTRATO_NOVEDADES["motivos_novedad_invalida"]
)
PREGUNTAS_ABIERTAS = tuple(CONTRATO_PLAN["preguntas_abiertas"])

ESTADO_BONIFICADA = "BONIFICADA"
ESTADO_PAGO_CONFIRMADO = "PAGO_CONFIRMADO"
ESTADO_COMPROBANTE_PRESENTADO = "COMPROBANTE_PRESENTADO"
ESTADO_PENDIENTE = "PENDIENTE"
# Las cuotas que cuentan para el «k de N», según §3.2 del diseño.
ESTADOS_CUBIERTOS = frozenset(
    {ESTADO_BONIFICADA, ESTADO_PAGO_CONFIRMADO, ESTADO_COMPROBANTE_PRESENTADO}
)

MOTIVO_ASUNTO_NO_COINCIDE = "asunto_no_coincide"
MOTIVO_REMITENTE_NO_INFORMADO = "remitente_no_informado"
MOTIVO_REMITENTE_SIN_COINCIDENCIA = "remitente_sin_coincidencia"
MOTIVO_REMITENTE_AMBIGUO = "remitente_ambiguo"

# Catálogo cerrado de la pestaña «Novedades de pago» del Departamento (§6.2).
NOVEDAD_CONFIRMADO_FUNDACION = "CONFIRMADO_FUNDACION"
NOVEDAD_COMPROBANTE_RECHAZADO = "COMPROBANTE_RECHAZADO"
NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS = "COMPROBANTE_CUBRE_N_CUOTAS"
NOVEDAD_EMAIL_ALTERNATIVO = "EMAIL_ALTERNATIVO"
NOVEDAD_BONIFICADO = "BONIFICADO"

MOTIVO_NOVEDAD_DATO_INVALID = "novedad_dato_invalid"
MOTIVO_NOVEDAD_TIPO_DESCONOCIDO = "novedad_tipo_desconocido"
MOTIVO_NOVEDAD_VALOR_INVALID = "novedad_valor_invalid"
MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA = "novedad_inscripcion_desconocida"
MOTIVO_NOVEDAD_NO_APLICABLE = "novedad_no_aplicable"

# Coherencia con el contrato: el módulo no puede emitir un estado ni un motivo
# que el contrato no declara, porque el informe es la cara visible del catálogo.
assert ESTADOS_CUOTA == frozenset(
    {
        ESTADO_BONIFICADA,
        ESTADO_PAGO_CONFIRMADO,
        ESTADO_COMPROBANTE_PRESENTADO,
        ESTADO_PENDIENTE,
    }
)
assert MOTIVOS_NO_ASOCIADA == frozenset(
    {
        MOTIVO_ASUNTO_NO_COINCIDE,
        MOTIVO_REMITENTE_NO_INFORMADO,
        MOTIVO_REMITENTE_SIN_COINCIDENCIA,
        MOTIVO_REMITENTE_AMBIGUO,
    }
)
assert TIPOS_NOVEDAD == frozenset(
    {
        NOVEDAD_CONFIRMADO_FUNDACION,
        NOVEDAD_COMPROBANTE_RECHAZADO,
        NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS,
        NOVEDAD_EMAIL_ALTERNATIVO,
        NOVEDAD_BONIFICADO,
    }
)
assert MOTIVOS_NOVEDAD_INVALIDA == frozenset(
    {
        MOTIVO_NOVEDAD_DATO_INVALID,
        MOTIVO_NOVEDAD_TIPO_DESCONOCIDO,
        MOTIVO_NOVEDAD_VALOR_INVALID,
        MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA,
        MOTIVO_NOVEDAD_NO_APLICABLE,
    }
)

# Columnas del CSV del plan (formato largo: una fila por dato).
COLUMNAS_PLAN = ("campo", "valor", "procedencia", "evidencia")
COLUMNAS_PLAN_OBLIGATORIAS = COLUMNAS_PLAN[:3]
# Una cuota llega como datos `cuota_<n>_<monto|vencimiento>`; el número de orden
# va en el nombre porque una pestaña de planilla no tiene filas anidadas.
PATRON_CAMPO_CUOTA = re.compile(r"\Acuota_(\d+)_(monto|vencimiento)\Z")

# Columnas del CSV del padrón exportado del origen de inscripción. `bonificado`
# es la columna opcional de D14: si falta, la condición de bonificación de la
# persona no es verificable por esta vía.
COLUMNAS_PADRON = (
    "id_inscripcion",
    "actividad_id",
    "nombre_destinatario",
    "email_destinatario",
    "bonificado",
)
COLUMNAS_PADRON_OBLIGATORIAS = COLUMNAS_PADRON[:4]

# Columnas del CSV de la pestaña «Novedades de pago» (§6.2). Las cinco son
# obligatorias: fecha y responsable existen para trazabilidad, no para efecto.
COLUMNAS_NOVEDADES = (
    "id_inscripcion",
    "tipo",
    "valor",
    "fecha",
    "responsable",
)

EMAIL_PADRON_RE = re.compile(r"[^\s@]+@[^\s@]+\Z")

# Un comprobante es un adjunto PDF o imagen (D13). El tipo lo declara la pieza
# MIME; no se inspecciona el contenido.
TIPO_ADJUNTO_PDF = "application/pdf"
PREFIJO_ADJUNTO_IMAGEN = "image/"

# Prefijos de respuesta que se eliminan al normalizar el asunto (§4.2).
PATRON_PREFIJO_RESPUESTA = re.compile(r"\A\s*(?:re|rv)\s*:\s*", re.IGNORECASE)

_FECHA_MINIMA = datetime.min.replace(tzinfo=timezone.utc)


class ControlPagosError(ValueError):
    """Falla de las fuentes de la corrida, identificada por un código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CuotaPlan:
    """Una cuota del plan: su orden, monto, vencimiento y procedencia."""

    nro: int
    monto: int
    vencimiento: date | None
    procedencia_monto: str
    procedencia_vencimiento: str


@dataclass(frozen=True)
class PlanPago:
    """El plan de pago de una actividad, con la procedencia de cada dato.

    `procedencias` mapea cada campo de actividad a su procedencia declarada;
    las cuotas llevan la suya en `CuotaPlan`. La procedencia no decide nada en
    la corrida — se conserva porque el plan existe para justificar de dónde salió
    cada monto y cada fecha ante la SEU.
    """

    actividad_id: str
    actividad: str
    asunto_preinscripcion: str
    fecha_inicio: date
    fecha_limite_inscripcion: date | None
    cuotas: tuple[CuotaPlan, ...]
    medios_pago: tuple[str, ...]
    categorias_bonificadas: tuple[str, ...]
    procedencias: dict[str, str]
    evidencias: dict[str, str]

    def fecha_referencia(self, cuota: CuotaPlan) -> date:
        """Fecha que manda para la cuota: su vencimiento propio, o la fecha
        límite de inscripción, o el inicio si no hay ninguna de las dos."""
        return (
            cuota.vencimiento
            or self.fecha_limite_inscripcion
            or self.fecha_inicio
        )


@dataclass(frozen=True)
class Preinscripto:
    """Una fila del padrón de la actividad.

    `bonificado` es `None` cuando el padrón no puede acreditar la condición —
    columna ausente o celda vacía (D14) — y no equivale a «no bonificado»: la
    bonificación no verificable se marca en el lote, no se asume.
    """

    id_inscripcion: str
    actividad_id: str
    nombre_destinatario: str
    email_destinatario: str
    bonificado: bool | None


@dataclass(frozen=True)
class Comprobante:
    """Un comprobante distinto presentado por una persona.

    La identidad del comprobante es el sha256 del adjunto; `fecha` y
    `message_id` ubican el envío más antiguo en que apareció.
    """

    sha256: str
    tipo: str
    nombre: str | None
    fecha: datetime | None
    message_id: str


@dataclass(frozen=True)
class NovedadPago:
    """Una fila de la pestaña «Novedades de pago» del Departamento (§6.2).

    Los campos llegan como texto crudo del CSV: su validez se decide dentro de
    la corrida, para que una novedad inválida se informe como error de la
    novedad en el informe en lugar de tirar abajo la lectura del archivo.
    `fila` es el número de fila del archivo contando el encabezado como 1 —
    trazabilidad para que una persona ubique la novedad en la fuente.
    """

    id_inscripcion: str
    tipo: str
    valor: str
    fecha: str
    responsable: str
    fila: int


@dataclass(frozen=True)
class NovedadConError:
    """Una novedad que no se aplicó, con el motivo cerrado del rechazo.

    El motivo sale del catálogo del contrato: dato inválido, tipo desconocido,
    valor inválido, inscripción desconocida o efecto incoherente con lo
    derivado. La novedad queda visible para que una persona la corrija.
    """

    novedad: NovedadPago
    motivo: str


@dataclass(frozen=True)
class SituacionCuota:
    """Estado derivado de una cuota de una persona en esta corrida."""

    nro_cuota: int
    estado: str
    fecha_referencia: date
    vencida: bool
    comprobante: Comprobante | None


@dataclass(frozen=True)
class SituacionPreinscripto:
    """Lo que la corrida derivó para una fila del padrón.

    `bonificacion_no_verificable` es la marca de D14: el plan declara
    categorías bonificadas y el padrón no informa la condición de esta persona
    (columna ausente o celda vacía). El estado de las cuotas no se asume: la
    marca existe para que el informe exponga que la bonificación no es
    verificable por esta vía.
    """

    id_inscripcion: str
    nombre_destinatario: str
    email_destinatario: str
    cuotas: tuple[SituacionCuota, ...]
    comprobantes_sin_cuota: tuple[Comprobante, ...]
    bonificacion_no_verificable: bool

    @property
    def cuotas_cubiertas(self) -> int:
        """El «k» de «k de N»: cuotas bonificadas, confirmadas o con comprobante."""
        return sum(1 for c in self.cuotas if c.estado in ESTADOS_CUBIERTOS)


@dataclass(frozen=True)
class RespuestaNoAsociada:
    """Un mensaje del buzón que no se pudo asociar, con el motivo cerrado."""

    message_id: str
    remitente: str
    asunto: str
    fecha: datetime | None
    motivo: str


@dataclass(frozen=True)
class InformeCorridaPagos:
    """La salida completa de la corrida: lo derivado, sin persistir nada."""

    actividad_id: str
    actividad: str
    hoy: date
    contract_version: str
    novedades_contract_version: str
    situaciones: tuple[SituacionPreinscripto, ...]
    no_asociadas: tuple[RespuestaNoAsociada, ...]
    novedades_aplicadas: tuple[NovedadPago, ...]
    novedades_con_error: tuple[NovedadConError, ...]


def cargar_plan_pagos_csv(path: Path) -> PlanPago:
    """Lee el plan de pago desde un CSV en formato largo.

    Cada fila es un dato: `campo`, `valor`, `procedencia` y `evidencia`
    opcional. Las cuotas llegan como `cuota_<n>_monto` y `cuota_<n>_vencimiento`
    con `n` entre 1 y `cantidad_cuotas`. Falla cerrado: un campo que el
    contrato no nombra, una procedencia fuera del vocabulario o una cuota que
    rompe la secuencia 1..N son un rechazo con código, no un dato ignorado.
    """

    return _plan_desde_filas(
        _leer_filas(path, COLUMNAS_PLAN_OBLIGATORIAS, COLUMNAS_PLAN, "plan")
    )


def _plan_desde_filas(filas: list[dict[str, str]]) -> PlanPago:
    """Interpreta las filas `campo/valor/procedencia/evidencia` como plan.

    Es la parte compartida de los dos caminos de lectura del plan — el CSV y
    la pestaña «Plan de pagos» de la planilla D2 — para que ambos produzcan
    exactamente el mismo `PlanPago` sobre la misma tabla.
    """

    datos: dict[str, str] = {}
    procedencias: dict[str, str] = {}
    evidencias: dict[str, str] = {}
    for fila in filas:
        campo = fila["campo"].strip()
        if not campo:
            raise ControlPagosError("plan_campo_desconocido")
        if campo in datos:
            raise ControlPagosError("plan_campo_duplicado")
        if campo not in CAMPOS_ACTIVIDAD and not PATRON_CAMPO_CUOTA.match(campo):
            raise ControlPagosError("plan_campo_desconocido")
        procedencia = fila["procedencia"].strip()
        if procedencia not in PROCEDENCIAS_DATO:
            raise ControlPagosError("plan_procedencia_invalid")
        datos[campo] = fila["valor"].strip()
        procedencias[campo] = procedencia
        if "evidencia" in fila:
            evidencias[campo] = fila["evidencia"].strip()

    obligatorios = {
        campo
        for campo, item in CONTRATO_PLAN["campos_actividad"].items()
        if item["obligatorio"]
    }
    for campo in sorted(obligatorios):
        if not datos.get(campo):
            raise ControlPagosError("plan_dato_obligatorio_ausente")

    cantidad_cuotas = _parsear_entero(datos["cantidad_cuotas"], minimo=1)
    por_numero: dict[int, dict[str, str]] = {}
    for campo, valor in datos.items():
        coincidencia = PATRON_CAMPO_CUOTA.match(campo)
        if not coincidencia:
            continue
        por_numero.setdefault(int(coincidencia.group(1)), {})[
            coincidencia.group(2)
        ] = valor
    if set(por_numero) != set(range(1, cantidad_cuotas + 1)) or any(
        "monto" not in subcampos for subcampos in por_numero.values()
    ):
        raise ControlPagosError("plan_cuotas_inconsistentes")

    cuotas = tuple(
        CuotaPlan(
            nro=nro,
            monto=_parsear_entero(por_numero[nro]["monto"], minimo=1),
            vencimiento=_parsear_fecha_opcional(por_numero[nro].get("vencimiento")),
            procedencia_monto=procedencias[f"cuota_{nro}_monto"],
            procedencia_vencimiento=procedencias.get(
                f"cuota_{nro}_vencimiento", "DESCONOCIDO"
            ),
        )
        for nro in range(1, cantidad_cuotas + 1)
    )
    return PlanPago(
        actividad_id=datos["actividad_id"],
        actividad=datos["actividad"],
        asunto_preinscripcion=datos["asunto_preinscripcion"],
        fecha_inicio=_parsear_fecha(datos["fecha_inicio"]),
        fecha_limite_inscripcion=_parsear_fecha_opcional(
            datos.get("fecha_limite_inscripcion")
        ),
        cuotas=cuotas,
        medios_pago=_parsear_lista(datos.get("medios_pago")),
        categorias_bonificadas=_parsear_lista(datos.get("categorias_bonificadas")),
        procedencias=procedencias,
        evidencias=evidencias,
    )


def cargar_padron_csv(path: Path, *, actividad_id: str) -> list[Preinscripto]:
    """Lee el padrón de preinscriptos de la actividad desde un CSV.

    Exige las columnas del contrato en orden; `bonificado` es la única
    opcional (D14). Todas las filas deben pertenecer a `actividad_id`: un
    padrón de otra actividad se rechaza entero en lugar de filtrar en silencio
    — un archivo equivocado es un error de la persona que lo exportó, no un
    dato a corregir por el agente.
    """

    return _padron_desde_filas(
        _leer_filas(
            path, COLUMNAS_PADRON_OBLIGATORIAS, COLUMNAS_PADRON, "padron"
        ),
        actividad_id,
    )


def _padron_desde_filas(
    filas: list[dict[str, str]], actividad_id: str
) -> list[Preinscripto]:
    """Interpreta las filas del padrón, común al CSV y a la pestaña de D2."""

    padron: list[Preinscripto] = []
    ids_vistos: set[str] = set()
    for fila in filas:
        if fila["actividad_id"].strip() != actividad_id:
            raise ControlPagosError("padron_actividad_distinta")
        id_inscripcion = fila["id_inscripcion"].strip()
        if not id_inscripcion:
            raise ControlPagosError("padron_fila_invalid")
        if id_inscripcion in ids_vistos:
            raise ControlPagosError("padron_id_duplicado")
        ids_vistos.add(id_inscripcion)
        email = fila["email_destinatario"].strip().lower()
        if not EMAIL_PADRON_RE.match(email):
            raise ControlPagosError("padron_fila_invalid")
        padron.append(
            Preinscripto(
                id_inscripcion=id_inscripcion,
                actividad_id=actividad_id,
                nombre_destinatario=fila["nombre_destinatario"].strip(),
                email_destinatario=email,
                bonificado=_parsear_bonificado(fila.get("bonificado")),
            )
        )
    return padron


def cargar_novedades_csv(path: Path) -> list[NovedadPago]:
    """Lee las novedades de pago del Departamento desde un CSV (§6.2).

    Replica la pestaña «Novedades de pago» de la planilla D2: una fila por
    novedad con las cinco columnas del contrato en orden. La validación de
    forma del archivo es cerrada — encabezado equivocado o filas desalineadas
    se rechazan entero — pero el contenido de cada fila se evalúa dentro de la
    corrida, porque una novedad inválida es un error *de la novedad* que el
    informe tiene que mostrar, no un motivo para abortar la corrida.
    """

    return _novedades_desde_filas(
        _leer_filas(path, COLUMNAS_NOVEDADES, COLUMNAS_NOVEDADES, "novedades")
    )


def _novedades_desde_filas(filas: list[dict[str, str]]) -> list[NovedadPago]:
    """Interpreta las filas de la pestaña «Novedades de pago», común al CSV y
    a la planilla. `fila` numera desde 2: el encabezado es la fila 1 en ambos
    soportes, así una persona ubica la novedad en la fuente que sea."""

    return [
        NovedadPago(
            id_inscripcion=fila["id_inscripcion"].strip(),
            tipo=fila["tipo"].strip(),
            valor=fila["valor"].strip(),
            fecha=fila["fecha"].strip(),
            responsable=fila["responsable"].strip(),
            fila=numero,
        )
        for numero, fila in enumerate(filas, start=2)
    ]


def correr_control_pagos(
    *,
    plan: PlanPago,
    padron: Sequence[Preinscripto],
    buzon: BuzonPropio,
    hoy: date,
    novedades: Sequence[NovedadPago] = (),
) -> InformeCorridaPagos:
    """La corrida: de las fuentes al informe, sin persistir nada.

    Es la única interfaz pública de la corrida de control de pagos. Recibe el
    plan ya cargado, el padrón ya leído, el buzón como puerto — la corrida lo
    relee adentro, porque cuando haya recordatorios el lote se arma sobre la
    lectura más reciente —, las novedades del Departamento como entrada y el
    día como parámetro. Devuelve el informe completo; no escribe en disco, no
    llama a la red, no consulta un reloj.

    Las novedades son opcionales para no romper la firma: sin ellas la corrida
    es la de siempre. Las que pasan la validación de forma se aplican después
    de la derivación del buzón, con precedencia sobre ella; las inválidas e
    inaplicables vuelven en el informe con su motivo.
    """

    validas, con_error = _clasificar_novedades(novedades, plan, padron)

    personas_por_id = {persona.id_inscripcion: persona for persona in padron}
    # El remitente se resuelve contra el padrón más las direcciones
    # alternativas que el Departamento cargó (§4.2). El dict interno por id
    # evita que una misma persona cuente dos veces si la alternativa repite
    # su correo del padrón.
    por_remitente: dict[str, dict[str, Preinscripto]] = {}
    for persona in padron:
        por_remitente.setdefault(persona.email_destinatario, {})[
            persona.id_inscripcion
        ] = persona
    novedades_por_id: dict[str, list[NovedadPago]] = {}
    aplicadas: list[NovedadPago] = []
    for novedad in validas:
        if novedad.tipo == NOVEDAD_EMAIL_ALTERNATIVO:
            alternativa = novedad.valor.lower()
            por_remitente.setdefault(alternativa, {})[
                novedad.id_inscripcion
            ] = personas_por_id[novedad.id_inscripcion]
            aplicadas.append(novedad)
        else:
            novedades_por_id.setdefault(novedad.id_inscripcion, []).append(
                novedad
            )

    asunto_plan = _normalizar_asunto(plan.asunto_preinscripcion)
    asociadas: dict[str, list[MensajeBuzon]] = {}
    no_asociadas: list[RespuestaNoAsociada] = []
    for mensaje in buzon.listar():
        if _normalizar_asunto(mensaje.asunto) != asunto_plan:
            no_asociadas.append(_no_asociada(mensaje, MOTIVO_ASUNTO_NO_COINCIDE))
            continue
        if not mensaje.remitente:
            no_asociadas.append(
                _no_asociada(mensaje, MOTIVO_REMITENTE_NO_INFORMADO)
            )
            continue
        coincidencias = list(por_remitente.get(mensaje.remitente, {}).values())
        if not coincidencias:
            no_asociadas.append(
                _no_asociada(mensaje, MOTIVO_REMITENTE_SIN_COINCIDENCIA)
            )
            continue
        if len(coincidencias) > 1:
            no_asociadas.append(_no_asociada(mensaje, MOTIVO_REMITENTE_AMBIGUO))
            continue
        asociadas.setdefault(coincidencias[0].id_inscripcion, []).append(mensaje)

    no_asociadas.sort(key=lambda r: _clave_cronologica(r.fecha, r.message_id))

    situaciones: list[SituacionPreinscripto] = []
    for persona in padron:
        situacion, aplicadas_persona, error_persona = _derivar_situacion(
            persona,
            plan,
            asociadas.get(persona.id_inscripcion, []),
            novedades_por_id.get(persona.id_inscripcion, []),
            hoy,
        )
        situaciones.append(situacion)
        aplicadas.extend(aplicadas_persona)
        con_error.extend(error_persona)

    return InformeCorridaPagos(
        actividad_id=plan.actividad_id,
        actividad=plan.actividad,
        hoy=hoy,
        contract_version=CONTRACT_VERSION,
        novedades_contract_version=NOVEDADES_CONTRACT_VERSION,
        situaciones=tuple(situaciones),
        no_asociadas=tuple(no_asociadas),
        novedades_aplicadas=tuple(
            sorted(aplicadas, key=lambda n: n.fila)
        ),
        novedades_con_error=tuple(
            sorted(con_error, key=lambda e: e.novedad.fila)
        ),
    )


@dataclass
class _CuotaTrabajo:
    """La cuota mientras se deriva y se corrige: la novedad pisa el estado que
    dejó el buzón, así que el objeto es mutable hasta cerrar la situación."""

    nro: int
    estado: str
    comprobante: Comprobante | None


def _derivar_situacion(
    persona: Preinscripto,
    plan: PlanPago,
    mensajes: Sequence[MensajeBuzon],
    novedades: Sequence[NovedadPago],
    hoy: date,
) -> tuple[SituacionPreinscripto, list[NovedadPago], list[NovedadConError]]:
    """Deriva las cuotas de una persona y después aplica sus novedades.

    Primero el buzón: comprobantes distintos, en orden, a las cuotas 1..N no
    bonificadas. Después las novedades del Departamento, en el orden del
    archivo y con precedencia sobre lo derivado (§6.2). Devuelve también qué
    novedades se aplicaron y cuáles se informan como error.
    """

    comprobantes = _comprobantes_distintos(mensajes)
    bonificado = persona.bonificado is True or any(
        novedad.tipo == NOVEDAD_BONIFICADO for novedad in novedades
    )

    trabajo = [
        _CuotaTrabajo(
            nro=cuota_plan.nro,
            estado=ESTADO_BONIFICADA if bonificado else ESTADO_PENDIENTE,
            comprobante=None,
        )
        for cuota_plan in plan.cuotas
    ]
    if not bonificado:
        for cuota, comprobante in zip(trabajo, comprobantes):
            cuota.estado = ESTADO_COMPROBANTE_PRESENTADO
            cuota.comprobante = comprobante

    aplicadas: list[NovedadPago] = []
    con_error: list[NovedadConError] = []
    for novedad in novedades:
        if novedad.tipo == NOVEDAD_BONIFICADO:
            aplicadas.append(novedad)
            continue
        if bonificado:
            # Una bonificación de la persona no se corrige por cuota: la
            # novedad de cuota se informa como incoherente, no se descarta.
            con_error.append(
                NovedadConError(novedad, MOTIVO_NOVEDAD_NO_APLICABLE)
            )
            continue
        motivo = _aplicar_novedad_cuota(novedad, trabajo, comprobantes)
        if motivo is None:
            aplicadas.append(novedad)
        else:
            con_error.append(NovedadConError(novedad, motivo))

    asignados = {
        cuota.comprobante.sha256
        for cuota in trabajo
        if cuota.comprobante is not None
    }
    sin_cuota = tuple(
        comprobante
        for comprobante in comprobantes
        if comprobante.sha256 not in asignados
    )

    cuotas = []
    for cuota, cuota_plan in zip(trabajo, plan.cuotas):
        referencia = plan.fecha_referencia(cuota_plan)
        cuotas.append(
            SituacionCuota(
                nro_cuota=cuota.nro,
                estado=cuota.estado,
                fecha_referencia=referencia,
                vencida=cuota.estado == ESTADO_PENDIENTE and hoy > referencia,
                comprobante=cuota.comprobante,
            )
        )
    situacion = SituacionPreinscripto(
        id_inscripcion=persona.id_inscripcion,
        nombre_destinatario=persona.nombre_destinatario,
        email_destinatario=persona.email_destinatario,
        cuotas=tuple(cuotas),
        comprobantes_sin_cuota=sin_cuota,
        bonificacion_no_verificable=bool(plan.categorias_bonificadas)
        and persona.bonificado is None,
    )
    return situacion, aplicadas, con_error


def _aplicar_novedad_cuota(
    novedad: NovedadPago,
    trabajo: list[_CuotaTrabajo],
    comprobantes: tuple[Comprobante, ...],
) -> str | None:
    """Aplica una novedad de cuota sobre lo ya derivado. `None` si se aplicó;
    el motivo cerrado si el efecto contradice lo derivado."""

    if novedad.tipo == NOVEDAD_CONFIRMADO_FUNDACION:
        cuota = trabajo[int(novedad.valor) - 1]
        # La confirmación pisa lo derivado pero conserva el comprobante
        # presentado: el rastro de que la persona mandó su constancia queda.
        cuota.estado = ESTADO_PAGO_CONFIRMADO
        return None

    if novedad.tipo == NOVEDAD_COMPROBANTE_RECHAZADO:
        cuota = trabajo[int(novedad.valor) - 1]
        if cuota.estado != ESTADO_COMPROBANTE_PRESENTADO:
            return MOTIVO_NOVEDAD_NO_APLICABLE
        cuota.estado = ESTADO_PENDIENTE
        cuota.comprobante = None
        return None

    if novedad.tipo == NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS:
        if not comprobantes:
            return MOTIVO_NOVEDAD_NO_APLICABLE
        cubre = int(novedad.valor)
        # El primer comprobante pasa a cubrir las cuotas 1..N; los demás
        # comprobantes siguen a partir de la N+1 en el mismo orden.
        for cuota in trabajo[:cubre]:
            cuota.estado = ESTADO_COMPROBANTE_PRESENTADO
            cuota.comprobante = comprobantes[0]
        for comprobante, cuota in zip(comprobantes[1:], trabajo[cubre:]):
            cuota.estado = ESTADO_COMPROBANTE_PRESENTADO
            cuota.comprobante = comprobante
        return None

    # Inalcanzable: el catálogo se validó al clasificar. Se devuelve el motivo
    # igual para no depender de que el invariante se mantenga.
    return MOTIVO_NOVEDAD_TIPO_DESCONOCIDO


def _clasificar_novedades(
    novedades: Sequence[NovedadPago],
    plan: PlanPago,
    padron: Sequence[Preinscripto],
) -> tuple[list[NovedadPago], list[NovedadConError]]:
    """Separa las novedades válidas en forma de las que llegan con error.

    La coherencia con lo derivado (`novedad_no_aplicable`) no se puede juzgar
    acá — depende del buzón — así que las válidas en forma entran a la corrida
    y el efecto se evalúa por persona.
    """

    ids = {persona.id_inscripcion for persona in padron}
    validas: list[NovedadPago] = []
    con_error: list[NovedadConError] = []
    for novedad in novedades:
        motivo = _motivo_invalidez_novedad(novedad, len(plan.cuotas), ids)
        if motivo is None:
            validas.append(novedad)
        else:
            con_error.append(NovedadConError(novedad, motivo))
    return validas, con_error


def _motivo_invalidez_novedad(
    novedad: NovedadPago, cantidad_cuotas: int, ids: set[str]
) -> str | None:
    """El primer motivo que invalida la novedad en forma, o `None`.

    Orden fijo para que dos corridas sobre las mismas fuentes reporten lo
    mismo: estructura, catálogo, existencia en el padrón y por último el
    valor propio del tipo.
    """

    if (
        not novedad.id_inscripcion
        or not novedad.responsable
        or not _es_fecha_iso(novedad.fecha)
    ):
        return MOTIVO_NOVEDAD_DATO_INVALID
    if novedad.tipo not in TIPOS_NOVEDAD:
        return MOTIVO_NOVEDAD_TIPO_DESCONOCIDO
    if novedad.id_inscripcion not in ids:
        return MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA
    return _motivo_valor_novedad(novedad, cantidad_cuotas)


def _motivo_valor_novedad(
    novedad: NovedadPago, cantidad_cuotas: int
) -> str | None:
    """El `valor` se interpreta según el tipo: cuota o cantidad en 1..N,
    dirección de correo para EMAIL_ALTERNATIVO y vacío para BONIFICADO."""

    if novedad.tipo == NOVEDAD_BONIFICADO:
        return None if not novedad.valor else MOTIVO_NOVEDAD_VALOR_INVALID
    if novedad.tipo == NOVEDAD_EMAIL_ALTERNATIVO:
        if EMAIL_PADRON_RE.match(novedad.valor.lower()):
            return None
        return MOTIVO_NOVEDAD_VALOR_INVALID
    try:
        numero = int(novedad.valor)
    except ValueError:
        return MOTIVO_NOVEDAD_VALOR_INVALID
    if not 1 <= numero <= cantidad_cuotas:
        return MOTIVO_NOVEDAD_VALOR_INVALID
    return None


def _es_fecha_iso(valor: str) -> bool:
    if not valor:
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _comprobantes_distintos(
    mensajes: Sequence[MensajeBuzon],
) -> tuple[Comprobante, ...]:
    """Los comprobantes distintos de una persona, deduplicados por sha256 y
    ordenados por fecha de envío. Mandar dos veces la misma captura cuenta una
    sola vez: gana la aparición más antigua."""

    candidatos: list[Comprobante] = []
    for mensaje in sorted(
        mensajes, key=lambda m: _clave_cronologica(m.fecha, m.message_id)
    ):
        for adjunto in mensaje.adjuntos:
            if not _es_adjunto_comprobante(adjunto.tipo):
                continue
            candidatos.append(
                Comprobante(
                    sha256=adjunto.sha256,
                    tipo=adjunto.tipo,
                    nombre=adjunto.nombre,
                    fecha=mensaje.fecha,
                    message_id=mensaje.message_id,
                )
            )
    vistos: set[str] = set()
    distintos: list[Comprobante] = []
    for comprobante in candidatos:
        if comprobante.sha256 in vistos:
            continue
        vistos.add(comprobante.sha256)
        distintos.append(comprobante)
    return tuple(distintos)


def _es_adjunto_comprobante(tipo: str) -> bool:
    return tipo == TIPO_ADJUNTO_PDF or tipo.startswith(PREFIJO_ADJUNTO_IMAGEN)


def _normalizar_asunto(asunto: str) -> str:
    """El asunto comparable: sin prefijos de respuesta, espacios colapsados y
    sin mayúsculas ni acentos. Es equivalencia canónica — la misma cadena
    escrita distinto —, nunca una aproximación."""

    normalizado = unicodedata.normalize("NFKC", asunto)
    while True:
        recortado = PATRON_PREFIJO_RESPUESTA.sub("", normalizado, count=1)
        if recortado == normalizado:
            break
        normalizado = recortado
    return " ".join(normalizado.split()).casefold()


def _clave_cronologica(
    fecha: datetime | None, message_id: str
) -> tuple[datetime, str]:
    """Orden determinista por fecha; sin fecha se asume la más antigua y el
    Message-ID desempata, para que dos corridas ordenen igual."""
    return (fecha or _FECHA_MINIMA, message_id)


def _no_asociada(mensaje: MensajeBuzon, motivo: str) -> RespuestaNoAsociada:
    return RespuestaNoAsociada(
        message_id=mensaje.message_id,
        remitente=mensaje.remitente,
        asunto=mensaje.asunto,
        fecha=mensaje.fecha,
        motivo=motivo,
    )


def _leer_filas(
    path: Path,
    obligatorias: tuple[str, ...],
    permitidas: tuple[str, ...],
    nombre: str,
) -> list[dict[str, str]]:
    """Lee un CSV y valida el encabezado de forma posicional.

    El encabezado tiene que empezar con las columnas obligatorias en ese orden
    exacto — el mismo criterio del adapter de Sheets — y sólo puede seguir con
    columnas declaradas en el contrato del recurso. Las filas desalineadas
    (más o menos celdas que el encabezado) se rechazan.
    """

    with Path(path).open(encoding="utf-8", newline="") as archivo:
        reader = csv.DictReader(archivo)
        _validar_encabezado(
            reader.fieldnames or [], obligatorias, permitidas, nombre
        )
        filas: list[dict[str, str]] = []
        for fila in reader:
            if None in fila or any(v is None for v in fila.values()):
                raise ControlPagosError(f"{nombre}_fila_invalid")
            filas.append(dict(fila))
    return filas


def _validar_encabezado(
    encabezados: Sequence[str],
    obligatorias: tuple[str, ...],
    permitidas: tuple[str, ...],
    nombre: str,
) -> None:
    """La regla del encabezado, única para los dos soportes tabulares.

    Empieza con las columnas obligatorias en ese orden exacto y sólo puede
    seguir con columnas declaradas en el contrato del recurso, sin repetir.
    Un encabezado distinto es un rechazo explícito — `*_encabezado_invalid` —
    nunca una lectura silenciosa de una tabla que podría ser otra cosa.
    """

    if (
        tuple(encabezados[: len(obligatorias)]) != obligatorias
        or set(encabezados) - set(permitidas)
        or len(encabezados) != len(set(encabezados))
    ):
        raise ControlPagosError(f"{nombre}_encabezado_invalid")


def _filas_desde_tabla(
    tabla: list[object],
    obligatorias: tuple[str, ...],
    permitidas: tuple[str, ...],
    nombre: str,
) -> list[dict[str, str]]:
    """Convierte el `values` de una pestaña en las mismas filas que un CSV.

    Es la contraparte de `_leer_filas` para la planilla D2: la primera fila
    de `tabla` es el encabezado y se valida con la misma regla posicional, así
    una pestaña con encabezado distinto falla con el mismo `*_encabezado_invalid`
    del CSV. Las diferencias de forma entre los dos soportes se traducen acá:

    - Sheets recorta las celdas vacías del final de cada fila; se completan
      con vacíos, que es lo mismo que vale una línea CSV terminada en `,,,`.
    - Una fila `[]` es el equivalente de la línea en blanco que `DictReader`
      salta: se ignora. Una fila de celdas vacías (`["", ""]`) se conserva —
      igual que en el CSV `,,` — y la rechaza la validación de dominio.
    - Una fila más larga que el encabezado, que no sea una lista o que traiga
      celdas que no sean texto, se rechaza: es el `*_fila_invalid` del CSV.
    """

    if (
        not tabla
        or not isinstance(tabla[0], list)
        or any(not isinstance(celda, str) for celda in tabla[0])
    ):
        raise ControlPagosError(f"{nombre}_encabezado_invalid")
    encabezados = tabla[0]
    _validar_encabezado(encabezados, obligatorias, permitidas, nombre)

    filas: list[dict[str, str]] = []
    for fila_cruda in tabla[1:]:
        if fila_cruda == []:
            continue
        if (
            not isinstance(fila_cruda, list)
            or len(fila_cruda) > len(encabezados)
            or any(not isinstance(celda, str) for celda in fila_cruda)
        ):
            raise ControlPagosError(f"{nombre}_fila_invalid")
        filas.append(
            dict(
                zip(
                    encabezados,
                    [*fila_cruda, *([""] * (len(encabezados) - len(fila_cruda)))],
                    strict=True,
                )
            )
        )
    return filas


def _parsear_entero(valor: str, *, minimo: int) -> int:
    try:
        entero = int(valor)
    except ValueError:
        raise ControlPagosError("plan_valor_invalid") from None
    if entero < minimo:
        raise ControlPagosError("plan_valor_invalid")
    return entero


def _parsear_fecha(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ControlPagosError("plan_valor_invalid") from None


def _parsear_fecha_opcional(valor: str | None) -> date | None:
    if not valor:
        return None
    return _parsear_fecha(valor)


def _parsear_lista(valor: str | None) -> tuple[str, ...]:
    if not valor:
        return ()
    return tuple(item.strip() for item in valor.split("|") if item.strip())


def _parsear_bonificado(valor: str | None) -> bool | None:
    """La columna `bonificado` del padrón: `si`/`sí` afirma, `no` niega, vacío
    — o columna ausente — deja la condición sin verificar (D14)."""
    if valor is None:
        return None
    normalizado = valor.strip().casefold()
    if not normalizado:
        return None
    if normalizado in {"si", "sí"}:
        return True
    if normalizado == "no":
        return False
    raise ControlPagosError("padron_fila_invalid")
