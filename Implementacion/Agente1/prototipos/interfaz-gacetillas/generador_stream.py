"""Ollama en streaming para observar la inferencia del prototipo."""

from __future__ import annotations

import json
import time
from http.client import HTTPConnection, HTTPException

from agente1.ollama import MAX_RESPONSE_BYTES, OllamaGenerator, _ajustar_timeout
from agente1.presupuesto import MENSAJE_PRESUPUESTO_AGOTADO, PresupuestoAgotadoError


class TiempoDeGeneracionAgotado(RuntimeError):
    pass


class GeneradorConProgreso(OllamaGenerator):
    def __init__(self, *, job, num_thread=1, **kwargs):
        super().__init__(**kwargs)
        self.job = job
        self.num_thread = num_thread

    def generar(self, prompt):
        deadline = time.monotonic() + self._timeout_s
        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": True,
            "think": self.think,
            "options": {
                "temperature": 0,
                "num_predict": self.num_predict,
                "num_thread": self.num_thread,
                "num_thread_batch": self.num_thread,
            },
        }
        if self._format_schema is not None:
            payload["format"] = self._format_schema
        connection = HTTPConnection(self._host, self._port, timeout=self._timeout_s)
        pieces = []
        total_bytes = 0
        self.job.update(
            state="esperando_modelo",
            fragments=0,
            characters_received=0,
            inference_options=payload["options"],
        )
        try:
            connection.request(
                "POST",
                "/api/generate",
                body=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            _ajustar_timeout(connection, deadline)
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError("El servicio del modelo rechazó la solicitud")
            while True:
                _ajustar_timeout(connection, deadline)
                line = response.readline(MAX_RESPONSE_BYTES + 1)
                if not line:
                    raise RuntimeError("La respuesta del modelo terminó incompleta")
                total_bytes += len(line)
                if total_bytes > MAX_RESPONSE_BYTES:
                    raise RuntimeError("La respuesta del modelo excedió el límite")
                chunk = json.loads(line)
                if not isinstance(chunk, dict):
                    raise RuntimeError("El modelo devolvió un fragmento inválido")
                if "error" in chunk:
                    raise RuntimeError("El modelo no pudo completar la generación")
                piece = chunk.get("response", "")
                if not isinstance(piece, str):
                    raise RuntimeError("El modelo devolvió un fragmento inválido")
                if piece:
                    pieces.append(piece)
                    self.job.update(
                        state="generando",
                        fragments=self.job["fragments"] + 1,
                        characters_received=self.job["characters_received"]
                        + len(piece),
                        last_fragment_at=time.time(),
                    )
                    self.job.setdefault("first_fragment_at", time.time())
                if chunk.get("done") is True:
                    self.job["model_metrics"] = {
                        key: chunk[key]
                        for key in (
                            "eval_count",
                            "eval_duration",
                            "prompt_eval_count",
                            "prompt_eval_duration",
                            "total_duration",
                            "load_duration",
                        )
                        if key in chunk
                    }
                    if chunk.get("done_reason") == "length":
                        raise PresupuestoAgotadoError(MENSAJE_PRESUPUESTO_AGOTADO)
                    text = "".join(pieces).strip()
                    if not text:
                        raise RuntimeError("El modelo devolvió una respuesta vacía")
                    return text
        except TimeoutError:
            raise TiempoDeGeneracionAgotado(
                "La generación no terminó dentro del tiempo disponible"
            ) from None
        except (OSError, HTTPException):
            raise RuntimeError("Se interrumpió la conexión con el modelo") from None
        finally:
            connection.close()
