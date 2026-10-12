#!/usr/bin/env python3
"""Purga de datos personales del registro durable de confirmaciones (#87).

Es la operación de la retención acotada (ADR 0009, término del glosario):
borra el texto del borrador y los datos de la persona de los registros en
estado terminal cuya ventana de reconciliación ya venció (30 días por
omisión), conservando la clave de idempotencia, el estado, las fechas y
los hashes. La idempotencia no se rompe: una solicitud repetida sigue
chocando contra la misma clave, así que purgar nunca habilita un reenvío.
Los registros `ENVIO_INDETERMINADO` y todo estado no terminal no se
toman: siguen a la vista hasta que una persona decida.

Uso manual:

    python scripts/purgar_registro.py \
        --registro salida/registro-confirmaciones \
        --salida salida

`--registro` es el directorio del registro durable (un archivo por clave)
y `--salida` el directorio bajo el que queda la auditoría
(`logs/confirmaciones-hu012.jsonl`): una línea por corrida con la
cantidad purgada y el hash del conjunto de claves, nunca contenido.

Punto de entrada del scheduler: el scheduler local (#84) invoca este
comando una vez por día dentro de la ventana de operación, antes del
respaldo diario del estado (#86), para que ningún respaldo conserve texto
que la política de retención ya venció.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.confirmaciones import (  # noqa: E402
    RegistroConfirmacionesArchivo,
    VENTANA_RECONCILIACION_DIAS,
    _hash,
    correr_purga_registro,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Purga el texto de los registros terminales vencidos; "
            "conserva clave, estado, fechas y hashes."
        )
    )
    parser.add_argument(
        "--registro",
        type=Path,
        required=True,
        help="directorio del registro durable (un archivo por clave)",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        required=True,
        help="directorio bajo el que queda logs/confirmaciones-hu012.jsonl",
    )
    parser.add_argument(
        "--ventana-dias",
        type=int,
        default=VENTANA_RECONCILIACION_DIAS,
        help="días de ventana de reconciliación (default: %(default)s)",
    )
    parser.add_argument(
        "--ahora",
        default=None,
        help=(
            "instante ISO-8601 con zona horaria contra el que se mide la "
            "ventana (default: ahora UTC); fijo sólo para corridas "
            "reproducibles"
        ),
    )
    args = parser.parse_args(argv)

    try:
        if not args.registro.is_dir():
            raise ValueError
        ahora = None
        if args.ahora is not None:
            ahora = datetime.fromisoformat(args.ahora.replace("Z", "+00:00"))
            if ahora.tzinfo is None:
                raise ValueError
        resultado = correr_purga_registro(
            registro=RegistroConfirmacionesArchivo(args.registro),
            directorio_salida=args.salida,
            ahora=ahora,
            ventana_dias=args.ventana_dias,
        )
    except (OSError, ValueError):
        print(
            json.dumps(
                {"status": "INVALID", "error_code": "purge_arguments_invalid"},
                sort_keys=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": "OK",
                "purgados": len(resultado.purgadas),
                "claves_hash": _hash("\n".join(resultado.purgadas)),
                "ventana_dias": resultado.ventana_dias,
                "ejecutado_en": resultado.ejecutado_en,
                "log_path": str(resultado.log_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
