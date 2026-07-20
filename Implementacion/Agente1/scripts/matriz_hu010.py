#!/usr/bin/env python3
"""Ejecuta la matriz contractual simulada HU-010 sin depender de un LLM."""

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

from agente1 import FakeGenerator, procesar_fila_csv  # noqa: E402


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
        description="Ejecuta cinco casos de conformidad contractual simulada HU-010."
    )
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "data" / "actividades_sinteticas.csv"
    resultados: list[dict[str, object]] = []

    for caso_id, perfil, estado_esperado in CASOS:
        caso_dir = salida / "casos" / caso_id
        golden_path = ROOT / "golden" / f"{caso_id}.md"
        if estado_esperado == "PENDIENTE_VALIDACION":
            golden = golden_path.read_text(encoding="utf-8")
            contenido = golden.removeprefix("# BORRADOR — NO PUBLICAR\n\n").strip()
            generator = FakeGenerator(contenido)
        else:
            golden = None
            generator = GeneratorQueNoDebeInvocarse()

        resultado = procesar_fila_csv(
            csv_path=dataset,
            id_solicitud=caso_id,
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
            raise RuntimeError(f"estado inesperado para {caso_id}")
        if registro["resultado"] != resultado_esperado:
            raise RuntimeError(f"resultado inesperado para {caso_id}")
        if estado_esperado == "PENDIENTE_VALIDACION":
            if not borrador_creado or resultado.borrador_path is None:
                raise RuntimeError(f"falta borrador para {caso_id}")
            if resultado.borrador_path.read_text(encoding="utf-8") != golden:
                raise RuntimeError(f"el borrador no coincide con el golden de {caso_id}")
        elif borrador_creado:
            raise RuntimeError(f"un caso incompleto creó borrador para {caso_id}")

        resultados.append(
            {
                "id_solicitud": caso_id,
                "fixture_profile": perfil,
                "expected_state": estado_esperado,
                "observed_state": resultado.estado,
                "expected_result": resultado_esperado,
                "observed_result": registro["resultado"],
                "correlation_id": resultado.correlation_id,
                "draft_created": borrador_creado,
                "input_sha256": registro["input_hash"],
                "output_sha256": registro["output_hash"],
                "golden_sha256": _sha256(golden_path) if golden is not None else None,
            }
        )

    resumen = {
        "schema_version": "matriz_conformidad_hu010_v1",
        "evidence_kind": "CONFORMIDAD_CONTRACTUAL_SIMULADA",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": _base_commit(),
        "implementation_scope_matches_base_commit": _scope_limpio(),
        "data_origin": "SIMULADA",
        "human_review": "PENDIENTE",
        "institutional_quality_assessed": False,
        "trl3_claimed": False,
        "artifact_hashes": {
            "dataset_sha256": _sha256(dataset),
            "prompt_sha256": _sha256(ROOT / "src" / "agente1" / "prompts" / "gacetilla_v2.txt"),
            "contract_sha256": _sha256(
                ROOT / "src" / "agente1" / "contracts" / "gacetilla_input_v1.schema.json"
            ),
            "runner_sha256": _sha256(Path(__file__)),
        },
        "totals": {
            "cases": len(resultados),
            "pending_validation": sum(
                caso["observed_state"] == "PENDIENTE_VALIDACION" for caso in resultados
            ),
            "incomplete": sum(caso["observed_state"] == "INCOMPLETA" for caso in resultados),
        },
        "cases": resultados,
        "limitations": [
            "La matriz usa datos simulados y un generador fake determinista.",
            "La conformidad mecánica no evalúa calidad institucional, tono ni verdad semántica.",
            "No existe validación humana o SEU registrada para estas salidas.",
            "La matriz no evalúa performance ni acredita TRL 3.",
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
    lineas = path.read_text(encoding="utf-8").splitlines()
    return json.loads(lineas[-1])


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
