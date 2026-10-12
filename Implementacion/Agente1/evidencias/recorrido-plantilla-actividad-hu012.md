# Recorrido — plantilla de correo por actividad (#73 / HU-012)

## Qué demuestra

- Que el pedido «generá la plantilla de correos de la actividad» produce
  **una plantilla por actividad**: el modelo redacta sólo prosa descriptiva
  sobre la base provisional `PENDIENTE_SEU` y todos los datos dinámicos
  —montos, cuotas, fechas, horarios, enlaces, destinatario— viajan como
  variables `{{...}}` del catálogo `plantilla_actividad_v1`.
- Que el gate descarta la salida entera ante cualquier incumplimiento:
  variable faltante, renombrada, desconocida o sin dato que la llene;
  dígito, fecha, importe, correo o enlace en el texto; hecho copiado de la
  fuente. El éxito es `PENDIENTE_VALIDACION`, nunca una pieza lista.
- Que la generación deja dos objetos abiertos a decisión en el Form de #72
  —la plantilla (`tpl-…`) con la doble aprobación semántica + utilitaria y
  el lote (`lote-…`) con `apruebo_lote`—, ids derivados del `sha256` del
  documento: otra redacción produce otros objetos y reinicia el circuito.
- Que sin las tres decisiones `registrada` no se encola nada
  (`template_not_approved` / `batch_not_approved`), y que con las tres el
  correo de cada preinscripto se renderiza **determinista y sin modelo** —
  la plantilla aprobada más actividad, plan de pago y padrón—, se encola
  con clave idempotente de actividad+inscripción+hash y se drena por el
  `DestinoConfirmacionesFake` con la marca `BORRADOR — NO ENVIAR`.
- Que re-correr con la misma plantilla aprobada es `DUPLICADA` y no
  reenvía, y que el `asunto` del correo sale del `asunto_preinscripcion`
  del plan —la misma llave con que la corrida de pagos asocia la respuesta
  con el comprobante (§4.2 del diseño).

## Qué NO demuestra

- No hay correo real: las entregas son archivos en
  `entregas-simuladas/` del directorio de trabajo. El adapter Gmail (#40)
  reemplaza al fake sólo bajo la lista de direcciones de prueba.
- La "hoja" de decisiones es un CSV: la verificación de identidad de Google
  sólo existe cuando el Form real recolecta el correo (ADR 0005). La
  autorización por rol sí se ensaya contra el padrón externo.
- La plantilla base y la fila de la actividad son provisionales
  (`SUPUESTO_TECNICO` donde aplica): nada de esto fue aprobado por la SEU.
- En live el plan de pago aún llega por `--plan-csv` del runner offline:
  la lectura de su pestaña por `GoogleSheetsFuentePagos` está cableada en
  `cli_pagos`, no en el canal — queda pendiente junto con el disparo
  automático de HU-015, que es otro ticket.
- Los recordatorios de pago no pasan por este circuito: siguen
  deterministas, diarios y por lote propio (#38). Este recorrido no los
  toca.

## Antes de empezar

- Una terminal en `Implementacion/Agente1`. Sin red ni credenciales.
- Los datos de la corrida viven en `data/` y son todos sintéticos:
  - `actividades_notebooklm_n2_sinteticas.csv` — la actividad
    `EJEMPLO-NOTEBOOKLM-N2` del hilo de demostración (formato
    `actividades_v2`; contacto inventado, campos desconocidos vacíos).
  - `plan_pagos_notebooklm_n2.csv` — el plan de pago provisional del hilo.
  - `padron_pagos_sintetico.csv` — los tres preinscriptos sintéticos.
  - `padron_roles_sintetico.csv` — los roles del circuito con correos
    inventados (`rgc@` firma lo semántico, `coord@` lo utilitario y el
    lote).

## Paso a paso (offline)

### 1. Circuito completo en una corrida

```bash
cd Implementacion/Agente1
PYTHONPATH=src python scripts/plantilla_actividad_lote_demo.py \
  --directorio /tmp/demo-plantilla-n2 \
  --csv data/actividades_notebooklm_n2_sinteticas.csv \
  --actividad EJEMPLO-NOTEBOOKLM-N2 \
  --plan-csv data/plan_pagos_notebooklm_n2.csv \
  --padron-csv data/padron_pagos_sintetico.csv \
  --padron-roles data/padron_roles_sintetico.csv
```

El script corre las tres fases y emite un JSON por cada una:

- **generacion** — el borrador queda en
  `borradores/EJEMPLO-NOTEBOOKLM-N2-plantilla.md` con `PENDIENTE_VALIDACION`,
  `tpl-EJEMPLO-NOTEBOOKLM-N2-<hash>` y `lote-EJEMPLO-NOTEBOOKLM-N2-<hash>`.
  La plantilla trae `{{detalle_cuotas}}`, `{{medios_pago}}` y
  `{{bonificaciones}}` porque hay plan; sin `--plan-csv` esas variables
  están prohibidas y el contrato lo exige.
- **declaracion** — los dos objetos quedan pendientes en
  `estado-decisiones/decisiones-pendientes.jsonl` con sus links
  prellenados (los ids `form_decisiones_offline`/`entry.*` son de mentira
  en offline; el contrato de links es el real).
- **decisiones** — sin `--respuestas-csv` el script escribe
  `respuestas-decisiones.csv` con las tres aprobaciones —lo que una
  persona habría respondido en el Form— y las pasa por
  `CanalFormDecisiones`: las tres quedan `registrada` con su rol.
- **lote** — `ENVIO_ENCOLADO` con 3 ítems, `drenajes: entregada ×3` y las
  piezas renderizadas en `entregas-simuladas/entrega-*.txt`: cada una
  lleva destinatario, el asunto del plan y el cuerpo con los datos ya
  sustituidos (cuota `$20.000`, medios, bonificaciones, contacto), con la
  marca `BORRADOR — NO ENVIAR`.

Re-correr el mismo comando sobre el mismo directorio devuelve el lote
`DUPLICADA`: la clave cubre actividad, inscripción y hash del documento.

### 2. El mismo pedido por el canal (#71)

El pedido en prosa también llega por el canal de pedidos. Como el id
`EJEMPLO-NOTEBOOKLM-N2` no tiene la forma que el reconocedor de
identificadores acepta (`LETRAS-DIGITOS`, tipo `SYN-001`), la prosa tiene
que distinguir la actividad — el título alcanza, porque es la única fila
del dataset:

```bash
cat > /tmp/demo-plantilla-n2/pedidos.csv <<'EOF'
Marca temporal,Correo,Pedido
2026-10-10 09:00:00,solicitante@example.invalid,generá la plantilla de correos para INTELIGENCIA ARTIFICIAL APLICADA A LA EDUCACIÓN Y GESTIÓN: NOTEBOOKLM - NIVEL 2
EOF
PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-plantilla-n2 \
  --respuestas-csv /tmp/demo-plantilla-n2/pedidos.csv \
  --csv data/actividades_notebooklm_n2_sinteticas.csv \
  --padron data/padron_roles_sintetico.csv \
  --plan-csv data/plan_pagos_notebooklm_n2.csv
```

La palabra «plantilla» clasifica el pedido a `generar_plantilla_actividad`,
el plan `--plan-csv` alimenta las variables de pago y el aviso que queda
en `estado-canal-form/avisos-offline.jsonl` enumera los links de
aprobación de los dos objetos (semántica, utilitaria y lote) — los mismos
ids que el paso 1, porque derivan del hash del documento. El registro de
decisiones es compartido: aprobar esos objetos por
`registrar_form_decisiones.py` habilita el lote igual que en la fase 2
del script.

Con una prosa que no distingue la actividad el canal repregunta — el
comportamiento de siempre (HU-013): el aviso ofrece el link prellenado
por candidata. Ojo: resolver esa repregunta exige el registro de
pendientes entre turnos (`RegistroPendientes`, #25), que este runner no
cablea — o un identificador con la forma `LETRAS-DIGITOS` en la
respuesta. Con `EJEMPLO-NOTEBOOKLM-N2` ninguna de las dos aplica, así
que el pedido que no resuelve en el primer turno vuelve a repreguntar
en lugar de generar.

## Camino live D2 (pendiente del operador)

El canal de pedidos corre live con el doble opt-in (`--live
--confirm-write-workspace`) y la configuración de `registrar_form_decisiones`:
los objetos `plantilla`/`lote` viajan por el mismo Form de decisiones de
#72 sin campos nuevos. Pendiente del ticket:

- el plan de pago live (hoy `--plan-csv` sólo existe en el camino
  offline; en live hay que cablear `GoogleSheetsFuentePagos` al runner),
- el padrón de preinscriptos y el drenaje contra el Gmail de lista de
  prueba — el encolado ya funciona, el destino se elige en la corrida
  live con `GmailDestino` en vez del fake.

Nada de esto es necesario para lo que el recorrido acredita: generación
acotada por contrato, doble aprobación + lote por el Form real de
decisiones, render determinista, encolado idempotente y entrega simulada.
