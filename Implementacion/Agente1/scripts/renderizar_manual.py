#!/usr/bin/env python3
"""Render del manual de operación: Markdown -> HTML autocontenido.

El manual de operación del Agente 1 es una sola fuente en Markdown dentro del
repo (`MANUAL-OPERACION-AGENTE-1.md`). Su PDF se adjunta al acta de traspaso y
a la versión etiquetada, pero **no se versiona** (política de artefactos,
`Documentos/PoC/Politica-Artefactos-Versionados-v1.md`). Este script hace la
mitad del render que Chromium no hace solo: convertir el Markdown a HTML. El PDF
lo imprime Chromium headless, igual que los demás renders del repositorio, desde
`scripts/renderizar-artefactos.sh` (grupo `manual`).

Decisiones que no se ven en el código:

- **Sin dependencias del paquete.** El manual no es parte del producto y no
  justifica sumar `markdown` a `pyproject.toml` (el runtime del Agente 1 tiene
  cero dependencias a propósito). Se trae de forma transitoria con
  `uv run --with markdown`, la misma convención que `scripts/anexo2_calidad.py`
  usa con `python-docx`. Si `markdown` no está disponible, el script falla con
  un mensaje que dice cómo invocarlo.
- **HTML autocontenido.** La hoja de estilo va embebida: el `.html` generado no
  depende de ningún otro archivo y Chromium lo imprime sin pedir nada.
- **El estilo existe para imprimir.** `@page` fija A4 y márgenes; las tablas y
  los bloques de código no se cortan al medio de una fila o de una línea.

Uso::

    uv run --with markdown python Implementacion/Agente1/scripts/renderizar_manual.py

Escribe `Implementacion/Agente1/MANUAL-OPERACION-AGENTE-1.html` junto a la
fuente. No toca la fuente ni el PDF.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import markdown
except ModuleNotFoundError:  # pragma: no cover - depende del entorno de render
    sys.stderr.write(
        "falta el paquete 'markdown': correr con\n"
        "  uv run --with markdown python "
        "Implementacion/Agente1/scripts/renderizar_manual.py\n"
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
FUENTE = ROOT / "MANUAL-OPERACION-AGENTE-1.md"
SALIDA = ROOT / "MANUAL-OPERACION-AGENTE-1.html"

# `extra` trae tablas y bloques cercados, que el manual usa. `sane_lists` evita
# que un ítem numerado partido en dos líneas se renuevre solo. No se activa
# `toc`: el manual ya trae su propio orden y toc sólo agregaría anclas que
# Chromium no usa al imprimir.
EXTENSIONES = ["extra", "sane_lists"]

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm 20mm 16mm; }}
  html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{
    font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif;
    font-size: 10pt; line-height: 1.45; color: #1a1a1a; margin: 0;
  }}
  h1 {{ font-size: 19pt; line-height: 1.2; margin: 0 0 0.6em; }}
  h2 {{
    font-size: 14pt; margin: 1.5em 0 0.5em; padding-bottom: 0.15em;
    border-bottom: 1px solid #999; page-break-after: avoid;
  }}
  h3 {{ font-size: 11.5pt; margin: 1.2em 0 0.4em; page-break-after: avoid; }}
  h4 {{ font-size: 10.5pt; margin: 1em 0 0.3em; page-break-after: avoid; }}
  p, li {{ orphans: 2; widows: 2; }}
  a {{ color: #0b4f9e; text-decoration: none; }}
  code {{
    font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
    font-size: 8.8pt; background: #f2f2f2; padding: 0 0.2em; border-radius: 2px;
  }}
  pre {{
    background: #f6f6f6; border: 1px solid #ddd; border-radius: 3px;
    padding: 0.5em 0.7em; overflow-wrap: anywhere; white-space: pre-wrap;
    page-break-inside: avoid;
  }}
  pre code {{ background: none; padding: 0; }}
  table {{
    border-collapse: collapse; width: 100%; margin: 0.6em 0 1em;
    font-size: 9pt;
  }}
  th, td {{
    border: 1px solid #bbb; padding: 0.3em 0.45em; text-align: left;
    vertical-align: top; overflow-wrap: anywhere;
  }}
  th {{ background: #eee; }}
  tr, li {{ page-break-inside: avoid; }}
  blockquote {{
    margin: 0.6em 0; padding: 0.2em 0.8em; border-left: 3px solid #bbb;
    color: #333;
  }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 1.6em 0; }}
  ul, ol {{ padding-left: 1.4em; }}
</style>
</head>
<body>
{cuerpo}
</body>
</html>
"""


def construir_html(texto_markdown: str) -> str:
    """El HTML completo (cabeza, estilo y cuerpo) de la fuente Markdown."""

    cuerpo = markdown.markdown(texto_markdown, extensions=EXTENSIONES)
    titulo = "Manual de operación del Agente 1"
    for linea in texto_markdown.splitlines():
        if linea.startswith("# "):
            titulo = linea[2:].strip()
            break
    return PLANTILLA.format(titulo=titulo, cuerpo=cuerpo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convierte el manual de operación Markdown a HTML imprimible."
    )
    parser.add_argument("--fuente", type=Path, default=FUENTE)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args(argv)

    if not args.fuente.is_file():
        sys.stderr.write(f"no existe la fuente: {args.fuente}\n")
        return 2

    html = construir_html(args.fuente.read_text(encoding="utf-8"))
    args.salida.write_text(html, encoding="utf-8")
    print(f"html:  {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
