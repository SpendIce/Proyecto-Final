# Plan de riesgos - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del proyecto de desarrollo y plan de riesgos  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-09-23

## 1. Proposito

Este documento evalua los riesgos del proyecto de desarrollo del Agente 1, Extension Bot, y define un plan operativo de mitigacion, contingencia y seguimiento. El plan se apoya en la documentacion vigente del repositorio, los criterios de evaluacion del Proyecto Centenario, los artefactos ya producidos para el Agente 1 y el enfoque de gestion de riesgos de DSI2.

El objetivo no es demostrar que el proyecto no tiene riesgos, sino mostrar que los riesgos principales estan identificados, priorizados, asignados a responsables, vinculados con BPM/HU/DoD/TRL y convertidos en controles verificables.

## 2. Fuentes consultadas

- `CLAUDE.md` y `AGENTS.md`
- `.claude/persistence.md`
- `Agentes/extension_bot_experto.md`
- `Agentes/arquitectura_multiagente_experto.md`
- `Agentes/evaluador_cicerchia.md`
- `Agentes/documentacion_sistemas_experto.md`
- `Contenido/Definicion/arquitectura-multiagente.md`
- `Contenido/Definicion/criterios-evaluacion-cicerchia.md`
- `Contenido/bible/README.md`
- `Contenido/bible/Procesos y Agentes.md`
- `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`
- `Contenido/Campus/INDEX.md`
- `Contenido/Campus/DSI2/_md/08-riesgos.md`
- `Contenido/Campus/DSI2/_md/09-calidad.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/DiagramaClases/Diagrama-Clases-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/Gantt/diagrama-gantt-agente-1.mmd`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`

Tambien se integraron tres lecturas read-only realizadas por subagentes: alcance y gobernanza; arquitectura y seguridad; anteproyecto, calidad, cronograma y evidencias.

## 3. Alcance evaluado

1. El alcance evaluado corresponde al Agente 1 durante el primer ano academico 2026, hasta TRL 4.
2. El Semestre 1 cubre el MVP: HU-010 generacion de gacetillas y HU-011 generacion de posts para redes sociales.
3. El Semestre 2 incorpora HU-012 notificaciones automaticas (la version del 2026-09-22 la amplio a inscripcion, participacion, situacion de pagos y aprobacion), HU-013 interaccion interna iniciada por email con invitacion a chat y HU-014 certificados con validacion humana.
4. S3 y S4 de 2027 se consideran continuidad del P100 completo, no compromiso actual del PPS de Juan Ignacio Gone.
5. HU-015 en su lectura de certificados/triggers por evento, HU-016 (BD de consultas con clasificacion semantica) y HU-017 (Disposiciones Decanales) quedan fuera de este alcance por decision de Direccion (issue #34, comunicada el 2026-09-30): se delegan a los alumnos de cuarto ano que continuaran el P100, al igual que cualquier historia nueva posterior a HU-014. Las ampliaciones de HU-010..HU-014 —como la de HU-012 citada en el punto 3— si forman parte de este alcance.
6. El Agente 1 se mantiene dentro del Proceso 4 - Comunicacion y Difusion Institucional. Puede recibir insumos de A2, A3, A4 y A5, pero no es orquestador, no hace scraping, no hace analitica, no construye dashboards, no atiende masivamente al publico y no reemplaza personal.

## 4. Evaluacion sintetica del proyecto

**Veredicto:** APROBADO CON OBSERVACIONES FUERTES.

El proyecto es viable y defendible si se mantiene como agente de comunicacion institucional acotado al Proceso 4 y si cada avance se prueba con evidencia. El mayor riesgo no es la generacion de texto por IA, sino llegar a los gates TRL con documentacion correcta pero sin instrumentos operativos: checklist de validacion, logs, evidencias, plantillas aprobadas, contratos de datos y responsables confirmados.

El premortem del proyecto muestra tres escenarios criticos:

1. **Fracaso mas probable:** el proyecto llega a G2/G4 con prototipos que funcionan, pero sin evidencia suficiente para demostrar TRL, aceptacion SEU y trazabilidad CONEAU.
2. **Fracaso mas peligroso:** se publica, envia o emite una pieza institucional sin validacion humana registrada, generando dano reputacional, incumplimiento de alcance y bloqueo academico.
3. **Supuesto oculto principal:** que la SEU, las plantillas institucionales, el entorno Google Workspace y el hardware local estaran disponibles en las fechas previstas sin necesidad de replanificacion.

## 5. Metodo de evaluacion

Se adopta una escala simple, consistente con el material DSI2 de gestion de riesgos:

| Valor | Probabilidad | Impacto |
|---:|---|---|
| 1 | Baja: poco probable | Bajo: efecto menor, no bloquea gate |
| 2 | Media: posible | Medio: retrabajo, atraso o degradacion parcial |
| 3 | Alta: muy posible o casi seguro | Alto: bloquea gate, afecta defensa, calidad, seguridad o alcance |

**Exposicion = Probabilidad x Impacto.**

| Exposicion | Nivel | Politica |
|---:|---|---|
| 1-3 | Bajo | Monitorear |
| 4 | Medio | Mitigar y revisar en reuniones de avance |
| 6-9 | Alto | Plan de mitigacion obligatorio, alarma y contingencia definida |

## 6. Registro de riesgos

| ID | Riesgo expresado como causa -> consecuencia | Cat. | P | I | Exp. | Nivel | Trazabilidad | Responsable primario |
|---|---|---|---:|---:|---:|---|---|---|
| R-ALC-01 | Mezcla de A1 con analitica, scraping, A4, A5 o soporte general -> expansion indebida del alcance y perdida de defendibilidad | Alcance | 2 | 3 | 6 | Alto | P4, HU-010 a HU-014, exclusiones | Juan Ignacio Gone / Director |
| R-ALC-02 | Newsletters, correos o comunicaciones externas quedan redactados como alcance independiente sin HU especifica -> sobrepromesa funcional | Alcance | 2 | 2 | 4 | Medio | P4, HU-010, HU-011, HU-012 | Juan Ignacio Gone |
| R-ALC-03 | La SEU o Direccion amplia HU existentes o incorpora HU/requisitos nuevos durante la ejecucion -> crecimiento del alcance del PPS, retrabajo y presion sobre el cierre de noviembre | Alcance | 3 | 3 | 9 | Alto | HU-010 a HU-014, matriz de alcance, issues #33/#34 | Juan Ignacio Gone / Director |
| R-ALC-04 | La continuidad del P100 en S3/S4 de 2027 se confunde con compromiso del PPS -> presion de alcance fuera del contrato academico | Alcance | 1 | 2 | 2 | Bajo | Anteproyecto, alcance evaluado, matriz de alcance | Juan Ignacio Gone |
| R-GOB-01 | Responsables de validacion no confirmados -> aprobaciones informales o imposibles de auditar | Gobernanza | 3 | 3 | 9 | Alto | P4/P5, CU-A1-06, DoD validacion | Coordinador de Extension |
| R-GOB-02 | Responsables nominales siguen pendientes aun con rol suplente -> aprobaciones firmadas por suplente en gates | Gobernanza | 2 | 1 | 2 | Bajo | CU-A1-06, RACI, checklist de validacion | Coordinador de Extension |
| R-HITL-01 | El flujo human-in-the-loop no queda bloqueado tecnicamente -> publicacion, envio o emision sin aprobacion humana | Seguridad/calidad | 2 | 3 | 6 | Alto | HU-010, HU-011, HU-014, RNF autonomia | Responsable Tecnico IA |
| R-REQ-01 | Campos de Sheets, plantillas y usuarios nominales quedan pendientes -> requisitos inestables y pruebas no concluyentes | Requisitos | 3 | 3 | 9 | Alto | HU-010 a HU-014, CU-A1-01 a CU-A1-05 | Juan Ignacio Gone + SEU |
| R-CRO-01 | Hitos y fechas difieren entre anteproyecto, plan mensual y Gantt -> baseline debil para gates TRL | Cronograma | 3 | 2 | 6 | Alto | Gantt, H3/H5/H6, TRL 3/4 | Juan Ignacio Gone |
| R-CRO-02 | S2 concentra backend, automatizaciones, persistencia, colas, integracion y pruebas -> poco margen de retrabajo antes de diciembre 2026 | Cronograma | 2 | 3 | 6 | Alto | HU-012, HU-013, HU-014, Gate TRL 4 | Juan Ignacio Gone / Responsable Tecnico IA |
| R-DAT-01 | Sheets opera como bus sin esquema cerrado, IDs ni validaciones -> duplicados, datos incompletos o contenido incorrecto | Datos | 3 | 3 | 9 | Alto | HU-010 a HU-014, DoD datos | Responsable Tecnico IA |
| R-DAT-02 | El MVP valida con datos de prueba o muestra acotada -> la validacion no representa el uso real | Datos | 2 | 1 | 2 | Bajo | DoD datos, gate TRL 3 | Juan Ignacio Gone + SEU |
| R-LLM-01 | Prompts, RAG o modelo local generan alucinaciones o tono inadecuado -> comunicacion institucional incorrecta | IA/calidad | 3 | 3 | 9 | Alto | HU-010, HU-011, HU-013 | Responsable Gestion del Conocimiento |
| R-SEG-01 | Entradas externas, documentos o mails inducen prompt injection -> salida manipulada o accion indebida | Seguridad | 2 | 3 | 6 | Alto | HU-013, RNF seguridad, HITL | Responsable Tecnico IA |
| R-SEG-02 | Credenciales, permisos o logs exponen informacion sensible -> incumplimiento de seguridad y Ley 25.326 | Seguridad | 2 | 3 | 6 | Alto | Google Workspace, RBAC, logs | Responsable Tecnico IA |
| R-TRA-01 | No se correlacionan fila, prompt, plantilla, output, aprobador y version -> evidencia no auditable | Trazabilidad | 3 | 3 | 9 | Alto | CONEAU, DoD auditoria, TRL | Juan Ignacio Gone / Responsable Tecnico IA |
| R-TEC-01 | Ollama/hardware local no alcanza latencia o estabilidad esperada -> dependencia de API externa o incumplimiento de rendimiento | Tecnico | 2 | 3 | 6 | Alto | Stack local, RNF performance, TRL 3 | Responsable Tecnico IA |
| R-TEC-02 | La contingencia de API externa con datos anonimizados se vuelve dependencia transitoria -> procesamiento fuera del entorno local | Tecnico | 1 | 2 | 2 | Bajo | RNF datos, decision de fallback | Responsable Tecnico IA |
| R-INT-01 | Cambios de permisos, cuotas o APIs de Google Workspace bloquean triggers -> interrupcion de flujos S1/S2 | Integracion | 2 | 2 | 4 | Medio | Sheets, Docs, Gmail, Apps Script | Responsable Tecnico IA |
| R-INT-02 | Contratos de datos A2-A5 no estan definidos -> A1 recibe insumos no normalizados o fuera de alcance | Integracion | 2 | 2 | 4 | Medio | A2->A1, A3->A1, A4->A1, A5->A1 | Responsable Tecnico IA / Pares P100 |
| R-ADOP-01 | Personal SEU no participa en codiseno y validacion -> baja adopcion, tono desalineado y TRL sin usuarios reales | Adopcion | 3 | 3 | 9 | Alto | P4, validacion SEU, checklist 1-4 | Coordinador de Extension |
| R-EVAL-01 | Se declaran metricas o mejoras sin baseline -> beneficios no demostrables ante evaluacion | Evaluacion | 3 | 2 | 6 | Alto | M3, M4, M5, evidencia TRL | Juan Ignacio Gone |
| R-CAL-01 | Checklist, registro de defectos e indice de evidencias no estan operativos -> retrabajo tardio y gates incompletos | Calidad | 3 | 3 | 9 | Alto | Plan de calidad, G2/G4 | Juan Ignacio Gone |

### 6.1 Correspondencia con la matriz oficial del P100 (bible sincronizada 2026-09-22)

La version vigente de `Contenido/bible/Procesos y Agentes.md` incorpora una matriz de riesgos de programa (R-01 a R-31, metodo PMBOK con disposicion ROAM). El registro local de arriba es el del PPS del Agente 1; esta tabla vincula ambos identificadores para que la lectura institucional y la del proyecto no diverjan. La correspondencia es orientativa: varios riesgos de la bible son de nivel programa (multi-equipo, presupuesto P100) y no bajan tal cual al registro del Agente 1.

| Riesgo local (PPS A1) | Riesgo(s) bible P100 | Comentario |
|---|---|---|
| R-ALC-01, R-ALC-02 | R-02, R-14 | Desviacion de alcance y sobre-documentacion |
| R-ALC-03 | R-02 | Expansion del backlog por el propio stakeholder durante la ejecucion; materializado el 22/09 con la ampliacion de HU-012 a cuatro tipos de notificacion, HU nuevas propuestas y el cambio de origen Forms -> SIU Guarani. Respuesta aplicada: exclusion provisional, fail-closed sobre datos DESCONOCIDO y escalamiento pendiente (issue #34) |
| R-GOB-01 | R-08 | Alineacion entre equipos/areas; los roles nominales quedaron confirmados el 22/09 (J. Manuel semantica, S. Moreira utilitaria/firma) |
| R-HITL-01 | R-19, R-27 | Autonomia sin control y acciones fuera de autorizacion |
| R-REQ-01 | R-16 | Requisitos/diseno no validados oficialmente |
| R-CRO-01, R-CRO-02 | R-03, R-15 | Dependencia entre fases y cronograma subestimado |
| R-DAT-01 | R-26 | Integridad de datos; R-26 agrega la lectura de fuga de PII |
| R-LLM-01 | R-19, R-24, R-07 | Alucinaciones/tono: expectativa del motor sin control, inyeccion indirecta via RAG y contenido que no cumple DoD |
| R-SEG-01 | R-23, R-24 | Spoofing e inyeccion de prompts (R-24 es el unico critico de la matriz bible) |
| R-SEG-02 | R-26, R-29 | Fuga de PII y credenciales hardcodeadas/compartidas |
| R-TRA-01 | R-25 | Repudio: imposibilidad de determinar error vs ataque |
| R-TEC-01 | R-18, R-31 | Inmadurez del stack IA local e inestabilidad de Ollama |
| R-INT-01 | R-10, R-11 | Dependencia de servicios cloud y demora de infraestructura |
| R-INT-02 | R-01, R-04 | Incompatibilidad de contratos A1<->A2..A5 y subestimacion de integracion |
| R-ADOP-01 | R-09 | Baja adopcion del personal de Extension |
| R-EVAL-01 | R-07 | Evidencia/DoD debil llegando a validacion |
| R-CAL-01 | R-06, R-07 | Identificacion incompleta de riesgos y DoD no cumplido en validacion |

Los riesgos aceptados (R-ALC-04, R-GOB-02, R-DAT-02, R-TEC-02) son decisiones locales del PPS sin equivalente en la matriz de programa de la bible.

Riesgos de la bible sin equivalente local directo (nivel programa, se registran aca para no perderlos): R-05 (costo de hardware especializado), R-12 (rotacion de estudiantes), R-13 (perfil insuficiente del equipo), R-17 (inmadurez del proceso multi-equipo), R-21 (respaldo institucional para escalar al Centenario), R-22 (apoyo politico sostenido), R-28 (poisoning de datos de entrenamiento/RAG — relevante si se adopta la opcion candidata de fine-tuning registrada el 22/09) y R-30 (saturacion por rafaga de solicitudes).

## 7. Planes de mitigacion y contingencia

| ID | Mitigacion preventiva | Alarma / disparador | Contingencia si ocurre | Evidencia de control |
|---|---|---|---|---|
| R-ALC-01 | Revisar backlog contra matriz BPM-HU-DoD en cada gate; rechazar tareas de A4/A5/scraping/analitica como alcance A1 | Nueva HU o texto de informe incorpora dashboards, scraping, atencion publica o orquestacion | Mover a backlog P100/A2-A5; dejar nota de exclusion y actualizar matriz de alcance | Matriz BPM-HU-DoD, acta de revision |
| R-ALC-02 | Redactar newsletters/correos como tipos de pieza derivados de HU existentes, no como HU nueva salvo aprobacion formal | Se pide medir cobertura de newsletter como entregable independiente | Reencuadrar como extension futura o salida de HU-010/HU-012 | Nota de alcance, backlog actualizado |
| R-ALC-03 | Mantener baseline de alcance por HU por gate; tratar toda HU/requisito nuevo o ampliacion como solicitud de cambio evaluada contra el cierre de noviembre, no como incorporacion automatica | Nueva version del backlog amplia una HU vigente, propone HU/requisitos nuevos o cambia un sistema origen de datos | Exclusion provisional documentada y fail-closed sobre datos DESCONOCIDO; absorber solo lo acotado al sprint vigente que no mueva el camino critico; el resto a backlog P100 con decision de Direccion | Nota de exclusion, issue de decision, matriz de alcance actualizada, acta de cambio |
| R-ALC-04 | Respuesta: ACEPTAR. La frontera PPS/continuidad ya esta declarada en el anteproyecto y en el alcance evaluado; basta mantener la nota de exclusion visible | Direccion pide comprometer entregables de 2027 dentro del PPS | Reabrir como riesgo activo y tramitar como solicitud de cambio formal | Nota de exclusion, matriz de alcance |
| R-GOB-01 | Confirmar roles por HU: Coordinador, Responsable Gestion del Conocimiento, RRSS, cursos, administracion y tecnico | Checklist sin responsable o aprobacion por chat sin registro | Bloquear validacion oficial hasta asignar rol suplente y registrar aprobacion | RACI por flujo, checklist firmado o registrado |
| R-GOB-02 | Respuesta: ACEPTAR condicionado a que exista rol suplente designado y aprobacion registrada por HU | Un gate queda sin aprobador disponible o el suplente deja de estar disponible | Reabrir como R-GOB-01 activo; bloquear el gate hasta la designacion | RACI, acta de designacion de suplente, checklist firmado |
| R-HITL-01 | Estados obligatorios: borrador, pendiente, aprobado, rechazado; bloquear publicar/enviar/emitir si no hay aprobacion | Hay boton, script o flujo que envia sin estado aprobado | Deshabilitar automatizacion, volver a flujo manual y registrar incidente | Log de estado, aprobador, fecha y version |
| R-REQ-01 | Cerrar G1 solo con campos minimos, plantillas versionadas, usuarios validadores y criterios de aceptacion por HU | Plantilla "pendiente", campos no definidos o validadores no asignados al iniciar implementacion | Implementar solo spike controlado; no declarar TRL hasta cerrar requisito | Plantilla, esquema Sheets, checklist HU |
| R-CRO-01 | Unificar tabla maestra de hitos entre anteproyecto, Gantt y plan mensual; registrar cambios de baseline | H3/H5/H6 o gates aparecen con fechas distintas | Emitir rebaseline documental y congelar fecha nueva | Version de Gantt, tabla de hitos, decision |
| R-CRO-02 | Reducir S2 a camino critico: HU-012/HU-013 antes de HU-014 si el margen se achica; reservar ventana de retrabajo | Al 2026-10-15 no hay HU-012/HU-013 operativas o logs activos | Postergar integracion A2-A5 completa y priorizar TRL 4 de A1 core | Burndown, reporte de avance, backlog recortado |
| R-DAT-01 | Definir esquema Sheets por HU con IDs, columnas obligatorias, validacion de tipos y estados | Columnas cambiadas manualmente, filas sin ID o datos incompletos recurrentes | Congelar hoja, restaurar estructura y cargar cola de correcciones manuales | Diccionario de datos, pruebas de validacion |
| R-DAT-02 | Respuesta: ACEPTAR condicionado a que el gate TRL 3 declare explicitamente la muestra acotada | Se pretende generalizar los resultados de la muestra a produccion o a validacion SEU | Reabrir como riesgo activo; exigir muestra ampliada o datos reales | Declaracion en paquete de gate, protocolo de muestra |
| R-LLM-01 | Versionar prompts y plantillas; separar instrucciones de datos; exigir fuente visible y checklist 1-4 | Rechazo de contenidos >20% o aparicion de datos no presentes en fuente | Volver a plantilla manual asistida y ajustar prompts antes de liberar | Version de prompt, salida, checklist, tasa de rechazo |
| R-SEG-01 | Sanitizar entradas, casos adversariales de prompt injection y aprobacion humana obligatoria | Entrada intenta alterar instrucciones, pedir secretos o forzar envio | Bloquear solicitud, registrar incidente y actualizar filtros/casos de prueba | Caso adversarial, log, defecto cerrado |
| R-SEG-02 | Minimo privilegio, secretos fuera del codigo, logs sin credenciales, RBAC por rol | Clave en repositorio/log o cuenta con permisos excesivos | Rotar credenciales, revocar permisos y auditar accesos | Checklist seguridad, inventario de credenciales |
| R-TRA-01 | Correlation ID por solicitud; log estructurado con input, output, validador, estado, version y evidencia | No se puede reconstruir una pieza generada de punta a punta | Rehacer registro desde evidencia disponible; bloquear gate si es sistemico | Muestra de trazabilidad, indice de evidencias |
| R-TEC-01 | Ejecutar spike de hardware/modelo local antes de prometer rendimiento; definir fallback aprobado y anonimizado | Latencia >30 s sostenida o caidas del entorno local | Reducir modelo/carga, usar cola asincrona o API externa solo como contingencia aprobada | Benchmark, reporte de entorno, decision de fallback |
| R-TEC-02 | Respuesta: ACEPTAR solo como contingencia aprobada, con anonimizacion y registro de decision | Se procesan datos identificables en API externa o la contingencia se vuelve permanente | Revocar la contingencia, volver al entorno local y auditar los datos enviados | Decision de fallback registrada, anonimizacion verificada |
| R-INT-01 | Pruebas periodicas de Apps Script, cuotas, permisos y APIs; cuenta de servicio con permisos minimos | Trigger falla o Google cambia permisos/cuotas | Activar trigger manual/documentado y reconfigurar permisos | Log de prueba end-to-end, nota de incidencia |
| R-INT-02 | Definir contratos minimos de datos con A2-A5: campos, origen, estados, responsabilidad y validacion | A1 recibe texto/datos sin origen o incompatible con plantilla | Procesar como insumo manual no automatizado hasta normalizar contrato | Contrato de interfaz, ejemplo real |
| R-ADOP-01 | Agenda de validaciones SEU, roles suplentes, sesiones cortas de codiseno y walkthroughs | Validadores no responden o no asisten a dos hitos seguidos | Replanificar gate, usar muestra reducida y registrar falta de disponibilidad | Minutas, invitaciones, checklists |
| R-EVAL-01 | Medir baseline manual de gacetilla/post antes de declarar reduccion de tiempo; definir muestra y frecuencia | Metricas presentadas sin muestra o responsable | Reemplazar afirmacion cuantitativa por evidencia cualitativa hasta medir | Hoja baseline, protocolo de medicion |
| R-CAL-01 | Crear checklist SEU, registro de defectos e indice de evidencias antes de G2 | Evidencias por HU siguen "pendiente de ejecucion" en el gate | Bloquear gate, ejecutar pruebas criticas y generar paquete minimo de evidencia | Checklist, registro defectos, paquete G2/G4 |

## 8. Mapa de trazabilidad por foco de riesgo

| Foco | Proceso BPM | HU / requisito | DoD afectado | Evidencia minima | Responsable |
|---|---|---|---|---|---|
| Gacetillas | P4 | HU-010 | Sheet -> Google Doc, plantilla, <30 s, validacion humana | Documento generado, log, checklist | Responsable Gestion del Conocimiento / Coordinador |
| Posts RRSS | P4 | HU-011 | Canal adaptable, longitud configurable, texto limpio, validacion | Borrador por canal, log, checklist canal | Responsable RRSS / Responsable Gestion del Conocimiento |
| Confirmaciones | P5/P4 | HU-012 | Trigger, email, registro de envio | Email de prueba, timestamp, estado en Sheet | Responsable de cursos / Personal SEU |
| Lenguaje natural interno | P4/P3 | HU-013 | Email de inicio, invitacion a chat, registro de datos en Sheets | Captura/transcript, log, registro Sheet | Personal SEU / Coordinador |
| Certificados | P5 | HU-014 | Plantilla, PDF, aprobacion previa obligatoria | PDF, aprobacion manual, log | Coordinador / Administracion |
| Validacion humana | Transversal | CU-A1-06, RNF autonomia | No publicar/enviar/emitir sin aprobacion | Checklist, aprobador, fecha, observacion | Coordinador de Extension |
| Trazabilidad | Transversal | CU-A1-07, CONEAU | Accion reconstruible y evidencia recuperable | Correlation ID, log, indice de evidencia | Responsable Tecnico IA |
| Seguridad | Transversal | RNF seguridad | RBAC, secretos protegidos, prompt injection controlado | Checklist seguridad, pruebas adversariales | Responsable Tecnico IA |
| Madurez TRL | Transversal | Gate TRL 3/4 | Evidencia de funcionamiento y validacion real | Paquete G2/G4, acta, pruebas, outputs | Director del Proyecto / Juan Ignacio Gone |

## 9. Cadencia de seguimiento

| Momento | Actividad | Riesgos revisados | Salida esperada |
|---|---|---|---|
| Semanal durante implementacion | Revision de top 5 riesgos por exposicion | R-GOB-01, R-REQ-01, R-DAT-01, R-TRA-01, R-CAL-01 | Estado actualizado y acciones de 7 dias |
| Antes de iniciar cada HU | Revision de requisitos, datos, DoD y validadores | Riesgos de la HU afectada | Decision iniciar / bloquear / hacer spike |
| Antes de cada gate | Auditoria de evidencia y riesgos residuales | Todos los riesgos altos | Paquete de evidencia y decision de gate |
| Luego de un incidente | Reanalisis de probabilidad, impacto y contingencia | Riesgo materializado | Defecto, causa, accion correctiva y regresion |
| Cierre de S1 y S2 | Rebaseline y lecciones aprendidas | Cronograma, TRL, adopcion, calidad | Informe de avance/final con riesgos residuales |

## 10. Criterios de escalamiento

Un riesgo debe escalar al Director del Proyecto o tutor cuando ocurra cualquiera de estas condiciones:

1. exposicion igual o mayor a 6 y sin mitigacion asignada;
2. riesgo que bloquea validacion humana o trazabilidad;
3. cambio de alcance que incorpora funciones ajenas a A1 o que amplia/agrega HU y requisitos del propio A1;
4. ausencia de validadores SEU para un gate;
5. imposibilidad de demostrar TRL 3 o TRL 4 con evidencia;
6. necesidad de usar API externa con datos institucionales;
7. incidente de seguridad, credenciales o publicacion sin aprobacion.

## 11. Acciones inmediatas recomendadas

| Prioridad | Accion | Riesgos que reduce | Responsable | Fecha objetivo sugerida |
|---|---|---|---|---|
| P0 | Unificar baseline de cronograma entre anteproyecto, plan mensual y Gantt | R-CRO-01, R-CRO-02 | Juan Ignacio Gone | Antes del proximo gate documental |
| P0 | Crear checklist SEU por tipo de pieza y acta/registro de validacion | R-GOB-01, R-HITL-01, R-CAL-01 | Juan Ignacio Gone + SEU | Antes de G2 |
| P0 | Definir esquema minimo de logs y correlation ID para S1 | R-TRA-01, R-DAT-01 | Responsable Tecnico IA | Antes de prototipos HU-010/HU-011 |
| P0 | Cerrar campos minimos de Sheets y plantillas para HU-010/HU-011 | R-REQ-01, R-DAT-01, R-LLM-01 | Juan Ignacio Gone + SEU | Antes de declarar TRL 3 |
| P0 | Formalizar el control de cambios de alcance: toda HU/requisito nuevo o ampliacion entra como solicitud evaluada contra el cierre, con exclusion provisional como default | R-ALC-03, R-CRO-02 | Juan Ignacio Gone / Director | Inmediato; primer caso pendiente: issue #34 |
| P1 | Ejecutar spike de Ollama/modelo local y medir latencia con caso real | R-TEC-01 | Responsable Tecnico IA | Durante S1 |
| P1 | Registrar baseline manual de gacetilla/post y protocolo de medicion | R-EVAL-01 | Juan Ignacio Gone + SEU | Antes de medir beneficio |
| P1 | Definir casos adversariales de seguridad y prompt injection | R-SEG-01, R-SEG-02 | Responsable Tecnico IA | Antes de G2 |
| P1 | Documentar contratos minimos de insumos A2-A5 hacia A1 | R-INT-02, R-ALC-01 | Responsable Tecnico IA / Pares P100 | Antes de integracion S2 |

## 12. Riesgos residuales aceptables

Los riesgos aceptados estan registrados en la seccion 6 con su respuesta en la seccion 7: la aceptacion es una politica de manejo y no exime del registro, la trazabilidad ni la revision periodica. Son R-ALC-04, R-GOB-02, R-DAT-02 y R-TEC-02, todos con exposicion baja y aceptacion condicionada a que se mantengan las condiciones declaradas; si una condicion se rompe, el riesgo se reabre como activo.

No se consideran aceptables (lineas rojas, no riesgos):

- publicar, enviar o emitir contenido/certificados sin validacion humana registrada;
- declarar TRL 3/4 sin outputs, logs, checklist y evidencia recuperable;
- ampliar A1 hacia scraping, analitica, dashboards, atencion publica o soporte administrativo general;
- procesar datos sensibles en servicios externos sin aprobacion, anonimizacion y registro;
- cerrar un gate con defectos criticos abiertos.

## 13. Pendientes de confirmacion

- Fechas oficiales de entrega, defensa y gates academicos.
- Personas nominales para Coordinador, Responsable Gestion del Conocimiento, Responsable RRSS, validadores y soporte tecnico.
- Plantillas institucionales definitivas de gacetilla, post, mail, newsletter y certificado.
- Campos exactos y permisos de las planillas Google Sheets.
- Entorno real disponible para Ollama, FastAPI, Google Workspace, Apps Script y almacenamiento.
- Criterio de muestra para baseline manual y validaciones SEU.
- Herramienta final para registro de defectos, riesgos y evidencias: Google Sheets, Jira, repositorio Markdown u otra.

