#!/usr/bin/env bash
# Demo visual con la cuenta de servicio (Plan A), lanzada desde la laptop.
#
# Hace todo el camino:
#   1. verifica el acceso por Tailscale (`fie-server-ts`);
#   2. actualiza el repo del servidor a main;
#   3. corre el preflight y el smoke live con el entorno normal del servidor;
#   4. levanta la consola visual con la cuenta de servicio;
#   5. abre un túnel SSH y el navegador en http://127.0.0.1:8080.
#
# No copia la clave de la cuenta de servicio: usa la que ya está en el servidor.
# El entorno `workspace-d2.env` apunta a la hoja v2. Para el Plan B OAuth, usá
# `run-demo-planb.sh`.
#
# Uso:
#   ./run-demo-plan-a.sh
#   FIE_HOST=fie-server PORT=8081 ./run-demo-plan-a.sh

set -euo pipefail

HOST="${FIE_HOST:-fie-server-ts}"
PORT="${PORT:-8080}"
REPO_REMOTO="${REPO_REMOTO:-~/p100/Agente1}"
PID_REMOTO="/tmp/demo-visual-plana.pid"
LOG_REMOTO="/tmp/demo-visual-plana.log"

echo "== 1. Acceso por Tailscale =="
ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" 'hostname; whoami' >/dev/null
echo "OK: $HOST"

echo "== 2. Repo del servidor =="
ssh "$HOST" "cd $REPO_REMOTO && git switch main && git pull --ff-only"

echo "== 3. Preflight y smoke live con cuenta de servicio =="
ssh "$HOST" "cd $REPO_REMOTO/Implementacion/Agente1 && set -a; . ~/.config/agente1/workspace-d2.env; set +a; .venv/bin/python scripts/corrida_unica.py --modelo gemma4:e4b --id-solicitud FIE-DIF-08 --timeout-modelo 300 --evidencia-dir /tmp/plan-a-check && .venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08"

echo "== 4. Consola visual =="
ssh "$HOST" "if [ -f $PID_REMOTO ]; then kill \$(cat $PID_REMOTO) 2>/dev/null || true; rm -f $PID_REMOTO; fi"
ssh "$HOST" "cd $REPO_REMOTO/Implementacion/Agente1 && PORT=$PORT AGENTE1_DEMO_AUTH=service_account nohup bash scripts/demo_visual_plan_a.sh >$LOG_REMOTO 2>&1 & echo \$! >$PID_REMOTO"

echo "== 5. Túnel y navegador =="
ssh -N \
  -o ControlMaster=no \
  -o ControlPath=none \
  -o ExitOnForwardFailure=yes \
  -L "$PORT:127.0.0.1:$PORT" "$HOST" &
TUNNEL_PID=$!

limpiar() {
  kill "$TUNNEL_PID" 2>/dev/null || true
  ssh "$HOST" "kill \$(cat $PID_REMOTO) 2>/dev/null || true; rm -f $PID_REMOTO" >/dev/null 2>&1 || true
}
trap limpiar EXIT INT TERM

for _ in $(seq 1 30); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "ERROR: la consola no respondió. Log remoto:" >&2
  ssh "$HOST" "tail -40 $LOG_REMOTO" >&2 || true
  exit 1
fi

URL="http://127.0.0.1:$PORT"
echo "Demo visual: $URL"
echo "Ctrl-C para cortar."
xdg-open "$URL" >/dev/null 2>&1 || true

wait "$TUNNEL_PID"
