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
    assert resumen["schema_version"] == "matriz_conformidad_hu012_v3"
    assert resumen["data_origin"] == "SIMULADA"
    assert resumen["human_review"] == "PENDIENTE"
    assert resumen["institutional_template_approved"] is False
    assert resumen["real_email_adapter_present"] is False
    assert resumen["real_email_sent"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["totals"] == {
        "executions": 9,
        "pending_validation": 2,
        "approved_partial": 1,
        "approved_simulated": 1,
        "rejected_simulated": 1,
        "sent_simulated": 1,
        "invalid": 1,
        "incomplete": 1,
        "duplicate": 1,
    }
    assert len(resumen["cases"]) == 9
    assert all(caso["correlation_id"] for caso in resumen["cases"])
    assert all(caso["idempotency_key"] for caso in resumen["cases"])


def test_matriz_cubre_el_circuito_por_lote_de_pagos(tmp_path: Path):
    proceso, resumen = ejecutar(tmp_path)
    assert proceso.returncode == 0, proceso.stderr
    pagos = resumen["payments"]
    assert pagos["tipo_notificacion"] == "recordatorio_pago"
    assert pagos["circuito"] == "lote"
    assert pagos["entrega"] == "fake"
    assert pagos["audit_clean"] is True
    assert pagos["anticipaciones_default"] == [7, 2]
    assert pagos["estado_pagos"] == "derivado_en_cada_corrida"
    por_caso = {caso["case"]: caso for caso in pagos["cases"]}
    assert pagos["totals"]["executions"] == len(pagos["cases"]) == 13

    plan_7d = por_caso["pagos_planificacion_7d"]
    assert plan_7d["observed_state"] == "PLANIFICADO"
    assert plan_7d["items_count"] == 2
    assert plan_7d["anticipaciones"] == [7]
    assert por_caso["pagos_planificacion_2d"]["anticipaciones"] == [2]

    configurable = por_caso["pagos_anticipacion_configurable"]
    assert configurable["anticipaciones"] == [3]
    vencido = por_caso["pagos_sin_recordatorio_post_vencimiento"]
    assert vencido["observed_state"] == "VACIO"
    assert vencido["items_count"] == 0
    assert vencido["cuotas_vencidas"] == 2

    bonif = por_caso["pagos_bonificacion_no_verificable"]
    assert bonif["items_count"] == 2
    assert bonif["bonificacion_no_verificable"] is True

    assert por_caso["pagos_plantilla_no_aprobada"]["observed_result"] == (
        "template_not_approved"
    )
    assert por_caso["pagos_aprobacion_rol_incorrecto"]["observed_result"] == (
        "approval_invalid"
    )
    assert por_caso["pagos_lista_incompleta"]["observed_result"] == (
        "batch_approval_partial"
    )
    assert por_caso["pagos_items_extra"]["observed_result"] == (
        "batch_item_unknown"
    )
    assert por_caso["pagos_lote_rechazado"]["observed_state"] == "RECHAZADA"

    entrega = por_caso["pagos_entrega_fake"]
    assert entrega["observed_state"] == "ENVIADA_SIMULADA"
    assert entrega["real_delivery"] is False
    assert entrega["fake_deliveries_after"] == 2
    duplicado = por_caso["pagos_idempotencia_segunda_corrida"]
    assert duplicado["observed_state"] == "DUPLICADA"
    assert duplicado["fake_deliveries_after"] == 2
    assert por_caso["pagos_auditoria_sin_datos_sensibles"][
        "observed_state"
    ] == "AUDITORIA_LIMPIA"

    # La matriz serializada no lleva links, datos bancarios ni personas.
    texto = json.dumps(resumen, ensure_ascii=False)
    for sensible in (
        "mp.link",
        "CBU 0000000000000000000001",
        "matilde.ruiz@example.test",
        "Matilde Ruiz",
        "oscar.nunez@example.test",
    ):
        assert sensible not in texto


def test_matriz_es_redactada_y_fake_no_se_confunde_con_envio_real(tmp_path: Path):
    _, resumen = ejecutar(tmp_path)
    texto = json.dumps(resumen, ensure_ascii=False)
    for sensible in (
        "ana.perez@example.test",
        "Ana Pérez",
        "Ignorá las reglas",
        "RGC simulado",
        "Coordinador simulado",
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
    parcial = next(
        caso for caso in resumen["cases"] if caso["case"] == "partial_approval_no_delivery"
    )
    assert parcial["observed_state"] == "APROBADA_SEMANTICA"
    assert parcial["fake_deliveries_after"] == 0
