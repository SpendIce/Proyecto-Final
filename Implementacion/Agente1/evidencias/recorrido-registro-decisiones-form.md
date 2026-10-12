# Recorrido — registro de decisiones por el segundo Form (#72)

## Qué demuestra

- Que el correo de «borrador listo» del canal de pedidos declara el pedido
  como objeto de decisión y adjunta los dos links prellenados del Form de
  decisiones («Lo publiqué» / «Lo descarté»), para HU-010 (gacetilla) y
  HU-011 (post).
- Que una respuesta del Form de decisiones se registra sólo si el correo
  verificado está en el padrón **y** su rol es el que la decisión exige,
  quedando en la auditoría con identidad hasheada, rol, código y fecha con
  zona horaria.
- Que un link alterado se rechaza con código registrado: tipo fuera del
  catálogo (`tipo_desconocido`), decisión inválida para el tipo
  (`decision_fuera_de_catalogo`), id sin forma (`objeto_invalido`) o id que
  el agente nunca declaró (`objeto_inexistente`).
- Que registrar la decisión no dispara nada: no hay publicación, ni envío,
  ni efecto lateral. La difusión la hace la persona.

## Qué NO demuestra

El recorrido offline no acredita la verificación de identidad de Google: el
correo se lee del CSV igual que vendría de la hoja, pero el atributo
«verificado por Google» sólo existe cuando el Form real lo recolecta
(restricción de dominio + colecta de correo, ADR 0005). La autorización por
rol sí se ensaya de verdad: el padrón es un archivo externo en ambos modos.

El criterio «demostradas en D2» del ticket queda **pendiente de la corrida
live**: exige el segundo Form creado en el Workspace D2, la hoja de
respuestas y el token efímero del operador. Los pasos live están abajo; lo
que este documento deja probado es el circuito completo con los runners
reales en modo offline, sin red.

## Antes de empezar

- No hace falta cuenta de Google ni credenciales: el modo offline usa un
  CSV como "hoja de respuestas" y escribe los avisos en un JSONL local.
- Hace falta una terminal en `Implementacion/Agente1` y un directorio de
  trabajo compartido entre los dos runners — el registro de decisiones vive
  en `<directorio>/estado-decisiones/` y lo leen los dos.
- El padrón es un CSV `correo,rol` externo al repo. Para el ensayo sirve uno
  con correos inventados; en producción lo arma la SEU desde el acta del
  22/09.

## Paso a paso (offline)

### 1. Preparar directorio, padrón y "hoja" de pedidos

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-decisiones
cat > /tmp/demo-decisiones/padron.csv <<'EOF'
correo,rol
solicitante@example.invalid,coordinador_seu
rgc@example.invalid,RESPONSABLE_GESTION_CONOCIMIENTO
coord@example.invalid,COORDINADOR_EXTENSION
EOF
cat > /tmp/demo-decisiones/pedidos.csv <<'EOF'
Marca temporal,Correo,Pedido
2026-10-10 09:00:00,solicitante@example.invalid,gacetilla SYN-001
EOF
```

### 2. Atender el pedido: el correo declara el pendiente y trae los links

```bash
PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-decisiones \
  --respuestas-csv /tmp/demo-decisiones/pedidos.csv \
  --padron /tmp/demo-decisiones/padron.csv
```

El pedido queda `PENDIENTE_VALIDACION`. En
`/tmp/demo-decisiones/estado-decisiones/decisiones-pendientes.jsonl` aparece
el objeto declarado (id hash del pedido, `pieza: gacetilla`, correlación) y
en `estado-canal-form/avisos-offline.jsonl` el cuerpo del correo, que trae:

```text
La difusión la hace una persona. Cuando definas qué pasa con el borrador,
registrá la decisión con tu correo verificado:
Lo publiqué: https://docs.google.com/forms/d/e/form_decisiones_offline/viewform?usp=pp_url&entry.000000021=publicacion&entry.000000022=<objeto>&entry.000000023=publique
Lo descarté: ...&entry.000000023=descarte
```

Para HU-011 el pedido sería `post de instagram para SYN-001` y el detalle
del pendiente registra `pieza: post` — el circuito es el mismo.

### 3. Registrar decisiones: válida, fuera del padrón, link alterado, lote

```bash
cat > /tmp/demo-decisiones/decisiones.csv <<EOF
Marca temporal,Correo,Tipo,Objeto,Decisión
2026-10-11 09:00:00,rgc@example.invalid,publicacion,<objeto>,publique
2026-10-11 09:05:00,desconocido@example.invalid,publicacion,<objeto>,publique
2026-10-11 09:10:00,coord@example.invalid,publicacion,id-inventado-9,publique
2026-10-11 09:15:00,coord@example.invalid,lote,lote-2026-10,apruebo_lote
EOF
PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-decisiones \
  --respuestas-csv /tmp/demo-decisiones/decisiones.csv \
  --padron /tmp/demo-decisiones/padron.csv \
  --declarar lote:lote-2026-10
```

(`<objeto>` es el `objeto_id` del pendiente de la línea 2. `--declarar` abre
el lote e imprime su link — es el camino manual para plantillas y lotes que
los correos de #73/#75 automatizarán.)

Resultado esperado, una línea JSON por respuesta:

| Respuesta | Resultado | Código |
|---|---|---|
| `publique` del RGC | `registrada` | — |
| correo fuera del padrón | `rechazada` | `fuera_de_padron` |
| id inventado | `rechazada` | `objeto_inexistente` |
| `apruebo_lote` del Coordinador | `registrada` | — |

Relanzar el mismo comando no duplica: el id de respuesta (hash de la fila)
ya está en `decisiones-procesadas.jsonl`.

## Camino live D2 (pendiente del operador)

Mismo circuito, con el segundo Form creado en el Workspace D2 restringido al
dominio y con colecta de correo, y las variables del entorno cargadas:

```text
AGENTE1_WORKSPACE_AMBIENTE=D2
AGENTE1_WORKSPACE_*            # fuente de actividades, carpeta, plantilla
AGENTE1_FORM_PEDIDOS_*         # Form de pedidos (#71)
AGENTE1_FORM_DECISIONES_*      # Form de decisiones (#72): SHEET_ID, RANGO_A1,
                               # FORM_ID, ENTRY_TIPO, ENTRY_OBJETO,
                               # ENTRY_DECISION, TIMEOUT_S
AGENTE1_PADRON_ROLES_PATH      # padrón fuera del repo
AGENTE1_GMAIL_DESTINATARIOS_PRUEBA
AGENTE1_WORKSPACE_ACCESS_TOKEN # token efímero, nunca por argv
```

```bash
PYTHONPATH=src python scripts/atender_canal_form.py \
  --live --confirm-write-workspace --directorio <dir>
PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --live --confirm-write-workspace --directorio <dir>
```

Los dos runners exigen el doble opt-in y fallan antes de tocar la red si la
configuración está incompleta. El agente sólo lee ambas hojas y sólo escribe
el correo de aviso por `gmail.send` bajo la lista de prueba.
