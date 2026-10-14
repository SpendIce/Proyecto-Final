# Agente 1 — MVP técnico controlado

Este directorio reúne la implementación incremental del Agente 1: HU-010 para
gacetillas, HU-011 para borradores de redes sociales, HU-012 para
confirmaciones —fake o Gmail real cercado por una lista de prueba— y el
slice offline de HU-014 para certificados.
También contiene preparación contractual de
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
- `src/agente1/prompts/gacetilla_v3.txt`: prompt versionado con estructura fija, límites y ejemplo sintético; también está marcado como provisional. La línea `Lugar:` se decide por caso antes de armar el prompt, en la estructura y en el ejemplo: v2 la mostraba siempre con la excepción escrita adentro del placeholder, y el modelo la copiaba sin valor para las filas sin lugar, lo que el gate rechazaba como `data_structure`. Ver `DEF-A1-014` y `evidencias/correccion-gacetillas-lugar-ausente-2026-09-08.md`. `gacetilla_v2.txt` se conserva versionado como plantilla histórica.
- `src/agente1/interpretacion.py`: seam de HU-013. Convierte una solicitud en lenguaje natural en una intención del catálogo cerrado, resuelve a qué actividad se refiere y despacha a los pipelines de gacetilla, de post, de emisión de certificados y de plantilla por actividad. Incluye la repregunta con candidatas, el estado entre turnos y el fallback con modelo local.
- `src/agente1/contracts/intenciones_v3.schema.json`: catálogo cerrado de intenciones, versionado y `PROVISIONAL_NO_INSTITUCIONAL`; agrega `generar_plantilla_actividad` (HU-012, #73) sobre `intenciones_v2` (que a su vez agregó `emitir_certificados`, HU-014, #75). `intenciones_v1` y `v2` se conservan como históricas.
- `src/agente1/contracts/interpretacion_fallback_v3.schema.json` y `src/agente1/prompts/interpretacion_fallback_v3.txt`: única salida admitida del modelo en el fallback de interpretación —una intención del catálogo v3 más términos de búsqueda— y el prompt que la pide. El presupuesto de decodificación se deriva de ese contrato. Las parejas v1 y v2 se conservan versionadas como históricas.
- `src/agente1/canal.py` y `src/agente1/canal_planilla.py`: puerto del canal de interacción, con fake en memoria y adapter de planilla offline. Viven por encima del seam: el núcleo no sabe nada de transporte.
- `data/frases_resolucion_actividad.csv`: corpus versionado de frases realistas con tipeos y títulos parciales, calibrado para que todas resuelvan sin inferencia.
- `data/frases_ambiguas_fallback.csv`: corpus deliberadamente **no** calibrado, para medir cuánta cobertura da realmente el camino determinístico. Ver `scripts/medir_cobertura_sin_inferencia.py`.
- `scripts/medir_cobertura_sin_inferencia.py`: mide qué porcentaje de un corpus resuelve sin invocar ningún modelo.
- `scripts/atender_canal_planilla.py`: corrida guiada del canal de planilla offline, sin credenciales. Ver `evidencias/recorrido-prueba-guiada-canal-planilla.md`.
- `src/agente1/canal_form.py`: adapter del canal de pedidos sobre el Google Form restringido al dominio (correo verificado + `PadronRoles` externo por `AGENTE1_PADRON_ROLES_PATH`, ADR 0005), con aviso por `gmail.send` bajo lista de prueba; el correo de «borrador listo» adjunta los links «lo publiqué / lo descarté» del Form de decisiones (#72). Runner: `scripts/atender_canal_form.py` (offline con CSV, live con doble opt-in).
- `src/agente1/decisiones_form.py`: registro de decisiones humanas por el segundo Google Form (#72, ADR 0008): catálogo cerrado de pares tipo/decisión (`publicacion`: `publique`/`descarte`; `plantilla`: `apruebo_semantica`/`apruebo_utilitaria`; `lote`: `apruebo_lote`; `linea_descriptiva`: `apruebo_semantica`/`apruebo_utilitaria`, #74), validación por rol del padrón, anti-tamper por registro de objetos pendientes y auditoría append-only sin correo en claro. Registrar no dispara ninguna acción. Runner: `scripts/registrar_form_decisiones.py`.
- `src/agente1/fuentes.py`: puerto `FuenteSolicitudes` (lectura por id y enumeración del catálogo completo) y adapter CSV compatible con el flujo local.
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
- `src/agente1/confirmaciones.py`: lifecycle por envío de HU-012 con entrega al fake o al adapter Gmail con lista de prueba (D12); rechaza con `notification_mode_mismatch` los tipos cuyo modo de circuito no es `por_envio`.
- `src/agente1/certificados.py`: lifecycle offline de HU-014 con generación de PDF determinista (stdlib, sin dependencias nuevas) y emisión únicamente fake; reusa el circuito de doble aprobación y el registro durable de HU-012. Desde `certificado_emision_v2` (#74) la solicitud puede traer la línea descriptiva de la actividad y las variables del registro (`id_actividad`, `modalidad`, `carga_horaria`), y la emisión con línea exige las precondiciones del Form de decisiones.
- `src/agente1/linea_descriptiva.py` y `src/agente1/prompts/linea_descriptiva_v1.txt`: pipeline de la línea descriptiva del certificado (#74): generación con campos acotados de la fila, gates deterministas, derivación del objeto de decisión `linea_descriptiva-<id_actividad>-<hash>` y verificación de las dos aprobaciones por actividad más la `apruebo_lote` del lote de cierre. Es la fuente única del objeto y de las aprobaciones: `certificados_emision` consume sus funciones.
- `src/agente1/certificados_emision.py`: circuito de emisión del lote de certificados sobre la lista de cierre (#75): validación entera de la lista, aprobaciones por el Form de decisiones (línea descriptiva #74 y lote atado al hash de la lista), PDF por titular con marca `DOCUMENTO DE PRUEBA — SIN VALIDEZ` y entrega por Gmail con lista de prueba. Sin red en offline (`DestinoCorreoArchivo` guarda sólo metadatos del adjunto).
- `scripts/emitir_certificados.py`: runner de la emisión, offline por defecto y live con doble opt-in; ver `evidencias/recorrido-emision-certificados-hu014.md`.
- `scripts/matriz_hu014.py`: matriz reproducible de HU-014, con emisión simulada, reconciliación de reservas colgadas y el circuito completo de la línea descriptiva (`matriz_conformidad_hu014_v2`).
- `src/agente1/politicas/politica_redes_provisional_v1.json` y `src/agente1/politica_redes.py`: política de redes de HU-011 como inventario de reglas verificables, con sus parámetros por canal y el estado de cada regla (`ACTIVA`, `NO_APLICADA_PENDIENTE_SEU`, `NO_MECANIZABLE`).
- `src/agente1/contracts/matriz_origenes_inscripcion_v1.json` y `src/agente1/origenes_inscripcion.py`: matriz operativa de HU-012 por origen de inscripción y decisión de envío fail-closed; ningún origen habilita envío.
- `src/agente1/contracts/plan_pagos_actividad_v1.json`, `src/agente1/contracts/novedades_pago_v1.json`, `src/agente1/pagos.py` y `src/agente1/buzon.py`: corrida de control de pagos de HU-012 — contrato del plan de pago con procedencia por dato, puerto de buzón propio con adapter de carpeta `.eml`, catálogo cerrado de novedades del Departamento (confirmación de la Fundación, comprobante rechazado, comprobante que cubre N cuotas, dirección alternativa, bonificado) con precedencia sobre lo derivado del buzón, y función pura que informa el «k de N» desglosado por preinscripto, las respuestas no asociadas y las novedades aplicadas o con error. La misma corrida planifica el lote diario de `recordatorio_pago`: anticipaciones por actividad (`7|2` por omisión, `SUPUESTO_TECNICO`), regla `hoy = fecha_referencia − anticipación` en `America/Argentina/Buenos_Aires`, nunca después de la referencia, e idempotencia por actividad, inscripción, cuota y anticipación. Además enumera los candidatos a confirmación de inscripción: los preinscriptos cuya cuota 1 quedó `PAGO_CONFIRMADO` o `BONIFICADA` (D9). Subcomando `python -m agente1 control-pagos` con `--novedades` y `--fecha` opcionales.
- `src/agente1/contracts/tipos_notificacion_v2.json` y `src/agente1/tipos_notificacion.py`: catálogo cerrado de los seis tipos de notificación con el modo de circuito por tipo —`por_envio` para los cuatro de HU-012 original e `instrucciones_pago`, `lote` para `recordatorio_pago`— y decisión fail-closed por procedencia de datos.
- `src/agente1/recordatorios.py` y `src/agente1/prompts/recordatorio_pago_provisional_v1.txt`: circuito por lote de los recordatorios de pago —la plantilla se aprueba una sola vez con doble decisión y cada lote diario lleva una aprobación utilitaria con la lista exacta de ítems— sobre el registro, la cola y el destino fake de HU-012.
- `src/agente1/instrucciones_pago.py` y `src/agente1/prompts/instrucciones_pago_provisional_v1.txt`: builders del corte 4 del diseño de pagos —el correo de preinscripción con las instrucciones de pago (D8) y la solicitud de confirmación de inscripción desde el candidato que la cuota 1 `PAGO_CONFIRMADO` o `BONIFICADA` habilita (D9)— más la plantilla provisional del primero, cuyo asunto es el `asunto_preinscripcion` del plan sin la marca de borrador para que la respuesta se asocie.
- `src/agente1/pagos_sheets.py`: adapter que lee las mismas tres fuentes desde las pestañas de la planilla D2 (plan de pago, padrón y novedades), para la demo en vivo — mismas estructuras de dominio y mismas validaciones que los CSV, compone el lector crudo compartido `GoogleSheetsLectorValores` (un `values.get` por pestaña), y falla explícito si falta una pestaña o cambia el encabezado. Configuración por entorno: `AGENTE1_WORKSPACE_SPREADSHEET_ID` (la misma planilla D2), `AGENTE1_WORKSPACE_ACCESS_TOKEN` y `AGENTE1_PAGOS_RANGO_{PLAN,PADRON,NOVEDADES}`. Modo `--planilla` del subcomando `control-pagos`.
- `src/agente1/buzon_gmail.py`: adapter del puerto `BuzonPropio` sobre Gmail API con `gmail.readonly` sobre la cuenta técnica (ADR 0004, D11) — sólo lectura de mensajes del usuario `me`, adjuntos hasheados en memoria, paginación con tope explícito; probado offline con transporte fake y equivalente al buzón `.eml`.
- `src/agente1/contracts/plantilla_actividad_v1.json`, `src/agente1/prompts/plantilla_actividad_base_provisional_v1.txt`, `src/agente1/prompts/plantilla_actividad_generacion_v1.txt` y `src/agente1/plantillas_actividad.py`: plantilla de correo por actividad de HU-012 (#73) — la intención `generar_plantilla_actividad` produce una plantilla por actividad con prosa del modelo y todos los datos dinámicos como variables `{{...}}` (montos, cuotas, fechas, enlaces y destinatario nunca salen del texto generado), el gate descarta la salida entera ante cualquier incumplimiento y el lote de correos por actividad exige las tres decisiones del Form (semántica, utilitaria y `apruebo_lote`) antes de renderizar por destinatario —determinista y sin modelo— y encolar con idempotencia de actividad+inscripción+hash. Los objetos de decisión `tpl-…`/`lote-…` derivan del hash del documento. `scripts/plantilla_actividad_lote_demo.py` corre el circuito completo offline: generación, decisiones por CSV y lote drenado contra el fake con entregas simuladas en disco. Los recordatorios de pago no pasan por este circuito (#38) y el disparo automático es HU-015.
- `data/plan_pagos_notebooklm_n2.csv`, `data/padron_pagos_sintetico.csv` y `data/novedades_pago_sinteticas.csv`: fixture del caso documentado NotebookLM Nivel 2 (cuota única de $20.000, categorías bonificadas, procedencia por dato), padrón sintético y novedades sintéticas para correr la demo local.
- `scripts/medir_capacidad_hu011.py`: prueba de capacidad local contra el volumen de referencia informado por la SEU; mide latencia fría y caliente y tasa de conformidad, y proyecta el mes.
- `scripts/operaciones_seguras.py`: health, reconciliación, consolidación y retención en dry-run.
- `src/agente1/contracts/insumos/agente1_insumo_candidate_v2.schema.json`, `src/agente1/insumos_agentes.py`, `src/agente1/insumos_corrida.py`, `src/agente1/insumos_sheets.py` y `src/agente1/cli_insumos.py`: entrada push de insumos A3–A5 (ADR 0008, #82) — el envelope candidato (A2 fuera, `data_origin` con `provisional_producer`), la corrida de la pestaña «Insumos de agentes» (estados `borrador generado`/`rechazado`/`aceptado sin flujo`, idempotencia por `correlation_id` en `insumos-procesados.jsonl`, despacho `evento`→HU-010), el escritor `values.update` acotado con su réplica CSV, y el subcomando `insumos-agentes` offline/live con doble opt-in.
- `src/agente1/contracts/insumos/a3_evento_gacetilla_v1.schema.json`: contrato declarado del `payload.content` de un insumo A3 `evento` destinado a gacetilla (#83) — campos admitidos y obligatorios que la corrida aplica antes de llamar al pipeline, con códigos de rechazo propios y procedencia del insumo visible en el borrador y en la auditoría.
- `src/agente1/scheduler.py`, `src/agente1/cli_scheduler.py` y `systemd/agente1-scheduler.{service,timer}` + `systemd/agente1-scheduler-loop.service`: scheduler local de las corridas programadas (#84) — agenda por ticks anclada a la ventana de operación configurable (`AGENTE1_SCHEDULER_*`), lock `flock` contra solapamientos, log versionado `scheduler-corridas.jsonl` (entrada de #88), slot diario con la purga (#87) y el respaldo diario (#86) en ese orden, y las unidades `systemd --user` como plantillas instalables junto al bucle `--loop` alternativo.
- `src/agente1/respaldo.py`, `scripts/respaldar_estado.py` y `scripts/restaurar_respaldo.py`: respaldo diario del estado local en Drive (#86, ADR 0009) — artefacto `.tar.gz` con manifiesto de hashes, subida siempre como archivo nuevo a la carpeta de la cuenta técnica, borrado de los propios vencidos a 30 días auditado con hash y fecha, aviso al operador por el destino Gmail cercado o por el fake declarado, y restauración manual que marca `ENVIO_INDETERMINADO` lo posterior a la marca del respaldo.
- `src/agente1/medicion_slo.py` y `scripts/medir_nivel_slo.py`: medición del nivel verificado de los SLO (#88) desde la auditoría ya escrita, con declaraciones `muestra insuficiente` / `sin_fuente` / `pendiente #50/#51` en lugar de números inventados, y emisión de la evidencia versionable en `evidencias/`.
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
| Por qué el encabezado de la planilla debe ser exacto (y qué implica para Google Forms) | `google_workspace.py`, `_parsear_filas` |
| Por qué el generador sólo acepta loopback | `src/agente1/ollama.py`, docstring de módulo y `_validar_base_url` |
| Por qué HU-012 modela un envío que no se hace | `src/agente1/confirmaciones.py`, docstring de módulo |
| Por qué la cola de envíos es una pista de trabajo y no la autoridad | `confirmaciones.py`, docstrings de `ColaEnvios`, `ColaEnviosArchivo` y `drenar_envios` |
| Por qué HU-014 modela una emisión que no se hace y por qué el PDF es stdlib | `src/agente1/certificados.py`, docstring de módulo |
| Por qué la línea descriptiva se aprueba una vez por actividad y no por certificado | `src/agente1/linea_descriptiva.py`, docstring de módulo y `declarar_linea_pendiente` |
| Por qué el objeto de la línea usa guiones y no `:` | `linea_descriptiva.py`, docstring de módulo y `objeto_id_linea_descriptiva` |
| Por qué el prompt de la línea no recibe fecha, carga ni modalidad | `linea_descriptiva.py`, comentario de `CAMPOS_PROMPT` |
| Por qué el lote de certificados se aprueba contra el hash de la lista y no contra la actividad | `src/agente1/certificados_emision.py`, docstring de módulo y `objeto_lote_cierre` |
| Por qué una fila inválida bloquea el lote entero en lugar de saltarla | `certificados_emision.py`, `parsear_lista_cierre` |
| Por qué quien cargó la lista no puede aprobarla | `certificados_emision.py`, `revisar_aprobacion_lote` |
| Por qué un adjunto de Gmail no agrega ningún endpoint nuevo | `src/agente1/gmail_envio.py`, docstring de `AdjuntoCorreo` y `entregar` |
| Por qué no se borra nada, sólo se marca | `persistencia.py`, `eliminar_logicamente_anteriores` |
| Qué prueba y qué no prueba la auditoría de seguridad | `src/agente1/auditoria_d2.py`, `auditar_manifest` |
| Por qué los límites de redes son provisionales | `src/agente1/politica_redes.py`, docstring de módulo (DEF-A1-007) |
| Por qué ningún origen de inscripción habilita envío | `src/agente1/origenes_inscripcion.py`, docstring de módulo |
| Por qué la prosa de una persona nunca llega a un prompt como instrucción | `src/agente1/interpretacion.py`, docstring de módulo y ADR 0001 |
| Por qué el despacho no se deriva del campo `pipeline_integrado` del catálogo | `interpretacion.py`, comentario de `INTENCIONES_CON_DESPACHO` |
| Por qué el registro de interacciones no guarda la prosa ni la identidad en claro | `interpretacion.py`, docstring de módulo y `_finalizar`; ADR 0002 |
| Por qué la interacción pendiente no necesita durabilidad | `interpretacion.py`, docstring de `RegistroPendientes` |
| Por qué los términos del modelo se suman a la prosa en lugar de reemplazarla | `interpretacion.py`, docstring de `_buscar_actividad_con_terminos` |
| Por qué se rechaza un intérprete cuyo presupuesto no cubre el contrato | `interpretacion.py`, comentario de `_interpretar_con_modelo` (DEF-A1-013) |
| Por qué el seam tiene una guarda de último recurso además de traducir cada falla prevista | `interpretacion.py`, docstring de `interpretar_solicitud` |
| Por qué el campo `intencion` que devuelve el modelo sólo puede rechazar, nunca habilitar | `interpretacion.py`, comentario dentro del fallback; ADR 0001 |
| Por qué un arreglo de texto libre acotado sí se puede dimensionar | `src/agente1/presupuesto.py`, docstring de `_dimensionar_arreglo` |
| Por qué el núcleo no sabe nada del transporte de la interacción | `src/agente1/canal.py`, docstring de módulo y de `atender_canal` |
| Por qué un link de decisión alterado se rechaza sin firmar nada | `src/agente1/decisiones_form.py`, docstring de módulo y `RegistroDecisiones`; ADR 0008 |
| Por qué registrar una decisión no dispara ninguna acción del agente | `decisiones_form.py`, docstring de módulo |
| De dónde sale el rol que una decisión exige | `decisiones_form.py`, comentario de `ROLES_POR_DECISION`; ADR 0005 |
| Por qué medir el corpus calibrado da 100 % y eso no informa nada | `scripts/medir_cobertura_sin_inferencia.py`, docstring de módulo |
| Por qué la situación de pagos se recalcula en cada corrida y no hay registro de pagos | `src/agente1/pagos.py`, docstring de módulo; ADR 0003 |
| Por qué el agente lee sólo su propio buzón | `src/agente1/buzon.py`, docstring de módulo; ADR 0004 |
| Por qué `MensajeBuzon` no tiene campo cuerpo ni datos de adjunto | `src/agente1/buzon.py`, docstrings de módulo y de `MensajeBuzon`; ADR 0001 |
| Por qué una respuesta nunca se asocia por nombre ni por similitud | `src/agente1/pagos.py`, docstring de módulo y de `correr_control_pagos` |
| Por qué `PAGO_CONFIRMADO` sólo sale de una novedad y nunca de un comprobante | `pagos.py`, docstring de módulo y de `_aplicar_novedad_cuota`; contrato `novedades_pago_v1.json` (D1) |
| Por qué una novedad inválida se informa en lugar de ignorarse | `pagos.py`, docstring de `cargar_novedades_csv` y de `NovedadConError` |
| Por qué `recordatorio_pago` no pasa por `procesar_confirmacion` | `src/agente1/tipos_notificacion.py` (`modo_circuito`), `confirmaciones.py` (`notification_mode_mismatch`); catálogo `tipos_notificacion_v2` |
| Por qué la plantilla se aprueba una vez y el lote cada día | `src/agente1/recordatorios.py`, docstring de módulo |
| Por qué la lista de ítems de la aprobación del lote debe ser exacta | `recordatorios.py`, docstrings de `AprobacionLote` y `encolar_lote_recordatorios` |
| Por qué un recordatorio nunca sale después de la fecha de referencia | `pagos.py`, docstring de `planificar_recordatorios`; D15 del diseño |
| Por qué los links y datos bancarios van al cuerpo y no a la auditoría | `recordatorios.py`, docstrings de `_auditar` y `_auditar_item`; `prompts/recordatorio_pago_provisional_v1.txt` |
| Por qué una pestaña faltante o con encabezado distinto nunca devuelve una lista vacía | `pagos_sheets.py`, docstring de módulo y de `_leer_values` |
| Por qué el modelo no escribe montos, fechas ni enlaces en la plantilla de actividad | `src/agente1/plantillas_actividad.py`, docstring de módulo y gate de `plantilla_actividad_v1`; contrato `contracts/plantilla_actividad_v1.json` |
| Por qué la aprobación de una plantilla vale para esa redacción exacta | `plantillas_actividad.py`, docstring de módulo (`tpl-…`/`lote-…` derivan del `sha256` del documento) |
| Por qué A2 no entrega insumos en la pestaña | `src/agente1/insumos_agentes.py`, docstring de módulo; ADR 0008 |
| Qué decide el estado escrito en la fila y qué el registro local | `src/agente1/insumos_corrida.py`, docstring de módulo y de `_despachar` |
| Por qué una reserva `inicio` sin `final` bloquea en vez de reintentar | `insumos_corrida.py`, docstring de módulo |
| Por qué el write a Sheets sólo puede tocar `C{n}:D{n}` de una pestaña | `src/agente1/insumos_sheets.py`, docstring de módulo y de `GoogleSheetsEscritorEstadoInsumos` |
| Por qué el `id_actividad` del evento se deriva del `correlation_id` | `insumos_corrida.py`, docstring de módulo y `_id_solicitud_insumo` |
| Qué campos exige el `content` de un `evento` A3 para gacetilla | `contracts/insumos/a3_evento_gacetilla_v1.schema.json`; `insumos_corrida.py` (`CAMPOS_EVENTO`, `CAMPOS_EVENTO_OBLIGATORIOS`) |
| Cómo se ve en el borrador y en el log que la pieza salió de un insumo | `procesamiento.py` (`ProcedenciaInsumo`, `_bloque_procedencia`, `_con_procedencia`) |
| Por qué el respaldo no puede sobrescribir otro respaldo | `src/agente1/respaldo.py`, docstring de módulo y de `GoogleDriveRespaldoDiario` |
| Por qué el borrado de respaldos está cercado tres veces | `respaldo.py`, docstrings de módulo, de `GoogleDriveRespaldoDiario` y de `correr_respaldo_diario`; ADR 0009 |
| Por qué la restauración marca indeterminado en vez de reenviar | `respaldo.py`, docstrings de `restaurar_estado_respaldo` y de `_marcar_posteriores_indeterminados` |
| Por qué el denominador de disponibilidad es la agenda y no las líneas del log | `src/agente1/medicion_slo.py`, docstring de módulo y de `indicador_disponibilidad` |
| Por qué el tiempo de atención exige el CSV de respuestas del Form | `medicion_slo.py`, docstrings de módulo y de `indicador_tiempo_atencion` |
| Por qué el SLO de aprobación a envío descuenta el tiempo fuera de la ventana | `medicion_slo.py`, docstrings de `indicador_aprobacion_envio` y de `segundos_en_ventana` |
| Por qué el manifest de versión no se controla a sí mismo ni incluye la configuración por entorno | `src/agente1/manifest_version.py`, docstring de módulo y `RUTAS_CONTROLADAS`; ADR 0010 |
| Por qué el gate de integridad vive en el armado del modo live y no en la CLI offline | `manifest_version.py`, docstring de módulo, y `cli_insumos.py`, `_dependencias_live` |
| Por qué la credencial del agente es una cuenta de servicio que sólo se hace pasar por una lista cerrada de cuentas | `src/agente1/workspace_auth.py`, docstring de módulo y de `CuentaServicioDelegadaProvider`; `contracts/cuentas_suplantables_v1.json`; ADR 0011 |
| Por qué el *assertion* RS256 se firma con `openssl` y no con una dependencia de criptografía | `workspace_auth.py`, docstring de `_firmar_rs256` |
| Por qué cada token deja asentado por quién se pidió | `workspace_auth.py`, docstring de `AuditoriaCuentaSuplantada` y de `obtener_access_token` |

Cada archivo de `tests/` abre con un docstring que resume qué cubre esa suite,
de modo que la pregunta "¿dónde está probado esto?" se responda leyendo los
encabezados.

## Ejecutar las pruebas

Desde este directorio:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache python -m pytest -q
```

## CI: suite, cobertura y linter

El workflow `.github/workflows/agente1-ci.yml` corre en cada push y pull
request que toque `Implementacion/Agente1/`: instala `uv`, sincroniza las
dependencias declaradas, ejecuta `ruff check` y la suite con cobertura, y
publica el número en el resumen del job y como artefacto `coverage.txt`. No
usa secretos ni toca la red de Google: sólo corre la suite determinista. El
número de cobertura no tiene umbral bloqueante; es evidencia de *capacidad de
prueba* y *analizabilidad* para el Anexo 2.

El mismo chequeo se reproduce en local, desde este directorio:

```bash
uv sync --frozen
uv run ruff check .
uv run pytest -q --cov=src --cov-report=term-missing
uv run coverage report > coverage.txt   # mismo artefacto que sube el job
```

`ruff` está configurado en `pyproject.toml` con `select = ["E", "F", "I", "W"]`:
pycodestyle, Pyflakes e imports ordenados. `E501` queda deshabilitada porque
el proyecto mantiene docstrings y aserciones en líneas largas a propósito, y
las familias del conjunto ampliado de ruff 0.17 (UP, BLE, TRY, S, SIM, RUF y
afines) no se habilitaron porque cumplirlas exigía un refactor amplio sin
hallazgos de bug concretos. Los `per-file-ignores` documentan los tres casos
deliberados: el bootstrap de `sys.path` de los scripts, el test que carga un
script por `importlib` y la demo con handlers HTTP compactos.

Nota para la extracción del repo (issue #80): el workflow vive en
`.github/workflows/` de la raíz porque GitHub Actions sólo lo ejecuta desde
ahí. Viaja con el repositorio del Agente 1 y, una vez extraído, los filtros
`paths:` de los disparadores deben ajustarse a la raíz nueva o quitarse.

## Ejecutar el smoke

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache bash scripts/smoke.sh
```

La CLI imprime un JSON con estado, correlation ID y paths de evidencia. Un caso válido debe finalizar en `PENDIENTE_VALIDACION`; uno incompleto finaliza en `INCOMPLETA`, retorna código 2, no invoca al generador y no crea un borrador. Una falla, salida vacía o salida no conforme finaliza en `FALLIDA`, retorna código 2 y tampoco crea borrador.

Un identificador rechazado o una solicitud inexistente finaliza en `INVALIDA` con un error genérico y código 2, sin traceback. Esos casos asignan correlation ID y generan un audit log con código cerrado y hash del identificador, sin copiar el identificador ni el path consultado. Fallas operativas o contractuales de una fuente terminan en `FALLIDA`, no invocan al generador ni crean borrador, y registran `source_error_code` sin token, cuerpo remoto ni fila de entrada.

## Adapter contractual de Google Sheets

El seam `FuenteSolicitudes` permite que el core procese la misma forma contractual desde CSV o Sheets. El adapter Sheets implementa y prueba offline una solicitud `spreadsheets.values.get` hacia el host oficial fijo, con rango A1 percent-encoded, `majorDimension=ROWS`, `valueRenderOption=FORMATTED_VALUE`, deadline total y respuesta limitada a 1 MiB. Exige las columnas exactas del contrato v2 de la planilla de actividades (`COLUMNAS_ACTIVIDADES_V2`, el mismo que usa el adapter CSV), valores string e identificadores únicos; completa únicamente las celdas finales vacías que la API puede omitir.

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
  --ollama-num-predict 300
```

El timeout conserva semántica de deadline total para conexión, envío, headers y cuerpo; un servidor trickle no puede reiniciarlo. La evidencia CPU live mostró generaciones que superan 30 segundos, por lo que el presupuesto operativo usa 45 segundos por defecto y admite configuración entre más de cero y 120 segundos. Este ajuste evita confundir capacidad del host con un corte artificial; no modifica ni declara cumplido un requisito institucional de performance. Puede definirse `OLLAMA_TIMEOUT` en el smoke live. `num_predict` usa 512 por defecto, derivado del contrato y no de una corrida que anduvo: `presupuesto.presupuesto_minimo_num_predict` construye el documento JSON más grande que admite el contrato creativo vigente y lo convierte a tokens con la relación de caracteres por token menos favorable medida sobre el mismo tokenizador, lo que da 484 tokens. Admite valores entre 32 y 1024, y una regresión falla si el default deja de cubrir el contrato. El piso queda bajo a propósito, para que una corrida de evidencia pueda elegir un presupuesto insuficiente y demostrar el agotamiento; lo que protege a una baseline es el default, no el rango. El techo acota una generación desbocada y deja margen sobre los 484 requeridos: con el techo pegado al requerido, un contrato apenas más largo se quedaba sin ninguna configuración válida. Subir el tope casi no cuesta porque `num_predict` acota, no fija: la latencia la determinan los tokens que el modelo llega a emitir. El valor efectivo queda auditado en cada ejecución Ollama; el fake registra `null`. También puede definirse `OLLAMA_NUM_PREDICT`. Cuando el presupuesto igual se agota, Ollama responde `done: true` con `done_reason: "length"`: el adapter lo detecta y el pipeline registra `presupuesto_agotado` en lugar de dejar que el corte llegue al parser como `json_invalid`. Ver `DEF-A1-013` y `evidencias/medicion-presupuesto-decodificacion-2026-09-08.md`. Errores HTTP, timeouts o respuestas inválidas terminan como `FALLIDA`: no crean borrador ni exponen prompt, URL o cuerpo remoto en la CLI o el audit log. Por seguridad, el adapter sólo acepta HTTP hacia `localhost`, direcciones `127.0.0.0/8` o `::1`; no admite hosts remotos, HTTPS, credenciales embebidas ni paths adicionales.

El smoke real deja sus resultados en un subdirectorio temporal de `salida/`, ignorado por Git. Verifica controles técnicos; no reemplaza la revisión humana, la validación SEU ni permite declarar cumplido el Gate TRL 3.

## HU-011 — matriz contractual provisional

HU-011 reutiliza los puertos de fuente y destino para producir borradores
separados de Instagram y LinkedIn. El contrato `post_input_v2`, las políticas
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

La credencial vigente es una **cuenta de servicio con *domain-wide
delegation*** (ADR 0011). El host declara `AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY`
(la ruta de la clave JSON, con `chmod 600` y fuera del repo) y
`AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT` (la cuenta por la que el agente se
hace pasar, que debe estar en `contracts/cuentas_suplantables_v1.json`). Cada
token emitido deja el sha256 de la cuenta suplantada en
`logs/cuenta-suplantada.jsonl`. El trío OAuth por refresh token
(`AGENTE1_WORKSPACE_OAUTH_*`) queda como respaldo explícito hasta el issue
#99.

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

## HU-012 — confirmaciones

HU-012 renderiza determinísticamente un asunto y cuerpo provisional con
`BORRADOR — NO ENVIAR`. Valida destinatario y exige las dos aprobaciones del
circuito —la semántica del Responsable de Gestión del Conocimiento y la
utilitaria del Coordinador de Extensión (CU10 del bible)— antes de habilitar
cualquier entrega. Conserva el mismo borrador durante el lifecycle
`PENDIENTE_VALIDACION → APROBADA_SEMANTICA/APROBADA_UTILITARIA → APROBADA →
ENVIO_RESERVADO → ENVIADA_SIMULADA/FALLIDA` (o `RECHAZADA` ante una decisión
negativa), con `ENVIO_INDETERMINADO` para una reserva que quedó colgada, y usa
transiciones atómicas para impedir retrocesos, carreras y entregas
duplicadas. Una sola aprobación —de cualquiera de los dos roles— deja el
registro en el estado parcial correspondiente y no habilita el envío.
`ENVIADA_SIMULADA` registra la entrega contra el destino habilitado: el fake
en memoria (`DestinoConfirmacionesFake`) o el adapter Gmail con lista de
prueba (`GmailDestinoConfirmaciones`, ver más abajo). El estado terminal del
lifecycle conserva su nombre histórico aunque la entrega haya sido real;
el campo `delivery_mode` de la auditoría distingue `fake` de
`gmail_test_list`.

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  bash scripts/smoke_confirmaciones.sh salida/smoke-hu012

PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_confirmaciones.py tests/test_matriz_hu012.py
```

### Registro durable y reconciliación

`RegistroConfirmacionesMemoria` alcanza para una corrida, pero la idempotencia
que importa es la que aguanta una caída: si el proceso muere después de reservar
el envío y al reiniciar no queda rastro, un reintento vuelve a entregar. Por eso
`RegistroConfirmacionesArchivo` guarda el estado en disco, un archivo por clave.

`crear` publica el archivo con `os.link` desde un temporal ya escrito: `link`
falla si el destino existe —lo que da la semántica de «crear una vez» entre
procesos— y además publica el registro completo. Con `O_EXCL` alcanzaba para la
exclusión pero no para eso: el archivo quedaba visible y vacío entre la
creación y la escritura, y otro proceso que perdía la carrera lo leía justo ahí.
`transicionar` toma `flock` sobre un `.lock` por clave, no sobre el `.json`,
porque el registro se reemplaza con `os.replace` y un lock sobre el `.json`
quedaría sobre el inodo viejo. El directorio queda `0700` y los archivos `0600`:
el registro guarda el texto del borrador, mientras que la auditoría sigue
llevando sólo hashes.

`reconciliar_envios_reservados` cierra las reservas que quedaron colgadas **sin
volver a entregar**. Una reserva interrumpida es indeterminada por definición: el
proceso murió entre reservar y saber el resultado, así que nadie puede afirmar si
la entrega ocurrió. Reintentar sería apostar a que no, y el costo de equivocarse
es una confirmación duplicada a una persona. La reconciliación mueve el registro
a `ENVIO_INDETERMINADO`, desde donde el pipeline no transiciona, para que una
persona decida con el registro a la vista.

```bash
uv run pytest -q tests/test_confirmaciones_durables.py
```

### Purga de datos personales (#87)

La retención es acotada (ADR 0009, término del glosario): el texto del
borrador y los datos de la persona viven en el registro sólo durante el
ciclo de envío y una ventana de reconciliación de 30 días, contados desde
la última transición del registro. Vencida la ventana,
`RegistroConfirmacionesArchivo.purgar_terminadas` reescribe el archivo de
cada registro terminal —`ENVIADA_SIMULADA`, `EMITIDA_SIMULADA`, `FALLIDA`
y `RECHAZADA`, el conjunto explícito `ESTADOS_PURGABLES`— con `asunto` y
`cuerpo` vacíos y `purgado_en` asentado. La reescritura usa la misma
atomicidad de siempre (temporal + `os.replace`, bajo el `.lock` por
clave) y conserva la clave de idempotencia, el estado, las fechas y el
hash del contenido borrado: una solicitud repetida sigue chocando contra
la misma clave, así que purgar nunca habilita un reenvío.
`ENVIO_INDETERMINADO`, `EMISION_INDETERMINADA`, todo estado no terminal y
cualquier estado desconocido no se tocan: siguen a la vista hasta que una
persona decida. Un registro escrito antes de que existieran las fechas se
mide por el `mtime` de su archivo. Como el registro de HU-014 es el mismo
objeto, la purga cubre los certificados con la misma regla.

`correr_purga_registro` es la operación invocable: corre la purga y anexa
una línea por corrida a `logs/confirmaciones-hu012.jsonl` con la cantidad
purgada y el hash del conjunto de claves, nunca contenido. El comando
manual es:

```bash
PYTHONPATH=src \
  python scripts/purgar_registro.py \
    --registro salida/registro-confirmaciones \
    --salida salida
```

El scheduler local (#84) invoca este comando una vez por día dentro de la
ventana de operación, en el slot diario de la primera corrida, siempre
antes del respaldo diario del estado (#86): ningún respaldo conserva
texto que la política ya venció, y si la purga del día falla el respaldo
del día también falla a propósito (ver la sección del scheduler más
abajo).

```bash
uv run pytest -q tests/test_purga_registro.py
```

### Respaldo diario del estado local en Drive (#86)

El respaldo cierra el ciclo de la retención acotada (ADR 0009): una vez
por día hábil, en el slot diario del scheduler y después de la purga, el
estado local del agente viaja a una carpeta de Drive de la cuenta técnica
que no se comparte con nadie. Así el RPO queda en un día hábil y el
registro que protege contra envíos duplicados sobrevive a la pérdida del
host; el respaldo comparte dominio de falla con Workspace, que es la
limitación declarada del ADR.

El artefacto es `agente1-respaldo-AAAA-MM-DD.tar.gz` con un
`manifest.json` adentro: record `agente1_respaldo_v1`, la marca
`creado_en` del empaquetado y un sha256 por miembro. Viaja el conjunto
declarado y nada más — el registro durable de confirmaciones, los JSONL
de `logs/`, `insumos-procesados.jsonl`, `estado-canal-form/`,
`estado-decisiones/`, `cola-envios/` y los manifests; los borradores
generados no son estado y quedan fuera. La subida es siempre
`files.create`: el adapter no tiene operación de actualización, así que
un respaldo nunca se sobrescribe; una segunda corrida del mismo día lo
omite por nombre.

El borrado por antigüedad —más de 30 días, la ventana de reconciliación—
es la única excepción a «el agente nunca borra» y está cercada tres
veces: sólo la carpeta fijada al construir el adapter, sólo archivos con
la convención `agente1-respaldo-*.tar.gz` más el marker `appProperties`
`agente1_respaldo=v1`, y con `drive.file` Drive además sólo devuelve
archivos que la aplicación creó. Cada borrado queda en
`logs/respaldo-diario.jsonl` con hash y fecha, sin contenido. Una falla
del paso se audita con código cerrado, se avisa al operador por el
destino Gmail cercado por la lista de prueba —o por el fake declarado en
offline— y la corrida sigue: el paso se reintenta en el tick siguiente.

La restauración es un procedimiento manual: el operador descarga el
artefacto y corre `scripts/restaurar_respaldo.py`, que verifica hashes,
repone archivos sin pisar lo que ya existe (un archivo distinto es
`conflicto`, nunca sobreescritura) y marca el registro: toda reserva pasa
al indeterminado de su pipeline y toda aprobación posterior a la marca
del respaldo pasa a `ENVIO_INDETERMINADO`. Lo indeterminado no se
reenvía: una persona cruza cada clave contra Gmail Enviados. El
procedimiento completo está en el runbook del scheduler
(`Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md`).

```bash
# Offline: carpeta local fake declarada, aviso en JSONL, sin red.
AGENTE1_RESPALDO_CARPETA_FAKE=salida/carpeta-respaldo-fake \
PYTHONPATH=src \
  python scripts/respaldar_estado.py --salida salida \
    --registro salida/registro-confirmaciones

# Live (operador, doble opt-in): carpeta real + aviso a dirección de la
# lista de prueba de Gmail.
AGENTE1_RESPALDO_CARPETA_ID=<id-carpeta> \
AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA=SI \
AGENTE1_RESPALDO_AVISO_DESTINATARIO=operador@example.com \
PYTHONPATH=src \
  python scripts/respaldar_estado.py --salida salida \
    --registro salida/registro-confirmaciones

# Restauración manual (sin red: el operador provee el artefacto).
PYTHONPATH=src \
  python scripts/restaurar_respaldo.py \
    --artefacto agente1-respaldo-2026-10-05.tar.gz \
    --salida salida --registro salida/registro-confirmaciones

uv run pytest -q tests/test_respaldo.py tests/test_respaldo_scripts.py
```

### Cola de envío asíncrono (s4d)

El envío también puede diferirse: `procesar_confirmacion(..., asincrono=True,
cola=...)` mueve el registro de `APROBADA` a `ENVIO_ENCOLADO` y deja un ítem
en la cola en lugar de entregar. El camino síncrono (`enviar=True`) no cambia.
No hay Celery ni Redis: el puerto `ColaEnvios` tiene una implementación en
memoria (`ColaEnviosMemoria`) y una durable en archivo (`ColaEnviosArchivo`)
con el mismo patrón atómico del registro (un archivo por ítem publicado con
`os.link`, orden FIFO por una secuencia tomada bajo `flock`).

`drenar_envios(registro=..., cola=..., destino=..., directorio_salida=...)` es
el worker: procesa los ítems debidos una vez por corrida, reserva con el
mismo compare-and-set (`ENVIO_ENCOLADO` → `ENVIO_RESERVADO` →
`ENVIADA_SIMULADA`/`FALLIDA`) y reintenta con un presupuesto fijo de 3
intentos; cada intento queda auditado en el mismo JSONL con `evento` e
`intento`. Un ítem cuyo registro ya no está en `ENVIO_ENCOLADO` se descarta
sin re-entregar, y una reserva colgada sigue yendo a `ENVIO_INDETERMINADO`
por la reconciliación existente. Sin un destino habilitado por tipo exacto
—fake o Gmail con lista— el worker no procesa nada: el encolado sólo cambia
cuándo se entrega, no qué se entrega.

```bash
uv run pytest -q tests/test_cola_envios.py
```

### Destino Gmail con lista de prueba (D11/D12)

`src/agente1/gmail_envio.py` implementa el mismo puerto
`DestinoConfirmaciones` contra `gmail.send`
(`POST gmail.googleapis.com /gmail/v1/users/me/messages/send`), con el mismo
transporte HTTP intercambiable de los adapters de Workspace. Es el primer
destino que manda correo de verdad, y entra cercado por las decisiones D11
y D12 del diseño de control de pagos:

- **La lista de direcciones de prueba es condición de existencia.** Sale de
  `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` (variable de entorno, separadas por
  coma, fuera del repo). Ausente, vacía o con una dirección inválida, el
  destino no se construye: `gmail_test_list_missing`/`gmail_test_list_invalid`.
- **La lista se re-verifica en cada entrega, antes del token y de la red.**
  Un destinatario fuera de la lista levanta `EntregaRechazadaError`
  (`recipient_off_test_list`): el registro queda `FALLIDA` —terminal, sin
  reintentos— aunque el envío tenga las dos aprobaciones. Pasar a
  destinatarios reales es un cambio de configuración, no de código.
- **El cuerpo lleva las dos marcas de borrador.** El adapter exige que el
  cuerpo empiece con `BORRADOR — NO ENVIAR` (la marca de HU-012) y le
  antepone `# BORRADOR — NO PUBLICAR` antes de armar el MIME: mientras rija
  la lista, el correo se declara no publicable.
- **El candado sigue siendo por tipo exacto.** `procesar_confirmacion` y
  `drenar_envios` habilitan exactamente `DestinoConfirmacionesFake` o
  `GmailDestinoConfirmaciones`; una subclase, un envoltorio o cualquier otro
  objeto sigue dando `offline_destination_required` (vía síncrona) o un
  worker que no procesa (vía encolada).
- **La auditoría D2 admite exactamente un servicio de distribución.** El
  check `no_distribution_endpoints` pasa el `POST` de `messages.send` sólo si
  el manifest declara `gmail_send.test_list_active`; cualquier otra ruta de
  Gmail —lectura incluida— y cualquier otro servicio siguen prohibidos.

Las pruebas (`tests/test_gmail_envio.py`) inyectan transporte y token fake:
éxito, errores HTTP, timeout, respuesta excesiva y todos los rechazos de
política sin una sola llamada de red. **No hay ejecución live ni
destinatarios institucionales**: lo demostrado es el mecanismo cercado.

Las APIs primarias (`SolicitudConfirmacion`, `AprobacionHumana`,
`ResultadoConfirmacion`, `RegistroConfirmacionesMemoria`,
`RegistroConfirmacionesArchivo`, `reconciliar_envios_reservados`,
`DestinoConfirmacionesFake` y `procesar_confirmacion`) se exportan desde
`agente1`, al igual que la cola (`ItemEnvio`, `ColaEnviosMemoria`,
`ColaEnviosArchivo`, `ResultadoEnvioEncolado` y `drenar_envios`), el
circuito por lote (`AprobacionLote`, `registrar_plantilla_recordatorio`,
`aprobar_plantilla_recordatorio`, `encolar_lote_recordatorios` y
`correr_lote_recordatorios`) y los builders del corte 4
(`solicitud_instrucciones_pago`, `solicitud_confirmacion_inscripcion`,
`planificar_confirmaciones`, `CandidatoConfirmacion`,
`DatosInstruccionesPago`, `CuotaInstrucciones` y
`TIPO_INSTRUCCIONES_PAGO`). Contrato, plantilla, aprobaciones de la matriz y destinatarios son
sintéticos o provisionales. Consultar
`evidencias/limites-hu012-offline.md`; no hay envío institucional, validación
SEU ni evidencia de TRL 3.

### Recordatorios de pago por lote

`recordatorio_pago` es el primer tipo cuyo modo de circuito no es por envío:
el catálogo `tipos_notificacion_v2` lo declara `lote` y
`procesar_confirmacion` lo rechaza con `notification_mode_mismatch`. La
corrida de control de pagos deriva la situación de cada cuota —como siempre,
sin registro propio de pagos (ADR 0003)— y `planificar_recordatorios` arma el
lote del día con las cuotas `PENDIENTE` cuya fecha de referencia cae exactamente
`anticipacion_d` días después de `hoy` (`7|2` por omisión, configurable por
actividad, zona `America/Argentina/Buenos_Aires`). Un inscripto que el plan
declara bonificable pero el padrón no puede verificar entra igual al lote con
la marca `bonificacion_no_verificable`, para que la revisión humana la vea.

El circuito tiene dos aprobaciones en dos niveles distintos
(`recordatorios.py`): la **plantilla** provisional se registra y aprueba una
sola vez con la doble decisión de HU-012 (semántica y utilitaria), y cada
**lote** diario pide una aprobación utilitaria que nombra la lista exacta de
ítems —una lista parcial (`batch_approval_partial`), con claves ajenas
(`batch_item_unknown`) o con el rol equivocado no encola nada. Con el lote
autorizado, cada ítem se renderiza desde la plantilla, se registra con su
clave de idempotencia y se encola; `correr_lote_recordatorios` drena la cola
contra `DestinoConfirmacionesFake`. Repetir la corrida el mismo día produce
las mismas claves y el registro devuelve `DUPLICADA`: no hay envíos dobles.
Los medios de pago —link o dato bancario— van en el cuerpo del borrador y
nunca en la auditoría, que sigue llevando sólo hashes, claves y decisiones.

```bash
uv run pytest -q tests/test_recordatorios_pagos.py tests/test_matriz_hu012.py
```

### Instrucciones de pago y confirmación por pago

El corte 4 del diseño de pagos suma dos piezas sobre el circuito por envío
de siempre (`instrucciones_pago.py`). La primera es el sexto tipo del
catálogo, `instrucciones_pago` (D8): `solicitud_instrucciones_pago` arma la
solicitud desde el plan y la fila del padrón copiando cuotas, medios de
pago, bonificaciones y fechas hacia `datos_pago`, la estructura que la
solicitud porta y que la clave de idempotencia cubre entera. El borrador
sale de `prompts/instrucciones_pago_provisional_v1.txt` y su asunto es el
`asunto_preinscripcion` del plan —exacto, sin la marca de borrador— porque
la respuesta del preinscripto con el comprobante se asocia a la actividad
por ese asunto normalizado (§4.2): la marca viaja sólo en el cuerpo, que es
donde el destino habilitado la exige. Un `datos_pago` ausente o mal formado
—sin asunto, sin cuotas, monto inválido o fecha no ISO— es
`required_fields_missing`, nunca un borrador recortado.

La segunda es la confirmación de inscripción que la cuota 1 habilita (D9):
`planificar_confirmaciones` enumera en el informe de la corrida los
preinscriptos cuya cuota 1 quedó `PAGO_CONFIRMADO` —única salida posible de
una novedad `CONFIRMADO_FUNDACION`— o `BONIFICADA`. Un
`COMPROBANTE_PRESENTADO` no genera candidato: la Fundación es la que
verifica el ingreso (D1). `solicitud_confirmacion_inscripcion` traduce el
candidato a una solicitud del tipo `inscripcion` ya declarado —no es un
tipo nuevo— y tramita con la doble aprobación por pieza y la entrega sólo
contra el destino habilitado. La corrida no persiste estado de pagos (ADR
0003): una segunda corrida enumera el mismo candidato y el registro de
HU-012 devuelve `DUPLICADA`. Ambas piezas comparten las reglas del
circuito: sin las dos aprobaciones no hay entrega, la auditoría conserva
hashes y nunca medios de pago ni datos personales, y la plantilla queda
`PENDIENTE_SEU`.

```bash
uv run pytest -q tests/test_instrucciones_pago.py tests/test_matriz_hu012.py
```

## HU-014 — certificados offline

HU-014 renderiza determinísticamente el texto canónico de un certificado de
`ASISTENCIA` o `APROBACION` (catálogo cerrado en `certificado_emision_v2`) y
genera un PDF mínimo con stdlib, sin dependencias nuevas: estructura fija,
offsets de xref calculados y sin timestamps ni IDs, de modo que mismas líneas
producen los mismos bytes. Todo PDF previo a la aprobación completa lleva la
marca `BORRADOR — NO EMITIR`; el documento emitido (simulado) ya no la lleva.

El circuito de decisión es el de HU-012 reutilizado por importación: las dos
aprobaciones (semántica del RGC y utilitaria del Coordinador de Extensión) son
obligatorias en cualquier orden, el rechazo alcanza desde pendiente o parcial
y `EMITIDA_SIMULADA` sólo registra una emisión en memoria mediante
`DestinoCertificadosFake`. El registro durable es el mismo archivo-por-clave;
`reconciliar_emisiones_reservadas` cierra reservas colgadas en
`EMISION_INDETERMINADA` sin reemitir. La línea de auditoría agrega
`pdf_hash`: el rastro de cada certificado emitido, sin datos personales en
claro. El módulo no se reexporta desde `agente1`: se importa como
`agente1.certificados`.

### Línea descriptiva por actividad (#74)

El certificado sigue con la plantilla fija y suma **una línea descriptiva por
actividad** que redacta el modelo. Título, carga horaria y modalidad son
variables del registro que la plantilla interpola, nunca texto del modelo:
`linea_descriptiva.py` sólo le pasa al prompt `titulo`, `descripcion` y
`publico`, de modo que no pueda copiar un hecho que nunca vio. Los gates de
`validar_linea_descriptiva` rechazan de forma determinista: más de una línea,
extensión fuera de 20 a 200 caracteres, cualquier dígito, fechas en números o
en letras, duraciones (`horas`, `hs`), modalidad, lugares, organizadores,
importes, correos, URLs, actos institucionales, tuteo peninsular, eco de
instrucciones y repetición de las palabras distintivas del título. El mismo
gate se reejecuta en la entrada de `procesar_certificado`: la barrera no
confía en que el llamador haya pasado por la generación.

**Clave de decisión (contrato estable para #75).** La línea se aprueba **una
vez por actividad** por el Form de decisiones, igual que una plantilla:

- Tipo: `linea_descriptiva`.
- Objeto: `linea_descriptiva-<id_actividad>-<sha256 de la línea normalizada>`,
  derivado sólo con `objeto_id_linea_descriptiva`. La notación del ticket con
  `:` no entra en `ID_RE`; la forma con guiones codifica los mismos tres
  elementos. `id_actividad` admite hasta 45 caracteres para que el objeto
  complete entre en el identificador de 128.
- Decisiones: `apruebo_semantica` (rol `RESPONSABLE_GESTION_CONOCIMIENTO`) y
  `apruebo_utilitaria` (rol `COORDINADOR_EXTENSION`).
- `declarar_linea_pendiente(enlaces, id_actividad=..., linea=...)` abre el
  objeto y devuelve los dos links prellenados para el correo al par de roles.

Para emitir con línea, `procesar_certificado` exige además del circuito
normal dos argumentos que no son datos del documento sino contexto de
autorización: `decisiones` (el `RegistroDecisiones` compartido donde quedó la
auditoría del Form) y `lote_cierre` (el objeto del lote de cierre con
`apruebo_lote` registrada). Los códigos distinguen cada falta:
`decisions_registry_required`, `closing_batch_required`,
`descriptive_line_unapproved` (ausente o parcial: una sola de las dos no
habilita) y `closing_batch_unapproved`. La aprobación ata el texto exacto:
modificar la línea después de aprobarla produce otro objeto, sin decisiones.
La auditoría registra `descriptive_line_hash`, `linea_objeto_id` y
`closing_batch_id`, nunca el texto de la línea.

#75 consume esta clave con el mismo `RegistroDecisiones` y compone la
solicitud con `id_actividad`, `linea_descriptiva` y las variables del
registro (`modalidad`, `carga_horaria`): la lista de participantes y su
emisión en vivo son de ese ticket. El recorrido guiado del circuito está en
`evidencias/recorrido-linea-descriptiva-hu014.md`.

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu014.py --salida salida/matriz-hu014

PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_certificados.py \
    tests/test_certificados_durables.py tests/test_linea_descriptiva.py \
    tests/test_matriz_hu014.py
```

La plantilla institucional, la firma digital y el destino de emisión real
quedan `PENDIENTE_SEU`. Consultar `evidencias/limites-hu014-offline.md`; no
hay emisión institucional, validación SEU ni evidencia de TRL 3.

## HU-014 — emisión del lote con lista de cierre (#75)

`certificados_emision.py` corre la otra mitad de HU-014: la emisión del lote
completo de certificados de una actividad sobre su **lista de cierre** —la
Sheet D2 que carga quien gestiona el curso—, con el disparo en un pedido del
canal («emití los certificados de `<actividad>`», intención
`emitir_certificados` del catálogo `intenciones_v3`). No hay trigger por
cambio de estado: eso es HU-015 y queda fuera de alcance.

El circuito, en orden y todo fail-closed:

1. **La actividad da los datos institucionales** (título, carga horaria,
   modalidad, fechas, organización) desde `FuenteSolicitudes`; nada sale del
   texto del pedido ni de la lista.
2. **La lista se valida entera.** Seis columnas posicionales
   (`nombre,apellido,dni,mail,tratamiento,condicion`), `condicion` cerrada en
   `asistencia`/`aprobacion` sin inferencias, sin duplicados de DNI ni mail.
   Una fila mala bloquea el lote (`INVALIDA`), no salta.
3. **La línea descriptiva tiene que estar aprobada** por los dos roles sobre
   el objeto `linea_descriptiva:<id>:<hash>` (#74), por el mismo Form de
   decisiones de #72.
4. **El lote lo aprueba el rol utilitario** con `apruebo_lote` sobre
   `sha256("lote_cierre_certificados|<id>|<hash_lista>")`: cualquier edición
   de la lista cambia el objeto y la aprobación anterior no aplica. Quien
   cargó la lista no puede aprobarla. Mientras falta, el lote queda
   `PENDIENTE_APROBACION` y sale el correo al aprobador con el enlace al
   Form y un **PDF de muestra marcado `BORRADOR — NO EMITIR`** adjunto.
5. **La entrega es un correo por titular con el PDF adjunto** por
   `gmail.send` cercado por la lista de prueba (un destinatario fuera de
   ella rechaza antes del token y de la red, sin reintento). Resultados:
   `EMITIDA`, `EMITIDA_PARCIAL`, `FALLIDA`, `INVALIDA` o
   `PENDIENTE_APROBACION`.
6. **Marcas permanentes y retención mínima.** Todo PDF lleva
   `DOCUMENTO DE PRUEBA — SIN VALIDEZ` como primera línea mientras rija la
   lista sintética. La auditoría `emisiones-certificados-hu014.jsonl` guarda
   sólo hashes (solicitante, lista, titular, destinatario, PDF): ni la lista
   ni los PDFs se persisten. La reemisión es un pedido nuevo sobre la lista
   vigente.

El despacho se hace por un callable inyectado (`emisor_certificados`): sin
medio configurado el pedido termina `emisor_no_configurado`, nunca otra
intención. Los runners son `scripts/emitir_certificados.py` (disparo manual)
y el wiring de `scripts/atender_canal_form.py` (pedido del Form):

```bash
PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad SYN-001 --lista-csv lista.csv --linea linea.txt \
  --aprobador coord@example.invalid --solicitante aux@example.invalid \
  --directorio /tmp/demo-certificados
```

En offline la lista es un CSV, la línea un archivo externo y las entregas
quedan en `entregas-certificados-offline.jsonl` (del adjunto, sólo sha256).
En live hacen falta `--live --confirm-write-workspace` y el entorno:
`AGENTE1_CERTIFICADOS_LISTA_SHEET_ID`, `…_LISTA_RANGO_A1`, `…_LINEA_PATH`,
`…_APROBADOR`, `…_SOLICITANTE`, además de las variables Workspace, Form de
decisiones, padrón y lista de prueba de siempre. La receta completa —offline
y live— está en `evidencias/recorrido-emision-certificados-hu014.md`.

El ambiente D2 previsto para la corrida live es el del hilo de demostración
NotebookLM Nivel 2. No hay firma digital ni imágenes de firma en el repo
(`PENDIENTE_SEU`, carpeta D2 restringida cuando la SEU las entregue), ni
emisión sin las aprobaciones, ni destinatarios fuera de la lista de prueba.

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

## Corrida de insumos de agentes (pestaña «Insumos de agentes»)

La entrada push del ADR 0008: A3, A4 y A5 —o el productor provisional
declarado mientras esos agentes no existan— dejan una fila por insumo en la
pestaña `Insumos de agentes` de la planilla D2, y el Agente 1 la sondea con
una corrida manual (#82). Historia Viva (A2) no entrega insumos: se consulta
por el puerto pull de `historia_viva.py`, por eso `producer = "A2"` se
rechaza igual que cualquier productor desconocido.

La pestaña tiene cuatro columnas: `insumo` (el envelope
`agente1.insumo.v1` serializado en una línea), `cargado_por` (identificador
opaco de quién la cargó), `estado` y `detalle` (las dos que escribe la
corrida). Una fila con `estado` vacío está pendiente; cualquier valor
escrito la marca como ya procesada y no se toca. Por cada fila pendiente la
corrida valida el envelope, verifica `cargado_por` y despacha por
`payload.type`: hoy sólo `evento` de A3 tiene pipeline y va al flujo de
gacetilla HU-010 (#83), que produce un borrador `PENDIENTE_VALIDACION`
—nunca una publicación— cuyo enlace queda escrito en la fila. Un tipo
válido sin pipeline queda `aceptado sin flujo` con el tipo en `detalle`;
una fila inválida queda `rechazado` con el código del contrato. La pieza
nunca vuelve al productor: sólo el enlace o el código.

El `payload.content` del `evento` tiene contrato declarado propio
(`contracts/insumos/a3_evento_gacetilla_v1.schema.json`): los campos
admitidos son las columnas de la planilla de actividades menos
`id_actividad` (que la corrida deriva del `correlation_id`) y los
obligatorios son los que `gacetilla_input_v2` exige para una gacetilla,
menos ese identificador. Un campo desconocido, un valor no texto o un
obligatorio ausente rechazan la fila con código propio
(`evento_campos_desconocidos`, `evento_valor_invalido`,
`evento_campos_faltantes`) sin invocar al generador ni inventar el dato.
Cuando el pipeline corre, el borrador lleva una línea visible
`[Procedencia: insumo de A3, tipo evento; productor provisional: sí/no;
cargado_por: …; correlation_id: …]` entre la marca `BORRADOR — NO PUBLICAR`
y la pieza, y la línea de `logs/ejecuciones.jsonl` suma el bloque
`procedencia` con los mismos identificadores opacos. Una solicitud del
canal de la SEU no declara procedencia: el artefacto queda igual que
siempre. El procedimiento de la corrida live sobre D2 con un insumo real
de A3 («Ingeniería por un día 2026») quedó preparado en
`evidencias/runbook-corrida-insumos-a3-evento-hu010.md`, pendiente del
operador.

La idempotencia es por `correlation_id`: `insumos-procesados.jsonl`, en el
directorio de salida, registra cada despacho con metadatos (productor, tipo,
hash del payload, `cargado_por`), nunca el payload. Una corrida repetida —o
una segunda fila con el mismo `correlation_id`— reescribe el resultado ya
registrado sin redespachar; una reserva `inicio` sin `final` deja la fila
`bloqueada` para reconciliación manual en vez de reejecutar un efecto
desconocido.

Subcomando manual, offline por defecto sobre un CSV con la misma forma que
la pestaña:

```bash
PYTHONPATH=src python -m agente1 insumos-agentes \
  --tabla insumos.csv --directorio salida/insumos --fake-output "salida"
```

El modo en vivo exige `--live` **y** `--confirm-write-workspace` juntos, un
modelo de Ollama y la configuración del entorno: las `AGENTE1_WORKSPACE_*`
de siempre más `AGENTE1_INSUMOS_RANGO_A1` con el rango `'Nombre'!A1:D<n>` de
la pestaña. La escritura va por `GoogleSheetsEscritorEstadoInsumos`, el
primer write a Sheets del repo: un único `values.update` por fila sobre
`C{n}:D{n}`, `valueInputOption=RAW`, token por operación y la allowlist de
planilla+pestaña fijada al construir. Correrla sobre D2 es tarea del
operador.

El envelope lo valida `insumos_agentes.py` contra
`contracts/insumos/agente1_insumo_candidate_v2.schema.json`
(`CANDIDATO_NO_INSTITUCIONAL`; el v1 queda histórico). A1 acepta o rechaza
datos no confiables de A3–A5: **no los invoca, coordina ni orquesta**, no
interpreta `payload.content` como control —un texto tipo «publicá ya» es
dato del borrador, nunca una instrucción— y no publica contenido. Cambios
del v1: A2 sale del envelope por el ADR 0008 y `data_origin` suma
`provisional_producer` para las filas del productor provisional.

Pruebas focalizadas:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python -m pytest -q tests/test_insumos_agentes.py \
    tests/test_insumos_corrida.py tests/test_insumos_sheets.py \
    tests/test_cli_insumos.py
```

## Scheduler local de corridas programadas (#84)

El subcomando `agente1 scheduler` dispara la corrida de insumos cada pocos
minutos en el host de la demo, para que el agente reaccione cuando un
productor carga una fila sin esperar una corrida manual. El disparo
automático **sólo produce borradores `PENDIENTE_VALIDACION`**: no publica,
no envía, y la validación humana queda intacta; la corrida manual sigue
disponible como contingencia.

Mismo proceso, mismos flags que `insumos-agentes` (la composición la
comparte `corrida_desde_args` de `cli_insumos`): offline exige `--tabla` y
un generador, live exige `--live` + `--confirm-write-workspace` + modelo
Ollama. Lo que agrega es la agenda, configurable por entorno con
`AGENTE1_SCHEDULER_*`: intervalo (`INTERVALO_S`, default 300 s), ventana
de operación (`VENTANA_DIAS`, `VENTANA_DESDE`/`HASTA` en `TZ`, default
días hábiles 8 a 16, **provisional** a confirmar por la SEU en #56), path
del repo (`REPO`) y el registro de confirmaciones que la purga diaria
procesa (`REGISTRO_CONFIRMACIONES`).

Los ticks son `desde + k * intervalo` dentro de la ventana. Cada disparo
responde al tick más reciente (`inicio_previsto`), así un disparo atrasado
deja el atraso a la vista. Dos mecanismos, a elegir uno por host:

- **Timer `systemd --user`** (natural en la demo): las plantillas de
  `systemd/` (`agente1-scheduler.timer` + `.service` oneshot que corre
  `--una-corrida`) se copian a `~/.config/systemd/user/` y se habilitan
  con `systemctl --user` por el operador designado; el repo no instala ni
  activa unidades.
- **Bucle con `sleep`** (`--loop`): un proceso único que espera al próximo
  tick y corre; sirve de alternativa y de ensayo (`--max-disparos`).

Solapamiento cubierto en tres capas: `flock` no bloqueante sobre
`scheduler-corrida.lock` (un disparo concurrente queda `omitida_lock`),
deduplicación por tick ya `completada` (`omitida_duplicada`) y la
idempotencia por `correlation_id` de la corrida como red de seguridad.
Fuera de la ventana el disparo queda `omitida_ventana` sin tocar nada.

Cada disparo deja una línea en `logs/scheduler-corridas.jsonl` (formato
versionado `scheduler_corrida_v1`): `inicio_previsto`, `inicio_real`,
`fin`, `resultado` y conteos cerrados de la corrida, más el bloque
`mantenimiento` cuando corre el slot diario. Nunca lleva payload ni
contenido: es la fuente que #88 usa para medir disponibilidad.

El slot diario de la primera corrida en ventana corre la **purga** de
datos personales (#87) como subproceso de `scripts/purgar_registro.py` y
el **respaldo** diario del estado (#86) como subproceso de
`scripts/respaldar_estado.py`, en ese orden y encadenados: si la purga
del día falla el respaldo también falla. Una vez por día cada uno, con
reintento en el tick siguiente si fallan y sin detener la corrida. El
respaldo existe cuando el entorno declara una carpeta
(`AGENTE1_RESPALDO_CARPETA_FAKE` offline o `AGENTE1_RESPALDO_CARPETA_ID`
+ `CONFIRMAR_ESCRITURA=SI` + `AVISO_DESTINATARIO` live); sin carpeta
declarada se asienta `pendiente`. La sección del respaldo en este README
y el runbook cubren formato, modos y restauración.

Manual completo de instalación, parada, diagnóstico y migración de host en
`Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md` (ADR 0007). El
esquema del log también está ahí.

```bash
# Ensayo offline de un disparo (sin instalar unidades)
PYTHONPATH=src python -m agente1 scheduler --una-corrida \
  --ahora 2026-10-05T10:00:00-03:00 \
  --tabla insumos.csv --directorio salida/insumos --fake-output "salida"

# Bucle acotado para ensayos
PYTHONPATH=src python -m agente1 scheduler --loop --max-disparos 2 \
  --tabla insumos.csv --directorio salida/insumos --fake-output "salida"

uv run pytest -q tests/test_scheduler.py tests/test_cli_scheduler.py
```

## Manifest de versión e integridad al arrancar (#92)

Una versión del agente lleva un **manifest** con el sha256 de todo lo
controlado que vive en el repo: código, prompts, políticas y contratos bajo
`src/`, `migrations/`, `uv.lock`, `pyproject.toml`, `scripts/` operativos y
`systemd/` (ADR 0010). El manifest viaja con la versión en
`manifest-version.json`, en la raíz del Agente 1 **fuera** de las rutas que
recorre, así que no se controla a sí mismo. La versión sale de
`pyproject.toml` (`[project].version`).

Se genera al cortar una versión, después de cualquier cambio bajo las rutas
controladas:

```bash
uv run python scripts/manifest_version.py --salida manifest-version.json
```

Es determinista: el mismo árbol produce el mismo archivo byte a byte, sin
timestamps volátiles y con orden estable.

En **modo operación** —las corridas con `--live`, que es como las unidades
`systemd/` invocan el scheduler— la corrida compara el manifest con el árbol
del host antes de pedir credenciales y de tocar la red. Si un archivo falta,
sobra o no coincide, o si el manifest está ausente o es inválido, **no
arranca** (código de salida 2, `{"estado": "INVALIDA", "error": ...}`) y deja
el archivo, el hash esperado y el encontrado en
`logs/integridad-arranque.jsonl` (formato `agente1_integridad_arranque_v1`).
Las corridas offline (`--tabla`), la CLI local y la suite **no verifican**: el
manifest se regenera al cortar una versión, no en cada cambio.

`scripts/manifest_corte.py` dejó de mantener su lista `FUENTES` congelada en
`gacetilla_v3`: cada manifest de corte referencia `version` y
`manifest_version_sha256`, y sólo suma lo propio del corte (la configuración
del adapter y la referencia Git).

```bash
uv run pytest -q tests/test_manifest_version.py tests/test_integridad_arranque.py
```

Paso en vivo para el laboratorio y la mesa —editar un prompt en el host → no
arranca → la auditoría muestra los dos hashes → restaurar → arranca— en
`evidencias/integridad-arranque-2026-10-14.md`.

## Nivel verificado de los SLO desde la auditoría (#88)

`scripts/medir_nivel_slo.py` calcula los cinco indicadores de la resolución
de SLO/SLA (#65) sobre los registros que la operación ya deja bajo un
directorio de salida, sin tocar la red ni escribir en las fuentes, y
publica el reporte `nivel_verificado_slo_v1`: disponibilidad (agenda vs.
corridas del scheduler), tiempo de atención (Form de pedido → aviso),
latencia por pieza (p95 de `latencia_s` por tipo), aprobación → envío
(doble aprobación → entrega, dentro de la ventana) e integridad del gate
(toda pieza en validación humana con gate aprobado).

La agenda y la ventana se leen de `AGENTE1_SCHEDULER_*` con
`cargar_configuracion_scheduler`, igual que el scheduler: el denominador
de disponibilidad son los ticks que la agenda ya debió disparar al
instante de corte, no las líneas del log. El intervalo de sondeo efectivo
y la ventana viajan declarados en la evidencia.

Nada se inventa: un indicador con `n < --muestra-minima` (default 20)
declara `muestra insuficiente (n=...)`; una fuente ausente o ilegible
declara `sin_fuente` con el hueco explícito; el objetivo de latencia se
declara `pendiente #50/#51` hasta que #50 fije el número sobre el modelo
de #51. Dos huecos conocidos que la evidencia reporta: la marca temporal
del Form de pedido sólo entra hasheada a la auditoría (el indicador de
tiempo de atención pide el CSV de respuestas exportado a la fecha de
corte por `--respuestas-csv`, o declara `sin_fuente`) y las aprobaciones
de los circuitos que no pasan por el Form de decisiones quedan como hash,
así que su ancla no se reconstruye.

```bash
PYTHONPATH=src python scripts/medir_nivel_slo.py \
  --directorio salida/insumos-d2 \
  --desde 2026-10-12 --hasta 2026-10-16 \
  --respuestas-csv respuestas-form.csv \
  --md evidencias/nivel-verificado-slo-2026-10-16.md
```

El JSON por stdout es el reporte completo (indicador por indicador:
`n`, nivel medido o declaración, objetivo, detalle y huecos); `--md`
emite el corte en markdown listo para versionar en `evidencias/` con el
comando exacto que lo produjo. La primera evidencia medida es
`evidencias/nivel-verificado-slo-2026-10-12.md`, producida sobre la
corrida sintética offline de `salida/slo-demo-2026-10-12` (backend fake,
sin red): sirve para verificar el instrumento end-to-end —agenda,
cruces por hash, ventana operativa y declaraciones— no para afirmar un
nivel operativo.

Es la evidencia que las celdas con SLO del perfil de calidad (#89)
citan como nivel verificado cuando se proyecta el Anexo 2 con
`scripts/anexo2_calidad.py`: mientras una celda diga `pendiente` o
`muestra insuficiente`, la proyección lo declara y el nivel no se
publica como cumplido.

```bash
uv run pytest -q tests/test_medicion_slo.py
```

## Seam de consulta a Historia Viva

`historia_viva.py` prepara el lado de A1 para consultar el acervo histórico
validado del Agente 2. Es un puerto único con tres operaciones —buscar
fragmentos, ampliar una pieza y registrar un aporte— y **A1 siempre inicia**:
no hay callback, webhook ni cola entrante, y una prueba verifica que esa
superficie no aparezca. Va en dirección contraria al envelope push de
`insumos_agentes.py`, que la corrida de insumos ya consume para A3–A5: A2
quedó fuera de ese contrato justamente porque su camino es esta consulta.

Dos controles sostienen el alcance:

- **La precisión de fecha no es un metadato, es un control.**
  `RangoHistorico.expresion_temporal` es la única forma de obtener una fecha
  para redactar, y devuelve sólo lo que la precisión declarada sostiene: una
  pieza con precisión de mes se nombra «agosto de 1926», nunca «7 de agosto de
  1926». No existe un atributo de fecha suelto que se pueda formatear por
  afuera.
- **Historia Viva no redacta, y A1 no inventa.** El acervo devuelve fragmentos
  citables; la efeméride la compone A1 con `componer_material_efemeride`, a
  partir de una búsqueda por período. Con material vacío,
  `MaterialEfemeride.afirmaciones` devuelve una tupla vacía: quien redacte no
  tiene un hueco para rellenar, tiene ausencia de material.

Los aportes conservan procedencia (`piezas_fuente`), exigen clave de
idempotencia —un POST reintentado a ciegas duplica el aporte— y sólo pueden
nacer `PENDIENTE_VALIDACION`: no existe forma de declarar uno validado ni
publicado.

`HistoriaVivaFake` implementa el puerto en memoria, sin red ni credenciales, y
permite forzar la falla de una operación por separado.

`historia_viva_cliente.py` es la capa cliente de ese seam: `ClienteHistoriaViva`
implementa el puerto sobre un `TransporteHistoriaViva` inyectado que devuelve
cuerpos crudos, y valida cada respuesta contra el contrato `/v1` de Historia
Viva (`openapi-agentes.yaml` 1.1.0-rc1, borrador hasta el congelado del
30/10), espejado en `contracts/historia_viva_v1.schema.json`. Lo que el
contrato no contempla se rechaza con `historia_viva_response_invalid`; lo que
falta no se inventa. El timeout y los reintentos son objetos de configuración
(`PoliticaCliente`): las consultas reintentan ante `429`/`503` esperando el
`Retry-After` (hasta `espera_maxima_segundos`) y `POST /v1/aportes` no
reintenta por default. Para uso programático, importar desde
`agente1.historia_viva_cliente`; no se reexporta en `agente1`.

`historia_viva_http.py` es el transporte HTTP (`TransporteHistoriaVivaHttp`,
issue #12): manda solo los parámetros del contrato, decide por `codigo` con
default por familia (todo `4xx` es definitivo), lee el token en cada pedido
para poder rotarlo sin reiniciar y nunca deja salir el `mensaje` remoto.

Pruebas focalizadas:

```bash
uv run pytest -q tests/test_historia_viva.py tests/test_cliente_historia_viva.py tests/test_historia_viva_http.py
```

Prueba de contrato contra el mock Prism de Historia Viva (paquete
`contratojuan`, clonado al lado del repo): `node ejecutar-contrato.mjs` levanta
el mock, exporta `HV_BASE_URL` y `HV_TOKEN` y corre `contrato/` con la línea de
`cliente.comando`. Sin `HV_BASE_URL` la prueba se saltea; los casos pendientes
de C48 se excluyen con `-m "not c48"`.

Los límites del slice están declarados en
`evidencias/limites-historia-viva-cliente.md`.

## Post de efeméride desde Historia Viva (#85)

`posts_efemeride.py` produce el borrador HU-011 de una efeméride con material
del acervo de A2: `procesar_post_efemeride` consulta el puerto `HistoriaViva`
—el fake en pruebas y recorridos, o `ClienteHistoriaViva` cuando tenga
transporte—, compone el material con `componer_material_efemeride` y genera el
post por el mismo carril estructurado de `posts.py`. El contrato creativo
`post_creative_efemeride_v1` y los prompts `post_*_efemeride_v1` siguen
`PROVISIONAL_NO_INSTITUCIONAL`; el contrato de consulta a A2 sigue
`CANDIDATO_NO_INSTITUCIONAL` (issue #17).

La pieza queda `PENDIENTE_VALIDACION` con `BORRADOR — NO PUBLICAR`: el modelo
sólo redacta la envoltura creativa y el renderer intercala cada fragmento
literalmente, con su cita `pieza / fragmento (expresión temporal)` —una pieza
con precisión de mes se cita como «agosto de 1926», nunca como día exacto—.
Una consulta sin material termina `INCOMPLETA` sin invocar al generador, y la
procedencia declarada (`insumo_a2` o `synthetic_test`) viaja a la auditoría
como `data_origin` y al borrador como línea `_Procedencia:_`. Los errores de
configuración —una política incompatible con la allowlist o un contrato
creativo que no sea de la familia `post_creative_efemeride`— terminan
`INVALIDA` antes de tocar el puerto. La publicación pasa por la misma decisión
`publique`/`descarte` del Form de #72: el objeto es el id del borrador,
`efemeride-<período>-<hash>-<canal>`.

No hay transporte: el adapter HTTP de Historia Viva queda pendiente del
contrato con A2 (#17, bloqueado por #12) y ninguna prueba toca la red. La
efeméride tampoco se dispara desde el canal: el catálogo `intenciones_v3` no
tiene una intención de efeméride —resolver una fecha desde prosa es un cambio
de contrato aparte— y el disparo es un pedido del operador, no un scheduler.

Prueba focalizada y recorrido offline:

```bash
uv run pytest -q tests/test_posts_efemeride.py

uv run python scripts/post_efemeride_demo.py \
  --directorio salida/post-efemeride-demo
```

Los límites del recorrido están declarados en
`evidencias/recorrido-post-efemeride-hu011.md`.

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

El incremento quedó versionado en `db06b3e`. En el corte vigente del
2026-09-08 (`a2c33b1`) la suite completa se ejecutó con `uv run pytest -q`:
534 pruebas, todas en verde. El corte del 2026-09-06 había dado 513; la
diferencia son las regresiones de `DEF-A1-013` y `DEF-A1-014`. `pytest` y `setuptools` también están declarados en el grupo de
dependencias de desarrollo para que un checkout limpio pueda reproducirla.

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
HU-010, HU-011, HU-012 y HU-014 continúan parciales y el Gate G2 / TRL 3
permanece pendiente.
