"""Contrato público de la CLI: códigos de salida por estado, forma estable del
JSON de stdout, exclusión mutua de generadores y rechazo de las banderas de
post cuando el tipo es gacetilla."""

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


def contenido_golden_syn001() -> str:
    documento = (ROOT / "golden" / "SYN-001.md").read_text(encoding="utf-8")
    return documento.removeprefix("# BORRADOR — NO PUBLICAR\n\n").strip()


def salida_conforme_cli() -> str:
    return (
        "## TÍTULO\nActividad sintética CLI\n\n"
        "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-08\n"
        "Organiza: Equipo de prueba\nLugar: Aula ficticia\n\n"
        "## CONTACTO\npruebas@example.invalid\n\n"
        "## BAJADA\nBorrador sintético para validar la CLI.\n\n"
        "## CUERPO\nEsta actividad requiere revisión humana antes de publicarse."
    )


def salida_post_v2_cli() -> str:
    return json.dumps(
        {
            "gancho": "Una propuesta para aprender y compartir.",
            "prosa": "Sumate a una experiencia pensada para la comunidad.",
            "cta": "Consultá los datos y participá.",
            "hashtags": ["#Aprender", "#Comunidad"],
        },
        ensure_ascii=False,
    )


@contextmanager
def servidor_ollama(*, cuerpo: bytes, status: int = 200):
    solicitudes: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            longitud = int(self.headers["Content-Length"])
            solicitudes.append(json.loads(self.rfile.read(longitud)))
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
        yield f"http://{host}:{puerto}", solicitudes
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
            salida_conforme_cli(),
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
    ).endswith("publicarse.\n")


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
            contenido_golden_syn001(),
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
    assert respuesta["borrador"] is None
    assert respuesta["correlation_id"]
    assert respuesta["error"] == "Solicitud inválida o inexistente"
    assert respuesta["estado"] == "INVALIDA"
    assert respuesta["log"]
    assert "secreto" not in proceso.stdout
    registro = Path(respuesta["log"]).read_text(encoding="utf-8")
    assert "../secreto" not in registro


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
    assert respuesta["correlation_id"]
    assert respuesta["log"]
    assert "SYN-NO-EXISTE" not in proceso.stdout
    registro = Path(respuesta["log"]).read_text(encoding="utf-8")
    assert "SYN-NO-EXISTE" not in registro


def test_cli_ollama_procesa_con_el_adapter_local(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    cuerpo = json.dumps({"response": contenido_golden_syn001(), "done": True}).encode()

    with servidor_ollama(cuerpo=cuerpo) as (base_url, solicitudes):
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
                "--ollama-num-predict",
                "144",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=entorno,
        )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "PENDIENTE_VALIDACION"
    assert Path(respuesta["borrador"]).read_text(encoding="utf-8") == (
        ROOT / "golden" / "SYN-001.md"
    ).read_text(encoding="utf-8")
    registro = json.loads(Path(respuesta["log"]).read_text(encoding="utf-8"))
    assert registro["modelo"] == "llama3.2:3b"
    assert registro["num_predict"] == 144
    assert solicitudes[0]["options"] == {"num_predict": 144, "temperature": 0}


def test_cli_ollama_fallida_no_filtra_error_remoto_ni_crea_borrador(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    cuerpo = b'{"error":"secreto@example.invalid"}'

    with servidor_ollama(cuerpo=cuerpo, status=500) as (base_url, _):
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


def test_cli_ollama_rechaza_num_predict_fuera_de_rango(tmp_path):
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
            "--ollama-model",
            "llama3.2:3b",
            "--ollama-num-predict",
            "513",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 2
    assert proceso.stderr == ""
    assert json.loads(proceso.stdout)["estado"] == "INVALIDA"
    assert not (tmp_path / "salida").exists()


def test_cli_post_mantiene_gacetilla_default_y_exige_canal(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")

    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--tipo",
            "post",
            "--canal",
            "linkedin",
            "--post-version",
            "text-v1",
            "--csv",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--id-solicitud",
            "SYN-001",
            "--salida",
            str(tmp_path / "salida"),
            "--fake-output",
            (
                "CANAL: linkedin\nTEXTO:\nTaller sintético de vinculación, 2026-08-05, "
                "Equipo de prueba, pruebas@example.invalid, Aula de prueba.\n"
                "HASHTAGS:\n#Actividad #Extension"
            ),
            "--post-max-chars",
            "200",
            "--post-max-hashtags",
            "2",
            "--post-min-hashtags",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert respuesta["estado"] == "PENDIENTE_VALIDACION"
    assert Path(respuesta["borrador"]).name == "SYN-001-linkedin.md"

    sin_canal = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--tipo",
            "post",
            "--csv",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--id-solicitud",
            "SYN-001",
            "--salida",
            str(tmp_path / "sin-canal"),
            "--fake-output",
            "no debe usarse",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )
    assert sin_canal.returncode == 2
    assert json.loads(sin_canal.stdout)["estado"] == "INVALIDA"


def test_cli_post_usa_structured_v2_por_default_seguro(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "agente1",
            "--tipo",
            "post",
            "--canal",
            "instagram",
            "--csv",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--id-solicitud",
            "SYN-001",
            "--salida",
            str(tmp_path / "salida-v2"),
            "--fake-output",
            salida_post_v2_cli(),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )

    assert proceso.returncode == 0, proceso.stderr
    respuesta = json.loads(proceso.stdout)
    assert Path(respuesta["borrador"]).name == "SYN-001-instagram-v2.md"
    registro = json.loads(Path(respuesta["log"]).read_text(encoding="utf-8"))
    assert registro["output_contract_version"] == "post_creative_output_v2"
    assert registro["renderer_version"] == "post_deterministic_renderer_v2"


def test_cli_post_v2_ollama_envia_schema_exacto_y_audita_solo_hash(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    cuerpo = json.dumps({"response": salida_post_v2_cli(), "done": True}).encode()
    schema_path = ROOT / "src" / "agente1" / "contracts" / "post_creative_output_v2.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    with servidor_ollama(cuerpo=cuerpo) as (base_url, solicitudes):
        proceso = subprocess.run(
            [
                sys.executable,
                "-m",
                "agente1",
                "--tipo",
                "post",
                "--canal",
                "instagram",
                "--csv",
                str(ROOT / "data" / "actividades_sinteticas.csv"),
                "--id-solicitud",
                "SYN-001",
                "--salida",
                str(tmp_path / "salida-v2-ollama"),
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
    assert solicitudes[0]["format"] == schema
    assert solicitudes[0]["options"]["temperature"] == 0
    respuesta = json.loads(proceso.stdout)
    log_serializado = Path(respuesta["log"]).read_text(encoding="utf-8")
    registro = json.loads(log_serializado)
    assert registro["generation_format"] == "json_schema"
    assert len(registro["format_schema_hash"]) == 64
    assert '"properties"' not in log_serializado
    assert "x-provisional-creative-catalog-by-channel" not in log_serializado


def test_cli_gacetilla_rechaza_flags_exclusivos_de_post(tmp_path):
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    flags = (
        ("--canal", "instagram"),
        ("--post-version", "text-v1"),
        ("--post-max-chars", "1000"),
        ("--post-min-hashtags", "1"),
        ("--post-max-hashtags", "10"),
    )

    for indice, flag in enumerate(flags):
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
                str(tmp_path / str(indice)),
                "--fake-output",
                contenido_golden_syn001(),
                *flag,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=entorno,
        )
        assert proceso.returncode == 2
        assert json.loads(proceso.stdout)["estado"] == "INVALIDA"
        assert not (tmp_path / str(indice)).exists()
