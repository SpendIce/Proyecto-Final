#!/usr/bin/env python3
"""Matriz live HU-011 JSON Schema v4 con cobertura ampliada.

Amplía el corte v4 de dos registros a las cinco actividades sintéticas en ambos
canales. A diferencia de la matriz fake, este runner NO aborta ante una salida
no conforme: registra el resultado observado para poder medir la tasa real de
conformidad del modelo local. Requiere un Ollama ya iniciado en loopback.

No publica, no envía y no comparte contenido. Toda salida exitosa conserva
`BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import OllamaGenerator  # noqa: E402
from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.posts import (  # noqa: E402
    CONTRATO_CREATIVO_V2,
    CONTRATO_CREATIVO_V3,
    procesar_post_estructurado,
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


class GeneratorQueNoDebeInvocarse:
    """Centinela: un caso incompleto debe rechazarse antes de invocar al LLM."""

    modelo = "centinela-no-invocar"
    num_predict = None

    def generar(self, prompt: str) -> str:
        raise AssertionError("un caso incompleto no debe invocar al generador")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta la matriz live HU-011 v4 contra un Ollama local."
    )
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--num-predict", type=int, default=112)
    parser.add_argument(
        "--contrato",
        choices=sorted(CONTRATOS),
        default="v2",
        help="v2 selecciona de un catálogo cerrado; v3 deja que el modelo redacte.",
    )
    parser.add_argument(
        "--evidencia",
        default="HU011-OLLAMA-JSON-SCHEMA-V4-COBERTURA-AMPLIADA",
        help="Identificador opaco del corte de evidencia.",
    )
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
    resultados: list[dict[str, object]] = []
    schema_hash: str | None = None
    contrato = CONTRATOS[args.contrato]

    for id_solicitud, estado_esperado in CASOS:
        for canal in CANALES:
            espera_generacion = estado_esperado == "PENDIENTE_VALIDACION"
            if espera_generacion:
                generator = OllamaGenerator(
                    modelo=args.modelo,
                    base_url=args.base_url,
                    timeout_s=args.timeout,
                    num_predict=args.num_predict,
                    format_schema=contrato.schema,
                )
                schema_hash = generator.format_schema_hash
            else:
                generator = GeneratorQueNoDebeInvocarse()

            inicio = time.perf_counter()
            resultado = procesar_post_estructurado(
                fuente=fuente,
                id_solicitud=id_solicitud,
                canal=canal,
                directorio_salida=salida / "casos" / id_solicitud / canal,
                generator=generator,
                contrato=contrato,
            )
            latencia_s = time.perf_counter() - inicio

            registro = json.loads(
                resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
            )
            conforme = (
                resultado.estado == estado_esperado
                and (resultado.borrador_path is not None) == espera_generacion
            )
            resultados.append(
                {
                    "id_solicitud": id_solicitud,
                    "canal": canal,
                    "llm_invoked": espera_generacion,
                    "expected_state": estado_esperado,
                    "observed_state": resultado.estado,
                    "conformant": conforme,
                    "draft_created": resultado.borrador_path is not None,
                    "latency_s": round(latencia_s, 6),
                    "input_sha256": registro.get("input_hash"),
                    "output_sha256": registro.get("output_hash"),
                    "validation_errors": registro.get("validation_errors"),
                    "output_contract_version": registro.get("output_contract_version"),
                    "renderer_version": registro.get("renderer_version"),
                    "prompt_version": registro.get("prompt_version"),
                    "correlation_id": resultado.correlation_id,
                }
            )
            print(
                json.dumps(
                    {
                        "caso": f"{id_solicitud}/{canal}",
                        "estado": resultado.estado,
                        "conforme": conforme,
                        "latencia_s": round(latencia_s, 3),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )

    generados = [caso for caso in resultados if caso["llm_invoked"]]
    negativos = [caso for caso in resultados if not caso["llm_invoked"]]
    latencias = [caso["latency_s"] for caso in generados]

    resumen = {
        "schema_version": "matriz_conformidad_hu011_live_v4",
        "evidence_id": args.evidencia,
        "evidence_kind": "CONFORMIDAD_MECANICA_LIVE_LLM_LOCAL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": "SINTETICA",
        "generator_kind": "OLLAMA_LOCAL_JSON_SCHEMA",
        "creative_contract_version": contrato.contract_version,
        "creative_mode": (
            "CATALOGO_CERRADO" if contrato.catalogo_por_canal else "REDACCION_LIBRE"
        ),
        "model": args.modelo,
        "format_mode": "json_schema",
        "format_schema_sha256": schema_hash,
        "temperature": 0,
        "num_predict": args.num_predict,
        "timeout_s": args.timeout,
        "human_review": "PENDIENTE",
        "institutional_quality_assessed": False,
        "seu_validated": False,
        "published": False,
        "trl3_claimed": False,
        "artifact_hashes": {
            "dataset_sha256": _sha256(dataset),
            "output_contract_sha256": _sha256(
                ROOT / "src" / "agente1" / "contracts" / "post_creative_output_v2.schema.json"
            ),
            "renderer_source_sha256": _sha256(ROOT / "src" / "agente1" / "posts.py"),
            "prompt_sha256_by_channel": {
                canal: _sha256(
                    ROOT / "src" / "agente1" / "prompts" / f"post_{canal}_structured_v2.txt"
                )
                for canal in CANALES
            },
        },
        "totals": {
            "activities": len(CASOS),
            "channel_executions": len(resultados),
            "llm_generations_attempted": len(generados),
            "llm_generations_accepted": sum(caso["conformant"] for caso in generados),
            "negative_cases": len(negativos),
            "negative_cases_conformant": sum(caso["conformant"] for caso in negativos),
            "drafts_created": sum(caso["draft_created"] for caso in resultados),
            "latency_min_s": min(latencias) if latencias else None,
            "latency_max_s": max(latencias) if latencias else None,
        },
        "cases": resultados,
        "limitations": [
            "Los datos son sintéticos y las políticas de canal son provisionales.",
            "Las latencias son de un host CPU concreto y no constituyen un SLA.",
            "El gate mecánico no demuestra verdad semántica ni calidad institucional.",
            "No existe validación SEU ni revisión humana registrada.",
            "No se invocaron APIs de redes sociales ni se publicó contenido.",
            "Esta matriz no acredita el Gate G2 ni TRL 3.",
        ],
    }
    resumen_path = salida / "matriz-live.json"
    resumen_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    aceptadas = resumen["totals"]["llm_generations_accepted"]
    intentadas = resumen["totals"]["llm_generations_attempted"]
    negativas_ok = resumen["totals"]["negative_cases_conformant"]
    print(
        json.dumps(
            {
                "status": "OK" if aceptadas == intentadas and negativas_ok == len(negativos) else "NO_CONFORME",
                "aceptadas": f"{aceptadas}/{intentadas}",
                "negativos_conformes": f"{negativas_ok}/{len(negativos)}",
                "summary_ref": "matriz-live.json",
            },
            sort_keys=True,
        )
    )
    return 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
