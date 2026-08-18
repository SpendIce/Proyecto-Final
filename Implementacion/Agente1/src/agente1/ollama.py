from __future__ import annotations

from http.client import HTTPConnection, HTTPException
from ipaddress import ip_address
import hashlib
import json
import math
import time
from urllib.parse import urlsplit


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_TIMEOUT_S = 45.0
MAX_OLLAMA_TIMEOUT_S = 120.0
DEFAULT_OLLAMA_NUM_PREDICT = 112
MIN_OLLAMA_NUM_PREDICT = 32
MAX_OLLAMA_NUM_PREDICT = 512
MAX_RESPONSE_BYTES = 1_048_576
MAX_FORMAT_SCHEMA_BYTES = 65_536


class OllamaGenerator:
    def __init__(
        self,
        *,
        modelo: str,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        timeout_s: float = DEFAULT_OLLAMA_TIMEOUT_S,
        num_predict: int = DEFAULT_OLLAMA_NUM_PREDICT,
        format_schema: dict[str, object] | None = None,
    ) -> None:
        if not modelo.strip():
            raise ValueError("modelo inválido")
        if not math.isfinite(timeout_s) or not 0 < timeout_s <= MAX_OLLAMA_TIMEOUT_S:
            raise ValueError("timeout debe ser mayor que 0 y menor o igual a 120 segundos")
        if (
            isinstance(num_predict, bool)
            or not isinstance(num_predict, int)
            or not MIN_OLLAMA_NUM_PREDICT <= num_predict <= MAX_OLLAMA_NUM_PREDICT
        ):
            raise ValueError("num_predict debe estar entre 32 y 512")
        self._host, self._port = _validar_base_url(base_url)
        self.modelo = modelo.strip()
        self._timeout_s = timeout_s
        self.num_predict = num_predict
        self._format_schema, self.format_schema_hash = _normalizar_format_schema(
            format_schema
        )
        self.format_mode = "json_schema" if self._format_schema is not None else None

    def generar(self, prompt: str) -> str:
        deadline = time.monotonic() + self._timeout_s
        solicitud: dict[str, object] = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": self.num_predict,
            },
        }
        if self._format_schema is not None:
            solicitud["format"] = self._format_schema
        payload = json.dumps(
            solicitud,
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


def _normalizar_format_schema(
    format_schema: dict[str, object] | None,
) -> tuple[dict[str, object] | None, str | None]:
    if format_schema is None:
        return None, None
    if not isinstance(format_schema, dict) or not format_schema:
        raise ValueError("format schema inválido")
    try:
        serializado = json.dumps(
            format_schema,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        raise ValueError("format schema inválido") from None
    codificado = serializado.encode("utf-8")
    if len(codificado) > MAX_FORMAT_SCHEMA_BYTES:
        raise ValueError("format schema inválido")
    normalizado = json.loads(serializado)
    return normalizado, hashlib.sha256(codificado).hexdigest()


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
