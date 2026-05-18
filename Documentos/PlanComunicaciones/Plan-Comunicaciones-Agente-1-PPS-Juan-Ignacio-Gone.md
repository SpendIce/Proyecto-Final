# Plan de comunicaciones - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del proyecto de desarrollo y plan de comunicaciones  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-05-18

## 1. Proposito

Este documento evalua el proyecto de desarrollo del Agente 1 y define un plan de comunicaciones para su ejecucion, validacion y seguimiento academico. El plan se orienta a asegurar que los interesados reciban informacion oportuna, trazable y suficiente para tomar decisiones, validar avances, controlar riesgos y sostener la evidencia requerida por los gates TRL y por criterios de evaluacion institucional.

El plan cubre dos planos relacionados pero distintos:

1. **Comunicaciones de gestion del proyecto:** avances, decisiones, riesgos, cambios de alcance, validaciones, evidencias, incidentes y reportes de desempeno del desarrollo del Agente 1.
2. **Control comunicacional de las piezas producidas por el Agente 1:** circuito de borrador, revision, aprobacion, publicacion o rechazo de gacetillas, posts, mails, confirmaciones y certificados.

Este documento no reemplaza el anteproyecto, el plan de calidad, el plan de riesgos ni los casos de uso. Los complementa con una matriz operativa de interesados, canales, cadencias, responsables, evidencias y criterios de escalamiento.

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
- `Contenido/Campus/DSI2/_md/12-comunicaciones.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`

Tambien se integraron dos relevamientos read-only realizados por subagentes:

- alcance, arquitectura, stakeholders, canales y brechas del Agente 1;
- criterios de evaluacion, evidencia institucional, restricciones HITL/seguridad y estructura recomendada para el plan.

## 3. Criterio metodologico

Se adopta el enfoque de DSI2 para gestion de comunicaciones de proyectos: identificar interesados, definir necesidades de informacion, seleccionar canales, distribuir informacion, gestionar expectativas e informar desempeno.

La matriz central responde cinco preguntas:

1. quien necesita informacion;
2. que informacion necesita;
3. cuando la necesita;
4. como se le suministra;
5. quien la suministra y que evidencia queda.

El plan se ajusta ademas a los criterios del Proyecto Centenario:

- trazabilidad documental completa;
- mapeo a procesos BPM;
- respeto de RACI;
- evidencia verificable para DoD y TRL;
- validacion humana obligatoria antes de publicar, enviar o emitir piezas institucionales;
- bajo costo y uso prioritario de Google Workspace;
- no reemplazo de personal ni automatizacion de decisiones institucionales criticas.

## 4. Alcance del plan

### 4.1 Alcance incluido

El plan aplica al desarrollo del Agente 1 durante el primer ano academico del Proyecto de Juan Ignacio Gone:

| Periodo | Alcance | TRL objetivo | Foco comunicacional |
|---|---|---|---|
| Semestre 1 | HU-010 gacetillas y HU-011 posts RRSS | TRL 3 | Requisitos, plantillas, prototipo controlado, validacion inicial SEU |
| Semestre 2 | HU-012 confirmaciones, HU-013 interaccion interna, HU-014 certificados | TRL 4 | Automatizacion, validacion con usuarios reales, evidencia de uso, integracion inicial A2-A5 |

Tambien aplica a comunicaciones de soporte para:

- cierre de requisitos y plantillas;
- seguimiento de riesgos y calidad;
- reuniones de avance;
- decisiones de alcance;
- incidentes de seguridad, privacidad, prompt injection o publicacion no autorizada;
- coordinacion tecnica con la arquitectura multiagente;
- preparacion de paquetes de evidencia para gates TRL.

### 4.2 Exclusiones

Este plan no habilita:

- publicar, enviar o emitir piezas oficiales sin validacion humana registrada;
- convertir al Agente 1 en chatbot publico;
- incorporar scraping, analitica, KPIs o dashboards como responsabilidad del Agente 1;
- asumir fechas oficiales, personas nominales, cuentas institucionales o SLA no confirmados;
- reemplazar criterios de la SEU por aprobaciones informales;
- usar canales externos no definidos para datos sensibles o institucionales.

## 5. Evaluacion sintetica del proyecto

**Veredicto:** APROBADO CON OBSERVACIONES.

El proyecto de desarrollo del Agente 1 es viable y defendible si se mantiene acotado como agente de comunicacion institucional del Proceso 4. La base documental es consistente: hay anteproyecto, alcance funcional, casos de uso, Gantt, plan de calidad, plan de riesgos, arquitectura multiagente y fuentes institucionales que sostienen la necesidad de mejorar la comunicacion multicanal de la SEU.

La mayor brecha no es conceptual, sino operativa: el proyecto necesita convertir su RACI, sus validaciones y sus evidencias en un circuito comunicacional formal. Sin ese circuito, el desarrollo podria llegar a prototipos tecnicamente funcionales pero debiles ante evaluacion por falta de registros, aprobaciones, responsables nominales, decisiones versionadas y evidencia recuperable.

### 5.1 Fortalezas detectadas

| Fortaleza | Impacto en comunicaciones |
|---|---|
| A1 esta claramente definido como agente de comunicacion institucional | Reduce ambiguedad de mensajes y evita expansion de alcance |
| HU-010 a HU-014 tienen DoD y evidencia esperada | Permite planificar comunicaciones por historia y por gate |
| HITL es obligatorio | Protege la calidad institucional y genera evidencia de aprobacion |
| Google Workspace ya aparece como plataforma base | Facilita canal comun, bajo costo y repositorio documental |
| Plan de calidad y plan de riesgos ya existen | Permiten integrar reportes de calidad, riesgos y desempeno |
| Casos de uso identifican actores y controles transversales | Sirven como base para matriz de interesados y validadores |

### 5.2 Observaciones principales

| Observacion | Riesgo asociado | Tratamiento en este plan |
|---|---|---|
| Falta matriz formal de comunicaciones | Mensajes dispersos, decisiones no trazables | Matriz por interesado, canal, frecuencia, evidencia y responsable |
| Faltan titulares/suplentes nominales para validaciones | Aprobaciones informales o bloqueos de gate | Pendiente de confirmacion y escalamiento por rol |
| No hay SLA de revision o rechazo definido | Retrasos en validacion y retrabajo tardio | Cadencias sugeridas y tiempos pendientes de aprobacion |
| Falta politica de archivo de evidencia | Imposibilidad de reconstruir decisiones | Repositorios y nomenclatura de evidencia |
| Integracion A2-A5 puede quedar sin coordinacion | Insumos no normalizados o fuera de alcance | Mesa tecnica de interfaces y contratos minimos |
| Comunicacion externa puede confundirse con marketing o analytics | Expansion indebida hacia A5/A4 | Distincion entre pieza generada por A1 y medicion/atencion externa |

## 6. Principios de comunicacion

1. **Trazabilidad por defecto:** toda comunicacion que afecte alcance, calidad, riesgos, aprobaciones o TRL debe dejar evidencia recuperable.
2. **Canal formal para decisiones:** las decisiones de alcance, validacion, seguridad o liberacion deben registrarse por escrito.
3. **Minimo privilegio informativo:** cada interesado recibe la informacion necesaria para su rol, evitando exponer datos o credenciales innecesarias.
4. **Human-in-the-loop obligatorio:** ninguna pieza institucional generada por IA pasa a publicacion, envio oficial o emision sin aprobacion humana registrada.
5. **Separacion de planos:** la comunicacion de gestion del proyecto no debe confundirse con las piezas comunicacionales generadas por el agente.
6. **Bajo costo y herramientas existentes:** priorizar Gmail, Google Drive, Docs, Sheets, Forms, Calendar, Meet y repositorio Markdown.
7. **Escalamiento temprano:** riesgos, bloqueos o cambios de alcance se comunican antes de comprometer un gate.
8. **No inventar datos:** ante informacion faltante, registrar `Pendiente de confirmacion`.

## 7. Mapa de interesados

| Interesado / rol | Tipo | Interes principal | Influencia | Necesidad comunicacional |
|---|---|---|---|---|
| Juan Ignacio Gone | Responsable del PPS | Desarrollar, documentar y defender A1 | Alta | Alcance, avances, decisiones, evidencia, riesgos, cambios |
| Director del Proyecto / Catedra | Evaluacion academica | Rigor, trazabilidad, TRL, alineacion institucional | Alta | Reportes de avance, gates, decisiones criticas |
| Coordinador de Extension | Accountable Proceso 4 | Pertinencia institucional y aprobacion final | Alta | Validaciones, excepciones, riesgos de publicacion |
| Responsable Gestion del Conocimiento | Responsable funcional contenido | Calidad semantica, tono y coherencia | Alta | Plantillas, borradores, checklist, rechazos |
| Responsable Redes Sociales | Responsable de canal | Adecuacion de posts por red | Media/Alta | Borradores por canal, criterios de longitud, aprobaciones |
| Personal SEU | Usuario operativo | Usabilidad, carga de datos, reduccion de tareas | Alta | Instrucciones, capacitacion, pruebas, feedback |
| Coordinadores/docentes de actividades | Proveedores de datos fuente | Exactitud de datos de eventos/cursos | Media | Solicitud de datos, confirmaciones, correcciones |
| Responsable tecnico Sistemas / IA | Soporte tecnico | Integraciones, logs, seguridad, permisos | Alta | Requisitos tecnicos, incidentes, cambios, pruebas |
| Pares P100 / responsables A2-A5 | Integracion multiagente | Contratos de datos e insumos | Media | Interfaces, mocks, dependencias, fechas de integracion |
| Secretario de Extension | Informado institucional | Impacto, riesgos y decision ejecutiva | Media/Alta | Reportes ejecutivos y escalamiento |
| Decanato / autoridades | Informado estrategico | Riesgo reputacional, avance institucional | Media/Alta | Reportes de hito, incidentes criticos |
| Destinatarios externos | Receptores finales | Recibir comunicaciones aprobadas | Baja | Solo piezas publicadas por canales oficiales |

## 8. RACI comunicacional

| Actividad comunicacional | R | A | C | I | Evidencia |
|---|---|---|---|---|---|
| Reporte de avance del proyecto | Juan Ignacio Gone | Director / Tutor | Responsable tecnico, SEU | Catedra | Informe, mail o minuta |
| Decision de alcance A1 | Juan Ignacio Gone | Director / Tutor | Coordinador Extension, Responsable tecnico | SEU | Registro de decision, matriz BPM-HU |
| Validacion de gacetilla | Responsable Gestion del Conocimiento | Coordinador Extension | Docente/coordinador actividad | Juan Ignacio Gone | Checklist, Google Doc, log |
| Validacion de post RRSS | Responsable RRSS | Coordinador Extension | Responsable Gestion del Conocimiento | Juan Ignacio Gone | Borrador, checklist canal, log |
| Validacion de confirmacion automatica | Personal SEU / Responsable cursos | Coordinador Extension | Responsable tecnico | Juan Ignacio Gone | Email de prueba, estado Sheet, log |
| Validacion de interaccion interna | Personal SEU | Coordinador Extension | Responsable tecnico | Juan Ignacio Gone | Captura/transcript, registro Sheet |
| Validacion de certificado | Administracion / Coordinador Extension | Coordinador Extension | Responsable curso, Responsable tecnico | Juan Ignacio Gone | PDF, aprobacion, log |
| Gestion de incidentes comunicacionales | Juan Ignacio Gone / Responsable tecnico | Coordinador Extension o Director segun severidad | SEU, RGC, RRSS | Autoridades si aplica | Registro incidente, accion correctiva |
| Coordinacion A2-A5 | Responsable tecnico / pares P100 | Director / arquitectura P100 | Juan Ignacio Gone, responsables agentes | SEU | Contrato de interfaz, minuta |
| Cierre de gate TRL | Juan Ignacio Gone | Director / Tutor | SEU, Responsable tecnico | Catedra, autoridades si aplica | Paquete de evidencia, acta/checklist |

## 9. Canales oficiales y uso esperado

| Canal | Uso principal | No usar para | Evidencia minima |
|---|---|---|---|
| Gmail institucional | Comunicacion formal, invitaciones, validaciones, escalamiento | Secretos, credenciales, datos sensibles sin proteccion | Mail archivado, asunto normalizado |
| Google Drive | Repositorio de documentos, plantillas, evidencias | Versiones sin control o duplicadas | Carpeta, enlace, version |
| Google Docs | Borradores de gacetillas, mails, actas, minutas | Registro unico de datos operativos | Documento con historial |
| Google Sheets | Bus de datos, registros, checklist, seguimiento de evidencias | Texto largo sin estructura o decisiones criticas sin acta | Fila con ID, estado, fecha, responsable |
| Google Forms | Captura estructurada de solicitudes o feedback | Decisiones complejas o excepciones no estructuradas | Respuesta registrada |
| Google Calendar / Meet | Reuniones, validaciones sincronicas, walkthroughs | Decisiones sin minuta posterior | Invitacion y minuta |
| Repositorio Markdown | Documentacion academica, trazabilidad tecnica, planes | Datos sensibles o secretos | Commit/diff, archivo versionado |
| Chat interno iniciado por email | Interaccion interna HU-013 | Atencion publica o aprobaciones sin registro | Transcript/captura y registro en Sheet |
| Redes sociales / web institucional | Publicacion de piezas aprobadas | Borradores no validados o pruebas | Captura/enlace y registro de aprobacion |

## 10. Matriz de comunicaciones

| ID | Interesado | Informacion requerida | Momento / frecuencia sugerida | Canal | Emisor | Responsable de validacion | Evidencia | Escalamiento |
|---|---|---|---|---|---|---|---|---|
| COM-01 | Director / Tutor | Estado de alcance, avance, riesgos, decisiones y evidencias | Mensual y en gates TRL | Mail + informe Markdown/PDF + reunion | Juan Ignacio Gone | Director / Tutor | Informe, minuta, paquete evidencia | Si hay cambio de alcance o bloqueo de gate |
| COM-02 | Coordinador Extension | Funcionalidades a validar, riesgos de publicacion, decisiones HITL | Por HU y antes de cada gate | Gmail, Meet, Docs | Juan Ignacio Gone | Coordinador Extension | Checklist, acta, observaciones | Si no hay validador o aprobacion |
| COM-03 | Responsable Gestion del Conocimiento | Plantillas, tono, coherencia, fuentes, borradores | Por pieza HU-010/HU-012/HU-013 | Docs + Sheets + Gmail | A1/Juan Ignacio Gone | RGC | Checklist de contenido, log | Si rechazo supera umbral pendiente o hay dato inventado |
| COM-04 | Responsable RRSS | Posts por canal, longitud, tono, formato, hashtags si aplica | Por pieza HU-011 | Docs + Sheets + Gmail | A1/Juan Ignacio Gone | Responsable RRSS | Borrador, checklist canal | Si el post no cumple formato o tono |
| COM-05 | Personal SEU | Instrucciones de carga, uso, validacion operativa y feedback | Antes de cada prueba y durante validacion | Meet, Docs, Forms, Sheets | Juan Ignacio Gone | Coordinador Extension | Minuta, feedback, captura | Si no hay disponibilidad para validacion |
| COM-06 | Coordinadores/docentes actividad | Datos fuente de actividades, cursos, eventos o certificados | Al cargar solicitud o detectar inconsistencia | Form/Sheets + Gmail | Personal SEU / Juan Ignacio Gone | Responsable del dato | Registro de correccion | Si datos incompletos bloquean HU |
| COM-07 | Responsable tecnico IA | Requisitos tecnicos, permisos, logs, seguridad, errores, rendimiento | Semanal durante implementacion y ante incidentes | Issue/Markdown, Sheets, Meet | Juan Ignacio Gone | Responsable tecnico | Registro tecnico, log, decision | Si afecta seguridad, TRL o disponibilidad |
| COM-08 | Pares P100 / A2-A5 | Contratos de datos, mocks, dependencias e integracion | Inicio S2 y cada hito de integracion | Docs, Sheets, Meet | Juan Ignacio Gone / Responsable tecnico | Arquitectura P100 / Director | Contrato interfaz, minuta | Si A1 recibe insumos fuera de alcance |
| COM-09 | Secretario Extension / Decanato | Hitos, beneficios, riesgos criticos, incidentes reputacionales | En gates, incidentes y decisiones criticas | Informe ejecutivo + mail | Director / Coordinador Extension | Autoridad correspondiente | Informe, acta, registro incidente | Si hay publicacion indebida o riesgo institucional |
| COM-10 | Catedra / evaluadores | Evidencia academica: TRL, DoD, pruebas, trazabilidad, calidad | Entregas, defensas, informes de avance | Informe, repositorio, presentacion | Juan Ignacio Gone | Director / Tutor | Paquete documental | Si falta evidencia de gate |
| COM-11 | Destinatarios externos | Comunicaciones institucionales aprobadas | Solo cuando corresponda a actividad real | Canal institucional oficial | SEU / Responsable canal | Coordinador Extension / RGC / RRSS | Enlace/captura/envio | Si hay error publicado |
| COM-12 | Equipo de infraestructura / IT | Cuentas, permisos, OAuth, cuotas, seguridad, backups | Antes de integraciones y ante cambios | Mail, ticket si existe, Meet | Juan Ignacio Gone / Responsable tecnico | Responsable IT | Solicitud, respuesta, checklist | Si permiso bloquea flujo critico |

Las frecuencias quedan como propuesta operativa. Deben confirmarse con la SEU y la catedra antes de asumirlas como compromiso oficial.

## 11. Flujos comunicacionales

### 11.1 Flujo de comunicacion de gestion del proyecto

1. Juan Ignacio Gone identifica avance, decision, riesgo, bloqueo o cambio.
2. Registra el punto en el artefacto correspondiente: plan, matriz, issue, minuta o reporte.
3. Comunica al interesado responsable por el canal definido en la matriz.
4. El interesado responde, aprueba, rechaza, observa o solicita ampliacion.
5. La decision queda registrada con fecha, responsable, impacto y evidencia.
6. Si afecta alcance, cronograma, calidad, riesgo o TRL, se actualizan los planes relacionados.

### 11.2 Flujo de validacion de piezas generadas por A1

1. Los datos se cargan en Google Forms/Sheets o repositorio autorizado.
2. El trigger o solicitud interna activa el Agente 1.
3. El Agente 1 genera un borrador en Google Docs, Gmail, Sheet o PDF segun la HU.
4. El borrador queda en estado `pendiente de validacion`.
5. El validador humano revisa exactitud, tono, formato, canal, fuente y alcance.
6. El validador decide `aprobado`, `rechazado` u `observado`.
7. Solo con estado `aprobado` se publica, envia o emite por canal oficial.
8. El sistema registra ID, fecha, pieza, solicitante, validador, decision, version, evidencia y observaciones.

Estados minimos:

| Estado | Significado | Puede publicarse/enviarse/emitirse |
|---|---|---|
| Borrador | Salida generada sin revision humana | No |
| Pendiente de validacion | En revision por rol responsable | No |
| Observado | Requiere correccion | No |
| Rechazado | No debe usarse como comunicacion oficial | No |
| Aprobado | Validado por responsable humano | Si, por canal oficial |
| Publicado/enviado/emitido | Accion final ejecutada y registrada | Ya ejecutado |

### 11.3 Flujo de incidentes comunicacionales

1. Se detecta error, dato inventado, publicacion no autorizada, fuga de informacion, credencial expuesta o salida fuera de alcance.
2. Se detiene el flujo afectado si hay riesgo institucional.
3. Se registra incidente con severidad, HU, pieza, canal, evidencia y responsable.
4. Se notifica a Coordinador Extension, Responsable tecnico y Director/Tutor segun severidad.
5. Se corrige el defecto, se revalida la pieza y se documenta accion preventiva.
6. Si hubo publicacion externa, se define comunicacion correctiva institucional con la SEU.

### 11.4 Flujo de cambios de alcance

1. La solicitud nueva se compara contra BPM, HU, DoD y exclusiones.
2. Si pertenece a A1, se registra como cambio o mejora con impacto en cronograma, calidad y riesgo.
3. Si pertenece a A2-A5, soporte administrativo, analitica, scraping o atencion publica, se deriva como fuera de alcance del Agente 1.
4. Toda decision queda documentada antes de implementarse.

## 12. Cadencia de comunicacion y reportes

| Cadencia | Objetivo | Participantes | Salida esperada |
|---|---|---|---|
| Semanal durante implementacion | Revisar avance, bloqueos, riesgos altos y acciones de 7 dias | Juan Ignacio Gone, responsable tecnico si aplica | Minuta breve, acciones, riesgos actualizados |
| Por historia de usuario | Cerrar requisitos, DoD, validadores y evidencia antes de iniciar o cerrar HU | Juan Ignacio Gone, SEU, validador de HU | Checklist HU, decision iniciar/cerrar |
| Por pieza generada | Validar salida comunicacional antes de uso oficial | Validador SEU correspondiente | Aprobacion/rechazo/observacion registrada |
| Mensual | Informar desempeno del proyecto | Juan Ignacio Gone, Director/Tutor | Reporte de alcance, cronograma, calidad, riesgos, evidencias |
| Antes de gate TRL | Confirmar que la evidencia permite defender el nivel TRL | Juan Ignacio Gone, Director/Tutor, SEU | Paquete G2/G4, checklist, decision de gate |
| Ante incidente | Contener impacto, decidir acciones y registrar correccion | Roles afectados segun severidad | Registro de incidente y accion correctiva |
| Cierre de semestre | Consolidar lecciones aprendidas y rebaseline | Juan Ignacio Gone, Director/Tutor, SEU | Informe de avance/cierre, pendientes |

Las cadencias semanales y mensuales son propuestas de gestion. Las fechas oficiales y disponibilidad real deben confirmarse.

## 13. Informes de desempeno

Cada informe de desempeno debe incluir, como minimo:

| Dimension | Contenido | Evidencia |
|---|---|---|
| Alcance | HU activas, cambios, exclusiones revisadas | Matriz BPM-HU, decisiones |
| Cronograma | Hitos cumplidos, atrasos, proximos hitos | Gantt, minuta, reporte |
| Calidad | Pruebas ejecutadas, defectos, checklist SEU | Plan de calidad, registros |
| Riesgos | Top riesgos, cambios de exposicion, mitigaciones | Plan de riesgos actualizado |
| Comunicaciones | Reuniones, validaciones, aprobaciones pendientes | Matriz COM, minutas |
| Seguridad | Incidentes, permisos, controles, pruebas adversariales | Checklist seguridad, logs |
| TRL / DoD | Evidencia por HU y gate | Paquete evidencia |
| Pendientes | Bloqueos y decisiones requeridas | Lista accionable con responsable |

## 14. Repositorio y nomenclatura de evidencia

La evidencia debe poder recuperarse sin depender de memoria personal. Se recomienda usar identificadores estables:

| Tipo de evidencia | Nomenclatura sugerida | Ejemplo |
|---|---|---|
| Comunicacion de gestion | `COM-A1-SX-YYYY-MM-DD-descripcion` | `COM-A1-S1-2026-06-10-reporte-avance` |
| Validacion de pieza | `VAL-A1-SX-HU-XXX-YYYY-MM-DD-descripcion` | `VAL-A1-S1-HU-010-2026-06-20-gacetilla-prueba` |
| Incidente | `INC-A1-SX-YYYY-MM-DD-descripcion` | `INC-A1-S2-2026-09-04-pieza-observada` |
| Decision | `DEC-A1-SX-YYYY-MM-DD-descripcion` | `DEC-A1-S1-2026-05-30-alcance-hu011` |
| Reporte de gate | `GATE-A1-TRLX-YYYY-MM-DD` | `GATE-A1-TRL3-2026-07-15` |

Ubicaciones sugeridas:

- documentos academicos: `Documentos/`;
- planes de gestion: subcarpetas especificas bajo `Documentos/`;
- fuentes institucionales: `Contenido/bible/`;
- evidencia operativa: Google Drive/Sheets institucional a definir;
- registros tecnicos y decisiones de desarrollo: repositorio Markdown, logs y/o herramienta que defina el equipo.

## 15. Seguridad, privacidad y control de informacion

| Regla | Aplicacion |
|---|---|
| No enviar secretos por mail, Docs, Sheets o chat | Credenciales en `.env`, vault o gestor institucional autorizado |
| Aplicar minimo privilegio | Cada rol accede solo a documentos y planillas necesarias |
| Separar instrucciones de datos | Reduce riesgo de prompt injection en documentos o mails |
| Validacion humana previa | Obligatoria en piezas oficiales, publicas, criticas o certificantes |
| Registrar decisiones y aprobaciones | Necesario para CONEAU, auditoria y defensa academica |
| Evitar datos sensibles en servicios externos | APIs externas solo como contingencia aprobada y documentada |
| Sanitizar entradas | Especialmente documentos, mails y prompts de HU-013 |
| Conservar logs sin credenciales | Logs utiles, auditables y sin informacion sensible innecesaria |

## 16. Metricas de comunicacion

| ID | Metrica | Medicion | Umbral / criterio | Frecuencia | Responsable |
|---|---|---|---|---|---|
| MC1 | Validaciones registradas | Piezas con aprobacion registrada / piezas publicadas, enviadas o emitidas | 100% | Por release/gate | Coordinador Extension |
| MC2 | Trazabilidad comunicacional | Comunicaciones criticas con evidencia / comunicaciones criticas totales | 100% en decisiones de alcance, HITL y gate | Mensual/gate | Juan Ignacio Gone |
| MC3 | Pendientes de validacion | Cantidad de piezas o decisiones en espera | Sin umbral confirmado; revisar tendencia | Semanal | Juan Ignacio Gone + SEU |
| MC4 | Tiempo de respuesta de validacion | Fecha decision - fecha solicitud | Pendiente de confirmacion con SEU | Por pieza/HU | Validador correspondiente |
| MC5 | Rechazos u observaciones | Piezas rechazadas u observadas / piezas generadas | Usar junto con plan de calidad; umbral pendiente | Mensual/gate | RGC/RRSS |
| MC6 | Cobertura de interesados | Interesados clave con canal y responsable definidos / interesados clave totales | 100% antes de G1/G2 | Gate | Juan Ignacio Gone |
| MC7 | Reportes de desempeno emitidos | Reportes emitidos / reportes planificados | 100% de reportes comprometidos | Mensual/gate | Juan Ignacio Gone |
| MC8 | Incidentes comunicacionales cerrados | Incidentes con accion correctiva / incidentes totales | 100% antes de release | Por incidente/gate | Responsable tecnico / Coordinador |

## 17. Riesgos comunicacionales y mitigaciones

| ID | Riesgo | Consecuencia | Mitigacion | Evidencia |
|---|---|---|---|---|
| RC-01 | Aprobaciones informales por canales no trazables | No se puede defender HITL ni DoD | Registrar decision en Sheet/Doc/mail formal | Checklist y registro de aprobacion |
| RC-02 | Validador no disponible | Gate bloqueado o pieza sin revision | Definir titular y suplente por HU | RACI confirmado |
| RC-03 | Comunicacion externa sin aprobacion | Riesgo reputacional e incumplimiento de alcance | Bloquear publicacion si estado no es `aprobado` | Log de estado y aprobador |
| RC-04 | Cambio de alcance comunicado tarde | Retrabajo y perdida de foco A1 | Revisar alcance en cada gate y registrar decisiones | Matriz BPM-HU actualizada |
| RC-05 | Falta de minuta en reuniones | Decisiones ambiguas | Minuta breve con acuerdos, pendientes y responsables | Acta o resumen por mail |
| RC-06 | Insumos A2-A5 sin contrato | A1 genera piezas con datos inconsistentes | Contratos minimos de interfaz y mocks | Documento de interfaz |
| RC-07 | Canales con permisos incorrectos | Exposicion de datos o bloqueo operativo | RBAC y revision de permisos antes de pruebas | Checklist seguridad |
| RC-08 | Feedback SEU no sistematizado | Mejoras dispersas y baja adopcion | Formulario/checklist estandar por validacion | Registro de feedback |
| RC-09 | Reportes sin evidencia | TRL declarado sin soporte verificable | Paquete de evidencia por gate | Indice de evidencia |
| RC-10 | Confusion entre A1 y A5/A4 | Sobrealcance hacia analytics o atencion publica | Repetir exclusiones en reportes y decisiones | Registro de alcance |

## 18. Plan de accion inmediato

| Prioridad | Accion | Responsable | Resultado esperado |
|---|---|---|---|
| P0 | Confirmar titulares y suplentes para validacion de HU-010 y HU-011 | Juan Ignacio Gone + SEU | RACI operativo para S1 |
| P0 | Definir carpeta o Sheet de evidencias comunicacionales | Juan Ignacio Gone | Repositorio unico de COM/VAL/DEC/INC/GATE |
| P0 | Crear plantilla de minuta y registro de decision | Juan Ignacio Gone | Decisiones trazables desde G1/G2 |
| P0 | Definir checklist de aprobacion para gacetillas y posts | Juan Ignacio Gone + RGC/RRSS | Validacion usable para TRL 3 |
| P1 | Confirmar SLA o tiempo esperado de revision por pieza | Coordinador Extension | Cadencia realista para validaciones |
| P1 | Coordinar contrato minimo de datos con A2-A5 para S2 | Responsable tecnico / pares P100 | Integracion sin sobrealcance |
| P1 | Definir politica de archivo de mails y evidencias | Juan Ignacio Gone + SEU | Evidencia recuperable |
| P1 | Vincular plan de comunicaciones con plan de riesgos y calidad | Juan Ignacio Gone | Reporte mensual integrado |

## 19. Trazabilidad por HU

| Elemento | Proceso BPM | HU / requisito | Comunicacion clave | Responsable | Evidencia |
|---|---|---|---|---|---|
| Gacetillas | P4 | HU-010 | Solicitud de datos, borrador, validacion RGC/Coordinador, aprobacion | RGC / Coordinador Extension | Google Doc, checklist, log, mail |
| Posts RRSS | P4 | HU-011 | Borrador por canal, revision RRSS, aprobacion | Responsable RRSS / RGC | Borrador, checklist canal, log |
| Confirmaciones | P5 con soporte P4 | HU-012 | Aviso de prueba, validacion de trigger y registro de envio | Personal SEU / Responsable cursos | Email prueba, estado Sheet, log |
| Interaccion interna | P4/P3 | HU-013 | Email inicial, invitacion a chat, transcript o captura, registro Sheet | Personal SEU / Coordinador | Mail, captura/transcript, Sheet |
| Certificados | P5 | HU-014 | Solicitud, generacion PDF, validacion previa, emision | Coordinador / Administracion | PDF, aprobacion, log |
| Validacion humana | Transversal | CU-A1-06 / HITL | Solicitud, decision, observaciones, aprobacion/rechazo | Validador segun pieza | Checklist, acta/mail, log |
| Trazabilidad | Transversal | CU-A1-07 / CONEAU | Registro de cada comunicacion critica y evidencia | Juan Ignacio Gone / Responsable tecnico | Indice de evidencia, logs |
| Gate TRL | Transversal | TRL 3 / TRL 4 | Reporte de avance, evidencia, decision de gate | Juan Ignacio Gone / Director | Paquete GATE-A1 |

## 20. Plantillas operativas

### 20.1 Minuta breve de reunion

```text
ID:
Fecha:
Participantes:
Objetivo:
Temas tratados:
Decisiones:
Pendientes:
Responsables:
Fecha objetivo:
Evidencia asociada:
Proximo contacto:
```

### 20.2 Registro de comunicacion critica

```text
ID:
Fecha:
Emisor:
Destinatario:
HU / proceso:
Tipo: avance | decision | validacion | incidente | cambio | gate
Resumen:
Canal:
Decision requerida:
Resultado:
Responsable:
Evidencia:
Escalamiento:
```

### 20.3 Registro de validacion de pieza

```text
ID:
HU:
Tipo de pieza:
Canal final:
Datos fuente:
Version de plantilla:
Version de prompt si aplica:
Estado: borrador | pendiente | observado | rechazado | aprobado | publicado/enviado/emitido
Validador:
Fecha de solicitud:
Fecha de decision:
Criterios revisados: exactitud | tono | formato | longitud | fuente | alcance | seguridad
Observaciones:
Evidencia:
```

## 21. Pendientes de confirmacion

- Fechas oficiales de entregas, gates academicos y defensa.
- Personas nominales para Coordinador Extension, RGC, Responsable RRSS, Personal SEU validador, soporte tecnico e IT.
- Titulares y suplentes por HU.
- Tiempo maximo esperado para validar gacetillas, posts, confirmaciones, interacciones internas y certificados.
- Carpeta institucional definitiva para evidencias.
- Cuentas oficiales, permisos y politica de archivo de Google Workspace.
- Criterio de escalamiento ante publicacion incorrecta, dato inventado o incidente de seguridad.
- Politica final para comunicaciones externas: web, RRSS, mailing y responsables de cada canal.
- Herramienta final para seguimiento de acciones: Google Sheets, Jira, repositorio Markdown u otra.

## 22. Cierre

El plan de comunicaciones vuelve operativa una condicion central del Proyecto Centenario: no alcanza con que el Agente 1 genere contenido; cada comunicacion relevante debe poder rastrearse desde su solicitud hasta su validacion, publicacion o rechazo. La evidencia comunicacional es parte del producto academico, porque permite demostrar alcance, calidad, seguridad, aceptacion SEU y progresion TRL sin depender de explicaciones informales.
