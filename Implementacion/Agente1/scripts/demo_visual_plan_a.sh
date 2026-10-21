#!/usr/bin/env bash
# Consola visual de la demo con la cuenta de servicio (Plan A).
#
# Usa el entorno normal del servidor, que ya apunta a la hoja v2 y trae el par
# de la cuenta de servicio. No copia ni modifica la clave. La consola conserva
# el par en el subproceso del agente; el modo OAuth queda para el launcher
# `demo_visual_plan_b.sh`.
#
# Uso:
#   bash scripts/demo_visual_plan_a.sh
#   PORT=8081 bash scripts/demo_visual_plan_a.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_PLANA="${AGENTE1_PLANA_ENV:-$HOME/.config/agente1/workspace-d2.env}"
PORT="${PORT:-8080}"

if [[ ! -f "$ENV_PLANA" ]]; then
  echo "ERROR: falta el entorno Plan A: $ENV_PLANA" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PLANA"
set +a

export AGENTE1_DEMO_AUTH=service_account
unset AGENTE1_WORKSPACE_ACCESS_TOKEN

if [[ -z "${AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY:-}" \
   || -z "${AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT:-}" ]]; then
  echo "ERROR: falta el par de la cuenta de servicio en $ENV_PLANA." >&2
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON=("$ROOT/.venv/bin/python")
else
  UV="${UV:-$(command -v uv || true)}"
  if [[ -z "$UV" && -x "$HOME/.local/bin/uv" ]]; then
    UV="$HOME/.local/bin/uv"
  fi
  if [[ -z "$UV" ]]; then
    echo "ERROR: no hay .venv/bin/python ni uv disponible." >&2
    exit 1
  fi
  PYTHON=("$UV" "run" "python")
fi

cd "$ROOT"
exec "${PYTHON[@]}" scripts/demo_visual_plan_b.py --host 127.0.0.1 --port "$PORT"
