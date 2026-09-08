"""HU-011: borradores de posts por canal, con los hechos fuera del modelo.

La diferencia central con HU-010 es cómo se reparte el trabajo con el modelo.
Acá el modelo **no escribe el post**: devuelve un JSON con tres piezas de
redacción acotadas (`gancho`, `prosa`, `cta`) más hashtags, y el post final lo
arma `_renderizar_post_estructurado`, que intercala los datos de la actividad
copiados literalmente de la fuente. El modelo nunca toca un dato institucional.

Sobre eso hay un *gate de hechos*: si en las piezas creativas aparece una
fecha, un número, un correo, una URL, un importe, un lugar o cualquier frase de
la fila, la salida se rechaza entera. La lógica es que un dato correcto salido
del modelo y un dato inventado son indistinguibles a simple vista; como los
datos verdaderos ya los pone el renderer, cualquier hecho en la zona creativa
sobra y es sospechoso. Es un criterio deliberadamente conservador: prefiere
rechazar un texto aceptable antes que dejar pasar uno con un dato inventado.

Dos caminos conviven:

- `procesar_post_estructurado` (el usado): contrato creativo + renderer.
- `procesar_post` (`text-v1`, heredado): el modelo devuelve el post completo y
  se valida a posteriori. Se conserva porque sus pruebas documentan por qué se
  abandonó —validar prosa libre exige adivinar qué parte es un hecho— y
  requiere selección explícita en la CLI.

Otras decisiones que no se ven en el código:

- **El registro rioplatense se controla mecánicamente** (`PATRON_TUTEO`): los
  modelos abiertos escriben en español neutro con tuteo peninsular, ajeno al
  registro institucional. Es un control de forma, no de calidad editorial.
- **Los hashtags salen de una allowlist provisional**, no de la creatividad del
  modelo: un hashtag inventado puede arrastrar a la institución a una campaña
  ajena. La lista está pendiente de aprobación de la SEU (DEF-A1-007).
- **Toda política es `PROVISIONAL_NO_INSTITUCIONAL`** y así se registra: los
  límites de extensión y de hashtags los fijó el equipo técnico.
"""

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
from .politica_redes import (
    CANALES_SOPORTADOS,
    POLICY_STATUS,
    POLICY_VERSION,
    POLITICA_DEFAULT,
    POLITICAS_DEFAULT,
    PoliticaPost,
    errores_de_estilo,
)
from .presupuesto import PresupuestoAgotadoError
from .procesamiento import Generator, ResultadoProceso


HU = "HU-011"
CONTRACT_VERSION = "post_input_v1"
STRUCTURED_OUTPUT_CONTRACT_VERSION = "post_creative_output_v2"
STRUCTURED_RENDERER_VERSION = "post_deterministic_renderer_v2"
CANALES = frozenset(CANALES_SOPORTADOS)
# Campos cuyo contenido el renderer sí puede poner en el post. Son también los
# que se buscan dentro del texto creativo para rechazarlo: si el modelo
# menciona cualquiera de estos valores, está duplicando —o inventando— un hecho
# que no le corresponde.
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
# --- Patrones del gate de hechos -------------------------------------------
# Cada uno detecta una clase de dato que el modelo no tiene autorización para
# escribir. Están puestos sobre el texto *creativo*, no sobre el post final:
# el post final sí lleva fecha y contacto, pero los pone el renderer.
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
# Verbos de acto institucional. Un borrador no puede afirmar que algo fue
# aprobado, confirmado u oficializado: esa afirmación sólo puede hacerla la
# institución, y aparecería en un texto todavía no validado. También se aplica
# sobre los datos de la fuente, para no arrastrar ese estado al post.
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
    """Camino heredado `text-v1`: el modelo devuelve el post entero.

    Se conserva por trazabilidad de la decisión y requiere pedirlo
    explícitamente. Validar prosa libre obliga a restar del texto los hechos
    autorizados y revisar el residuo (`_remover_hechos_autorizados`), técnica
    frágil que motivó pasar al contrato estructurado.
    """

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
    """Pipeline común a los dos contratos de HU-011.

    `structured=None` corre el camino heredado; con un `ContratoCreativo` corre
    el estructurado. Igual que en HU-010, no propaga excepciones: cada frontera
    (fuente, generador, destino) se traduce a estado + línea de auditoría.
    """

    correlation_id = str(uuid.uuid4())
    inicio = time.perf_counter()
    # Para poder auditar un fallo que ocurre antes de conocer el canal hace
    # falta una política igual: se usa una por defecto sólo a efectos del
    # registro, y se reemplaza por la del canal apenas éste se valida.
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
    # Controles sobre la *fuente* previos a generar. El renderer copia estos
    # valores tal cual al post, así que lo que no sea seguro copiar tiene que
    # frenarse acá y no después: un carácter de control rompería la estructura
    # del documento, y un estado institucional ("aprobado") pasaría al borrador
    # como si fuera un hecho ya validado.
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
    # Si la política exige más hashtags de los que tiene la lista segura, no hay
    # salida posible que cumpla ambas reglas. Se rechaza como incompatibilidad
    # de configuración en vez de generar algo que después falle el gate.
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
    # Antes del genérico: una salida truncada por presupuesto no es un fallo de
    # generación, y registrarla como tal hace que el diagnóstico apunte al
    # modelo en vez de a la configuración. Ver DEF-A1-013.
    except PresupuestoAgotadoError:
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
            resultado="presupuesto_agotado",
            error="El presupuesto de decodificación no alcanzó para la salida",
            extra_fields=_campos_auditoria_estructurada(structured, canal),
        )
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
    # El nombre del borrador lleva canal y versión de contrato: una misma
    # solicitud produce una pieza por canal, y al comparar contratos (v2 contra
    # v3) las salidas tienen que poder convivir sin pisarse.
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
        .replace("{max_emojis}", _limite_declarado(politica.max_emojis))
        .replace("{max_exclamaciones}", _limite_declarado(politica.max_exclamaciones))
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
        .replace("{max_emojis}", _limite_declarado(politica.max_emojis))
        .replace("{max_exclamaciones}", _limite_declarado(politica.max_exclamaciones))
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


def _limite_declarado(valor: int | None) -> str:
    """Una política sin la regla declarada no debe inyectar `None` al prompt."""
    # Se declara "cero" y no "sin límite": si la regla no está aplicada, pedirle
    # al modelo el comportamiento más conservador es preferible a autorizarlo.
    return "cero" if valor is None else str(valor)


class _ClaveJsonDuplicada(ValueError):
    pass


def _objeto_json_sin_duplicados(
    pares: list[tuple[str, object]],
) -> dict[str, object]:
    """Rechaza claves repetidas en el JSON del modelo.

    `json.loads` se queda por defecto con la última aparición, así que un
    objeto con `"cta"` dos veces validaría un valor y renderizaría otro. Es
    justamente la forma que tendría un intento de evadir el gate.
    """

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
    r"modalidad|horarios?|transmisi[oó]n|presencial|virtual|remot[oa]s?|"
    r"online|digital(?:es)?)\b",
    flags=re.IGNORECASE,
)
PATRON_CIRCUITO_NO_AUTORIZADO = re.compile(
    r"\b(?:inscrib(?:ite|irse|ir|an|en)|registr(?:ate|arse|ar|en)|"
    r"reserv(?:á|a|ar)|compr(?:á|a|ar)|agend(?:á|a|ar))\b",
    flags=re.IGNORECASE,
)
# Formas verbales de tuteo peninsular ("inscríbete", "únete"). Los modelos
# abiertos las producen por defecto; el registro institucional local usa voseo o
# formas impersonales. Es un control de registro, no de calidad: la lista es
# corta a propósito y cubre los imperativos que aparecen en la práctica.
PATRON_TUTEO = re.compile(
    r"\b(?:inscr[ií]bete|reg[ií]strate|[uú]nete|participa|comp[aá]rtelo|"
    r"desc[uú]brelo|aprovecha|con[ée]ctate)\b",
    flags=re.IGNORECASE,
)
# Eco de vocabulario de prompting en la salida. Si aparece, o el modelo está
# repitiendo sus instrucciones o alguien intentó inyectar texto por la fila de
# la planilla; en cualquier caso el borrador no sirve.
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
    """Parsea el JSON del modelo y le aplica el gate de hechos.

    Es el control central de HU-011. Se ejecuta en dos tramos:

    1. **Forma**: que sea JSON, sin claves duplicadas, con exactamente los
       campos del contrato, tipos correctos y longitudes dentro de rango.
    2. **Contenido**: que las piezas creativas no contengan ningún hecho —ni de
       la fila ni inventado—, ni llamados a la acción que impliquen un circuito
       de inscripción que la SEU no definió, ni registro ajeno al institucional.

    Devuelve `(creatividad, errores)`. La creatividad puede venir acompañada de
    errores: el llamador sólo renderiza si la lista está vacía. Los códigos se
    deduplican conservando el orden para que el log sea estable.
    """

    if not contenido:
        return None, ["output_empty"]
    # Tope antes de parsear: un JSON enorme no puede cumplir los límites del
    # contrato, y parsearlo sólo gastaría memoria sobre una entrada no confiable.
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

    # A partir de acá se evalúan las piezas creativas juntas, como un único
    # texto: da lo mismo en cuál de ellas aparezca un hecho no autorizado.
    texto_creativo = "\n".join(
        [str(creatividad[campo]) for campo in contrato.limites]
        + [" ".join(hashtags)]
    )
    # Cualquier dígito se rechaza sin más análisis: separar un número inocente
    # de una cifra inventada exigiría entender el texto, y todos los números
    # legítimos del post (fecha, cupos, horarios) los pone el renderer.
    if any(
        _contiene_hecho(texto_creativo, fila.get(campo, ""))
        for campo in CAMPOS_SEMANTICOS_AUTORIZADOS
        if fila.get(campo, "").strip()
    ) or _contiene_fragmento_significativo(texto_creativo, fila.get("titulo", "")):
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
    if PATRON_CIRCUITO_NO_AUTORIZADO.search(texto_creativo):
        errores.append("unauthorized_call_to_action")
    if PATRON_TUTEO.search(texto_creativo):
        errores.append("non_rioplatense_register")
    if PATRON_HECHO_CREATIVO.search(texto_creativo):
        errores.append("unauthorized_fact_claim")
    if PATRON_ATRIBUCION_FACTUAL.search(texto_creativo):
        errores.append("unauthorized_fact_claim")
    if PATRON_INYECCION.search(texto_creativo):
        errores.append("prompt_injection_echo")
    errores.extend(errores_de_estilo(texto_creativo, politica))
    return creatividad, list(dict.fromkeys(errores))


def _renderizar_post_estructurado(
    fila: dict[str, str], canal: str, creatividad: dict[str, object]
) -> str:
    """Arma el post: creatividad del modelo + hechos copiados de la fuente.

    Es una función pura y determinista, sin ninguna decisión propia: la misma
    fila y la misma creatividad producen siempre el mismo texto. Eso es lo que
    permite verificar después, en `_validar_render_estructurado`, que el
    contenido guardado sea exactamente el que corresponde a esas dos entradas.

    `Lugar` sólo se agrega si la fila lo trae: no hay valor por defecto ni
    texto de relleno para un dato que la institución no cargó.
    """

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
    """Verifica el post ya armado, antes de guardarlo.

    El primer control vuelve a renderizar y compara: si el contenido que está a
    punto de guardarse no es idéntico al que produce el renderer con esas
    entradas, algo lo modificó en el camino y se aborta. Es barato y cierra la
    posibilidad de que se guarde un texto que nunca pasó por el gate.

    El límite de extensión se aplica recién acá porque incluye los hechos que
    agrega el renderer: el modelo no puede calcularlo por adelantado.
    """

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
    """Validación del camino heredado `text-v1`, sobre prosa libre.

    Acá el post entero lo escribió el modelo, así que no alcanza con prohibir
    hechos: primero hay que exigir que los hechos verdaderos estén presentes, y
    después restarlos del texto (`_remover_hechos_autorizados`) para revisar
    qué queda. Ese residuo es lo que se inspecciona en busca de datos
    inventados.

    La técnica es frágil —depende de acertar la forma exacta en que el modelo
    escribió cada hecho— y es la razón por la que el contrato estructurado la
    reemplazó. Se documenta para que quede constancia de por qué.
    """

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
    # La detección de lugares necesita el texto con su capitalización original
    # (un lugar propio se reconoce por la mayúscula), así que se usa un residual
    # sin plegar el caso, distinto del que se usa para fechas y números.
    residual_original = _remover_hechos_autorizados_original(texto, fila)
    lugares_propios = [
        valor
        for valor in PATRON_LUGAR_PROPIO.findall(residual_original)
        # "en Instagram" / "en LinkedIn" son el canal, no una sede.
        if valor.casefold() not in {"instagram", "linkedin"}
    ]
    if PATRON_LUGAR_ETIQUETADO.search(residual_original) is not None or lugares_propios:
        errores.append("unauthorized_place")
    if PATRON_ACCION_NO_AUTORIZADA.search(texto) is not None:
        errores.append("unauthorized_action_claim")
    errores.extend(errores_de_estilo(texto, politica))
    return list(dict.fromkeys(errores))


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
    """Campos comunes a toda línea de auditoría de HU-011.

    Incluye la política aplicada con su `policy_status`: una evidencia de este
    módulo siempre dice, en la misma línea, que los límites usados eran
    provisionales y no institucionales.

    `fila is None` significa que la fuente no se pudo leer; en ese caso el id se
    registra como hash, porque no está confirmado que sea una solicitud real.
    """

    registro = {
        "correlation_id": correlation_id,
        "id_solicitud": id_solicitud if fila is not None else None,
        "id_solicitud_hash": None if fila is not None else _hash_texto(id_solicitud),
        "HU": HU,
        "canal": canal,
        "contract_version": CONTRACT_VERSION,
        "policy_version": politica.version,
        "policy_status": politica.status,
        "policy_document_version": POLICY_VERSION,
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
    # Sólo los generadores que fuerzan salida con esquema exponen estos
    # atributos. Se registran cuando existen porque cambian el resultado: no es
    # lo mismo un JSON obtenido por instrucción en el prompt que uno impuesto
    # por el motor. Se leen con getattr para no obligar a todo adapter del
    # puerto `Generator` a declararlos.
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
    """¿El texto contiene ese hecho, tolerando acentos, caso y espacios?

    Se usa con dos sentidos opuestos según el contrato: en `text-v1` la
    ausencia del hecho es el error (el post debe informarlo); en el
    estructurado, su presencia en la zona creativa es el error.
    """

    patron = _patron_hecho(hecho, normalizado=True)
    return patron is not None and patron.search(_normalizar_hecho(texto)) is not None


def _contiene_fragmento_significativo(texto: str, hecho: str) -> bool:
    """Detecta fragmentos de hechos sin confundir artículos o preposiciones.

    El gate estructurado no permite que la creatividad replique hechos de la
    fuente: el renderer los agrega en secciones fijas. Comparar sólo la frase
    completa dejaba pasar, por ejemplo, ``Taller`` cuando el título era
    ``Taller sintético de vinculación``. Se rechazan palabras de al menos cinco
    caracteres que no sean conectores; sigue siendo un control mecánico
    conservador y la revisión semántica corresponde a la SEU.
    """
    palabras = re.findall(r"[^\W_]+", _normalizar_hecho(hecho), flags=re.UNICODE)
    for palabra in palabras:
        if len(palabra) < 5 or palabra in {"desde", "hasta", "sobre", "entre"}:
            continue
        patron = re.compile(r"(?<!\w)" + re.escape(palabra) + r"(?!\w)")
        if patron.search(_normalizar_hecho(texto)) is not None:
            return True
    return False


def _remover_hechos_autorizados(texto: str, fila: dict[str, str]) -> str:
    """Resta del texto los hechos que sí venían de la fuente.

    Lo que sobra es lo que el modelo agregó por su cuenta, y es ahí donde se
    buscan fechas, números, correos o importes. Se sustituye de más largo a más
    corto para que un valor contenido en otro (por ejemplo el organizador
    dentro del título) no rompa la coincidencia del más largo.
    """

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
