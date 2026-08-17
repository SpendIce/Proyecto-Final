from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .ollama import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_NUM_PREDICT,
    DEFAULT_OLLAMA_TIMEOUT_S,
    MAX_OLLAMA_TIMEOUT_S,
    OllamaGenerator,
)
from .procesamiento import FakeGenerator, procesar_fila_csv
from .fuentes import CsvFuenteSolicitudes
from .posts import POLITICAS_DEFAULT, PoliticaPost, procesar_post


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Genera un borrador local HU-010/HU-011 desde una fila CSV sintética."
    )
    parser.add_argument("--tipo", choices=("gacetilla", "post"), default="gacetilla")
    parser.add_argument("--canal", choices=("instagram", "linkedin"))
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
    parser.add_argument(
        "--ollama-num-predict",
        default=DEFAULT_OLLAMA_NUM_PREDICT,
        type=int,
        metavar="TOKENS",
    )
    parser.add_argument(
        "--post-max-chars",
        default=None,
        type=_entero_positivo,
        metavar="CARACTERES",
        help="Límite técnico provisional HU-011; sólo válido con --tipo post.",
    )
    parser.add_argument(
        "--post-min-hashtags",
        default=None,
        type=_entero_no_negativo,
        metavar="CANTIDAD",
        help="Mínimo técnico provisional HU-011 (default 1); sólo para posts.",
    )
    parser.add_argument(
        "--post-max-hashtags",
        default=None,
        type=_entero_positivo,
        metavar="CANTIDAD",
        help="Máximo técnico provisional HU-011; sólo válido con --tipo post.",
    )
    args = parser.parse_args(argv)

    try:
        post_flags = (
            args.canal,
            args.post_max_chars,
            args.post_min_hashtags,
            args.post_max_hashtags,
        )
        if args.tipo == "gacetilla" and any(valor is not None for valor in post_flags):
            raise ValueError("flags exclusivos de post")
        generator = (
            FakeGenerator(args.fake_output)
            if args.fake_output is not None
            else OllamaGenerator(
                modelo=args.ollama_model,
                base_url=args.ollama_base_url,
                timeout_s=args.ollama_timeout,
                num_predict=args.ollama_num_predict,
            )
        )
        if args.tipo == "post":
            if args.canal is None:
                raise ValueError("canal requerido")
            politica_base = POLITICAS_DEFAULT[args.canal]
            resultado = procesar_post(
                fuente=CsvFuenteSolicitudes(args.csv),
                id_solicitud=args.id_solicitud,
                canal=args.canal,
                directorio_salida=args.salida,
                generator=generator,
                politica=PoliticaPost(
                    version=politica_base.version,
                    status=politica_base.status,
                    max_chars=args.post_max_chars or politica_base.max_chars,
                    min_hashtags=(
                        args.post_min_hashtags
                        if args.post_min_hashtags is not None
                        else politica_base.min_hashtags
                    ),
                    max_hashtags=args.post_max_hashtags or politica_base.max_hashtags,
                ),
            )
        else:
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
    if not 0 < timeout_s <= MAX_OLLAMA_TIMEOUT_S:
        raise argparse.ArgumentTypeError("debe ser mayor que 0 y menor o igual a 120")
    return timeout_s


def _entero_positivo(value: str) -> int:
    try:
        entero = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un entero") from None
    if entero <= 0:
        raise argparse.ArgumentTypeError("debe ser mayor que 0")
    return entero


def _entero_no_negativo(value: str) -> int:
    try:
        entero = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un entero") from None
    if entero < 0:
        raise argparse.ArgumentTypeError("debe ser mayor o igual que 0")
    return entero
