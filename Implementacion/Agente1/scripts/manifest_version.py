"""Genera el manifest de versión del Agente 1 (#92, ADR 0010).

Recorre lo controlado del repo —`src/`, `migrations/`, `uv.lock`,
`pyproject.toml`, `scripts/`, `systemd/`, `docker/` y el `Dockerfile`— y emite el sha256 de cada archivo
junto con la versión del agente. El manifest viaja con la versión que se
instala: el agente lo compara con el árbol del host al arrancar en modo
operación y no arranca si algo no coincide.

Es determinista: el mismo árbol produce el mismo archivo byte a byte, sin
timestamps ni orden dependiente del sistema de archivos, para que `git diff`
muestre sólo cambios reales.

Uso:

    uv run python scripts/manifest_version.py > manifest-version.json

El archivo vive en la raíz del Agente 1, **fuera** de las rutas que recorre,
así que no se controla a sí mismo. Se regenera al cortar una versión, después
de cualquier cambio bajo las rutas controladas: un manifest viejo es un agente
que no arranca.

La versión sale de `pyproject.toml` (`[project].version`); `--version` la
sobreescribe para ensayos.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.manifest_version import (  # noqa: E402
    IntegridadError,
    construir_manifest,
    serializar_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        help="Versión del manifest; por defecto la de pyproject.toml.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        help="Archivo de salida; por defecto stdout.",
    )
    args = parser.parse_args(argv)

    try:
        manifest = construir_manifest(ROOT, version=args.version)
    except IntegridadError as exc:
        print(f"manifest de versión inválido: {exc.code}", file=sys.stderr)
        return 1

    texto = serializar_manifest(manifest)
    if args.salida is None:
        sys.stdout.write(texto)
    else:
        args.salida.write_text(texto, encoding="utf-8")
    print(
        f"manifest de versión {manifest['version']}: "
        f"{len(manifest['archivos_sha256'])} archivos controlados",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
