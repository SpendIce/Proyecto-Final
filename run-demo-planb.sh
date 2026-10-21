#!/usr/bin/env bash
# Demo visual del Plan B OAuth, lanzada desde la laptop.
#
# Hace todo el camino:
#   1. verifica el acceso por Tailscale (`fie-server-ts`);
#   2. copia el entorno Plan B al servidor;
#   3. actualiza el repo del servidor a main;
#   4. corre el preflight y el smoke live;
#   5. levanta la consola visual en el servidor;
#   6. abre un túnel SSH y el navegador en http://127.0.0.1:8080.
#
# Uso:
#   ./run-demo-planb.sh
#   FIE_HOST=fie-server PORT=8081 ./run-demo-planb.sh
#
# Ctrl-C corta el túnel y la consola. El par de la cuenta de servicio no se
# toca: sigue en el entorno del servidor para cuando se habilite Plan A.

set -euo pipefail

HOST="${FIE_HOST:-fie-server-ts}"
PORT="${PORT:-8080}"
REPO_REMOTO="${REPO_REMOTO:-~/p100/Agente1}"
ENV_LOCAL="${AGENTE1_PLANB_ENV:-$HOME/.config/agente1/workspace-d2-planb.env}"
ENV_REMOTO="~/.config/agente1/workspace-d2-planb.env"
PID_REMOTO="/tmp/demo-visual-planb.pid"
LOG_REMOTO="/tmp/demo-visual-planb.log"

if [[ ! -f "$ENV_LOCAL" ]]; then
  echo "ERROR: falta el entorno Plan B local: $ENV_LOCAL" >&2
  exit 1
fi

echo "== 1. Acceso por Tailscale =="
ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" 'hostname; whoami' >/dev/null
echo "OK: $HOST"

echo "== 2. Entorno Plan B =="
ssh "$HOST" 'mkdir -p ~/.config/agente1 && chmod 700 ~/.config/agente1'
scp -q "$ENV_LOCAL" "$HOST:$ENV_REMOTO"
ssh "$HOST" "chmod 600 $ENV_REMOTO"
echo "OK: $ENV_REMOTO"

echo "== 3. Repo del servidor =="
ssh "$HOST" "cd $REPO_REMOTO && git switch main && git pull --ff-only"

echo "== 4. Preflight y smoke live =="
ssh "$HOST" "cd $REPO_REMOTO && bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh --check"

echo "== 5. Consola visual =="
ssh "$HOST" "if [ -f $PID_REMOTO ]; then kill \$(cat $PID_REMOTO) 2>/dev/null || true; rm -f $PID_REMOTO; fi"
ssh "$HOST" "cd $REPO_REMOTO/Implementacion/Agente1 && PORT=$PORT nohup bash scripts/demo_visual_plan_b.sh >$LOG_REMOTO 2>&1 & echo \$! >$PID_REMOTO"

echo "== 6. Túnel y navegador =="
ssh -N -L "$PORT:127.0.0.1:$PORT" "$HOST" &
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
