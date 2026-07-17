from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .ollama import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT_S,
    OllamaGenerator,
)
from .procesamiento import FakeGenerator, procesar_fila_csv


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Genera un borrador local HU-010 desde una fila CSV sintética."
    )
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--id-solicitud", required=True)
    parser.add_argument("--salida", required=True, type=Path)
    generator_group = parser.add_mutually_exclusive_group(required=True)
    generator_group.add_argument("--fake-output")
    generator_group.add_argument("--ollama-model")
    parser.add_argument("--ollama-base-url", default=DEFAULT_OLLAMA_BASE_URL)
    parser.add_argument(
        "--ollama-timeout",
        default=DEFAULT_OLLAMA_TIMEOUT_S,
        type=_timeout_ollama,
        metavar="SEGUNDOS",
    )
    args = parser.parse_args(argv)

    try:
        generator = (
            FakeGenerator(args.fake_output)
            if args.fake_output is not None
            else OllamaGenerator(
                modelo=args.ollama_model,
                base_url=args.ollama_base_url,
                timeout_s=args.ollama_timeout,
            )
        )
        resultado = procesar_fila_csv(
            csv_path=args.csv,
            id_solicitud=args.id_solicitud,
            directorio_salida=args.salida,
            generator=generator,
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


def _timeout_ollama(value: str) -> float:
    try:
        timeout_s = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un número") from None
    if not 0 < timeout_s <= 30:
        raise argparse.ArgumentTypeError("debe ser mayor que 0 y menor o igual a 30")
    return timeout_s
