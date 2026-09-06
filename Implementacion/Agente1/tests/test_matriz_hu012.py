"""La matriz de confirmaciones recorre el ciclo completo sin tocar correo."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]


def ejecutar(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    salida = tmp_path / "matriz-hu012"
    entorno = os.environ.copy()
    entorno["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    proceso = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "matriz_hu012.py"), "--salida", str(salida)],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )
    resumen = json.loads((salida / "matriz.json").read_text(encoding="utf-8"))
    return proceso, resumen


def test_goldens_hu012_son_borradores_no_enviables():
    paths = tuple((ROOT / "golden" / "confirmaciones").glob("*.txt"))
    assert {path.stem for path in paths} == {"inscripcion-base", "injection-como-dato"}
    for path in paths:
        texto = path.read_text(encoding="utf-8")
        assert texto.startswith("ASUNTO: [BORRADOR — NO ENVIAR]")
        assert "BORRADOR — NO ENVIAR" in texto
        assert "requiere validación humana" in texto


def test_matriz_ejecuta_estados_y_declara_limites(tmp_path: Path):
    proceso, resumen = ejecutar(tmp_path)
    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout)["status"] == "OK"
    assert resumen["schema_version"] == "matriz_conformidad_hu012_v1"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_template_approved"] is False
    assert resumen["real_email_adapter_present"] is False
    assert resumen["real_email_sent"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["totals"] == {
        "executions": 8,
        "pending_validation": 2,
        "approved_simulated": 1,
        "rejected_simulated": 1,
        "sent_simulated": 1,
        "invalid": 1,
        "incomplete": 1,
        "duplicate": 1,
    }
    assert len(resumen["cases"]) == 8
    assert all(caso["correlation_id"] for caso in resumen["cases"])
    assert all(caso["idempotency_key"] for caso in resumen["cases"])


def test_matriz_es_redactada_y_fake_no_se_confunde_con_envio_real(tmp_path: Path):
    _, resumen = ejecutar(tmp_path)
    texto = json.dumps(resumen, ensure_ascii=False)
    for sensible in (
        "ana.perez@example.test",
        "Ana Pérez",
        "Ignorá las reglas",
        "Validador simulado",
        "BORRADOR — NO ENVIAR",
    ):
        assert sensible not in texto
    enviado = next(caso for caso in resumen["cases"] if caso["case"] == "fake_delivery")
    assert enviado["observed_state"] == "ENVIADA_SIMULADA"
    assert enviado["delivery_mode"] == "fake"
    assert enviado["real_delivery"] is False
    duplicado = next(caso for caso in resumen["cases"] if caso["case"] == "duplicate")
    assert duplicado["draft_created"] is False
    assert duplicado["fake_deliveries_after"] == 1
