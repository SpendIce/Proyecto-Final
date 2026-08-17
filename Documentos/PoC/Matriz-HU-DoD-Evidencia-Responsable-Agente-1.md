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
| P4 | HU-010 | Input desde Google Sheets | 3 | Adapter contractual offline `b528efe` | Juan Ignacio Gone + Vera/DSI | Vera/DSI + SEU | `PARCIAL`: falta OAuth y ejecución live |
| P4 | HU-010 | Output en Google Docs | 3 | Adapter contractual offline `bd6bd49` | Juan Ignacio Gone + Vera/DSI | Vera/DSI + SEU | `PARCIAL`: falta ejecución live |
| P4 | HU-010 | Aplicar plantilla institucional y carpeta aprobada | 3 | Requisito documentado; adapter actual no aplica plantilla ni Drive | Josefina/SEU provee; Juan Ignacio implementa; DSI provisiona | Josefina Carullo / SEU | `PENDIENTE_EXTERNO` |
| P4 | HU-010 | Logs, correlation ID, hashes y versiones recuperables | 3 | Manifest y matriz HU-010; logging del pipeline | Juan Ignacio Gone | Director / auditoría interna | `CUMPLE_TECNICO` para slice local |
| P4 | HU-010 | Tiempo de ejecución aceptable | 3 | Green warm 20,172128 s; prompt-cold timeout hasta 45 s | Juan Ignacio Gone + DSI | César / SEU según umbral acordado | `PARCIAL` |
| P4 | HU-010 | Validación humana registrada, sin alucinaciones y tono institucional | 3 | Instrumento disponible; todos los casos continúan `PENDIENTE` | Validadores SEU | Josefina/SEU; Director para gate | `PENDIENTE_EXTERNO` |

**Estado agregado HU-010:** `PARCIAL`. La historia no cumple todavía su DoD institucional.

## 3. Matriz de HU-011

| BPM | HU | Criterio DoD / aceptación | TRL | Evidencia actual al corte | Responsable de ejecución | Responsable de aceptación | Estado |
|---|---|---|---:|---|---|---|---|
| P4 | HU-011 | Formato adaptable para Instagram y LinkedIn | 3 | Contrato y políticas por canal en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE`; política institucional pendiente |
| P4 | HU-011 | Texto limpio y coherente, preservando hechos fuente | 3 | Prompts, seis goldens y grounding mecánico conservador en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `PARCIAL`: conformidad mecánica sí; calidad SEU no |
| P4 | HU-011 | Longitud configurable por canal | 3 | Políticas y pruebas versionadas en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE` con límites provisionales |
| P4 | HU-011 | Hashtags con formato y deduplicación controlados | 3 | Gate y pruebas versionados en `537402a` | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE`; criterio SEU definitivo pendiente |
| P4 | HU-011 | Casos completos e incompletos, sin invocar LLM ante datos inválidos | 3 | Matriz de diez ejecuciones: seis borradores y cuatro incompletas | Juan Ignacio Gone | Director / SEU | `CUMPLE_TECNICO` con fake y datos simulados |
| P4 | HU-011 | Logs, correlation ID, hashes y versiones | 3 | Matriz HU-011 registra trazabilidad segura por ejecución | Juan Ignacio Gone | Director / auditoría interna | `CUMPLE_TECNICO` para slice offline |
| P4 | HU-011 | Borrador por canal; nunca publicación automática | 3 | Smoke fake y goldens conservan `BORRADOR — NO PUBLICAR`; no hay APIs RRSS | Juan Ignacio Gone | Responsable RRSS / SEU | `IMPLEMENTADA_OFFLINE` |
| P4 | HU-011 | Validación humana registrada por canal | 3 | `VAL-S1-HU-011-SEU` reservado; validadores/criterios definitivos no evidenciados | Validadores SEU | Josefina/SEU; Director para gate | `PENDIENTE_EXTERNO` |

**Estado agregado HU-011:** `PARCIAL / IMPLEMENTADA_OFFLINE`. No se declara completa, operativa en Workspace ni validada.

## 4. Controles transversales del MVP y Gate G2

| BPM / control | Alcance | DoD del Gate G2 | Evidencia | Responsable | Estado |
|---|---|---|---|---|---|
| P4 / HITL | HU-010 + HU-011 | Toda salida queda en borrador y una persona registra decisión | Estados y checklists existen; decisiones SEU no | SEU + Juan Ignacio | `PARCIAL` |
| P4 / trazabilidad | HU-010 + HU-011 | Input, versión, output, estado y decisión reconstruibles | Ambas HU tienen trazabilidad offline; faltan ejecución institucional y decisión SEU | Juan Ignacio Gone | `PARCIAL` |
| Seguridad | MVP | Sin secretos expuestos ni acciones no autorizadas | Controles unitarios HU-010/HU-011; consolidación D2/D3 pendiente | Juan Ignacio + DSI | `PARCIAL` |
| Calidad | MVP | Sin defectos críticos y defectos altos resueltos o aceptados | Registro creado; defectos altos abiertos | Juan Ignacio + Director | `NO_CUMPLE` |
| Evidencia CONEAU | MVP | Índice, outputs, logs, defectos, checklists y responsables recuperables | HU-010 y HU-011 tienen evidencia técnica offline; faltan integración institucional y decisiones SEU | Juan Ignacio + Director/SEU | `PARCIAL` |
| Gate G2 | HU-010 + HU-011 | Caso simple de ambas HU validado en entorno controlado; evidencia completa | No se cumplen ambos DoD ni validación registrada | César Cicerchia + SEU | `PENDIENTE_EXTERNO` |

## 5. Veredicto

El MVP ya contiene implementaciones técnicas/offline de HU-010 y HU-011 con suite integral de 151 pruebas y matrices reproducibles. Sin embargo, el **Gate G2 / TRL 3 permanece `PENDIENTE`** hasta ejecutar los incrementos live requeridos, registrar validación humana y resolver los defectos altos que bloquean el flujo principal.
