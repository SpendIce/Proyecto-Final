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

from .destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
    ReferenciaBorrador,
)
from .fuentes import COLUMNAS_GACETILLA, FuenteSolicitudes, FuenteSolicitudesError
from .procesamiento import Generator, ResultadoProceso


HU = "HU-011"
CONTRACT_VERSION = "post_input_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
CANALES = frozenset({"instagram", "linkedin"})
CAMPOS_SEMANTICOS_AUTORIZADOS = (
    "titulo",
    "descripcion",
    "fecha",
    "publico",
    "organiza",
    "contacto",
    "lugar",
)
CONTRATO_ENTRADA = json.loads(
    files("agente1").joinpath("contracts", "post_input_v1.schema.json").read_text(
        encoding="utf-8"
    )
)
CAMPOS_OBLIGATORIOS = tuple(CONTRATO_ENTRADA["required"])
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
PATRON_SALIDA = re.compile(
    r"\ACANAL: (?P<canal>instagram|linkedin)\n"
    r"TEXTO:\n(?P<texto>[^\r\n](?:.*?[^\s])?)\n"
    r"HASHTAGS:(?:\n(?P<hashtags>[^\r\n]+))?\Z",
    flags=re.DOTALL,
)
PATRON_HASHTAG = re.compile(r"#(?!\d)[^\W_][\w]*\Z", flags=re.UNICODE)
PATRON_FECHA = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")
PATRON_NUMERO = re.compile(r"\b\d+(?:[.,]\d+)?\b")
PATRON_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@.,;:!?]+\b", flags=re.UNICODE)
PATRON_URL = re.compile(r"\bhttps?://[^\s]+", flags=re.IGNORECASE)
PATRON_IMPORTE = re.compile(
    r"(?:[$€]|\b(?:usd|ars)\b)\s*\d+(?:[.,]\d+)?|"
    r"\b\d+(?:[.,]\d+)?\s*(?:pesos?|d[oó]lares?|usd|ars)\b",
    flags=re.IGNORECASE,
)
PATRON_LUGAR_ETIQUETADO = re.compile(
    r"\b(?:lugar|sede|ubicaci[oó]n)\s*:\s*([^\s.,;][^.,;\n]*)",
    flags=re.IGNORECASE,
)
PATRON_LUGAR_PROPIO = re.compile(
    r"\b(?:en|desde)\s+(?:(?:el|la|los|las)\s+)?"
    r"([A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ-]*)",
)
PATRON_ACCION_NO_AUTORIZADA = re.compile(
    r"\b(?:aprobad[oa]s?|publicad[oa]s?|enviad[oa]s?|confirmad[oa]s?|"
    r"oficializad[oa]s?|oficializ[oó])\b",
    flags=re.IGNORECASE,
)
SOURCE_ERROR_CODES = frozenset(
    {
        "source_contract_invalid",
        "source_duplicate_id",
        "source_id_mismatch",
        "source_request_invalid",
        "source_request_not_found",
        "source_unavailable",
        "sheets_headers_invalid",
        "sheets_row_invalid",
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
        "drive_auth_denied",
        "drive_rate_limited",
        "drive_request_too_large",
        "drive_resource_not_found",
        "drive_response_invalid",
        "drive_response_too_large",
        "drive_unavailable",
        "workspace_auth_unavailable",
    }
)


@dataclass(frozen=True)
class PoliticaPost:
    version: str
    status: str
    max_chars: int
    min_hashtags: int
    max_hashtags: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.version, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.version)
            or self.status != POLICY_STATUS
            or isinstance(self.max_chars, bool)
            or not isinstance(self.max_chars, int)
            or not 1 <= self.max_chars <= 10000
            or isinstance(self.min_hashtags, bool)
            or not isinstance(self.min_hashtags, int)
            or not 0 <= self.min_hashtags <= 100
            or isinstance(self.max_hashtags, bool)
            or not isinstance(self.max_hashtags, int)
            or not 1 <= self.max_hashtags <= 100
            or self.min_hashtags > self.max_hashtags
        ):
            raise ValueError("política de post inválida")


POLITICAS_DEFAULT = {
    "instagram": PoliticaPost(
        version="post_instagram_policy_provisional_v1",
        status=POLICY_STATUS,
        max_chars=1000,
        min_hashtags=1,
        max_hashtags=10,
    ),
    "linkedin": PoliticaPost(
        version="post_linkedin_policy_provisional_v1",
        status=POLICY_STATUS,
        max_chars=1000,
        min_hashtags=1,
        max_hashtags=10,
    ),
}
POLITICA_DEFAULT = POLITICAS_DEFAULT["instagram"]


def procesar_post(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost | None = None,
    destino: DestinoBorradores | None = None,
) -> ResultadoProceso:
    correlation_id = str(uuid.uuid4())
    inicio = time.perf_counter()
    politica_auditoria = politica or POLITICA_DEFAULT
    if not isinstance(id_solicitud, str) or ID_SOLICITUD_RE.fullmatch(id_solicitud) is None:
        return _fallo_fuente(
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_auditoria,
            correlation_id=correlation_id,
            inicio=inicio,
            code="source_request_invalid",
        )
    if canal not in CANALES:
        return _fallo(
            fila=None,
            id_solicitud=id_solicitud,
            canal=None,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_auditoria,
            correlation_id=correlation_id,
            inicio=inicio,
            estado="INVALIDA",
            resultado="channel_invalid",
            error="Canal inválido",
            validation_errors=["channel_not_allowed"],
        )
    politica_efectiva = politica or POLITICAS_DEFAULT[canal]
    try:
        fila_cruda = fuente.obtener(id_solicitud)
    except FuenteSolicitudesError as exc:
        return _fallo_fuente(
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            code=exc.code,
        )
    except Exception:
        return _fallo_fuente(
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            code="source_unavailable",
        )
    fila, source_code = _normalizar_fila(fila_cruda, id_solicitud)
    if source_code:
        return _fallo_fuente(
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            code=source_code,
        )
    faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if not fila[campo].strip()]
    if faltantes:
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            estado="INCOMPLETA",
            resultado="datos_incompletos",
            error="Datos obligatorios incompletos",
            validation_errors=["required_fields_missing"],
        )
    prompt = _construir_prompt(fila, canal, politica_efectiva)
    inicio_generacion = time.perf_counter()
    try:
        salida_cruda = generator.generar(prompt)
    except Exception:
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            estado="FALLIDA",
            resultado="error_generacion",
            error="Falló la generación del borrador",
        )
    contenido = unicodedata.normalize("NFC", salida_cruda.strip()) if isinstance(salida_cruda, str) else ""
    errores = _validar_salida(contenido, fila, canal, politica_efectiva)
    if errores:
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            estado="FALLIDA",
            resultado="salida_no_conforme" if contenido else "salida_vacia",
            error="La salida generada no cumple el contrato mínimo",
            validation_errors=errores,
        )
    borrador = f"{BORRADOR_MARKER}{contenido}\n"
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    id_borrador = f"{id_solicitud}-{canal}"
    try:
        referencia = destino_efectivo.guardar(id_borrador, borrador)
        if not isinstance(referencia, ReferenciaBorrador):
            raise DestinoBorradoresError("destination_contract_invalid")
    except DestinoBorradoresError as exc:
        return _fallo_destino(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            borrador=borrador,
            code=exc.code,
            reconciliation_ref_hash=exc.reconciliation_ref_hash,
        )
    except Exception:
        return _fallo_destino(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            borrador=borrador,
            code="destination_unavailable",
            reconciliation_ref_hash=None,
        )
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        _registro_base(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_generacion, 6),
        )
        | {
            "estado": "PENDIENTE_VALIDACION",
            "resultado": "borrador_generado",
            "error": None,
            "output_hash": _hash_texto(borrador),
            "destination_type": referencia.tipo,
            "borrador_ref_hash": _hash_texto(referencia.referencia),
        },
    )
    return ResultadoProceso(
        estado="PENDIENTE_VALIDACION",
        borrador_path=referencia.path,
        log_path=log_path,
        correlation_id=correlation_id,
        referencia_borrador=referencia,
    )


def _normalizar_fila(fila: object, id_solicitud: str) -> tuple[dict[str, str], str | None]:
    if not isinstance(fila, dict) or any(campo not in fila for campo in CAMPOS_OBLIGATORIOS):
        return {}, "source_contract_invalid"
    canonica: dict[str, str] = {}
    for campo in COLUMNAS_GACETILLA:
        valor = fila.get(campo, "")
        if not isinstance(valor, str):
            return {}, "source_contract_invalid"
        canonica[campo] = unicodedata.normalize("NFC", valor)
    if canonica["id_solicitud"] != id_solicitud:
        return {}, "source_id_mismatch"
    return canonica, None


def _construir_prompt(fila: dict[str, str], canal: str, politica: PoliticaPost) -> str:
    plantilla = files("agente1").joinpath("prompts", f"post_{canal}_v1.txt").read_text(
        encoding="utf-8"
    )
    datos = json.dumps(fila, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        plantilla.replace("{max_chars}", str(politica.max_chars))
        .replace("{min_hashtags}", str(politica.min_hashtags))
        .replace("{max_hashtags}", str(politica.max_hashtags))
        .replace("{datos_fuente}", datos)
    )


def _validar_salida(
    contenido: str,
    fila: dict[str, str],
    canal: str,
    politica: PoliticaPost,
) -> list[str]:
    if not contenido:
        return ["output_empty"]
    if contenido.count("CANAL:") != 1 or contenido.count("TEXTO:") != 1 or contenido.count("HASHTAGS:") != 1:
        return ["document_structure"]
    match = PATRON_SALIDA.fullmatch(contenido)
    if match is None:
        return ["document_structure"]
    errores: list[str] = []
    if match.group("canal") != canal:
        errores.append("channel_mismatch")
    texto = match.group("texto")
    hashtags_texto = match.group("hashtags") or ""
    hashtags = hashtags_texto.split()
    if len(texto) + len(hashtags_texto) > politica.max_chars:
        errores.append("length_out_of_range")
    if not politica.min_hashtags <= len(hashtags) <= politica.max_hashtags:
        errores.append("hashtag_count_out_of_range")
    if any(PATRON_HASHTAG.fullmatch(tag) is None for tag in hashtags):
        errores.append("hashtag_invalid")
    canonicos = [unicodedata.normalize("NFKC", tag).casefold() for tag in hashtags]
    if len(canonicos) != len(set(canonicos)):
        errores.append("hashtag_duplicate")
    hechos = (
        ("titulo", "title_missing"),
        ("fecha", "date_missing"),
        ("organiza", "organizer_missing"),
        ("contacto", "contact_missing"),
    )
    for campo, codigo in hechos:
        if not _contiene_hecho(texto, fila[campo]):
            errores.append(codigo)
    if fila.get("lugar", "").strip() and not _contiene_hecho(texto, fila["lugar"]):
        errores.append("place_missing")

    residual = _remover_hechos_autorizados(texto, fila)
    if PATRON_FECHA.search(residual) is not None:
        errores.append("unauthorized_date")
    if PATRON_NUMERO.search(residual) is not None:
        errores.append("unauthorized_number")
    if PATRON_EMAIL.search(residual) is not None:
        errores.append("unauthorized_email")
    if PATRON_URL.search(residual) is not None:
        errores.append("unauthorized_url")
    if PATRON_IMPORTE.search(residual) is not None:
        errores.append("unauthorized_amount")
    residual_original = _remover_hechos_autorizados_original(texto, fila)
    lugares_propios = [
        valor
        for valor in PATRON_LUGAR_PROPIO.findall(residual_original)
        if valor.casefold() not in {"instagram", "linkedin"}
    ]
    if PATRON_LUGAR_ETIQUETADO.search(residual_original) is not None or lugares_propios:
        errores.append("unauthorized_place")
    if PATRON_ACCION_NO_AUTORIZADA.search(texto) is not None:
        errores.append("unauthorized_action_claim")
    return errores


def _prompt_version(canal: str | None) -> str | None:
    return f"post_{canal}_v1" if canal in CANALES else None


def _registro_base(
    *,
    fila: dict[str, str] | None,
    id_solicitud: str,
    canal: str | None,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    latencia_s: float,
) -> dict[str, object]:
    return {
        "correlation_id": correlation_id,
        "id_solicitud": id_solicitud if fila is not None else None,
        "id_solicitud_hash": None if fila is not None else _hash_texto(id_solicitud),
        "HU": HU,
        "canal": canal,
        "contract_version": CONTRACT_VERSION,
        "policy_version": politica.version,
        "policy_status": politica.status,
        "max_chars": politica.max_chars,
        "min_hashtags": politica.min_hashtags,
        "max_hashtags": politica.max_hashtags,
        "prompt_version": _prompt_version(canal),
        "modelo": generator.modelo,
        "num_predict": getattr(generator, "num_predict", None),
        "latencia_s": latencia_s,
        "input_hash": _hash_json(fila) if fila is not None else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _fallo(
    *,
    fila: dict[str, str] | None,
    id_solicitud: str,
    canal: str | None,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    inicio: float,
    estado: str,
    resultado: str,
    error: str,
    validation_errors: list[str] | None = None,
    extra_fields: dict[str, object] | None = None,
) -> ResultadoProceso:
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro = _registro_base(
        fila=fila,
        id_solicitud=id_solicitud,
        canal=canal,
        generator=generator,
        politica=politica,
        correlation_id=correlation_id,
        latencia_s=round(time.perf_counter() - inicio, 6),
    ) | {
        "estado": estado,
        "resultado": resultado,
        "error": error,
        "output_hash": None,
    }
    if validation_errors is not None:
        registro["validation_errors"] = validation_errors
    if extra_fields is not None:
        registro.update(extra_fields)
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado=estado,
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _fallo_fuente(
    *,
    id_solicitud: object,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    inicio: float,
    code: str,
) -> ResultadoProceso:
    code_seguro = code if code in SOURCE_ERROR_CODES else "source_unavailable"
    invalida = code_seguro in {"source_request_invalid", "source_request_not_found"}
    id_seguro = id_solicitud if isinstance(id_solicitud, str) else ""
    resultado = _fallo(
        fila=None,
        id_solicitud=id_seguro,
        canal=canal if canal in CANALES else None,
        directorio_salida=directorio_salida,
        generator=generator,
        politica=politica,
        correlation_id=correlation_id,
        inicio=inicio,
        estado="INVALIDA" if invalida else "FALLIDA",
        resultado="source_invalid" if invalida else "source_failure",
        error="Solicitud inválida o inexistente" if invalida else "Falló la lectura de la fuente",
        extra_fields={"source_error_code": code_seguro},
    )
    return resultado


def _fallo_destino(
    *,
    fila: dict[str, str],
    id_solicitud: str,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    inicio: float,
    borrador: str,
    code: str,
    reconciliation_ref_hash: str | None,
) -> ResultadoProceso:
    code_seguro = code if code in DESTINATION_ERROR_CODES else "destination_unavailable"
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro = _registro_base(
        fila=fila,
        id_solicitud=id_solicitud,
        canal=canal,
        generator=generator,
        politica=politica,
        correlation_id=correlation_id,
        latencia_s=round(time.perf_counter() - inicio, 6),
    ) | {
        "estado": "FALLIDA",
        "resultado": "destination_failure",
        "error": "Falló la persistencia del borrador",
        "output_hash": _hash_texto(borrador),
        "destination_error_code": code_seguro,
    }
    if code_seguro == code and reconciliation_ref_hash is not None:
        registro["reconciliation_ref_hash"] = reconciliation_ref_hash
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="Falló la persistencia del borrador",
    )


def _registrar(path: Path, registro: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")


def _hash_json(valor: dict[str, str]) -> str:
    return _hash_texto(
        json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _hash_texto(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _normalizar_hecho(valor: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", valor).casefold().split())


def _patron_hecho(valor: str, *, normalizado: bool) -> re.Pattern[str] | None:
    frase = _normalizar_hecho(valor) if normalizado else unicodedata.normalize("NFKC", valor).strip()
    if not frase:
        return None
    partes = frase.split()
    cuerpo = r"\s+".join(re.escape(parte) for parte in partes)
    return re.compile(
        r"(?<!\w)" + cuerpo + r"(?!\w)",
        flags=0 if normalizado else re.IGNORECASE,
    )


def _contiene_hecho(texto: str, hecho: str) -> bool:
    patron = _patron_hecho(hecho, normalizado=True)
    return patron is not None and patron.search(_normalizar_hecho(texto)) is not None


def _remover_hechos_autorizados(texto: str, fila: dict[str, str]) -> str:
    residual = _normalizar_hecho(texto)
    valores = sorted(
        (fila.get(campo, "") for campo in CAMPOS_SEMANTICOS_AUTORIZADOS),
        key=lambda valor: len(_normalizar_hecho(valor)),
        reverse=True,
    )
    for valor in valores:
        patron = _patron_hecho(valor, normalizado=True)
        if patron is not None:
            residual = patron.sub(" ", residual)
    return " ".join(residual.split())


def _remover_hechos_autorizados_original(texto: str, fila: dict[str, str]) -> str:
    residual = unicodedata.normalize("NFKC", texto)
    valores = sorted(
        (fila.get(campo, "") for campo in CAMPOS_SEMANTICOS_AUTORIZADOS),
        key=lambda valor: len(_normalizar_hecho(valor)),
        reverse=True,
    )
    for valor in valores:
        patron = _patron_hecho(valor, normalizado=False)
        if patron is not None:
            residual = patron.sub(" ", residual)
    return residual
