# Plan de calidad - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del proyecto de desarrollo y plan de calidad  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-05-18

## 1. Proposito

Este documento evalua el proyecto de desarrollo del Agente 1 y define un plan de calidad operativo para su ejecucion. El plan consolida los criterios ya presentes en el anteproyecto, los perfiles expertos del repositorio, la bible institucional del Proyecto Centenario y los materiales de DSI1/DSI2 sobre calidad, pruebas, indicadores, riesgos, auditoria y liberacion.

El objetivo es que la calidad del Agente 1 no dependa de una declaracion general, sino de actividades verificables: revisiones, pruebas, metricas, evidencia, responsables, trazabilidad BPM/DoD/TRL y validacion formal con la Secretaria de Extension Universitaria.

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

## 3. Supuestos y alcance evaluado

1. El alcance evaluado es el desarrollo del Agente 1 durante el primer ano academico del Proyecto de Juan Ignacio Gone: Semestre 1 y Semestre 2, hasta TRL 4.
2. El Semestre 1 cubre el MVP del Agente 1: HU-010 generacion de gacetillas y HU-011 generacion de posts para redes sociales.
3. El Semestre 2 incorpora HU-012 confirmaciones automaticas, HU-013 interaccion interna en lenguaje natural y HU-014 certificados con validacion humana.
4. S3 y S4 se consideran proyeccion del P100 completo, no compromiso de alcance del PPS de Juan Ignacio Gone.
5. El Agente 1 pertenece principalmente al Proceso 4 - Comunicacion y Difusion Institucional. Puede dar soporte documental a P3, P5 y P6, pero no se transforma en orquestador, analitica, scraping, chatbot publico ni soporte administrativo general.
6. No se asumen fechas oficiales de entrega, personas nominales ni disponibilidad concreta de infraestructura institucional hasta que sean confirmadas.

## 4. Evaluacion sintetica del proyecto

**Veredicto:** APROBADO CON OBSERVACIONES.

El proyecto es viable y defendible si se mantiene acotado al Agente 1 como agente de comunicacion institucional. La base documental es consistente: el anteproyecto delimita alcance, historias, TRL, seguridad, metricas, trazabilidad y riesgos; los documentos de casos de uso, clases y Gantt refuerzan la transformacion del alcance en artefactos tecnicos verificables.

Las observaciones principales no invalidan el proyecto, pero deben convertirse en trabajo de calidad:

- La validacion humana esta correctamente definida, pero falta un instrumento operativo con checklist, acta, evidencia y criterio de cierre por HU.
- Las metricas existen, pero falta protocolo de medicion: linea base manual, muestra, frecuencia, responsable y formato de registro.
- La viabilidad tecnica esta argumentada, pero falta evidencia de prueba de hardware o entorno real disponible.
- La RACI general debe bajar a nivel de flujo de validacion, prueba, evidencia y liberacion.
- La proyeccion P100 S3/S4 debe mantenerse visible como continuidad, no como alcance actual del PPS.

## 5. Politica de calidad

Para este proyecto, calidad significa que cada funcionalidad del Agente 1:

1. pertenece al alcance autorizado del Agente 1;
2. mapea a un proceso BPM definido;
3. cumple su Definition of Done;
4. produce salidas institucionalmente correctas, sin informacion inventada y adaptadas al canal;
5. mantiene validacion humana obligatoria cuando la comunicacion sea oficial, publica, critica o certificante;
6. deja evidencia auditable: logs, outputs, checklist, aprobacion, rechazo u observacion;
7. respeta restricciones de bajo costo, soberania de datos, seguridad, credenciales protegidas y minimo privilegio;
8. alcanza el TRL objetivo con evidencia verificable, no solo con declaracion de intencion.

La calidad se gestionara preventivamente mediante revisiones tempranas de alcance, requisitos, plantillas, prompts, seguridad y arquitectura; y correctivamente mediante pruebas, registro de defectos, retrabajo controlado, medicion de indicadores y gates de liberacion.

## 6. Organizacion y responsabilidades

Los nombres propios quedan pendientes de confirmacion con la SEU. Hasta tanto se formalicen, se usan roles institucionales.

| Actividad de calidad | Responsable primario | Aprueba | Consultados | Evidencia |
|---|---|---|---|---|
| Validar alcance BPM y exclusiones | Juan Ignacio Gone / Responsable tecnico IA | Director del Proyecto | Coordinador de Extension, Responsable Gestion del Conocimiento | Matriz BPM-HU-DoD, acta o nota de alcance |
| Definir plantillas institucionales | Responsable Gestion del Conocimiento | Coordinador de Extension | Responsable RRSS, docentes responsables | Plantilla aprobada, version, ubicacion Drive |
| Revisar prompts y criterios anti-hallucination | Juan Ignacio Gone / Responsable tecnico IA | Coordinador de Extension | Responsable Gestion del Conocimiento | Checklist de prompt, casos de prueba, version |
| Validar gacetillas | Responsable Gestion del Conocimiento | Coordinador de Extension | Docente o coordinador de actividad | Checklist, Google Doc, log de validacion |
| Validar posts RRSS | Responsable RRSS | Coordinador de Extension | Responsable Gestion del Conocimiento | Borrador, checklist canal, log |
| Validar confirmaciones | Responsable de cursos / Personal SEU | Coordinador de Extension | Responsable tecnico IA | Email de prueba, registro de envio |
| Validar interaccion interna | Personal SEU | Coordinador de Extension | Responsable tecnico IA | Captura o transcript, registro en Sheets |
| Validar certificados | Coordinador de Extension / Administracion | Coordinador de Extension | Responsable de curso, Responsable tecnico IA | PDF generado, aprobacion manual, log |
| Gestionar defectos y pruebas | Juan Ignacio Gone / Responsable tecnico IA | Director del Proyecto | Usuarios validadores | Registro de defectos, reporte de pruebas |
| Autorizar release academica o tecnica | Director del Proyecto | Director del Proyecto | SEU, tutor, responsable tecnico | Acta, checklist gate TRL, paquete de evidencia |

## 7. Gates de calidad

| Gate | Momento | Criterio de entrada | Criterio de salida | Evidencia minima |
|---|---|---|---|---|
| G0 - Alcance validado | Inicio S1 | Fuentes base disponibles | A1 acotado a HU-010 a HU-014, exclusiones documentadas | Matriz alcance, backlog, riesgos iniciales |
| G1 - Diseno validable | S1 diseno | Casos de uso y arquitectura inicial | Plantillas, prompts, flujo HITL, logs y seguridad definidos | Casos de uso, diagrama de clases, checklist seguridad |
| G2 - TRL 3 | Cierre S1 | HU-010 y HU-011 implementadas en entorno controlado | Gacetilla y post generados sobre datos de prueba, validacion humana registrada | Outputs, logs, checklist SEU, reporte de defectos |
| G3 - Automatizacion S2 | Mitad S2 | Base S1 estable | HU-012 y HU-013 operativas, persistencia/logs activos | Emails de prueba, capturas, registros en Sheets/PostgreSQL |
| G4 - TRL 4 | Cierre S2 | HU-010 a HU-014 version candidata | Validacion con usuarios reales SEU, sin defectos criticos, documentacion minima | Acta gate TRL 4, reporte de pruebas, paquete de liberacion |

## 8. Aseguramiento de calidad

Las actividades de aseguramiento verifican que el proceso correcto se esta siguiendo antes de llegar a la prueba final.

| Actividad | Frecuencia | Aplica a | Criterio | Evidencia |
|---|---|---|---|---|
| Revision de alcance contra BPM | En cada gate | Todas las HU | La funcionalidad pertenece a P4/P3/P5/P6 segun alcance A1 y no invade A2-A5 | Matriz actualizada |
| Revision de DoD | Por HU antes de iniciar desarrollo | HU-010 a HU-014 | La HU tiene entrada, salida, validacion, log, evidencia y responsable | Checklist DoD |
| Walkthrough de requisitos | Antes de implementar cada HU | Casos de uso | Los flujos principales, alternativos y excepciones son comprensibles para usuario y tecnico | Minuta o acta |
| Inspeccion de plantillas | Antes de generar contenido oficial | Gacetillas, posts, emails, certificados | Plantilla aprobada, versionada y coherente con tono institucional | Plantilla versionada |
| Revision de prompts | Por iteracion de prompt | Generacion de contenido y LN | Instrucciones separadas de datos, restricciones anti-hallucination, formato de salida definido | Version de prompt, casos de prueba |
| Revision de seguridad base | Antes de cada release/gate | Stack tecnico | Credenciales fuera del codigo, permisos minimos, sanitizacion, logs sin secretos | Checklist seguridad |
| Auditoria documental interna | En G2 y G4 | Evidencia CONEAU | Las evidencias existen, son recuperables y trazan a HU/DoD/responsable | Indice de evidencia |

## 9. Control de calidad

El control de calidad mide resultados concretos y detecta defectos.

| Control | Objeto controlado | Metodo | Criterio de conformidad | Accion ante no conformidad |
|---|---|---|---|---|
| Prueba funcional por HU | Comportamiento visible | Casos de prueba caja negra | Cumple flujo principal y excepciones criticas | Registrar defecto y re-probar |
| Prueba de integracion | Sheets, Docs, Gmail, Drive, Apps Script/backend | Caso end-to-end | No hay perdida de datos ni estados inconsistentes | Bloquear gate afectado |
| Prueba de contenido | Gacetillas, posts, mails, certificados | Checklist SEU escala 1-4 | Puntaje >= 3 en precision, tono, plantilla y canal | Ajustar prompt/plantilla y revalidar |
| Prueba de rendimiento | Generacion de pieza | Medicion de tiempo | < 30 segundos por pieza, salvo excepcion documentada | Optimizar o activar contingencia aprobada |
| Prueba de seguridad | Entradas, credenciales, permisos, logs | Checklist y casos adversariales | No expone credenciales, respeta roles, no ejecuta acciones sin aprobacion | Corregir antes de release |
| Prueba de trazabilidad | Logs y evidencia | Muestreo de acciones | Accion reconstruible: quien, cuando, que, estado, evidencia | Completar registro y corregir logging |
| Validacion de usuario | Usuarios SEU | Checklist/entrevista | Resultado usable y aceptado o observado formalmente | Registrar observacion y retrabajo |

## 10. Estrategia de pruebas

La estrategia se organiza de menor a mayor integracion.

| Nivel | Objetivo | Ejemplos para A1 | Responsable | Evidencia |
|---|---|---|---|---|
| Unidad | Detectar defectos en componentes aislados | Validadores de campos, armado de prompts, parser de respuestas, generador de logs | Juan Ignacio Gone | Reporte PyTest o equivalente |
| Integracion | Verificar colaboracion entre componentes | Sheets -> backend -> Docs; Sheets -> Gmail; Drive -> plantilla -> PDF | Juan Ignacio Gone / Responsable tecnico IA | Log end-to-end, capturas, outputs |
| Sistema | Validar flujo completo del Agente 1 | Actividad -> contenido -> validacion -> estado final -> evidencia | Juan Ignacio Gone + SEU | Caso ejecutado, checklist, registro |
| Validacion | Confirmar utilidad institucional | Revision por Coordinador, Responsable Gestion del Conocimiento y RRSS | SEU | Acta/checklist escala 1-4 |
| Regresion | Evitar que correcciones rompan funcionalidades previas | Re-ejecutar casos criticos tras cambios de prompt, plantilla o integracion | Juan Ignacio Gone | Reporte de regresion |
| Seguridad | Confirmar limites de autonomia y control de acceso | Prompt injection, datos incompletos, accion no autorizada, credenciales | Juan Ignacio Gone / Responsable tecnico IA | Checklist seguridad, defectos |
| Aceptacion/liberacion | Decidir si la version candidata puede cerrar gate | Sin defectos criticos, evidencia completa, documentacion minima | Director del Proyecto + SEU | Acta de gate y paquete de liberacion |

## 11. Plan de pruebas por historia

| HU | Pruebas minimas | Evidencia de conformidad | Responsable de validacion |
|---|---|---|---|
| HU-010 Gacetillas | Datos completos, datos incompletos, plantilla ausente, generacion dentro de tiempo, validacion/rechazo | Google Doc, log, checklist de contenido, estado en Sheet | Responsable Gestion del Conocimiento / Coordinador |
| HU-011 Posts RRSS | Canal Instagram, canal LinkedIn, longitud configurable, rechazo por tono, hashtags/formato | Borrador por canal, checklist canal, log | Responsable RRSS / Responsable Gestion del Conocimiento |
| HU-012 Confirmaciones | Trigger por nueva inscripcion, email generado, duplicado evitado, error de destinatario | Email de prueba, log de envio, estado en Sheet | Responsable de cursos / Personal SEU |
| HU-013 Lenguaje natural interno | Email de inicio, invitacion a chat, solicitud valida, solicitud fuera de alcance, registro de datos | Captura/transcript, registro en Sheet, log | Personal SEU / Coordinador |
| HU-014 Certificados | Plantilla valida, datos faltantes, PDF generado, validacion previa, emision bloqueada sin aprobacion | PDF, aprobacion manual, log de certificado | Coordinador / Administracion |

## 12. Metricas de calidad

| ID | Metrica | Formula / medicion | Umbral | Frecuencia | Responsable |
|---|---|---|---|---|---|
| M1 | Tiempo de generacion | timestamp salida - timestamp trigger | < 30 s por pieza | Por ejecucion | Responsable tecnico IA |
| M2 | Validacion humana | piezas validadas / piezas publicadas o enviadas | 100% | Por release | Coordinador / SEU |
| M3 | Reduccion de tiempo manual | 1 - tiempo A1 / tiempo manual base | >= 50% al cierre S2, sujeto a baseline validada | G2/G4 | Juan Ignacio Gone + SEU |
| M4 | Satisfaccion SEU | promedio checklist 1-4 | >= 3/4 al cierre S2 | G2/G4 | Coordinador / validadores |
| M5 | Progresion TRL | cumple/no cumple criterios TRL | TRL 3 en S1, TRL 4 en S2 | Gate | Director del Proyecto |
| M6 | Cobertura funcional | HU completadas / HU planificadas del semestre | 100% HU criticas del gate | Semestral | Juan Ignacio Gone |
| M7 | Tasa de rechazo | borradores rechazados / borradores generados | <= 20% al cierre S2 | Mensual en S2 | Responsable Gestion del Conocimiento |
| M8 | Trazabilidad completa | acciones con log completo / acciones totales | 100% en S2 | Por release | Responsable tecnico IA |
| M9 | Seguridad base | controles criticos cumplidos / controles criticos definidos | 100% antes de release | Por gate | Responsable tecnico IA |
| M10 | Cobertura de prueba | casos ejecutados / casos planificados | Umbral pendiente de confirmacion; no liberar con casos criticos sin ejecutar | Por gate | Juan Ignacio Gone |
| M11 | Defectos criticos abiertos | cantidad de defectos severidad critica sin cerrar | 0 para liberar | Semanal en estabilizacion | Juan Ignacio Gone |

## 13. Protocolo de medicion

1. **Linea base manual:** antes de afirmar reduccion de tiempo, medir el proceso manual de redaccion de gacetillas/posts o relevar evidencia historica disponible. La muestra concreta queda pendiente de confirmacion con la SEU.
2. **Muestra de contenido:** registrar por cada pieza: tipo, canal, datos de entrada, fecha, prompt/version, salida, validador, decision y observaciones.
3. **Frecuencia:** medir automaticamente M1, M2 y M8 por ejecucion; revisar M3, M4, M5, M6, M7, M9, M10 y M11 en gates y reportes de avance.
4. **Registro:** usar Google Sheets o PostgreSQL segun semestre. En S1 se acepta trazabilidad en Sheets; en S2 se espera persistencia mas robusta.
5. **Evidencia:** conservar enlaces a outputs, capturas, checklists, actas y logs. La evidencia debe permitir reconstruir el flujo sin depender de memoria personal.

## 14. Gestion de defectos

Todo defecto debe registrarse con:

- ID;
- fecha de deteccion;
- HU afectada;
- ambiente;
- descripcion;
- pasos de reproduccion;
- severidad;
- prioridad;
- responsable;
- estado;
- evidencia;
- fecha de cierre;
- prueba de regresion asociada.

### Severidad

| Severidad | Definicion | Politica |
|---|---|---|
| Critica | Publica/envia/emite sin validacion, inventa informacion critica, expone credenciales, pierde trazabilidad o bloquea una HU completa | Bloquea release y gate |
| Alta | Afecta flujo principal, rompe integracion o produce contenido no usable | Debe corregirse antes de gate |
| Media | Afecta flujo alternativo, formato o usabilidad sin comprometer seguridad ni evidencia | Puede cerrarse con plan de correccion |
| Baja | Error menor de texto, documentacion o mejora no bloqueante | No bloquea release si queda registrado |

## 15. Gestion de riesgos de calidad

| Riesgo | Causa | Consecuencia | Mitigacion | Evidencia de control |
|---|---|---|---|---|
| Alucinaciones del LLM | Datos insuficientes, prompt debil, ausencia de validacion | Comunicacion incorrecta o dano reputacional | HITL obligatorio, prompts restrictivos, fuente de datos visible | Checklist contenido, log, rechazo/aprobacion |
| Calidad de texto insuficiente | Plantillas o tono no acordados | Retrabajo alto, rechazo del usuario | Co-diseno de plantillas y refinamiento iterativo | Plantilla aprobada, tasa de rechazo |
| Alcance expandido | Mezcla A1 con A5/A4/soporte | Proyecto sobredimensionado | Matriz BPM-HU y exclusion explicita en cada gate | Revision de backlog |
| Baseline inexistente | No se mide proceso manual | No se puede demostrar mejora | Medicion inicial o registro historico validado | Hoja de baseline |
| Hardware insuficiente | Inferencia local no validada | Latencia alta o dependencia externa | Spike tecnico, criterio de fallback aprobado | Benchmark, reporte de entorno |
| Falta de disponibilidad SEU | Usuarios no validan a tiempo | TRL 4 sin evidencia real | Agenda de validaciones y roles alternos | Actas/checklists |
| Prompt injection | Entrada maliciosa o documentos no confiables | Salida manipulada o accion indebida | Sanitizacion, separacion instrucciones/datos, aprobacion humana | Casos adversariales |
| Logs incompletos | Diseno de trazabilidad tardio | Evidencia no auditable | Esquema de log desde S1, prueba de trazabilidad | Muestreo de logs |

## 16. Evidencia y trazabilidad

La evidencia minima por HU debe guardarse con identificador estable, fecha, responsable y enlace al output.

| Elemento | Proceso BPM | HU / requisito | DoD | Evidencia | Estado |
|---|---|---|---|---|---|
| Gacetilla | P4 | HU-010 | Sheet -> Google Doc, plantilla, < 30 s, validacion | Doc, log, checklist | Pendiente de ejecucion |
| Post RRSS | P4 | HU-011 | Canal adaptable, texto limpio, longitud configurable, validacion | Borrador, log, checklist canal | Pendiente de ejecucion |
| Confirmacion | P5/P4 | HU-012 | Trigger, email, registro de envio | Email, log, estado Sheet | Pendiente de ejecucion |
| Lenguaje natural interno | P4/P3 | HU-013 | Email -> invitacion chat, datos en Sheets, respuesta usable | Captura/transcript, Sheet, log | Pendiente de ejecucion |
| Certificado | P5 | HU-014 | Plantilla, PDF, aprobacion previa | PDF, aprobacion, log | Pendiente de ejecucion |
| Seguridad y auditoria | Transversal | RNF seguridad/CONEAU | RBAC, credenciales protegidas, logs, validacion formal | Checklist seguridad, registro activos | Pendiente de ejecucion |

Nomenclatura sugerida para evidencias: `EVID-A1-SX-HU-XXX-YYYY-MM-DD-descripcion`. Si la evidencia corresponde a validacion formal, mantener compatibilidad con la nomenclatura del anteproyecto: `VAL-SX-YYYY-MM-DD-descripcion`.

## 17. Liberacion y aceptacion

Una version candidata del Agente 1 solo puede liberarse academicamente o pasar un gate TRL si:

1. no existen defectos criticos abiertos;
2. todos los casos criticos de prueba del gate fueron ejecutados;
3. las historias incluidas cumplen DoD;
4. la validacion humana fue registrada;
5. los logs permiten reconstruir las acciones;
6. la documentacion minima de uso, instalacion y operacion esta disponible;
7. las exclusiones de alcance fueron revisadas;
8. seguridad base esta aprobada;
9. la evidencia del gate esta indexada y accesible.

El paquete de liberacion debe incluir: version del codigo o prototipo, configuracion no sensible, plantillas, prompts versionados, casos de prueba, reporte de defectos, evidencias de validacion, manual breve de usuario y nota de cambios.

## 18. Plan de accion inmediato

| Prioridad | Accion | Responsable | Resultado esperado |
|---|---|---|---|
| P0 | Crear checklist formal de validacion SEU por tipo de pieza | Juan Ignacio Gone + SEU | Instrumento usable en G2/G4 |
| P0 | Definir registro de defectos y evidencia | Juan Ignacio Gone | Plantilla de seguimiento |
| P0 | Relevar baseline manual de gacetilla/post | Juan Ignacio Gone + SEU | Medicion para M3 |
| P0 | Definir esquema de log S1 en Sheets | Juan Ignacio Gone | Trazabilidad minima desde TRL 3 |
| P1 | Ejecutar spike de hardware/modelo local | Juan Ignacio Gone / Responsable tecnico IA | Evidencia de latencia y viabilidad |
| P1 | Revisar RACI por flujo y responsable de validacion | Coordinador + SEU | Responsabilidades por HU |
| P1 | Separar visualmente alcance A1 S1-S2 de proyeccion P100 S3-S4 | Juan Ignacio Gone | Menor riesgo de lectura en defensa |
| P2 | Preparar paquete de liberacion academica G2/G4 | Juan Ignacio Gone | Evidencia ordenada para evaluacion |

## 19. Pendientes de confirmacion

- Fechas oficiales de entrega, defensa y gates academicos.
- Personas nominales para Coordinador, Responsable Gestion del Conocimiento, Responsable RRSS, validadores y soporte tecnico.
- Plantillas institucionales definitivas de gacetilla, post, mail y certificado.
- Entorno real disponible para Ollama/FastAPI/Google Workspace.
- Criterio de muestra para baseline manual y validaciones SEU.
- Herramienta final para registro de defectos y evidencias: Google Sheets, Jira, repositorio Markdown u otra definida por la catedra/SEU.

