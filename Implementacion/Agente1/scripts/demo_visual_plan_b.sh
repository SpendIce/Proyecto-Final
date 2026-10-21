#!/usr/bin/env bash
# Consola visual de la demo, del lado del servidor.
#
# Carga el entorno Plan B (OAuth + hoja v2 sintética), quita del proceso el par
# de la cuenta de servicio y el access token efímero, y levanta la consola en
# loopback. El par de la cuenta de servicio sigue intacto en
# ~/.config/agente1/workspace-d2.env y en cuenta-servicio.json: esto sólo
# cambia la credencial del proceso de la demo.
#
# Uso:
#   bash scripts/demo_visual_plan_b.sh
#   PORT=8081 bash scripts/demo_visual_plan_b.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_PLANB="${AGENTE1_PLANB_ENV:-$HOME/.config/agente1/workspace-d2-planb.env}"
PORT="${PORT:-8080}"

if [[ ! -f "$ENV_PLANB" ]]; then
  echo "ERROR: falta el entorno Plan B: $ENV_PLANB" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PLANB"
set +a

export AGENTE1_DEMO_AUTH=oauth

unset AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY
unset AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT
unset AGENTE1_WORKSPACE_ACCESS_TOKEN

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
