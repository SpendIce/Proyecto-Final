#!/usr/bin/env python3
"""Worker de generación del canal web (issue #149, ADR 0016).

Toma las ejecuciones reservables de la base —`SELECT ... FOR UPDATE SKIP
LOCKED` con plazo—, corre el pipeline vigente por tipo y deja el estado
durable. Corre fuera de la respuesta HTTP, un trabajo por ciclo; ante una
caída, la reserva vence y otra corrida retoma sin duplicar el Doc.

Entorno:

- `AGENTE1_POSTGRES_DSN` (obligatoria): DSN de la base; en producción
  conecta como `agente1_app`.
- `AGENTE1_WORKER_ID`: nombre de la reserva (default `worker-1`).

Uso:

    python scripts/worker_canal_web.py --tabla data/actividades_sinteticas.csv \
        --salida salida --generador-salida "texto fijo" [--una-vez]

`--generador-salida` es el modo offline determinista (FakeGenerator); sin
él se exige `--ollama-model` para el modelo real del stack. El destino del
Doc se inyecta: `--destino-fake` usa el destino en memoria con marca de
solicitud (desarrollo y evidencia); el adapter real de Docs con marca queda
declarado para #153/el despliegue.
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
        description="Worker de generación del canal web (ADR 0016)."
    )
    parser.add_argument("--tabla", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--generador-salida", default=None)
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--destino-fake", action="store_true")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--plazo-segundos", type=int, default=300)
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--una-vez", action="store_true")
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    if not dsn:
        return _invalida("worker_dsn_ausente")
    if not args.destino_fake:
        return _invalida("worker_destino_no_declarado")

    from agente1.fuentes import CsvFuenteSolicitudes
    from agente1.procesamiento import FakeGenerator
    from agente1.web.persistencia import RepositorioWeb, conectar
    from agente1.web.worker import DestinoPorMarcaMemoria, correr_una_vez

    if args.generador_salida is not None:
        generator = FakeGenerator(args.generador_salida)
    elif args.ollama_model:
        from agente1.ollama import OllamaGenerator

        generator = OllamaGenerator(modelo=args.ollama_model)
    else:
        return _invalida("worker_generador_no_declarado")

    fuente = CsvFuenteSolicitudes(args.tabla)
    repositorio = RepositorioWeb(functools.partial(conectar, dsn))
    destino = DestinoPorMarcaMemoria()
    worker_id = (
        args.worker_id
        or entorno.get("AGENTE1_WORKER_ID")
        or "worker-1"
    )
    args.salida.mkdir(parents=True, exist_ok=True)

    while True:
        trabajo = correr_una_vez(
            repositorio=repositorio,
            worker_id=worker_id,
            fuente=fuente,
            generator=generator,
            directorio_salida=args.salida,
            destino=destino,
            plazo_segundos=args.plazo_segundos,
        )
        if args.una_vez:
            print(
                json.dumps(
                    {
                        "status": "OK",
                        "trabajo": trabajo.id_ejecucion if trabajo else None,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if trabajo is None:
            time.sleep(args.intervalo)


if __name__ == "__main__":
    sys.exit(main())
