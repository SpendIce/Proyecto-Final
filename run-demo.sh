#!/usr/bin/env bash
# Demo guiada para el tutor — Agente 1, Extension Bot (P100).
# Corre la muestra de avance en el orden sugerido:
#   1) Visor Gantt (plan vs avance real) + visor del plan de riesgos
#   2) HU-014 certificados (matriz offline, doble aprobación, PDF borrador)
#   3) HU-012 notificaciones (matriz offline, doble aprobación, fail-closed)
#   4) HU-013 canal de planilla (pedido en prosa → borrador / repregunta / rechazo)
#   5) Comparación de modelos HU-011 (evidencia, no en vivo)
#
# Todo es offline, sin credenciales, sin red y sin modelo instalado.
# Uso: ./run-demo.sh   (avanza con Enter entre pasos; Ctrl-C para cortar)

set -euo pipefail
cd "$(dirname "$0")"

AG="Implementacion/Agente1"
PY="$AG/.venv/bin/python"
DEMO_DIR="$AG/salida/demo-tutor"
CANAL_DIR="$DEMO_DIR/canal"

paso() { printf '\n\033[1;36m=== %s ===\033[0m\n' "$1"; }
pausa() { printf '\033[1;33m[Enter para continuar]\033[0m '; read -r _ || true; }

# ---------- chequeo de entorno ----------
paso "0. Chequeo de entorno"
faltan=0
for f in "$PY" \
  "Documentos/Gantt/visor-gantt-implementacion-semanal.html" \
  "Documentos/PlanRiesgos/visor-plan-riesgos.html" \
  "$AG/scripts/matriz_hu014.py" \
  "$AG/scripts/matriz_hu012.py" \
  "$AG/scripts/atender_canal_planilla.py" \
  "$AG/evidencias/medicion-hu011-v3-modelos-2026-09-23.md" \
  "$AG/data/actividades_sinteticas.csv"; do
  if [ -e "$f" ]; then echo "  ok  $f"; else echo "  FALTA  $f"; faltan=1; fi
done
[ "$faltan" -eq 0 ] || { echo "Faltan archivos — abortar."; exit 1; }
rm -rf "$DEMO_DIR"
mkdir -p "$CANAL_DIR"
echo "Salida de la demo: $DEMO_DIR"
pausa

# ---------- 1. visores ----------
paso "1. Plan y avance: visor Gantt + plan de riesgos"
echo "Se abren en el navegador (archivos locales, sin servidor):"
echo "  - Documentos/Gantt/visor-gantt-implementacion-semanal.html"
echo "  - Documentos/PlanRiesgos/visor-plan-riesgos.html"
xdg-open "$PWD/Documentos/Gantt/visor-gantt-implementacion-semanal.html" >/dev/null 2>&1 || true
xdg-open "$PWD/Documentos/PlanRiesgos/visor-plan-riesgos.html" >/dev/null 2>&1 || true
echo
echo "A mostrar en pantalla:"
echo "  · Gantt: plan (.mmd) vs avance real (gantt-progreso.js) — bloqueantes externos visibles."
echo "  · Riesgos: matriz P×I, R-ALC-03 materializado 22/09 (⚑), respuesta aplicada."
pausa

# ---------- 2. HU-014 ----------
paso "2. HU-014 — Certificados con doble aprobación (offline)"
echo "Matriz contractual completa: pendiente → aprobación parcial → aprobada"
echo "en ambos órdenes → rechazada → duplicada → emisión simulada → recuperación durable."
"$PY" "$AG/scripts/matriz_hu014.py" --salida "$DEMO_DIR/hu014"
echo
echo "Estados observados:"
"$PY" - "$DEMO_DIR/hu014/matriz.json" <<'EOF'
import json, sys
t = json.load(open(sys.argv[1]))["totals"]
for k, v in t.items():
    print(f"  {k}: {v}")
EOF
echo
echo "PDFs generados — se abren en el visor:"
echo "  · casos/pending_base/certificado-borrador.pdf (marca BORRADOR — NO EMITIR)"
echo "  · casos/fake_emission/certificado-emitido-simulado.pdf (sin marca: ya 'emitido')"
xdg-open "$DEMO_DIR/hu014/casos/pending_base/certificado-borrador.pdf" >/dev/null 2>&1 || true
xdg-open "$DEMO_DIR/hu014/casos/fake_emission/certificado-emitido-simulado.pdf" >/dev/null 2>&1 || true
pausa

# ---------- 3. HU-012 ----------
paso "3. HU-012 — Notificaciones con doble aprobación (offline)"
echo "Mismo circuito: semántica (contenido correcto) + utilitaria (conviene enviar),"
echo "destino fake, cola durable, fail-closed en datos desconocidos."
"$PY" "$AG/scripts/matriz_hu012.py" --salida "$DEMO_DIR/hu012"
echo
echo "Estados observados:"
"$PY" - "$DEMO_DIR/hu012/matriz.json" <<'EOF'
import json, sys
t = json.load(open(sys.argv[1]))["totals"]
for k, v in t.items():
    print(f"  {k}: {v}")
EOF
pausa

# ---------- 4. HU-013 ----------
paso "4. HU-013 — Pedido en prosa por planilla (offline)"
echo "Ronda 1 — camino feliz: un pedido válido de la SEU."
cat > "$CANAL_DIR/pedidos.csv" <<'CSV'
id_pedido,identificador,rol,texto
1,jgone,coordinador_seu,Necesito una gacetilla para la actividad SYN-001 del martes
CSV
echo "pedidos.csv:"; sed 's/^/  /' "$CANAL_DIR/pedidos.csv"
echo
PYTHONPATH="$AG/src" "$PY" "$AG/scripts/atender_canal_planilla.py" --directorio "$CANAL_DIR"
echo
echo "respuestas.csv (se abre en la app de planillas — es lo que vería la SEU):"
sed 's/^/  /' "$CANAL_DIR/respuestas.csv"
xdg-open "$CANAL_DIR/respuestas.csv" >/dev/null 2>&1 || true
echo
echo "Borrador generado (PENDIENTE_VALIDACION, no publicable sin humano):"
cat "$CANAL_DIR"/borradores/*.md | head -25
xdg-open "$CANAL_DIR"/borradores/*.md >/dev/null 2>&1 || true
pausa

echo "Ronda 2 — repregunta (sin identificador) + rechazo (rol no habilitado):"
cat >> "$CANAL_DIR/pedidos.csv" <<'CSV'
2,jgone,coordinador_seu,Necesito una gacetilla para el taller del martes
3,visitante,visitante,Necesito una gacetilla para la actividad SYN-001
CSV
PYTHONPATH="$AG/src" "$PY" "$AG/scripts/atender_canal_planilla.py" --directorio "$CANAL_DIR"
echo
echo "respuestas.csv completo (se reabre actualizado):"
sed 's/^/  /' "$CANAL_DIR/respuestas.csv"
xdg-open "$CANAL_DIR/respuestas.csv" >/dev/null 2>&1 || true
echo
echo "Auditoría (identidad_verificada siempre false, texto nunca guardado — solo hash):"
sed 's/^/  /' "$CANAL_DIR/logs/interpretaciones-hu013.jsonl" | head -5
pausa

# ---------- 5. modelos ----------
paso "5. HU-011 — Comparación de modelos (evidencia, no en vivo)"
awk '/## 1\. Resultado por modelo/,/## 2\./' \
  "$AG/evidencias/medicion-hu011-v3-modelos-2026-09-23.md" | head -20
echo
echo "Lectura: mismo gate, mismo prompt, misma matriz — el modelo concreto importa."
echo "Residuales del 8B son lo que el few-shot con ejemplos SEU (#14) buscaría cerrar."
pausa

paso "Cierre"
echo "Lo que NO se mostró (bloqueantes externos, no falta de trabajo):"
echo "  · OAuth/Workspace live, plantilla institucional, validación humana SEU,"
echo "    autenticación, criterio G2 — todos marcados BLOQUEADO_EXTERNO en el Gantt."
echo "  · Suite de tests: 944 verdes (uv run pytest -q en Implementacion/Agente1)."
echo
echo "Artefactos de esta corrida en: $DEMO_DIR"
echo "  · hu014/matriz.json + PDFs  · hu012/matriz.json  · canal/{pedidos,respuestas}.csv + borradores + logs"
