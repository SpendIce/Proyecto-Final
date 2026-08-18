# Matriz BPM–HU–DoD–TRL–evidencia–responsable — MVP Agente 1

- **Fecha de corte:** 17 de agosto de 2026
- **Proceso BPM:** P4 — Comunicación y Difusión Institucional
- **TRL objetivo:** 3 — prueba de concepto en entorno controlado

## 1. Convenciones

- `CUMPLE_TECNICO`: existe evidencia controlada suficiente para ese criterio técnico.
- `PARCIAL`: existe parte de la evidencia, pero no completa el criterio.
- `IMPLEMENTADA_OFFLINE`: incremento versionado y verificado sin servicios institucionales live.
- `PENDIENTE_EXTERNO`: depende de SEU, DSI o Dirección.
- `NO_CUMPLE`: no existe todavía la evidencia exigida.

La conformidad técnica no sustituye validación humana ni aceptación institucional.

## 2. Matriz de HU-010

| BPM | HU | Criterio DoD / aceptación | TRL | Evidencia actual | Responsable de ejecución | Responsable de aceptación | Estado |
|---|---|---|---:|---|---|---|---|
| P4 | HU-010 | Leer entrada estructurada y rechazar datos incompletos sin inventar | 3 | Contrato `gacetilla_input_v1`; matriz de cinco casos en `b528efe` | Juan Ignacio Gone | Responsable Gestión del Conocimiento / SEU | `CUMPLE_TECNICO` con datos simulados |
| P4 | HU-010 | Generar borrador local, limpio, trazable y no publicable | 3 | Commits `809ee24`, `e0510b8`, `3de9a9c`; manifest `SYN-001` | Juan Ignacio Gone | Responsable Gestión del Conocimiento / SEU | `PARCIAL`: gate mecánico sí; calidad SEU no |
| P4 | HU-010 | Input desde Google Sheets | 3 | Adapter/config versionados; runner E2E candidato verificado offline | Juan Ignacio Gone + Vera/DSI | Vera/DSI + SEU | `PARCIAL`: preparación offline; falta OAuth y ejecución live |
| P4 | HU-010 | Output en Google Docs | 3 | Adapter y operaciones Drive offline; runner E2E candidato copia plantilla y actualiza Docs con fakes | Juan Ignacio Gone + Vera/DSI | Vera/DSI + SEU | `PARCIAL`: falta ejecución live |
| P4 | HU-010 | Aplicar plantilla institucional y carpeta aprobada | 3 | Copia de plantilla y ubicación en carpeta probadas offline en `5484684` | Josefina/SEU provee; Juan Ignacio integra; DSI provisiona | Josefina Carullo / SEU | `PARCIAL`: recursos institucionales y prueba live pendientes |
| P4 | HU-010 | Logs, correlation ID, hashes y versiones recuperables | 3 | Manifest y matriz HU-010; logging del pipeline | Juan Ignacio Gone | Director / auditoría interna | `CUMPLE_TECNICO` para slice local |
| P4 | HU-010 | Tiempo de ejecución aceptable | 3 | Green warm 20,172128 s; prompt-cold timeout hasta 45 s | Juan Ignacio Gone + DSI | César / SEU según umbral acordado | `PARCIAL` |
| P4 | HU-010 | Validación humana registrada, sin alucinaciones y tono institucional | 3 | Paquete `1264d59` incluye nueve muestras y 17 referencias; acta `PENDIENTE` | Validadores SEU | Josefina/SEU; Director para gate | `PENDIENTE_EXTERNO` |

**Estado agregado HU-010:** `PARCIAL`. La historia no cumple todavía su DoD institucional.

## 3. Matriz de HU-011

| BPM | HU | Criterio DoD / aceptación | TRL | Evidencia actual al corte | Responsable de ejecución | Responsable de aceptación | Estado |
|---|---|---|---:|---|---|---|---|
| P4 | HU-011 | Formato adaptable para Instagram y LinkedIn | 3 | Contrato y políticas por canal en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE`; política institucional pendiente |
| P4 | HU-011 | Texto limpio y coherente, preservando hechos fuente | 3 | V4 candidata combina JSON Schema compatible y renderer determinista: 6/6 aceptadas técnicas | Juan Ignacio Gone | Responsable RRSS / SEU | `PARCIAL`: técnica sí; calidad SEU no |
| P4 | HU-011 | Longitud configurable por canal | 3 | Políticas y pruebas versionadas en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE` con límites provisionales |
| P4 | HU-011 | Hashtags con formato y deduplicación controlados | 3 | Gate y pruebas versionados en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE`; criterio SEU definitivo pendiente |
| P4 | HU-011 | Casos completos e incompletos, sin invocar LLM ante datos inválidos | 3 | Matriz de diez ejecuciones: seis borradores y cuatro incompletas | Juan Ignacio Gone | Director / SEU | `CUMPLE_TECNICO` con fake y datos simulados |
| P4 | HU-011 | Logs, correlation ID, hashes y versiones | 3 | Matriz HU-011 registra trazabilidad segura por ejecución | Juan Ignacio Gone | Director / auditoría interna | `CUMPLE_TECNICO` para slice offline |
| P4 | HU-011 | Borrador por canal; nunca publicación automática | 3 | Smoke fake y goldens conservan `BORRADOR — NO PUBLICAR`; no hay APIs RRSS | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE` |
| P4 | HU-011 | Generación con LLM local bajo gate fail-closed | 3 | v2 0/6 `json_invalid`; v3 0/6 HTTP 400 grammar; v4 6/6 aceptadas, 7,035854–29,485820 s | Juan Ignacio Gone | Responsable técnico + Responsable RRSS / SEU | `RESUELTO_PENDIENTE_REGRESION`; candidata sin commit |
| P4 | HU-011 | Validación humana registrada por canal | 3 | Paquete `1264d59` listo; acta, persona y nueve decisiones permanecen `PENDIENTE` | Validadores SEU | Josefina/SEU; Director para gate | `PENDIENTE_EXTERNO` |

**Estado agregado HU-011:** `PARCIAL / V4_ACEPTADA_PENDIENTE_REGRESION`. La muestra v4 fue técnicamente conforme, pero no está commiteada, la suite integral fuera del sandbox sigue pendiente y no hay validación SEU ni SLA.

## 4. Avance HU-012 fuera del Gate G2

| BPM | HU | Criterio | Evidencia candidata | Responsable | Estado |
|---|---|---|---|---|---|
| P4/P5 | HU-012 | Contrato, render determinista, estados HITL e idempotencia | Matriz offline y goldens de confirmación en el worktree | Juan Ignacio Gone | `PARCIAL / CANDIDATA_SIN_COMMIT` |
| P4/P5 | HU-012 | Entrega de confirmación | Sólo `DestinoConfirmacionesFake` en memoria; `ENVIADA_SIMULADA` | Juan Ignacio Gone + DSI/SEU | `NO_IMPLEMENTADA_LIVE`: no Gmail, SMTP ni email real |
| P4/P5 | HU-012 | Validación y plantilla institucional | Checklist vacío y límites documentados | Validadores SEU | `PENDIENTE_EXTERNO` |

## 5. Controles transversales del MVP y Gate G2

| BPM / control | Alcance | DoD del Gate G2 | Evidencia | Responsable | Estado |
|---|---|---|---|---|---|
| P4 / HITL | HU-010 + HU-011 | Toda salida queda en borrador y una persona registra decisión | Paquete de nueve muestras/17 referencias listo; acta y decisiones SEU pendientes | SEU + Juan Ignacio | `PARCIAL` |
| P4 / trazabilidad | HU-010 + HU-011 | Input, versión, output, estado y decisión reconstruibles | Ambas HU tienen trazabilidad offline; faltan ejecución institucional y decisión SEU | Juan Ignacio Gone | `PARCIAL` |
| Seguridad y operaciones | MVP/D2/D3 | Sin secretos ni acciones no autorizadas; health/reconciliación/retención seguras | Harness versionado más tooling candidato offline sobre manifests sanitizados; probes live pendientes | Juan Ignacio + DSI | `PARCIAL` |
| Calidad | MVP | Sin defectos críticos y defectos altos resueltos o aceptados | Registro creado; defectos altos abiertos | Juan Ignacio + Director | `NO_CUMPLE` |
| Persistencia Sprint 3 | Transversal | Esquema, transacciones, idempotencia y retención verificables | Spike con puerto, adapter memoria y SQL no ejecutado | Juan Ignacio + DSI | `PREPARADO_NO_EJECUTADO`; no PostgreSQL operativo |
| Interfaces A2–A5 | P4 inbound | A1 recibe datos trazables sin orquestar productores | Contrato candidato `b187960`; pipelines aún no integrados | Arquitectura P100 + Juan Ignacio | `CANDIDATO_NO_INSTITUCIONAL` |
| Evidencia CONEAU | MVP | Índice, outputs, logs, defectos, checklists y responsables recuperables | Evidencia offline, paquete SEU y smoke fallido HU-011 indexados; faltan integración y decisiones institucionales | Juan Ignacio + Director/SEU | `PARCIAL` |
| Gate G2 | HU-010 + HU-011 | Caso simple de ambas HU validado en entorno controlado; evidencia completa | No se cumplen ambos DoD ni validación registrada | César Cicerchia + SEU | `PENDIENTE_EXTERNO` |

## 6. Veredicto

La candidata agrega HU-011 v4 técnicamente conforme, Workspace E2E offline, tooling operativo, un spike de persistencia y HU-012 offline. Todo este cierre continúa sin commit y sin regresión integral fuera del sandbox. El **Gate G2 / TRL 3 permanece `PENDIENTE`** hasta versionar y verificar la candidata, ejecutar los incrementos live requeridos, registrar validación humana y cerrar los defectos altos.
