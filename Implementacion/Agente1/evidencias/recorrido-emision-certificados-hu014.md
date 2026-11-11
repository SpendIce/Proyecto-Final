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
  (#74: `apruebo_semantica` del Responsable de Gestión del Conocimiento y
  `apruebo_utilitaria` del Coordinador de Extensión, una decisión por rol
  sobre `linea_descriptiva-<id_actividad>-<hash>`) y sin el `apruebo_lote`
  del rol utilitario atado al hash de la lista (#72).
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
- Los comandos usan `uv run --no-sync` desde `Implementacion/Agente1`
  (crea o reusa el `.venv` del proyecto sin tocar la red). Sin uv el
  equivalente es `PYTHONPATH=src python <script> …` desde el mismo
  directorio.
- La línea descriptiva es un archivo de texto fuera del repo, tal como la
  va a entregar #74; el circuito la exige aprobada, no la escribe.
- Sobre las dos identidades del ensayo:
  - `--aprobador` es el correo del rol utilitario: recibe el aviso del
    lote pendiente (enlace al Form de decisiones + muestra `BORRADOR`) y
    es quien **carga** la decisión `apruebo_lote` en el Form. El flag no
    registra ni fuerza ninguna aprobación: las decisiones se cargan sólo
    por el Form —en el ensayo, por las filas del CSV que procesa
    `registrar_form_decisiones.py`; no hay aprobación por CLI suelta.
  - `--solicitante` es el correo de quien disparó el pedido y cargó la
    lista de cierre. En el código vigente un `apruebo_lote` que venga de
    ese mismo correo no habilita (`aprobador_es_cargador`), así que el
    ensayo usa dos correos distintos.

## Paso a paso (offline)

### 1. Preparar directorio, padrón, lista de cierre y línea

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-certificados/run
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
uv run --no-sync env PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad SYN-001 \
  --lista-csv /tmp/demo-certificados/lista.csv \
  --linea /tmp/demo-certificados/linea.txt \
  --aprobador coord@example.invalid \
  --solicitante aux@example.invalid \
  --directorio /tmp/demo-certificados/run
```

Salida real:

```text
{"config": {"modo_offline": true}, "correlation_id": "808d5f4669849f0e", "emitidas": 0, "entregas_fallidas": 0, "error": "linea_descriptiva_no_aprobada", "estado": "PENDIENTE_APROBACION", "log_path": "/tmp/demo-certificados/run/emisiones-certificados-hu014.jsonl", "modo": "offline_fake", "resumen": "la línea descriptiva no tiene las dos aprobaciones"}
```

El log `emisiones-certificados-hu014.jsonl` deja el objeto esperado con
guiones, `linea_descriptiva-SYN-001-<sha256>` — los `:` de la notación del
ticket no entran en `ID_RE`; la forma vigente la deriva
`objeto_id_linea_descriptiva` y el hash es el sha256 de la línea
normalizada:

```text
{"correlation_id": "808d5f4669849f0e", "evento": "linea_descriptiva_no_aprobada", "hu": "HU-014", "manifest_version_sha256": "…", "objeto_linea": "linea_descriptiva-SYN-001-aad61b5d3ab4592c100f1b3abc9a640270f3ca05f6f1dd5b9ac03665df4b029b", "schema": "certificado_emision_lote_v1", "version_agente": "0.5.10"}
```

Para extraerlo sin leer el log a mano:

```bash
OBJETO=$(python3 -c "import json; print([json.loads(l)['objeto_linea'] for l in open('/tmp/demo-certificados/run/emisiones-certificados-hu014.jsonl') if 'objeto_linea' in l][-1])")
```

### 3. Registrar las dos aprobaciones de la línea (#74)

La línea se aprueba **una vez por actividad** con una decisión por rol,
igual que una plantilla: primero `apruebo_semantica` del
`RESPONSABLE_GESTION_CONOCIMIENTO` y después `apruebo_utilitaria` del
`COORDINADOR_EXTENSION` — la aprobación parcial no habilita, y un rol
cruzado sale `rechazada` con `rol_no_corresponde`. El objeto se declara
por el camino manual de `registrar_form_decisiones.py` con la sintaxis
`tipo:objeto_id` (el `tipo` va antes de los `:` y el `objeto_id` ya trae
su propio prefijo `linea_descriptiva-`):

```bash
cat > /tmp/demo-certificados/decisiones-linea.csv <<EOF
Marca temporal,Correo,Tipo,Objeto,Decisión
2026-10-01 10:00:00,rgc@example.invalid,linea_descriptiva,${OBJETO},apruebo_semantica
2026-10-01 10:05:00,coord@example.invalid,linea_descriptiva,${OBJETO},apruebo_utilitaria
EOF
uv run --no-sync env PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/decisiones-linea.csv \
  --padron /tmp/demo-certificados/padron.csv \
  --declarar "linea_descriptiva:${OBJETO}"
```

Salida real (resumen; los enlaces son del Form offline y nadie los abre):

```text
{"declarado": {"enlaces": {"apruebo_semantica": "https://docs.google.com/forms/d/e/form_decisiones_offline/viewform?usp=pp_url&entry.000000021=linea_descriptiva&entry.000000022=linea_descriptiva-SYN-001-aad61b5d…&entry.000000023=apruebo_semantica", "apruebo_utilitaria": "…&entry.000000023=apruebo_utilitaria"}, "objeto_id": "linea_descriptiva-SYN-001-aad61b5d3ab4592c100f1b3abc9a640270f3ca05f6f1dd5b9ac03665df4b029b", "tipo": "linea_descriptiva"}}
{"decision": "apruebo_semantica", "id_respuesta": "dbf5d0e4f805c19bb91c0bc6eabee20bdd05c7c490c85d47ce4642cc59e684cf", "objeto_id": "linea_descriptiva-SYN-001-aad61b5d3ab4592c100f1b3abc9a640270f3ca05f6f1dd5b9ac03665df4b029b", "rechazo_codigo": null, "resultado": "registrada", "rol": "RESPONSABLE_GESTION_CONOCIMIENTO", "rol_origen": "padron", "timestamp": "2026-11-11T13:30:25.189910+00:00", "tipo": "linea_descriptiva"}
{"decision": "apruebo_utilitaria", "id_respuesta": "6b5aedb19c6abc19c0348d3a5c122927e5a41db9981ed86e19b60f37d1ac97f6", "objeto_id": "linea_descriptiva-SYN-001-aad61b5d3ab4592c100f1b3abc9a640270f3ca05f6f1dd5b9ac03665df4b029b", "rechazo_codigo": null, "resultado": "registrada", "rol": "COORDINADOR_EXTENSION", "rol_origen": "padron", "timestamp": "2026-11-11T13:30:25.190847+00:00", "tipo": "linea_descriptiva"}
{"config": {"modo_offline": true}, "modo": "offline_fake", "procesadas": 2, "registro_decisiones": "decisiones-procesadas.jsonl", "registro_pendientes": "decisiones-pendientes.jsonl"}
```

Sin el `--declarar` previo las dos respuestas se rechazan como
`objeto_inexistente`: el único modo de abrir un objeto a decisión es que
se declare (en el circuito real lo hace el correo del agente que trae el
enlace; acá queda el camino manual).

### 4. Segunda corrida: el lote queda pendiente y sale el correo

La misma invocación de `emitir_certificados.py` ahora devuelve:

```text
{"config": {"modo_offline": true}, "correlation_id": "808d5f4669849f0e", "emitidas": 0, "entregas_fallidas": 0, "error": "lote_no_aprobado", "estado": "PENDIENTE_APROBACION", "log_path": "/tmp/demo-certificados/run/emisiones-certificados-hu014.jsonl", "modo": "offline_fake", "resumen": "el lote quedó pendiente y se envió el correo de aprobación con el certificado de muestra"}
```

Esta vez **el emisor declara el objeto de lote** en
`estado-decisiones/decisiones-pendientes.jsonl` (`tipo: lote`,
`objeto_id` = sha256 de `lote_cierre_certificados|<id_actividad>|<hash_lista>`,
un hex de 64) y escribe en
`estado-canal-form/entregas-certificados-offline.jsonl` el correo al
aprobador con el adjunto `certificado-muestra.pdf` — del adjunto quedan
nombre, MIME, bytes y sha256, nunca el PDF:

```text
{"version": "decisiones_pendientes_v1", "tipo": "lote", "objeto_id": "f345e7da653bd19f4545d45691a586f4ddf56613111644946636f8057fb95516", "detalle": {"pieza": "certificados_lote_cierre", "id_actividad": "SYN-001", "personas": "2"}, "declarado_en": "2026-11-11T13:30:28.326763+00:00"}
{"adjunto": {"bytes": 1648, "nombre": "certificado-muestra.pdf", "sha256": "57a1bd544f564daf2f6758433549558390da6cd106593ba8319d4d54f3b5988d", "tipo_mime": "application/pdf"}, "asunto": "[Agente 1] Aprobación pendiente — lote de certificados SYN-001", "destinatario": "coord@example.invalid", "idempotency_key": "4bf7a76ea1b4dab717a2300f456dde1583eff2e06566be36c229656cd05754e7", "manifest_version_sha256": "…", "version_agente": "0.5.10"}
```

El objeto se lee del registro de pendientes:

```bash
OBJETO_LOTE=$(python3 -c "import json; print([json.loads(l)['objeto_id'] for l in open('/tmp/demo-certificados/run/estado-decisiones/decisiones-pendientes.jsonl') if json.loads(l).get('tipo') == 'lote'][-1])")
```

### 5. Aprobar el lote por el Form de decisiones

Como el emisor ya declaró el objeto, no hace falta `--declarar`: basta la
fila del `apruebo_lote` del Coordinador sobre el objeto del paso anterior.

```bash
cat > /tmp/demo-certificados/decisiones-lote.csv <<EOF
Marca temporal,Correo,Tipo,Objeto,Decisión
2026-10-01 11:00:00,coord@example.invalid,lote,${OBJETO_LOTE},apruebo_lote
EOF
uv run --no-sync env PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/decisiones-lote.csv \
  --padron /tmp/demo-certificados/padron.csv
```

```text
{"decision": "apruebo_lote", "id_respuesta": "3c4f3672780dbbb2e21ad5babada0bff95980331deeb9a1052f7d9393cdca625", "objeto_id": "f345e7da653bd19f4545d45691a586f4ddf56613111644946636f8057fb95516", "rechazo_codigo": null, "resultado": "registrada", "rol": "COORDINADOR_EXTENSION", "rol_origen": "padron", "timestamp": "2026-11-11T13:30:35.457402+00:00", "tipo": "lote"}
{"config": {"modo_offline": true}, "modo": "offline_fake", "procesadas": 1, "registro_decisiones": "decisiones-procesadas.jsonl", "registro_pendientes": "decisiones-pendientes.jsonl"}
```

> **Nota — regla del 11/11/2026 (#125, pendiente de código).** Por la
> definición vigente, el lote de certificados lo aprueba **quien lo
> genera**, igual que el resto de las piezas: una sola persona autorizada,
> no un par cargador/aprobador. El código actual puede no reflejarlo
> todavía —hoy un `apruebo_lote` del correo del solicitante queda
> descalificado (`aprobador_es_cargador`)—; la adaptación es alcance del
> issue #125. Este recorrido describe el comportamiento del código
> vigente, por eso `--aprobador` y `--solicitante` son correos distintos.

### 6. Tercera corrida: `EMITIDA`

La misma invocación devuelve `EMITIDA` con `emitidas: 2`:

```text
{"config": {"modo_offline": true}, "correlation_id": "808d5f4669849f0e", "emitidas": 2, "entregas_fallidas": 0, "error": null, "estado": "EMITIDA", "log_path": "/tmp/demo-certificados/run/emisiones-certificados-hu014.jsonl", "modo": "offline_fake", "resumen": "2 certificados entregados de 2 (Taller sintético de vinculación)"}
```

En el log `emisiones-certificados-hu014.jsonl` quedan, por entrega,
`destinatario_hash`, `holder_hash`, `certificado_ref_hash` y `pdf_hash`,
más el evento `cierre` con el total — nombres, correos, DNI y PDFs no
aparecen en ningún artefacto:

```text
{"certificado_ref_hash": "566fd9a6404ccd1a8f0bad10bd786c8ccc67d53320304993590be006c34c4283", "correlation_id": "808d5f4669849f0e", "destinatario_hash": "7adf377dc69a99bbf3e215f054d4c991453567344cd2e7c7126970642d7c9169", "evento": "entrega", "holder_hash": "3942ea074cdfb98248c9f9dddf12dc5aef06fddd7bb645d0d78f71a5c5a96e2b", "hu": "HU-014", "manifest_version_sha256": "…", "pdf_hash": "968a02e2fdcea0ca6a92438ea989a179157bf1bede9def1679050c7cc444aab3", "resultado": "enviada", "schema": "certificado_emision_lote_v1", "version_agente": "0.5.10"}
{"certificado_ref_hash": "4b1b43defd02bfb0c2ae20b3ff0c6d5e704e1671c1dd6556274ed145dea40899", "correlation_id": "808d5f4669849f0e", "destinatario_hash": "a96f91b36ea05946792c2ec17c79bd776e99cf5fe47bc9f0fb54cfe5cf032181", "evento": "entrega", "holder_hash": "709fa6806b62a05098fda09b6ba443257a6571331b2b9ccdf725980012698ec7", "hu": "HU-014", "manifest_version_sha256": "…", "pdf_hash": "938c18515931b2ec69ae7a04156979a7a2c99f7027918fdd68179a7b2aaa95d2", "resultado": "enviada", "schema": "certificado_emision_lote_v1", "version_agente": "0.5.10"}
{"correlation_id": "808d5f4669849f0e", "emitidas": 2, "entregas_fallidas": 0, "estado": "EMITIDA", "evento": "cierre", "hu": "HU-014", "manifest_version_sha256": "…", "schema": "certificado_emision_lote_v1", "version_agente": "0.5.10"}
```

### 7. Mutación de la lista: la aprobación anterior no vale

Agregar una fila a `lista.csv` y relanzar el mismo comando: el hash de la
lista cambia, el objeto de lote cambia y el resultado vuelve a
`PENDIENTE_APROBACION` con un nuevo correo de aprobación:

```text
{"config": {"modo_offline": true}, "correlation_id": "808d5f4669849f0e", "emitidas": 0, "entregas_fallidas": 0, "error": "lote_no_aprobado", "estado": "PENDIENTE_APROBACION", "log_path": "…/emisiones-certificados-hu014.jsonl", "modo": "offline_fake", "resumen": "el lote quedó pendiente y se envió el correo de aprobación con el certificado de muestra"}
```

### 8. Bloqueo por condición inválida

Una fila con `condicion` vacía o con un texto fuera del par cerrado hace
fallar el lote entero con `INVALIDA` y código `lista_cierre_condicion_vacia`
o `lista_cierre_condicion_invalida` — por ejemplo, `aprobado` en lugar de
`aprobacion`:

```text
{"config": {"modo_offline": true}, "correlation_id": "808d5f4669849f0e", "emitidas": 0, "entregas_fallidas": 0, "error": "lista_cierre_condicion_invalida", "estado": "INVALIDA", "log_path": "…/emisiones-certificados-hu014.jsonl", "modo": "offline_fake", "resumen": "la lista de cierre no habilita el lote (lista_cierre_condicion_invalida)"}
```

No hay emisión parcial de una lista mal armada.

### 9. El mismo circuito desde el canal de pedidos

Con un CSV de respuestas del Form que imita el pedido:

```bash
cat > /tmp/demo-certificados/pedidos.csv <<'EOF'
Marca temporal,Correo,Pedido
2026-10-02 11:00:00,aux@example.invalid,emití los certificados de SYN-001
EOF
uv run --no-sync env PYTHONPATH=src python scripts/atender_canal_form.py \
  --directorio /tmp/demo-certificados/run \
  --respuestas-csv /tmp/demo-certificados/pedidos.csv \
  --padron /tmp/demo-certificados/padron.csv \
  --lista-csv /tmp/demo-certificados/lista.csv \
  --linea /tmp/demo-certificados/linea.txt \
  --aprobador coord@example.invalid
```

El canal despacha `emitir_certificados` con el mismo estado del lote del
registro — con la lista de dos personas y su `apruebo_lote` registrado,
`EMITIDA`; con la lista mutada del paso 7, `PENDIENTE_APROBACION` — y la
identidad del solicitante es el correo verificado de la fila
(`aux@example.invalid`), que queda como `solicitante_hash` y como cargador
de la lista:

```text
{"correlation_id": "a3b1a565-b8ac-4ae2-8ffd-c220f3e11474", "estado": "EMITIDA", "intencion": "emitir_certificados"}
{"atendidos": 1, "config": {"certificados": true, "modo_offline": true, "planes_pago": 0}, "modo": "offline_fake", "registro_atendidos": "atendidos-canal-form.jsonl"}
```

Sin `--lista-csv` el medio no existe y el pedido termina `FALLIDA` con
resultado `emisor_no_configurado` en `logs/interpretaciones-hu013.jsonl`.

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
- La aprobación del lote por quien lo genera (regla del 11/11/2026) es el
  issue #125: mientras tanto vale el par cargador/aprobador que este
  recorrido ensaya.
