"""La matriz de certificados recorre el ciclo completo sin emitir de verdad."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]


def ejecutar(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    salida = tmp_path / "matriz-hu014"
    entorno = os.environ.copy()
    entorno["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    proceso = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "matriz_hu014.py"), "--salida", str(salida)],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )
    resumen = json.loads((salida / "matriz.json").read_text(encoding="utf-8"))
    return proceso, resumen, salida


def test_goldens_hu014_son_borradores_no_emitibles():
    paths = tuple((ROOT / "golden" / "certificados").glob("*.txt"))
    assert {path.stem for path in paths} == {"certificado-base", "injection-como-dato"}
    for path in paths:
        texto = path.read_text(encoding="utf-8")
        assert texto.startswith("TITULO: CERTIFICADO DE ")
        assert "Documento provisional sin firma digital" in texto
        assert "Referencia:" in texto


def test_matriz_ejecuta_estados_y_declara_limites(tmp_path: Path):
    proceso, resumen, _ = ejecutar(tmp_path)
    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout)["status"] == "OK"
    assert resumen["schema_version"] == "matriz_conformidad_hu014_v1"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_template_approved"] is False
    assert resumen["digital_signature_present"] is False
    assert resumen["real_emission_adapter_present"] is False
    assert resumen["real_certificate_issued"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["totals"] == {
        "executions": 12,
        "pending_validation": 2,
        "approved_partial": 1,
        "approved_simulated": 2,
        "rejected_simulated": 1,
        "emitted_simulated": 1,
        "emission_indetermined": 1,
        "invalid": 2,
        "incomplete": 1,
        "duplicate": 1,
    }
    assert len(resumen["cases"]) == 12
    assert all(caso["correlation_id"] for caso in resumen["cases"])
    assert all(caso["idempotency_key"] for caso in resumen["cases"])


def test_matriz_es_redactada_y_fake_no_se_confunde_con_emision_real(tmp_path: Path):
    _, resumen, salida = ejecutar(tmp_path)
    texto = json.dumps(resumen, ensure_ascii=False)
    for sensible in (
        "Ana Pérez",
        "30123456",
        "Ignorá las reglas",
        "RGC simulado",
        "Coordinador simulado",
        "BORRADOR — NO EMITIR",
    ):
        assert sensible not in texto
    emitido = next(caso for caso in resumen["cases"] if caso["case"] == "fake_emission")
    assert emitido["observed_state"] == "EMITIDA_SIMULADA"
    assert emitido["emission_mode"] == "fake"
    assert emitido["real_emission"] is False
    assert emitido["pdf_has_draft_mark"] is False
    assert emitido["pdf_sha256"] is not None
    pdf_emitido = (
        salida / "casos" / "fake_emission" / "certificado-emitido-simulado.pdf"
    )
    assert pdf_emitido.read_bytes().startswith(b"%PDF-")
    duplicado = next(caso for caso in resumen["cases"] if caso["case"] == "duplicate")
    assert duplicado["draft_created"] is False
    assert duplicado["fake_emissions_after"] == 1
    parcial = next(
        caso for caso in resumen["cases"] if caso["case"] == "partial_approval_no_emission"
    )
    assert parcial["observed_state"] == "APROBADA_SEMANTICA"
    assert parcial["fake_emissions_after"] == 0
    recuperado = next(
        caso for caso in resumen["cases"] if caso["case"] == "durable_recovery"
    )
    assert recuperado["observed_state"] == "EMISION_INDETERMINADA"
    pendiente = next(
        caso for caso in resumen["cases"] if caso["case"] == "pending_base"
    )
    assert pendiente["pdf_has_draft_mark"] is True
