from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
CASOS_VALIDOS = {"SYN-001", "SYN-003", "SYN-005"}
CASOS_INCOMPLETOS = {"SYN-002", "SYN-004"}


def ejecutar_matriz(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    salida = tmp_path / "matriz"
    entorno = os.environ.copy()
    entorno["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    proceso = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "matriz_hu010.py"),
            "--salida",
            str(salida),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )
    resumen = json.loads((salida / "matriz.json").read_text(encoding="utf-8"))
    return proceso, resumen


def test_fixtures_definen_tres_validos_dos_incompletos_y_golden_por_valido():
    with (ROOT / "data" / "actividades_sinteticas.csv").open(
        encoding="utf-8", newline=""
    ) as archivo:
        filas = {fila["id_solicitud"]: fila for fila in csv.DictReader(archivo)}

    assert set(filas) == CASOS_VALIDOS | CASOS_INCOMPLETOS
    assert {caso for caso, fila in filas.items() if fila["fecha"] and fila["contacto"]} == (
        CASOS_VALIDOS
    )
    assert {path.stem for path in (ROOT / "golden").glob("SYN-*.md")} == CASOS_VALIDOS
    assert "Lugar:" not in (ROOT / "golden" / "SYN-003.md").read_text(encoding="utf-8")
    assert "Lugar:" not in (ROOT / "golden" / "SYN-005.md").read_text(encoding="utf-8")


def test_runner_ejecuta_cinco_casos_y_expone_frontera_epistemologica(tmp_path):
    proceso, resumen = ejecutar_matriz(tmp_path)

    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout)["status"] == "OK"
    assert resumen["schema_version"] == "matriz_conformidad_hu010_v1"
    assert resumen["evidence_kind"] == "CONFORMIDAD_CONTRACTUAL_SIMULADA"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_quality_assessed"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["base_commit"]
    assert resumen["artifact_hashes"]["dataset_sha256"]
    assert resumen["artifact_hashes"]["prompt_sha256"]
    assert resumen["artifact_hashes"]["contract_sha256"]
    assert resumen["totals"] == {
        "cases": 5,
        "incomplete": 2,
        "pending_validation": 3,
    }


def test_runner_valida_goldens_y_no_genera_borrador_para_incompletos(tmp_path):
    _, resumen = ejecutar_matriz(tmp_path)
    casos = {caso["id_solicitud"]: caso for caso in resumen["cases"]}

    assert set(casos) == CASOS_VALIDOS | CASOS_INCOMPLETOS
    for caso_id in CASOS_VALIDOS:
        caso = casos[caso_id]
        assert caso["expected_state"] == "PENDIENTE_VALIDACION"
        assert caso["observed_state"] == "PENDIENTE_VALIDACION"
        assert caso["observed_result"] == "borrador_generado"
        assert caso["draft_created"] is True
        assert caso["input_sha256"]
        assert caso["output_sha256"]
        assert caso["golden_sha256"] == caso["output_sha256"]
        assert (tmp_path / "matriz" / "casos" / caso_id / "borradores" / f"{caso_id}.md").is_file()

    for caso_id in CASOS_INCOMPLETOS:
        caso = casos[caso_id]
        assert caso["expected_state"] == "INCOMPLETA"
        assert caso["observed_state"] == "INCOMPLETA"
        assert caso["observed_result"] == "datos_incompletos"
        assert caso["draft_created"] is False
        assert caso["output_sha256"] is None
        assert caso["golden_sha256"] is None
        assert not (tmp_path / "matriz" / "casos" / caso_id / "borradores").exists()


def test_resumen_no_copia_datos_contactos_prompts_ni_borradores(tmp_path):
    _, resumen = ejecutar_matriz(tmp_path)
    serializado = json.dumps(resumen, ensure_ascii=False)

    for prohibido in (
        "pruebas@example.invalid",
        "contacto@example.invalid",
        "Taller sintético de vinculación",
        "PROMPT_VERSION:",
        "## CUERPO",
    ):
        assert prohibido not in serializado
    assert "limitations" in resumen
    assert any("no evalúa" in limite for limite in resumen["limitations"])
