#!/usr/bin/env bash
# Regenera los artefactos derivados que la politica de artefactos versionados
# deja fuera de Git. Ver Documentos/PoC/Politica-Artefactos-Versionados-v1.md.
#
# Uso:
#   scripts/renderizar-artefactos.sh              # regenera todo
#   scripts/renderizar-artefactos.sh latex        # solo PDFs desde .tex
#   scripts/renderizar-artefactos.sh presentacion # solo renders desde HTML
#
# El script no borra nada y no toca fuentes versionadas. Escribe cada salida
# junto a su fuente, en rutas que .gitignore ya excluye.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM="${CHROMIUM:-chromium}"
PDFLATEX="${PDFLATEX:-pdflatex}"
PDFTOPPM="${PDFTOPPM:-pdftoppm}"

requerir() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "falta la herramienta requerida: $1" >&2
    exit 1
  }
}

# pdflatex escribe .aux/.log/.out/.toc junto al .tex; el .toc obliga a dos
# pasadas para que el indice quede resuelto.
render_latex() {
  local tex="$1" pasadas="$2" dir base
  dir="$(dirname "$RAIZ/$tex")"
  base="$(basename "$tex")"
  echo "latex: $tex ($pasadas pasada(s))"
  for _ in $(seq 1 "$pasadas"); do
    (cd "$dir" && "$PDFLATEX" -interaction=nonstopmode -halt-on-error "$base" >/dev/null)
  done
}

# Chromium headless imprime respetando el @page declarado en cada HTML.
render_pdf_html() {
  local html="$1" pdf="$2"
  echo "pdf:   $pdf"
  "$CHROMIUM" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf="$RAIZ/$pdf" "file://$RAIZ/$html" >/dev/null 2>&1
}

# --force-device-scale-factor 2 reproduce los PNG a doble densidad del corte
# 2026-08-26 (1600x900 -> 3200x1800; 1240x1754 -> 2480x3508).
render_png_html() {
  local html="$1" png="$2" ancho="$3" alto="$4"
  echo "png:   $png"
  "$CHROMIUM" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --screenshot="$RAIZ/$png" --window-size="$ancho,$alto" \
    --force-device-scale-factor=2 "file://$RAIZ/$html" >/dev/null 2>&1
}

# Un deck de varias laminas se rasteriza desde su PDF: cada pagina del PDF es
# una lamina, y asi no hace falta guionar la navegacion del deck.
render_png_por_pagina() {
  local pdf="$1" destino="$2" ancho="$3" alto="$4"
  shift 4
  local nombres=("$@") i=1
  mkdir -p "$RAIZ/$destino"
  "$PDFTOPPM" -png -scale-to-x "$ancho" -scale-to-y "$alto" \
    "$RAIZ/$pdf" "$RAIZ/$destino/pagina"
  for nombre in "${nombres[@]}"; do
    local origen
    origen="$(printf '%s/%s/pagina-%d.png' "$RAIZ" "$destino" "$i")"
    [ -f "$origen" ] || origen="$(printf '%s/%s/pagina-%02d.png' "$RAIZ" "$destino" "$i")"
    echo "png:   $destino/$nombre"
    mv "$origen" "$RAIZ/$destino/$nombre"
    i=$((i + 1))
  done
}

grupo_latex() {
  requerir "$PDFLATEX"
  render_latex "Documentos/PoC/Ficha-Definiciones-Operativas-SEU-Agente-1.tex" 1
  render_latex "Documentos/PoC/Validacion-SEU/Paquete-Revision-SEU-Agente-1.tex" 2
}

grupo_presentacion() {
  requerir "$CHROMIUM"
  requerir "$PDFTOPPM"
  local base="Documentos/Presentacion"

  render_pdf_html "$base/Flujo-Aprobacion-SEU-Agente-1-2026-08-26.html" \
                  "$base/Flujo-Aprobacion-SEU-Agente-1-2026-08-26.pdf"
  render_png_html "$base/Flujo-Aprobacion-SEU-Agente-1-2026-08-26.html" \
                  "$base/Flujo-Aprobacion-SEU-Agente-1-2026-08-26.png" 1240 1754

  render_png_html "$base/Lamina-Agente-1-Extension-Bot-2026-08-26.html" \
                  "$base/Lamina-Agente-1-Extension-Bot-2026-08-26.png" 1600 900

  render_pdf_html "$base/Laminas-Agente-1-Extension-Bot-2026-08-26.html" \
                  "$base/Laminas-Agente-1-Extension-Bot-2026-08-26.pdf"
  render_png_por_pagina "$base/Laminas-Agente-1-Extension-Bot-2026-08-26.pdf" \
                        "$base/Laminas-Agente-1-Extension-Bot-2026-08-26" 3200 1800 \
                        "01-problema-y-propuesta.png" \
                        "02-generacion-real.png" \
                        "03-control-humano-y-pedido.png"
}

case "${1:-todo}" in
  latex) grupo_latex ;;
  presentacion) grupo_presentacion ;;
  todo) grupo_latex; grupo_presentacion ;;
  *) echo "grupo desconocido: $1 (latex | presentacion | todo)" >&2; exit 2 ;;
esac

echo "listo"
