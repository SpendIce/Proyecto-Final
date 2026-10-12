"""Subcomando `control-pagos`: forma del JSON de stdout, códigos de salida y
rechazo de entradas inválidas, por subproceso como las pruebas de la CLI
principal."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).parents[1]
PLAN_NOTEBOOKLM = ROOT / "data" / "plan_pagos_notebooklm_n2.csv"
PADRON_SINTETICO = ROOT / "data" / "padron_pagos_sintetico.csv"
NOVEDADES_SINTETICAS = ROOT / "data" / "novedades_pago_sinteticas.csv"


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


def test_control_pagos_aplica_novedades_desde_su_csv(tmp_path):
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(buzon, "ana.eml", "ana.perez@example.test", b"%PDF-1.4 a")

    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(buzon),
        "--novedades", str(NOVEDADES_SINTETICAS),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["contrato_novedades"] == "novedades_pago_v1"

    preinscriptos = {
        p["id_inscripcion"]: p for p in respuesta["preinscriptos"]
    }
    ana = preinscriptos["PRE-NBLM2-001"]
    # La confirmación de la Fundación pisa lo derivado del buzón (D1, §6.2).
    assert ana["cuotas"][0]["estado"] == "PAGO_CONFIRMADO"
    assert ana["detalle"] == "1 confirmada por la Fundación"
    # El comprobante presentado queda como rastro, no como estado.
    assert ana["cuotas"][0]["comprobante"]["sha256"]
    assert ana["bonificacion_no_verificable"] is False

    aplicadas = respuesta["novedades_aplicadas"]
    assert [n["tipo"] for n in aplicadas] == [
        "CONFIRMADO_FUNDACION",
        "EMAIL_ALTERNATIVO",
    ]
    assert aplicadas[0]["responsable"] == (
        "Departamento Cursos Complementarios"
    )
    assert respuesta["novedades_con_error"] == []


def test_control_pagos_informa_novedades_con_error_en_el_json(tmp_path):
    novedades = tmp_path / "novedades.csv"
    novedades.write_text(
        "id_inscripcion,tipo,valor,fecha,responsable\n"
        "PRE-INEXISTENTE,CONFIRMADO_FUNDACION,1,2026-09-21,Dep.\n"
        "PRE-NBLM2-001,PAGO_RECIBIDO,1,2026-09-21,Dep.\n",
        encoding="utf-8",
    )
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--novedades", str(novedades),
        "--fecha", "2026-09-22",
    )

    # La corrida produce informe igual: los errores son de la novedad, no de
    # la corrida, y viajan en el JSON para que una persona los corrija.
    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    con_error = respuesta["novedades_con_error"]
    assert [e["motivo"] for e in con_error] == [
        "novedad_inscripcion_desconocida",
        "novedad_tipo_desconocido",
    ]
    assert [e["fila"] for e in con_error] == [2, 3]


def test_control_pagos_rechaza_novedades_inexistentes(tmp_path):
    (tmp_path / "buzon").mkdir()
    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--novedades", str(tmp_path / "no-existe.csv"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "entrada_inaccesible"


def test_control_pagos_sin_novedades_lista_las_secciones_vacias(tmp_path):
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--plan", str(PLAN_NOTEBOOKLM),
        "--padron", str(PADRON_SINTETICO),
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["novedades_aplicadas"] == []
    assert respuesta["novedades_con_error"] == []


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
