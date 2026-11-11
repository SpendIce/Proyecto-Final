#!/usr/bin/env python3
"""Purga diaria del canal web (ADR 0016, issue #149).

El paso de retención mínima que el scheduler corre una vez por día, antes
del respaldo: vence las solicitudes sin actividad por la ventana (30 días)
y vacía la prosa transitoria de las solicitudes cerradas — el texto queda
en NULL, conservando clase, hash y marcas. Después corre el VACUUM de la
tabla, con el rol de mantenimiento.

Entorno:

- `AGENTE1_POSTGRES_DSN` (obligatoria): conexión del paso; en producción
  debe apuntar al rol `agente1_mantenimiento`, dueño de la tabla de prosa,
  para que el VACUUM corra con mínimo privilegio.

Uso:

    python scripts/purgar_canal_web.py [--ventana-dias 30] [--ahora ISO]
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.web.persistencia import (  # noqa: E402
    VENTANA_VENCIMIENTO_DIAS,
    RepositorioWeb,
    conectar,
)


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Purga diaria del canal web (ADR 0016)."
    )
    parser.add_argument("--ventana-dias", type=int,
                        default=VENTANA_VENCIMIENTO_DIAS)
    parser.add_argument("--ahora", default=None)
    parser.add_argument(
        "--sin-vacuum",
        action="store_true",
        help="Corre la purga sin el VACUUM (ensayos sin rol dueño).",
    )
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    if not dsn:
        print(json.dumps(
            {"status": "INVALID", "error_code": "purga_dsn_ausente"},
            sort_keys=True,
        ))
        return 2
    ahora = None
    if args.ahora is not None:
        ahora = datetime.fromisoformat(args.ahora.replace("Z", "+00:00"))
        if ahora.tzinfo is None:
            print(json.dumps(
                {"status": "INVALID", "error_code": "purga_ahora_invalid"},
                sort_keys=True,
            ))
            return 2

    repositorio = RepositorioWeb(functools.partial(conectar, dsn))
    resultado = repositorio.vencer_y_purgar(
        ahora=ahora, ventana_dias=args.ventana_dias
    )
    vacuum = False
    if not args.sin_vacuum:
        RepositorioWeb.vaciar_prosa(dsn)
        vacuum = True

    print(
        json.dumps(
            {
                "status": "OK",
                "vencidas": resultado.vencidas,
                "purgadas": resultado.purgadas,
                "vacuum": vacuum,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
