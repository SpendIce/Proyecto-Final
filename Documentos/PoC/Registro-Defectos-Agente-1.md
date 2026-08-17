# Registro de defectos y bloqueantes del MVP — Agente 1

- **Fecha de corte:** 17 de agosto de 2026
- **Gate asociado:** G2 — TRL 3 (`PENDIENTE`)

## 1. Criterio de registro

Este documento registra defectos técnicos observados y brechas verificables contra el DoD. Una dependencia externa abierta se rotula como `BLOQUEANTE` para no presentarla falsamente como incidente de software. No se inventan fallas productivas: todavía no existe una operación institucional live aceptada.

Severidad aplicada según el Plan de Calidad:

- `CRITICA`: exposición, publicación no autorizada, invención crítica, pérdida de trazabilidad o bloqueo total sin alternativa segura.
- `ALTA`: afecta el flujo principal, rompe integración o impide el gate.
- `MEDIA`: afecta un flujo alternativo, formato o usabilidad sin comprometer seguridad.
- `BAJA`: mejora no bloqueante.

Estados: `ABIERTO`, `EN_CORRECCION`, `BLOQUEADO_EXTERNO`, `RESUELTO_TECNICO`, `RESUELTO_PENDIENTE_REGRESION`, `CERRADO`.

## 2. Registro vigente

| ID | Tipo | HU / control | Ambiente | Descripción y evidencia verificable | Severidad | Estado | Responsable / owner | Criterio de cierre |
|---|---|---|---|---|---|---|---|---|
| `DEF-A1-001` | Brecha de integración | HU-010 / DoD Workspace | D2/D3 no provisionado | Los adapters Sheets y Docs están probados offline (`b528efe`, `bd6bd49`), pero no existen OAuth/credenciales, IDs institucionales ni smoke live. Véase la especificación D2/D3 `3931a90`. | `ALTA` | `BLOQUEADO_EXTERNO` | Vera Batista/DSI + administrador designado; Juan Ignacio integra | Prueba positiva y negativa de permisos; manifest Sheets → Docs; cero secretos expuestos |
| `DEF-A1-002` | Brecha funcional | HU-010 / plantilla | D2/D3 | El adapter Docs crea texto en un documento vacío; no aplica plantilla ni lo ubica en la carpeta institucional. La plantilla, carpeta, campos definitivos y reglas deben ser provistos o aprobados por Josefina Carullo/SEU. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU; Vera/DSI para recursos; Juan Ignacio para implementación | Plantilla versionada aplicada en D2/D3, Folder/Template configurados por canal seguro y prueba recuperable |
| `DEF-A1-003` | Performance / estabilidad | HU-010 / LLM | Local controlado | El benchmark registra timeouts prompt-cold hasta 45 s; sólo una corrida `112/45` con caché warm del mismo prompt quedó verde en 20,172128 s. Evidencia: `benchmark-hu010-2026-07-17.md`. | `ALTA` | `ABIERTO` | Juan Ignacio Gone / responsable técnico IA; DSI para host objetivo | Matriz repetible cold/warm en host acordado, umbral aceptado y fallback operativo documentado |
| `DEF-A1-004` | Brecha de alcance MVP | HU-011 | Local controlado | La brecha de implementación offline fue resuelta en `537402a`: contrato y políticas por canal, prompts, seis goldens, pipeline, matriz, smoke fake y checklist. Suite integral: 151 pruebas verdes; revisión `CLEAN`. No incluye Ollama live ni validación SEU. | `ALTA` | `RESUELTO_TECNICO` | Juan Ignacio Gone | Cumplido para alcance offline; el DoD institucional permanece abierto por `DEF-A1-005` y `DEF-A1-007` |
| `DEF-A1-005` | Brecha de validación | HU-010 y HU-011 / HITL | D2/D3 | No hay checklists completados por validadores nominales SEU. La designación estaba prevista desde el 04/08, pero no existe evidencia recuperable de nombres, fechas y decisiones en el repositorio. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU y validadores designados | Validadores titular/suplente registrados y checklist por muestra con puntaje, observaciones, fecha y decisión |
| `DEF-A1-006` | Brecha de criterio de gate | Gate G2 | Gestión | César Cicerchia indicó que analizaría la evidencia exigida; no consta aún una definición final de evidencia mínima, firmantes y mecanismo go/no-go. | `ALTA` | `BLOQUEADO_EXTERNO` | César Cicerchia | Criterio G2 documentado y decisión registrada sobre el paquete completo |
| `DEF-A1-007` | Brecha de contenido | HU-011 / canal | Gestión / local | No constan criterios SEU definitivos de tono, longitud y hashtags para Instagram y LinkedIn. La implementación sólo puede usar reglas provisionales explícitas. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU + responsable RRSS; Juan Ignacio versiona | Guía por canal aprobada y versión de prompts/gates ajustada con regresión |

## 3. Observaciones de seguridad

- No se registró evidencia de publicación, envío, sharing automático o exposición de credenciales en el slice controlado.
- Esa ausencia de incidentes **no** equivale a aprobación de seguridad: faltan las pruebas transversales de permisos, prompt injection, revocación y acciones no autorizadas en D2/D3.
- El Gate G2 permanece bloqueado aun sin defectos `CRITICA`, porque existen defectos `ALTA` que afectan el flujo principal y la evidencia de aceptación.

## 4. Revisión y cierre

Para cerrar un registro deben agregarse fecha, evidencia de corrección y prueba de regresión. Los bloqueantes externos no deben marcarse `CERRADO` por una conversación informal: requieren un recurso, decisión o acta recuperable.

| ID | Fecha de cierre | Evidencia de corrección | Prueba de regresión | Aceptado por |
|---|---|---|---|---|
| `DEF-A1-004` | 2026-08-17 | Commit `537402a`; matriz y checklist HU-011 versionados | 151 pruebas, smoke fake y matrices HU-010/HU-011 verdes; review `CLEAN` | Revisión técnica del incremento; no aceptación SEU |
