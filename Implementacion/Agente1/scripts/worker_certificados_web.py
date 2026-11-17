#!/usr/bin/env python3
"""Worker de la cola durable de emisión de certificados (#168).

Reclama un trabajo de `emisiones_certificados` por ciclo —`FOR UPDATE
SKIP LOCKED` con token de reserva— y lo ejecuta con el snapshot aprobado
del lote. Los trabajos demo componen el render real con marcas de prueba
(`ejecutar_trabajo_demo`); los reales pasan por todas las barreras —
lote aprobado, rol vigente del generador, aprobaciones registradas,
plantillas y firmas— antes de que `fabrica_destino` toque la red de
Gmail. Un envío que pudo haber salido cierra `INDETERMINADA` y nunca se
reintenta desde acá.

El servicio se arma con `construir_emision_certificados_web`: no abre la
base ni la red en el arranque, así el worker puede levantar con la
config incompleta y reportar el bloqueo en vez de caer en loop.

Entorno:

- `AGENTE1_POSTGRES_DSN` (obligatoria): DSN de la base; en producción
  conecta como `agente1_app`.
- `AGENTE1_PADRON_ROLES_CSV`: padrón de roles para revalidar al generador.
- `AGENTE1_DECISIONES_DIR`: registro JSONL de aprobaciones.
- `AGENTE1_CERTIFICADOS_RECURSOS_DIR` / `AGENTE1_PLANTILLAS_APROBADAS_PATH`:
  firmas y redacciones aprobadas, fuera del repo.
- `AGENTE1_WEB_MODO_DEMO=si`: el worker corre el carril demo; los trabajos
  reales quedan `FALLIDA` sin tocar la red.
- `AGENTE1_ENV_FILE` con las credenciales Workspace para el destino Gmail.
- `AGENTE1_WORKER_ID`: nombre de la reserva (default `worker-certificados-1`).
- `AGENTE1_ESTADO`: base del directorio de auditoría de la emisión.

Uso:

    python scripts/worker_certificados_web.py [--una-vez] [--intervalo N]
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _invalida(code: str) -> int:
    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Worker de la cola durable de certificados (#168)."
    )
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--una-vez", action="store_true")
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args(argv)
    entorno = dict(os.environ if environ is None else environ)

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    if not dsn:
        return _invalida("worker_certificados_dsn_ausente")

    from agente1.web.emision_certificados_runtime import (
        construir_emision_certificados_web,
    )
    from agente1.web.persistencia import conectar

    servicio = construir_emision_certificados_web(
        entorno,
        conexion_factory=functools.partial(conectar, dsn),
    )
    worker_id = (
        args.worker_id
        or entorno.get("AGENTE1_WORKER_ID")
        or "worker-certificados-1"
    )

    while True:
        try:
            id_emision = servicio.correr_una_vez(worker_id=worker_id)
        except Exception as exc:
            # La reserva vence sola y `reconciliar` la recupera: un ciclo
            # roto no mata al daemon, se reporta y se espera al próximo.
            print(
                json.dumps(
                    {
                        "status": "ERROR",
                        "error_code": getattr(
                            exc, "code", "worker_ciclo_fallido"
                        ),
                    },
                    sort_keys=True,
                )
            )
            if args.una_vez:
                return 1
            time.sleep(args.intervalo)
            continue
        if args.una_vez:
            print(
                json.dumps(
                    {"status": "OK", "trabajo": id_emision},
                    sort_keys=True,
                )
            )
            return 0
        if id_emision is None:
            time.sleep(args.intervalo)


if __name__ == "__main__":
    raise SystemExit(main())
