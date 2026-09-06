#!/usr/bin/env bash
set -euo pipefail

# Smoke opt-in contra un Ollama YA iniciado en loopback, con el modelo
# descargado. Es el único smoke que necesita un modelo real; sirve para
# confirmar que el adapter y el entorno hablan entre sí, no para medir calidad
# (para eso están las matrices live y `medir_capacidad_hu011.py`).
# Configurable por entorno: OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
# OLLAMA_NUM_PREDICT.

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base_url="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
model="${OLLAMA_MODEL:-llama3.2:3b}"
timeout_s="${OLLAMA_TIMEOUT:-45}"
num_predict="${OLLAMA_NUM_PREDICT:-112}"

curl --fail --silent --show-error "${base_url}/api/tags" \
  | python -c '
import json
import sys

model = sys.argv[1]
documento = json.load(sys.stdin)
disponibles = {item.get("name") for item in documento.get("models", [])}
if model not in disponibles:
    raise SystemExit(f"El modelo {model!r} no está descargado en Ollama")
' "${model}"

mkdir -p "${repo_dir}/salida"
salida_dir="$(mktemp -d "${repo_dir}/salida/smoke-ollama.XXXXXX")"

PYTHONPATH="${repo_dir}/src" \
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/agente1-pycache}" \
python -m agente1 \
  --csv "${repo_dir}/data/actividades_sinteticas.csv" \
  --id-solicitud SYN-001 \
  --salida "${salida_dir}" \
  --ollama-model "${model}" \
  --ollama-base-url "${base_url}" \
  --ollama-timeout "${timeout_s}" \
  --ollama-num-predict "${num_predict}"

python - "${salida_dir}" <<'PY'
import json
from pathlib import Path
import sys

salida = Path(sys.argv[1])
borrador = salida / "borradores" / "SYN-001.md"
registros = (salida / "logs" / "ejecuciones.jsonl").read_text(
    encoding="utf-8"
).splitlines()
ultimo = json.loads(registros[-1])
assert ultimo["estado"] == "PENDIENTE_VALIDACION"
assert ultimo["resultado"] == "borrador_generado"
assert borrador.read_text(encoding="utf-8").startswith("# BORRADOR — NO PUBLICAR\n")
assert "pruebas@example.invalid" not in registros[-1]
print(f"smoke Ollama HU-010: OK — evidencia runtime en {salida}")
PY
