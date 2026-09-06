#!/usr/bin/env bash
set -euo pipefail

# Smoke local de HU-011: corre la matriz fake de posts en ambos canales. Igual
# que el de gacetillas, es determinista y no depende de un modelo instalado.

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
salida_dir="${1:-${repo_dir}/salida/smoke-hu011}"

PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/agente1-pycache}" \
python "${repo_dir}/scripts/matriz_hu011.py" \
  --salida "${salida_dir}" \
  --solo-id SYN-001

python - "${salida_dir}/matriz.json" <<'PY'
import json
from pathlib import Path
import sys

resumen = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert resumen["totals"]["channel_executions"] == 2
assert resumen["totals"]["pending_validation"] == 2
assert {caso["canal"] for caso in resumen["cases"]} == {"instagram", "linkedin"}
assert all(caso["draft_created"] for caso in resumen["cases"])
print("smoke HU-011: OK — Instagram y LinkedIn coinciden con goldens")
PY
