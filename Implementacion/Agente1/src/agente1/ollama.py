from __future__ import annotations

from http.client import HTTPConnection, HTTPException
from ipaddress import ip_address
import json
import math
import time
from urllib.parse import urlsplit


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_TIMEOUT_S = 25.0
MAX_RESPONSE_BYTES = 1_048_576


class OllamaGenerator:
    def __init__(
        self,
        *,
        modelo: str,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        timeout_s: float = DEFAULT_OLLAMA_TIMEOUT_S,
    ) -> None:
        if not modelo.strip():
            raise ValueError("modelo inválido")
        if not math.isfinite(timeout_s) or not 0 < timeout_s <= 30:
            raise ValueError("timeout debe ser mayor que 0 y menor o igual a 30 segundos")
        self._host, self._port = _validar_base_url(base_url)
        self.modelo = modelo.strip()
        self._timeout_s = timeout_s

    def generar(self, prompt: str) -> str:
        deadline = time.monotonic() + self._timeout_s
        payload = json.dumps(
            {
                "model": self.modelo,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        connection: HTTPConnection | None = None
        try:
            connection = HTTPConnection(
                self._host,
                self._port,
                timeout=_tiempo_restante(deadline),
            )
            connection.request(
                "POST",
                "/api/generate",
                body=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            _ajustar_timeout(connection, deadline)
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                raise _TransportError
            cuerpo = bytearray()
            while len(cuerpo) <= MAX_RESPONSE_BYTES:
                _ajustar_timeout(connection, deadline)
                restante = MAX_RESPONSE_BYTES + 1 - len(cuerpo)
                chunk = response.read1(min(65_536, restante))
                if not chunk:
                    break
                cuerpo.extend(chunk)
        except (HTTPException, OSError, TimeoutError, _TransportError):
            raise RuntimeError("No se pudo contactar al generador local") from None
        finally:
            if connection is not None:
                connection.close()

        if len(cuerpo) > MAX_RESPONSE_BYTES:
            raise RuntimeError("Respuesta inválida del generador local")
        try:
            documento = json.loads(cuerpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError("Respuesta inválida del generador local") from None
        if not isinstance(documento, dict):
            raise RuntimeError("Respuesta inválida del generador local")
        contenido = documento.get("response")
        if (
            "error" in documento
            or documento.get("done") is not True
            or not isinstance(contenido, str)
            or not contenido.strip()
        ):
            raise RuntimeError("Respuesta inválida del generador local")
        return contenido.strip()


class _TransportError(Exception):
    pass


def _validar_base_url(base_url: str) -> tuple[str, int]:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("URL base de Ollama inválida")
    host = parsed.hostname
    if host != "localhost":
        try:
            direccion = ip_address(host)
        except ValueError:
            raise ValueError("URL base de Ollama inválida") from None
        if not direccion.is_loopback:
            raise ValueError("URL base de Ollama inválida")
    try:
        port = parsed.port or 80
    except ValueError:
        raise ValueError("URL base de Ollama inválida") from None
    return host, port


def _tiempo_restante(deadline: float) -> float:
    restante = deadline - time.monotonic()
    if restante <= 0:
        raise TimeoutError
    return restante


def _ajustar_timeout(connection: HTTPConnection, deadline: float) -> None:
    restante = _tiempo_restante(deadline)
    connection.timeout = restante
    if connection.sock is not None:
        connection.sock.settimeout(restante)
