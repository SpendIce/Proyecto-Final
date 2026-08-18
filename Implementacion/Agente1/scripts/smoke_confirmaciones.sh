#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SALIDA="${1:-${ROOT}/salida/smoke-hu012}"

PYTHONDONTWRITEBYTECODE=1 python "${ROOT}/scripts/matriz_hu012.py" --salida "${SALIDA}"
printf 'smoke HU-012 offline: OK (sin correo real)\n'
