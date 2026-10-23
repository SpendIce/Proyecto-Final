#!/usr/bin/env bash
# Demo visual del Agente 1, lanzada desde la laptop.
#
# Desde el 23/10/2026 el agente corre en contenedores en el servidor (stack
# `agente1` de Portainer, ADR 0013): la consola ya está levantada y se
# reinicia sola. Este script no arranca nada en el servidor:
#   1. verifica el acceso por Tailscale (`fie-server-ts`);
#   2. verifica que la consola del contenedor responda en 127.0.0.1:8090;
#   3. abre un túnel SSH y el navegador en http://127.0.0.1:$PORT.
#
# El smoke y la corrida completa se corren dentro del contenedor (ver
# Documentos/PlanDespliegue/Runbook-Contenedores-Agente-1.md).
#
# Uso:
#   ./run-demo-plan-a.sh
#   FIE_HOST=fie-server PORT=8091 ./run-demo-plan-a.sh

set -euo pipefail

HOST="${FIE_HOST:-fie-server-ts}"
PORT="${PORT:-8090}"
PUERTO_REMOTO="${PUERTO_REMOTO:-8090}"

echo "== 1. Acceso por Tailscale =="
ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" 'hostname' >/dev/null
echo "OK: $HOST"

echo "== 2. Consola del contenedor =="
if ! ssh "$HOST" "curl -fsS --max-time 5 http://127.0.0.1:$PUERTO_REMOTO/health" >/dev/null; then
  echo "ERROR: la consola del contenedor no responde en el servidor." >&2
  echo "Mirá el stack 'agente1' en Portainer (logs del servicio 'consola')." >&2
  exit 1
fi
echo "OK: consola en 127.0.0.1:$PUERTO_REMOTO del servidor"

echo "== 3. Túnel y navegador =="
ssh -N \
  -o ControlMaster=no \
  -o ControlPath=none \
  -o ExitOnForwardFailure=yes \
  -L "$PORT:127.0.0.1:$PUERTO_REMOTO" "$HOST" &
TUNNEL_PID=$!
trap 'kill "$TUNNEL_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 30); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

URL="http://127.0.0.1:$PORT"
echo "Demo visual: $URL"
echo "Ctrl-C para cortar el túnel (la consola sigue corriendo en el servidor)."
xdg-open "$URL" >/dev/null 2>&1 || true

wait "$TUNNEL_PID"
