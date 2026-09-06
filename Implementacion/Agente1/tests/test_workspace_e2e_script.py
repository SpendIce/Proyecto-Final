"""El script del runner corre offline por defecto y no sale a la red sin las dos
banderas explícitas."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from agente1.posts import CONTRATO_SALIDA_ESTRUCTURADA


SCRIPT = Path(__file__).parents[1] / "scripts" / "workspace_e2e.py"


def _cargar_script():
    spec = importlib.util.spec_from_file_location("workspace_e2e_script_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class _Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read1(self, size: int) -> bytes:
        body, self._body = self._body, b""
        return body


class _Connection:
    solicitudes: list[dict[str, object]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.sock = None

    def request(self, method: str, target: str, *, body: bytes, headers: dict[str, str]) -> None:
        self.solicitudes.append(json.loads(body))

    def getresponse(self) -> _Response:
        return _Response(json.dumps({"response": '{"gancho":"ok"}', "done": True}).encode())

    def close(self) -> None:
        pass


def test_constructor_y_request_post_live_envian_schema_exacto_temperature_zero(monkeypatch) -> None:
    modulo = _cargar_script()
    _Connection.solicitudes = []
    monkeypatch.setattr("agente1.ollama.HTTPConnection", _Connection)

    generator = modulo._crear_generator_live(tipo="post", modelo="llama3.2:3b")
    generator.generar("prompt")

    payload = _Connection.solicitudes[0]
    assert payload["format"] == CONTRATO_SALIDA_ESTRUCTURADA
    assert payload["options"]["temperature"] == 0
    assert generator.format_mode == "json_schema"
    assert len(generator.format_schema_hash) == 64


def test_constructor_y_request_gacetilla_live_no_envian_format(monkeypatch) -> None:
    modulo = _cargar_script()
    _Connection.solicitudes = []
    monkeypatch.setattr("agente1.ollama.HTTPConnection", _Connection)

    generator = modulo._crear_generator_live(tipo="gacetilla", modelo="llama3.2:3b")
    generator.generar("prompt")

    payload = _Connection.solicitudes[0]
    assert "format" not in payload
    assert payload["options"]["temperature"] == 0
    assert generator.format_mode is None
    assert generator.format_schema_hash is None
