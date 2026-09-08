# Plan de estados - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del estado del proyecto y plan de estados de desarrollo  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-09-06

## 1. Proposito

Este documento consolida una evaluacion del proyecto de desarrollo del Agente 1 y define un plan de estados para controlar su avance. El objetivo es evitar que el proyecto avance por declaraciones generales y asegurar que cada cambio de estado quede respaldado por evidencia verificable: proceso BPM, historia de usuario, Definition of Done, TRL, responsable, validacion humana y registro documental.

El plan complementa el anteproyecto, los casos de uso, el diagrama de clases, el Gantt, el plan de calidad, el plan de riesgos, el plan de comunicaciones y el plan de auditoria. No reemplaza esos documentos ni modifica el alcance institucional del Proyecto Centenario.

## 2. Fuentes consultadas

- `CLAUDE.md`
- `.claude/persistence.md`
- `Agentes/extension_bot_experto.md`
- `Agentes/arquitectura_multiagente_experto.md`
- `Agentes/evaluador_cicerchia.md`
- `Agentes/documentacion_sistemas_experto.md`
- `Contenido/Definicion/arquitectura-multiagente.md`
- `Contenido/Definicion/criterios-evaluacion-cicerchia.md`
- `Contenido/bible/README.md`
- `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`
- `Contenido/bible/Procesos y Agentes.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/DiagramaClases/Diagrama-Clases-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanComunicaciones/Plan-Comunicaciones-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanAuditoria/Plan-Auditoria-Agente-1-PPS-Juan-Ignacio-Gone.md`

Tambien se integraron tres lecturas read-only realizadas por subagentes: estado documental y brechas, arquitectura/evaluacion/seguridad, y estrategia de verificacion por estados.

## 3. Evaluacion sintetica

**Veredicto:** APROBADO CON OBSERVACIONES.

El proyecto es viable y defendible si permanece acotado al Agente 1 como agente de comunicacion institucional del Proceso 4. La documentacion vigente ya contiene una base solida: alcance, exclusiones, historias HU-010 a HU-014, casos de uso, matriz de trazabilidad, arquitectura, TRL, seguridad, validacion humana, metricas, cronograma, planes de calidad, riesgos, comunicaciones y auditoria.

Las observaciones principales son operativas:

1. El anteproyecto esta redactado y el alcance esta bien delimitado, pero aun debe validarse formalmente contra la bible, criterios Cicerchia y lineamientos de catedra.
2. Las fechas oficiales, personas nominales, disponibilidad de SEU, plantillas definitivas, campos finales de Google Sheets y entorno tecnico real siguen pendientes de confirmacion.
3. TRL 3 y TRL 4 no deben declararse por avance documental: requieren outputs, pruebas, logs, checklist SEU, evidencia recuperable, defectos gestionados y acta o informe de gate.
4. HU-013 debe mantenerse con el criterio vigente: interaccion interna iniciada por email con invitacion a chat y registro operativo en Google Sheets. En el backlog fuente aparece una formulacion antigua como "prompt en Sheet o Doc"; debe tratarse como inconsistencia documental a resolver antes de cerrar trazabilidad.
5. La integracion con A2-A5 debe permanecer como recepcion de insumos, no como orquestacion ni absorcion de responsabilidades ajenas.

## 4. Estado actual asignado

**Estado recomendado al 2026-09-06:** `E3 - MVP controlado S1` en entorno offline, con preparacion parcial de `E4 - Gate G2 / TRL 3`.

Justificacion:

- El alcance, backlog y controles transversales estan documentados.
- Existen artefactos de casos de uso, clases, Gantt, calidad, riesgos, comunicaciones y auditoria.
- Existe implementacion tecnica ejecutable, outputs offline de HU-010/HU-011, logs y una regresion integral canónica de 534 pruebas verdes, según el corte del 2026-09-08 (`a2c33b1`). Las 513 del corte documental del 2026-09-06 quedan como referencia histórica.
- La evidencia sigue siendo local/offline: no acredita Workspace live ni validacion SEU. Por lo tanto, el proyecto no debe declararse en `E4 - Gate G2 / TRL 3 cerrado`.

## 5. Plan de estados del proyecto

| Estado | Nombre | Entrada minima | Salida / DoD del estado | TRL | Evidencia requerida | Responsable principal |
|---|---|---|---|---:|---|---|
| E0 | Alcance consolidado | Fuentes base disponibles; foco Juan Ignacio Gone + A1 confirmado | A1 acotado a comunicacion institucional; exclusiones documentadas; HU-010 a HU-014 identificadas | 2-3 | Matriz BPM-HU-DoD-responsable; nota de alcance; riesgos iniciales | Juan Ignacio Gone / Director |
| E1 | Diseno validable | E0 cerrado; perfiles expertos y anteproyecto disponibles | Casos de uso, estados, flujo HITL, trazabilidad, seguridad, roles y criterios por HU definidos | 3 | Casos de uso, diagrama de clases, plan calidad, plan riesgos, checklist seguridad | Juan Ignacio Gone |
| E2 | Preparado para MVP controlado | Campos minimos, plantillas S1, validadores y esquema de log definidos o simulados formalmente | HU-010/HU-011 listas para implementacion y prueba controlada; bloqueos conocidos | 3 | Diccionario Sheets, plantillas versionadas, prompt versionado, plan de pruebas S1 | Juan Ignacio Gone + SEU |
| E3 | MVP controlado S1 | E2 cerrado; entorno local o sandbox disponible | HU-010 y HU-011 generan borradores desde datos de prueba; nada se publica sin validacion | 3 | Google Doc, borrador RRSS, logs, checklist SEU, medicion < 30 s, defectos | Juan Ignacio Gone / Responsable tecnico IA |
| E4 | Gate G2 - TRL 3 cerrado | E3 ejecutado con muestra minima | Caso simple validado en entorno controlado; sin defectos criticos; evidencia completa | 3 | Paquete G2, outputs, logs, checklist, informe S1, matriz actualizada | Director / SEU |
| E5 | Automatizacion S2 candidata | G2 cerrado; base S1 estable | HU-012, HU-013 y HU-014 operativas en entorno real limitado o sandbox institucional | 4 | Email de prueba, transcript/captura, PDF, registros en Sheets/PostgreSQL, pruebas seguridad | Juan Ignacio Gone / Responsable tecnico IA |
| E6 | Gate G4 - TRL 4 cerrado | HU-010 a HU-014 candidatas; usuarios SEU disponibles | Validacion con usuarios reales internos; checklist >= 3/4; logs operativos; 0 defectos criticos | 4 | Acta TRL 4, reporte pruebas, indice evidencias, registro defectos cerrado, informe final | Director / Coordinador Extension |
| E7 | Continuidad P100 | Cierre del alcance directo del PPS de Gone | Integracion progresiva con A2-A5, operacion real, metricas sostenidas | 5-6 | Evidencia de uso real, metricas de impacto, contratos A2-A5, operacion sostenida | P100 / SEU |

**Regla:** E7 no es compromiso directo del PPS de Juan Ignacio Gone salvo que el Director lo redefina formalmente. Debe presentarse como continuidad del P100.

## 6. Estados de historias de usuario

Estos estados se aplican a HU-010 a HU-014 y a controles transversales como validacion humana, trazabilidad y seguridad.

| Estado HU | Significado | Puede entrar si... | Puede salir si... | Evidencia minima |
|---|---|---|---|---|
| H0 - Pendiente de definicion | La HU existe, pero faltan datos criticos | Figura en backlog o anteproyecto | Tiene BPM, responsable, datos minimos, DoD y pruebas definidas | Ficha HU / caso de uso |
| H1 - Preparada | Lista para iniciar implementacion o spike | Estan definidos alcance, plantilla/datos, validador y riesgos | Se inicia desarrollo, spike o prueba controlada | Checklist de preparacion |
| H2 - En implementacion | Hay trabajo tecnico o documental activo | H1 aprobado | Hay salida candidata para prueba | Commit, version, nota de avance o evidencia tecnica |
| H3 - En prueba tecnica | La HU produce resultado ejecutable o simulable | Salida candidata disponible | Pasa pruebas tecnicas y no tiene defectos criticos | Reporte de pruebas, log, captura/output |
| H4 - En validacion SEU | La salida fue probada tecnicamente y requiere juicio humano | H3 aprobado | SEU aprueba, observa o rechaza | Checklist, acta, estado en Sheet |
| H5 - Cerrada por DoD | La HU cumple DoD global y especifico | H4 aprobado y evidencia completa | Se incluye en gate o release | Matriz DoD, evidencia indexada |
| H6 - Observada / retrabajo | La HU no cumple calidad, dato, tono, seguridad o evidencia | Defecto u observacion registrada | Defecto corregido y reprueba ejecutada | Registro defecto, accion correctiva |
| H7 - Bloqueada | No puede avanzar por dependencia, alcance o decision externa | Falta validacion, entorno, plantilla, permiso o dato critico | Se elimina bloqueo o se replanifica | Registro de bloqueo y responsable |
| H8 - Diferida / fuera de alcance | La funcionalidad no pertenece al estado actual | Es S3/S4, otro agente o no esta autorizada | Director la aprueba como cambio formal | Nota de alcance o backlog P100 |

## 7. Estado inicial recomendado por HU

| HU / Control | Estado inicial recomendado | Motivo | Proxima accion |
|---|---|---|---|
| HU-010 Gacetillas | H1 - Preparada parcial | SEU comunicó que no hay plantilla oficial; existe nota institucional candidata y roles de revisión/aprobación diferenciados, pero faltan activos aprobados, checklist completado y evidencia real | Co-diseñar formato con activos/reglas SEU y ejecutar sesión de validación |
| HU-011 Posts RRSS | H1 - Preparada parcial | Existe referente nominal para revisar borradores y ayudar a definir criterios; aún faltan guía de tono/longitud/hashtags, acta y muestra validada | Definir criterios por canal y realizar sesión de nueve muestras |
| HU-012 Confirmaciones | H1 - Contrato candidato por origen | v1 offline probado; v2 clasifica SIU Guaraní, SIU Guaraní de Extensión y Google Forms, pero faltan matriz operativa, permisos, trigger y política de envío | Confirmar matriz origen/tipo/estado/campos y autorización de cada envío |
| HU-013 Lenguaje natural interno | H0/H1 - Definicion con inconsistencia documental | El criterio vigente es email + invitacion a chat + registro en Sheets; hay formulacion antigua en fuente backlog | Resolver trazabilidad textual y definir canal inicial |
| HU-014 Certificados | H0 - Pendiente de definicion operativa | Requiere plantilla, datos academicos validados, aprobacion previa y log de emision | Definir plantilla, responsables y control de emision |
| HITL / Validacion humana | H1 - Preparada parcial | Esta definida como obligatoria, pero falta instrumento operativo final | Crear checklist y acta/registro por tipo de pieza |
| Trazabilidad / logs | H0/H1 - Definicion avanzada | Se exige evidencia, pero falta esquema ejecutable de correlation ID y campos de log | Definir formato log S1 y nomenclatura de evidencias |
| Seguridad base | H0/H1 - Definicion avanzada | Hay criterios de seguridad, pero faltan pruebas adversariales y matriz de permisos | Crear checklist seguridad y casos prompt injection |

## 8. Estados de solicitud y pieza generada

El diagrama de clases ya modela estados de solicitud que deben respetarse durante la implementacion. Este plan los usa como maquina de estados funcional minima:

| Estado | Descripcion | Transicion permitida |
|---|---|---|
| RECIBIDA | La solicitud ingreso por Sheets, Forms, Gmail, chat interno o insumo A2-A5 | A INCOMPLETA o EN_PROCESO |
| INCOMPLETA | Faltan datos minimos o fuente verificable | A RECIBIDA si se corrige; a RECHAZADA si no corresponde |
| EN_PROCESO | El agente esta validando datos, generando o armando salida | A BORRADOR o FALLIDA |
| BORRADOR | Existe una pieza generada no oficial | A PENDIENTE_VALIDACION |
| PENDIENTE_VALIDACION | La salida espera revision humana | A APROBADA, OBSERVADA o RECHAZADA |
| APROBADA | La salida fue aceptada por responsable humano | Puede pasar a publicacion, envio o emision por canal institucional |
| OBSERVADA | Requiere correccion antes de aprobar | A EN_PROCESO o BORRADOR tras retrabajo |
| RECHAZADA | No debe usarse como comunicacion oficial | Cierre con log y motivo |
| FALLIDA | Hubo error tecnico o de datos | A EN_PROCESO tras correccion o cierre con defecto |

Reglas no negociables:

1. Ninguna pieza oficial puede publicarse, enviarse o emitirse si no esta en estado `APROBADA`.
2. Todo cambio a `APROBADA`, `OBSERVADA`, `RECHAZADA` o `FALLIDA` debe registrar responsable, fecha, motivo y evidencia.
3. `INCOMPLETA` no debe completarse con informacion inventada por el LLM.
4. `FALLIDA` o `OBSERVADA` no bloquean necesariamente el proyecto, pero si bloquean el cierre de la HU hasta que exista retrabajo o decision formal.

## 9. Gates y bloqueantes

| Gate | Bloquea si... | No bloquea si... |
|---|---|---|
| G0 Alcance | A1 absorbe scraping, analitica, chatbot publico, dashboards, soporte general u orquestacion | La funcion se registra como insumo recibido desde A2-A5 o backlog P100 |
| G1 Diseno | Faltan DoD, responsable, datos minimos, estado, evidencia o control HITL para una HU | Hay pendiente menor documentado con responsable y no afecta MVP |
| G2 TRL 3 | HU-010/HU-011 no tienen outputs, logs, checklist, defectos y validacion controlada | La muestra usa datos de prueba, si se declara explicitamente |
| G3 Automatizacion | HU-012/HU-013 no tienen registros de envio/interaccion o fallan controles de seguridad | La integracion A2-A5 completa se posterga sin afectar A1 core |
| G4 TRL 4 | No hay usuarios SEU, checklist >= 3/4, logs, pruebas o 0 defectos criticos | Hay defectos medios/bajos con plan aceptado y sin riesgo institucional |

## 10. Indicadores de avance por estado

| Indicador | Formula / medicion | Umbral sugerido |
|---|---|---|
| Avance HU | HU en H5 / HU planificadas del gate | 100% de HU criticas del gate |
| Evidencia completa | Acciones con evidencia completa / acciones auditadas | 100% para cierre de gate |
| Validacion humana | Piezas oficiales aprobadas / piezas oficiales publicadas, enviadas o emitidas | 100% |
| Defectos criticos | Cantidad de defectos criticos abiertos | 0 |
| Calidad SEU | Promedio checklist 1-4 | >= 3/4 |
| Rendimiento | Tiempo trigger -> salida | < 30 s para contenido, salvo excepcion documentada |
| Trazabilidad | Solicitudes con correlation ID y enlaces / solicitudes auditadas | 100% en S2 |

## 11. Acciones inmediatas

| Prioridad | Accion | Estado que habilita | Responsable |
|---|---|---|---|
| P0 | Crear checklist SEU por tipo de pieza y formato de acta/registro | E2, H4, G2 | Juan Ignacio Gone + SEU |
| P0 | Definir esquema minimo de Google Sheets y correlation ID para S1 | E2, H1 | Juan Ignacio Gone / Responsable tecnico IA |
| P0 | Cerrar plantillas S1 para gacetilla y post RRSS | E2, HU-010, HU-011 | SEU / Responsable Gestion del Conocimiento |
| P0 | Unificar la formulacion de HU-013 en toda la trazabilidad documental | E1, H0/H1 HU-013 | Juan Ignacio Gone |
| P1 | Ejecutar spike tecnico con Ollama/FastAPI/Google Workspace o sandbox equivalente | E3 | Responsable tecnico IA |
| P1 | Definir registro de defectos y evidencia con nomenclatura estable | G2/G4 | Juan Ignacio Gone |
| P1 | Medir baseline manual de gacetilla/post antes de prometer reduccion cuantitativa | Metricas S1/S2 | Juan Ignacio Gone + SEU |
| P1 | Definir contratos minimos de insumos A2-A5 para S2 | E5 | Responsable tecnico IA / pares P100 |

## 12. Criterio de cierre

El proyecto puede considerarse correctamente encauzado si, antes de cerrar cada gate, existe una matriz actualizada que responda por cada HU:

- a que proceso BPM mapea;
- que historia y caso de uso cubre;
- que estado tiene;
- que DoD aplica;
- que evidencia existe;
- quien valida;
- que TRL pretende demostrar;
- que riesgos siguen abiertos;
- que defectos bloquean o no bloquean el cierre.

Sin esa matriz y sin evidencia recuperable, el avance debe tratarse como `en progreso`, no como `completado`.
