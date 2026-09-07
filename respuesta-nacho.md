# Respuesta al contrato Historia Viva ↔ Agente 1

De: Juan Goñe (Agente 1)
Fecha: 31 de agosto de 2026

## Veredicto general

Esta es la posición unilateral de Juan, no un contrato acordado. La propuesta sirve con cambios acotados de trazabilidad e idempotencia. Se acepta que el Agente 1 consulte por HTTP y reciba exclusivamente material validado; del lado de A1 hay que reemplazar el contrato candidato que hoy supone insumos enviados por A2 y admite una `efemeride` ya elaborada.

## Efemérides

El diseño de A1 sí contempla gacetillas de efemérides, posts alusivos y comunicados de fechas fijas, y el contrato candidato actual admite un payload A2 de tipo `efemeride` (`Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`, línea 1013; `Agentes/extension_bot_experto.md`, sección “Funciones core”; `Implementacion/Agente1/src/agente1/contracts/insumos/agente1_insumo_candidate_v1.schema.json`). No hay, sin embargo, un flujo implementado que invoque a Historia Viva ni código que dependa de un endpoint “efeméride del día”: el validador A2 existente no está conectado a HU-010/HU-011 y está marcado `CANDIDATO_NO_INSTITUCIONAL` (`Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`, secciones 1 y 6).

La búsqueda por período alcanza para conservar la funcionalidad: A1 consultará `desde`/`hasta`, recibirá fragmentos validados con fecha y cita, y redactará su propia efeméride. Debe contemplar `precision_fecha` y no presentar como fecha exacta una pieza cuya precisión sea `mes`, `anio` o `decada`. Este cambio queda del lado de A1 y elimina `efemeride` como producto esperado de A2.

## Lo que se acepta como está

- HTTP/REST sobre JSON UTF-8, versionado bajo `/v1`.
- A1 inicia todas las llamadas; Historia Viva no necesita callbacks ni webhooks.
- `Authorization: Bearer <token>`, un token revocable por agente, secreto fuera de los repositorios, y distinción `401`/`403`. Es consistente con la política de identidad por agente, scopes mínimos y secretos no versionados (`Documentos/PlanIntegracion/Plan-Integracion-Agente-1-PPS-Juan-Ignacio-Gone.md`, sección 11).
- A1 accede exclusivamente a piezas validadas y una pieza inexistente o no validada responde `404` sin revelar cuál de los dos casos ocurrió.
- Historia Viva devuelve fragmentos y citas, no prosa redactada; A1 conserva la responsabilidad de generar la pieza comunicacional y de someterla a validación humana (`Agentes/extension_bot_experto.md`, CU03–CU05 y DoD de generación de contenido).
- `GET /v1/fragmentos` con consulta semántica, filtros de período y tipo, límite 10/tope 50, y resultado vacío como `200`.
- Fechas históricas como rangos con precisión explícita.
- `GET /v1/piezas/{pieza_id}` para ampliar una recuperación insuficiente.
- Todo aporte de A1 entra pendiente de validación humana y no se indexa por el solo hecho de haber sido recibido. Es consistente con el estado `PENDIENTE_VALIDACION` de toda salida exitosa de A1 (`Implementacion/Agente1/src/agente1/procesamiento.py`, docstring de módulo y `procesar_solicitud`).
- Historia Viva no sirve binarios: A1 puede usar la URL de Drive cuando exista acceso institucional.
- Sin caché de Historia Viva en esta entrega y objetivo de respuesta menor a 15 segundos.
- Códigos `400`, `401`, `403`, `404`, `429` y `503`, y ausencia de reintentos o colas del lado de Historia Viva.

## Lo que hay que cambiar

- Agregar un `fragmento_id` estable a cada elemento de `fragmentos` y, cuando corresponda, una ubicación dentro de la pieza (`pagina`, `seccion` o equivalente). `pieza_id` y `url_original` identifican el documento, pero no el pasaje exacto que fundamenta una afirmación. A1 exige fuente verificable, metadatos y evidencia recuperable para los insumos A2 (`Documentos/PlanIntegracion/Plan-Integracion-Agente-1-PPS-Juan-Ignacio-Gone.md`, secciones 7, 8 y 10).
- Especificar en OpenAPI la forma completa y cerrada de la respuesta de `GET /v1/piezas/{pieza_id}`. “Todos sus campos” no permite generar cliente, mock ni pruebas de contrato. A1 planifica contratos y mocks antes de la integración real (`Documentos/Gantt/diagrama-gantt-implementacion-semanal.mmd`, líneas 59–63).
- Agregar idempotencia a `POST /v1/aportes`, preferentemente mediante `Idempotency-Key`, y definir la respuesta repetida. Los adapters de A1 evitan reintentos ciegos porque una operación remota puede completarse aunque la respuesta se pierda; sin idempotencia, un retry puede duplicar el aporte (`Implementacion/Agente1/src/agente1/workspace_e2e.py`, docstring de módulo y `_DestinoIdempotente`).
- Agregar `tipo_contenido` y `canal` al aporte, o documentarlos como campos opcionales equivalentes. A1 genera al menos gacetillas y posts diferenciados para Instagram y LinkedIn; `titulo` y `cuerpo` no conservan esa clasificación (`Implementacion/Agente1/README.md`, secciones HU-010 y HU-011; `Implementacion/Agente1/src/agente1/posts.py`).
- Permitir registrar el aporte después de la aprobación aunque todavía no exista publicación externa: hacer `fecha_publicacion` y `url_publicacion` opcionales, o separar “aporte aprobado” de “aporte publicado”. El MVP actual sólo produce borradores y no publica ni conoce una URL final (`Implementacion/Agente1/README.md`, primer apartado y sección HU-011; `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`, líneas 215–223 y 277–284).
- Del lado de A1, reemplazar el envelope push `a1.communication_input` y los tipos A2 `dato_historico`/`efemeride` por un cliente pull para los tres endpoints acordados. El artefacto actual declara expresamente que es candidato, offline y no integrado (`Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`; `Implementacion/Agente1/src/agente1/insumos_agentes.py`).

## Respuestas

1. **Efemérides.** A1 contempla esa clase de contenido, pero no hay implementación que dependa de recibir una efeméride redactada. La búsqueda por período alcanza y A1 debe componerla respetando `precision_fecha`. Hay que retirar la expectativa `efemeride` del contrato candidato de A1 (`Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`, línea 1013; `Implementacion/Agente1/src/agente1/contracts/insumos/agente1_insumo_candidate_v1.schema.json`; `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`, sección 6).

2. **La consulta real.** Hoy la generación implementada se dispara por una solicitud de actividad identificada por `id_solicitud`, leída desde CSV o Google Sheets. Para gacetillas y posts exige `titulo`, `descripcion`, `fecha`, `publico`, `organiza`, `contacto` y `fuente`; `lugar` es opcional (`Implementacion/Agente1/src/agente1/contracts/gacetilla_input_v1.schema.json`; `Implementacion/Agente1/src/agente1/contracts/post_input_v1.schema.json`; `Implementacion/Agente1/README.md`, secciones “Adapter contractual de Google Sheets” y HU-011). Todavía no existe una traducción implementada desde esos datos hacia una consulta A2. La regla propuesta es: para una pieza histórica o alusiva, A1 consulta por combinación de período y tema (`desde`/`hasta` + `q`), agregando `tipo` sólo cuando la solicitud o plantilla lo determine. Para efemérides puras usa el período; no debe inventarse un tipo de pieza.

3. **Los campos del fragmento.** `texto`, rango de fechas, `precision_fecha`, `tipo`, `resumen_pieza`, `pieza_id`, `url_original` y `validada_el` alcanzan para redactar y citar a nivel de pieza. Falta `fragmento_id` y, si existe, ubicación interna para trazabilidad fina. Ningún campo propuesto sobra. Los campos operativos de la comunicación (`publico`, `organiza`, `contacto`, canal) seguirán viniendo del trigger de A1, no de Historia Viva (`Implementacion/Agente1/src/agente1/contracts/gacetilla_input_v1.schema.json`; `Implementacion/Agente1/src/agente1/contracts/post_input_v1.schema.json`; `Documentos/PlanIntegracion/Plan-Integracion-Agente-1-PPS-Juan-Ignacio-Gone.md`, secciones 7–10).

4. **Imágenes.** A1 puede necesitar una imagen para un post, pero el código actual sólo genera texto y borradores; no hay pipeline de descarga o publicación de imágenes (`Implementacion/Agente1/README.md`, alcance HU-011; `Implementacion/Agente1/src/agente1/posts.py`). La URL de Drive es suficiente como contrato si A1 recibe permisos. El repo contiene adapters HTTP de Drive probados offline, pero declara que no existen todavía OAuth, credenciales, IDs ni permisos institucionales para una ejecución live (`Implementacion/Agente1/README.md`, secciones “Adapter contractual de Google Sheets” y “Preparación Workspace D2 y seguridad offline”). Por ahora, A1 no tiene credenciales institucionales de Drive confirmadas.

5. **Volumen y latencia.** La referencia disponible es de aproximadamente 12 publicaciones mensuales; el benchmark modeló 36 generaciones por mes, no consultas a Historia Viva (`Implementacion/Agente1/evidencias/benchmark-capacidad-a1-2026-08-26.md`, secciones 1 y 4). El número de consultas A2 por día no está definido. Una respuesta de hasta 15 segundos es tolerable para la generación de borradores: el propio LLM local tiene medianas aproximadas de 15,6 a 24,4 segundos por pieza y el objetivo general de A1 es menor a 30 segundos (`Implementacion/Agente1/evidencias/benchmark-capacidad-a1-2026-08-26.md`, sección 3; `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`, línea 630). Conviene que el timeout A1 para Historia Viva sea mayor a 15 segundos y separado del presupuesto del LLM.

6. **El aporte.** `titulo`, `cuerpo` y `piezas_fuente` cubren el texto y la procedencia básica; A1 puede conservar los `pieza_id` devueltos por la búsqueda, aunque esa vinculación todavía no está implementada. Faltan `tipo_contenido` y `canal`. A1 hoy no sabe si se publicó ni dónde: produce `PENDIENTE_VALIDACION`, no llama APIs de redes y no obtiene `fecha_publicacion` o `url_publicacion` (`Implementacion/Agente1/README.md`, primer apartado y HU-011; `Implementacion/Agente1/src/agente1/procesamiento.py`). Por eso esos dos campos deben ser opcionales o el POST debe ejecutarse desde una etapa posterior de publicación que aún no existe.

7. **Fallas.** La conducta vigente es fail-closed: una fuente fallida, timeout, respuesta inválida o generación no conforme deja el proceso `FALLIDA` y no crea borrador; una entrada incompleta queda `INCOMPLETA` (`Implementacion/Agente1/README.md`, alcance y ejecución; `Implementacion/Agente1/src/agente1/procesamiento.py`, `procesar_solicitud` y `_resultado_fuente_fallida`). Ante Historia Viva caída o lenta, A1 no publica y registra/avisa la falla para revisión. Ante resultado vacío, no atribuye hechos históricos ni publica una efeméride como si estuviera documentada; puede continuar sin componente histórico sólo si la solicitud original permite una pieza autónoma y queda igualmente sujeta a validación humana. No se hará retry ciego de `POST /aportes`; para habilitarlo hace falta idempotencia. La cantidad y backoff de reintentos GET no están definidos en el repo.

8. **Fechas.** El cronograma semanal reserva el 26–30 de octubre de 2026 para contratos/mocks A2–A5, el 30 de octubre–6 de noviembre para integración progresiva y el 2–10 de noviembre para pruebas (`Documentos/Gantt/diagrama-gantt-implementacion-semanal.mmd`, líneas 59–63). Por lo tanto, A1 necesita un endpoint o mock contractual estable el **30 de octubre de 2026** y planifica tener su lado listo para comenzar pruebas contra Historia Viva el **2 de noviembre de 2026**. Son fechas del plan vigente de Juan, no constancia de disponibilidad comprometida por Ignacio.

9. **El OpenAPI.** De acuerdo con que el OpenAPI 3.1 viva en el repositorio de Ignacio como fuente única. A1 consumirá una versión fijada por tag o commit y mantendrá sólo mocks/fixtures de prueba derivados; no hay en este repo un repositorio compartido definido que justifique abrir otro (`Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`, secciones 5–7).

10. **Cualquier cosa del repositorio que rompa esta propuesta.** No hay transporte, autenticación ni cliente HTTP A2 implementados que la bloqueen. Sí contradicen la dirección y la semántica definitivas el envelope candidato inbound `a1.communication_input` y el tipo `efemeride`; deben reemplazarse del lado de A1 (`Implementacion/Agente1/src/agente1/insumos_agentes.py`; `Implementacion/Agente1/src/agente1/contracts/insumos/agente1_insumo_candidate_v1.schema.json`). FastAPI, Celery y Redis están diferidos y el MVP no tiene scheduler operativo para este intercambio, por lo que el cliente y su scheduling todavía deben construirse (`.claude/persistence.md`; `Implementacion/Agente1/README.md`). Además, el POST necesita idempotencia y no puede exigir datos de publicación que A1 aún no produce.

## Fechas

| Qué | Cuándo |
| --- | ------ |
| Endpoint de Historia Viva funcionando | 30 de octubre de 2026 |
| Agente 1 listo para probar contra él | 2 de noviembre de 2026 |

## Lo que no pude responder

- El límite de consultas por token: el repo informa unas 12 publicaciones mensuales, pero no define cuántas búsquedas, ampliaciones de pieza o reintentos requiere cada una. Hace falta acordar el flujo editorial y medirlo en la prueba de integración.
- La política exacta de timeout, cantidad de reintentos y backoff del cliente GET de A1: no existe todavía ese cliente. Hace falta definirla junto con el SLA operativo y probar `429`/`503`.
- Las credenciales y permisos institucionales de Drive: el repo confirma que no fueron provistos ni probados live. Hace falta que DSI/SEU entregue una identidad autorizada y defina el alcance de lectura.
- El momento institucional exacto en que A1 debe registrar un aporte —aprobación, programación o publicación— y quién dispara esa llamada. Hace falta cerrar el flujo de validación/publicación con la SEU.
- Los valores permitidos de `tipo` de pieza y de `tipo_contenido`/`canal`: hacen falta enums versionados en el OpenAPI y validación conjunta.
- Las fechas indicadas son las del cronograma de Juan, pero el repositorio no registra un compromiso coordinado con Ignacio. Hace falta confirmarlas entre ambos responsables.
