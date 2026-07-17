import csv
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread


ROOT = Path(__file__).parents[1]


@contextmanager
def servidor_ollama(*, cuerpo: bytes, status: int = 200):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            longitud = int(self.headers["Content-Length"])
            self.rfile.read(longitud)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, format: str, *args: object) -> None:
            return

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        host, puerto = servidor.server_address
        yield f"http://{host}:{puerto}"
    finally:
        servidor.shutdown()
        thread.join()
        servidor.server_close()


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


def test_cli_ollama_procesa_con_el_adapter_local(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    cuerpo = json.dumps({"response": "Borrador desde Ollama.", "done": True}).encode()

    with servidor_ollama(cuerpo=cuerpo) as base_url:
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
                "--ollama-model",
                "llama3.2:3b",
                "--ollama-base-url",
                base_url,
                "--ollama-timeout",
                "5",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=entorno,
        )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "PENDIENTE_VALIDACION"
    assert Path(respuesta["borrador"]).read_text(encoding="utf-8").endswith(
        "Borrador desde Ollama.\n"
    )
    registro = json.loads(Path(respuesta["log"]).read_text(encoding="utf-8"))
    assert registro["modelo"] == "llama3.2:3b"


def test_cli_ollama_fallida_no_filtra_error_remoto_ni_crea_borrador(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    cuerpo = b'{"error":"secreto@example.invalid"}'

    with servidor_ollama(cuerpo=cuerpo, status=500) as base_url:
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
                "--ollama-model",
                "llama3.2:3b",
                "--ollama-base-url",
                base_url,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=entorno,
        )

    assert proceso.returncode == 2
    assert proceso.stderr == ""
    assert "secreto@example.invalid" not in proceso.stdout
    assert base_url not in proceso.stdout
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "FALLIDA"
    assert respuesta["borrador"] is None
    assert respuesta["error"] == "Falló la generación del borrador"
    assert not (tmp_path / "salida" / "borradores").exists()
    log_serializado = Path(respuesta["log"]).read_text(encoding="utf-8")
    assert "secreto@example.invalid" not in log_serializado
    assert base_url not in log_serializado
