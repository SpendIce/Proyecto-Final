"""Pruebas del transporte real HTTP/NDJSON con un servidor local controlado."""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from generador_stream import GeneradorConProgreso, TiempoDeGeneracionAgotado  # noqa: E402

from agente1.presupuesto import PresupuestoAgotadoError  # noqa: E402


class StreamChecks(unittest.TestCase):
    def run_stream(self, chunks, delay=0, timeout=2):
        seen = {}

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_POST(self):
                seen.update(
                    json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                )
                lines = [json.dumps(chunk).encode() + b"\n" for chunk in chunks]
                self.send_response(200)
                self.send_header("Content-Length", str(sum(map(len, lines))))
                self.end_headers()
                try:
                    for line in lines:
                        if delay:
                            time.sleep(delay)
                        self.wfile.write(line)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        job = {}
        generator = GeneradorConProgreso(
            job=job,
            modelo="modelo-prueba",
            base_url=f"http://127.0.0.1:{server.server_port}",
            timeout_s=timeout,
            num_predict=512,
            think=False,
        )
        return generator, job, seen

    def test_progress_and_complete_response(self):
        generator, job, seen = self.run_stream(
            [
                {"response": "Hola ", "done": False},
                {"response": "mundo.", "done": False},
                {"response": "", "done": True, "eval_count": 2, "eval_duration": 1000},
            ]
        )
        self.assertEqual(generator.generar("texto"), "Hola mundo.")
        self.assertEqual(job["fragments"], 2)
        self.assertEqual(job["characters_received"], 11)
        self.assertTrue(seen["stream"])
        self.assertEqual(seen["options"]["num_thread"], 1)
        self.assertEqual(job["model_metrics"]["eval_count"], 2)

    def test_budget_exhaustion_is_not_a_valid_draft(self):
        generator, _, _ = self.run_stream(
            [{"response": "cortado", "done": True, "done_reason": "length"}]
        )
        with self.assertRaises(PresupuestoAgotadoError):
            generator.generar("texto")

    def test_truncated_stream_is_rejected(self):
        generator, _, _ = self.run_stream([{"response": "parcial", "done": False}])
        with self.assertRaisesRegex(RuntimeError, "incompleta"):
            generator.generar("texto")

    def test_timeout_has_its_own_reason(self):
        generator, job, _ = self.run_stream(
            [{"response": "tarde", "done": True}], delay=0.2, timeout=0.05
        )
        with self.assertRaises(TiempoDeGeneracionAgotado):
            generator.generar("texto")
        self.assertEqual(job["state"], "esperando_modelo")

    def test_invalid_fragment_is_rejected(self):
        generator, _, _ = self.run_stream([{"response": 42, "done": True}])
        with self.assertRaisesRegex(RuntimeError, "inválido"):
            generator.generar("texto")


if __name__ == "__main__":
    unittest.main()
