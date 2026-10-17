# Recorrido: propuesta de intención y confirmación por correo y Form (#27, #115)

## Qué demuestra

- Que un pedido que la clasificación determinística no reconoce («necesito la
  gasetiya del taller sintetico») hace intervenir al modelo para **proponer**
  una intención permitida (`generar_gacetilla` o `generar_post`), y que esa
  propuesta **no genera ningún borrador**: el log del núcleo queda con
  `pipeline_correlation_id: null` y el directorio de borradores no existe.
- Que la propuesta vuelve por el correo de aviso existente con **un enlace al
  mismo Form de pedidos**, prellenado **por código** con la intención permitida
  y el identificador de la actividad resuelta contra la fuente institucional.
  El aviso no copia prosa del usuario ni del modelo.
- Que abrir el enlace no ejecuta nada y que **reenviar** el prellenado
  constituye un pedido nuevo, que se clasifica, resuelve y autoriza otra vez, y
  recién ahí produce el borrador.
- Que el enlace no depende de un estado pendiente entre turnos ni de un
  vencimiento de quince minutos: el prellenado trae un identificador explícito
  que el núcleo resuelve solo.
- Que la suite cubre los caminos negativos desde los puertos públicos: salida
  inválida, inyección, intención fuera del conjunto permitido, actividad
  ausente o ambigua, canal de post faltante, cambio de padrón entre la
  propuesta y el reenvío, y registro de auditoría sin prosa ni correo en claro.

## Qué NO demuestra

El recorrido offline usa un **intérprete fake declarado**
(`_InterpreteOffline` en `scripts/atender_canal_form.py`), igual que el
generador del modo offline: devuelve una propuesta fija con los términos
normalizados de la fila `SYN-001` del dataset, en lugar de correr el modelo
local. No acredita la calidad de la propuesta de un modelo real ni su
disponibilidad; en live el intérprete es `OllamaGenerator`.

Tampoco acredita aceptación de la SEU ni un nivel TRL: es evidencia técnica del
circuito. La corrida live con el modelo local y el Form real queda a cargo del
operador (ver abajo).

## Antes de empezar

- No hace falta cuenta de Google: el modo offline usa un CSV como «hoja de
  respuestas» y escribe los avisos en un JSONL local.
- Hace falta una terminal en `Implementacion/Agente1` y el padrón como CSV
  `correo,rol` externo al repo.

## Paso a paso (offline)

### 1. Preparar el directorio, el padrón y la «hoja» de pedidos

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-propuesta
cat > /tmp/demo-propuesta/padron.csv <<'EOF'
correo,rol
solicitante@example.invalid,coordinador_seu
EOF
cat > /tmp/demo-propuesta/pedidos.csv <<'EOF'
Marca temporal,Correo,Pedido
2026-10-16 09:00:00,solicitante@example.invalid,Necesito la gasetiya del taller sintetico
EOF
```

### 2. Atender el pedido: la propuesta sale por correo y no genera nada

```bash
PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-propuesta/estado \
  --respuestas-csv /tmp/demo-propuesta/pedidos.csv \
  --padron /tmp/demo-propuesta/padron.csv
```

Salida:

```json
{"correlation_id": "fb9e3d28-c81d-44cc-aec0-ab7f2318d73d", "estado": "PENDIENTE_CONFIRMACION", "intencion": "generar_gacetilla"}
{"atendidos": 1, "config": {"certificados": false, "modo_offline": true, "planes_pago": 0}, "modo": "offline_fake", "registro_atendidos": "atendidos-canal-form.jsonl"}
```

El aviso en `/tmp/demo-propuesta/estado/estado-canal-form/avisos-offline.jsonl`:

```text
Asunto: [Agente 1] Pedido c82b5aa0ec66: confirmá el pedido
BORRADOR — NO ENVIAR

Tu pedido (ref. c82b5aa0ec66) no se reconoció como una pieza del catálogo, así que no se generó nada.
Gacetilla para 'Taller sintético de vinculación' (2026-08-05).

Si es correcto, revisá el formulario y envialo: ese envío es un pedido nuevo y recién ahí se genera.
Abrir el enlace no confirma nada. Podés editarlo antes de enviarlo:
https://docs.google.com/forms/d/e/form_offline_demo/viewform?usp=pp_url&entry.000000001=gacetilla%20actividad%20SYN-001%20%28pedido%20c82b5aa0ec66%29
```

El prellenado del enlace, decodificado, es `gacetilla actividad SYN-001
(pedido c82b5aa0ec66)`: la palabra clave que el núcleo vuelve a clasificar, el
identificador explícito de la actividad y la referencia del pedido original
sólo como trazabilidad. No hay prosa de la persona ni del modelo.

No hay borrador: `estado/borradores/` no existe. La auditoría del núcleo
registra la propuesta sin despacho:

```json
{"intencion": "generar_gacetilla", "id_actividad": "SYN-001", "modelo_utilizado": true, "estado": "PENDIENTE_CONFIRMACION", "resultado": "propuesta_generada", "pipeline_correlation_id": null}
```

### 3. Reenviar el prellenado: ahora sí es un pedido nuevo y genera el borrador

Se agrega la respuesta que el Form escribiría al enviar el enlace:

```bash
printf '2026-10-16 09:30:00,solicitante@example.invalid,gacetilla actividad SYN-001 (pedido c82b5aa0ec66)\n' \
  >> /tmp/demo-propuesta/pedidos.csv
PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-propuesta/estado \
  --respuestas-csv /tmp/demo-propuesta/pedidos.csv \
  --padron /tmp/demo-propuesta/padron.csv
```

Salida:

```json
{"correlation_id": "f57508be-e87b-4d75-ac9a-8741f3e46268", "estado": "PENDIENTE_VALIDACION", "intencion": "generar_gacetilla"}
{"atendidos": 1, "config": {"certificados": false, "modo_offline": true, "planes_pago": 0}, "modo": "offline_fake", "registro_atendidos": "atendidos-canal-form.jsonl"}
```

El borrador queda en `/tmp/demo-propuesta/estado/borradores/SYN-001.md` y el
aviso dice `tu borrador está listo`. La segunda línea del log marca
`modelo_utilizado: false`: el pedido nuevo lo resolvió entero el camino
determinístico. La confirmación no aprobó nada: el borrador sigue
`PENDIENTE_VALIDACION` y su validación humana es la de siempre.

## Verificaciones de CI

Desde `Implementacion/Agente1`:

```bash
uv run pytest -q      # 2201 passed, 8 skipped
uv run ruff check .   # All checks passed!
```

Las pruebas del circuito (seam y canal) viven en `tests/test_interpretacion.py`
(sección 14) y `tests/test_canal_form.py` (sección «Propuesta de intención por
correo y confirmación por el Form»).

## Camino live D2 (pendiente del operador)

Mismo circuito con el intérprete real (`OllamaGenerator`) sobre el Form de
pedidos del ambiente D2 y las variables de siempre:

```text
AGENTE1_WORKSPACE_AMBIENTE=D2
AGENTE1_WORKSPACE_*            # fuente de actividades, carpeta, plantilla
AGENTE1_FORM_PEDIDOS_*         # Form de pedidos (#71)
AGENTE1_PADRON_ROLES_PATH      # padrón fuera del repo
AGENTE1_GMAIL_DESTINATARIOS_PRUEBA
AGENTE1_WORKSPACE_ACCESS_TOKEN # token efímero, nunca por argv
```

```bash
PYTHONPATH=src python scripts/atender_canal_form.py \
  --live --confirm-write-workspace --directorio <dir> --modelo <modelo-ollama>
```

El pedido con el nombre de la pieza mal escrito devuelve
`PENDIENTE_CONFIRMACION` por correo, con el enlace prellenado; nada se escribe
en Drive hasta que la persona envíe el Form.
