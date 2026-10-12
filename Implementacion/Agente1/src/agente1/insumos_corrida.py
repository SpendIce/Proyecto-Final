"""Corrida de insumos de agentes sobre la pestaña «Insumos de agentes».

Implementa el punto de entrada push del ADR 0008: A3, A4 y A5 —o el productor
provisional declarado mientras esos agentes no existan— dejan una fila por
insumo en la pestaña `Insumos de agentes` de la planilla D2, y la corrida
manual la sondea. Por cada fila pendiente la corrida:

1. valida el envelope serializado contra `agente1.insumo.v1`
   (`insumos_agentes.validar_insumo_agente`, dato nunca instrucción);
2. despacha el insumo aceptado al flujo que le corresponde por
   `payload.type`, o lo acepta sin flujo si todavía no hay pipeline;
3. escribe el estado del insumo en la misma fila, dirigido al productor:
   `borrador generado` con el enlace al borrador, `rechazado` con el código
   del contrato o del flujo, o `aceptado sin flujo` con el tipo de payload.

La pieza nunca vuelve al productor: la fila sólo recibe el enlace. Todo lo
generado queda con la marca `BORRADOR — NO PUBLICAR` y pendiente de
validación humana.

Contrato tabular de la pestaña (una fila de encabezado, cuatro columnas):

| Columna | Encabezado    | Contenido |
|---------|---------------|-----------|
| A       | `insumo`      | Envelope `agente1.insumo.v1` serializado como JSON en una línea. |
| B       | `cargado_por` | Identificador opaco de quién cargó la fila (agente o productor provisional declarado). |
| C       | `estado`      | Lo escribe la corrida; vacío significa pendiente. Cualquier valor presente hace que la fila no se toque. |
| D       | `detalle`     | Lo escribe la corrida: enlace al borrador, código de rechazo o tipo de payload sin flujo. |

Decisiones que no se ven en el código:

- **El estado escrito es la barrera de reprocesamiento visible.** Una fila
  con `estado` no vacío se considera ya procesada y no se toca, aunque el
  valor no sea uno de los tres estados del contrato: la columna es la
  superficie de respuesta al productor y sobreescribirla podría borrar una
  anotación humana. Quien necesite reprocesar una fila la duplica con un
  `correlation_id` nuevo.
- **La idempotencia durable es local y por `correlation_id`.** Antes de
  despachar, la corrida consulta `insumos-procesados.jsonl` (append-only en
  el directorio de salida). Una corrida que se repite —o una segunda fila
  que declara el mismo `correlation_id`— no vuelve a despachar: reescribe el
  resultado ya registrado. El registro guarda metadatos (productor, tipo,
  hash del payload, `cargado_por`) y nunca el payload.
- **La reserva `inicio`/`final` cubre la ventana entre despachar y
  escribir.** Si la corrida muere después de despachar y antes de escribir el
  estado, el `correlation_id` queda registrado `inicio` sin `final`: la
  corrida siguiente lo reporta `bloqueada` en vez de volver a ejecutar el
  flujo, y la reconciliación es manual (revisar el registro y decidir si la
  fila se completa a mano). Lo mismo ocurre si el flujo levanta una excepción
  que no es `FlujoInsumoError`: el insumo queda en curso hasta que una
  persona mire qué pasó.
- **Los rechazos de fila no entran al registro.** `insumo_json_invalid`,
  `insumo_ausente`, `fila_insumo_invalid`, los códigos del envelope y los de
  `cargado_por` se derivan determinísticamente de la fila en cada corrida, así
  que una escritura fallida se reintenta sola en la corrida siguiente sin
  riesgo de doble despacho.
- **Despachar no es orquestar.** El mapa `despachos` es explícito y cerrado:
  hoy sólo `evento` tiene pipeline (`FlujoEventoGacetilla` → HU-010). Un tipo
  válido sin entrada en el mapa queda `aceptado sin flujo`, visible en la
  fila, y no se rechaza. Agregar un flujo es agregar una entrada al mapa en
  la CLI, nunca que el Agente 1 decida a qué agente llamar.
- **`evento` no tiene `id_actividad` propio.** El pipeline HU-010 identifica
  su solicitud por `id_actividad`; para un insumo se deriva uno opaco
  (`insumo-<productor>-<hash del correlation_id>`), así el log y el nombre
  del borrador quedan correlacionados con el insumo sin depender de campos
  inventados.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from .destinos import DestinoBorradores, MarkdownDestinoBorradores, ReferenciaBorrador
from .fuentes import (
    COLUMNAS_ACTIVIDADES_V2,
    FuenteSolicitudesError,
)
from .insumos_agentes import CONTRACT_VERSION, validar_insumo_agente
from .procesamiento import CAMPOS_OBLIGATORIOS, Generator, procesar_solicitud

# Encabezado posicional de la pestaña «Insumos de agentes» (ver docstring).
# Es tupla y no conjunto porque se compara celda a celda: las mismas columnas
# en otro orden se rechazan en vez de leerse mal.
COLUMNAS_INSUMOS_AGENTES_V1 = ("insumo", "cargado_por", "estado", "detalle")
COL_INSUMO = 0
COL_CARGADO_POR = 1
COL_ESTADO = 2
COL_DETALLE = 3

ESTADO_BORRADOR_GENERADO = "borrador generado"
ESTADO_RECHAZADO = "rechazado"
ESTADO_ACEPTADO_SIN_FLUJO = "aceptado sin flujo"
ESTADOS_FILA = frozenset(
    {ESTADO_BORRADOR_GENERADO, ESTADO_RECHAZADO, ESTADO_ACEPTADO_SIN_FLUJO}
)

REGISTRO_INSUMOS_NOMBRE = "insumos-procesados.jsonl"
_REGISTRO_VERSION = "insumos_procesados_v1"

# `cargado_por` es un identificador opaco, no un nombre libre: la celda termina
# en el registro y en el informe, y un texto libre podría llevar PII o romper
# la línea de una celda.
CARGADO_POR_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
MAX_DETALLE_CHARS = 500

# Campos que un `payload.content` de tipo `evento` puede declarar: las columnas
# de la planilla de actividades menos el identificador, que la corrida deriva.
CAMPOS_EVENTO = frozenset(COLUMNAS_ACTIVIDADES_V2) - {"id_actividad"}
# Los obligatorios de la gacetilla, menos `id_actividad` (lo deriva la corrida).
CAMPOS_EVENTO_OBLIGATORIOS = tuple(
    campo for campo in CAMPOS_OBLIGATORIOS if campo != "id_actividad"
)

_TIPOS_REFERENCIA_DOCS = frozenset({"google_docs", "google_drive_template"})


class CorridaInsumosError(RuntimeError):
    """Falla de la corrida entera, identificada por un código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EscrituraEstadoError(RuntimeError):
    """Falla al escribir el estado de una fila, con código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FlujoInsumoError(RuntimeError):
    """Rechazo definitivo dentro de un flujo de despacho, con código estable.

    El código se escribe en la columna `detalle` de la fila: es el vocabulario
    con que el productor corrige su insumo. Sólo se levanta para un desenlace
    seguro de explicar; una excepción inesperada del flujo deja el
    `correlation_id` en `inicio` y la fila bloqueada.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FlujoInsumo(Protocol):
    """Puerto de despacho: un pipeline acotado por tipo de payload.

    Devuelve el estado y el detalle a escribir en la fila (`borrador
    generado` + enlace, o `rechazado` + código), o levanta
    `FlujoInsumoError` con el código de rechazo. El `envelope` ya pasó la
    validación del contrato; el `payload.content` sigue siendo dato no
    confiable que el flujo valida a su manera, nunca una instrucción.
    """

    def ejecutar(
        self, *, envelope: dict[str, Any], cargado_por: str
    ) -> "ResultadoFlujo": ...


@dataclass(frozen=True)
class ResultadoFlujo:
    """Desenlace que el flujo pide escribir en la fila."""

    estado: str
    detalle: str


@dataclass(frozen=True)
class ResultadoFilaInsumo:
    """Qué pasó con una fila de la pestaña en esta corrida.

    `desenlace` es cerrado: `escrita` (la fila quedó con su estado),
    `omitida_vacia`, `omitida_procesada` (ya tenía estado), `bloqueada` (el
    `correlation_id` quedó a medias en una corrida anterior o el flujo falló
    sin código) y `escritura_fallida` (el resultado existe pero no pudo
    escribirse; la próxima corrida lo reintenta).
    """

    fila: int
    desenlace: str
    estado_fila: str | None = None
    detalle: str | None = None
    codigo: str | None = None
    producer: str | None = None
    correlation_id: str | None = None
    payload_type: str | None = None
    data_origin: str | None = None
    cargado_por: str | None = None
    via_registro: bool = False


@dataclass(frozen=True)
class InformeCorridaInsumos:
    """Resumen de la corrida: conteos cerrados más el detalle por fila."""

    estado: str
    contract_version: str
    filas_leidas: int
    filas_nuevas: int
    filas_escritas: int
    filas_omitidas: int
    filas_bloqueadas: int
    filas_fallidas: int
    filas: tuple[ResultadoFilaInsumo, ...]


class RegistroInsumosArchivo:
    """Idempotencia durable: un JSONL append-only por directorio de salida.

    Cada línea es un evento `inicio` o `final` de un `correlation_id`, con
    metadatos del envelope y nunca el payload. `consultar` relee el archivo
    entero: el volumen (una línea por despacho) no justifica un índice, y
    releer es lo que hace durable a la reserva ante una corrida interrumpida.
    Una línea malformada invalida el registro completo
    (`insumos_registro_invalid`): preferir no procesar a procesar dos veces.
    """

    def __init__(self, directorio: Path) -> None:
        self._path = Path(directorio) / REGISTRO_INSUMOS_NOMBRE

    def consultar(self, correlation_id: str) -> dict[str, Any] | None:
        """Último estado conocido del `correlation_id`, o `None`.

        Devuelve `{"fase": "inicio"}` cuando quedó una reserva sin cerrar y
        `{"fase": "final", "estado_fila": ..., "detalle": ...}` cuando el
        insumo ya tiene desenlace registrado.
        """

        estado: dict[str, Any] | None = None
        for linea in _leer_jsonl(self._path):
            if linea["correlation_id"] != correlation_id:
                continue
            estado = linea
        if estado is None:
            return None
        if estado["fase"] == "final":
            return {
                "fase": "final",
                "estado_fila": estado["estado_fila"],
                "detalle": estado["detalle"],
            }
        return {"fase": "inicio"}

    def registrar_inicio(
        self, correlation_id: str, *, meta: Mapping[str, str]
    ) -> None:
        self._append(
            correlation_id,
            fase="inicio",
            estado_fila=None,
            detalle=None,
            meta=meta,
        )

    def registrar_final(
        self,
        correlation_id: str,
        *,
        estado_fila: str,
        detalle: str,
        meta: Mapping[str, str],
    ) -> None:
        self._append(
            correlation_id,
            fase="final",
            estado_fila=estado_fila,
            detalle=detalle,
            meta=meta,
        )

    def _append(
        self,
        correlation_id: str,
        *,
        fase: str,
        estado_fila: str | None,
        detalle: str | None,
        meta: Mapping[str, str],
    ) -> None:
        entrada = {
            "record": _REGISTRO_VERSION,
            "fase": fase,
            "correlation_id": correlation_id,
            "producer": meta["producer"],
            "payload_type": meta["payload_type"],
            "payload_hash": meta["payload_hash"],
            "data_origin": meta["data_origin"],
            "cargado_por": meta["cargado_por"],
            "estado_fila": estado_fila,
            "detalle": detalle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
            archivo.write("\n")


class RegistroInsumosMemoria:
    """Registro en memoria para pruebas: mismo contrato, sin disco."""

    def __init__(self) -> None:
        self._entradas: dict[str, dict[str, Any]] = {}
        self.inicios: list[str] = []
        self.finales: list[str] = []

    def consultar(self, correlation_id: str) -> dict[str, Any] | None:
        return self._entradas.get(correlation_id)

    def registrar_inicio(
        self, correlation_id: str, *, meta: Mapping[str, str]
    ) -> None:
        self._entradas[correlation_id] = {"fase": "inicio"}
        self.inicios.append(correlation_id)

    def registrar_final(
        self,
        correlation_id: str,
        *,
        estado_fila: str,
        detalle: str,
        meta: Mapping[str, str],
    ) -> None:
        self._entradas[correlation_id] = {
            "fase": "final",
            "estado_fila": estado_fila,
            "detalle": detalle,
        }
        self.finales.append(correlation_id)


def correr_insumos(
    *,
    lector: Any,
    escritor: Any,
    registro: Any,
    despachos: Mapping[str, FlujoInsumo],
) -> InformeCorridaInsumos:
    """Sondea la pestaña y procesa cada fila pendiente.

    `lector` es cualquier objeto con `leer_valores()` (el
    `GoogleSheetsLectorValores` de la planilla D2 o el `LectorValoresCsv`
    offline). `escritor` implementa `escribir_estado(numero_fila=...,
    estado=..., detalle=...)` (el adapter `values.update` acotado o el
    escritor CSV). La corrida nunca levanta por una fila: cada desenlace
    queda asentado en el informe. Las fallas de tabla completa —lector,
    encabezado, registro corrupto— sí levantan `CorridaInsumosError`, porque
    procesar a medias una fuente rota es peor que no procesar.
    """

    try:
        values = lector.leer_valores()
    except FuenteSolicitudesError as exc:
        raise CorridaInsumosError(exc.code) from None
    if (
        not isinstance(values, list)
        or not values
        or not isinstance(values[0], list)
        or [_limpiar_celda(c) for c in values[0][: len(COLUMNAS_INSUMOS_AGENTES_V1)]]
        != list(COLUMNAS_INSUMOS_AGENTES_V1)
    ):
        raise CorridaInsumosError("insumos_encabezado_invalid")

    resultados: list[ResultadoFilaInsumo] = []
    for numero_fila, fila_raw in enumerate(values[1:], start=2):
        resultados.append(
            _procesar_fila(
                numero_fila=numero_fila,
                fila_raw=fila_raw,
                escritor=escritor,
                registro=registro,
                despachos=despachos,
            )
        )

    return InformeCorridaInsumos(
        estado="OK",
        contract_version=CONTRACT_VERSION,
        filas_leidas=len(resultados),
        filas_nuevas=sum(
            1 for r in resultados if r.desenlace not in {"omitida_vacia", "omitida_procesada"}
        ),
        filas_escritas=sum(1 for r in resultados if r.desenlace == "escrita"),
        filas_omitidas=sum(
            1 for r in resultados if r.desenlace in {"omitida_vacia", "omitida_procesada"}
        ),
        filas_bloqueadas=sum(1 for r in resultados if r.desenlace == "bloqueada"),
        filas_fallidas=sum(1 for r in resultados if r.desenlace == "escritura_fallida"),
        filas=tuple(resultados),
    )


def _procesar_fila(
    *,
    numero_fila: int,
    fila_raw: object,
    escritor: Any,
    registro: Any,
    despachos: Mapping[str, FlujoInsumo],
) -> ResultadoFilaInsumo:
    """El ciclo de una fila: leer, validar, despachar o rechazar, escribir."""

    if not isinstance(fila_raw, list):
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle="fila_insumo_invalid",
            codigo="fila_insumo_invalid",
        )
    celdas = [_limpiar_celda(c) for c in fila_raw[: len(COLUMNAS_INSUMOS_AGENTES_V1)]]
    while len(celdas) < len(COLUMNAS_INSUMOS_AGENTES_V1):
        celdas.append("")
    insumo_texto, cargado_por, estado_celda = (
        celdas[COL_INSUMO],
        celdas[COL_CARGADO_POR],
        celdas[COL_ESTADO],
    )
    if all(not celda for celda in celdas):
        return ResultadoFilaInsumo(fila=numero_fila, desenlace="omitida_vacia")
    if estado_celda:
        return ResultadoFilaInsumo(fila=numero_fila, desenlace="omitida_procesada")

    if not insumo_texto:
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle="insumo_ausente",
            codigo="insumo_ausente",
            cargado_por=cargado_por or None,
        )
    try:
        raw: object = json.loads(insumo_texto)
    except json.JSONDecodeError:
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle="insumo_json_invalid",
            codigo="insumo_json_invalid",
            cargado_por=cargado_por or None,
        )

    validacion = validar_insumo_agente(raw)
    if not validacion.aceptado or validacion.envelope is None:
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle=validacion.codigo,
            codigo=validacion.codigo,
            producer=validacion.producer,
            cargado_por=cargado_por or None,
        )
    if not cargado_por:
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle="cargado_por_ausente",
            codigo="cargado_por_ausente",
            producer=validacion.producer,
            correlation_id=_correlation_id(validacion.envelope),
            payload_type=_payload_type(validacion.envelope),
            data_origin=_data_origin(validacion.envelope),
        )
    if CARGADO_POR_RE.fullmatch(cargado_por) is None:
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=ESTADO_RECHAZADO,
            detalle="cargado_por_invalid",
            codigo="cargado_por_invalid",
            producer=validacion.producer,
            correlation_id=_correlation_id(validacion.envelope),
            payload_type=_payload_type(validacion.envelope),
            data_origin=_data_origin(validacion.envelope),
        )

    return _despachar(
        numero_fila=numero_fila,
        envelope=validacion.envelope,
        cargado_por=cargado_por,
        escritor=escritor,
        registro=registro,
        despachos=despachos,
    )


def _despachar(
    *,
    numero_fila: int,
    envelope: dict[str, Any],
    cargado_por: str,
    escritor: Any,
    registro: Any,
    despachos: Mapping[str, FlujoInsumo],
) -> ResultadoFilaInsumo:
    """Idempotencia + despacho de un envelope aceptado."""

    producer = envelope["producer"]
    payload_type = envelope["payload"]["type"]
    correlation_id = envelope["correlation_id"]
    contexto = {
        "producer": producer,
        "correlation_id": correlation_id,
        "payload_type": payload_type,
        "data_origin": envelope["data_origin"],
        "cargado_por": cargado_por,
    }
    meta_registro = {
        "producer": producer,
        "payload_type": payload_type,
        "payload_hash": hashlib.sha256(
            json.dumps(
                envelope["payload"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "data_origin": envelope["data_origin"],
        "cargado_por": cargado_por,
    }

    previo = registro.consultar(correlation_id)
    if previo is not None and previo.get("fase") == "final":
        # Mismo correlation_id ya despachado (corrida repetida o fila
        # duplicada): se repite el resultado, no el trabajo.
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=previo["estado_fila"],
            detalle=previo["detalle"],
            via_registro=True,
            **contexto,
        )
    if previo is not None:
        return ResultadoFilaInsumo(
            fila=numero_fila,
            desenlace="bloqueada",
            codigo="insumo_en_progreso",
            **contexto,
        )

    flujo = despachos.get(payload_type)
    if flujo is None:
        estado_fila, detalle = ESTADO_ACEPTADO_SIN_FLUJO, payload_type
        registro.registrar_final(
            correlation_id,
            estado_fila=estado_fila,
            detalle=detalle,
            meta=meta_registro,
        )
        return _escribir_veredicto(
            numero_fila=numero_fila,
            escritor=escritor,
            estado=estado_fila,
            detalle=detalle,
            **contexto,
        )

    registro.registrar_inicio(correlation_id, meta=meta_registro)
    try:
        resultado_flujo = flujo.ejecutar(envelope=envelope, cargado_por=cargado_por)
    except FlujoInsumoError as exc:
        estado_fila, detalle = ESTADO_RECHAZADO, exc.code
    except Exception:
        # Falla sin vocabulario: el insumo queda reservado `inicio` y la fila
        # se reporta bloqueada en vez de reintentar un efecto desconocido.
        return ResultadoFilaInsumo(
            fila=numero_fila,
            desenlace="bloqueada",
            codigo="insumo_en_progreso",
            **contexto,
        )
    else:
        if not _resultado_flujo_valido(resultado_flujo):
            return ResultadoFilaInsumo(
                fila=numero_fila,
                desenlace="bloqueada",
                codigo="insumo_en_progreso",
                **contexto,
            )
        estado_fila, detalle = resultado_flujo.estado, resultado_flujo.detalle

    registro.registrar_final(
        correlation_id,
        estado_fila=estado_fila,
        detalle=detalle,
        meta=meta_registro,
    )
    return _escribir_veredicto(
        numero_fila=numero_fila,
        escritor=escritor,
        estado=estado_fila,
        detalle=detalle,
        **contexto,
    )


def _escribir_veredicto(
    *,
    numero_fila: int,
    escritor: Any,
    estado: str,
    detalle: str,
    via_registro: bool = False,
    codigo: str | None = None,
    producer: str | None = None,
    correlation_id: str | None = None,
    payload_type: str | None = None,
    data_origin: str | None = None,
    cargado_por: str | None = None,
) -> ResultadoFilaInsumo:
    """Escribe estado+detalle en la fila y arma el resultado del informe."""

    try:
        escritor.escribir_estado(
            numero_fila=numero_fila, estado=estado, detalle=detalle
        )
    except EscrituraEstadoError as exc:
        return ResultadoFilaInsumo(
            fila=numero_fila,
            desenlace="escritura_fallida",
            estado_fila=estado,
            detalle=detalle,
            codigo=codigo or exc.code,
            producer=producer,
            correlation_id=correlation_id,
            payload_type=payload_type,
            data_origin=data_origin,
            cargado_por=cargado_por,
            via_registro=via_registro,
        )
    return ResultadoFilaInsumo(
        fila=numero_fila,
        desenlace="escrita",
        estado_fila=estado,
        detalle=detalle,
        codigo=codigo,
        producer=producer,
        correlation_id=correlation_id,
        payload_type=payload_type,
        data_origin=data_origin,
        cargado_por=cargado_por,
        via_registro=via_registro,
    )


def _resultado_flujo_valido(resultado: object) -> bool:
    """Un flujo sólo puede pedir `borrador generado` o `rechazado`.

    `aceptado sin flujo` lo decide la corrida, no el flujo. El detalle es una
    sola línea acotada porque se escribe tal cual en la celda.
    """

    return (
        isinstance(resultado, ResultadoFlujo)
        and resultado.estado in {ESTADO_BORRADOR_GENERADO, ESTADO_RECHAZADO}
        and isinstance(resultado.detalle, str)
        and 0 < len(resultado.detalle) <= MAX_DETALLE_CHARS
        and "\r" not in resultado.detalle
        and "\n" not in resultado.detalle
    )


def _limpiar_celda(valor: object) -> str:
    """Una celda es texto plano o nada: sin saltos ni tabulaciones."""

    if not isinstance(valor, str):
        return ""
    return re.sub(r"[\r\n\t]+", " ", valor).strip()


def _correlation_id(envelope: dict[str, Any]) -> str:
    return envelope["correlation_id"]


def _payload_type(envelope: dict[str, Any]) -> str:
    return envelope["payload"]["type"]


def _data_origin(envelope: dict[str, Any]) -> str:
    return envelope["data_origin"]


def _leer_jsonl(path: Path) -> list[dict[str, Any]]:
    """Relee el registro entero; cualquier línea inválida lo invalida todo."""

    if not path.exists():
        return []
    entradas: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8", newline="") as archivo:
            for linea in archivo:
                texto = linea.strip()
                if not texto:
                    continue
                entradas.append(_entrada_registro(json.loads(texto)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise CorridaInsumosError("insumos_registro_invalid") from None
    return entradas


def _entrada_registro(valor: object) -> dict[str, Any]:
    if (
        not isinstance(valor, dict)
        or valor.get("record") != _REGISTRO_VERSION
        or valor.get("fase") not in {"inicio", "final"}
        or not isinstance(valor.get("correlation_id"), str)
        or not valor["correlation_id"]
    ):
        raise ValueError("entrada de registro inválida")
    if valor["fase"] == "final" and (
        valor.get("estado_fila") not in ESTADOS_FILA
        or not isinstance(valor.get("detalle"), str)
    ):
        raise ValueError("entrada de registro inválida")
    return valor


# --- Flujo A3 `evento` → gacetilla HU-010 -----------------------------------


class _FuenteEventoInsumo:
    """Fuente de una sola fila: la actividad que trae el `payload.content`.

    Implementa el puerto `FuenteSolicitudes` sobre el contenido del insumo ya
    mapeado a `COLUMNAS_ACTIVIDADES_V2`, así el pipeline HU-010 se ejercita
    completo —validación de campos, prompt, contrato de salida, marca de
    borrador, destino y log— sin un camino paralelo que lo esquive.
    """

    def __init__(self, id_solicitud: str, fila: dict[str, str]) -> None:
        self._id_solicitud = id_solicitud
        self._fila = fila

    def obtener(self, id_actividad: str) -> dict[str, str]:
        if id_actividad != self._id_solicitud:
            raise FuenteSolicitudesError("source_request_not_found")
        return dict(self._fila)

    def enumerar(self) -> list[dict[str, str]]:
        return [dict(self._fila)]


class FlujoEventoGacetilla:
    """Despacha un insumo A3 `evento` al pipeline de gacetilla HU-010.

    El `payload.content` se trata como la fila de una actividad: debe usar
    nombres de `COLUMNAS_ACTIVIDADES_V2` (sin `id_actividad`, que la corrida
    deriva del `correlation_id`) con valores texto, y traer los campos que el
    contrato de gacetilla declara obligatorios. Lo que sobra o falta es un
    rechazo explicable para el productor, no una corrección silenciosa.

    El resultado es siempre un borrador `PENDIENTE_VALIDACION` —nunca una
    publicación— y el detalle que vuelve a la fila es el enlace al borrador.
    """

    def __init__(
        self,
        *,
        generator: Generator,
        directorio_salida: Path,
        destino: DestinoBorradores | None = None,
    ) -> None:
        self._generator = generator
        self._directorio_salida = Path(directorio_salida)
        self._destino = destino or MarkdownDestinoBorradores(
            self._directorio_salida
        )

    def ejecutar(
        self, *, envelope: dict[str, Any], cargado_por: str
    ) -> ResultadoFlujo:
        content = envelope["payload"]["content"]
        if any(campo not in CAMPOS_EVENTO for campo in content):
            raise FlujoInsumoError("evento_campos_desconocidos")
        fila = {columna: "" for columna in COLUMNAS_ACTIVIDADES_V2}
        for campo, valor in content.items():
            if not isinstance(valor, str):
                raise FlujoInsumoError("evento_valor_invalido")
            fila[campo] = valor.strip()
        if any(not fila[campo] for campo in CAMPOS_EVENTO_OBLIGATORIOS):
            raise FlujoInsumoError("evento_campos_faltantes")

        id_solicitud = _id_solicitud_insumo(envelope)
        fila["id_actividad"] = id_solicitud
        resultado = procesar_solicitud(
            fuente=_FuenteEventoInsumo(id_solicitud, fila),
            id_solicitud=id_solicitud,
            directorio_salida=self._directorio_salida,
            generator=self._generator,
            destino=self._destino,
        )
        if resultado.estado == "PENDIENTE_VALIDACION":
            if resultado.referencia_borrador is None:
                raise FlujoInsumoError("evento_enlace_no_disponible")
            return ResultadoFlujo(
                estado=ESTADO_BORRADOR_GENERADO,
                detalle=_enlace_borrador(resultado.referencia_borrador),
            )
        if resultado.estado == "INCOMPLETA":
            raise FlujoInsumoError("evento_datos_incompletos")
        if resultado.estado == "INVALIDA":
            raise FlujoInsumoError("evento_actividad_invalid")
        raise FlujoInsumoError("evento_generacion_fallida")


def _id_solicitud_insumo(envelope: dict[str, Any]) -> str:
    """Identificador derivado y opaco para el pipeline: `insumo-aN-<hash>`."""

    digest = hashlib.sha256(
        str(envelope["correlation_id"]).encode("utf-8")
    ).hexdigest()[:12]
    return f"insumo-{str(envelope['producer']).lower()}-{digest}"


def _enlace_borrador(referencia: ReferenciaBorrador) -> str:
    """Lo que ve el productor: URL de Docs para destinos remotos, path local
    para el destino Markdown offline. Nunca el contenido de la pieza."""

    if referencia.tipo in _TIPOS_REFERENCIA_DOCS:
        return f"https://docs.google.com/document/d/{referencia.referencia}/edit"
    return referencia.referencia
