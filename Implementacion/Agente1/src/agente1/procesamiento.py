from __future__ import annotations

import csv
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


def procesar_fila_csv(
    *,
    csv_path: Path,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
) -> ResultadoProceso:
    _validar_id_solicitud(id_solicitud)
    fila = _buscar_fila(csv_path, id_solicitud)
    correlation_id = str(uuid.uuid4())
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

    borrador_path = _ruta_borrador_segura(directorio_salida, id_solicitud)
    borrador_path.parent.mkdir(parents=True, exist_ok=True)
    borrador = f"# BORRADOR — NO PUBLICAR\n\n{contenido}\n"
    borrador_path.write_text(borrador, encoding="utf-8")

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return ResultadoProceso(
        estado="PENDIENTE_VALIDACION",
        borrador_path=borrador_path,
        log_path=log_path,
        correlation_id=correlation_id,
    )


def _buscar_fila(csv_path: Path, id_solicitud: str) -> dict[str, str]:
    with csv_path.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila.get("id_solicitud") == id_solicitud:
                return {
                    clave: valor or ""
                    for clave, valor in fila.items()
                    if clave is not None
                }
    raise ValueError(f"No existe la solicitud {id_solicitud!r} en {csv_path}")


def _validar_id_solicitud(id_solicitud: str) -> None:
    if not ID_SOLICITUD_RE.fullmatch(id_solicitud):
        raise ValueError(
            "id_solicitud inválido: use entre 1 y 128 caracteres alfanuméricos, "
            "guion o guion bajo"
        )


def _ruta_borrador_segura(directorio_salida: Path, id_solicitud: str) -> Path:
    directorio_borradores = (directorio_salida / "borradores").resolve()
    candidato = (directorio_borradores / f"{id_solicitud}.md").resolve()
    if not candidato.is_relative_to(directorio_borradores):
        raise ValueError("id_solicitud inválido: la ruta resultante queda fuera de borradores")
    return candidato


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
