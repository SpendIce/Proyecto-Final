"""Subcomando `control-pagos`: forma del JSON de stdout, códigos de salida y
rechazo de entradas inválidas, por subproceso como las pruebas de la CLI
principal."""

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
PLAN_NOTEBOOKLM = ROOT / "data" / "plan_pagos_notebooklm_n2.csv"
PADRON_SINTETICO = ROOT / "data" / "padron_pagos_sintetico.csv"


def escribir_eml(directorio: Path, nombre: str, remitente: str, datos: bytes):
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["Subject"] = "Re: Pre-Inscripción NotebookLM Nivel 2"
    mensaje["Date"] = format_datetime(
        datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    )
    mensaje["Message-ID"] = f"<{nombre}@example.test>"
    mensaje.set_content("Adjunto.")
    mensaje.add_attachment(
        datos, maintype="application", subtype="pdf", filename="comprobante.pdf"
    )
    (directorio / nombre).write_bytes(mensaje.as_bytes())


def correr_cli(*args: str) -> subprocess.CompletedProcess:
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "agente1", "control-pagos", *args],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )


def test_control_pagos_informa_cuotas_y_no_asociadas(tmp_path):
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(buzon, "ana.eml", "ana.perez@example.test", b"%PDF-1.4 a")
    escribir_eml(buzon, "desconocido.eml", "nadie@example.test", b"%PDF-1.4 b")

    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(buzon),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "OK"
    assert respuesta["actividad_id"] == "EJEMPLO-NOTEBOOKLM-N2"
    assert respuesta["contrato_plan"] == "plan_pagos_actividad_v1"
    assert respuesta["hoy"] == "2026-09-22"

    preinscriptos = {
        p["id_inscripcion"]: p for p in respuesta["preinscriptos"]
    }
    assert set(preinscriptos) == {"PRE-NBLM2-001", "PRE-NBLM2-002", "PRE-NBLM2-003"}
    ana = preinscriptos["PRE-NBLM2-001"]
    assert ana["cuotas_cubiertas"] == "1 de 1"
    assert ana["detalle"] == "1 con comprobante presentado"
    assert ana["cuotas"][0]["estado"] == "COMPROBANTE_PRESENTADO"
    assert ana["cuotas"][0]["fecha_referencia"] == "2026-09-29"
    assert preinscriptos["PRE-NBLM2-002"]["cuotas"][0]["estado"] == "BONIFICADA"
    assert preinscriptos["PRE-NBLM2-003"]["cuotas_cubiertas"] == "0 de 1"

    assert len(respuesta["respuestas_no_asociadas"]) == 1
    no_asociada = respuesta["respuestas_no_asociadas"][0]
    assert no_asociada["remitente"] == "nadie@example.test"
    assert no_asociada["motivo"] == "remitente_sin_coincidencia"
    # Nada del cuerpo del mensaje viaja a la salida.
    assert "Adjunto." not in proceso.stdout


def test_control_pagos_rechaza_fecha_mal_formada(tmp_path):
    (tmp_path / "buzon").mkdir()
    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "22/09/2026",
    )

    assert proceso.returncode == 2
    # argparse reporta por stderr; stdout no lleva datos.
    assert proceso.stdout == ""


def test_control_pagos_rechaza_plan_inexistente(tmp_path):
    (tmp_path / "buzon").mkdir()
    proceso = correr_cli(
        "--plan", str(tmp_path / "no-existe.csv"),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "entrada_inaccesible"


def test_control_pagos_rechaza_buzon_inexistente(tmp_path):
    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "no-existe"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "buzon_no_encontrado"


def test_control_pagos_rechaza_padron_de_otra_actividad(tmp_path):
    padron = tmp_path / "padron.csv"
    padron.write_text(
        "id_inscripcion,actividad_id,nombre_destinatario,email_destinatario\n"
        "PRE-1,OTRA,Ana,ana@example.test\n",
        encoding="utf-8",
    )
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(padron),
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "padron_actividad_distinta"


def test_control_pagos_rechaza_plan_con_campo_desconocido(tmp_path):
    plan = tmp_path / "plan.csv"
    plan.write_text(
        "campo,valor,procedencia\n"
        "campo_inventado,x,SUPUESTO_TECNICO\n",
        encoding="utf-8",
    )
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--plan", str(plan),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "plan_campo_desconocido"
