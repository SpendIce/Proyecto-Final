#!/usr/bin/env python3
"""Regenera el artefacto durable de HU-010: goldens y muestras de la SEU.

Corre el pipeline de gacetilla con el generador fake determinista sobre las
fichas golden versionadas —la salida del modelo que el pipeline valida— y
escribe el mail renderizado (el artefacto durable, con su marca de borrador)
en los dos lugares donde se versiona: `golden/SYN-*.md`, que usa la matriz de
conformidad, y las muestras del paquete de validación de la SEU.

Es reproducible por construcción: mismas fichas, mismo dataset y mismo
renderer dan el mismo archivo byte a byte. No usa modelo ni red, y sólo
escribe los tres casos completos. Pensado para correr después de un cambio de
renderer o de prompt; ver `evidencias/` para la traza del corte.

Uso:
    uv run python scripts/regenerar_gacetilla_durable.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import FakeGenerator, procesar_fila_csv  # noqa: E402

CASOS_COMPLETOS = ("SYN-001", "SYN-003", "SYN-005")


def _durable(caso_id: str, salida: Path) -> str:
    """Mail renderizado del caso, tal como lo escribe el destino local."""

    ficha = (ROOT / "golden" / f"{caso_id}.ficha.md").read_text(encoding="utf-8").strip()
    resultado = procesar_fila_csv(
        csv_path=ROOT / "data" / "actividades_sinteticas.csv",
        id_solicitud=caso_id,
        directorio_salida=salida / caso_id,
        generator=FakeGenerator(ficha),
    )
    if resultado.estado != "PENDIENTE_VALIDACION" or resultado.borrador_path is None:
        raise RuntimeError(
            f"{caso_id}: el pipeline no produjo borrador ({resultado.estado})"
        )
    return resultado.borrador_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-dir", type=Path, default=ROOT / "golden")
    parser.add_argument(
        "--muestras-dir",
        type=Path,
        default=REPO_ROOT / "Documentos" / "PoC" / "Validacion-SEU" / "muestras",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "salida" / "regenerar-durable",
        help="Directorio de trabajo del pipeline (se crea si no existe).",
    )
    args = parser.parse_args(argv)

    args.golden_dir.mkdir(parents=True, exist_ok=True)
    args.muestras_dir.mkdir(parents=True, exist_ok=True)

    for caso_id in CASOS_COMPLETOS:
        contenido = _durable(caso_id, args.salida)
        (args.golden_dir / f"{caso_id}.md").write_text(contenido, encoding="utf-8")
        (args.muestras_dir / f"gacetilla-{caso_id}-live.md").write_text(
            contenido, encoding="utf-8"
        )
        print(f"{caso_id}: golden y muestra regenerados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
