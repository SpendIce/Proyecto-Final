#!/usr/bin/env python3
"""Matriz fake reproducible para el renderer determinista HU-011 v2.

Ejercita el contrato creativo v2 —el que restringe al modelo a un catálogo
cerrado— alimentando creatividades fijas. Sirve para verificar el renderer y el
gate de hechos sin que intervenga un modelo: si esta matriz falla, el problema
está en el código y no en la generación.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import FakeGenerator  # noqa: E402
from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.posts import procesar_post_estructurado  # noqa: E402


CANALES = ("instagram", "linkedin")
CASOS = (
    ("SYN-001", "PENDIENTE_VALIDACION"),
    ("SYN-002", "INCOMPLETA"),
    ("SYN-003", "PENDIENTE_VALIDACION"),
    ("SYN-004", "INCOMPLETA"),
    ("SYN-005", "PENDIENTE_VALIDACION"),
)
CREATIVIDAD = {
    "instagram": {
        "gancho": "Una propuesta para aprender y compartir.",
        "prosa": "Sumate a una experiencia pensada para la comunidad.",
        "cta": "Consultá los datos y participá.",
        "hashtags": ["#Aprender", "#Comunidad"],
    },
    "linkedin": {
        "gancho": "Una oportunidad para conectar conocimientos.",
        "prosa": "Te invitamos a ser parte de una experiencia de intercambio.",
        "cta": "Conocé los datos y sumate.",
        "hashtags": ["#Conocimiento", "#Comunidad"],
    },
}


class GeneratorQueNoDebeInvocarse:
    modelo = "fake-no-invocar"
    num_predict = None

    def generar(self, prompt: str) -> str:
        raise AssertionError("un caso incompleto no debe invocar al generador")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta la matriz fake HU-011 v2.")
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "data" / "actividades_sinteticas.csv"
    fuente = CsvFuenteSolicitudes(dataset)
    resultados: list[dict[str, object]] = []

    for id_solicitud, estado_esperado in CASOS:
        for canal in CANALES:
            if estado_esperado == "PENDIENTE_VALIDACION":
                generator = FakeGenerator(
                    json.dumps(CREATIVIDAD[canal], ensure_ascii=False, sort_keys=True)
                )
            else:
                generator = GeneratorQueNoDebeInvocarse()
            resultado = procesar_post_estructurado(
                fuente=fuente,
                id_solicitud=id_solicitud,
                canal=canal,
                directorio_salida=salida / "casos" / id_solicitud / canal,
                generator=generator,
            )
            if resultado.estado != estado_esperado:
                raise RuntimeError(f"estado inesperado para {id_solicitud}/{canal}")
            registro = json.loads(resultado.log_path.read_text(encoding="utf-8").splitlines()[-1])
            golden = ROOT / "golden" / "posts_v2" / f"{id_solicitud}-{canal}.md"
            if estado_esperado == "PENDIENTE_VALIDACION":
                if resultado.borrador_path is None:
                    raise RuntimeError(f"falta borrador para {id_solicitud}/{canal}")
                if resultado.borrador_path.read_bytes() != golden.read_bytes():
                    raise RuntimeError(f"borrador distinto del golden para {id_solicitud}/{canal}")
            elif resultado.borrador_path is not None:
                raise RuntimeError(f"caso incompleto creó borrador para {id_solicitud}/{canal}")
            resultados.append(
                {
                    "id_solicitud": id_solicitud,
                    "canal": canal,
                    "expected_state": estado_esperado,
                    "observed_state": resultado.estado,
                    "draft_created": resultado.borrador_path is not None,
                    "input_sha256": registro["input_hash"],
                    "output_sha256": registro["output_hash"],
                    "golden_sha256": _sha256(golden) if golden.exists() else None,
                    "output_contract_version": registro.get("output_contract_version"),
                    "renderer_version": registro.get("renderer_version"),
                    "prompt_version": registro["prompt_version"],
                }
            )

    resumen = {
        "schema_version": "matriz_conformidad_hu011_structured_v2",
        "evidence_kind": "CONFORMIDAD_CONTRACTUAL_SIMULADA",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": "SIMULADA",
        "generator_kind": "FAKE_DETERMINISTA",
        "human_review": "PENDIENTE",
        "institutional_quality_assessed": False,
        "ollama_evaluated": False,
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
            "pending_validation": sum(
                caso["observed_state"] == "PENDIENTE_VALIDACION" for caso in resultados
            ),
            "incomplete": sum(caso["observed_state"] == "INCOMPLETA" for caso in resultados),
        },
        "cases": resultados,
        "limitations": [
            "La matriz usa datos simulados y creatividad fake determinista.",
            "El gate léxico conservador no demuestra verdad semántica ni calidad institucional.",
            "No se evaluó Ollama ni se registró validación humana o SEU.",
            "No se invocaron APIs de redes sociales ni se publicó contenido.",
            "La matriz no acredita TRL 3.",
        ],
    }
    resumen_path = salida / "matriz.json"
    resumen_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "OK", "summary_ref": "matriz.json"}, sort_keys=True))
    return 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
