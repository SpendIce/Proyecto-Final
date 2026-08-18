# Índice de evidencias del MVP — Agente 1

- **Fecha de corte:** 17 de agosto de 2026
- **Alcance:** Proceso 4 — Comunicación y Difusión Institucional; HU-010 y HU-011
- **Estado del Gate G2 / TRL 3:** `PENDIENTE`

## 1. Regla de lectura

Este índice distingue evidencia existente, evidencia parcial y pendientes técnicos o institucionales. Una referencia a código, prueba contractual o salida simulada no equivale a validación de la Secretaría de Extensión Universitaria (SEU). Ningún elemento de este paquete autoriza publicación automática ni permite declarar cerrado el Gate G2.

Estados utilizados:

- `DISPONIBLE`: el artefacto está versionado y es recuperable.
- `PARCIAL`: existe evidencia técnica, pero no satisface por sí sola el DoD institucional.
- `IMPLEMENTADA_OFFLINE`: el incremento está versionado y verificado sin servicios institucionales live.
- `CANDIDATA_SIN_COMMIT`: código y evidencia presentes en el worktree, todavía sin hash Git de cierre.
- `PENDIENTE_TECNICO`: falta una ejecución o artefacto técnico específico.
- `PENDIENTE_EXTERNO`: depende de una definición, recurso o validación institucional.

## 2. Línea base versionada

| Referencia Git | Contenido verificable | Alcance probatorio |
|---|---|---|
| `809ee24` | Thin slice local de HU-010: CSV → generador fake → borrador → log | Flujo controlado inicial; no Workspace ni SEU |
| `e0510b8` | Adapter local de Ollama y smoke opt-in | Invocación local controlada; no calidad institucional |
| `3de9a9c` | Contrato y prompt versionados de gacetillas | Gate mecánico provisional de HU-010 |
| `dbf3bbf` | Benchmark, manifest y checklist HU-010 | Evidencia técnica local; revisión humana pendiente |
| `b528efe` | Fuente CSV/Sheets contractual y matriz sintética HU-010 | Contrato Sheets probado offline; no OAuth ni ejecución live |
| `bd6bd49` | Destino Markdown/Google Docs contractual | Contrato Docs probado offline; no plantilla, carpeta ni ejecución live |
| `3931a90` | Especificación D2/D3 con tenant Google Workspace `@fie.undef.edu.ar` | Requisitos de provisión; no acredita ambiente provisionado |
| `537402a` | HU-011 multicanal: contrato, políticas, prompts, goldens, pipeline, matriz y checklist | Implementación offline verificada; el baseline Ollama posterior fue no conforme |
| `5484684` | Configuración y smoke Workspace opt-in, operaciones Drive plantilla/carpeta offline y harness de seguridad | Preparación técnica offline; ninguna ejecución Workspace live |
| `b187960` | Contrato candidato de insumos A2–A5 hacia A1 | Interfaz inbound provisional y offline; A1 no invoca ni orquesta otros agentes |
| `1264d59` | Paquete ejecutable de validación SEU | Nueve muestras y 17 referencias preparadas; acta y decisión `PENDIENTE` |
| `aa4765e` | Benchmark y manifest Ollama HU-011 | Transporte 6/6 sin timeout; conformidad 0/6 y cero borradores |

La suite conjunta del paquete versionado anterior registró 265 pruebas. Ese
total no se atribuye a un incremento individual ni describe la candidata actual.

## 2.1 Candidata de cierre todavía sin commit

El cierre actual agrega HU-011 structured v2/v4, runner Workspace E2E offline,
spike de persistencia, tooling operativo y HU-012 offline. Estos cambios y sus
evidencias están en el worktree **sin commit**: no se inventa un hash. El commit
atómico quedó pendiente por un bloqueo externo de límite de uso de Codex. Antes
de versionar debe repetirse la suite completa fuera del sandbox: la corrida
disponible obtuvo 417 pruebas verdes y 16 fallas `EPERM` de loopback atribuibles
al entorno; los bloques focalizados de 114 y 105 pruebas tuvieron review
`CLEAN`.

## 3. Evidencia disponible — HU-010

| ID de evidencia | Artefacto | Estado | Qué demuestra | Qué no demuestra |
|---|---|---|---|---|
| `EVID-A1-S1-HU-010-2026-07-17-BENCHMARK` | [`Implementacion/Agente1/evidencias/benchmark-hu010-2026-07-17.md`](../../Implementacion/Agente1/evidencias/benchmark-hu010-2026-07-17.md) | `PARCIAL` | Una corrida Ollama `llama3.2:3b` conforme bajo caché warm del mismo prompt, con latencia de 20,172128 s | Estabilidad prompt-cold, SLA, calidad SEU o TRL 3 |
| `EVID-A1-S1-HU-010-2026-07-17-MANIFEST` | [`Implementacion/Agente1/evidencias/manifest-hu010-syn001.json`](../../Implementacion/Agente1/evidencias/manifest-hu010-syn001.json) | `PARCIAL` | Trazabilidad de modelo, prompt, contrato, hashes y correlation ID de `SYN-001` | Validación humana o uso institucional |
| `EVID-A1-S1-HU-010-2026-07-20-MATRIZ` | [`Implementacion/Agente1/evidencias/matriz-conformidad-hu010-2026-07-20.md`](../../Implementacion/Agente1/evidencias/matriz-conformidad-hu010-2026-07-20.md) | `PARCIAL` | Cinco casos sintéticos: tres borradores conformes y dos rechazos previos por datos incompletos | Calidad LLM, tono, verdad semántica, Workspace live o SEU |
| `EVID-A1-S1-HU-010-CHECKLIST` | [`Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`](../../Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md) | `DISPONIBLE` como instrumento; `PENDIENTE_EXTERNO` como registro | Criterios y escala 1–4 para revisión | Una validación, mientras no tenga persona, fecha, puntajes y decisión |
| `EVID-A1-S1-HU-010-SHEETS-CONTRACT` | Código en `b528efe` y configuración/smoke opt-in en `5484684` | `PARCIAL` | Lectura contractual, configuración cerrada y camino read-only listo para D2 | OAuth, planilla institucional, permisos o ejecución live |
| `EVID-A1-S1-HU-010-DOCS-CONTRACT` | Código en `bd6bd49` y operaciones Drive plantilla/carpeta offline en `5484684` | `PARCIAL` | Creación/edición Docs y copia/ubicación Drive verificadas con transporte fake | Plantilla y carpeta oficiales, permisos o ejecución live |

### Pendientes HU-010 para cerrar DoD

| ID reservado | Evidencia requerida | Responsable principal | Estado |
|---|---|---|---|
| `EVID-A1-S1-HU-010-WORKSPACE-LIVE` | Acta o manifest de prueba Sheets → generación → Docs en D2/D3, sin secretos | Juan Ignacio Gone + Vera Batista/DSI | `PENDIENTE_EXTERNO` |
| `EVID-A1-S1-HU-010-PLANTILLA-SEU` | Plantilla y campos aprobados, con versión y responsable | Josefina Carullo / SEU | `PENDIENTE_EXTERNO` |
| `VAL-S1-HU-010-SEU` | Checklists completados, validador nominal, fecha y decisión por caso | Validadores designados por SEU | `PENDIENTE_EXTERNO` |

## 4. Evidencia disponible y pendiente — HU-011

HU-011 quedó implementada y aceptada en alcance técnico/offline en `537402a`. Los smokes fake y las matrices HU-010/HU-011 finalizaron verdes. El smoke posterior con Ollama real, documentado en `aa4765e`, respondió en los seis intentos sin timeout, pero ninguna salida fue conforme y el gate creó cero borradores. Por lo tanto, el transporte está probado y el fail-closed funcionó; la capacidad generativa real de HU-011 continúa abierta.

| ID de evidencia | Artefacto | Alcance probatorio | Estado |
|---|---|---|---|
| `EVID-A1-S1-HU-011-CONTRATO-CANAL` | `src/agente1/contracts/post_input_v1.schema.json` y `src/agente1/posts.py`, commit `537402a` | Contrato y políticas por canal, aún `PROVISIONAL_NO_INSTITUCIONAL` | `IMPLEMENTADA_OFFLINE` |
| `EVID-A1-S1-HU-011-PROMPTS-GOLDENS` | `src/agente1/prompts/post_instagram_v1.txt`, `post_linkedin_v1.txt` y seis archivos en `golden/posts/`, commit `537402a` | Formato y regresión determinista por canal; no calidad institucional | `IMPLEMENTADA_OFFLINE` |
| `EVID-A1-S1-HU-011-MATRIZ-SINTETICA` | [`Implementacion/Agente1/evidencias/matriz-conformidad-hu011-2026-08-17.md`](../../Implementacion/Agente1/evidencias/matriz-conformidad-hu011-2026-08-17.md) | Diez ejecuciones: seis borradores idénticos a golden y cuatro incompletas sin generador ni borrador | `IMPLEMENTADA_OFFLINE` |
| `EVID-A1-S1-HU-011-SMOKE-FAKE` | `Implementacion/Agente1/scripts/smoke_posts.sh`, commit `537402a` | Flujo acotado de una actividad completa en ambos canales | `IMPLEMENTADA_OFFLINE` |
| `EVID-A1-S1-HU-011-SMOKE-OLLAMA-V1` | [`benchmark-hu011-ollama-2026-08-17.md`](../../Implementacion/Agente1/evidencias/benchmark-hu011-ollama-2026-08-17.md) y manifest, commit `aa4765e` | 6/6 respuestas de transporte, 0 timeouts, 0/6 conformes y 0 borradores | `NO_CONFORME` histórico |
| `EVID-A1-S1-HU-011-STRUCTURED-V2` | [`benchmark-hu011-ollama-structured-v2-2026-08-17.md`](../../Implementacion/Agente1/evidencias/benchmark-hu011-ollama-structured-v2-2026-08-17.md) y manifest | 0/6 aceptadas por `json_invalid`; cero borradores | `CANDIDATA_SIN_COMMIT` |
| `EVID-A1-S1-HU-011-JSON-SCHEMA-V3` | [`benchmark-hu011-ollama-json-schema-v3-2026-08-17.md`](../../Implementacion/Agente1/evidencias/benchmark-hu011-ollama-json-schema-v3-2026-08-17.md) y manifest | 0/6; HTTP 400 por grammar incompatible antes de inferencia | `CANDIDATA_SIN_COMMIT` |
| `EVID-A1-S1-HU-011-JSON-SCHEMA-V4` | [`benchmark-hu011-ollama-json-schema-v4-2026-08-17.md`](../../Implementacion/Agente1/evidencias/benchmark-hu011-ollama-json-schema-v4-2026-08-17.md) y manifest | 6/6 aceptaciones técnicas, 7,035854–29,485820 s, estado `PENDIENTE_VALIDACION` | `CANDIDATA_SIN_COMMIT`; regresión completa pendiente |
| `EVID-A1-S1-HU-011-CHECKLIST` | [`Implementacion/Agente1/evidencias/checklist-validacion-humana-hu011.md`](../../Implementacion/Agente1/evidencias/checklist-validacion-humana-hu011.md) | Instrumento por canal disponible; todos sus campos de revisión siguen pendientes | `DISPONIBLE` como instrumento; `PENDIENTE_EXTERNO` como registro |
| `VAL-S1-HU-011-SEU` | [`Documentos/PoC/Validacion-SEU/`](Validacion-SEU/) | Paquete listo con nueve muestras y 17 referencias; persona, puntajes, observaciones, decisión y acta permanecen pendientes | `DISPONIBLE` como paquete; `PENDIENTE_EXTERNO` como validación |

## 5. Evidencia transversal del Gate G2

| ID | Artefacto | Estado |
|---|---|---|
| `EVID-A1-G2-INDICE` | Este índice | `DISPONIBLE` |
| `EVID-A1-G2-DEFECTOS` | [`Registro-Defectos-Agente-1.md`](Registro-Defectos-Agente-1.md) | `DISPONIBLE`; cierre pendiente |
| `EVID-A1-G2-MATRIZ-TRAZABILIDAD` | [`Matriz-HU-DoD-Evidencia-Responsable-Agente-1.md`](Matriz-HU-DoD-Evidencia-Responsable-Agente-1.md) | `DISPONIBLE`; filas abiertas |
| `EVID-A1-G2-PLAN-RECUPERACION` | [`Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`](Plan-Recuperacion-MVP-Agente-1-2026-08-17.md) | `DISPONIBLE` |
| `EVID-A1-G2-WORKSPACE-D2` | `5484684`: configuración cerrada, smoke read-only opt-in y Drive plantilla/carpeta offline | `PARCIAL`; no hubo acceso live |
| `EVID-A1-G2-PRUEBAS-SEGURIDAD` | [`auditoria-seguridad-d2-d3.md`](../../Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md) y reporte offline PASS, commit `5484684` | `IMPLEMENTADA_OFFLINE`; permisos, revocación y aislamiento live pendientes |
| `EVID-A1-G2-VALIDACION-SEU` | Paquete de nueve muestras y manifest de 17 referencias, commit `1264d59` | `DISPONIBLE`; acta `PENDIENTE`, sin validación real |
| `EVID-A1-G2-CONTRATO-A2-A5` | [`Contrato-Candidato-Insumos-A2-A5-Agente-1.md`](Contrato-Candidato-Insumos-A2-A5-Agente-1.md), commit `b187960` | `CANDIDATO_NO_INSTITUCIONAL`; sin integración ni orquestación |
| `EVID-A1-G2-WORKSPACE-E2E-OFFLINE` | [`runbook-workspace-e2e.md`](../../Implementacion/Agente1/evidencias/runbook-workspace-e2e.md) | Runner Sheets → HU → Drive/Docs → manifest verificado con fakes; no live | `CANDIDATA_SIN_COMMIT` |
| `EVID-A1-S3-PERSISTENCIA-SPIKE` | [`spike-persistencia-postgresql-2026-08-17.md`](../../Implementacion/Agente1/evidencias/spike-persistencia-postgresql-2026-08-17.md) | Puerto, adapter memoria y SQL contractual; PostgreSQL no instalado ni ejecutado | `CANDIDATA_SIN_COMMIT` |
| `EVID-A1-S3-OPS-OFFLINE` | [`runbook-operaciones-seguras-d2-d3.md`](../../Implementacion/Agente1/evidencias/runbook-operaciones-seguras-d2-d3.md) | Health, reconciliación, consolidación y retención dry-run sobre manifests sanitizados | `CANDIDATA_SIN_COMMIT`; probes live pendientes |
| `EVID-A1-S2-HU-012-OFFLINE` | [`matriz-conformidad-hu012-2026-08-17.md`](../../Implementacion/Agente1/evidencias/matriz-conformidad-hu012-2026-08-17.md) | Contrato y entrega fake en memoria; no Gmail/SMTP, email real ni aprobación SEU | `CANDIDATA_SIN_COMMIT` |
| `EVID-A1-G2-INFORME` | Informe de go/no-go firmado o aceptado según criterio de César Cicerchia | `PENDIENTE_EXTERNO` |

## 6. Veredicto al corte

- **HU-010:** `PARCIAL`; existe flujo técnico controlado y evidencia reproducible, pero faltan Workspace live, plantilla institucional y validación SEU.
- **HU-011:** `PARCIAL / V4_ACEPTADA_PENDIENTE_REGRESION`; v4 produjo 6/6 borradores técnicamente aceptados, pero el código/evidencia no están commiteados, falta la regresión completa fuera del sandbox y no existe validación SEU ni SLA.
- **Gate G2 / TRL 3:** `PENDIENTE`; faltan ambos DoD, validación humana registrada, cierre de defectos altos y decisión formal.
