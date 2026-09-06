#!/usr/bin/env python3
"""Ejecuta la matriz contractual simulada HU-011 sin depender de un LLM.

Equivalente de `matriz_hu010.py` para posts: cubre los dos canales y los casos
de rechazo del gate. Al usar el generador fake, cualquier diferencia entre dos
corridas es un cambio del código, nunca variabilidad del modelo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import FakeGenerator, procesar_post  # noqa: E402
from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402


CANALES = ("instagram", "linkedin")
CASOS = (
    ("SYN-001", "complete_with_place", "PENDIENTE_VALIDACION"),
    ("SYN-002", "missing_required_contact", "INCOMPLETA"),
    ("SYN-003", "complete_without_optional_place", "PENDIENTE_VALIDACION"),
    ("SYN-004", "missing_required_date", "INCOMPLETA"),
    ("SYN-005", "complete_remote_without_optional_place", "PENDIENTE_VALIDACION"),
)


class GeneratorQueNoDebeInvocarse:
    modelo = "fake-no-invocar"
    num_predict = None

    def generar(self, prompt: str) -> str:
        raise AssertionError("un caso incompleto no debe invocar al generador")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta la matriz de conformidad contractual simulada HU-011."
    )
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument(
        "--solo-id",
        choices=tuple(caso_id for caso_id, _, _ in CASOS),
        help="Limita la corrida a una actividad; se ejecutan ambos canales.",
    )
    args = parser.parse_args()

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "data" / "actividades_sinteticas.csv"
    fuente = CsvFuenteSolicitudes(dataset)
    casos_seleccionados = tuple(
        caso for caso in CASOS if args.solo_id is None or caso[0] == args.solo_id
    )
    resultados: list[dict[str, object]] = []

    for caso_id, perfil, estado_esperado in casos_seleccionados:
        for canal in CANALES:
            caso_dir = salida / "casos" / caso_id / canal
            golden_path = ROOT / "golden" / "posts" / f"{caso_id}-{canal}.md"
            if estado_esperado == "PENDIENTE_VALIDACION":
                golden = golden_path.read_text(encoding="utf-8")
                contenido = golden.removeprefix("# BORRADOR — NO PUBLICAR\n\n").strip()
                generator = FakeGenerator(contenido)
            else:
                golden = None
                generator = GeneratorQueNoDebeInvocarse()

            resultado = procesar_post(
                fuente=fuente,
                id_solicitud=caso_id,
                canal=canal,
                directorio_salida=caso_dir,
                generator=generator,
            )
            registro = _ultimo_registro(resultado.log_path)
            borrador_creado = resultado.borrador_path is not None
            resultado_esperado = (
                "borrador_generado"
                if estado_esperado == "PENDIENTE_VALIDACION"
                else "datos_incompletos"
            )
            if resultado.estado != estado_esperado:
                raise RuntimeError(f"estado inesperado para {caso_id}/{canal}")
            if registro["resultado"] != resultado_esperado:
                raise RuntimeError(f"resultado inesperado para {caso_id}/{canal}")
            if estado_esperado == "PENDIENTE_VALIDACION":
                if not borrador_creado or resultado.borrador_path is None:
                    raise RuntimeError(f"falta borrador para {caso_id}/{canal}")
                if resultado.borrador_path.read_text(encoding="utf-8") != golden:
                    raise RuntimeError(f"borrador distinto del golden para {caso_id}/{canal}")
            elif borrador_creado:
                raise RuntimeError(f"caso incompleto creó borrador para {caso_id}/{canal}")

            resultados.append(
                {
                    "id_solicitud": caso_id,
                    "canal": canal,
                    "fixture_profile": perfil,
                    "expected_state": estado_esperado,
                    "observed_state": resultado.estado,
                    "expected_result": resultado_esperado,
                    "observed_result": registro["resultado"],
                    "correlation_id": resultado.correlation_id,
                    "draft_created": borrador_creado,
                    "contract_version": registro["contract_version"],
                    "policy_version": registro["policy_version"],
                    "policy_status": registro["policy_status"],
                    "policy_limits": {
                        "max_chars": registro["max_chars"],
                        "min_hashtags": registro["min_hashtags"],
                        "max_hashtags": registro["max_hashtags"],
                    },
                    "prompt_version": registro["prompt_version"],
                    "input_sha256": registro["input_hash"],
                    "output_sha256": registro["output_hash"],
                    "golden_sha256": _sha256(golden_path) if golden is not None else None,
                }
            )

    actividades_completas = sum(
        estado == "PENDIENTE_VALIDACION" for _, _, estado in casos_seleccionados
    )
    actividades_incompletas = len(casos_seleccionados) - actividades_completas
    resumen = {
        "schema_version": "matriz_conformidad_hu011_v1",
        "evidence_kind": "CONFORMIDAD_CONTRACTUAL_SIMULADA",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": _base_commit(),
        "implementation_scope_matches_base_commit": _scope_limpio(),
        "data_origin": "SIMULADA",
        "generator_kind": "FAKE_DETERMINISTA",
        "ollama_evaluated": False,
        "human_review": "PENDIENTE",
        "institutional_quality_assessed": False,
        "trl3_claimed": False,
        "social_media_api_used": False,
        "published": False,
        "artifact_hashes": {
            "dataset_sha256": _sha256(dataset),
            "prompt_sha256_by_channel": {
                canal: _sha256(ROOT / "src" / "agente1" / "prompts" / f"post_{canal}_v1.txt")
                for canal in CANALES
            },
            "contract_sha256": _sha256(
                ROOT / "src" / "agente1" / "contracts" / "post_input_v1.schema.json"
            ),
            "runner_sha256": _sha256(Path(__file__)),
        },
        "totals": {
            "activities": len(casos_seleccionados),
            "channel_executions": len(resultados),
            "complete_activities": actividades_completas,
            "incomplete_activities": actividades_incompletas,
            "pending_validation": sum(
                caso["observed_state"] == "PENDIENTE_VALIDACION" for caso in resultados
            ),
            "incomplete": sum(
                caso["observed_state"] == "INCOMPLETA" for caso in resultados
            ),
        },
        "cases": resultados,
        "limitations": [
            "La matriz usa datos simulados y un generador fake determinista.",
            "La conformidad mecánica no evalúa calidad institucional, tono ni verdad semántica.",
            "Ollama y la performance del LLM no fueron evaluados por esta matriz.",
            "No existe validación humana o SEU registrada para estas salidas.",
            "No se invocaron APIs de redes sociales ni se publicó contenido.",
            "La matriz no acredita TRL 3.",
        ],
    }
    resumen_path = salida / "matriz.json"
    resumen_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"status": "OK", "summary": str(resumen_path)},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _ultimo_registro(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_commit() -> str:
    proceso = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return proceso.stdout.strip()


def _scope_limpio() -> bool:
    proceso = subprocess.run(
        ["git", "status", "--porcelain", "--", "Implementacion/Agente1"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not proceso.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
