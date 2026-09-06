"""Adapter del generador local: sólo acepta loopback, respeta el deadline, exige
`done: true` y rechaza respuestas truncadas, vacías o demasiado grandes."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import time

import pytest

from agente1 import OllamaGenerator
from agente1.ollama import DEFAULT_OLLAMA_TIMEOUT_S, MAX_FORMAT_SCHEMA_BYTES


@contextmanager
def servidor_ollama(*, cuerpo: bytes, status: int = 200):
    solicitudes: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            longitud = int(self.headers["Content-Length"])
            solicitudes.append(
                {
                    "path": self.path,
                    "content_type": self.headers["Content-Type"],
                    "body": self.rfile.read(longitud),
                }
            )
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


@contextmanager
def servidor_ollama_trickle(*, cuerpo: bytes, demora_s: float):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            longitud = int(self.headers["Content-Length"])
            self.rfile.read(longitud)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                for byte in cuerpo:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(demora_s)
            except (BrokenPipeError, ConnectionResetError):
                return

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


def test_ollama_envia_generate_no_streaming_y_devuelve_respuesta():
    cuerpo = json.dumps(
        {"model": "llama3.2:3b", "response": " Borrador local. ", "done": True}
    ).encode()
    with servidor_ollama(cuerpo=cuerpo) as (base_url, solicitudes):
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=5,
        )

        respuesta = generator.generar("PROMPT SECRETO")

    assert respuesta == "Borrador local."
    assert solicitudes[0]["path"] == "/api/generate"
    assert solicitudes[0]["content_type"] == "application/json"
    assert json.loads(solicitudes[0]["body"]) == {
        "model": "llama3.2:3b",
        "options": {"num_predict": 112, "temperature": 0},
        "prompt": "PROMPT SECRETO",
        "stream": False,
    }
    assert generator.modelo == "llama3.2:3b"


@pytest.mark.parametrize("timeout_s", [0, -1, 120.01])
def test_ollama_rechaza_timeout_fuera_del_limite(timeout_s):
    with pytest.raises(ValueError, match="timeout"):
        OllamaGenerator(modelo="llama3.2:3b", timeout_s=timeout_s)


def test_ollama_timeout_default_y_maximo_operativo():
    assert DEFAULT_OLLAMA_TIMEOUT_S == 45
    generator = OllamaGenerator(modelo="llama3.2:3b", timeout_s=120)

    assert generator.modelo == "llama3.2:3b"


@pytest.mark.parametrize("num_predict", [31, 513])
def test_ollama_rechaza_num_predict_fuera_del_rango(num_predict):
    with pytest.raises(ValueError, match="num_predict"):
        OllamaGenerator(modelo="llama3.2:3b", num_predict=num_predict)


def test_ollama_permite_configurar_num_predict():
    cuerpo = json.dumps({"response": "Respuesta válida.", "done": True}).encode()
    with servidor_ollama(cuerpo=cuerpo) as (base_url, solicitudes):
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=5,
            num_predict=128,
        )

        generator.generar("Prompt")

    payload = json.loads(solicitudes[0]["body"])
    assert payload["options"] == {"num_predict": 128, "temperature": 0}


def test_ollama_envia_format_schema_exacto_y_expone_solo_hash():
    schema = {
        "type": "object",
        "properties": {"gancho": {"type": "string"}},
        "required": ["gancho"],
        "additionalProperties": False,
    }
    esperado = json.loads(json.dumps(schema))
    canonico = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    cuerpo = json.dumps({"response": '{"gancho":"ok"}', "done": True}).encode()
    with servidor_ollama(cuerpo=cuerpo) as (base_url, solicitudes):
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=5,
            format_schema=schema,
        )
        schema["properties"] = {"mutado": {"type": "number"}}
        generator.generar("Prompt")

    payload = json.loads(solicitudes[0]["body"])
    assert payload["format"] == esperado
    assert payload["options"]["temperature"] == 0
    assert generator.format_mode == "json_schema"
    assert generator.format_schema_hash == hashlib.sha256(canonico).hexdigest()
    assert not hasattr(generator, "format_schema")


@pytest.mark.parametrize(
    "schema",
    [
        {},
        [],
        {"const": float("nan")},
        {"description": "x" * MAX_FORMAT_SCHEMA_BYTES},
    ],
)
def test_ollama_rechaza_format_schema_invalido_sin_filtrar_contenido(schema):
    with pytest.raises(ValueError) as error:
        OllamaGenerator(modelo="llama3.2:3b", format_schema=schema)

    assert str(error.value) == "format schema inválido"
    assert "description" not in str(error.value)


def test_ollama_rechaza_format_schema_ciclico():
    schema: dict[str, object] = {"type": "object"}
    schema["self"] = schema

    with pytest.raises(ValueError, match="format schema inválido"):
        OllamaGenerator(modelo="llama3.2:3b", format_schema=schema)


@pytest.mark.parametrize(
    "cuerpo",
    [
        b"no es json secreto@example.invalid",
        b'{"done": true}',
        b'{"response": 42, "done": true}',
        b'{"response": "  ", "done": true}',
        b'{"response": "texto"}',
        b'{"response": "texto", "done": false}',
        b'{"response": "texto", "done": true, "error": null}',
        b'{"response": "texto", "done": true, "error": "secreto@example.invalid"}',
    ],
)
def test_ollama_rechaza_respuesta_invalida_sin_filtrar_contenido(cuerpo):
    with servidor_ollama(cuerpo=cuerpo) as (base_url, _):
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=5,
        )

        with pytest.raises(RuntimeError) as error:
            generator.generar("PROMPT SECRETO")

    mensaje = str(error.value)
    assert mensaje == "Respuesta inválida del generador local"
    assert "secreto@example.invalid" not in mensaje
    assert "PROMPT SECRETO" not in mensaje
    assert base_url not in mensaje


def test_ollama_oculta_error_http_y_cuerpo_remoto():
    cuerpo = b'{"error":"modelo privado y secreto@example.invalid"}'
    with servidor_ollama(cuerpo=cuerpo, status=500) as (base_url, _):
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=5,
        )

        with pytest.raises(RuntimeError) as error:
            generator.generar("PROMPT SECRETO")

    mensaje = str(error.value)
    assert mensaje == "No se pudo contactar al generador local"
    assert "secreto@example.invalid" not in mensaje
    assert "PROMPT SECRETO" not in mensaje
    assert base_url not in mensaje


@pytest.mark.parametrize(
    "base_url",
    [
        "https://127.0.0.1:11434",
        "http://example.com:11434",
        "http://192.168.1.10:11434",
        "http://[::2]:11434",
        "http://usuario:clave@localhost:11434",
        "http://localhost:11434/api",
        "http://localhost:11434?secreto=1",
        "http://localhost:11434#fragmento",
    ],
)
def test_ollama_rechaza_base_url_fuera_del_loopback(base_url):
    with pytest.raises(ValueError, match="URL base de Ollama inválida") as error:
        OllamaGenerator(modelo="llama3.2:3b", base_url=base_url)

    assert base_url not in str(error.value)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:11434",
        "http://127.0.0.2:11434",
        "http://[::1]:11434",
    ],
)
def test_ollama_acepta_http_loopback(base_url):
    generator = OllamaGenerator(modelo="llama3.2:3b", base_url=base_url)

    assert generator.modelo == "llama3.2:3b"


def test_ollama_timeout_es_deadline_total_aunque_el_servidor_entregue_bytes():
    cuerpo = json.dumps(
        {"response": "Esta respuesta llega demasiado lentamente.", "done": True}
    ).encode()
    with servidor_ollama_trickle(cuerpo=cuerpo, demora_s=0.02) as base_url:
        generator = OllamaGenerator(
            modelo="llama3.2:3b",
            base_url=base_url,
            timeout_s=0.12,
        )
        inicio = time.monotonic()

        with pytest.raises(RuntimeError) as error:
            generator.generar("PROMPT SECRETO")

        transcurrido = time.monotonic() - inicio

    assert str(error.value) == "No se pudo contactar al generador local"
    assert transcurrido < 0.5
