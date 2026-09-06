"""CLI local del MVP: una solicitud, un borrador, salida JSON en stdout.

Es la interfaz usada en pruebas, smokes y matrices de evidencia. Trabaja
siempre contra un CSV local y deja el borrador en disco: **no tiene modo
Workspace**. Salir a Google se hace por `scripts/workspace_e2e.py`, que exige
el doble opt-in; que no exista una bandera `--live` acá es intencional.

Decisiones que no se ven en el código:

- **El código de salida distingue estados, no excepciones.** `0` sólo si quedó
  un borrador (`PENDIENTE_VALIDACION`); `2` para cualquier otro desenlace,
  incluidos los legítimos como datos incompletos. Un script que encadene
  ejecuciones no debe seguir adelante como si se hubiera generado algo.
- **La salida es JSON con claves ordenadas** para poder compararla entre
  corridas y guardarla como evidencia.
- **Elegir generador es obligatorio y excluyente**: o el fake determinista o un
  modelo de Ollama. No hay default, para que ninguna evidencia quede con dudas
  sobre con qué se produjo.
- **El default seguro de HU-011 es el contrato estructurado**; `text-v1`, el
  camino heredado sin renderer determinista, hay que pedirlo explícitamente.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
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
from .posts import (
    CONTRATO_SALIDA_ESTRUCTURADA,
    POLITICAS_DEFAULT,
    procesar_post,
    procesar_post_estructurado,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""

    parser = argparse.ArgumentParser(
        description="Genera un borrador local HU-010/HU-011 desde una fila CSV sintética."
    )
    parser.add_argument("--tipo", choices=("gacetilla", "post"), default="gacetilla")
    parser.add_argument("--canal", choices=("instagram", "linkedin"))
    parser.add_argument(
        "--post-version",
        choices=("structured-v2", "text-v1"),
        default=None,
        help=(
            "Contrato de salida HU-011; structured-v2 es el default seguro. "
            "text-v1 requiere selección explícita."
        ),
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
            args.post_version,
            args.post_max_chars,
            args.post_min_hashtags,
            args.post_max_hashtags,
        )
        # Las banderas de post con --tipo gacetilla son un error, no algo a
        # ignorar: quien las pasó cree estar ajustando límites que no se van a
        # aplicar, y la evidencia resultante diría otra cosa que lo pedido.
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
                format_schema=(
                    CONTRATO_SALIDA_ESTRUCTURADA
                    if args.tipo == "post" and args.post_version != "text-v1"
                    else None
                ),
            )
        )
        if args.tipo == "post":
            if args.canal is None:
                raise ValueError("canal requerido")
            politica_base = POLITICAS_DEFAULT[args.canal]
            procesador_post = (
                procesar_post if args.post_version == "text-v1" else procesar_post_estructurado
            )
            resultado = procesador_post(
                fuente=CsvFuenteSolicitudes(args.csv),
                id_solicitud=args.id_solicitud,
                canal=args.canal,
                directorio_salida=args.salida,
                generator=generator,
                politica=replace(
                    politica_base,
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
        # Todo error de armado (flags incompatibles, canal faltante, URL de
        # Ollama inválida) se reporta con el mismo mensaje genérico: el detalle
        # ya lo dio argparse por stderr, y stdout debe mantener una forma
        # estable y sin datos para quien parsee la salida.
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
