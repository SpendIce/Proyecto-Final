"""Adapter del generador local (Ollama). El modelo corre en la misma máquina.

Decisiones que no se ven en el código:

- **Sólo loopback.** `_validar_base_url` rechaza cualquier host que no sea
  `localhost` o una IP de loopback. Es lo que sostiene la afirmación "el modelo
  es local y no sale a internet": no es una convención de despliegue, está
  impedido en el código. Por eso también se acepta `http` y no se exige TLS: el
  tráfico no abandona la máquina.
- **`temperature: 0`.** El objetivo no es un texto creativo distinto en cada
  corrida sino uno reproducible: dos ejecuciones de la misma fila deberían dar
  el mismo borrador, para que la evidencia sea comparable. La variedad
  aceptable la aporta el contrato creativo, no el muestreo.
- **`format_schema` opcional.** Cuando se pasa, Ollama fuerza la salida a ese
  esquema JSON. Su hash se registra en la auditoría: no es lo mismo un JSON
  pedido por prompt que uno impuesto por el motor, y la diferencia explica
  tasas de conformidad distintas entre corridas.
- **Todo error de red o de forma se colapsa a un `RuntimeError` genérico.** El
  pipeline sólo necesita saber que el generador no entregó algo utilizable, y
  un mensaje detallado podría arrastrar el prompt —que contiene datos de la
  actividad— hacia el log.
"""

from __future__ import annotations

from http.client import HTTPConnection, HTTPException
from ipaddress import ip_address
import hashlib
import json
import math
import time
from urllib.parse import urlsplit

from .presupuesto import PresupuestoAgotadoError


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_TIMEOUT_S = 45.0
MAX_OLLAMA_TIMEOUT_S = 120.0
# El presupuesto por defecto se deriva del contrato, no de una corrida que
# anduvo: `presupuesto.presupuesto_minimo_num_predict` da 482 tokens para el
# documento más grande que admite el contrato creativo vigente, medido con el
# tokenizador real. Subir el techo casi no cuesta: `num_predict` es un tope, no
# una meta, y la latencia la fija la cantidad de tokens que el modelo llega a
# emitir. Ver DEF-A1-013.
DEFAULT_OLLAMA_NUM_PREDICT = 512
MIN_OLLAMA_NUM_PREDICT = 32
MAX_OLLAMA_NUM_PREDICT = 512
MAX_RESPONSE_BYTES = 1_048_576
MAX_FORMAT_SCHEMA_BYTES = 65_536


class OllamaGenerator:
    """Implementa el puerto `Generator` contra un Ollama local ya iniciado.

    No descarga modelos ni levanta el servicio: si Ollama no está corriendo, la
    generación falla y la ejecución queda `FALLIDA`. Es deliberado que el
    agente no administre el runtime del modelo.
    """

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
        # Lo lee la auditoría por `getattr`: es un contador de la última
        # generación, no contenido. `None` significa que todavía no se generó.
        self.ultimo_num_predict_agotado: bool | None = None

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
        # `done is not True` es intencional: Ollama puede devolver 200 con una
        # respuesta truncada porque se cortó el stream. Un texto incompleto no
        # es una generación válida.
        if (
            "error" in documento
            or documento.get("done") is not True
            or not isinstance(contenido, str)
            or not contenido.strip()
        ):
            raise RuntimeError("Respuesta inválida del generador local")
        # Cuando se agota `num_predict`, Ollama igual responde `done: true` y
        # marca el motivo en `done_reason`. Sin este chequeo el corte llega al
        # parser como JSON incompleto y el defecto se le atribuye al modelo.
        if documento.get("done_reason") == "length":
            self.ultimo_num_predict_agotado = True
            raise PresupuestoAgotadoError(
                "El generador local agotó el presupuesto de decodificación"
            )
        self.ultimo_num_predict_agotado = False
        return contenido.strip()


class _TransportError(Exception):
    pass


def _normalizar_format_schema(
    format_schema: dict[str, object] | None,
) -> tuple[dict[str, object] | None, str | None]:
    """Serializa el esquema de forma canónica y devuelve su hash.

    El hash tiene que identificar al esquema, no a cómo se escribió: por eso se
    serializa con claves ordenadas y sin espacios antes de hashear. Así dos
    corridas con el mismo esquema escrito distinto quedan con el mismo hash en
    la auditoría, y un cambio real de esquema se nota.
    """

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
    """Acepta únicamente un Ollama en loopback.

    Rechaza credenciales embebidas, query y fragment porque no tienen uso
    legítimo acá y sí serían una forma de apuntar el generador a otro destino.
    Es el control que hace verificable la frase "el modelo corre local".
    """

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
