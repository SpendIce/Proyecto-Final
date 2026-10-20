#!/usr/bin/env bash
# Plan B de la demo del 21/10/2026: credencial OAuth anterior.
#
# El archivo de entorno vive fuera del repo y trae el trío OAuth, la hoja v2
# sintética, la carpeta y la plantilla D2. El script:
#   1. carga ese entorno;
#   2. borra el par de la cuenta de servicio y el access token efímero, para
#      que `construir_token_provider` no pueda elegir otra credencial;
#   3. corre el comando pedido. Sin argumentos, corre la corrida única live
#      con `gemma4:e4b` y la solicitud `SYN-002`.
#
# Uso:
#   bash scripts/corrida_plan_b_oauth.sh --check
#   bash scripts/corrida_plan_b_oauth.sh
#   bash scripts/corrida_plan_b_oauth.sh uv run python scripts/workspace_smoke.py --live --id-solicitud SYN-002
#
# El trío OAuth es una contingencia declarada hasta #99. La identidad objetivo
# sigue siendo la cuenta de servicio (ADR 0011).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_PLANB="${AGENTE1_PLANB_ENV:-$HOME/.config/agente1/workspace-d2-planb.env}"

if [[ ! -f "$ENV_PLANB" ]]; then
  echo "ERROR: falta el entorno Plan B: $ENV_PLANB" >&2
  echo "Copiá el archivo desde la máquina del autor, fuera del repo, con chmod 600." >&2
  exit 1
fi

# Cargar el entorno completo del Plan B.
set -a
# shellcheck disable=SC1090
source "$ENV_PLANB"
set +a

# El par de la cuenta de servicio tiene prioridad en `construir_token_provider`.
# Si quedó exportado en la shell, se borra acá y se verifica que no vuelva.
unset AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY
unset AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT
unset AGENTE1_WORKSPACE_ACCESS_TOKEN

if [[ -n "${AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY:-}" ]]; then
  echo "ERROR: la cuenta de servicio sigue en el entorno; no se puede forzar OAuth." >&2
  exit 1
fi
if [[ -z "${AGENTE1_WORKSPACE_OAUTH_CLIENT_ID:-}" \
   || -z "${AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET:-}" \
   || -z "${AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN:-}" ]]; then
  echo "ERROR: el trío OAuth del Plan B está incompleto." >&2
  exit 1
fi
if [[ -z "${AGENTE1_WORKSPACE_SPREADSHEET_ID:-}" \
   || -z "${AGENTE1_WORKSPACE_RANGO_A1:-}" \
   || -z "${AGENTE1_WORKSPACE_FOLDER_ID:-}" \
   || -z "${AGENTE1_WORKSPACE_TEMPLATE_ID:-}" ]]; then
  echo "ERROR: faltan recursos de Workspace en el entorno Plan B." >&2
  exit 1
fi

echo "Plan B OAuth: hoja v2 sintética (${AGENTE1_WORKSPACE_RANGO_A1}), ambiente ${AGENTE1_WORKSPACE_AMBIENTE}." >&2

cd "$ROOT"

case "${1:-}" in
  --check)
    # Dry-run del preflight (sin red) y smoke live de sólo lectura.
    uv run python scripts/corrida_unica.py --modelo gemma4:e4b --id-solicitud SYN-002
    uv run python scripts/workspace_smoke.py --live --id-solicitud SYN-002
    exit $?
    ;;
  "")
    exec uv run python scripts/corrida_unica.py \
      --live \
      --modelo gemma4:e4b \
      --id-solicitud SYN-002
    ;;
  *)
    exec "$@"
    ;;
esac
