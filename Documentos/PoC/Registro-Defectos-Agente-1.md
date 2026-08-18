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

Estados: `ABIERTO`, `EN_CORRECCION`, `BLOQUEADO_EXTERNO`, `RESUELTO_TECNICO`, `RESUELTO_PENDIENTE_REGRESION`, `RESUELTO_PENDIENTE_COMMIT`, `RESUELTO_PENDIENTE_VALIDACION`, `RESUELTO_PARCIAL`, `CERRADO`.

- `RESUELTO_PENDIENTE_COMMIT`: la corrección está verificada en el worktree pero todavía no existe en un commit recuperable.
- `RESUELTO_PENDIENTE_VALIDACION`: la corrección técnica está verificada pero depende de una validación humana o institucional para cerrarse.
- `RESUELTO_PARCIAL`: una parte del defecto fue corregida y verificada; el resto queda abierto con criterio explícito.

## 2. Registro vigente

| ID | Tipo | HU / control | Ambiente | Descripción y evidencia verificable | Severidad | Estado | Responsable / owner | Criterio de cierre |
|---|---|---|---|---|---|---|---|---|
| `DEF-A1-001` | Brecha de integración | HU-010 / DoD Workspace | D2/D3 no provisionado | `5484684` agregó configuración cerrada y smoke read-only opt-in; los adapters continúan verificados offline. No existen en evidencia OAuth/credenciales, IDs institucionales ni una corrida live. | `ALTA` | `BLOQUEADO_EXTERNO` | Vera Batista/DSI + administrador designado; Juan Ignacio integra | Prueba positiva y negativa de permisos; manifest Sheets → Docs/Drive; cero secretos expuestos |
| `DEF-A1-002` | Brecha funcional | HU-010 / plantilla | D2/D3 | `5484684` implementó y probó offline copia de plantilla y ubicación en carpeta mediante transporte fake. Siguen faltando plantilla/carpeta oficiales, permisos y ejecución live aprobada. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU; Vera/DSI para recursos; Juan Ignacio para integración | Plantilla institucional versionada aplicada en D2/D3, Folder/Template configurados por canal seguro y prueba recuperable live |
| `DEF-A1-003` | Performance / estabilidad | HU-010 / LLM | Local controlado | El benchmark registra timeouts prompt-cold hasta 45 s; sólo una corrida `112/45` con caché warm del mismo prompt quedó verde en 20,172128 s. Evidencia: `benchmark-hu010-2026-07-17.md`. | `ALTA` | `ABIERTO` | Juan Ignacio Gone / responsable técnico IA; DSI para host objetivo | Matriz repetible cold/warm en host acordado, umbral aceptado y fallback operativo documentado |
| `DEF-A1-004` | Brecha de alcance MVP | HU-011 | Local controlado | La brecha de implementación offline fue resuelta en `537402a`: contrato y políticas por canal, prompts, seis goldens, pipeline, matriz, smoke fake y checklist. | `ALTA` | `RESUELTO_TECNICO` | Juan Ignacio Gone | Cumplido para alcance offline; el DoD permanece abierto por `DEF-A1-005`, `DEF-A1-007` y `DEF-A1-008` |
| `DEF-A1-005` | Brecha de validación | HU-010 y HU-011 / HITL | D2/D3 | `1264d59` dejó listo un paquete de nueve muestras y 17 referencias, pero el acta, la persona revisora, los puntajes y la decisión continúan `PENDIENTE`; no hay validación SEU real. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU y validadores designados | Validadores titular/suplente registrados y acta/checklist por nueve muestras con puntaje, observaciones, fecha y decisión |
| `DEF-A1-006` | Brecha de criterio de gate | Gate G2 | Gestión | César Cicerchia indicó que analizaría la evidencia exigida; no consta aún una definición final de evidencia mínima, firmantes y mecanismo go/no-go. | `ALTA` | `BLOQUEADO_EXTERNO` | César Cicerchia | Criterio G2 documentado y decisión registrada sobre el paquete completo |
| `DEF-A1-007` | Brecha de contenido | HU-011 / canal | Gestión / local | No constan criterios SEU definitivos de tono, longitud y hashtags para Instagram y LinkedIn. La implementación sólo puede usar reglas provisionales explícitas. | `ALTA` | `BLOQUEADO_EXTERNO` | Josefina Carullo/SEU + responsable RRSS; Juan Ignacio versiona | Guía por canal aprobada y versión de prompts/gates ajustada con regresión |
| `DEF-A1-008` | Conformidad generativa | HU-011 / Ollama | Local controlado | La secuencia no commiteada registró structured v2 0/6 por `json_invalid`, v3 0/6 por HTTP 400 de grammar y v4 6/6 aceptaciones técnicas entre 7,035854 y 29,485820 s. Falta la regresión integral fuera del sandbox y evidencia versionada. | `ALTA` | `RESUELTO_PENDIENTE_REGRESION` | Juan Ignacio Gone / responsable técnico IA | Reejecutar suite completa fuera del sandbox, confirmar v4 sin debilitar gates, versionar código/evidencia en un commit atómico y ampliar cobertura; SEU/SLA permanecen en otros bloqueantes |
| `DEF-A1-009` | Bloqueante de verificación y empaquetado | Candidata MVP/Sprint 3 | Entorno local | La suite completa se ejecutó fuera del sandbox: **437 pruebas, 436 verdes, cero `EPERM`**. Las 16 fallas de loopback eran ambientales y no se reprodujeron. La única falla restante es el test de consistencia del README sobre migraciones versionadas, que se anticipa al commit. La candidata **sigue sin commit**. | `ALTA` | `RESUELTO_PENDIENTE_COMMIT` | Juan Ignacio Gone / responsable técnico IA | Inspeccionar scope y crear commit atómico sin inventar hash; tras el commit, actualizar el README y confirmar la suite en verde completo |
| `DEF-A1-011` | Brecha de aptitud funcional | HU-011 / creatividad | Local controlado | El catálogo enum de `post_creative_output_v2` admite sólo **8 combinaciones de texto por canal**. En la corrida live del 17/08, tres actividades distintas produjeron **una única combinación creativa por canal** y siempre los cuatro hashtags: a temperatura 0 sobre un enum, el modelo se comporta como función constante y no discrimina entre entradas. Un selector aleatorio daría más variedad a 0,001 s en lugar de 36 s de inferencia. La conformidad 6/6 mide transporte y contrato, **no aptitud comunicacional**. Evidencia: `benchmark-hu011-ollama-live-cobertura-ampliada-2026-08-17.md`. | `ALTA` | `RESUELTO_PENDIENTE_VALIDACION` | Juan Ignacio Gone / responsable técnico IA; SEU define criterios | El contrato `post_creative_output_v3` libera la redacción sin tocar el gate de hechos: 4/6 aceptadas con cuatro textos distintos, y los 2 rechazos son fuga real de hechos detectada por el gate. Falta validación SEU de calidad y registro lingüístico. Evidencia: `benchmark-hu011-contrato-v3-redaccion-libre-2026-08-17.md` |
| `DEF-A1-012` | Brecha de detección | HU-011 / gate de hechos | Local controlado | El gate léxico no cubre riesgos que aparecen con redacción libre: escribe en tuteo neutro pese a pedirse voseo rioplatense; `PATRON_HECHO_CREATIVO` no incluye `remoto` y una salida usó «seminario remoto»; «¡Inscríbete ahora!» sugiere un circuito inexistente; `_contiene_hecho` compara el campo completo, de modo que un fragmento como «taller» no coincide con «Taller sintético de vinculación». | `MEDIA` | `ABIERTO` | Juan Ignacio Gone / responsable técnico IA; SEU define registro y tono | Ampliar el patrón de modalidad, decidir tratamiento de paráfrasis y fragmentos, y fijar registro lingüístico con la SEU; ninguno de estos riesgos es detectable de forma completa por un gate léxico |
| `DEF-A1-010` | Brecha de integridad estructural | Sprint 3 / persistencia | PostgreSQL efímero local | La ejecución real de `0001` reveló cinco invariantes documentadas que el esquema **no** aplicaba: borrador sobre ejecución `FALLIDA`/`INCOMPLETA`/`INICIADA`, `output_hash` de borrador distinto al de su ejecución, validación anterior al borrador y timestamps futuros. Quedaron persistidos tres borradores huérfanos y una validación con fecha futura. Evidencia: `validacion-migraciones-postgresql-efimero-2026-08-17.md`. | `MEDIA` | `RESUELTO_PARCIAL` | Juan Ignacio Gone / responsable técnico IA; DSI para entorno | `0002` cierra las tres primeras brechas con FK compuestas, verificado con atribución de constraint. Timestamps futuros siguen dependiendo del puerto: requieren decisión sobre usar `now()` en CHECK o un trigger |

## 3. Observaciones de seguridad

- No se registró evidencia de publicación, envío, sharing automático o exposición de credenciales en el slice controlado.
- El harness offline de `5484684` obtuvo `PASS` para redacción, allowlists, errores remotos, ausencia de endpoints de distribución, revocación simulada y estado de borrador. Esto **no** equivale a aprobación de seguridad: faltan permisos, revocación, aislamiento y tráfico real en D2/D3.
- El Gate G2 permanece bloqueado aun sin defectos `CRITICA`, porque existen defectos `ALTA` que afectan el flujo principal y la evidencia de aceptación.

## 4. Revisión y cierre

Para cerrar un registro deben agregarse fecha, evidencia de corrección y prueba de regresión. Los bloqueantes externos no deben marcarse `CERRADO` por una conversación informal: requieren un recurso, decisión o acta recuperable.

| ID | Fecha de cierre | Evidencia de corrección | Prueba de regresión | Aceptado por |
|---|---|---|---|---|
| `DEF-A1-004` | 2026-08-17 | Commit `537402a`; matriz y checklist HU-011 versionados | 151 pruebas, smoke fake y matrices HU-010/HU-011 verdes; review `CLEAN` | Revisión técnica del incremento; no aceptación SEU |
| `DEF-A1-008` | Pendiente | Evidencia v2/v3/v4 presente sólo en worktree; corte de cobertura ampliada agrega 6/6 live y 4/4 negativos | Suite completa fuera del sandbox: 437 pruebas, 436 verdes, cero `EPERM`; cuatro output hashes reproducidos entre sesiones independientes | `RESUELTO_PENDIENTE_COMMIT`; no cerrado — falta commit atómico y validación SEU |
| `DEF-A1-010` | Pendiente | `migrations/0002_integridad_referencial_borradores.up.sql` | Ocho casos verificados con atribución de constraint sobre PostgreSQL 16; cero huérfanos; camino feliz intacto; rollback limpio | `RESUELTO_PARCIAL`; brechas de timestamp futuro abiertas por decisión |
