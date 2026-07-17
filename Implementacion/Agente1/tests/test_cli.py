import csv
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]


def test_cli_fake_procesa_una_fila_de_forma_reproducible(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_solicitud", "titulo", "descripcion", "fecha", "publico",
                "organiza", "contacto", "fuente", "lugar",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_solicitud": "SYN-CLI-001",
                "titulo": "Actividad sintética CLI",
                "descripcion": "Caso ficticio reproducible.",
                "fecha": "2026-08-08",
                "publico": "Público ficticio",
                "organiza": "Equipo de prueba",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético versionado",
                "lugar": "Aula ficticia",
            }
        )
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")

    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--csv",
            str(csv_path),
            "--id-solicitud",
            "SYN-CLI-001",
            "--salida",
            str(tmp_path / "salida"),
            "--fake-output",
            "Borrador fijo para smoke.",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "PENDIENTE_VALIDACION"
    assert (tmp_path / "salida" / "borradores" / "SYN-CLI-001.md").read_text(
        encoding="utf-8"
    ).endswith("Borrador fijo para smoke.\n")


def test_dataset_versionado_produce_el_golden_por_cli(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")

    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--csv",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--id-solicitud",
            "SYN-001",
            "--salida",
            str(tmp_path / "salida"),
            "--fake-output",
            "La Secretaría de Extensión Universitaria invita a la comunidad universitaria ficticia al Taller sintético de vinculación.",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "PENDIENTE_VALIDACION"
    assert respuesta["borrador"] is not None
    assert Path(respuesta["borrador"]).read_text(encoding="utf-8") == (
        ROOT / "golden" / "SYN-001.md"
    ).read_text(encoding="utf-8")


def test_cli_rechaza_id_invalido_con_json_seguro_sin_traceback(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n",
        encoding="utf-8",
    )
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")

    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--csv",
            str(csv_path),
            "--id-solicitud",
            "../secreto",
            "--salida",
            str(tmp_path / "salida"),
            "--fake-output",
            "No debe usarse.",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 2
    assert proceso.stderr == ""
    respuesta = json.loads(proceso.stdout)
    assert respuesta == {
        "borrador": None,
        "correlation_id": None,
        "error": "Solicitud inválida o inexistente",
        "estado": "INVALIDA",
        "log": None,
    }
    assert "secreto" not in proceso.stdout
    assert not (tmp_path / "salida").exists()


def test_cli_reporta_solicitud_inexistente_con_el_mismo_json_seguro(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")

    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--csv",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--id-solicitud",
            "SYN-NO-EXISTE",
            "--salida",
            str(tmp_path / "salida"),
            "--fake-output",
            "No debe usarse.",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 2
    assert proceso.stderr == ""
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["error"] == "Solicitud inválida o inexistente"
    assert respuesta["correlation_id"] is None
    assert respuesta["log"] is None
    assert "SYN-NO-EXISTE" not in proceso.stdout
    assert not (tmp_path / "salida").exists()
