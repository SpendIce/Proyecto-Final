# Revisión del avance del Gantt al 21/10/2026

- **Ticket:** #129, hijo del mapa #128.
- **Corte:** 2026-10-19, noche, antes de la presentación de avance del miércoles 2026-10-21 a las 09:00.
- **Plan:** `Documentos/Gantt/diagrama-gantt-implementacion-semanal.mmd`. No se modificó: no hay rebaseline ni estados nuevos.
- **Avance:** `Documentos/Gantt/gantt-progreso.js`.
- **Resultado:** 47 IDs en el `.mmd`; 27 con `done: true` y 20 sin marca. El 20/10 se sumaron s1c, s3b, s5a y m7.

## 1. Corte y fuentes usadas

El contraste se hizo con estas fuentes, todas consultadas el 2026-10-19:

| Fuente | Qué se miró |
|---|---|
| Git | `git log --oneline --since=2026-09-20`; commits de cierre de los tickets #50, #117, #121, #122, #123, #111 y #98. |
| Issues | `gh issue list --state closed --limit 100` y `gh issue list --state open --limit 100`. Se usaron #14, #15, #17, #50, #63, #64, #99, #118, #119, #125 y #126. |
| Evidencias | `Implementacion/Agente1/evidencias/`: medición del servidor del 2026-10-19, contrato Historia Viva rc2, anexos del 2026-10-17, SLO del 2026-10-12, cuenta de servicio del 2026-10-14, auditoría de seguridad D2/D3 y límites de HU-014. |
| Suite y CI | `uv run pytest -q` en `Implementacion/Agente1` el 2026-10-19: 2282 passed, 8 skipped en 63,42 s. Run de CI `39302694001` del 2026-10-19: 1 failed, 2284 passed, 5 skipped, cobertura 90 %. |
| Defectos | `Documentos/PoC/Registro-Defectos-Agente-1.md`. Siguen sin cierre definitivo DEF-A1-001, DEF-A1-002, DEF-A1-003, DEF-A1-005, DEF-A1-006, DEF-A1-007, DEF-A1-011, DEF-A1-012 y DEF-A1-015. |
| Visita SEU | Documentación local de la visita del 2026-10-19 en `Documentos/Reuniones/SEU-2026-10-19/`: actas de Josefina y Leandro, cierre, precisiones de Juani, ficha de la plantilla de certificado y clasificación de respuestas. Al corte esos archivos no están versionados; no se copiaron al repo. Los issues #125 y #126 son el registro durable de los dos trabajos derivados. |
| Plan y formato | `Documentos/Gantt/README.md` y el propio `.mmd`. Se respetaron los IDs y las fechas del plan. |

La documentación de la visita se usó como contexto; las afirmaciones de esta revisión se apoyan en el acta, en la ficha de la plantilla y en los issues creados, no en inferencias sobre lo que la SEU podría aprobar.

## 2. Cómo queda el avance por sprint

| Sprint | IDs | Marcados | Sin marca |
|---|---:|---:|---:|
| Sprint 0 - Bootstrap | 4 | 4 | 0 |
| Sprint 1 - HU-010 Gacetillas | 6 | 4 | 2 |
| Sprint 2 - HU-011 Posts | 5 | 3 | 2 |
| Sprint 3 - Bloqueantes y base técnica | 5 | 3 | 2 |
| Sprint 4 - HU-012 Confirmaciones | 6 | 4 | 2 |
| Sprint 5 - HU-013 Lenguaje natural | 5 | 3 | 2 |
| Sprint 6 - HU-014 Certificados | 6 | 5 | 1 |
| Sprint 7 - Integración y pruebas | 5 | 1 | 4 |
| Cierre - Validación y Gate TRL 4 | 5 | 0 | 5 |
| **Total** | **47** | **27** | **20** |

## 3. Lo marcado vigente al corte

No hay altas nuevas en este corte. La tabla conserva lo que ya estaba marcado y permite ver, para cada tarea, la fecha y la evidencia que la sostiene.

| ID | Tarea del `.mmd` | `at` | Evidencia |
|---|---|---|---|
| s0a | Entorno local mínimo con Ollama user-local y script Python sin framework web | 2026-07-06 | `.claude/persistence.md`: Ollama user-local restaurado y `llama3.2:3b` descargado. |
| s0b | Conectar Google Workspace y credenciales OAuth2 | 2026-09-28 | `notas/workspace-live-d2-2026-09-28.md`: cuenta técnica dedicada, scopes y lectura de la carpeta autorizada. El mecanismo definitivo (cuenta de servicio, #98) está implementado offline desde el 2026-10-14; su instalación en el host sigue en #99. |
| s0c | Esqueleto del proyecto Python, repo y logging básico | 2026-07-10 | Suite del Agente 1 en `Implementacion/Agente1/tests/`; logging básico verificado en la regresión. |
| m0 | Entorno mínimo listo para construir el MVP | 2026-07-10 | Entorno offline suficiente. Workspace live quedó fuera de este hito y se resolvió después (DEF-A1-001, `notas/workspace-live-d2-2026-09-28.md`). |
| s1a | Diseñar prompt y pipeline Python de gacetilla, sin LangGraph | 2026-07-15 | Pipeline offline y plantilla `gacetilla_v3`, que decide la línea de lugar por caso y cierra DEF-A1-014 (`evidencias/correccion-gacetillas-lugar-ausente-2026-09-08.md`). |
| s1b | Integrar lectura de datos desde Google Sheets | 2026-09-28 | `notas/workspace-live-d2-2026-09-28.md`: lectura real de la planilla sintética D2, con negativos live sin tocar la red. |
| s1d | Probar gacetillas con datos completos e incompletos | 2026-09-08 | `evidencias/matriz-conformidad-hu010-2026-07-20.md` y `tests/test_matriz_hu010.py`: 6/6 borradores y cuatro casos negativos de lugar tras DEF-A1-014. |
| s1c | Aplicar plantilla institucional y salida en Google Docs | 2026-10-19 | Forma FIE INFORMA aprobada como referencia de formato y estructura (Brief SEU 19/10); salida a Docs live 28/09. El archivo de plantilla en Docs es sintético; la revisión de muestras es s1e. |
| s2a | Criterios de canal por tono, longitud y hashtags | 2026-08-07 | Commit `537402a`; DEF-A1-004 `RESUELTO_TECNICO`. |
| s2b | Prototipo de post para Instagram y LinkedIn | 2026-08-12 | Commit `537402a`; DEF-A1-004. |
| s2c | Control de longitud y limpieza de la salida | 2026-08-14 | Commit `537402a`; DEF-A1-004. |
| s3c | Consolidar persistencia JSONL y cerrar spike PostgreSQL validado, sin driver ni integración operativa | 2026-08-26 | `evidencias/validacion-migraciones-postgresql-0003-2026-08-26.md`: migraciones 0001 a 0003, rechazos de timestamps futuros, rollback y forward en PostgreSQL 16 efímero. |
| s3d | Capa de secretos y logging con correlation ID | 2026-08-26 | Regresión local de logging seguro con correlation ID, hashes y versiones; `evidencias/auditoria-seguridad-d2-d3.md` documenta los límites de la evidencia offline. |
| s3b | Gestionar validadores SEU y criterios definitivos de canal | 2026-09-22 | Acta del 22/09: roles nominales y criterios por canal confirmados; la revisión de muestras es s1e/s2d. |
| s4a | Modelar datos y puerto de confirmación, sin endpoint web | 2026-08-26 | `src/agente1/confirmaciones.py` y `tests/test_confirmaciones.py`; contrato y puerto local de HU-012. |
| s4b | Lógica de idempotencia con clave única en registro | 2026-09-08 | Issue #9 y `evidencias/recuperacion-hu012-idempotencia-durable-2026-09-08.md`: `RegistroConfirmacionesArchivo` y reconciliación de reservas colgadas, con 18 pruebas nuevas. |
| s4c | Plantilla provisional y puerto de entrega, sin correo live | 2026-08-26 | `src/agente1/destinos.py`: puerto de entrega fake. Gmail quedó habilitado con lista de prueba (#40/#41); el modo producción existe desde #141 pero no está habilitado. La plantilla institucional sigue bloqueada (DEF-A1-002). |
| s4d | Tarea de envío asíncrona propia, sin Celery/Redis, y registro en base | 2026-09-21 | Merge `feature/s4d-envio-asincrono`; 28 pruebas nuevas. La cola durable es `ColaEnviosArchivo`; el "registro en base" del `.mmd` no se interpreta como PostgreSQL operativo, que sigue diferido (s3c y Plan de Recuperación). |
| s5b | Módulo Python de interpretación con LLM local, sin LangGraph | 2026-09-09 | `src/agente1/interpretacion.py`; issues #19 a #26; suite de 588 a 749 pruebas. |
| s5c | Fallback fuera de alcance y persistir derivado estructurado, sin prosa | 2026-09-09 | Issues #25 y #26; `tests/test_interpretacion.py`; la pendiente guarda solo orden, id, título y fecha de cada candidata, la intención y el vencimiento. |
| s5a | Chat interno con autenticación de personal SEU | 2026-10-20 | El canal es el Form de pedidos con correo verificado por Google y rol por padrón (ADR 0005), no un chat; el `.mmd` conserva el nombre legado. El padrón queda provisional. |
| s6a | Plantilla de certificado y máquina de estados HITL | 2026-09-21 | Issue #29, merge `feature/hu014-certificados`; `src/agente1/certificados.py`. El 2026-10-19 llegó la plantilla institucional de aprobación (#126), pero no está integrada; la variante de asistencia sigue pendiente. |
| s6b | Generación de PDF con datos académicos | 2026-09-21 | `src/agente1/certificados.py` y `tests/test_certificados.py`: PDF determinista con stdlib, marcas de borrador y bytes reproducibles. |
| s6c | Bloqueo sin aprobación y cola de aprobación al validador | 2026-09-21 | `src/agente1/certificados.py` y `tests/test_certificados_emision.py`: emisión bloqueada sin las dos aprobaciones; destino `DestinoCertificadosFake`. |
| s6d | Probar datos faltantes, rechazo y emisión controlada | 2026-09-21 | `tests/test_matriz_hu014.py`: matriz de conformidad HU-014, 12 casos y 62 pruebas nuevas. |
| s6e | Registro de emisión, logs y evidencia | 2026-09-21 | `evidencias/recorrido-emision-certificados-hu014.md` y `evidencias/limites-hu014-offline.md`: `pdf_hash`, reconciliación de `EMISION_RESERVADA` y límites documentados. |
| m7 | Suite de pruebas en verde y cobertura registrada | 2026-10-20 | Suite local 2377 passed / 8 skipped; cobertura 90 % registrada; CI de main verde en el run `39455797467` (`f2dfbf6`). |

## 4. Lo NO marcado al corte

Esta es la tabla que revisa Juani. Las frases son borradores para decir en voz alta; no agregan datos que la evidencia no sostenga.

| ID | Tarea del `.mmd` | Por qué | Frase para la presentación |
|---|---|---|---|
| s1e | Validar gacetillas con la SEU | **Bloqueada por la SEU.** DEF-A1-005 `BLOQUEADO_EXTERNO`. El paquete de nueve muestras está listo desde el 2026-09-22; JOS-P5 sigue pendiente y el 2026-10-19 no hubo revisión con Juan Manuel. | "El paquete de muestras está listo desde septiembre; la revisión de la SEU sigue pendiente." |
| m1 | HU-010 operativa con DoD | **Pendiente.** El DoD de HU-010 incluye la validación SEU de las muestras (s1e); la forma FIE INFORMA y la salida a Docs ya están. | "HU-010 está resuelta en lo técnico; el hito espera la validación de la SEU." |
| s2d | Validar posts con SEU y ajustar prompts | **Bloqueada por la SEU.** Los criterios por canal se confirmaron e implementaron el 2026-09-22 (DEF-A1-007 `EN_CORRECCION`); la revisión de muestras (DEF-A1-005) sigue pendiente. El 2026-10-19 no hubo revisión. | "Los criterios de las redes están confirmados y ya están en el código; falta la revisión de las muestras." |
| m2 | MVP HU-010 y HU-011 con evidencia - Gate TRL 3 | **Bloqueada por otro tercero y por la SEU.** Falta el criterio formal del Gate G2 (DEF-A1-006 `BLOQUEADO_EXTERNO`, a cargo de Cicerchia) y la validación de la SEU. | "El Gate TRL 3 no lo puedo declarar sin el criterio formal del profesor y sin la validación de la SEU." |
| s3a | Gestionar Workspace live, OAuth y recursos D2/D3 con DSI | **Bloqueada por otro tercero (DSI).** D2 está provisionado y verificado live desde el 2026-09-28. El servidor de la facultad corre como host de cómputo desde el 19/10 y la carpeta compartida de trabajo se usa como plano de archivos: eso se declara **D3 provisional**. La unidad institucional de D3 (#100), el aval formal y el host institucional siguen abiertos (#63, #64 y #119). | "D3 provisional: el servidor y la carpeta compartida ya se usan; la unidad institucional sigue pendiente." |
| m3 | Bloqueantes gestionados y base técnica consolidada, sin infraestructura diferida | **Pendiente.** Depende de s3a; s3b está completo desde el 22/09. | "Depende de cerrar D3." |
| s4e | Probar duplicados, destinatario inválido y validar SEU | **Bloqueada por la SEU.** Duplicados y destinatario inválido están probados; falta la validación SEU del mismo ítem. El 2026-10-19 no hubo validación. El issue #125 cambia la aprobación a una sola persona y requiere adaptación. | "La parte técnica de confirmaciones está probada; falta la validación de la SEU." |
| m4 | HU-012 operativa con DoD | **Pendiente.** El adapter Gmail existe con lista de prueba y modo producción (#141); lo que falta es que los renderers compongan el cuerpo de la plantilla aprobada por tipo y la lista real de la SEU. | "El adapter existe; falta la plantilla aprobada y la lista real." |
| s5d | Regresión de solicitudes y prueba guiada de usabilidad con SEU | **Bloqueada por la SEU.** La prueba guiada con Juan Manuel estaba agendada para el 2026-09-25 y no se hizo; JOS-P4 sigue pendiente y no hay fecha nueva. La regresión automatizable de #19 a #26 sí existe. | "La prueba guiada con Juan Manuel estaba para el 25 de septiembre y no se hizo; hay que reagendarla." |
| m5 | HU-013 operativa con DoD | **Pendiente.** Depende de s5d; s5a está completo con el canal Form. | "Depende de la prueba guiada." |
| m6 | HU-014 operativa con DoD | **Pendiente y bloqueada por la SEU en la validación.** El slice offline está hecho (s6a a s6e). La plantilla de aprobación llegó el 2026-10-19 (#126), pero no está integrada; faltan la variante de asistencia, el aprobador final del lote y la validación humana. | "HU-014 está completa en lo técnico; la plantilla llegó el 19 de octubre, falta integrarla y validar el lote." |
| s7a | Definir contratos y mocks con A2-A5 sin orquestar | **Pendiente.** Hay contratos y mocks para A3 a A5 y un puerto A2 con fakes, pero el contrato con Historia Viva (#17) sigue abierto; no cubre A2-A5 completo. | "Los contratos con A3 a A5 y el mock de A2 están; el contrato con Historia Viva sigue abierto." |
| s7b | Integrar insumos disponibles de A2-A5 progresivo | **Pendiente.** Depende de s7a y del contrato #17. | "La integración con A2 a A5 depende de cerrar ese contrato." |
| s7c | Pruebas unitarias, integración y E2E | **Pendiente.** Hay suite amplia y un E2E D2 del 2026-09-28, y la suite y el CI de main están verdes (run `39455797467`), pero la corrida E2E en el servidor de la demo (#118) todavía no está versionada. | "Tenemos suite y un E2E en D2, pero el CI está en rojo y el E2E en el servidor de la demo no corrió." |
| s7d | Probar seguridad, permisos y prompt injection | **Pendiente.** La auditoría de seguridad D2/D3 y las pruebas de prompt injection son offline; permisos y revocación reales siguen pendientes. | "La seguridad está auditada offline; permisos y revocación reales todavía no se probaron." |
| c1 | Validar con usuarios SEU, checklist 1-4 y trazabilidad | **Bloqueada por la SEU.** No hay sesión de validación agendada; JOS-D5 registra que nadie de la SEU asistirá al 18/11. | "La validación con usuarios de la SEU no tiene fecha, y para el 18 de noviembre la SEU nos dijo que no va a asistir." |
| c2 | Cerrar defectos críticos y regresión completa | **Pendiente.** No hay defectos `CRITICA` abiertos, pero hay defectos `ALTA` bloqueados. | "No hay defectos críticos abiertos, pero hay defectos altos bloqueados." |
| c3 | Release candidata y paquete de evidencias | **Pendiente.** El tag `agente1-v0.1.0` existe, pero al corte no hay release candidate con paquete de evidencias cerrado. | "Todavía no hay release candidate con el paquete de evidencias cerrado." |
| c4 | Auditoría go/no-go e informe de avance final | **Pendiente.** Depende de c1 a c3. | "Depende de la validación y de la release." |
| m8 | Gate TRL 4 validado y cierre del año | **Pendiente.** Depende de c1 a c4 y del Gate TRL 4. | "El Gate TRL 4 depende del cierre completo." |

No queda ninguna tarea reformulada sin marcar. La única reformulación del período es s5c, que ya está marcada.

## 5. Verificación ejecutada

| Comprobación | Resultado |
|---|---|
| `node --check Documentos/Gantt/gantt-progreso.js` | Sin errores. |
| `uv run pytest -q` en `Implementacion/Agente1`, 2026-10-19 | 2282 passed, 8 skipped en 63,42 s. |
| Test que falla en CI, corrido localmente el 2026-10-19 | `tests/test_gmail_envio.py::test_envio_real_post_a_gmail_send_con_mime_completo`: 1 passed en 0,44 s. |
| Run de CI `39302694001`, 2026-10-19 | 1 failed, 2284 passed, 5 skipped; cobertura 90 %. El fallo es el mismo test de Gmail, por un espacio inicial en un header MIME. El CI usó Python 3.12.3; la corrida local usó Python 3.12.14. No se investigó más la diferencia en este ticket. |
| `git diff -- Documentos/Gantt/diagrama-gantt-implementacion-semanal.mmd` | Vacío: el plan no se tocó. |

## 6. Observaciones para Juani

1. **El 20/10 se marcaron s1c, s3b, s5a y m7.** La forma FIE INFORMA está aprobada, los roles y criterios del 22/09 están confirmados, el canal interno es el Form con correo verificado (no un chat) y el CI de main está verde en el run `39455797467`.
2. **El plan queda intacto.** El `.mmd` conserva sus fechas y sus IDs. Lo que cambia es solo la lectura del avance en `gantt-progreso.js` y este informe.
2. **La visita del 19/10 no cerró validaciones.** Aportó definiciones (aprobación única, lotes de pagos, remitente, calendario, plantilla de certificado), pero no reemplaza la revisión de muestras ni la prueba guiada. Por eso s1e, s2d, s4e, s5d y c1 siguen sin marca.
3. **La plantilla de certificado llegó, pero no alcanza para m6.** La ficha de la SEU dice expresamente que recibir el archivo no demuestra que el renderer lo use ni habilita la emisión institucional. Falta integrarla (#126), definir la variante de asistencia y designar quién aprueba el lote.
4. **El CI es el único rojo del corte.** La suite local pasa y el test de Gmail pasa localmente; el run de CI falla por una diferencia de entorno en Python 3.12.3. No se marca m7 para no declarar "suite en verde" con el check requerido en rojo. Si se corrige antes del miércoles, m7 y s7c se pueden revisar, pero eso requiere un commit de código y no entra en este ticket.
5. **El "registro en base" de s4d** se sostiene con la cola durable en archivo. PostgreSQL operativo sigue diferido por decisión (s3c y Plan de Recuperación). Si la cátedra pregunta, conviene decirlo así y no presentar PostgreSQL como si estuviera en operación.
