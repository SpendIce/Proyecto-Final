# Plan de integracion - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot  
**Autor del PPS:** Juan Ignacio Gone  
**Artefacto:** evaluacion del proyecto de desarrollo y plan de integracion  
**Estado:** borrador academico trazable  
**Ultima actualizacion:** 2026-09-06

## 1. Proposito

Este documento evalua el estado actual del proyecto de desarrollo del Agente 1, Extension Bot, y define un plan de integracion para incorporarlo de forma progresiva al Proyecto Centenario (P100), sin ampliar su alcance funcional ni convertirlo en orquestador del sistema multiagente.

El plan funciona como artefacto puente entre el anteproyecto, los casos de uso, el diagrama de clases, el Gantt, el plan de calidad, el plan de riesgos, el plan de comunicaciones, el plan de auditoria, el plan de estados y el plan de despliegue. Su foco no es repetir esos documentos, sino ordenar como el Agente 1 se integra con:

- Google Workspace como plataforma institucional;
- el backend y motor de IA local;
- los flujos de validacion humana;
- la trazabilidad exigible para CONEAU;
- los controles de seguridad desde el principio;
- los otros agentes A2-A5 como proveedores de insumos, no como componentes orquestados por A1.

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
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/DiagramaClases/Diagrama-Clases-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanComunicaciones/Plan-Comunicaciones-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanAuditoria/Plan-Auditoria-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanEstados/Plan-Estados-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanDespliegue/Plan-Despliegue-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md`

Tambien se integraron relevamientos read-only realizados por subagentes sobre alcance documental, arquitectura de integracion y seguridad.

## 3. Evaluacion sintetica del proyecto

**Veredicto:** APROBADO CON OBSERVACIONES FUERTES.

El proyecto del Agente 1 es viable y defendible como proyecto de desarrollo si se mantiene acotado al rol definido: agente de comunicacion institucional de la Secretaria de Extension Universitaria, asociado principalmente al Proceso 4. La documentacion vigente ya contiene una base suficiente para iniciar una integracion controlada: alcance, HU-010 a HU-014, DoD, casos de uso, clases, cronograma, riesgos, calidad, comunicaciones, auditoria, estados, despliegue, seguridad, TRL y trazabilidad.

La debilidad principal no es conceptual. La brecha esta en convertir las definiciones en instrumentos operativos verificables: contratos de datos, plantillas versionadas, validadores confirmados, logs no editables, checklist SEU, pruebas de seguridad, evidencia de gate y mecanismos tecnicos que impidan saltar la validacion humana.

## 4. Alcance de integracion

### 4.1 Incluido

| Frente | Alcance permitido |
|---|---|
| Proceso principal | P4 - Comunicacion y Difusion Institucional |
| Procesos de apoyo | P3, P5 y P6 solo cuando el resultado sea una pieza comunicacional o documental del A1 |
| Historias A1 | HU-010, HU-011, HU-012, HU-013, HU-014 |
| Plataforma base | Google Workspace: Forms, Sheets, Drive, Docs, Gmail y Apps Script |
| Backend | FastAPI, LangChain, Ollama local, PostgreSQL en S2, Celery/Redis si el volumen lo justifica |
| Integracion A2-A5 | Recepcion de insumos normalizados para transformarlos en comunicacion institucional |
| Validacion | Human-in-the-loop obligatorio antes de publicar, enviar oficialmente o emitir certificados |
| Evidencia | Logs, outputs, checklist, aprobaciones, rechazos, defectos y paquetes de gate TRL |

### 4.2 Excluido

Este plan no habilita:

- scraping, extraccion RRSS, analitica, KPIs o dashboards como responsabilidad del Agente 1;
- atencion publica masiva o chatbot publico;
- orquestacion funcional del sistema multiagente;
- soporte administrativo general no asignado formalmente al Agente 1;
- publicacion, envio oficial o emision de certificados sin aprobacion humana registrada;
- integraciones externas complejas no definidas;
- uso de LLM externo con datos reales sin aprobacion, anonimizacion y registro;
- declarar TRL 3 o TRL 4 sin evidencia ejecutable.

## 5. Principios de integracion

1. **A1 como hub de comunicacion, no orquestador:** recibe insumos de A2-A5 y genera piezas institucionales, pero la orquestacion la resuelven procesos, triggers, Apps Script y colas tecnicas.
2. **Integracion por fases:** primero A1 autonomo con insumos SEU; luego automatizaciones internas; despues interfaces A2-A5 con mocks y finalmente integracion real gradual.
3. **Validacion humana bloqueante:** el estado `APROBADA` debe ser condicion tecnica para publicar, enviar oficialmente o emitir certificados.
4. **Google Workspace como interfaz primaria:** Sheets actua como bus operativo, Docs/Drive como repositorio de salidas, Gmail como canal formal y Apps Script como trigger tecnico.
5. **Inferencia local como base:** Ollama y modelos locales preservan soberania de datos; cualquier API externa es contingencia aprobada y anonimizacion obligatoria.
6. **Trazabilidad desde S1:** cada solicitud debe tener identificador, fuente, version de plantilla/prompt, output, validador, estado y evidencia.
7. **Seguridad como condicion de avance:** RBAC, NHI, secretos, permisos minimos, prompt injection, logs y kill switch son criterios de gate, no mejoras opcionales.
8. **Mocks antes de dependencias reales:** si A2-A5 no estan listos en S2, A1 debe probar contratos con insumos estaticos versionados sin bloquear el TRL 4 del nucleo A1.

## 6. Modelo de integracion propuesto

```text
Fuentes SEU / A2-A5
        |
        v
Google Forms / Sheets / Gmail / Drive
        |
        v
Apps Script / trigger tecnico
        |
        v
FastAPI - Backend A1
        |
        +--> Validador de alcance y datos minimos
        +--> Gestor de plantillas
        +--> LangChain - prompts versionados
        +--> Ollama - LLM local
        +--> Servicio de trazabilidad
        +--> PostgreSQL o Sheets - estado y logs
        +--> Celery / Redis - tareas asincronas S2
        |
        v
Google Docs / borradores / emails de prueba / PDFs
        |
        v
Validacion humana SEU
        |
        v
Publicacion, envio o emision solo si estado = APROBADA
```

El LLM no debe tener permiso directo para publicar, enviar, borrar, aprobar ni emitir. Su salida es insumo de borrador. Las acciones institucionales quedan fuera del modelo y pasan por servicios controlados con RBAC, estado aprobatorio y log.

## 7. Contrato minimo de datos

Toda entrada al Agente 1 debe normalizarse con un contrato minimo. En S1 puede implementarse en Sheets; en S2 puede persistirse o replicarse en PostgreSQL.

| Campo | Obligatorio | Descripcion |
|---|---|---|
| `id_solicitud` | Si | Identificador unico y estable para correlacionar datos, logs y evidencia |
| `origen` | Si | SEU, A2, A3, A4, A5 u otro origen autorizado |
| `tipo_insumo` | Si | Actividad, efemeride, evento, respuesta compleja, texto RRSS enriquecido, inscripcion, certificado |
| `proceso_bpm` | Si | P4 como principal, o P3/P5/P6 cuando corresponda apoyo comunicacional |
| `hu_destino` | Si | HU-010 a HU-014 o control transversal |
| `contenido_base` | Si | Texto o datos estructurados que sustentan la pieza |
| `metadatos` | Si | Fecha, responsable del dato, fuente, canal, version y restricciones |
| `fuente_verificada` | Si | Indica si la fuente fue validada por rol humano o sistema autorizado |
| `estado` | Si | RECIBIDA, INCOMPLETA, EN_PROCESO, BORRADOR, PENDIENTE_VALIDACION, APROBADA, OBSERVADA, RECHAZADA, FALLIDA |
| `responsable_validacion` | Si para salida oficial | Rol o persona que valida, cuando este confirmado |
| `evidencia_uri` | Si para gate | Enlace a Doc, PDF, captura, mail, log, checklist o registro |
| `hash_input` | Recomendado | Control de integridad del insumo |
| `hash_output` | Recomendado | Control de integridad de la salida |

## 8. Interfaces A2-A5 hacia A1

| Origen | Insumo permitido | Uso por A1 | Criterio de aceptacion | Riesgo si falta contrato |
|---|---|---|---|---|
| A2 - Historia Viva | Efemerides, resenas, hitos historicos con fuente y fecha | Gacetillas o posts institucionales de memoria historica | Metadatos completos, fuente verificable, no duplicacion | A1 puede difundir datos historicos sin trazabilidad |
| A3 - Vinculacion y Congresos | Datos de eventos, jornadas, convenios u oportunidades ya validadas | Difusion de eventos y oportunidades | Estado validado, responsable de dato, canal sugerido | A1 puede publicar eventos incompletos o no aprobados |
| A4 - Atencion a Comunidad | Solicitudes de redaccion institucional para respuestas complejas | Respuesta redactada con tono institucional | No atencion masiva; solo pieza comunicacional revisable | A1 puede convertirse en chatbot publico indirecto |
| A5 - Monitoreo y Mejora | Texto RRSS limpio/enriquecido o datos normalizados para comunicacion | Mejora de piezas antes de difusion | Origen, version, datos normalizados, sin delegar analitica a A1 | A1 puede absorber scraping o analitica |

Regla: toda interfaz A2-A5 debe probarse primero con mocks estaticos. La integracion real solo avanza si el contrato incluye origen, metadatos, estado, responsable y evidencia.

## 9. Fases de integracion

| Fase | Nombre | Actividades principales | Salida verificable |
|---|---|---|---|
| F0 | Gobierno de alcance | Congelar alcance A1, exclusiones, matriz BPM-HU-DoD, dependencias HU-001/HU-002 y criterio HU-013 vigente | Matriz de alcance y pendientes de confirmacion |
| F1 | Plataforma base | Preparar Drive/Sheets, Apps Script minimo, permisos, estructura de carpetas, esquema de logs y nomenclatura de evidencia | Bus Sheets y repositorio Drive listos para pruebas |
| F2 | A1 autonomo S1 | Implementar/probar HU-010 y HU-011 con insumos SEU, plantillas, prompts versionados y borradores | Paquete G2: Google Doc, post, log, checklist y medicion < 30 s |
| F3 | Automatizacion interna S2 | Incorporar HU-012, HU-013 y HU-014; Gmail, certificados PDF, persistencia y colas si aplican | Emails de prueba, captura HU-013, PDF, logs y controles HITL |
| F4 | Contratos A2-A5 | Definir y probar mocks de insumos A2-A5; validar que A1 solo consume y transforma | Contratos de interfaz, mocks, pruebas de alcance y logs |
| F5 | Integracion real gradual | Conectar insumos reales disponibles de A2-A5, de a uno, con fallback al modo autonomo | Evidencia punta a punta por origen y decision de go/no-go |
| F6 | Gate TRL 4 y transferencia | Validar con usuarios SEU, cerrar defectos criticos, documentar manual breve y continuidad P100 | Acta/informe G4, paquete de release y backlog de continuidad |

## 10. Gates de integracion

| Gate | Condicion de entrada | Criterios obligatorios | Bloquea si... |
|---|---|---|---|
| GI-0 Alcance | Fuentes y backlog disponibles | A1 acotado a P4, HU-010 a HU-014, exclusiones visibles | A1 absorbe scraping, analitica, A4, A5, soporte general u orquestacion |
| GI-1 Datos y plataforma | Drive/Sheets/Apps Script definidos | Campos minimos, estados, permisos, responsables por rol y log basico | faltan campos criticos, validador o evidencia por HU |
| GI-2 MVP autonomo | HU-010/HU-011 candidatas | Salidas en borrador, validacion humana, log, checklist, rendimiento | no hay output, log, aprobacion/rechazo o control de publicacion |
| GI-3 Automatizacion interna | Base S1 estable | HU-012/HU-013/HU-014 con registros, seguridad y control de duplicados | hay envio/emision sin aprobacion o logs incompletos |
| GI-4 Interfaces A2-A5 | Contratos y mocks listos | Cada insumo tiene origen, estado, responsable, metadatos y evidencia | A1 recibe datos no normalizados o fuera de alcance |
| GI-5 TRL 4 | HU-010 a HU-014 candidatas | Usuarios SEU, checklist >= 3/4, 0 defectos criticos, seguridad probada | faltan RBAC, HITL, logs, prueba prompt injection o evidencia CONEAU |

## 11. Controles de seguridad para la integracion

| Control | Criterio minimo | Evidencia |
|---|---|---|
| RBAC | roles administrador, validador y visualizador; solo validador aprueba | matriz de permisos y prueba de autorizacion |
| NHI | identidad por agente/ambiente, scopes minimos y propietario | inventario de cuentas/tokens |
| Secretos | `.env` fuera de Git o Properties Service; sin claves en logs | checklist de secretos y revision de repositorio |
| Prompt injection | sanitizacion, delimitadores, schemas, allowlist de acciones | pruebas adversariales documentadas |
| HITL tecnico | publicacion/envio/emision requieren estado `APROBADA` server-side | prueba negativa de bypass |
| Logs no editables | append-only o control de integridad; hash de input/output | muestra de trazabilidad |
| Fallback externo | deny-by-default; aprobacion y anonimizacion obligatorias | decision registrada y prueba de no salida |
| Kill switch | mecanismo para desactivar triggers/envios ante incidente | prueba de activacion y registro |

## 12. Validacion human-in-the-loop

| Pieza / HU | Validador principal por rol | Evidencia minima | Regla bloqueante |
|---|---|---|---|
| HU-010 Gacetilla | Revisión editorial: referente SEU designado; aprobación/corrección: Oficial de Comunicación Institucional | Borrador, checklist, estado, log y decisión por etapa | no se publica ni eleva oficialmente sin aprobación/corrección institucional registrada |
| HU-011 Post RRSS | Revisión editorial y criterios: referente SEU designado; aprobación/corrección institucional si corresponde | borrador por canal, checklist canal, log y decisión por etapa | no se publica sin decisión humana registrada; la revisión editorial no autoriza publicación |
| HU-012 Confirmacion | Responsable de Cursos / personal SEU, a confirmar por origen | email de prueba, estado, timestamp, log y origen de inscripción | permanece en borrador; ningún envío automático hasta definir la regla escrita de aprobación individual o preaprobación de plantilla |
| HU-013 Chat interno | Personal SEU / Coordinador | email de inicio, captura/transcript, registro Sheet | no es chatbot publico; usuario autenticado |
| HU-014 Certificado | Coordinador / Administracion | PDF, aprobacion manual, log | no se emite sin aprobacion previa |

## 13. Indicadores de integracion

| ID | Indicador | Umbral sugerido |
|---|---|---:|
| MI-01 | Acciones oficiales con validacion humana previa | 100% |
| MI-02 | Solicitudes con `id_solicitud` y evidencia recuperable | 100% para gates |
| MI-03 | Generacion de pieza HU-010/HU-011 | < 30 s o excepcion documentada |
| MI-04 | Checklist SEU | >= 3/4 en dimensiones criticas |
| MI-05 | Defectos criticos abiertos | 0 para gate |
| MI-06 | Interfaces A2-A5 con contrato probado | 100% de interfaces usadas |
| MI-07 | Pruebas de prompt injection criticas aprobadas | 100% antes de TRL 4 |
| MI-08 | Uso de LLM externo con PII | 0 |
| MI-09 | Eventos duplicados HU-012 | 0 |
| MI-10 | Logs con input hash, output hash, estado y validador | 100% para muestra auditada |
| MI-11 | Publicaciones mensuales de referencia para prueba de capacidad | 12 aproximadas; no SLA |
| MI-12 | Mínimo informado para calendario editorial | 1 reel mensual y 2 publicaciones semanales; no sustituye la prioridad por eventos |

## 14. Matriz de trazabilidad de integracion

| Elemento | Proceso BPM | HU / control | DoD de integracion | Evidencia | Responsable |
|---|---|---|---|---|---|
| Bus operativo Sheets | Transversal | HU-001/HU-002 como prerequisito | estructura, campos, estados, permisos | Sheet versionada, matriz de campos | Responsable tecnico IA |
| Gacetillas | P4 | HU-010 | actividad aprobada, nota institucional candidata, revisión y aprobación por etapa | Doc/borrador, checklist, log, decisión | Departamento de Comunicación / Oficial de Comunicación Institucional |
| Posts RRSS | P4 | HU-011 | canal, longitud, tono y validación; criterios aún pendientes | borrador, checklist, log, decisión | Referente de redes SEU / Oficial de Comunicación Institucional |
| Confirmaciones | P5/P4 | HU-012 | origen, trigger, plantilla, no duplicado, registro y regla de envío | email de prueba, timestamp, log, origen | Cursos / SEU |
| Lenguaje natural interno | P4/P3 | HU-013 | email + invitacion a chat, usuario interno, registro | captura/transcript, Sheet, log | Coordinacion / SEU |
| Certificados | P5 | HU-014 | plantilla, PDF, aprobacion previa | PDF, aprobacion, log | Coordinador / Administracion |
| Insumos A2-A5 | P4 con origen segun agente | Integracion S2 | contrato, mock, metadatos, evidencia | contrato, ejemplo, log | Responsable tecnico / pares P100 |
| HITL | Transversal | CU-A1-06 | bloqueo tecnico sin aprobacion | prueba negativa, checklist | Coordinador Extension |
| Seguridad | Transversal | RNF seguridad | RBAC, NHI, secretos, prompt injection | checklist, pruebas, inventario | Responsable tecnico IA |
| TRL | Transversal | Gates GI-2/GI-5 | evidencia ejecutable, usuarios, defectos cerrados | paquete gate, acta/informe | Director / Juan Ignacio Gone |

## 15. Riesgos especificos de integracion

| Riesgo | Nivel | Tratamiento |
|---|---|---|
| A1 se interpreta como orquestador por su rol de hub | Alto | redactar interfaces como recepcion de insumos y mantener orquestacion en infraestructura |
| A2-A5 no entregan insumos reales en S2 | Medio | usar mocks versionados y diferir integracion real sin bloquear A1 autonomo |
| Se publica/envia/emite sin validacion humana | Critico | bloqueo server-side por estado `APROBADA`, RBAC, logs y kill switch |
| Prompt injection por Sheets, mails, PDF/DOCX o agentes externos | Critico | sanitizacion, delimitadores, allowlist, salida como borrador y pruebas adversariales |
| Logs editables impiden auditoria CONEAU | Alto | append-only, hash, backup y revision history |
| HU-013 conserva criterio ambiguo | Medio | unificar texto: email con invitacion a chat y registro en Sheets |
| Fallback externo expone datos institucionales | Alto | deny-by-default, anonimizacion, aprobacion formal y registro |
| Campos de Sheets no cerrados generan retrabajo | Alto | diccionario de datos antes de GI-1 |

## 16. Acciones inmediatas recomendadas

| Prioridad | Accion | Habilita | Responsable |
|---|---|---|---|
| P0 | Crear diccionario minimo de campos Sheets para HU-010 a HU-014 e interfaces A2-A5 | GI-1 | Juan Ignacio Gone / Responsable tecnico IA |
| P0 | Crear checklist SEU de validacion por tipo de pieza | GI-2 / GI-5 | Juan Ignacio Gone + SEU |
| P0 | Definir esquema de log con `id_solicitud`, input hash, output hash, estado, validador y evidencia | trazabilidad CONEAU | Responsable tecnico IA |
| P0 | Unificar HU-013 como email + invitacion a chat + registro en Sheets | cierre de inconsistencia | Juan Ignacio Gone |
| P0 | Definir prueba negativa de no publicacion/envio/emision sin aprobacion | seguridad HITL | Responsable tecnico IA |
| P1 | Preparar mocks A2-A5 con contrato minimo | integracion S2 sin bloqueo | Pares P100 / Responsable tecnico IA |
| P1 | Ejecutar spike Ollama/FastAPI/Workspace y medir latencia | viabilidad tecnica | Responsable tecnico IA |
| P1 | Crear threat model STRIDE especifico del A1 | seguridad de integracion | Juan Ignacio Gone / Responsable tecnico IA |
| P1 | Definir politica de retencion de evidencias y logs | auditoria CONEAU | Director / SEU / Juan Ignacio Gone |

## 17. Pendientes de confirmacion

- Fechas oficiales de entrega, defensa y gates academicos.
- Personas nominales para Coordinador, Responsable Gestion del Conocimiento, Responsable RRSS, administracion, cursos, soporte tecnico y validadores suplentes.
- Plantillas institucionales finales de gacetilla, post, mail, newsletter y certificado.
- Campos exactos y permisos finales de Google Sheets.
- Disponibilidad real de entorno para Ollama, FastAPI, Apps Script, Gmail, Drive, PostgreSQL, Celery y Redis.
- Disponibilidad real de A2-A5 para S2 o decision formal de usar mocks.
- Politica de retencion, backup y no repudio de logs/evidencias.
- Criterio de doble aprobacion para comunicaciones criticas y certificados.

## 18. Criterio de cierre del plan

El plan de integracion queda documentalmente completo cuando:

1. cada interfaz del Agente 1 tiene origen, destino, responsable, contrato de datos y evidencia;
2. cada HU conserva trazabilidad BPM-HU-DoD-evidencia-responsable;
3. la salida oficial queda tecnicamente bloqueada hasta validacion humana;
4. los insumos A2-A5 se tratan como entradas normalizadas, no como responsabilidades absorbidas;
5. los riesgos criticos tienen prueba negativa y control verificable;
6. los gates TRL se demuestran con outputs, logs, checklist, defectos gestionados y paquete de evidencia.

Sin estos elementos, el proyecto puede considerarse bien definido, pero no integrado en sentido defendible ante evaluacion academica o institucional.
