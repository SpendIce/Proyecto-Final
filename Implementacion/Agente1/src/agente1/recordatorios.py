"""Circuito por lote del `recordatorio_pago` de HU-012 (D3, §5.3).

El recordatorio de una cuota `PENDIENTE` no tramita por solicitud
individual: la corrida de `pagos.py` lo planifica como ítem del lote del
día y este módulo lo encola hacia la entrega simulada, con un modelo de
autorización distinto del circuito por envío:

1. **La plantilla se aprueba una sola vez.** El texto provisional
   (`prompts/recordatorio_pago_provisional_v1.txt`) se registra bajo una
   clave derivada de su contenido y atraviesa la misma doble decisión del
   circuito — aprobación semántica y aprobación utilitaria — como una pieza
   más del registro. Mientras no esté `APROBADA`, ningún lote puede
   encolarse (`template_not_approved`).
2. **El lote lleva una aprobación utilitaria con su lista.** El Coordinador
   de Extensión aprueba el lote del día declarando exactamente qué ítems
   revisó: la decisión queda ligada al conjunto aprobado. Una lista que no
   cubre el lote es aprobación parcial y no autoriza nada
   (`batch_approval_partial`); una clave ajena al lote invalida la lista
   (`batch_item_unknown`); un ítem planeado que no figura en la lista no se
   encola.

Los ítems encolados comparten la infraestructura del circuito por envío —
registro durable por clave, `ItemEnvio`, la cola y `drenar_envios` contra
el fake — pero no su autorización: el ítem no pide aprobación por pieza
porque su texto es la plantilla ya aprobada y su envío es lo que el lote
autorizó. Por eso nace en `ENVIO_ENCOLADO`: la transición desde
`PENDIENTE_VALIDACION` es la materialización de la aprobación del lote, no
una aprobación escondida.

La clave del ítem la planificó la corrida — `sha256(tipo, actividad,
inscripción, cuota, anticipación)` (§5.2) — así que una segunda corrida del
mismo día produce las mismas claves, el registro las rechaza al crear y el
ítem se cuenta como `DUPLICADA`: nunca hay un segundo recordatorio.

La auditoría conserva lo de siempre: hashes, claves, roles y decisiones.
Los medios de pago del plan — incluidos links o datos bancarios cuando el
plan los declare — viajan sólo en el cuerpo renderizado, que el registro
guarda bajo la clave y el fake entrega; nunca en una línea del log.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from importlib.resources import files
from pathlib import Path
import re
import uuid

from .confirmaciones import (
    CLAVE_REGISTRO_RE,
    ESTADO_ENVIO_ENCOLADO,
    ESTADOS_PARCIALES_APROBACION,
    MARCADOR_BORRADOR,
    ROL_APROBACION_UTILITARIA,
    AprobacionHumana,
    ColaEnvios,
    DestinoConfirmaciones,
    ItemEnvio,
    RegistroConfirmaciones,
    ResultadoEnvioEncolado,
    _PARCIAL_POR_ROL,
    _aprobacion_valida,
    _hash,
    _seccion_cuerpo,
    drenar_envios,
)
from .pagos import (
    CONTRACT_VERSION as PLAN_CONTRACT_VERSION,
    ItemRecordatorio,
    LoteRecordatorios,
    PlanPago,
    TIPO_RECORDATORIO_PAGO,
)
from .tipos_notificacion import descripcion_tipo


HU = "HU-012"
CONTRACT_VERSION = PLAN_CONTRACT_VERSION
TEMPLATE_VERSION = "recordatorio_pago_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"

# El documento de plantilla: es la pieza que la SEU aprueba una sola vez.
# El cuerpo renderizado sale de su sección central; el documento completo —
# versión, estado, límites — es lo que queda cubierto por la aprobación.
TEXTO_PLANTILLA = (
    files("agente1")
    .joinpath("prompts", "recordatorio_pago_provisional_v1.txt")
    .read_text(encoding="utf-8")
)

# Clave bajo la que la plantilla vive en el registro: `sha256` del vector
# «ámbito, tipo, versión, texto». Como el texto entra al hash, aprobar esta
# clave es aprobar esa redacción exacta: cualquier cambio del documento es
# otra plantilla, que vuelve a empezar el circuito desde cero.
CLAVE_PLANTILLA_RECORDATORIO = _hash(
    json.dumps(
        [
            "plantilla",
            TIPO_RECORDATORIO_PAGO,
            TEMPLATE_VERSION,
            TEXTO_PLANTILLA,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
)

_PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


@dataclass(frozen=True)
class AprobacionLote:
    """La aprobación utilitaria del lote del día, ligada a su lista.

    `items` son las claves `sha256` de los ítems que la persona aprobó:
    tienen que ser exactamente las del lote planeado — ni una menos
    (aprobación parcial) ni una más (algo que no se planificó). La lista
    viaja en la decisión porque la autorización es del conjunto revisado,
    no del lote en abstracto.
    """

    aprobacion: AprobacionHumana
    items: tuple[str, ...]


@dataclass(frozen=True)
class ResultadoPlantilla:
    estado: str
    clave_plantilla: str
    log_path: Path
    correlation_id: str
    error: str | None = None


@dataclass(frozen=True)
class ResultadoItemLote:
    """Qué pasó con un ítem del lote al encolarlo."""

    idempotency_key: str
    estado: str


@dataclass(frozen=True)
class ResultadoLote:
    """Resultado de intentar encolar el lote planeado.

    `estado` es `ENVIO_ENCOLADO` cuando al menos un ítem quedó encolado,
    `DUPLICADA` cuando todos ya existían (una segunda corrida del mismo
    día), `VACIO` si el lote no tenía ítems, `RECHAZADA` si la decisión del
    lote fue negativa, e `INVALIDA` con `error` cuando la aprobación, la
    lista o la plantilla no habilitan el encolado.
    """

    estado: str
    clave_lote: str
    log_path: Path
    correlation_id: str
    items: tuple[ResultadoItemLote, ...]
    error: str | None = None


def registrar_plantilla_recordatorio(
    *,
    registro: RegistroConfirmaciones,
    directorio_salida: Path,
) -> ResultadoPlantilla:
    """Crea la entrada de la plantilla en `PENDIENTE_VALIDACION`.

    Idempotente por clave: registrar dos veces la misma redacción es
    `DUPLICADA`, porque la clave se deriva del texto. El ciclo de vida es
    el de cualquier pieza del circuito: doble aprobación humana antes de
    que sirva para algo.
    """

    correlation_id = str(uuid.uuid4())
    log_path = _log_path(directorio_salida)
    if not registro.crear(
        CLAVE_PLANTILLA_RECORDATORIO, TEMPLATE_VERSION, TEXTO_PLANTILLA
    ):
        _auditar(
            log_path,
            correlation_id=correlation_id,
            evento="plantilla",
            estado="DUPLICADA",
            resultado="idempotency_duplicate",
        )
        return ResultadoPlantilla(
            estado="DUPLICADA",
            clave_plantilla=CLAVE_PLANTILLA_RECORDATORIO,
            log_path=log_path,
            correlation_id=correlation_id,
            error="idempotency_duplicate",
        )
    _auditar(
        log_path,
        correlation_id=correlation_id,
        evento="plantilla",
        estado="PENDIENTE_VALIDACION",
        resultado="ok",
    )
    return ResultadoPlantilla(
        estado="PENDIENTE_VALIDACION",
        clave_plantilla=CLAVE_PLANTILLA_RECORDATORIO,
        log_path=log_path,
        correlation_id=correlation_id,
    )


def aprobar_plantilla_recordatorio(
    *,
    registro: RegistroConfirmaciones,
    directorio_salida: Path,
    aprobacion: AprobacionHumana,
) -> ResultadoPlantilla:
    """Registra una decisión sobre la plantilla: misma doble aprobación.

    Cada rol deja su estado parcial y la decisión del otro rol completa el
    circuito — los mismos `ESTADOS_PARCIALES_APROBACION` y `_PARCIAL_POR_ROL`
    del circuito por envío, así que la evidencia de doble decisión es la
    misma que la de una notificación por envío. Si la plantilla no fue
    registrada antes, la decisión la materializa, como en los otros
    circuitos. Una plantilla `RECHAZADA` es terminal: el lote que la exige
    queda `template_not_approved`.
    """

    correlation_id = str(uuid.uuid4())
    log_path = _log_path(directorio_salida)
    if not _aprobacion_valida(aprobacion):
        _auditar(
            log_path,
            correlation_id=correlation_id,
            evento="decision_plantilla",
            estado="INVALIDA",
            resultado="approval_invalid",
            aprobacion=aprobacion,
        )
        return ResultadoPlantilla(
            estado="INVALIDA",
            clave_plantilla=CLAVE_PLANTILLA_RECORDATORIO,
            log_path=log_path,
            correlation_id=correlation_id,
            error="approval_invalid",
        )
    existente = registro.obtener(CLAVE_PLANTILLA_RECORDATORIO)
    if existente is None:
        registro.crear(
            CLAVE_PLANTILLA_RECORDATORIO, TEMPLATE_VERSION, TEXTO_PLANTILLA
        )

    if not aprobacion.aprobada:
        if not registro.transicionar(
            CLAVE_PLANTILLA_RECORDATORIO,
            frozenset({"PENDIENTE_VALIDACION"} | ESTADOS_PARCIALES_APROBACION),
            "RECHAZADA",
        ):
            return _resultado_plantilla(
                log_path,
                correlation_id,
                "DUPLICADA",
                "idempotency_duplicate",
                aprobacion,
            )
        return _resultado_plantilla(
            log_path, correlation_id, "RECHAZADA", None, aprobacion
        )

    parcial_propia, parcial_ajena = _PARCIAL_POR_ROL[aprobacion.rol]
    if registro.transicionar(
        CLAVE_PLANTILLA_RECORDATORIO,
        frozenset({"PENDIENTE_VALIDACION"}),
        parcial_propia,
    ):
        estado_actual = parcial_propia
    elif registro.transicionar(
        CLAVE_PLANTILLA_RECORDATORIO,
        frozenset({parcial_ajena}),
        "APROBADA",
    ):
        estado_actual = "APROBADA"
    else:
        return _resultado_plantilla(
            log_path,
            correlation_id,
            "DUPLICADA",
            "idempotency_duplicate",
            aprobacion,
        )
    return _resultado_plantilla(
        log_path, correlation_id, estado_actual, None, aprobacion
    )


def _resultado_plantilla(
    log_path: Path,
    correlation_id: str,
    estado: str,
    error: str | None,
    aprobacion: AprobacionHumana,
) -> ResultadoPlantilla:
    _auditar(
        log_path,
        correlation_id=correlation_id,
        evento="decision_plantilla",
        estado=estado,
        resultado=error or "ok",
        aprobacion=aprobacion,
    )
    return ResultadoPlantilla(
        estado=estado,
        clave_plantilla=CLAVE_PLANTILLA_RECORDATORIO,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def encolar_lote_recordatorios(
    *,
    plan: PlanPago,
    lote: LoteRecordatorios,
    aprobacion_lote: AprobacionLote,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    directorio_salida: Path,
) -> ResultadoLote:
    """Encola los ítems del lote aprobado hacia la entrega simulada.

    Orden de los controles — primero lo que descalifica la autorización,
    después lo que toca el registro:

    1. La decisión del lote es una `AprobacionHumana` válida del rol
       utilitario y su lista tiene claves con formato `sha256`; si la
       decisión es de rechazo, el lote queda `RECHAZADA` y nada se encola.
    2. La plantilla está `APROBADA` — las dos decisiones registradas — en
       el mismo registro: un lote sin plantilla aprobada es
       `template_not_approved`.
    3. La lista aprobada cubre exactamente el lote planeado: una clave de
       más es `batch_item_unknown`, una de menos es
       `batch_approval_partial`. En ambos casos nada se encola.

    Recién ahí, por cada ítem: render desde la plantilla versionada,
    `crear` por clave (una segunda corrida del día choca acá como
    `DUPLICADA`), `PENDIENTE_VALIDACION` → `ENVIO_ENCOLADO` y `ItemEnvio`
    en la cola. La entrega no pasa por acá: la hace `drenar_envios` con su
    candado de destino fake, como cualquier envío de HU-012.
    """

    correlation_id = str(uuid.uuid4())
    log_path = _log_path(directorio_salida)
    aprobacion = aprobacion_lote.aprobacion
    items_aprobados = sorted(aprobacion_lote.items)

    def rechazo_lote(estado: str, error: str) -> ResultadoLote:
        _auditar(
            log_path,
            correlation_id=correlation_id,
            evento="autorizacion_lote",
            estado=estado,
            resultado=error,
            lote=lote,
            aprobacion=aprobacion,
            items_aprobados=items_aprobados,
        )
        return ResultadoLote(
            estado=estado,
            clave_lote=lote.clave_lote,
            log_path=log_path,
            correlation_id=correlation_id,
            items=(),
            error=error,
        )

    if (
        not _aprobacion_valida(aprobacion)
        or aprobacion.rol != ROL_APROBACION_UTILITARIA
        or any(
            not isinstance(clave, str)
            or CLAVE_REGISTRO_RE.fullmatch(clave) is None
            for clave in aprobacion_lote.items
        )
        or len(set(aprobacion_lote.items)) != len(aprobacion_lote.items)
    ):
        return rechazo_lote("INVALIDA", "approval_invalid")
    if not aprobacion.aprobada:
        return rechazo_lote("RECHAZADA", "batch_rejected")
    plantilla = registro.obtener(CLAVE_PLANTILLA_RECORDATORIO)
    if plantilla is None or plantilla.estado != "APROBADA":
        return rechazo_lote("INVALIDA", "template_not_approved")
    planeadas = {item.idempotency_key for item in lote.items}
    aprobadas = set(aprobacion_lote.items)
    if aprobadas - planeadas:
        return rechazo_lote("INVALIDA", "batch_item_unknown")
    if planeadas - aprobadas:
        return rechazo_lote("INVALIDA", "batch_approval_partial")

    _auditar(
        log_path,
        correlation_id=correlation_id,
        evento="autorizacion_lote",
        estado="AUTORIZADA",
        resultado="ok",
        lote=lote,
        aprobacion=aprobacion,
        items_aprobados=items_aprobados,
    )

    resultados: list[ResultadoItemLote] = []
    for item in lote.items:
        asunto, cuerpo = renderizar_recordatorio(plan=plan, item=item)
        if not registro.crear(item.idempotency_key, asunto, cuerpo):
            estado_item = "DUPLICADA"
            _auditar_item(
                log_path,
                correlation_id=correlation_id,
                lote=lote,
                item=item,
                estado=estado_item,
                resultado="idempotency_duplicate",
                asunto=asunto,
                cuerpo=cuerpo,
                aprobacion=aprobacion,
            )
        elif registro.transicionar(
            item.idempotency_key,
            frozenset({"PENDIENTE_VALIDACION"}),
            ESTADO_ENVIO_ENCOLADO,
        ):
            cola.encolar(
                ItemEnvio(
                    idempotency_key=item.idempotency_key,
                    destinatario=item.email_destinatario,
                    input_hash=_hash(
                        f"{lote.clave_lote}|{item.idempotency_key}"
                    ),
                )
            )
            estado_item = ESTADO_ENVIO_ENCOLADO
            _auditar_item(
                log_path,
                correlation_id=correlation_id,
                lote=lote,
                item=item,
                estado=estado_item,
                resultado="ok",
                asunto=asunto,
                cuerpo=cuerpo,
                aprobacion=aprobacion,
            )
        else:
            # La transición es la autorización: si no se toma, el ítem no
            # llega a la cola. Se prefiere un recordatorio no encolado —
            # visible para revisión humana — antes que uno encolado sin la
            # autorización del lote reflejada en el registro.
            estado_item = "ERROR"
            _auditar_item(
                log_path,
                correlation_id=correlation_id,
                lote=lote,
                item=item,
                estado=estado_item,
                resultado="enqueue_transition_failed",
                asunto=asunto,
                cuerpo=cuerpo,
                aprobacion=aprobacion,
            )
        resultados.append(
            ResultadoItemLote(
                idempotency_key=item.idempotency_key, estado=estado_item
            )
        )

    if not lote.items:
        estado_lote = "VACIO"
    elif all(item.estado == "DUPLICADA" for item in resultados):
        estado_lote = "DUPLICADA"
    else:
        estado_lote = ESTADO_ENVIO_ENCOLADO
    return ResultadoLote(
        estado=estado_lote,
        clave_lote=lote.clave_lote,
        log_path=log_path,
        correlation_id=correlation_id,
        items=tuple(resultados),
    )


def correr_lote_recordatorios(
    *,
    plan: PlanPago,
    lote: LoteRecordatorios,
    aprobacion_lote: AprobacionLote,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    destino: DestinoConfirmaciones,
    directorio_salida: Path,
) -> tuple[ResultadoLote, tuple[ResultadoEnvioEncolado, ...]]:
    """El circuito completo del día: encolar el lote aprobado y drenar.

    El drenaje es el mismo `drenar_envios` del circuito por envío — su
    candado exige el destino habilitado por tipo exacto, así que la entrega
    existe sólo contra el fake (o el Gmail con lista, según la política
    vigente de D12). La función no agrega controles: los viven el encolado
    y el worker.
    """

    resultado_lote = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote,
        registro=registro,
        cola=cola,
        directorio_salida=directorio_salida,
    )
    drenajes = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=directorio_salida,
    )
    return resultado_lote, drenajes


def renderizar_recordatorio(
    *, plan: PlanPago, item: ItemRecordatorio
) -> tuple[str, str]:
    """Asunto y cuerpo del ítem, desde la plantilla versionada. Sin modelo.

    La plantilla es la sección central del documento aprobado, con
    placeholders `{{...}}` que se reemplazan por los datos del ítem y del
    plan. Un placeholder sin valor es un error de programación, no un texto
    a medio renderizar: se rechaza en vez de entregar una llave suelta al
    destinatario. Los medios de pago salen del plan — con links o datos
    bancarios cuando el plan los declare — y llegan sólo acá, al cuerpo.
    """

    asunto_base = descripcion_tipo(TIPO_RECORDATORIO_PAGO)["plantilla"][
        "asunto_base"
    ]
    medios = ", ".join(plan.medios_pago).strip()
    valores = {
        "nombre_destinatario": item.nombre_destinatario.strip(),
        "actividad": plan.actividad.strip(),
        "nro_cuota": str(item.nro_cuota),
        "monto": str(item.monto),
        "fecha_referencia": item.fecha_referencia.isoformat(),
        "anticipacion": (
            "vence hoy"
            if item.anticipacion_d == 0
            else f"en {item.anticipacion_d} días"
        ),
        "medios_pago": medios or "A confirmar por la Secretaría de Extensión",
    }
    cuerpo = _seccion_cuerpo(TEXTO_PLANTILLA)
    for clave, valor in valores.items():
        cuerpo = cuerpo.replace("{{" + clave + "}}", valor)
    if _PLACEHOLDER_RE.search(cuerpo):
        raise ValueError("plantilla con placeholders sin renderizar")
    return f"[{MARCADOR_BORRADOR}] {asunto_base}", cuerpo


def _log_path(directorio_salida: Path) -> Path:
    return Path(directorio_salida) / "logs" / "recordatorios-hu012.jsonl"


def _auditar_item(
    log_path: Path,
    *,
    correlation_id: str,
    lote: LoteRecordatorios,
    item: ItemRecordatorio,
    estado: str,
    resultado: str,
    asunto: str,
    cuerpo: str,
    aprobacion: AprobacionHumana,
) -> None:
    """Constancia por ítem encolado: hashes, nunca texto ni correo.

    `bonificacion_no_verificable` es la marca de D14 en la evidencia: un
    flag, no un dato personal. `output_hash` cubre el cuerpo con los medios
    de pago ya renderizados, así que la línea prueba qué se encoló sin
    guardar links ni datos bancarios.
    """

    _auditar(
        log_path,
        correlation_id=correlation_id,
        evento="encolado_lote",
        estado=estado,
        resultado=resultado,
        lote=lote,
        aprobacion=aprobacion,
        item=item,
        extra={
            "idempotency_key": item.idempotency_key,
            "recipient_hash": _hash(item.email_destinatario),
            "output_hash": _hash(asunto + "\n" + cuerpo),
            "bonificacion_no_verificable": item.bonificacion_no_verificable,
        },
    )


def _auditar(
    log_path: Path,
    *,
    correlation_id: str,
    evento: str,
    estado: str,
    resultado: str,
    lote: LoteRecordatorios | None = None,
    aprobacion: AprobacionHumana | None = None,
    items_aprobados: list[str] | None = None,
    item: ItemRecordatorio | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    """La línea de auditoría del circuito por lote.

    Misma política que `confirmaciones._resultado`: lo que identifica a la
    comunicación (`idempotency_key`, `lote_clave`, la lista aprobada) viaja
    en claro porque ya son hashes, y lo que identifica a la persona o el
    texto (destinatario, cuerpo con medios de pago) viaja sólo como hash.
    """

    if item is not None:
        clave_registro: str | None = item.idempotency_key
    elif evento in ("plantilla", "decision_plantilla"):
        clave_registro = CLAVE_PLANTILLA_RECORDATORIO
    else:
        clave_registro = None
    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "evento": evento,
        "tipo_notificacion": TIPO_RECORDATORIO_PAGO,
        "estado": estado,
        "resultado": resultado,
        "idempotency_key": clave_registro,
        "lote_clave": lote.clave_lote if lote is not None else None,
        "items_count": len(lote.items) if lote is not None else None,
        "items_aprobados": items_aprobados,
        "template_key": CLAVE_PLANTILLA_RECORDATORIO,
        "input_hash": _hash(
            f"{lote.clave_lote}|{item.idempotency_key}"
        )
        if lote is not None and item is not None
        else None,
        "recipient_hash": None,
        "output_hash": None,
        "bonificacion_no_verificable": None,
        "human_decision_present": aprobacion is not None,
        "human_decision_hash": _hash(
            json.dumps(asdict(aprobacion), ensure_ascii=False, sort_keys=True)
        )
        if aprobacion is not None
        else None,
        "approval_role": aprobacion.rol if aprobacion is not None else None,
        # La entrega la audita el worker con su propia línea; acá el modo
        # sólo declara de qué circuito salió el ítem.
        "delivery_mode": "none",
        "origen_envio": "lote",
    }
    if extra:
        auditoria.update(extra)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as archivo:
        archivo.write(
            json.dumps(auditoria, ensure_ascii=False, sort_keys=True) + "\n"
        )


__all__ = [
    "AprobacionLote",
    "CLAVE_PLANTILLA_RECORDATORIO",
    "CONTRACT_VERSION",
    "HU",
    "POLICY_STATUS",
    "ResultadoItemLote",
    "ResultadoLote",
    "ResultadoPlantilla",
    "TEMPLATE_VERSION",
    "TEXTO_PLANTILLA",
    "aprobar_plantilla_recordatorio",
    "correr_lote_recordatorios",
    "encolar_lote_recordatorios",
    "registrar_plantilla_recordatorio",
    "renderizar_recordatorio",
]
