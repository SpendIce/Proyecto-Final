# Recorrido — emisión de certificados HU-014 con lista de cierre (#75)

## Qué demuestra

- Que el pedido «emití los certificados de `<actividad>`» se clasifica como
  `emitir_certificados` (catálogo `intenciones_v2`), resuelve la actividad
  por el resolver determinístico y despacha al circuito de lote de
  `certificados_emision.py` — nunca a otra intención, y sin medio
  configurado termina `emisor_no_configurado`.
- Que la lista de cierre se lee cruda y se valida entera: seis columnas
  posicionales, `condicion` cerrada (`asistencia`/`aprobacion`, nunca
  inferida), y una fila vacía, inválida o duplicada bloquea el lote.
- Que ningún PDF sale sin la línea descriptiva aprobada por los dos roles
  (#74: una decisión por rol sobre `linea_descriptiva:<id>:<hash>`) y sin
  el `apruebo_lote` del rol utilitario atado al hash de la lista (#72).
- Que editar la lista invalida la aprobación anterior: cambia el objeto de
  decisión y el lote vuelve a quedar pendiente.
- Que el correo de aprobación lleva el link al Form de decisiones y un PDF
  de muestra marcado `BORRADOR — NO EMITIR`, y que el PDF final lleva
  `DOCUMENTO DE PRUEBA — SIN VALIDEZ` como primera línea.
- Que la entrega es un correo por titular con el PDF adjunto, y que la
  auditoría (`emisiones-certificados-hu014.jsonl`) y el registro offline
  de entregas guardan sólo hashes y metadatos del adjunto: ni la lista ni
  los PDFs quedan persistidos.

## Qué NO demuestra

El recorrido offline no acredita la verificación de identidad de Google ni
el envío real por Gmail: el correo se lee del CSV y las entregas se escriben
en `entregas-certificados-offline.jsonl` (del adjunto queda el sha256, no el
PDF). En live vale el mismo circuito con `GmailDestinoConfirmaciones`, que
rechaza un destinatario fuera de la lista de prueba antes de tocar el token
o la red.

El criterio «demostradas en D2» queda **pendiente de la corrida live**: el
entorno D2 previsto para la demostración es NotebookLM Nivel 2, con la Sheet
de lista de cierre cargada por quien gestiona el curso. Los pasos live
están abajo; lo que este documento deja probado es el circuito completo con
los runners reales en modo offline, sin red.

## Antes de empezar

- No hace falta cuenta de Google ni credenciales: el modo offline usa CSV
  locales que imitan la hoja del Form de pedidos, la lista de cierre y el
  padrón de roles.
- Hace falta una terminal en `Implementacion/Agente1` y un directorio de
  trabajo compartido entre `emitir_certificados.py` y
  `registrar_form_decisiones.py`: el registro vive en
  `<directorio>/estado-decisiones/` y lo leen los dos.
- La línea descriptiva es un archivo de texto fuera del repo, tal como la
  va a entregar #74; el circuito la exige aprobada, no la escribe.

## Paso a paso (offline)

### 1. Preparar directorio, padrón, lista de cierre y línea

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-certificados
cat > /tmp/demo-certificados/padron.csv <<'EOF'
correo,rol
aux@example.invalid,auxiliar_seu
rgc@example.invalid,RESPONSABLE_GESTION_CONOCIMIENTO
coord@example.invalid,COORDINADOR_EXTENSION
EOF
cat > /tmp/demo-certificados/lista.csv <<'EOF'
nombre,apellido,dni,mail,tratamiento,condicion
Ana,Prueba Uno,30111222,ana.prueba@example.invalid,Dra.,asistencia
Bruno,Prueba Dos,30222333,bruno.prueba@example.invalid,Lic.,aprobacion
EOF
cat > /tmp/demo-certificados/linea.txt <<'EOF'
En el marco de la política de extensión universitaria, la actividad aporta
a la vinculación tecnológica educativa.
EOF
```

La lista tiene las dos condiciones a propósito: el lote demuestra los dos
textos del certificado sin que el agente infiera nada.

### 2. Primera corrida: la línea aún no está aprobada

```bash
PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad SYN-001 \
  --lista-csv /tmp/demo-certificados/lista.csv \
  --linea /tmp/demo-certificados/linea.txt \
  --aprobador coord@example.invalid \
  --solicitante aux@example.invalid \
  --directorio /tmp/demo-certificados/run
```

Resultado: `PENDIENTE_APROBACION` con error `linea_descriptiva_no_aprobada`.
El log deja el objeto esperado, `linea_descriptiva:SYN-001:<hash_linea>`.

### 3. Registrar las dos aprobaciones de la línea (#74)

El objeto se declara por el camino manual de
`registrar_form_decisiones.py` y responden los dos roles:

```bash
OBJETO=linea_descriptiva:SYN-001:<hash_linea>
cat > /tmp/demo-certificados/decisiones-linea.csv <<EOF
Marca temporal,Correo,Tipo,Objeto,Decisión
2026-10-01 10:00:00,rgc@example.invalid,linea_descriptiva,${OBJETO},aprobacion_linea_descriptiva
2026-10-01 10:05:00,coord@example.invalid,linea_descriptiva,${OBJETO},aprobacion_linea_descriptiva
EOF
PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/decisiones-linea.csv \
  --padron /tmp/demo-certificados/padron.csv \
  --declarar "linea_descriptiva:${OBJETO}"
```

(`<hash_linea>` es el sha256 del texto de `linea.txt`; la corrida anterior
lo imprime en el log como `objeto_linea`.)

### 4. Segunda corrida: el lote queda pendiente y sale el correo

La misma invocación de `emitir_certificados.py` ahora devuelve
`PENDIENTE_APROBACION` con error `lote_no_aprobado` y:

- declara el objeto de lote en `decisiones-pendientes.jsonl`
  (`tipo: lote`, `objeto_id` = sha256 de
  `lote_cierre_certificados|<actividad>|<hash_lista>`);
- escribe en `estado-canal-form/entregas-certificados-offline.jsonl` el
  correo al aprobador con el enlace al Form y el adjunto
  `certificado-muestra.pdf` — del adjunto quedan nombre, MIME, bytes y
  sha256, nunca el PDF.

### 5. Aprobar el lote por el Form de decisiones

```bash
OBJETO_LOTE=<objeto del log, 64 hex>
cat > /tmp/demo-certificados/decisiones-lote.csv <<EOF
Marca temporal,Correo,Tipo,Objeto,Decisión
2026-10-01 11:00:00,coord@example.invalid,lote,${OBJETO_LOTE},apruebo_lote
EOF
PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/decisiones-lote.csv \
  --padron /tmp/demo-certificados/padron.csv
```

### 6. Tercera corrida: `EMITIDA`

La misma invocación devuelve `EMITIDA` con `emitidas: 2`. En el log
`emisiones-certificados-hu014.jsonl` quedan, por entrega,
`destinatario_hash`, `holder_hash`, `certificado_ref_hash` y `pdf_hash` —
nombres, correos, DNI y PDFs no aparecen en ningún artefacto.

### 7. Mutación de la lista: la aprobación anterior no vale

Agregar una fila a `lista.csv` y relanzar el mismo comando: el hash de la
lista cambia, el objeto de lote cambia y el resultado vuelve a
`PENDIENTE_APROBACION` con un nuevo correo de aprobación.

### 8. Bloqueo por condición inválida

Una fila con `condicion` vacía o con un texto fuera del par cerrado hace
fallar el lote entero con `INVALIDA` y código `lista_cierre_condicion_vacia`
o `lista_cierre_condicion_invalida`: no hay emisión parcial de una lista
mal armada.

### 9. El mismo circuito desde el canal de pedidos

Con un CSV de respuestas del Form que imita el pedido:

```bash
cat > /tmp/demo-certificados/pedidos.csv <<'EOF'
Marca temporal,Correo,Pedido
2026-10-02 11:00:00,aux@example.invalid,emití los certificados de SYN-001
EOF
PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/pedidos.csv \
  --padron /tmp/demo-certificados/padron.csv \
  --lista-csv /tmp/demo-certificados/lista.csv \
  --linea /tmp/demo-certificados/linea.txt \
  --aprobador coord@example.invalid
```

Resultado: `emitir_certificados` despachada con el mismo estado del lote
(`PENDIENTE_APROBACION` o `EMITIDA` según el registro). Sin `--lista-csv`
el medio no existe y el pedido termina `emisor_no_configurado`.

## Camino live D2 (pendiente del operador)

Mismo circuito con el entorno cargado. La Sheet de lista de cierre es una
pestaña D2 cargada por quien gestiona el curso; el correo del aprobador es
el del rol utilitario del padrón:

```text
AGENTE1_WORKSPACE_AMBIENTE=D2
AGENTE1_WORKSPACE_*                  # planilla de actividades, carpeta, etc.
AGENTE1_FORM_DECISIONES_*            # Form de decisiones (#72)
AGENTE1_GMAIL_DESTINATARIOS_PRUEBA   # lista de prueba de la cuenta técnica
AGENTE1_PADRON_ROLES_PATH            # padrón fuera del repo
AGENTE1_CERTIFICADOS_LISTA_SHEET_ID  # Sheet D2 de la lista de cierre
AGENTE1_CERTIFICADOS_LISTA_RANGO_A1  # rango A1 de esa lista
AGENTE1_CERTIFICADOS_LINEA_PATH      # archivo con la línea aprobada (#74)
AGENTE1_CERTIFICADOS_APROBADOR       # correo del rol utilitario
AGENTE1_CERTIFICADOS_SOLICITANTE     # correo de quien cargó la lista
AGENTE1_WORKSPACE_ACCESS_TOKEN       # token efímero, nunca por argv
```

```bash
PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad <id> --live --confirm-write-workspace --directorio <dir>
```

o el mismo wiring desde `atender_canal_form.py --live`, que despacha
`emitir_certificados` sólo cuando `AGENTE1_CERTIFICADOS_LISTA_SHEET_ID`
está declarado.

## Restricciones que quedan en pie

- El certificado es provisional y de prueba: `DOCUMENTO DE PRUEBA —
  SIN VALIDEZ` en todo PDF y `BORRADOR — NO EMITIR` en la muestra.
- No hay firma digital ni imágenes de firma versionadas: la plantilla
  institucional y las firmas quedan `PENDIENTE_SEU` y vivirán en una
  carpeta D2 restringida de la cuenta técnica.
- El trigger automático al cerrar la actividad es HU-015: fuera de
  alcance. El disparo es siempre un pedido humano.
- Una reemisión es un pedido nuevo sobre la lista vigente: si la lista
  cambió hay que aprobar el nuevo objeto de lote.
- Los destinatarios live están restringidos a la lista de prueba D12; un
  destinatario fuera de ella rechaza antes de la red y sin reintento.
