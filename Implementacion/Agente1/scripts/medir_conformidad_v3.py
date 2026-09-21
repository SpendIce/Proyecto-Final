#!/usr/bin/env python3
"""Medición diagnóstica de la conformidad del contrato v3 de HU-011.

El corte 2026-09-08 (`evidencias/manifest-hu011-live-v3-2026-09-08.json` y
`regresion-consolidada-2026-09-08.md`) registró 0/6 aceptaciones para
`post_creative_output_v3` con `llama3.2:3b`, pero el resumen sólo conserva los
códigos del gate: no dice qué escribió el modelo ni qué literal disparó cada
regla. Este script existe para convertir ese resultado en diagnóstico: corre la
misma matriz de casos contra el mismo pipeline —`procesar_post_estructurado`,
sin tocarlo— y, por cada generación, registra qué regla cayó, con qué literal
de la salida y con cuántos tokens emitidos.

Para eso el transporte se reimplementa acá con los parámetros abiertos
(`temperature`, `num_predict`, `format` y una transformación del prompt), en
lugar de modificar `OllamaGenerator`: el adapter de producción fija
`temperature: 0` a propósito y este spike no tiene por qué tocarlo. La semántica
del intercambio es la misma (`/api/generate`, `stream: false`, detección de
`done_reason == "length"` como `PresupuestoAgotadoError`), de modo que la
medición ejercita el mismo contrato de puerto que el código versionado.

Las transformaciones de prompt se aplican sobre el prompt ya construido, dentro
del generador de medición: el archivo de plantilla versionado no se modifica y
cada corrida declara su variante en el resumen. Las respuestas crudas del
modelo se guardan como archivos aparte bajo el directorio de salida (ignorado
por Git, igual que `salida/`): el JSON de resumen sólo lleva códigos, literales
de patrón, conteos y hashes, nunca la prosa generada.

Requiere un Ollama local ya iniciado con el modelo descargado y la bandera
`--confirm-live-llm`, porque invoca un modelo real. No publica, no envía y no
comparte contenido.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPConnection
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.politica_redes import (  # noqa: E402
    POLITICA_REDES,
    contar_emojis,
    contar_exclamaciones,
)
from agente1.posts import (  # noqa: E402
    CAMPOS_SEMANTICOS_AUTORIZADOS,
    CONTRATO_CREATIVO_V2,
    CONTRATO_CREATIVO_V3,
    PATRON_ACCION_NO_AUTORIZADA,
    PATRON_ATRIBUCION_FACTUAL,
    PATRON_CIRCUITO_NO_AUTORIZADO,
    PATRON_EMAIL,
    PATRON_FECHA,
    PATRON_HECHO_CREATIVO,
    PATRON_IMPORTE,
    PATRON_INYECCION,
    PATRON_LUGAR_ETIQUETADO,
    PATRON_LUGAR_PROPIO,
    PATRON_REFERENCIA_LUGAR,
    PATRON_TUTEO,
    PATRON_URL,
    _contiene_hecho,
    _normalizar_hecho,
    procesar_post_estructurado,
)
from agente1.presupuesto import (  # noqa: E402
    MENSAJE_PRESUPUESTO_AGOTADO,
    PresupuestoAgotadoError,
)


CONTRATOS = {"v2": CONTRATO_CREATIVO_V2, "v3": CONTRATO_CREATIVO_V3}
CANALES = ("instagram", "linkedin")
CASOS = (
    ("SYN-001", "PENDIENTE_VALIDACION"),
    ("SYN-002", "INCOMPLETA"),
    ("SYN-003", "PENDIENTE_VALIDACION"),
    ("SYN-004", "INCOMPLETA"),
    ("SYN-005", "PENDIENTE_VALIDACION"),
)

# Mapeo código de gate -> regla del artefacto de política. Los códigos que no
# tienen regla RED-* pertenecen al gate de hechos o al parseo contractual, y se
# agrupan por categoría estructural más abajo.
CODIGO_A_REGLA = {
    str(regla["codigo_gate"]): str(regla["id"])
    for regla in POLITICA_REDES["reglas"]
    if regla["codigo_gate"] is not None
}
CATEGORIA_POR_CODIGO = {
    "output_empty": "parseo",
    "json_invalid": "parseo",
    "json_duplicate_key": "parseo",
    "json_too_large": "parseo",
    "json_types_invalid": "parseo",
    "json_fields_invalid": "parseo",
    "creative_field_invalid": "contrato_creativo",
    "creative_slot_not_in_catalog": "contrato_creativo",
    "renderer_invariant_violation": "contrato_creativo",
    "document_structure": "contrato_creativo",
    "source_fact_in_creative_field": "gate_hechos",
    "unauthorized_date": "gate_hechos",
    "unauthorized_number": "gate_hechos",
    "unauthorized_email": "gate_hechos",
    "unauthorized_url": "gate_hechos",
    "unauthorized_amount": "gate_hechos",
    "unauthorized_place": "gate_hechos",
    "unauthorized_fact_claim": "gate_hechos",
    "unauthorized_action_claim": "gate_hechos",
    "prompt_injection_echo": "gate_hechos",
    "non_rioplatense_register": "politica_redes",
    "unauthorized_call_to_action": "politica_redes",
    "unauthorized_promotional_language": "politica_redes",
    "unauthorized_exclamation": "politica_redes",
    "unauthorized_emoji": "politica_redes",
    "length_out_of_range": "politica_redes",
    "hashtag_count_out_of_range": "politica_redes",
    "hashtag_not_in_provisional_safety_allowlist": "politica_redes",
    "hashtag_duplicate": "politica_redes",
    "hashtag_invalid": "politica_redes",
    "channel_not_allowed": "politica_redes",
}

# Bloques que el spike puede insertar en el prompt ya renderizado, antes del
# delimitador de datos. Ninguno toca la plantilla versionada: son texto extra
# inyectado por el medidor para aislar el efecto de la instrucción.
BLOQUE_VOSEO = (
    "Recordatorio de registro rioplatense: la segunda persona del singular se "
    "escribe con voseo. Imperativos permitidos: «sumate», «participá», "
    "«conocé», «acercate», «animáte», «enterate». Formas impersonales "
    "permitidas: «se invita», «los invitamos», «te invitamos». Están prohibidas "
    "todas las formas de tuteo, por ejemplo: «inscríbete», «regístrate», "
    "«únete», «participa», «descubre», «explora», «aprovecha», «conoce», "
    "«comparte», «suscríbete», «visita», «sigue». Si dudás entre voseo y "
    "tuteo, preferí una forma impersonal."
)
BLOQUE_ANTIHECHOS = (
    "Recordatorio de separación de hechos: el sistema ya agrega por su cuenta "
    "el título, la fecha, la organización, el lugar y el contacto de la "
    "actividad. Tu texto no puede repetir ninguna de esas cosas, ni siquiera "
    "una palabra de cinco o más letras del título. Escribí una invitación "
    "genérica que funcione con cualquier actividad."
)


@dataclass
class RespuestaCapturada:
    """Lo que el servidor devolvió, antes de que el pipeline lo interprete."""

    contenido: str
    done_reason: str | None
    eval_count: int | None
    prompt_eval_count: int | None
    http_status: int | None
    error: str | None = None


class GeneradorMedicion:
    """Generador del puerto `Generator` con los parámetros de decodificación abiertos.

    Replica el intercambio del adapter de producción (`/api/generate`,
    `stream: false`, `done_reason == "length"` -> `PresupuestoAgotadoError`)
    pero deja elegir `temperature`, `num_predict`, `format` y una
    transformación del prompt. La lista `capturas` guarda cada respuesta en el
    orden en que llegó: como el pipeline llama `generar` una sola vez por caso,
    la última captura corresponde al caso en curso.
    """

    def __init__(
        self,
        *,
        modelo: str,
        base_url: str,
        timeout_s: float,
        num_predict: int,
        temperature: float,
        format_mode: str,
        format_schema: dict[str, object] | None,
        transform_prompt,
    ) -> None:
        self.modelo = modelo
        self.num_predict = num_predict
        self.temperature = temperature
        self.format_mode = format_mode if format_mode != "none" else None
        self.format_schema_hash = (
            hashlib.sha256(
                json.dumps(
                    format_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            if format_mode == "json_schema" and format_schema is not None
            else None
        )
        self._format = (
            format_schema if format_mode == "json_schema"
            else "json" if format_mode == "json"
            else None
        )
        self._transform = transform_prompt
        # Misma restricción que el adapter de producción: el medidor sólo
        # habla con un Ollama en loopback.
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.path not in {"", "/"}:
            raise ValueError("base_url debe ser http plano a un host de loopback")
        host = parsed.hostname or ""
        if host != "localhost":
            try:
                if not ip_address(host).is_loopback:
                    raise ValueError("base_url debe apuntar a loopback")
            except ValueError:
                raise ValueError("base_url debe apuntar a loopback") from None
        self._host = host
        self._port = parsed.port or 80
        self._timeout_s = timeout_s
        self.capturas: list[RespuestaCapturada] = []

    def generar(self, prompt: str) -> str:
        prompt_efectivo = self._transform(prompt) if self._transform else prompt
        solicitud: dict[str, object] = {
            "model": self.modelo,
            "prompt": prompt_efectivo,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }
        if self._format is not None:
            solicitud["format"] = self._format
        payload = json.dumps(solicitud, ensure_ascii=False).encode("utf-8")
        connection = HTTPConnection(self._host, self._port, timeout=self._timeout_s)
        http_status = None
        try:
            connection.request(
                "POST",
                "/api/generate",
                body=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            http_status = response.status
            cuerpo = response.read(1_048_576)
        except Exception as exc:
            self.capturas.append(
                RespuestaCapturada("", None, None, None, http_status, error=type(exc).__name__)
            )
            raise RuntimeError("No se pudo contactar al generador local") from None
        finally:
            connection.close()
        try:
            documento = json.loads(cuerpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.capturas.append(
                RespuestaCapturada("", None, None, None, http_status, error="respuesta_invalida")
            )
            raise RuntimeError("Respuesta inválida del generador local") from None
        if not isinstance(documento, dict):
            self.capturas.append(
                RespuestaCapturada("", None, None, None, http_status, error="respuesta_invalida")
            )
            raise RuntimeError("Respuesta inválida del generador local")
        contenido = documento.get("response")
        captura = RespuestaCapturada(
            contenido=contenido if isinstance(contenido, str) else "",
            done_reason=documento.get("done_reason"),
            eval_count=documento.get("eval_count"),
            prompt_eval_count=documento.get("prompt_eval_count"),
            http_status=http_status,
            error=str(documento.get("error"))[:120] if "error" in documento else None,
        )
        self.capturas.append(captura)
        if "error" in documento or documento.get("done") is not True or not isinstance(contenido, str) or not contenido.strip():
            raise RuntimeError("Respuesta inválida del generador local")
        if documento.get("done_reason") == "length":
            raise PresupuestoAgotadoError(MENSAJE_PRESUPUESTO_AGOTADO)
        return contenido.strip()


class GeneradorQueNoDebeInvocarse:
    """Centinela: un caso incompleto debe rechazarse antes de invocar al LLM."""

    modelo = "centinela-no-invocar"
    num_predict = None

    def generar(self, prompt: str) -> str:
        raise AssertionError("un caso incompleto no debe invocar al generador")


def _transformacion(variante: str):
    """Devuelve la función prompt->prompt de la variante pedida.

    El bloque se inserta antes de `DATOS_JSON_INICIO` para que quede dentro de
    las instrucciones y no mezclado con los datos no confiables.
    """

    bloques = {
        "baseline": (),
        "voseo": (BLOQUE_VOSEO,),
        "antihechos": (BLOQUE_ANTIHECHOS,),
        "voseo_antihechos": (BLOQUE_VOSEO, BLOQUE_ANTIHECHOS),
    }[variante]
    if not bloques:
        return None

    def transformar(prompt: str) -> str:
        inyeccion = "\n".join(bloques)
        marcador = "\nDATOS_JSON_INICIO"
        if marcador in prompt:
            return prompt.replace(marcador, "\n" + inyeccion + marcador, 1)
        return prompt + "\n" + inyeccion

    return transformar


def _literales_disparadores(contenido_crudo: str, fila: dict[str, str]) -> dict[str, object]:
    """Repite el gate a nivel literal: qué pedazo de texto disparó cada regla.

    Sirve para pasar de «cayó `non_rioplatense_register`» a «cayó porque el
    modelo escribió `únete`». Sólo se reportan los literales del patrón o del
    hecho fuente, nunca la prosa completa.
    """

    detalle: dict[str, object] = {}
    try:
        valor = json.loads(contenido_crudo)
    except (json.JSONDecodeError, TypeError):
        return {"parseable": False}
    if not isinstance(valor, dict):
        return {"parseable": False}
    campos = ("gancho", "prosa", "cta")
    piezas = [unicodedata.normalize("NFC", str(valor.get(c, ""))).strip() for c in campos]
    hashtags = valor.get("hashtags")
    lista_tags = hashtags if isinstance(hashtags, list) else []
    texto_creativo = "\n".join(piezas + [" ".join(str(t) for t in lista_tags)])
    detalle["parseable"] = True
    detalle["longitudes"] = {campo: len(pieza) for campo, pieza in zip(campos, piezas)}
    detalle["tuteos"] = sorted(set(PATRON_TUTEO.findall(texto_creativo)), key=str.casefold)
    detalle["circuito_cta"] = sorted(
        set(PATRON_CIRCUITO_NO_AUTORIZADO.findall(texto_creativo)), key=str.casefold
    )
    detalle["hecho_creativo"] = sorted(
        set(PATRON_HECHO_CREATIVO.findall(texto_creativo)), key=str.casefold
    )
    detalle["atribucion_factual"] = sorted(
        set(PATRON_ATRIBUCION_FACTUAL.findall(texto_creativo)), key=str.casefold
    )
    detalle["accion_no_autorizada"] = sorted(
        set(PATRON_ACCION_NO_AUTORIZADA.findall(texto_creativo)), key=str.casefold
    )
    detalle["inyeccion"] = sorted(set(PATRON_INYECCION.findall(texto_creativo)), key=str.casefold)
    detalle["lugar_etiquetado"] = PATRON_LUGAR_ETIQUETADO.findall(texto_creativo)
    detalle["lugar_propio"] = PATRON_LUGAR_PROPIO.findall(texto_creativo)
    detalle["referencia_lugar"] = PATRON_REFERENCIA_LUGAR.findall(texto_creativo)
    detalle["fechas"] = PATRON_FECHA.findall(texto_creativo)
    detalle["emails"] = PATRON_EMAIL.findall(texto_creativo)
    detalle["urls"] = PATRON_URL.findall(texto_creativo)
    detalle["importes"] = PATRON_IMPORTE.findall(texto_creativo)
    detalle["digitos"] = sorted(set(re.findall(r"\d", texto_creativo))) if re.search(r"\d", texto_creativo) else []
    detalle["emojis"] = contar_emojis(texto_creativo)
    detalle["exclamaciones"] = contar_exclamaciones(texto_creativo)
    # Qué campo de la fuente fugó al texto creativo. `fragmento_titulo` lista
    # las palabras del título de cinco o más letras que aparecen: es la forma
    # habitual de `source_fact_in_creative_field` con redacción libre.
    campos_fugados = [
        campo
        for campo in CAMPOS_SEMANTICOS_AUTORIZADOS
        if fila.get(campo, "").strip() and _contiene_hecho(texto_creativo, fila[campo])
    ]
    fragmentos = []
    palabras_titulo = re.findall(
        r"[^\W_]+", _normalizar_hecho(fila.get("titulo", "")), flags=re.UNICODE
    )
    texto_normalizado = _normalizar_hecho(texto_creativo)
    for palabra in palabras_titulo:
        if len(palabra) < 5 or palabra in {"desde", "hasta", "sobre", "entre"}:
            continue
        if re.search(r"(?<!\w)" + re.escape(palabra) + r"(?!\w)", texto_normalizado):
            fragmentos.append(palabra)
    detalle["campos_fuente_en_texto"] = campos_fugados
    detalle["fragmentos_titulo_en_texto"] = sorted(set(fragmentos))
    return detalle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mide la conformidad del contrato creativo de HU-011 por regla del gate."
    )
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--num-predict", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--format",
        choices=("json_schema", "json", "none"),
        default="json_schema",
        help="json_schema fuerza el contrato por grammar; json sólo pide JSON; none deja el prompt solo.",
    )
    parser.add_argument(
        "--variante-prompt",
        choices=("baseline", "voseo", "antihechos", "voseo_antihechos"),
        default="baseline",
        help="Texto extra que el medidor inserta en el prompt, sin tocar la plantilla versionada.",
    )
    parser.add_argument(
        "--contrato",
        choices=sorted(CONTRATOS),
        default="v3",
    )
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=1,
        help="Veces que se repite cada generación; con temperatura 0 son idénticas salvo variación del runtime.",
    )
    parser.add_argument(
        "--guardar-respuestas",
        action="store_true",
        help="Escribe la respuesta cruda de cada generación en salida/respuestas-crudas/ (directorio ignorado por Git).",
    )
    parser.add_argument("--evidencia", default="HU011-V3-SPIKE")
    parser.add_argument(
        "--confirm-live-llm",
        action="store_true",
        required=True,
        help="Opt-in explícito: este runner invoca un modelo local real.",
    )
    args = parser.parse_args()

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "data" / "actividades_sinteticas.csv"
    fuente = CsvFuenteSolicitudes(dataset)
    contrato = CONTRATOS[args.contrato]
    transform = _transformacion(args.variante_prompt)

    generator = GeneradorMedicion(
        modelo=args.modelo,
        base_url=args.base_url,
        timeout_s=args.timeout,
        num_predict=args.num_predict,
        temperature=args.temperature,
        format_mode=args.format,
        format_schema=contrato.schema,
        transform_prompt=transform,
    )

    resultados: list[dict[str, object]] = []
    indice_captura = 0
    repeticiones = max(1, args.repeticiones)
    for repeticion in range(repeticiones):
        for id_solicitud, estado_esperado in CASOS:
            for canal in CANALES:
                espera_generacion = estado_esperado == "PENDIENTE_VALIDACION"
                generator_caso = generator if espera_generacion else GeneradorQueNoDebeInvocarse()
                inicio = time.perf_counter()
                resultado = procesar_post_estructurado(
                    fuente=fuente,
                    id_solicitud=id_solicitud,
                    canal=canal,
                    directorio_salida=salida / "casos" / f"rep{repeticion}" / id_solicitud / canal,
                    generator=generator_caso,
                    contrato=contrato,
                )
                latencia_s = time.perf_counter() - inicio
                registro = json.loads(
                    resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
                )
                captura = (
                    generator.capturas[indice_captura]
                    if espera_generacion and indice_captura < len(generator.capturas)
                    else None
                )
                if espera_generacion:
                    indice_captura += 1
                errores = list(registro.get("validation_errors") or [])
                detalle = None
                if espera_generacion and captura is not None:
                    detalle = _literales_disparadores(captura.contenido, _fila(fuente, id_solicitud))
                    if args.guardar_respuestas:
                        destino = (
                            salida
                            / "respuestas-crudas"
                            / f"rep{repeticion}-{id_solicitud}-{canal}.txt"
                        )
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        destino.write_text(captura.contenido, encoding="utf-8")
                resultados.append(
                    {
                        "repeticion": repeticion,
                        "id_solicitud": id_solicitud,
                        "canal": canal,
                        "llm_invoked": espera_generacion,
                        "expected_state": estado_esperado,
                        "observed_state": resultado.estado,
                        "conformant": (
                            resultado.estado == estado_esperado
                            and (resultado.borrador_path is not None) == espera_generacion
                        ),
                        "draft_created": resultado.borrador_path is not None,
                        "latency_s": round(latencia_s, 6),
                        "resultado": registro.get("resultado"),
                        "validation_errors": errores,
                        "categorias": sorted(
                            {CATEGORIA_POR_CODIGO.get(c, "otro") for c in errores}
                        ),
                        "reglas_politica": sorted(
                            {CODIGO_A_REGLA[c] for c in errores if c in CODIGO_A_REGLA}
                        ),
                        "eval_count": captura.eval_count if captura else None,
                        "done_reason": captura.done_reason if captura else None,
                        "input_sha256": registro.get("input_hash"),
                        "output_sha256": registro.get("output_hash"),
                        "correlation_id": resultado.correlation_id,
                        "detalle": detalle,
                    }
                )
                print(
                    json.dumps(
                        {
                            "caso": f"rep{repeticion}/{id_solicitud}/{canal}",
                            "estado": resultado.estado,
                            "errores": errores,
                            "latencia_s": round(latencia_s, 3),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    flush=True,
                )

    generados = [caso for caso in resultados if caso["llm_invoked"]]
    negativos = [caso for caso in resultados if not caso["llm_invoked"]]
    conteo_codigos: dict[str, int] = {}
    conteo_reglas: dict[str, int] = {}
    conteo_categorias: dict[str, int] = {}
    for caso in generados:
        for codigo in caso["validation_errors"]:
            conteo_codigos[codigo] = conteo_codigos.get(codigo, 0) + 1
        for regla in caso["reglas_politica"]:
            conteo_reglas[regla] = conteo_reglas.get(regla, 0) + 1
        for categoria in caso["categorias"]:
            conteo_categorias[categoria] = conteo_categorias.get(categoria, 0) + 1

    latencias = [caso["latency_s"] for caso in generados]
    resumen = {
        "schema_version": "medicion_conformidad_v3_spike",
        "evidence_id": args.evidencia,
        "evidence_kind": "DIAGNOSTICO_CONFORMIDAD_LIVE_LLM_LOCAL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": "SINTETICA",
        "generator_kind": "OLLAMA_LOCAL_SPIKE",
        "creative_contract_version": contrato.contract_version,
        "creative_mode": (
            "CATALOGO_CERRADO" if contrato.catalogo_por_canal else "REDACCION_LIBRE"
        ),
        "model": args.modelo,
        "format_mode": args.format,
        "format_schema_sha256": generator.format_schema_hash,
        "temperature": args.temperature,
        "num_predict": args.num_predict,
        "timeout_s": args.timeout,
        "variante_prompt": args.variante_prompt,
        "repeticiones": repeticiones,
        "human_review": "PENDIENTE",
        "institutional_quality_assessed": False,
        "seu_validated": False,
        "published": False,
        "trl3_claimed": False,
        "totals": {
            "channel_executions": len(resultados),
            "llm_generations_attempted": len(generados),
            "llm_generations_accepted": sum(caso["conformant"] for caso in generados),
            "negative_cases": len(negativos),
            "negative_cases_conformant": sum(caso["conformant"] for caso in negativos),
            "drafts_created": sum(caso["draft_created"] for caso in resultados),
            "latency_min_s": min(latencias) if latencias else None,
            "latency_max_s": max(latencias) if latencias else None,
            "eval_count_max": max(
                (caso["eval_count"] for caso in generados if caso["eval_count"]),
                default=None,
            ),
            "conteo_por_categoria": conteo_categorias,
            "conteo_por_codigo_gate": dict(
                sorted(conteo_codigos.items(), key=lambda item: -item[1])
            ),
            "conteo_por_regla_politica": dict(
                sorted(conteo_reglas.items(), key=lambda item: -item[1])
            ),
        },
        "cases": resultados,
        "limitations": [
            "Los datos son sintéticos y las políticas de canal son provisionales.",
            "Las variantes de prompt son instrumentación del spike: no modifican la plantilla versionada ni el contrato.",
            "El transporte del medidor replica el adapter con parámetros abiertos; no cambia el código de producción.",
            "Las respuestas crudas se guardan aparte, en un directorio ignorado por Git.",
            "Esta medición no acredita el Gate G2, TRL 3 ni validación SEU.",
        ],
    }
    resumen_path = salida / "medicion-v3.json"
    resumen_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    aceptadas = resumen["totals"]["llm_generations_accepted"]
    intentadas = resumen["totals"]["llm_generations_attempted"]
    print(
        json.dumps(
            {
                "status": "OK" if aceptadas == intentadas else "NO_CONFORME",
                "aceptadas": f"{aceptadas}/{intentadas}",
                "conteo_por_codigo_gate": conteo_codigos,
                "summary_ref": str(resumen_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _fila(fuente: CsvFuenteSolicitudes, id_solicitud: str) -> dict[str, str]:
    """Lee la fila fuente para el diagnóstico de fuga de hechos."""

    try:
        cruda = fuente.obtener(id_solicitud)
    except Exception:
        return {}
    return {campo: str(valor) for campo, valor in cruda.items()} if isinstance(cruda, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
