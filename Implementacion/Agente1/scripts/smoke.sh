#!/usr/bin/env bash
set -euo pipefail

# Smoke local de HU-010: genera una gacetilla con el generador fake a partir
# del golden SYN-001 y verifica que la salida sea idéntica. Es la comprobación
# más rápida de que el pipeline y el contrato siguen funcionando; no usa modelo
# ni red.

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
salida_dir="${1:-${repo_dir}/salida/smoke}"
fake_output="$(python - "${repo_dir}/golden/SYN-001.md" <<'PY'
from pathlib import Path
import sys

documento = Path(sys.argv[1]).read_text(encoding="utf-8")
print(documento.removeprefix("# BORRADOR — NO PUBLICAR\n\n").strip())
PY
)"

PYTHONPATH="${repo_dir}/src" \
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/agente1-pycache}" \
python -m agente1 \
  --csv "${repo_dir}/data/actividades_sinteticas.csv" \
  --id-solicitud SYN-001 \
  --salida "${salida_dir}" \
  --fake-output "${fake_output}"

diff -u \
  "${repo_dir}/golden/SYN-001.md" \
  "${salida_dir}/borradores/SYN-001.md"

python - "${salida_dir}/logs/ejecuciones.jsonl" <<'PY'
import json
from pathlib import Path
import sys

registros = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
ultimo = json.loads(registros[-1])
assert ultimo["estado"] == "PENDIENTE_VALIDACION"
assert ultimo["resultado"] == "borrador_generado"
assert "pruebas@example.invalid" not in registros[-1]
print("smoke HU-010: OK — borrador golden y log redacted verificados")
PY
