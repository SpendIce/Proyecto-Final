"""La matriz de certificados recorre el ciclo completo sin emitir de verdad."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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
    assert {path.stem for path in paths} == {
        "certificado-base",
        "injection-como-dato",
        "certificado-linea",
    }
    for path in paths:
        texto = path.read_text(encoding="utf-8")
        assert texto.startswith("TITULO: CERTIFICADO DE ")
        assert "Documento provisional sin firma digital" in texto
        assert "Referencia:" in texto
    # El golden con línea (#74) muestra la línea descriptiva y las variables
    # del registro interpoladas por la plantilla, nunca escritas por el modelo.
    linea = (ROOT / "golden" / "certificados" / "certificado-linea.txt").read_text(
        encoding="utf-8"
    )
    assert "Modalidad: presencial" in linea
    assert "Carga horaria: 6 horas" in linea


def test_matriz_ejecuta_estados_y_declara_limites(tmp_path: Path):
    proceso, resumen, _ = ejecutar(tmp_path)
    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout)["status"] == "OK"
    assert resumen["schema_version"] == "matriz_conformidad_hu014_v2"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_template_approved"] is False
    assert resumen["digital_signature_present"] is False
    assert resumen["real_emission_adapter_present"] is False
    assert resumen["real_certificate_issued"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["totals"] == {
        "executions": 20,
        "pending_validation": 3,
        "approved_partial": 1,
        "approved_simulated": 2,
        "rejected_simulated": 1,
        "emitted_simulated": 2,
        "emission_indetermined": 1,
        "invalid": 8,
        "incomplete": 1,
        "duplicate": 1,
    }
    assert len(resumen["cases"]) == 20
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


def test_matriz_recorre_el_circuito_de_la_linea_descriptiva(tmp_path: Path):
    """#74: la matriz deja evidencia de las precondiciones de emisión con
    línea —sin registro de decisiones, aprobación parcial, lote sin aprobar
    y lote no declarado— y del caso completo que sí emite."""

    _, resumen, salida = ejecutar(tmp_path)
    por_nombre = {caso["case"]: caso for caso in resumen["cases"]}
    assert por_nombre["linea_pending_draft"]["observed_state"] == (
        "PENDIENTE_VALIDACION"
    )
    assert por_nombre["linea_pending_draft"]["linea_objeto_id"] is not None
    for caso, error in (
        ("linea_gate_invalid", "descriptive_line_invalid"),
        ("linea_gate_multiline", "descriptive_line_invalid"),
        ("linea_no_decisions", "decisions_registry_required"),
        ("linea_partial_approval", "descriptive_line_unapproved"),
        ("linea_batch_unapproved", "closing_batch_unapproved"),
        ("linea_no_batch_declared", "closing_batch_required"),
    ):
        assert por_nombre[caso]["observed_state"] == "INVALIDA"
        assert por_nombre[caso]["observed_result"] == error
        assert por_nombre[caso]["fake_emissions_after"] == 0
    emitida = por_nombre["linea_emission_simulated"]
    assert emitida["observed_state"] == "EMITIDA_SIMULADA"
    assert emitida["emission_mode"] == "fake"
    assert emitida["real_emission"] is False
    assert emitida["pdf_has_draft_mark"] is False
    assert emitida["descriptive_line_hash"] is not None
    assert emitida["linea_objeto_id"] is not None
    assert emitida["closing_batch_id"] == "lote-cierre-syn-001"
    # El PDF simulado queda en la evidencia con la línea dentro.
    pdf = (
        salida
        / "casos"
        / "linea_emission_simulated"
        / "certificado-emitido-simulado.pdf"
    )
    assert pdf.read_bytes().startswith(b"%PDF-")
    # Las decisiones simuladas del Form quedaron en la auditoría del caso.
    procesadas = (
        salida
        / "casos"
        / "linea_emission_simulated"
        / "decisiones"
        / "decisiones-procesadas.jsonl"
    ).read_text(encoding="utf-8")
    assert "apruebo_semantica" in procesadas
    assert "apruebo_utilitaria" in procesadas
    assert "apruebo_lote" in procesadas
