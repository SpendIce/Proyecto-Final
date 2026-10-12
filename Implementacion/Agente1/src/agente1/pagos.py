"""Corrida de control de pagos de HU-012: comprobantes, cuotas, no asociadas.

En cada corrida el agente recalcula la situación de pagos de cada preinscripto
a partir de las fuentes del diseño — el plan de pago de la actividad, el padrón
y su propio buzón (ADR 0004) — sin guardar un estado de pago por persona (ADR
0003). La única interfaz pública de la corrida es `correr_control_pagos`: una
función pura en el sentido que el diseño exige — sin reloj (el día entra por
parámetro), sin red y sin persistencia — porque todo lo que toca llega por
puertos inyectados y nada de lo que deriva se escribe. El buzón que ve es el
que el llamante le da: la cuenta técnica en vivo, una carpeta `.eml` o el fake.

Qué hace la corrida, en el orden de §4.2 del diseño:

1. **Asocia respuestas.** El asunto normalizado (se quitan los prefijos de
   respuesta `Re:`/`RV:`, se colapsan espacios y se compara sin mayúsculas ni
   acentos) tiene que coincidir con el `asunto_preinscripcion` del plan, y el
   remitente con el `email_destinatario` de una sola fila del padrón. Sin
   coincidencia — o con más de una — la respuesta va a «no asociadas» con su
   motivo. Nunca se asocia por nombre ni por similitud: lo que no encaja lo
   resuelve una persona.
2. **Cuenta comprobantes.** Una respuesta asociada con al menos un adjunto PDF
   o imagen cuenta como comprobante presentado (D13, sin OCR). Los comprobantes
   se distinguen por el sha256 del adjunto: la misma captura enviada dos veces
   cuenta una sola vez.
3. **Asigna cuotas.** Los comprobantes distintos de cada persona se asignan en
   orden cronológico a las cuotas no bonificadas, de la 1 a la N; los que
   exceden quedan informados como comprobantes sin cuota.
4. **Deriva estados.** `BONIFICADA` si el padrón marca al preinscripto como
   bonificado; `COMPROBANTE_PRESENTADO` si la cuota recibió comprobante;
   `PENDIENTE` en caso contrario. `PAGO_CONFIRMADO` existe en el modelo pero
   sólo puede salir de una novedad del Departamento (D1), que es otro ticket.
   «Vencida» no es un estado: se deriva de `PENDIENTE` más `hoy` pasada la
   fecha de referencia.

El plan se lee de un CSV en formato largo — una fila por dato, cada uno con su
procedencia declarada — conforme al contrato versionado
`contracts/plan_pagos_actividad_v1.json`. El padrón es el CSV exportado del
origen de inscripción (D10). Ambos loaders fallan cerrado: lo que el contrato
no contempla se rechaza con código, no se ignora.

Lo que falta para el alcance completo de HU-012 pagos: la pestaña «Novedades
de pago» del Departamento (precedencia sobre lo derivado) y el lote diario de
recordatorios con su plantilla preaprobada. Esta interfaz los recibe como
entradas adicionales cuando entren.
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

CONTRACT_VERSION = CONTRATO_PLAN["x-contract-version"]
STATUS = CONTRATO_PLAN["x-status"]
PROCEDENCIAS_DATO = frozenset(CONTRATO_PLAN["procedencia_dato"])
CAMPOS_ACTIVIDAD = frozenset(CONTRATO_PLAN["campos_actividad"])
CAMPOS_CUOTA = frozenset(CONTRATO_PLAN["campos_cuota"])
ESTADOS_CUOTA = frozenset(CONTRATO_PLAN["estados_derivados_cuota"])
MOTIVOS_NO_ASOCIADA = frozenset(CONTRATO_PLAN["motivos_no_asociada"])
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
class SituacionCuota:
    """Estado derivado de una cuota de una persona en esta corrida."""

    nro_cuota: int
    estado: str
    fecha_referencia: date
    vencida: bool
    comprobante: Comprobante | None


@dataclass(frozen=True)
class SituacionPreinscripto:
    """Lo que la corrida derivó para una fila del padrón."""

    id_inscripcion: str
    nombre_destinatario: str
    email_destinatario: str
    cuotas: tuple[SituacionCuota, ...]
    comprobantes_sin_cuota: tuple[Comprobante, ...]

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
    situaciones: tuple[SituacionPreinscripto, ...]
    no_asociadas: tuple[RespuestaNoAsociada, ...]


def cargar_plan_pagos_csv(path: Path) -> PlanPago:
    """Lee el plan de pago desde un CSV en formato largo.

    Cada fila es un dato: `campo`, `valor`, `procedencia` y `evidencia`
    opcional. Las cuotas llegan como `cuota_<n>_monto` y `cuota_<n>_vencimiento`
    con `n` entre 1 y `cantidad_cuotas`. Falla cerrado: un campo que el
    contrato no nombra, una procedencia fuera del vocabulario o una cuota que
    rompe la secuencia 1..N son un rechazo con código, no un dato ignorado.
    """

    filas = _leer_filas(path, COLUMNAS_PLAN_OBLIGATORIAS, "plan")
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

    filas = _leer_filas(path, COLUMNAS_PADRON_OBLIGATORIAS, "padron")
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


def correr_control_pagos(
    *,
    plan: PlanPago,
    padron: Sequence[Preinscripto],
    buzon: BuzonPropio,
    hoy: date,
) -> InformeCorridaPagos:
    """La corrida: de las fuentes al informe, sin persistir nada.

    Es la única interfaz pública de la corrida de control de pagos. Recibe el
    plan ya cargado, el padrón ya leído, el buzón como puerto — la corrida lo
    relee adentro, porque cuando haya recordatorios el lote se arma sobre la
    lectura más reciente — y el día como parámetro. Devuelve el informe
    completo; no escribe en disco, no llama a la red, no consulta un reloj.
    """

    asunto_plan = _normalizar_asunto(plan.asunto_preinscripcion)
    por_remitente: dict[str, list[Preinscripto]] = {}
    for persona in padron:
        por_remitente.setdefault(persona.email_destinatario, []).append(persona)

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
        coincidencias = por_remitente.get(mensaje.remitente, [])
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

    situaciones = tuple(
        _derivar_situacion(
            persona,
            plan,
            asociadas.get(persona.id_inscripcion, []),
            hoy,
        )
        for persona in padron
    )
    return InformeCorridaPagos(
        actividad_id=plan.actividad_id,
        actividad=plan.actividad,
        hoy=hoy,
        contract_version=CONTRACT_VERSION,
        situaciones=situaciones,
        no_asociadas=tuple(no_asociadas),
    )


def _derivar_situacion(
    persona: Preinscripto,
    plan: PlanPago,
    mensajes: Sequence[MensajeBuzon],
    hoy: date,
) -> SituacionPreinscripto:
    """Deriva las cuotas de una persona: comprobantes distintos, en orden, a
    las cuotas 1..N no bonificadas; el resto queda informado sin cuota."""

    comprobantes = _comprobantes_distintos(mensajes)
    bonificado = persona.bonificado is True
    asignables = () if bonificado else comprobantes[: len(plan.cuotas)]
    excedentes = comprobantes if bonificado else comprobantes[len(plan.cuotas) :]

    cuotas = []
    for indice, cuota_plan in enumerate(plan.cuotas):
        comprobante = asignables[indice] if indice < len(asignables) else None
        if bonificado:
            estado = ESTADO_BONIFICADA
        elif comprobante is not None:
            estado = ESTADO_COMPROBANTE_PRESENTADO
        else:
            estado = ESTADO_PENDIENTE
        referencia = plan.fecha_referencia(cuota_plan)
        cuotas.append(
            SituacionCuota(
                nro_cuota=cuota_plan.nro,
                estado=estado,
                fecha_referencia=referencia,
                vencida=estado == ESTADO_PENDIENTE and hoy > referencia,
                comprobante=comprobante,
            )
        )
    return SituacionPreinscripto(
        id_inscripcion=persona.id_inscripcion,
        nombre_destinatario=persona.nombre_destinatario,
        email_destinatario=persona.email_destinatario,
        cuotas=tuple(cuotas),
        comprobantes_sin_cuota=tuple(excedentes),
    )


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
    path: Path, obligatorias: tuple[str, ...], nombre: str
) -> list[dict[str, str]]:
    """Lee un CSV y valida el encabezado de forma posicional.

    El encabezado tiene que empezar con las columnas obligatorias en ese orden
    exacto — el mismo criterio del adapter de Sheets — y sólo puede seguir con
    columnas declaradas en el contrato del recurso. Las filas desalineadas
    (más o menos celdas que el encabezado) se rechazan.
    """

    permitidas = COLUMNAS_PLAN if nombre == "plan" else COLUMNAS_PADRON
    with Path(path).open(encoding="utf-8", newline="") as archivo:
        reader = csv.DictReader(archivo)
        encabezados = reader.fieldnames or []
        if (
            tuple(encabezados[: len(obligatorias)]) != obligatorias
            or set(encabezados) - set(permitidas)
            or len(encabezados) != len(set(encabezados))
        ):
            raise ControlPagosError(f"{nombre}_encabezado_invalid")
        filas: list[dict[str, str]] = []
        for fila in reader:
            if None in fila or any(v is None for v in fila.values()):
                raise ControlPagosError(f"{nombre}_fila_invalid")
            filas.append(dict(fila))
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
