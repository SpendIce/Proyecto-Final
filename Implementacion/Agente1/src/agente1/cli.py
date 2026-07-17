from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .procesamiento import FakeGenerator, procesar_fila_csv


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Genera un borrador local HU-010 desde una fila CSV sintética."
    )
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--id-solicitud", required=True)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--fake-output", required=True)
    args = parser.parse_args(argv)

    try:
        resultado = procesar_fila_csv(
            csv_path=args.csv,
            id_solicitud=args.id_solicitud,
            directorio_salida=args.salida,
            generator=FakeGenerator(args.fake_output),
        )
    except ValueError:
        print(
            json.dumps(
                {
                    "estado": "INVALIDA",
                    "correlation_id": None,
                    "borrador": None,
                    "log": None,
                    "error": "Solicitud inválida o inexistente",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "estado": resultado.estado,
                "correlation_id": resultado.correlation_id,
                "borrador": str(resultado.borrador_path) if resultado.borrador_path else None,
                "log": str(resultado.log_path),
                "error": resultado.error,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if resultado.estado == "PENDIENTE_VALIDACION" else 2
