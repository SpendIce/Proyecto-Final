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
STRUCTURED_OUTPUT_CONTRACT_VERSION = "post_creative_output_v2"
STRUCTURED_RENDERER_VERSION = "post_deterministic_renderer_v2"
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
CONTRATO_SALIDA_ESTRUCTURADA = json.loads(
    files("agente1")
    .joinpath("contracts", "post_creative_output_v2.schema.json")
    .read_text(encoding="utf-8")
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
    r"validad[oa]s?|oficializad[oa]s?|oficializ[oó]|"
    r"aprob[aá]|aprobar|public[aá]|publicar|envi[aá]|enviar|"
    r"confirm[aá]|confirmar|valid[aá]|validar)\b",
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
    return _procesar_post(
        fuente=fuente,
        id_solicitud=id_solicitud,
        canal=canal,
        directorio_salida=directorio_salida,
        generator=generator,
        politica=politica,
        destino=destino,
        structured=None,
    )


def procesar_post_estructurado(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost | None = None,
    destino: DestinoBorradores | None = None,
    contrato: ContratoCreativo | None = None,
) -> ResultadoProceso:
    """Genera sólo creatividad acotada y renderiza hechos de forma determinista.

    `contrato` selecciona la versión del contrato creativo. `CONTRATO_CREATIVO_V2`
    restringe al modelo a un catálogo cerrado; `CONTRATO_CREATIVO_V3` lo deja
    redactar. En ambos casos los hechos institucionales los agrega el renderer
    determinista y el gate de validación rechaza invención de hechos.
    """
    return _procesar_post(
        fuente=fuente,
        id_solicitud=id_solicitud,
        canal=canal,
        directorio_salida=directorio_salida,
        generator=generator,
        politica=politica,
        destino=destino,
        structured=contrato or CONTRATO_CREATIVO_V2,
    )


def _procesar_post(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    politica: PoliticaPost | None,
    destino: DestinoBorradores | None,
    structured: ContratoCreativo | None,
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
            structured=structured,
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
            extra_fields=_campos_auditoria_estructurada(structured, None),
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
            structured=structured,
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
            structured=structured,
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
            structured=structured,
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
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    campos_renderizados = ("titulo", "fecha", "organiza", "contacto", "lugar")
    valores_renderizados = [fila.get(campo, "") for campo in campos_renderizados]
    if structured and any(
        unicodedata.category(char).startswith("C")
        for valor in valores_renderizados
        for char in valor
    ):
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            estado="FALLIDA",
            resultado="source_not_renderable",
            error="La fuente contiene controles incompatibles con el renderer",
            validation_errors=["source_rendering_unsafe"],
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    hechos_renderizados = " ".join(valores_renderizados)
    if structured and PATRON_ACCION_NO_AUTORIZADA.search(hechos_renderizados):
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            estado="FALLIDA",
            resultado="source_not_renderable",
            error="La fuente contiene un estado no autorizado para el borrador",
            validation_errors=["source_status_claim_not_allowed"],
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    if structured and politica_efectiva.min_hashtags > len(structured.hashtags_seguros):
        return _fallo(
            fila=fila,
            id_solicitud=id_solicitud,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            estado="INVALIDA",
            resultado="policy_incompatible",
            error="La política no es compatible con la lista segura provisional",
            validation_errors=["structured_policy_incompatible"],
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    prompt = (
        _construir_prompt_estructurado(fila, canal, politica_efectiva, structured)
        if structured
        else _construir_prompt(fila, canal, politica_efectiva)
    )
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
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    contenido_crudo = (
        unicodedata.normalize("NFC", salida_cruda.strip())
        if isinstance(salida_cruda, str)
        else ""
    )
    if structured:
        creatividad, errores = _parsear_creatividad_estructurada(
            contenido_crudo, fila, canal, politica_efectiva, structured
        )
        contenido = (
            _renderizar_post_estructurado(fila, canal, creatividad)
            if creatividad is not None and not errores
            else ""
        )
        if contenido:
            errores.extend(
                _validar_render_estructurado(
                    contenido, fila, canal, creatividad, politica_efectiva
                )
            )
    else:
        contenido = contenido_crudo
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
            resultado="salida_no_conforme" if contenido_crudo else "salida_vacia",
            error="La salida generada no cumple el contrato mínimo",
            validation_errors=list(dict.fromkeys(errores)),
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
    borrador = f"{BORRADOR_MARKER}{contenido}\n"
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    sufijo_borrador = structured.borrador_suffix if structured else ""
    id_borrador = f"{id_solicitud}-{canal}{sufijo_borrador}"
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
            structured=structured,
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
            structured=structured,
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
        | _campos_auditoria_estructurada(structured, canal)
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


def _construir_prompt_estructurado(
    fila: dict[str, str],
    canal: str,
    politica: PoliticaPost,
    contrato: ContratoCreativo,
) -> str:
    plantilla = files("agente1").joinpath(
        "prompts", f"post_{canal}_structured_{contrato.prompt_suffix}.txt"
    ).read_text(encoding="utf-8")
    datos = json.dumps(fila, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    prompt = (
        plantilla.replace("{max_chars}", str(politica.max_chars))
        .replace("{min_hashtags}", str(politica.min_hashtags))
        .replace(
            "{max_hashtags}",
            str(min(politica.max_hashtags, len(contrato.hashtags_seguros))),
        )
        .replace("{datos_fuente}", datos)
    )
    if contrato.catalogo_por_canal is not None:
        prompt = prompt.replace(
            "{catalogo_creativo}",
            json.dumps(
                contrato.catalogo_por_canal[canal],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    return prompt


class _ClaveJsonDuplicada(ValueError):
    pass


def _objeto_json_sin_duplicados(
    pares: list[tuple[str, object]],
) -> dict[str, object]:
    objeto: dict[str, object] = {}
    for clave, valor in pares:
        if clave in objeto:
            raise _ClaveJsonDuplicada(clave)
        objeto[clave] = valor
    return objeto


CAMPOS_CREATIVOS = frozenset(CONTRATO_SALIDA_ESTRUCTURADA["required"])
LIMITES_CREATIVOS = {
    campo: CONTRATO_SALIDA_ESTRUCTURADA["properties"][campo]["maxLength"]
    for campo in ("gancho", "prosa", "cta")
}
PATRON_HECHO_CREATIVO = re.compile(
    r"\b(?:gratis|gratuit[oa]s?|cupos?|certificad[oa]s?|inscripci[oó]n|"
    r"modalidad|horarios?|transmisi[oó]n|presencial|virtual)\b",
    flags=re.IGNORECASE,
)
PATRON_INYECCION = re.compile(
    r"\b(?:ignor[aá]|instrucciones|prompt|sistema|system|assistant)\b",
    flags=re.IGNORECASE,
)
HASHTAGS_CREATIVOS_SEGUROS = frozenset(
    unicodedata.normalize("NFC", tag)
    for tag in CONTRATO_SALIDA_ESTRUCTURADA["x-provisional-safety-hashtags"]
)
CATALOGO_CREATIVO_POR_CANAL = CONTRATO_SALIDA_ESTRUCTURADA[
    "x-provisional-creative-catalog-by-channel"
]
CATALOGO_CREATIVO_VERSION = CONTRATO_SALIDA_ESTRUCTURADA[
    "x-provisional-creative-catalog-version"
]
CONTRATO_SALIDA_ESTRUCTURADA_V3 = json.loads(
    files("agente1")
    .joinpath("contracts", "post_creative_output_v3.schema.json")
    .read_text(encoding="utf-8")
)


@dataclass(frozen=True)
class ContratoCreativo:
    """Agrupa todo lo que cambia entre versiones del contrato creativo.

    `catalogo_por_canal` en `None` significa que el modelo redacta en lugar de
    seleccionar. El gate de hechos de `_parsear_creatividad_estructurada` es
    independiente de esta elección y se aplica igual en todas las versiones.
    """

    contract_version: str
    renderer_version: str
    prompt_suffix: str
    borrador_suffix: str
    schema: dict[str, object]
    campos: frozenset[str]
    limites: dict[str, int]
    minimos: dict[str, int]
    hashtags_seguros: frozenset[str]
    catalogo_por_canal: dict[str, dict[str, list[str]]] | None
    catalogo_version: str | None


def _construir_contrato_creativo(
    contrato: dict[str, object],
    *,
    renderer_version: str,
    prompt_suffix: str,
    borrador_suffix: str,
) -> ContratoCreativo:
    propiedades = contrato["properties"]
    campos_texto = ("gancho", "prosa", "cta")
    catalogo = contrato.get("x-provisional-creative-catalog-by-channel")
    return ContratoCreativo(
        contract_version=str(contrato["x-contract-version"]),
        renderer_version=renderer_version,
        prompt_suffix=prompt_suffix,
        borrador_suffix=borrador_suffix,
        schema=contrato,
        campos=frozenset(contrato["required"]),
        limites={campo: propiedades[campo]["maxLength"] for campo in campos_texto},
        minimos={
            campo: propiedades[campo].get("minLength", 1) for campo in campos_texto
        },
        hashtags_seguros=frozenset(
            unicodedata.normalize("NFC", tag)
            for tag in contrato["x-provisional-safety-hashtags"]
        ),
        catalogo_por_canal=catalogo,
        catalogo_version=(
            str(contrato["x-provisional-creative-catalog-version"])
            if catalogo is not None
            else None
        ),
    )


CONTRATO_CREATIVO_V2 = _construir_contrato_creativo(
    CONTRATO_SALIDA_ESTRUCTURADA,
    renderer_version=STRUCTURED_RENDERER_VERSION,
    prompt_suffix="v2",
    borrador_suffix="-v2",
)
CONTRATO_CREATIVO_V3 = _construir_contrato_creativo(
    CONTRATO_SALIDA_ESTRUCTURADA_V3,
    renderer_version="post_deterministic_renderer_v3",
    prompt_suffix="v3",
    borrador_suffix="-v3",
)
# Detecta referencias a lugares genéricos en minúscula ("en el aula", "desde la
# sede"). La versión anterior usaba `\S+` como objeto, de modo que matcheaba
# cualquier sintagma preposicional del español —"en un mundo", "en esta
# actividad"— y hacía imposible redactar prosa libre. Los lugares con nombre
# propio los sigue cubriendo PATRON_LUGAR_PROPIO, los etiquetados
# PATRON_LUGAR_ETIQUETADO, y el lugar informado por la fuente se compara aparte
# con `source_fact_in_creative_field`. Ver DEF-A1-011.
PATRON_REFERENCIA_LUGAR = re.compile(
    r"\b(?:en|desde|hacia)\s+(?:(?:el|la|los|las|un|una)\s+)?"
    r"(?:aulas?|sedes?|campus|sal(?:[oó]n|ones)|salas?|auditorios?|edificios?|"
    r"predios?|pabell(?:[oó]n|ones)|anfiteatros?|laboratorios?|bibliotecas?|"
    r"institutos?|facultades?|facultad|universidades?|universidad|escuelas?|"
    r"colegios?|centros?|clubes?|club|teatros?|museos?|hoteles?|hotel|"
    r"direcci(?:[oó]n|ones)|calles?|avenidas?|pisos?|oficinas?)\b",
    flags=re.IGNORECASE,
)
PATRON_ATRIBUCION_FACTUAL = re.compile(
    r"\b(?:organiza|auspicia|incluye|ofrece|dictad[oa]\s+por|a\s+cargo\s+de)\b",
    flags=re.IGNORECASE,
)


def _parsear_creatividad_estructurada(
    contenido: str,
    fila: dict[str, str],
    canal: str,
    politica: PoliticaPost,
    contrato: ContratoCreativo,
) -> tuple[dict[str, object] | None, list[str]]:
    if not contenido:
        return None, ["output_empty"]
    if len(contenido.encode("utf-8")) > 16384:
        return None, ["json_too_large"]
    try:
        valor = json.loads(contenido, object_pairs_hook=_objeto_json_sin_duplicados)
    except _ClaveJsonDuplicada:
        return None, ["json_duplicate_key"]
    except (json.JSONDecodeError, UnicodeError):
        return None, ["json_invalid"]
    if not isinstance(valor, dict):
        return None, ["json_types_invalid"]
    if set(valor) != contrato.campos:
        return None, ["json_fields_invalid"]
    tipos_invalidos = (
        any(not isinstance(valor[campo], str) for campo in contrato.limites)
        or not isinstance(valor["hashtags"], list)
        or any(not isinstance(tag, str) for tag in valor["hashtags"])
    )
    if tipos_invalidos:
        return None, ["json_types_invalid"]

    creatividad: dict[str, object] = {
        campo: unicodedata.normalize("NFC", str(valor[campo]).strip())
        for campo in contrato.limites
    }
    creatividad["hashtags"] = [
        unicodedata.normalize("NFC", tag.strip()) for tag in valor["hashtags"]
    ]
    errores: list[str] = []
    if any(
        not creatividad[campo]
        or len(str(creatividad[campo])) > contrato.limites[campo]
        or len(str(creatividad[campo])) < contrato.minimos[campo]
        or any(
            unicodedata.category(char).startswith("C")
            for char in str(creatividad[campo])
        )
        for campo in contrato.limites
    ):
        errores.append("creative_field_invalid")
    # Un contrato sin catálogo deja que el modelo redacte. El gate de hechos que
    # sigue más abajo no depende de esta elección y se aplica igual.
    if contrato.catalogo_por_canal is not None:
        catalogo = contrato.catalogo_por_canal[canal]
        if any(
            creatividad[campo] not in catalogo[campo] for campo in contrato.limites
        ):
            errores.append("creative_slot_not_in_catalog")

    hashtags = creatividad["hashtags"]
    assert isinstance(hashtags, list)
    max_hashtags_efectivo = min(
        politica.max_hashtags, len(contrato.hashtags_seguros)
    )
    if not politica.min_hashtags <= len(hashtags) <= max_hashtags_efectivo:
        errores.append("hashtag_count_out_of_range")
    if any(PATRON_HASHTAG.fullmatch(tag) is None for tag in hashtags):
        errores.append("hashtag_invalid")
    canonicos = [unicodedata.normalize("NFKC", tag).casefold() for tag in hashtags]
    if len(canonicos) != len(set(canonicos)):
        errores.append("hashtag_duplicate")
    if any(tag not in contrato.hashtags_seguros for tag in hashtags):
        errores.append("hashtag_not_in_provisional_safety_allowlist")

    texto_creativo = "\n".join(
        [str(creatividad[campo]) for campo in contrato.limites]
        + [" ".join(hashtags)]
    )
    if any(
        _contiene_hecho(texto_creativo, fila.get(campo, ""))
        for campo in CAMPOS_SEMANTICOS_AUTORIZADOS
        if fila.get(campo, "").strip()
    ):
        errores.append("source_fact_in_creative_field")
    if PATRON_FECHA.search(texto_creativo):
        errores.append("unauthorized_date")
    if re.search(r"\d", texto_creativo):
        errores.append("unauthorized_number")
    if PATRON_EMAIL.search(texto_creativo):
        errores.append("unauthorized_email")
    if PATRON_URL.search(texto_creativo):
        errores.append("unauthorized_url")
    if PATRON_IMPORTE.search(texto_creativo):
        errores.append("unauthorized_amount")
    if (
        PATRON_LUGAR_ETIQUETADO.search(texto_creativo)
        or PATRON_LUGAR_PROPIO.search(texto_creativo)
        or PATRON_REFERENCIA_LUGAR.search(texto_creativo)
    ):
        errores.append("unauthorized_place")
    if PATRON_ACCION_NO_AUTORIZADA.search(texto_creativo):
        errores.append("unauthorized_action_claim")
    if PATRON_HECHO_CREATIVO.search(texto_creativo):
        errores.append("unauthorized_fact_claim")
    if PATRON_ATRIBUCION_FACTUAL.search(texto_creativo):
        errores.append("unauthorized_fact_claim")
    if PATRON_INYECCION.search(texto_creativo):
        errores.append("prompt_injection_echo")
    return creatividad, list(dict.fromkeys(errores))


def _renderizar_post_estructurado(
    fila: dict[str, str], canal: str, creatividad: dict[str, object]
) -> str:
    lineas = [
        f"CANAL: {canal}",
        "TEXTO:",
        str(creatividad["gancho"]),
        "",
        str(creatividad["prosa"]),
        "",
        f"Título: {fila['titulo']}",
        f"Fecha: {fila['fecha']}",
        f"Organiza: {fila['organiza']}",
    ]
    if fila.get("lugar", "").strip():
        lineas.append(f"Lugar: {fila['lugar']}")
    lineas.extend(
        [
            f"Contacto: {fila['contacto']}",
            "",
            str(creatividad["cta"]),
            "HASHTAGS:",
            " ".join(creatividad["hashtags"]),
        ]
    )
    return "\n".join(lineas)


def _validar_render_estructurado(
    contenido: str,
    fila: dict[str, str],
    canal: str,
    creatividad: dict[str, object],
    politica: PoliticaPost,
) -> list[str]:
    if contenido != _renderizar_post_estructurado(fila, canal, creatividad):
        return ["renderer_invariant_violation"]
    _, separador_texto, cuerpo = contenido.partition("\nTEXTO:\n")
    texto, separador_hashtags, hashtags = cuerpo.rpartition("\nHASHTAGS:\n")
    if not separador_texto or not separador_hashtags:
        return ["document_structure"]
    if len(texto) + len(hashtags) > politica.max_chars:
        return ["length_out_of_range"]
    return []


def _campos_auditoria_estructurada(
    structured: ContratoCreativo | None, canal: str | None
) -> dict[str, object]:
    if not structured:
        return {}
    return {
        "output_contract_version": structured.contract_version,
        "renderer_version": structured.renderer_version,
        "creative_catalog_version": structured.catalogo_version,
        "prompt_version": (
            f"post_{canal}_structured_{structured.prompt_suffix}"
            if canal in CANALES
            else None
        ),
    }


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
    registro = {
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
    format_mode = getattr(generator, "format_mode", None)
    format_schema_hash = getattr(generator, "format_schema_hash", None)
    if format_mode is not None and format_schema_hash is not None:
        registro["generation_format"] = format_mode
        registro["format_schema_hash"] = format_schema_hash
    return registro


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
    structured: ContratoCreativo | None = None,
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
        extra_fields={"source_error_code": code_seguro}
        | _campos_auditoria_estructurada(structured, canal),
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
    structured: ContratoCreativo | None = None,
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
    ) | _campos_auditoria_estructurada(structured, canal) | {
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
