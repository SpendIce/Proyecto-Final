#!/usr/bin/env bash
set -euo pipefail

# Smoke local de HU-012: recorre el ciclo de vida de una confirmación contra el
# destino fake. No hay adapter de correo, así que no puede enviar nada.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SALIDA="${1:-${ROOT}/salida/smoke-hu012}"

PYTHONDONTWRITEBYTECODE=1 python "${ROOT}/scripts/matriz_hu012.py" --salida "${SALIDA}"
printf 'smoke HU-012 offline: OK (sin correo real)\n'
