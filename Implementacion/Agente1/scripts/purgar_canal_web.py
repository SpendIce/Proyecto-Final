#!/usr/bin/env python3
"""Purga diaria del canal web (ADR 0016, issue #149).

El paso de retención mínima que el scheduler corre una vez por día, antes
del respaldo, con el reparto de roles de la migración 0005:

1. `agente1_app` vence: pasa a `VENCIDA` toda solicitud abierta sin
   actividad por la ventana (30 días). Es el rol que sirve la app y el
   único que escribe el ciclo de vida.
2. `agente1_mantenimiento` purga y vacía: pone en NULL la prosa
   transitoria de toda solicitud cerrada —conservando clase, hash y
   marcas— y corre el VACUUM de la tabla, del que es dueña.

Sin el DSN de mantenimiento el paso falla cerrado: una purga que corre
con el rol de la app podría tocar el contenido que la retención ya cerró,
que es justo lo que el reparto evita.

Entorno:

- `AGENTE1_POSTGRES_DSN` (obligatoria): conexión como `agente1_app`.
- `AGENTE1_POSTGRES_DSN_MANTENIMIENTO` (obligatoria): conexión como
  `agente1_mantenimiento`.

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


def _invalida(code: str) -> int:
    print(json.dumps({"status": "INVALID", "error_code": code},
                     sort_keys=True))
    return 2


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

    dsn_app = entorno.get("AGENTE1_POSTGRES_DSN")
    dsn_mantenimiento = entorno.get("AGENTE1_POSTGRES_DSN_MANTENIMIENTO")
    if not dsn_app or not dsn_mantenimiento:
        return _invalida("purga_dsn_ausente")
    ahora = None
    if args.ahora is not None:
        ahora = datetime.fromisoformat(args.ahora.replace("Z", "+00:00"))
        if ahora.tzinfo is None:
            return _invalida("purga_ahora_invalid")

    repositorio_app = RepositorioWeb(functools.partial(conectar, dsn_app))
    vencidas = repositorio_app.vencer_solicitudes(
        ahora=ahora, ventana_dias=args.ventana_dias
    )

    repositorio_mantenimiento = RepositorioWeb(
        functools.partial(conectar, dsn_mantenimiento)
    )
    purgadas = repositorio_mantenimiento.purgar_prosa(ahora=ahora)
    vacuum = False
    if not args.sin_vacuum:
        RepositorioWeb.vaciar_prosa(dsn_mantenimiento)
        vacuum = True

    print(
        json.dumps(
            {
                "status": "OK",
                "vencidas": vencidas,
                "purgadas": purgadas,
                "vacuum": vacuum,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
