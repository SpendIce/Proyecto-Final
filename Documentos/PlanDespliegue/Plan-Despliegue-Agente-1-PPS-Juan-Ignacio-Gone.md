# Plan de despliegue - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del proyecto de desarrollo y plan de despliegue  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-05-18

## 1. Proposito

Este documento formaliza el plan de despliegue del Agente 1, Extension Bot, para el primer ano academico del Proyecto de Juan Ignacio Gone. Su objetivo es transformar el alcance funcional, los casos de uso, el plan de calidad, el plan de riesgos, el plan de comunicaciones, el plan de auditoria y el plan de estados en una estrategia operativa de puesta en marcha.

El plan no declara que el sistema ya este implementado. Define como debe desplegarse, bajo que condiciones puede avanzar de entorno, que evidencias debe producir, que roles deben intervenir y que situaciones bloquean la liberacion academica o tecnica.

El criterio rector es que el Agente 1 se despliega por etapas: primero como prototipo controlado, luego como piloto interno limitado y solo despues como componente integrable del Proyecto Centenario. No se recomienda conversion directa ni publicacion/envio institucional real sin validacion humana registrada.

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
- `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`
- `Contenido/bible/Procesos y Agentes.md`
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`
- `Contenido/Campus/INDEX.md`
- `Contenido/Campus/DSI1/_md/unidad-vi.md`
- `Contenido/Campus/DSI1/_md/unidad-vii.md`
- `Contenido/Campus/DSI2/_md/06-control-de-proyecto.md`
- `Contenido/Campus/DSI2/_md/07-indicadores.md`
- `Contenido/Campus/DSI2/_md/08-riesgos.md`
- `Contenido/Campus/DSI2/_md/09-calidad.md`
- `Contenido/Campus/DSI2/_md/10-liberacion.md`
- `Contenido/Campus/DSI2/_md/11-auditoria.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/DiagramaClases/Diagrama-Clases-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanComunicaciones/Plan-Comunicaciones-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanAuditoria/Plan-Auditoria-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanEstados/Plan-Estados-Agente-1-PPS-Juan-Ignacio-Gone.md`

Tambien se integraron lecturas read-only realizadas por subagentes sobre alcance, seguridad, verificacion, riesgos y evidencia de despliegue.

## 3. Alcance del despliegue

### 3.1 Incluido

El plan cubre el despliegue del Agente 1 durante S1 y S2 del primer ano academico:

| Periodo | TRL objetivo | Historias | Alcance de despliegue |
|---|---:|---|---|
| S1 | TRL 3 | HU-010, HU-011 | Prototipo controlado para generacion de gacetillas y posts desde datos estructurados, con salidas en borrador y validacion humana registrada. |
| S2 | TRL 4 | HU-012, HU-013, HU-014 | Piloto interno limitado con confirmaciones, interaccion interna por email + invitacion a chat, certificados, persistencia/logs y validacion con usuarios SEU. |

Tambien incluye controles transversales:

- validacion humana obligatoria;
- trazabilidad y evidencia CONEAU;
- seguridad desde el principio;
- permisos minimos;
- gestion de defectos;
- criterios de go/no-go por gate;
- rollback o fallback operativo;
- integracion inicial con A2-A5 solo como recepcion de insumos.

### 3.2 Excluido

Este plan no habilita:

- scraping, analitica, KPIs o dashboards como responsabilidad del Agente 1;
- atencion masiva al publico general o chatbot publico;
- orquestacion funcional del sistema multiagente;
- soporte administrativo general no asignado formalmente;
- publicacion, envio oficial o emision de certificados sin validacion humana;
- integraciones externas complejas no definidas;
- uso de APIs externas con datos reales sin aprobacion, anonimizacion y registro;
- S3/S4 como compromiso directo del PPS actual.

## 4. Evaluacion sintetica

**Veredicto:** APROBADO CON OBSERVACIONES FUERTES.

El despliegue del Agente 1 es viable si se ejecuta como piloto progresivo, con controles de calidad, evidencia y seguridad desde la primera iteracion. El riesgo principal no esta en la generacion de texto por IA, sino en liberar funciones sin validacion humana, sin trazabilidad reconstruible o con permisos excesivos sobre Google Workspace.

El proyecto no debe saltar directamente a operacion real. Debe avanzar por gates:

1. alcance validado;
2. diseno validable;
3. prototipo controlado TRL 3;
4. automatizacion interna S2;
5. release candidata TRL 4;
6. continuidad P100 fuera del alcance directo del PPS.

## 5. Principios de despliegue

1. **Piloto antes que produccion:** toda funcionalidad se prueba primero en entorno controlado con datos de prueba o muestra acotada.
2. **Human-in-the-loop no negociable:** ninguna salida oficial se publica, envia o emite sin aprobacion humana registrada.
3. **Google Workspace como plataforma base:** Sheets, Drive, Docs, Gmail, Forms y Apps Script son la interfaz institucional principal.
4. **Inferencia local como base:** Ollama y modelos locales son el camino principal para preservar soberania de datos.
5. **Bajo costo y reversibilidad:** priorizar software open source, infraestructura local y fallback manual documentado.
6. **Trazabilidad desde S1:** cada solicitud debe poder reconstruirse por ID, fuente, version, output, estado, validador y evidencia.
7. **Seguridad como condicion de release:** permisos, secretos, prompt injection, logs y acciones de alto impacto deben estar controlados antes de cada gate.
8. **A1 como hub de contenido, no orquestador:** puede recibir insumos de A2-A5, pero no absorbe sus responsabilidades ni coordina el sistema completo.

## 6. Modelo de entornos

| Entorno | Proposito | Datos permitidos | Salidas permitidas | Gate asociado |
|---|---|---|---|---|
| D0 - Documental | Alinear alcance, requisitos, riesgos y despliegue | Fuentes del repo | Documentos, matrices, planes | G0/G1 |
| D1 - Desarrollo local | Construir componentes y pruebas unitarias | Datos sinteticos o anonimizados | Archivos locales, logs de prueba | G1 |
| D2 - Sandbox Workspace | Probar integracion con Google Workspace no productivo | Datos de prueba o muestra autorizada | Docs, Sheets, emails de prueba | G2 |
| D3 - Piloto SEU controlado | Validar uso interno limitado | Datos reales acotados y autorizados | Borradores y evidencias, no publicacion automatica | G2/G3 |
| D4 - Release candidata TRL 4 | Validar flujo completo con usuarios internos | Datos reales limitados | Borradores, emails/certificados bajo reglas aprobadas | G4 |
| D5 - Operacion P100 | Continuidad posterior al PPS | Datos reales bajo gobernanza institucional | Operacion real controlada | G5/G6, fuera del PPS actual |

Regla: si un entorno no tiene responsable, permisos, logs y rollback definidos, no puede usarse para validar un gate TRL.

## 7. Arquitectura de despliegue prevista

La arquitectura de despliegue debe mantener separadas la interfaz institucional, el backend del agente, el motor LLM, la persistencia y la aprobacion humana.

```text
Google Forms / Sheets / Gmail / Drive
        |
        v
Google Apps Script / trigger tecnico
        |
        v
FastAPI - capa backend A1
        |
        +--> Validacion de entrada / esquema / permisos
        +--> LangChain - prompts versionados
        +--> Ollama - LLM local
        +--> PostgreSQL o Sheets - logs y estado
        +--> Celery + Redis - tareas asincronas S2
        |
        v
Google Docs / borradores / emails de prueba / PDF
        |
        v
Validacion humana SEU
        |
        v
Publicacion, envio o emision solo si estado = APROBADA
```

Apps Script actua como orquestador tecnico de triggers, no como agente central. El Agente 1 conserva su rol funcional de generacion y gestion de contenido institucional.

## 8. Fases de despliegue

| Fase | Nombre | Actividades principales | Salida |
|---|---|---|---|
| F0 | Preparacion documental | Validar alcance, exclusiones, HU, RACI, dependencias HU-001/HU-002 y fuentes | Matriz BPM-HU-DoD-responsable |
| F1 | Preparacion tecnica S1 | Definir esquema Sheets, plantillas S1, prompts, estructura de logs, permisos minimos | Entorno D1/D2 preparado |
| F2 | Prototipo TRL 3 | Ejecutar HU-010/HU-011 en sandbox; generar gacetilla y posts; medir tiempo; validar con SEU | Paquete G2 |
| F3 | Endurecimiento S1 | Corregir defectos, ajustar prompts, cerrar checklist, consolidar evidencia y baseline manual | MVP controlado estable |
| F4 | Automatizacion S2 | Incorporar HU-012/HU-013/HU-014, triggers, Gmail, PDFs, persistencia, colas y seguridad ampliada | Version candidata interna |
| F5 | Validacion TRL 4 | Pruebas de sistema, seguridad, regresion, usuarios reales SEU y paquete de release | Acta G4 / TRL 4 |
| F6 | Transferencia y continuidad | Manual breve, capacitacion, pendientes, contratos A2-A5 y lecciones aprendidas | Cierre PPS + backlog P100 |

## 9. Gates de despliegue

| Gate | Entrada | Validaciones obligatorias | Salida | Bloquea si... |
|---|---|---|---|---|
| G0 - Alcance | Fuentes disponibles | BPM, exclusiones, HU, dependencias, RACI por rol | Alcance congelado para S1 | A1 absorbe A4/A5, scraping, analitica, soporte general u orquestacion |
| G1 - Diseno validable | Casos de uso y arquitectura | plantillas, prompts, logs, estados, seguridad, roles, pruebas | Entorno listo para MVP controlado | faltan datos minimos, validador, DoD o evidencia por HU |
| G2 - TRL 3 | HU-010/HU-011 candidatas | prueba funcional, integracion Sheets-Docs, contenido, rendimiento, HITL, trazabilidad | MVP S1 validado en entorno controlado | no hay output, log, checklist o validacion humana |
| G3 - Automatizacion S2 | Base S1 estable | HU-012/HU-013, triggers, Gmail, registros, permisos y errores | piloto interno S2 preparado | hay duplicados, logs incompletos o envio sin aprobacion/regla preaprobada |
| G4 - TRL 4 | HU-010..HU-014 candidatas | sistema completo, seguridad, regresion, aceptacion SEU, auditoria, release | prototipo validado en entorno real limitado | defectos criticos, falta usuarios reales, trazabilidad incompleta o controles de seguridad no probados |
| G5/G6 - Continuidad | PPS cerrado | operacion real, integracion A2-A5, metricas sostenidas | P100 operativo | fuera del alcance PPS si no hay decision formal |

## 10. Criterios go/no-go

### 10.1 Go

Una version puede avanzar de entorno si cumple:

- HU incluidas con DoD global y especifico cumplido;
- pruebas criticas ejecutadas;
- 0 defectos criticos abiertos;
- validacion humana registrada cuando corresponde;
- logs con correlation ID o identificador equivalente;
- evidencia indexada;
- permisos minimos revisados;
- secretos fuera del codigo, logs y repositorio;
- plan de rollback o fallback definido;
- responsables institucionales por rol confirmados o suplentes documentados.

### 10.2 No-go

Debe bloquearse el despliegue si ocurre cualquiera de estas condiciones:

- cualquier ruta publica, envia o emite contenido generado por LLM sin aprobacion humana;
- una confirmacion automatica usa texto LLM no revisado en lugar de plantilla deterministica preaprobada;
- credenciales versionadas, hardcoded o expuestas en logs;
- service account con permisos amplios no justificados sobre Drive, Gmail o Sheets;
- falta de pruebas adversarias de prompt injection;
- uso de API externa con datos reales sin anonimizacion y aprobacion registrada;
- ausencia de logs reconstruibles para decisiones y outputs;
- falta de responsable institucional para validacion o incidentes;
- defectos criticos abiertos;
- intento de declarar TRL 3/4 solo con narrativa o demo sin paquete de evidencia.

## 11. Despliegue por historia

| HU | Entorno inicial | Condicion de activacion | Salida operativa | Control especifico |
|---|---|---|---|---|
| HU-010 Gacetillas | D2 Sandbox Workspace | Sheet con campos minimos y plantilla aprobada | Google Doc en borrador | No publicar sin `APROBADA`; checklist RGC/Coordinador |
| HU-011 Posts RRSS | D2 Sandbox Workspace | criterios IG/LinkedIn y guia de tono | borradores por canal | No publicar; validar longitud, tono y datos fuente |
| HU-012 Confirmaciones | D3 Piloto SEU controlado | plantilla deterministica preaprobada, control duplicados y log | email de confirmacion o email de prueba | Si hay LLM, debe quedar como borrador; no envio automatico |
| HU-013 Lenguaje natural interno | D3 Piloto SEU controlado | email de inicio, invitacion a chat, registro en Sheets | respuesta usable interna | No es chatbot publico; registrar transcript/captura |
| HU-014 Certificados | D4 Release candidata | plantilla aprobada, datos validados y responsable de emision | PDF generado | emision bloqueada hasta aprobacion humana |

## 12. Requisitos previos tecnicos

| Requisito | S1 | S2 | Evidencia |
|---|---|---|---|
| Google Drive/Sheets base | obligatorio | obligatorio | estructura de carpetas y planillas |
| Plantillas gacetilla/post | obligatorio | obligatorio | version y aprobacion SEU |
| Apps Script | minimo o simulado | obligatorio | script, trigger, permisos y logs |
| FastAPI backend | prototipo | estable para piloto | endpoint, configuracion no sensible |
| Ollama local | spike + prueba | base de inferencia | benchmark, modelo, version |
| LangChain/prompts | prototipo | versionado formal | prompt versionado y pruebas |
| PostgreSQL | opcional | recomendado/esperado | esquema logs/estado |
| Celery + Redis | opcional/inicial | recomendado si hay tareas asincronas | cola, idempotencia, DLQ o fallback |
| PyTest o equivalente | recomendado | obligatorio para release candidata | reporte de pruebas |
| Registro de defectos | obligatorio para G2 | obligatorio | planilla/issue con severidad |
| Indice de evidencias | obligatorio para G2 | obligatorio | links por HU/gate |

## 13. Seguridad de despliegue

| Control | Criterio minimo | Bloquea release |
|---|---|---|
| RBAC | roles administrador, validador, visualizador; solo validador aprueba | si |
| NHI / cuentas de servicio | identidad, propietario, scopes minimos, rotacion prevista | si |
| Secretos | `.env` fuera de git o Properties Service; sin claves en logs | si |
| PoLP | permisos acotados a carpetas, planillas y acciones necesarias | si |
| Prompt injection | sanitizacion, delimitadores, allowlist de acciones, casos adversariales | si |
| Salida del LLM | validacion antes de ejecutar acciones sobre Workspace | si |
| APIs externas | deny-by-default; solo contingencia aprobada, anonimizacion y registro | si |
| Logs | no secretos; append-only o control de integridad cuando sea posible | si para G4 |
| Rate limit / idempotencia | evitar duplicados y abuso de triggers/colas | si para HU-012/S2 |
| Kill switch | mecanismo para desactivar triggers/envios ante incidente | si para piloto S2 |

## 14. Human-in-the-loop y estados de salida

Los estados minimos de una pieza generada son:

| Estado | Significado | Puede avanzar a |
|---|---|---|
| BORRADOR | salida generada no oficial | PENDIENTE_VALIDACION |
| PENDIENTE_VALIDACION | requiere revision humana | APROBADA, OBSERVADA, RECHAZADA |
| APROBADA | validada por responsable humano | publicacion, envio o emision |
| OBSERVADA | requiere correccion | BORRADOR tras retrabajo |
| RECHAZADA | no puede usarse | cierre con motivo |
| FALLIDA | error tecnico o de datos | retrabajo o defecto |

Reglas:

1. `APROBADA` requiere usuario validador, fecha, rol, decision y evidencia.
2. `OBSERVADA`, `RECHAZADA` y `FALLIDA` requieren motivo.
3. El LLM no puede autoaprobar salidas ni modificar estados finales.
4. En HU-012, la confirmacion automatica solo puede enviarse sin revision caso a caso si usa plantilla preaprobada, datos validados y no contiene texto libre generado por LLM.

## 15. Plan de pruebas para despliegue

| Nivel | Objetivo | Casos minimos | Evidencia |
|---|---|---|---|
| Unidad | validar componentes aislados | validadores de campos, prompts, generacion de logs, estados | reporte PyTest o equivalente |
| Integracion | verificar colaboracion tecnica | Sheets -> backend -> Docs; Sheets -> Gmail; Drive -> PDF | log end-to-end y capturas |
| Sistema | validar flujo completo A1 | actividad -> borrador -> validacion -> estado final | output, checklist, registro |
| Seguridad | probar limites y abuso | prompt injection, credenciales, permisos, accion no autorizada | reporte seguridad y defectos |
| Rendimiento | medir generacion | pieza simple y pieza completa | tiempo < 30 s o excepcion |
| Regresion | proteger lo ya validado | HU-010/HU-011 tras cambios S2 | reporte de regresion |
| Aceptacion | decidir release | usuarios SEU, checklist, 0 defectos criticos | acta gate |

## 16. Paquete de release

Cada gate de despliegue debe producir un paquete con:

- version de codigo o prototipo, si existe;
- configuracion no sensible;
- plantillas usadas;
- prompts versionados;
- esquema de datos de Sheets/PostgreSQL;
- matriz BPM-HU-DoD-evidencia-responsable;
- casos de prueba ejecutados;
- reporte de defectos;
- outputs generados;
- logs y correlation IDs;
- checklist SEU;
- acta o informe de gate;
- manual breve de usuario/operacion;
- riesgos residuales;
- decision go/no-go.

Nomenclatura sugerida:

- `GATE-A1-G2-TRL3-YYYY-MM-DD`
- `GATE-A1-G4-TRL4-YYYY-MM-DD`
- `EVID-A1-SX-HU-XXX-YYYY-MM-DD-descripcion`
- `VAL-A1-SX-HU-XXX-YYYY-MM-DD-descripcion`
- `DEF-A1-SX-HU-XXX-YYYY-MM-DD-descripcion`

## 17. Operacion del piloto

### 17.1 Cadencia

| Momento | Actividad | Responsable | Evidencia |
|---|---|---|---|
| Antes de cada HU | revisar datos, plantilla, DoD, responsable y riesgos | Juan Ignacio Gone / SEU | checklist preparacion |
| Durante pruebas | ejecutar casos, medir tiempos, registrar errores | Responsable tecnico IA | reporte pruebas |
| Antes del gate | auditar evidencia, riesgos y defectos | Juan Ignacio Gone / Director | paquete gate |
| Despues del gate | registrar decision, pendientes y rebaseline | Juan Ignacio Gone | acta o informe |
| Ante incidente | activar kill switch/fallback, registrar causa y accion | Responsable tecnico IA / Coordinador | registro incidente |

### 17.2 Roles operativos

| Rol | Responsabilidad en despliegue |
|---|---|
| Juan Ignacio Gone | coordinar plan, ejecutar pruebas, mantener evidencia, informar avance |
| Director / Tutor | aprobar gates academicos, resolver alcance y prioridades |
| Coordinador de Extension | accountable funcional, validar pertinencia y autorizar uso institucional |
| Responsable Gestion del Conocimiento | validar tono, coherencia, exactitud y plantillas |
| Responsable RRSS | validar posts por canal |
| Personal SEU | cargar datos, probar uso interno, reportar observaciones |
| Responsable tecnico IA | mantener backend, permisos, logs, seguridad y entorno |
| Pares P100 / A2-A5 | acordar contratos de insumos hacia A1 |

## 18. Monitoreo e indicadores

| ID | Indicador | Umbral |
|---|---|---:|
| M1 | Tiempo de generacion | < 30 s por pieza |
| M2 | Validacion humana antes de publicar/enviar/emitir | 100% |
| M3 | Acciones con trazabilidad completa | 100% para G4 |
| M4 | Checklist SEU | >= 3/4 sin dimension critica menor a 3 |
| M5 | Defectos criticos abiertos | 0 para gate/release |
| M6 | Tasa de rechazo de contenido | <= 20% al cierre S2, sujeto a baseline |
| M7 | Eventos duplicados en HU-012 | 0 |
| M8 | Pruebas criticas ejecutadas | 100% de las planificadas para el gate |
| M9 | Controles de seguridad criticos | 100% antes de release candidata |
| M10 | Uso de API externa con PII | 0 |

## 19. Rollback, fallback y contingencia

| Situacion | Accion inmediata | Fallback | Evidencia |
|---|---|---|---|
| Fallo de trigger Apps Script | desactivar trigger y registrar incidente | ejecucion manual controlada | log, captura, defecto |
| Salida con alucinacion | rechazar pieza, bloquear publicacion y ajustar prompt | redaccion manual asistida | checklist y version prompt |
| Publicacion/envio indebido | activar kill switch, escalar a Coordinador/Director | comunicacion correctiva institucional | registro incidente |
| Token o credencial expuesta | revocar y rotar credencial | operar manualmente hasta recuperar seguridad | acta tecnica |
| Latencia > 30 s sostenida | medir causa, reducir modelo o usar cola | fallback manual; API externa solo aprobada y anonima | benchmark y decision |
| Falla de Redis/Celery | pausar colas, drenar tareas, revisar duplicados | ejecucion sin asincronia o manual | reporte tecnico |
| Datos incompletos en Sheets | marcar `INCOMPLETA`, pedir correccion | no generar contenido oficial | estado y log |
| Falta de validador SEU | bloquear aprobacion oficial | replanificar o usar suplente documentado | registro de bloqueo |

## 20. Trazabilidad de despliegue

| Elemento | Proceso BPM | HU / control | Gate | Evidencia minima | Responsable |
|---|---|---|---|---|---|
| Gacetillas | P4 | HU-010 | G2/G4 | Google Doc, log, checklist, aprobacion | RGC / Coordinador |
| Posts RRSS | P4 | HU-011 | G2/G4 | borrador IG/LinkedIn, log, checklist canal | RRSS / RGC |
| Confirmaciones | P5/P4 | HU-012 | G3/G4 | email, timestamp, no duplicado, log | Responsable cursos / SEU |
| Lenguaje natural interno | P4/P3 | HU-013 | G3/G4 | email, invitacion, transcript/captura, Sheet | Personal SEU / Coordinador |
| Certificados | P5 | HU-014 | G4 | PDF, aprobacion previa, log | Coordinador / Administracion |
| HITL | Transversal | CU-A1-06 | todos | estado, aprobador, fecha, motivo | Coordinador Extension |
| Trazabilidad | Transversal | CU-A1-07 | todos | correlation ID, output, log, evidencia | Responsable tecnico IA |
| Seguridad | Transversal | RNF seguridad | G1-G4 | checklist, permisos, pruebas adversariales | Responsable tecnico IA |
| TRL | Transversal | M5 / gates | G2/G4 | paquete gate, informe, acta | Director / Juan Ignacio Gone |

## 21. Checklist de despliegue

### 21.1 Checklist pre-G2 / TRL 3

- [ ] HU-010 y HU-011 tienen caso de uso, DoD y pruebas.
- [ ] Campos minimos de Sheets definidos.
- [ ] Plantillas S1 aprobadas o marcadas como version de prueba.
- [ ] Prompts versionados y revisados contra hallucinations.
- [ ] Google Docs de salida en carpeta controlada.
- [ ] Estados BORRADOR/PENDIENTE/APROBADA/RECHAZADA registrados.
- [ ] Checklist SEU disponible.
- [ ] Logs con ID, fecha, usuario, HU, output y estado.
- [ ] Pruebas de datos completos, incompletos y error tecnico.
- [ ] Medicion de tiempo de generacion.
- [ ] 0 defectos criticos abiertos.
- [ ] Paquete G2 indexado.

### 21.2 Checklist pre-G4 / TRL 4

- [ ] HU-010 a HU-014 ejecutadas o justificadas formalmente.
- [ ] HU-012 usa plantilla deterministica preaprobada o queda en borrador si usa LLM.
- [ ] HU-013 opera solo para uso interno via email + invitacion a chat.
- [ ] HU-014 no emite certificado sin aprobacion humana.
- [ ] PostgreSQL o registro robusto disponible para logs/estado.
- [ ] Pruebas de prompt injection ejecutadas.
- [ ] RBAC y permisos minimos revisados.
- [ ] Secretos fuera del repositorio y logs.
- [ ] Kill switch o mecanismo de desactivacion documentado.
- [ ] Usuarios SEU participaron en validacion.
- [ ] Checklist SEU >= 3/4.
- [ ] Trazabilidad completa en muestra auditada.
- [ ] 0 defectos criticos abiertos.
- [ ] Manual breve de uso/operacion disponible.
- [ ] Paquete G4 indexado y aprobado.

## 22. Acciones inmediatas recomendadas

| Prioridad | Accion | Habilita | Responsable | Fecha objetivo sugerida |
|---|---|---|---|---|
| P0 | Crear `Checklist-Validacion-SEU-Agente-1.md` | G2/G4 | Juan Ignacio Gone + SEU | Antes de G2 |
| P0 | Crear `Registro-Defectos-Agente-1.md` | calidad y release | Juan Ignacio Gone | Antes de G2 |
| P0 | Crear `Indice-Evidencias-Agente-1.md` | auditoria CONEAU | Juan Ignacio Gone | Antes de G2 |
| P0 | Definir esquema minimo de log y correlation ID | trazabilidad | Responsable tecnico IA | Antes de prototipo HU-010/HU-011 |
| P0 | Confirmar plantillas y campos minimos S1 | MVP controlado | SEU / Juan Ignacio Gone | Antes de TRL 3 |
| P1 | Preparar casos adversariales de prompt injection | seguridad | Responsable tecnico IA | Antes de G2/G4 |
| P1 | Ejecutar spike Ollama/FastAPI/Workspace y benchmark | viabilidad tecnica | Responsable tecnico IA | Durante S1 |
| P1 | Definir contratos de insumos A2-A5 | integracion S2 | Pares P100 / Responsable tecnico IA | Antes de S2 |
| P1 | Medir baseline manual gacetilla/post | beneficios | Juan Ignacio Gone + SEU | Antes de reportar mejora |

## 23. Pendientes de confirmacion

- Fechas oficiales de entrega, defensa y gates academicos.
- Personas nominales para Coordinador, Responsable Gestion del Conocimiento, Responsable RRSS, responsables de cursos, administracion y soporte tecnico.
- Plantillas institucionales definitivas de gacetilla, post, mail, newsletter y certificado.
- Campos exactos, validaciones y permisos de Google Sheets.
- Entorno real disponible para Ollama, FastAPI, Apps Script, Gmail, Drive, PostgreSQL, Celery y Redis.
- Herramienta final de registro de defectos y evidencias: Google Sheets, Jira, repositorio Markdown u otra.
- Umbral formal de cobertura de pruebas si la catedra o SEU exige uno distinto.
- Criterio de muestra para validacion con usuarios reales de la SEU.
- Politica institucional final sobre uso excepcional de APIs externas.

## 24. Criterio de cierre del plan

El plan de despliegue queda completo a nivel documental cuando:

1. esta alineado con alcance, casos de uso, calidad, riesgos, comunicaciones, auditoria, estados y Gantt;
2. no agrega funcionalidades fuera del Agente 1;
3. define entornos, fases, gates, bloqueantes, roles, pruebas, seguridad, evidencia y rollback;
4. distingue TRL 3 controlado de TRL 4 interno real limitado;
5. marca pendientes sin inventar datos institucionales;
6. permite que un evaluador reconstruya como se pasa de documentacion a piloto y de piloto a release candidata.

El despliegue tecnico real solo puede considerarse cerrado cuando existan outputs, logs, checklist, pruebas, defectos gestionados, evidencia indexada y aprobacion formal del gate correspondiente.
