from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
CANALES = {"instagram", "linkedin"}
VALIDOS = {"SYN-001", "SYN-003", "SYN-005"}
INCOMPLETOS = {"SYN-002", "SYN-004"}


def ejecutar(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    salida = tmp_path / "matriz-hu011"
    entorno = os.environ.copy()
    entorno["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    proceso = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "matriz_hu011.py"),
            "--salida",
            str(salida),
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )
    resumen = json.loads((salida / "matriz.json").read_text(encoding="utf-8"))
    return proceso, resumen


def test_goldens_versionan_tres_actividades_por_dos_canales():
    nombres = {path.stem for path in (ROOT / "golden" / "posts").glob("*.md")}

    assert nombres == {
        f"{caso}-{canal}" for caso in VALIDOS for canal in CANALES
    }
    for path in (ROOT / "golden" / "posts").glob("*.md"):
        contenido = path.read_text(encoding="utf-8")
        assert contenido.startswith("# BORRADOR — NO PUBLICAR\n\nCANAL: ")
        assert "\nTEXTO:\n" in contenido
        assert "\nHASHTAGS:\n" in contenido


def test_runner_ejecuta_matriz_completa_y_declara_limites(tmp_path: Path):
    proceso, resumen = ejecutar(tmp_path)

    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout)["status"] == "OK"
    assert resumen["schema_version"] == "matriz_conformidad_hu011_v1"
    assert resumen["evidence_kind"] == "CONFORMIDAD_CONTRACTUAL_SIMULADA"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_quality_assessed"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["social_media_api_used"] is False
    assert resumen["published"] is False
    assert resumen["totals"] == {
        "activities": 5,
        "channel_executions": 10,
        "complete_activities": 3,
        "incomplete_activities": 2,
        "pending_validation": 6,
        "incomplete": 4,
    }
    assert resumen["artifact_hashes"]["dataset_sha256"]
    assert resumen["artifact_hashes"]["contract_sha256"]
    assert set(resumen["artifact_hashes"]["prompt_sha256_by_channel"]) == CANALES


def test_runner_compara_seis_borradores_y_no_genera_para_incompletos(tmp_path: Path):
    _, resumen = ejecutar(tmp_path)
    casos = {(caso["id_solicitud"], caso["canal"]): caso for caso in resumen["cases"]}

    assert set(casos) == {
        (actividad, canal)
        for actividad in VALIDOS | INCOMPLETOS
        for canal in CANALES
    }
    for actividad in VALIDOS:
        for canal in CANALES:
            caso = casos[actividad, canal]
            assert caso["observed_state"] == "PENDIENTE_VALIDACION"
            assert caso["observed_result"] == "borrador_generado"
            assert caso["draft_created"] is True
            assert caso["contract_version"] == "post_input_v1"
            assert caso["policy_version"] == f"post_{canal}_policy_provisional_v1"
            assert caso["policy_status"] == "PROVISIONAL_NO_INSTITUCIONAL"
            assert caso["policy_limits"] == {
                "max_chars": 1000,
                "min_hashtags": 1,
                "max_hashtags": 10,
            }
            assert caso["prompt_version"] == f"post_{canal}_v1"
            assert caso["correlation_id"]
            assert caso["input_sha256"]
            assert caso["output_sha256"] == caso["golden_sha256"]
            assert (
                tmp_path
                / "matriz-hu011"
                / "casos"
                / actividad
                / canal
                / "borradores"
                / f"{actividad}-{canal}.md"
            ).is_file()

    for actividad in INCOMPLETOS:
        for canal in CANALES:
            caso = casos[actividad, canal]
            assert caso["observed_state"] == "INCOMPLETA"
            assert caso["observed_result"] == "datos_incompletos"
            assert caso["draft_created"] is False
            assert caso["output_sha256"] is None
            assert caso["golden_sha256"] is None
            assert not (
                tmp_path / "matriz-hu011" / "casos" / actividad / canal / "borradores"
            ).exists()


def test_resumen_es_redactado_y_no_confunde_fake_con_validacion_llm(tmp_path: Path):
    _, resumen = ejecutar(tmp_path)
    serializado = json.dumps(resumen, ensure_ascii=False)

    for prohibido in (
        "pruebas@example.invalid",
        "contacto@example.invalid",
        "Taller sintético de vinculación",
        "DATOS_JSON_INICIO",
        "TEXTO:\\n",
        "#Taller",
    ):
        assert prohibido not in serializado
    assert resumen["generator_kind"] == "FAKE_DETERMINISTA"
    assert resumen["ollama_evaluated"] is False
    assert any("no evalúa calidad" in limite for limite in resumen["limitations"])


def test_smoke_ejecuta_una_actividad_en_ambos_canales(tmp_path: Path):
    salida = tmp_path / "smoke"
    entorno = os.environ.copy()
    entorno["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    proceso = subprocess.run(
        ["bash", str(ROOT / "scripts" / "smoke_posts.sh"), str(salida)],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 0, proceso.stderr
    assert "smoke HU-011: OK" in proceso.stdout
    resumen = json.loads((salida / "matriz.json").read_text(encoding="utf-8"))
    assert resumen["totals"]["channel_executions"] == 2
    assert resumen["totals"]["pending_validation"] == 2
    assert {caso["canal"] for caso in resumen["cases"]} == CANALES
