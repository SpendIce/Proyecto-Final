from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Protocol

from .destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
    ReferenciaBorrador,
)
from .fuentes import (
    COLUMNAS_GACETILLA,
    CsvFuenteSolicitudes,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)


HU = "HU-010"
PROMPT_VERSION = "gacetilla_v2"
CONTRACT_VERSION = "gacetilla_input_v1"
MAX_BORRADOR_CHARS = 5000
MAX_CUERPO_WORDS = 12
MAX_BAJADA_WORDS = 12
CONTRATO_ENTRADA = json.loads(
    files("agente1")
    .joinpath("contracts", "gacetilla_input_v1.schema.json")
    .read_text(encoding="utf-8")
)
CAMPOS_OBLIGATORIOS = tuple(CONTRATO_ENTRADA["required"])
ENCABEZADOS_OBLIGATORIOS = (
    "## TÍTULO",
    "## DATOS DE LA ACTIVIDAD",
    "## CONTACTO",
    "## BAJADA",
    "## CUERPO",
)
PATRON_BORRADOR = re.compile(
    r"\A## TÍTULO\n(?P<titulo>.+?)\n\n"
    r"## DATOS DE LA ACTIVIDAD\n(?P<datos>.+?)\n\n"
    r"## CONTACTO\n(?P<contacto>.+?)\n\n"
    r"## BAJADA\n(?P<bajada>.+?)\n\n"
    r"## CUERPO\n(?P<cuerpo>.+)\Z",
    flags=re.DOTALL,
)
PATRON_DATOS = re.compile(
    r"\AFecha: (?P<fecha>[^\n]+)\n"
    r"Organiza: (?P<organiza>[^\n]+)"
    r"(?:\nLugar: (?P<lugar>[^\n]+))?\Z"
)
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
SOURCE_ERROR_CODES = frozenset(
    {
        "sheets_headers_invalid",
        "sheets_row_invalid",
        "source_contract_invalid",
        "source_duplicate_id",
        "source_id_mismatch",
        "source_request_invalid",
        "source_request_not_found",
        "source_unavailable",
        "workspace_auth_denied",
        "workspace_auth_unavailable",
        "workspace_rate_limited",
        "workspace_response_invalid",
        "workspace_response_too_large",
        "workspace_source_not_found",
        "workspace_unavailable",
    }
)
DESTINATION_ERROR_CODES = frozenset(
    {
        "destination_contract_invalid",
        "destination_unavailable",
        "docs_auth_denied",
        "docs_rate_limited",
        "docs_response_invalid",
        "docs_response_too_large",
        "docs_unavailable",
        "docs_update_failed_orphaned",
        "workspace_auth_unavailable",
    }
)


class Generator(Protocol):
    modelo: str
    num_predict: int | None

    def generar(self, prompt: str) -> str: ...


class FakeGenerator:
    modelo = "fake-determinista"
    num_predict = None

    def __init__(self, respuesta: str) -> None:
        self._respuesta = respuesta

    def generar(self, prompt: str) -> str:
        return self._respuesta


@dataclass(frozen=True)
class ResultadoProceso:
    estado: str
    borrador_path: Path | None
    log_path: Path
    correlation_id: str
    error: str | None = None
    referencia_borrador: ReferenciaBorrador | None = None


def procesar_fila_csv(
    *,
    csv_path: Path,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
) -> ResultadoProceso:
    return procesar_solicitud(
        fuente=CsvFuenteSolicitudes(csv_path),
        id_solicitud=id_solicitud,
        directorio_salida=directorio_salida,
        generator=generator,
    )


def procesar_solicitud(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
) -> ResultadoProceso:
    correlation_id = str(uuid.uuid4())
    inicio_fuente = time.perf_counter()
    try:
        _validar_id_solicitud(id_solicitud)
    except (TypeError, ValueError):
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_request_invalid",
        )
    try:
        fila = fuente.obtener(id_solicitud)
    except FuenteSolicitudesError as error_fuente:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=error_fuente.code,
        )
    except Exception:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_unavailable",
        )
    fila, source_error_code = _normalizar_fila_fuente(fila, id_solicitud)
    if source_error_code is not None:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=source_error_code,
        )
    faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if not fila.get(campo, "").strip()]
    if faltantes:
        error = f"Campos obligatorios faltantes: {', '.join(faltantes)}"
        log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
        _registrar(
            log_path,
            {
                "correlation_id": correlation_id,
                "id_solicitud": id_solicitud,
                "HU": HU,
                "contract_version": CONTRACT_VERSION,
                "modelo": generator.modelo,
                "num_predict": _num_predict(generator),
                "prompt_version": PROMPT_VERSION,
                "latencia_s": 0.0,
                "estado": "INCOMPLETA",
                "resultado": "datos_incompletos",
                "error": error,
                "input_hash": _hash_json(fila),
                "output_hash": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return ResultadoProceso(
            estado="INCOMPLETA",
            borrador_path=None,
            log_path=log_path,
            correlation_id=correlation_id,
            error=error,
        )

    inicio = time.perf_counter()
    prompt = _construir_prompt(fila)
    try:
        contenido_generado = generator.generar(prompt)
    except Exception:
        latencia_s = round(time.perf_counter() - inicio, 6)
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="error_generacion",
            error="Falló la generación del borrador",
        )
    latencia_s = round(time.perf_counter() - inicio, 6)
    contenido = contenido_generado.strip() if isinstance(contenido_generado, str) else ""
    if not contenido:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_vacia",
            error="El generador devolvió contenido vacío",
        )
    validation_errors = _validar_salida(contenido, fila)
    if validation_errors:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_no_conforme",
            error="La salida generada no cumple el contrato mínimo",
            validation_errors=validation_errors,
        )

    borrador = f"{BORRADOR_MARKER}{contenido}\n"
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    try:
        referencia_borrador = destino_efectivo.guardar(id_solicitud, borrador)
        if not isinstance(referencia_borrador, ReferenciaBorrador):
            raise DestinoBorradoresError("destination_contract_invalid")
    except DestinoBorradoresError as error_destino:
        return _resultado_destino_fallido(
            fila=fila,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            borrador=borrador,
            destination_error_code=error_destino.code,
            reconciliation_ref_hash=error_destino.reconciliation_ref_hash,
        )
    except Exception:
        return _resultado_destino_fallido(
            fila=fila,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            borrador=borrador,
            destination_error_code="destination_unavailable",
            reconciliation_ref_hash=None,
        )

    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        {
            "correlation_id": correlation_id,
            "id_solicitud": id_solicitud,
            "HU": HU,
            "contract_version": CONTRACT_VERSION,
            "modelo": generator.modelo,
            "num_predict": _num_predict(generator),
            "prompt_version": PROMPT_VERSION,
            "latencia_s": latencia_s,
            "estado": "PENDIENTE_VALIDACION",
            "resultado": "borrador_generado",
            "error": None,
            "input_hash": _hash_json(fila),
            "output_hash": _hash_texto(borrador),
            "destination_type": referencia_borrador.tipo,
            "borrador_ref_hash": _hash_texto(referencia_borrador.referencia),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return ResultadoProceso(
        estado="PENDIENTE_VALIDACION",
        borrador_path=referencia_borrador.path,
        log_path=log_path,
        correlation_id=correlation_id,
        referencia_borrador=referencia_borrador,
    )


def _validar_id_solicitud(id_solicitud: str) -> None:
    if not isinstance(id_solicitud, str) or not ID_SOLICITUD_RE.fullmatch(id_solicitud):
        raise ValueError(
            "id_solicitud inválido: use entre 1 y 128 caracteres alfanuméricos, "
            "guion o guion bajo"
        )


def _resultado_fallido(
    *,
    fila: dict[str, str],
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    resultado: str,
    error: str,
    validation_errors: list[str] | None = None,
) -> ResultadoProceso:
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro: dict[str, object] = {
            "correlation_id": correlation_id,
            "id_solicitud": id_solicitud,
            "HU": HU,
            "contract_version": CONTRACT_VERSION,
            "modelo": generator.modelo,
            "num_predict": _num_predict(generator),
            "prompt_version": PROMPT_VERSION,
            "latencia_s": latencia_s,
            "estado": "FALLIDA",
            "resultado": resultado,
            "error": error,
            "input_hash": _hash_json(fila),
            "output_hash": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    if validation_errors is not None:
        registro["validation_errors"] = validation_errors
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_fuente_fallida(
    *,
    id_solicitud: object,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    source_error_code: str,
) -> ResultadoProceso:
    if source_error_code not in SOURCE_ERROR_CODES:
        source_error_code = "source_unavailable"
    invalida = source_error_code in {
        "source_request_invalid",
        "source_request_not_found",
    }
    estado = "INVALIDA" if invalida else "FALLIDA"
    resultado = "source_invalid" if invalida else "source_failure"
    error = (
        "Solicitud inválida o inexistente"
        if invalida
        else "Falló la lectura de la fuente"
    )
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        {
            "correlation_id": correlation_id,
            "id_solicitud": None,
            "id_solicitud_hash": (
                _hash_texto(id_solicitud) if isinstance(id_solicitud, str) else None
            ),
            "HU": HU,
            "contract_version": CONTRACT_VERSION,
            "modelo": generator.modelo,
            "num_predict": _num_predict(generator),
            "prompt_version": PROMPT_VERSION,
            "latencia_s": latencia_s,
            "estado": estado,
            "resultado": resultado,
            "error": error,
            "source_error_code": source_error_code,
            "input_hash": None,
            "output_hash": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return ResultadoProceso(
        estado=estado,
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_destino_fallido(
    *,
    fila: dict[str, str],
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    borrador: str,
    destination_error_code: str,
    reconciliation_ref_hash: str | None,
) -> ResultadoProceso:
    if destination_error_code not in DESTINATION_ERROR_CODES:
        destination_error_code = "destination_unavailable"
        reconciliation_ref_hash = None
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro: dict[str, object] = {
        "correlation_id": correlation_id,
        "id_solicitud": None,
        "id_solicitud_hash": _hash_texto(fila["id_solicitud"]),
        "HU": HU,
        "contract_version": CONTRACT_VERSION,
        "modelo": generator.modelo,
        "num_predict": _num_predict(generator),
        "prompt_version": PROMPT_VERSION,
        "latencia_s": latencia_s,
        "estado": "FALLIDA",
        "resultado": "destination_failure",
        "error": "Falló la persistencia del borrador",
        "destination_error_code": destination_error_code,
        "input_hash": _hash_json(fila),
        "output_hash": _hash_texto(borrador),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if reconciliation_ref_hash is not None:
        registro["reconciliation_ref_hash"] = reconciliation_ref_hash
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="Falló la persistencia del borrador",
    )


def _normalizar_fila_fuente(
    fila: object, id_solicitud: str
) -> tuple[dict[str, str], str | None]:
    if not isinstance(fila, dict) or any(
        campo not in fila for campo in CAMPOS_OBLIGATORIOS
    ):
        return {}, "source_contract_invalid"
    fila_canonica: dict[str, str] = {}
    for campo in COLUMNAS_GACETILLA:
        valor = fila.get(campo, "")
        if not isinstance(valor, str):
            return {}, "source_contract_invalid"
        fila_canonica[campo] = valor
    if fila_canonica["id_solicitud"] != id_solicitud:
        return {}, "source_id_mismatch"
    return fila_canonica, None


def _construir_prompt(fila: dict[str, str]) -> str:
    datos = "\n".join(f"{campo}: {valor}" for campo, valor in fila.items())
    plantilla = (
        files("agente1")
        .joinpath("prompts", "gacetilla_v2.txt")
        .read_text(encoding="utf-8")
    )
    return plantilla.replace("{datos_fuente}", datos)


def _registrar(path: Path, registro: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")


def _hash_json(valor: dict[str, str]) -> str:
    serializado = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_texto(serializado)


def _hash_texto(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _validar_salida(contenido: str, fila: dict[str, str]) -> list[str]:
    errores: list[str] = []
    if len(contenido) > MAX_BORRADOR_CHARS:
        errores.append("length_out_of_range")
        return errores
    if any(contenido.count(encabezado) != 1 for encabezado in ENCABEZADOS_OBLIGATORIOS):
        errores.append("document_structure")
        return errores
    match = PATRON_BORRADOR.fullmatch(contenido)
    if match is None:
        errores.append("document_structure")
        return errores

    titulo = _normalizar_texto(match.group("titulo").strip())
    contacto = _normalizar_texto(match.group("contacto").strip())
    bajada = match.group("bajada").strip()
    cuerpo = match.group("cuerpo").strip()
    if titulo != _normalizar_texto(fila["titulo"]):
        errores.append("title_mismatch")
    datos_match = PATRON_DATOS.fullmatch(match.group("datos").strip())
    if datos_match is None:
        errores.append("data_structure")
        return errores
    if _normalizar_texto(datos_match.group("fecha")) != _normalizar_texto(fila["fecha"]):
        errores.append("date_mismatch")
    if _normalizar_texto(datos_match.group("organiza")) != _normalizar_texto(
        fila["organiza"]
    ):
        errores.append("organizer_mismatch")
    lugar = fila.get("lugar", "").strip()
    lugar_generado = datos_match.group("lugar")
    if not lugar and lugar_generado is not None:
        errores.append("unexpected_place")
    elif lugar and lugar_generado is None:
        errores.append("place_missing")
    elif lugar and _normalizar_texto(lugar_generado or "") != _normalizar_texto(lugar):
        errores.append("place_mismatch")
    if contacto != _normalizar_texto(fila["contacto"]):
        errores.append("contact_mismatch")
    if len(bajada.split()) > MAX_BAJADA_WORDS:
        errores.append("bajada_too_long")
    if len(cuerpo.split()) > MAX_CUERPO_WORDS:
        errores.append("cuerpo_too_long")
    if re.fullmatch(r"[^.!?]+[.!?]", cuerpo, flags=re.DOTALL) is None:
        errores.append("cuerpo_sentence_invalid")
    return errores


def _num_predict(generator: Generator) -> int | None:
    return getattr(generator, "num_predict", None)


def _normalizar_texto(valor: str) -> str:
    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_acentos.casefold().split())
