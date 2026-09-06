# Agente 1 — MVP técnico controlado

Este directorio reúne la implementación incremental del Agente 1: HU-010 para
gacetillas, HU-011 para borradores de redes sociales y el slice offline de
HU-012 para confirmaciones. También contiene preparación contractual de
Workspace, persistencia y operaciones. Ningún flujo publica o envía contenido
real sin una autorización humana e institucional externa al repositorio.

El alcance actual es deliberadamente local y reproducible:

- Puerto de entrada con adapter CSV y adapter contractual de Google Sheets probado offline.
- Generador fake determinista para regresión y adapter HTTP para Ollama local.
- Puerto de salida con adapter Markdown y adapter contractual de Google Docs probado offline.
- Estado `PENDIENTE_VALIDACION` y encabezado `BORRADOR — NO PUBLICAR` en toda salida exitosa.
- Rechazo previo a la generación cuando falta un campo obligatorio.
- Rechazo de identificadores fuera de la allowlist antes de resolver paths de salida.
- Estado `FALLIDA` sin borrador cuando el generador falla, devuelve contenido vacío o no cumple el contrato mecánico mínimo.
- Auditoría JSONL con correlation ID, hashes, versiones de contrato/prompt, modelo y latencia, sin copiar datos fuente ni contenido generado.

Esto valida el flujo y sus controles, pero **no completa el DoD institucional de HU-010**: los adapters de Sheets y Docs todavía no tienen OAuth, configuración institucional ni prueba live; además faltan la plantilla institucional definitiva y la validación de la SEU prevista en el Gantt.

## Estructura

- `data/actividades_sinteticas.csv`: dataset ficticio de cinco filas; incluye tres casos completos, dos incompletos y lugares opcionales ausentes.
- `src/agente1/contracts/gacetilla_input_v1.schema.json`: contrato técnico versionado de los campos actuales, marcado `PROVISIONAL_NO_INSTITUCIONAL`.
- `src/agente1/prompts/gacetilla_v2.txt`: prompt versionado con estructura fija, límites y ejemplo sintético; también está marcado como provisional.
- `src/agente1/fuentes.py`: puerto `FuenteSolicitudes` y adapter CSV compatible con el flujo local.
- `src/agente1/destinos.py`: puerto `DestinoBorradores` y adapter Markdown que preserva la salida local.
- `src/agente1/google_workspace.py`: contratos HTTP de lectura Google Sheets y creación de borradores Google Docs; sólo están verificados offline con token y transporte fake.
- `golden/SYN-001.md`, `SYN-003.md` y `SYN-005.md`: salidas esperadas del generador fake para las tres filas completas.
- `tests/`: contrato público del procesador y de la CLI.
- `scripts/smoke.sh`: ejecución end-to-end local contra dataset y golden.
- `scripts/matriz_hu010.py`: matriz reproducible de los cinco casos contractuales sin depender de un LLM.
- `scripts/smoke_ollama.sh`: smoke opt-in contra un Ollama ya iniciado y con el modelo descargado.
- `scripts/matriz_hu011_v2.py`: matriz fake de creatividad JSON y render determinista para HU-011 v2.
- `scripts/workspace_e2e.py`: runner Sheets→procesamiento→Drive, offline por defecto y live con doble opt-in.
- `src/agente1/persistencia.py` y `migrations/`: puerto en memoria y SQL del spike PostgreSQL, ya ejecutado contra un contenedor efímero.
- `src/agente1/confirmaciones.py`: lifecycle offline de HU-012 con entrega únicamente fake.
- `src/agente1/politicas/politica_redes_provisional_v1.json` y `src/agente1/politica_redes.py`: política de redes de HU-011 como inventario de reglas verificables, con sus parámetros por canal y el estado de cada regla (`ACTIVA`, `NO_APLICADA_PENDIENTE_SEU`, `NO_MECANIZABLE`).
- `src/agente1/contracts/matriz_origenes_inscripcion_v1.json` y `src/agente1/origenes_inscripcion.py`: matriz operativa de HU-012 por origen de inscripción y decisión de envío fail-closed; ningún origen habilita envío.
- `scripts/medir_capacidad_hu011.py`: prueba de capacidad local contra el volumen de referencia informado por la SEU; mide latencia fría y caliente y tasa de conformidad, y proyecta el mes.
- `scripts/operaciones_seguras.py`: health, reconciliación, consolidación y retención en dry-run.
- `salida/`: evidencia runtime local ignorada por Git.

## Dónde está documentada cada decisión

El criterio de documentación del código es: los docstrings de módulo explican
**por qué** el módulo está hecho así y qué compromiso institucional sostiene;
los docstrings de función describen el contrato; los comentarios en línea sólo
aparecen donde el "por qué" no se deduce leyendo el código. Nada documenta lo
que el código ya dice por sí mismo.

Para revisar una decisión puntual, empezar por el docstring del módulo:

| Decisión | Dónde está explicada |
|---|---|
| Por qué el modelo no escribe los datos de la actividad (renderer determinista y gate de hechos) | `src/agente1/posts.py`, docstring de módulo y de `_parsear_creatividad_estructurada` |
| Por qué se rechaza cualquier dígito en la zona creativa | `posts.py`, comentario sobre `texto_creativo` |
| Por qué existe un control de registro rioplatense | `posts.py`, comentario de `PATRON_TUTEO` |
| Por qué el camino `text-v1` sigue en el repo | `posts.py`, docstrings de `procesar_post` y `_validar_salida` |
| Por qué toda falla termina sin borrador | `src/agente1/procesamiento.py`, docstring de módulo |
| Por qué el log guarda hashes y no contenido | `procesamiento.py` y `src/agente1/persistencia.py`, docstrings de módulo |
| Por qué no hay reintento automático tras una ejecución cortada | `src/agente1/workspace_e2e.py`, docstring de módulo y `RegistroIdempotenciaArchivo` |
| Por qué la reserva de idempotencia se toma recién al escribir | `workspace_e2e.py`, docstring de `_DestinoIdempotente` |
| Por qué el modo live exige dos banderas | `workspace_e2e.py`, `crear_dependencias_workspace_live` |
| Por qué se usa HTTP a mano y no el SDK de Google | `src/agente1/google_workspace.py`, docstring de módulo |
| Qué pasa si la copia de la plantilla queda huérfana | `google_workspace.py`, `GoogleDrivePlantillaDestinoBorradores` y `DestinoBorradoresError` |
| Por qué el encabezado de la planilla debe ser exacto (y qué implica para Google Forms) | `google_workspace.py`, `_buscar_fila` |
| Por qué el generador sólo acepta loopback | `src/agente1/ollama.py`, docstring de módulo y `_validar_base_url` |
| Por qué HU-012 modela un envío que no se hace | `src/agente1/confirmaciones.py`, docstring de módulo |
| Por qué no se borra nada, sólo se marca | `persistencia.py`, `eliminar_logicamente_anteriores` |
| Qué prueba y qué no prueba la auditoría de seguridad | `src/agente1/auditoria_d2.py`, `auditar_manifest` |
| Por qué los límites de redes son provisionales | `src/agente1/politica_redes.py`, docstring de módulo (DEF-A1-007) |
| Por qué ningún origen de inscripción habilita envío | `src/agente1/origenes_inscripcion.py`, docstring de módulo |

Cada archivo de `tests/` abre con un docstring que resume qué cubre esa suite,
de modo que la pregunta "¿dónde está probado esto?" se responda leyendo los
encabezados.

## Ejecutar las pruebas

Desde este directorio:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache python -m pytest -q
```

## Ejecutar el smoke

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache bash scripts/smoke.sh
```

La CLI imprime un JSON con estado, correlation ID y paths de evidencia. Un caso válido debe finalizar en `PENDIENTE_VALIDACION`; uno incompleto finaliza en `INCOMPLETA`, retorna código 2, no invoca al generador y no crea un borrador. Una falla, salida vacía o salida no conforme finaliza en `FALLIDA`, retorna código 2 y tampoco crea borrador.

Un identificador rechazado o una solicitud inexistente finaliza en `INVALIDA` con un error genérico y código 2, sin traceback. Esos casos asignan correlation ID y generan un audit log con código cerrado y hash del identificador, sin copiar el identificador ni el path consultado. Fallas operativas o contractuales de una fuente terminan en `FALLIDA`, no invocan al generador ni crean borrador, y registran `source_error_code` sin token, cuerpo remoto ni fila de entrada.

## Adapter contractual de Google Sheets

El seam `FuenteSolicitudes` permite que el core procese la misma forma contractual desde CSV o Sheets. El adapter Sheets implementa y prueba offline una solicitud `spreadsheets.values.get` hacia el host oficial fijo, con rango A1 percent-encoded, `majorDimension=ROWS`, `valueRenderOption=FORMATTED_VALUE`, deadline total y respuesta limitada a 1 MiB. Exige las columnas exactas de `gacetilla_input_v1`, valores string e identificadores únicos; completa únicamente las celdas finales vacías que la API puede omitir.

Las pruebas usan un token provider y un transporte fake inyectados. **No existe todavía un flujo OAuth real, credenciales, spreadsheet ID/rango institucional, permisos ni ejecución live contra Google Workspace.** El token no se acepta como flag de CLI y nunca debe persistirse en logs o mensajes de error. Por lo tanto, este incremento demuestra el contrato y el aislamiento técnico, no una integración institucional operativa.

## Adapter contractual de Google Docs

El seam `DestinoBorradores` mantiene el adapter Markdown local y permite inyectar el adapter Docs después del gate mecánico. El adapter contractual hace exactamente dos operaciones sobre el host oficial fijo: crea un documento con título `BORRADOR — NO PUBLICAR — <id>` y luego inserta el borrador validado en el índice 1 mediante `documents.batchUpdate`. No ejecuta operaciones de compartir, enviar, publicar ni aplicar una plantilla institucional.

Las dos solicitudes comparten una deadline total, limitan las respuestas a 1 MiB y no se reintentan. `documents.create` y `batchUpdate` no forman una transacción única: si la segunda operación falla, puede quedar un documento vacío. Ese caso termina en `FALLIDA` y registra sólo un hash de reconciliación opaco, nunca el document ID, token, contenido, cuerpo remoto o URL completa. El adapter sigue siendo **exclusivamente contractual/offline**: no hay OAuth, credenciales, permisos, carpeta institucional, template ID ni ejecución live.

## Ejecutar la matriz contractual simulada

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu010.py --salida salida/matriz-manual
```

El runner ejecuta las cinco filas versionadas. `SYN-001`, `SYN-003` y
`SYN-005` deben producir borradores idénticos a sus goldens y quedar en
`PENDIENTE_VALIDACION`; `SYN-002` y `SYN-004` deben quedar `INCOMPLETA` sin
invocar al generador ni crear borradores. `matriz.json` conserva IDs de
correlación, estados y hashes, pero no copia datos fuente, contactos, prompts o
borradores.

La matriz usa origen `SIMULADA` y un fake determinista: prueba conformidad
contractual, controles y reproducibilidad. **No prueba calidad del LLM, tono
institucional, precisión semántica, performance, validación SEU ni TRL 3.** Los
tres borradores conservan revisión humana `PENDIENTE` y requieren un checklist
individual. La corrida recuperable del 20 de julio está documentada en
`evidencias/matriz-conformidad-hu010-2026-07-20.md`; no reutiliza el manifest
del experimento Ollama.

## Gate mecánico provisional de salida

Antes de escribir un borrador, un parser anclado exige que el documento comience exactamente en `## TÍTULO`, contenga una sola vez y en orden `TÍTULO → DATOS DE LA ACTIVIDAD → CONTACTO → BAJADA → CUERPO`, y no tenga preámbulo, duplicados ni texto externo. El documento completo no puede superar 5000 caracteres; no se impone un mínimo arbitrario. Los hechos fuente no cuentan para un límite de palabras: BAJADA y CUERPO admiten hasta 12 palabras cada uno; el CUERPO debe ser exactamente una oración y terminar en `.`, `?` o `!`.

Cada hecho etiquetado se compara por igualdad normalizada sólo dentro de su sección: título en TÍTULO; fecha, organización y lugar en DATOS; contacto en CONTACTO. Si la fuente no informa lugar, cualquier línea `Lugar:` queda prohibida; si lo informa, el valor debe coincidir exactamente después de normalizar mayúsculas, espacios y acentos. Una salida no conforme registra códigos cerrados en `validation_errors`, nunca fragmentos rechazados. Este gate sigue sin evaluar tono o verdad semántica.

Este gate sólo evita aceptar basura evidente o pérdida de hechos críticos. NO evalúa tono institucional, claridad, gramática, pertinencia ni verdad semántica; tampoco convierte el formato provisional en plantilla oficial. Esos criterios requieren checklist y validación humana de la SEU antes de aprobar HU-010 o declarar el Gate TRL 3.

## Probar Ollama local

Ollama no está instalado a nivel global del sistema. Sí existe y fue probado el runtime user-local ignorado por Git. Docker está disponible, pero esa vía se descartó para este slice por el peso adicional de imagen, capas y modelo. Para el PoC se fija `llama3.2:3b`: la [ficha oficial de Ollama](https://ollama.com/library/llama3.2:3b) publica un artefacto de 2,0 GB y la variante 3B permite empezar con un host limitado. Ese tamaño corresponde a la descarga del modelo, no garantiza por sí solo un consumo equivalente de RAM.

La preparación del runtime es deliberadamente externa a las pruebas y al build del paquete. Como alternativa user-local, el directorio `.runtime/` está ignorado por Git y puede alojar el ejecutable obtenido de la distribución oficial y los modelos sin contaminar el repositorio:

```bash
mkdir -p .runtime/bin .runtime/models
# Ubicar el ejecutable oficial en .runtime/bin/ollama sin commitearlo.
OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama serve
```

En otra terminal, con el servicio iniciado:

```bash
OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama pull llama3.2:3b
```

El binario, sus librerías y los modelos son runtime local: NO deben agregarse a Git. El runtime user-local ya fue probado en este host. Con `llama3.2:3b` sobre CPU, una corrida warm completó en `22.859583 s`, otras generaciones superaron 30 segundos y la carga cold agotó el deadline anterior; el benchmark debe distinguir esos estados. La variante 1B fue rechazada por el gate de la prueba. Estos resultados son evidencia técnica local: no constituyen validación SEU ni habilitan declarar un nivel TRL.

Con el servicio y el modelo listos:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache bash scripts/smoke_ollama.sh
```

La CLI también admite el adapter explícitamente:

```bash
python -m agente1 \
  --csv data/actividades_sinteticas.csv \
  --id-solicitud SYN-001 \
  --salida salida/manual \
  --ollama-model llama3.2:3b \
  --ollama-base-url http://127.0.0.1:11434 \
  --ollama-timeout 45 \
  --ollama-num-predict 112
```

El timeout conserva semántica de deadline total para conexión, envío, headers y cuerpo; un servidor trickle no puede reiniciarlo. La evidencia CPU live mostró generaciones que superan 30 segundos, por lo que el presupuesto operativo usa 45 segundos por defecto y admite configuración entre más de cero y 120 segundos. Este ajuste evita confundir capacidad del host con un corte artificial; no modifica ni declara cumplido un requisito institucional de performance. Puede definirse `OLLAMA_TIMEOUT` en el smoke live. `num_predict` usa 112 por defecto, valor elegido tras el benchmark para permitir un cierre completo con puntuación, y admite valores entre 32 y 512. El valor efectivo queda auditado en cada ejecución Ollama; el fake registra `null`. También puede definirse `OLLAMA_NUM_PREDICT`. Errores HTTP, timeouts o respuestas inválidas terminan como `FALLIDA`: no crean borrador ni exponen prompt, URL o cuerpo remoto en la CLI o el audit log. Por seguridad, el adapter sólo acepta HTTP hacia `localhost`, direcciones `127.0.0.0/8` o `::1`; no admite hosts remotos, HTTPS, credenciales embebidas ni paths adicionales.

El smoke real deja sus resultados en un subdirectorio temporal de `salida/`, ignorado por Git. Verifica controles técnicos; no reemplaza la revisión humana, la validación SEU ni permite declarar cumplido el Gate TRL 3.

## HU-011 — matriz contractual provisional

HU-011 reutiliza los puertos de fuente y destino para producir borradores
separados de Instagram y LinkedIn. El contrato `post_input_v1`, las políticas
de canal y los prompts están marcados como `PROVISIONAL_NO_INSTITUCIONAL`.
Toda salida exitosa conserva `BORRADOR — NO PUBLICAR` y
`PENDIENTE_VALIDACION`; el agente no comparte, envía ni publica contenido y no
invoca APIs de redes sociales.

La matriz reproducible ejecuta las cinco actividades sintéticas en ambos
canales: las tres completas producen seis borradores idénticos a
`golden/posts/`; las dos incompletas producen cuatro resultados `INCOMPLETA`
sin invocar al generador ni crear borradores.

El gate aplica un **grounding mecánico conservador**: exige que el texto
preserve literalmente la fecha y los hechos críticos de la fuente —título,
organización, contacto y lugar cuando fue informado— y rechaza ciertos hechos
o afirmaciones no autorizados. Este control no constituye una evaluación
semántica integral ni garantiza por sí solo la ausencia de alucinaciones;
precisión, contexto y sentido institucional requieren revisión humana
obligatoria de la SEU.

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu011.py --salida salida/matriz-hu011

PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  bash scripts/smoke_posts.sh salida/smoke-hu011
```

El resumen JSON conserva IDs de correlación, estados, versiones y hashes sin
copiar textos, contactos, datos fuente o prompts. Este circuito utiliza un fake
determinista: verifica conformidad contractual y reproducibilidad, **no calidad
de Ollama, grounding semántico integral, tono institucional, validación SEU o
TRL 3**. El checklist y el
informe de corte viven en `evidencias/checklist-validacion-humana-hu011.md` y
`evidencias/matriz-conformidad-hu011-2026-08-17.md`.

## HU-011 — salida estructurada v2

`procesar_post_estructurado` limita al modelo a un objeto JSON con `gancho`,
`prosa`, `cta` y `hashtags`. Un renderer determinista agrega los hechos de la
fuente y el marcador de borrador; fechas, organización, contacto y lugar no se
delegan como texto libre al LLM. El contrato `post_creative_output_v2` y los
prompts `post_*_structured_v2` siguen marcados
`PROVISIONAL_NO_INSTITUCIONAL`.

La matriz fake compara seis borradores —tres actividades por dos canales— con
`golden/posts_v2/` y verifica además los casos incompletos:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu011_v2.py --salida salida/matriz-hu011-v2

PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_posts_structured.py tests/test_matriz_hu011_v2.py
```

Esta matriz usa creatividad fake y, por sí sola, no demuestra conformidad con
Ollama. Los experimentos v2/v3/v4 posteriores sí evalúan el transporte real y
se documentan más abajo. Ninguna de esas pruebas demuestra calidad
institucional, grounding semántico integral, validación SEU, publicación ni
TRL 3. La API primaria está disponible desde `agente1` como
`procesar_post_estructurado`.

## Preparación Workspace D2 y seguridad offline

La configuración cerrada de `workspace_config.py` y el smoke
`workspace_smoke.py` preparan una lectura opt-in de Sheets para D2. Las
operaciones de copia de plantilla y ubicación en carpeta Drive están probadas
offline con transporte fake. **No hubo una ejecución Workspace live:** no hay
OAuth, token, IDs ni permisos institucionales aportados al repositorio, y el
smoke live sólo leerá Sheets; no prueba Docs, Drive ni publicación.

Después de cargar por un mecanismo seguro las siete variables **no sensibles**
definidas en
`Documentos/PlanDespliegue/Runbook-Workspace-D2-D3-Agente-1.md`, validar la
configuración sin red:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache PYTHONPATH=src \
  python scripts/workspace_smoke.py
```

No se debe pasar el token por CLI, escribirlo en `.env` versionado ni copiarlo
al historial. `--live` queda reservado para una sesión autorizada por DSI y
requiere un token efímero en `AGENTE1_WORKSPACE_ACCESS_TOKEN`.

El harness de seguridad es deliberadamente offline y no acepta credenciales:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/auditar_seguridad_d2.py \
  --manifest data/security_d2_manifest.synthetic.json \
  --reporte /tmp/reporte-seguridad-d2.json
```

El reporte versionado obtuvo `PASS` sobre redacción, allowlists, errores
remotos, ausencia de endpoints de distribución, revocación simulada y estado
de borrador. Esto no demuestra permisos, revocación, aislamiento ni tráfico
reales.

La cantidad de pruebas cambia con cada incremento y debe obtenerse ejecutando la
suite del checkout actual. Un resultado verde no es evidencia de integración
institucional ni se atribuye a Workspace/security de forma aislada.

## Runner Workspace end-to-end

`workspace_e2e.py` compone fuente Sheets, HU-010 o HU-011 structured v2,
destino Drive/Docs, manifest e idempotencia. Por defecto opera enteramente con
fakes y datos sintéticos:

```bash
PYTHONPATH=src python scripts/workspace_e2e.py --tipo gacetilla
PYTHONPATH=src python scripts/workspace_e2e.py --tipo post --canal instagram
PYTHONPATH=src python scripts/workspace_e2e.py --tipo post --canal linkedin
```

El modo live exige simultáneamente `--live` y
`--confirm-write-workspace`, además de configuración y token efímero. Puede
crear un documento remoto: se debe seguir
`evidencias/runbook-workspace-e2e.md`, usar un `--id-solicitud` y ambiente
autorizados, y reconciliar estados `UNCERTAIN` antes de reintentar. No prueba
publicación, sharing, email ni validación SEU. Para uso programático, importar
explícitamente desde `agente1.workspace_e2e`; estas APIs operativas no se
reexportan en el namespace raíz.

## Spike de persistencia PostgreSQL

`agente1.persistencia` define `RepositorioEjecuciones` y un adapter en memoria
para solicitudes, ejecuciones, borradores, validaciones, defectos, eventos,
idempotencia y retención lógica. No existe adapter PostgreSQL, driver ni
conexión activa. El detalle y los pendientes están en
`evidencias/spike-persistencia-postgresql-2026-08-17.md`.

Las migraciones son artefactos SQL numerados del repositorio bajo
`migrations/`. No se incluyen como package-data ni se afirma que viajen en un
wheel: se aplican con un cliente SQL. La superficie se importa desde
`agente1.persistencia`, no desde `agente1`.

El ciclo forward/rollback/forward **ya fue ejecutado** contra PostgreSQL 16 en un
contenedor efímero: `0001` crea seis tablas, catorce índices, 44 CHECK, cinco FK
y cuatro UNIQUE, y el rollback deja la base vacía. Doce inserciones inválidas
fueron rechazadas por el motor.

Esa ejecución también reveló que cinco invariantes documentadas en el spike **no**
estaban cubiertas por el esquema: borradores colgados de ejecuciones `FALLIDA`,
`INCOMPLETA` o `INICIADA`, `output_hash` de borrador distinto al de su ejecución,
validaciones anteriores al borrador y timestamps futuros.
`migrations/0002_integridad_referencial_borradores.up.sql` cierra las tres
primeras mediante claves foráneas compuestas. La migración
`0003_rechazo_timestamps_futuros` agrega triggers para rechazar escrituras
directas con `creada_en` o `registrada_en` futuro, sin usar `now()` dentro de
un CHECK. El ciclo completo `0001 → 0002 → 0003`, su rollback y un forward
final se ejecutaron contra PostgreSQL 16 efímero el 2026-08-26; ver
`evidencias/validacion-migraciones-postgresql-0003-2026-08-26.md`.

Continúa pendiente ejecutar los mismos contract tests contra un adapter
PostgreSQL real, que todavía no existe.

## HU-012 — confirmaciones offline

HU-012 renderiza determinísticamente un asunto y cuerpo provisional con
`BORRADOR — NO ENVIAR`. Valida destinatario y aprobación humana, conserva el
mismo borrador durante el lifecycle
`PENDIENTE_VALIDACION → APROBADA/RECHAZADA → ENVIADA_SIMULADA` y usa
transiciones atómicas para impedir retrocesos, carreras y entregas duplicadas.
`ENVIADA_SIMULADA` sólo registra una entrega en memoria mediante
`DestinoConfirmacionesFake`: no existe adapter de correo real.

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  bash scripts/smoke_confirmaciones.sh salida/smoke-hu012

PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_confirmaciones.py tests/test_matriz_hu012.py
```

Las APIs primarias (`SolicitudConfirmacion`, `AprobacionHumana`,
`ResultadoConfirmacion`, `RegistroConfirmacionesMemoria`,
`DestinoConfirmacionesFake` y `procesar_confirmacion`) se exportan desde
`agente1`. Contrato, plantilla, aprobaciones de la matriz y destinatarios son
sintéticos o provisionales. Consultar
`evidencias/limites-hu012-offline.md`; no hay envío institucional, validación
SEU ni evidencia de TRL 3.

## Operaciones seguras D2/D3

El tooling operativo consume manifests sanitizados y no modifica recursos. Los
comandos disponibles son `health`, `reconcile`, `consolidate` y `retention`;
retención siempre produce un plan `dry_run` y reconciliación sólo indica
`REVISAR_MANUAL`:

```bash
PYTHONPATH=src \
  python scripts/operaciones_seguras.py health data/health_operativo.synthetic.json
```

El CLI no posee probe live: `health --live` falla cerrado hasta que exista una
implementación read-only autorizada por DSI. No se deben pasar manifests
completos, IDs Workspace, PII, contactos, prompts ni credenciales. Ver
`evidencias/runbook-operaciones-seguras-d2-d3.md`. Para uso programático,
importar desde `agente1.operaciones_seguras`; no se reexporta en `agente1`.

## Contrato candidato de insumos A2–A5

`insumos_agentes.py` y
`contracts/insumos/agente1_insumo_candidate_v1.schema.json` validan un envelope
inbound provisional. A1 acepta o rechaza datos no confiables de A2–A5: **no los
invoca, coordina ni orquesta**, no interpreta `payload.content` como control y
no publica contenido. El contrato permanece `CANDIDATO_NO_INSTITUCIONAL` y los
pipelines HU-010/HU-011 todavía no consumen esos envelopes.

Prueba focalizada:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_insumos_agentes.py
```

## Paquete pendiente de validación SEU

`Documentos/PoC/Validacion-SEU/` contiene nueve muestras y un manifest de 17
referencias para una sesión humana. El acta está `PENDIENTE`: no identifica
persona revisora, no contiene puntajes ni decisión y no acredita validación.

Desde la raíz del repositorio se puede verificar o regenerar únicamente el
manifest de hashes, sin copiar contenido ni PII:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python Implementacion/Agente1/scripts/preparar_validacion_seu.py
```

## Resultados Ollama structured de HU-011

El runtime user-local Ollama `0.32.14-1` fue restaurado en el directorio
ignorado por Git. Los tres cortes controlados con `llama3.2:3b` fueron:

1. structured v2: 0/6 aceptadas por `json_invalid`, sin borradores;
2. JSON Schema v3: 0/6; HTTP 400 al compilar la grammar, sin inferencia;
3. JSON Schema v4: 6/6 aceptaciones técnicas, entre 7,035854 y 29,485820 s,
   todas en `PENDIENTE_VALIDACION`.

V4 corrigió el patrón incompatible mediante un enum exacto sin quitar la
allowlist posterior. Esto prueba conformidad mecánica en dos registros y seis
intentos; no prueba estabilidad amplia, SLA, calidad institucional, validación
SEU ni TRL 3. Los benchmarks y manifests v2/v3/v4 están en `evidencias/`.

El incremento quedó versionado en `db06b3e`. En el corte de control del
2026-08-26, la suite completa **se ejecutó fuera del sandbox**: 455 pruebas,
todas en verde y cero fallas `EPERM`. Las 16 fallas de loopback registradas bajo
sandbox son ambientales y no se reproducen fuera de él.

La suite verifica comportamiento del sistema, no redacción de documentación: se
retiraron las pruebas que afirmaban sobre el texto de este README y de los
archivos de `evidencias/`, porque acoplaban el verde a la prosa en lugar de a
una propiedad observable del software.

Un corte posterior amplió la cobertura live de dos a tres actividades en ambos
canales y agregó los cuatro casos negativos contra el modelo real: **6/6
generaciones aceptadas y 4/4 rechazos previos correctos**, con los cuatro
output hashes compartidos reproducidos respecto del corte v4 anterior en una
sesión independiente. El máximo cold subió a 36,225976 s, por encima del máximo
previo de 29,485820 s, lo que refuerza `DEF-A1-003`. Ver
`evidencias/benchmark-hu011-ollama-live-cobertura-ampliada-2026-08-17.md`.

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu011_live_v4.py \
  --salida salida/matriz-hu011-live-v4 --confirm-live-llm
```

El runner exige `--confirm-live-llm` porque invoca un modelo local real, y a
diferencia de la matriz fake **no aborta ante una salida no conforme**: la
registra, para poder medir la tasa real de conformidad.

## Próximo incremento según el Gantt

El próximo cierre técnico es estabilizar la generación live de HU-011: la
regresión v3 del 26/08 registró 0/6 aceptaciones y mantiene abiertos
performance y conformidad mecánica. La persistencia `0001 → 0003` ya fue
validada como spike y no debe integrarse al core ni reemplazar JSONL sin una
necesidad operativa. Luego corresponde completar la baseline documental de
HU-012 y, sólo con autorización, correr Workspace D2 live. En paralelo,
DSI/SEU deben provisionar identidad, recursos y permisos, aprobar
plantilla/criterios y completar el paquete de validación. Hasta entonces
HU-010, HU-011 y HU-012 continúan parciales y el Gate G2 / TRL 3 permanece
pendiente.
