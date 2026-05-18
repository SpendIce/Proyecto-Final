# Plan de auditoría - Agente 1 Extension Bot

**Proyecto:** Proyecto Centenario (P100) - Agente 1, Extension Bot
**Autor del PPS:** Juan Ignacio Gone
**Artefacto:** evaluación del proyecto de desarrollo y plan de auditoría
**Estado:** borrador académico trazable
**Última actualización:** 2026-05-18

## 1. Propósito

Este documento evalúa el proyecto de desarrollo del Agente 1, Extension Bot, y define un plan de auditoría para verificar que su avance sea trazable, defendible y consistente con el Proyecto Centenario.

La auditoría no busca reemplazar el plan de calidad ni el plan de riesgos. Su función es comprobar, con evidencia, si el desarrollo cumple el alcance autorizado, los procesos BPM, las historias de usuario, los Definition of Done, los controles de seguridad, la validación humana, la trazabilidad CONEAU y los gates TRL definidos para el primer año del proyecto.

El resultado esperado de cada auditoría es un informe con situaciones detectadas, riesgo o consecuencia, recomendación, responsable, opinión del área auditada cuando corresponda y necesidad de reauditoría.

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
- `Contenido/Campus/DSI2/_md/07-indicadores.md`
- `Contenido/Campus/DSI2/_md/09-calidad.md`
- `Contenido/Campus/DSI2/_md/11-auditoria.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/DiagramaClases/Diagrama-Clases-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`

También se integraron tres lecturas read-only realizadas por subagentes:

- alcance, gobernanza, HU, DoD y evidencia;
- arquitectura, seguridad, HITL, RBAC, NHI y prompt injection;
- metodología de auditoría, calidad documental, riesgos, pruebas, métricas y gates.

## 3. Supuestos y límites

1. El alcance auditado corresponde al proyecto de Juan Ignacio Gone sobre el Agente 1 durante el primer año académico, hasta TRL 4.
2. El Semestre 1 cubre el MVP: HU-010 generación de gacetillas y HU-011 generación de posts para redes sociales.
3. El Semestre 2 incorpora HU-012 confirmaciones automáticas, HU-013 interacción interna en lenguaje natural y HU-014 certificados con validación humana.
4. S3 y S4 se consideran continuidad del P100 completo, no compromiso directo del PPS de Juan Ignacio Gone.
5. El Agente 1 pertenece principalmente al Proceso 4 - Comunicación y Difusión Institucional. Puede dar soporte comunicacional a P3, P5 y P6, pero no se convierte en orquestador, analítica, scraping, chatbot público ni soporte administrativo general.
6. No se asumen fechas oficiales, responsables nominales, plantillas finales, campos exactos de Sheets ni infraestructura real hasta que estén confirmados por la SEU, la cátedra o el director del proyecto.

## 4. Evaluación consolidada del proyecto

**Veredicto:** APROBADO CON OBSERVACIONES.

El proyecto es viable y defendible si se mantiene acotado al Agente 1 como agente de comunicación institucional del Proceso 4 y si cada avance se demuestra con evidencia verificable. La documentación vigente ya contiene una base fuerte: alcance, historias HU-010 a HU-014, casos de uso, matriz de trazabilidad, plan de calidad, plan de riesgos, cronograma, métricas, controles de seguridad y validación humana.

Las observaciones principales son auditables y deben tratarse como condiciones de cierre:

- la validación humana está correctamente definida, pero debe existir un instrumento operativo por HU: checklist, estado, aprobador, fecha, observación y evidencia;
- los logs y la trazabilidad deben diseñarse desde S1, no agregarse al final del proyecto;
- la progresión TRL no puede declararse por avance narrativo: debe demostrarse con outputs, pruebas, logs, evidencia de validación y reporte de defectos;
- la integración inicial con A2-A5 debe mantenerse como recepción de insumos, no como orquestación ni absorción de responsabilidades ajenas;
- HU-013 debe auditarse con el criterio vigente: interacción interna iniciada por email con invitación a chat y registro de datos en Sheets;
- las confirmaciones automáticas de HU-012 requieren especial atención: si no hay revisión humana caso a caso, debe probarse que usan plantilla preaprobada, datos validados, registro de envío y control de errores;
- la seguridad debe ser demostrable: inventario de activos IA, identidades no humanas, permisos mínimos, secretos protegidos, protección frente a prompt injection y logs sin datos sensibles innecesarios.

## 5. Objetivos de auditoría

| ID | Objetivo | Pregunta de auditoría | Resultado esperado |
|---|---|---|---|
| OA-01 | Verificar alcance | ¿Cada funcionalidad auditada pertenece a A1 y al proceso BPM correcto? | Sin invasión de A4, A5, soporte administrativo, scraping ni analítica |
| OA-02 | Verificar DoD | ¿Cada HU cumple su Definition of Done global y específico? | Cierre por evidencia, no por declaración |
| OA-03 | Verificar HITL | ¿Toda publicación, envío crítico o emisión requiere validación humana registrada? | 100% de salidas oficiales con aprobación previa |
| OA-04 | Verificar trazabilidad | ¿Se puede reconstruir cada acción desde insumo hasta salida y validación? | Logs, enlaces, responsables, estados y evidencias recuperables |
| OA-05 | Verificar calidad | ¿Las salidas son claras, correctas, institucionales y adaptadas al canal? | Checklist SEU con resultado >= 3/4 cuando aplique |
| OA-06 | Verificar seguridad | ¿Los controles críticos están implementados y probados? | RBAC, secretos protegidos, PoLP, NHI, prompt injection y logs seguros |
| OA-07 | Verificar TRL | ¿El gate TRL 3/4 tiene evidencia suficiente? | Acta o informe de gate con matriz cumplido/no cumplido |
| OA-08 | Verificar gestión | ¿Los riesgos, defectos, cambios y pendientes tienen responsable y estado? | Registro vivo y plan de acción correctiva |

## 6. Alcance de la auditoría

### 6.1 Incluido

- HU-010, HU-011, HU-012, HU-013 y HU-014.
- CU-A1-01 a CU-A1-07.
- Flujo Actividad -> Comunicación.
- Google Sheets, Google Docs, Drive, Gmail, Forms y Apps Script como plataforma institucional.
- Backend FastAPI, cadenas LangChain, modelo local Ollama y componentes de persistencia/logs cuando existan.
- Plantillas, prompts versionados, outputs, estados de validación, logs, checklists, actas, registros de defectos y paquetes de evidencia.
- Controles transversales: validación humana, trazabilidad, seguridad, bajo costo, soberanía de datos y exclusiones.

### 6.2 Excluido

- Scraping, extracción RRSS, KPIs, dashboards y analítica, salvo como insumos recibidos desde A5.
- Atención pública masiva, ventanilla virtual y chatbot público, propios de A4.
- Orquestación general del sistema multiagente.
- Soporte administrativo general o interfaces intersecretaría no asignadas formalmente a A1.
- Publicación automática sin validación humana.
- Integraciones externas complejas no definidas.
- Evaluación de S3/S4 como compromiso directo del PPS actual.

## 7. Criterios de auditoría

| Eje | Criterio | Fuente / soporte | Condición de conformidad |
|---|---|---|---|
| Alcance | A1 como comunicación institucional | Extension Bot, arquitectura P100, anteproyecto | Toda función mapea a P4 o apoyo acotado P3/P5/P6 |
| BPM/RACI | Proceso, responsable y aprobación claros | Procesos y Agentes, criterios Cicerchia | Cada HU tiene responsable institucional y técnico |
| DoD | Global y específico por tipo de historia | Bible, criterios Cicerchia, plan calidad | La HU no cierra sin implementación, prueba, log, documentación y validación |
| HITL | Validación humana obligatoria | Bible, casos de uso, plan calidad | Ninguna salida oficial se publica, envía o emite sin aprobación registrada |
| Calidad de contenido | Precisión, tono, formato y canal | Checklist SEU, plan calidad | Resultado >= 3/4 o defecto registrado |
| Trazabilidad | Evidencia reconstruible | CONEAU, casos de uso, plan calidad | Correlation ID, log, output, estado, validador y enlaces |
| Seguridad | Seguridad desde el principio | Bible, arquitectura, plan riesgos | Inventario, RBAC, secretos, NHI, PoLP, prompt injection y logs seguros |
| TRL | Progresión por evidencia | Criterios Cicerchia, anteproyecto | TRL 3/4 demostrado por pruebas, usuarios y outputs |
| Riesgos | Mitigación y contingencia | Plan riesgos | Riesgos altos tienen responsable, acción y evidencia de control |
| Liberación | Gate bloqueante | Plan calidad | No hay defectos críticos abiertos ni evidencia faltante crítica |

## 8. Metodología

La auditoría se estructura en seis fases. Puede ejecutarse completa en G2/G4 o de forma parcial antes de iniciar cada historia de usuario.

### F0 - Preparación

**Objetivo:** delimitar qué se audita, con qué muestra, quién participa y qué evidencia debe estar disponible.

Actividades:

- confirmar gate o momento de auditoría: pre-G2, G2, pre-G4, G4 o auditoría extraordinaria;
- fijar muestra: por HU, por ejecución, por tipo de pieza o por release candidata;
- listar responsables institucionales por rol, sin inventar nombres si no están confirmados;
- congelar versión auditada de documentación, prompts, plantillas y prototipo;
- preparar checklist, matriz de trazabilidad, registro de hallazgos y carpeta de evidencias.

Evidencia de salida:

- alcance de auditoría;
- plan de muestra;
- lista de artefactos;
- matriz inicial con estado `Pendiente`.

### F1 - Auditoría documental

**Objetivo:** verificar que la documentación describe un sistema coherente, acotado y evaluable.

Actividades:

- contrastar anteproyecto, casos de uso, plan de calidad, plan de riesgos, Gantt y criterios Cicerchia;
- verificar que cada HU tenga caso de uso, DoD, evidencia, responsable y TRL objetivo;
- revisar que las exclusiones estén explícitas;
- detectar contradicciones, especialmente en HU-013, validación humana, alcance de newsletters/correos y rol de hub;
- revisar que los pendientes de confirmación estén marcados y no presentados como hechos.

Evidencia de salida:

- matriz documental;
- lista de inconsistencias;
- recomendaciones de corrección documental.

### F2 - Auditoría funcional

**Objetivo:** verificar que cada historia incluida en la muestra cumple su comportamiento observable.

Actividades:

- ejecutar o revisar evidencia end-to-end de HU-010 a HU-014;
- probar flujo principal, datos incompletos, plantilla ausente, usuario no autorizado, rechazo humano y error técnico;
- confirmar que HU-010/HU-011 cubren el MVP S1;
- confirmar que HU-012/HU-013/HU-014 no se declaran TRL 4 sin entorno real limitado y usuarios internos;
- verificar que A1 recibe insumos de otros agentes sólo como entrada, no como orquestador.

Evidencia de salida:

- resultados de casos de prueba;
- outputs generados;
- logs;
- defectos detectados.

### F3 - Auditoría de evidencia y trazabilidad

**Objetivo:** comprobar que cada acción relevante puede reconstruirse.

Actividades:

- tomar una muestra de ejecuciones y rastrear: fuente -> solicitud -> prompt/plantilla -> output -> validación -> estado final;
- verificar correlation ID o identificador equivalente;
- revisar que logs no contengan secretos ni datos sensibles innecesarios;
- verificar enlaces a Docs, PDFs, emails o capturas;
- controlar que cada evidencia tenga fecha, responsable, HU y estado.

Evidencia de salida:

- índice de evidencias;
- muestra trazada;
- hallazgos de trazabilidad.

### F4 - Auditoría de calidad y seguridad

**Objetivo:** verificar controles de conformidad, seguridad y prevención de fallas críticas.

Actividades:

- revisar checklist SEU de precisión factual, tono institucional, plantilla y canal;
- revisar registro de defectos, severidad, prioridad, estado y re-prueba;
- verificar RBAC en Google Workspace, permisos de cuentas y principio de privilegio mínimo;
- auditar gestión de secretos: `.env`, Properties Service, tokens, credenciales y ausencia de claves hardcoded;
- probar prompt injection directo e indirecto desde Sheets, Gmail, Docs o texto de entrada;
- verificar que el LLM no tenga permisos directos sobre Google APIs;
- revisar inventario de activos IA, modelos, prompts, propietarios y versiones;
- confirmar que cualquier API externa sea contingencia aprobada, con datos anonimizados y registro.

Evidencia de salida:

- checklist de seguridad;
- reporte de pruebas adversariales;
- matriz de permisos;
- inventario de activos;
- defectos de seguridad.

### F5 - Informe y plan de mejora

**Objetivo:** emitir conclusión, hallazgos, recomendaciones y plan de acción.

Actividades:

- clasificar hallazgos por severidad;
- definir recomendación razonable y útil para la organización;
- registrar responsable y fecha objetivo, si está confirmada;
- pedir opinión del área auditada cuando corresponda;
- definir si se requiere reauditoría;
- emitir veredicto final del gate.

Evidencia de salida:

- informe de auditoría;
- registro de acciones correctivas;
- decisión de gate;
- fecha tentativa de reauditoría si aplica.

## 9. Matriz núcleo de auditoría

| Elemento | BPM | HU / CU | DoD auditado | Evidencia requerida | Responsable | Resultado | Hallazgo |
|---|---|---|---|---|---|---|---|
| Gacetilla institucional | P4 | HU-010 / CU-A1-01 | Sheet, Google Docs, plantilla, < 30 s, validación | Doc generado, log, checklist, estado Sheet | RGC / Coordinador | Pendiente | Pendiente |
| Post RRSS | P4 | HU-011 / CU-A1-02 | Canal, longitud, texto limpio, sin alucinaciones, validación | Borrador por canal, log, checklist RRSS | RRSS / RGC | Pendiente | Pendiente |
| Confirmación de inscripción | P5/P4 | HU-012 / CU-A1-03 | Trigger, email, registro, duplicados, errores | Email recibido, fila actualizada, log de envío | Cursos / Personal SEU | Pendiente | Pendiente |
| Lenguaje natural interno | P4/P3 | HU-013 / CU-A1-04 | Email + invitación a chat, respuesta usable, registro en Sheets | Captura/transcript, registro Sheet, log | Coordinación / RGC | Pendiente | Pendiente |
| Certificado | P5 | HU-014 / CU-A1-05 | Plantilla, PDF, aprobación previa, log | PDF, aprobación, estado, log | Coordinación / Administración | Pendiente | Pendiente |
| Validación humana | Transversal | CU-A1-06 / RF-A1-09 | No publicar, enviar ni emitir sin aprobación | Checklist, validador, fecha, decisión, observación | SEU | Pendiente | Pendiente |
| Trazabilidad | Transversal | CU-A1-07 / RNF-A1-04 | Acción reconstruible | Correlation ID, links, logs, versiones | Responsable técnico IA | Pendiente | Pendiente |
| Seguridad base | Transversal | RNF seguridad | RBAC, secretos, NHI, PoLP, prompt injection | Checklist seguridad, matriz permisos, pruebas adversariales | Responsable técnico IA | Pendiente | Pendiente |
| TRL 3 | Gate S1 | HU-010 / HU-011 | Entorno controlado, caso simple validado | Outputs, pruebas, checklist SEU, informe G2 | Director / Juan Ignacio Gone | Pendiente | Pendiente |
| TRL 4 | Gate S2 | HU-010 a HU-014 | Entorno real limitado, usuarios internos, integración base | Paquete G4, acta, logs, validaciones | Director / SEU | Pendiente | Pendiente |

## 10. Checklist por eje

### 10.1 Alcance

- [ ] La funcionalidad auditada mapea a P4 o apoyo acotado P3/P5/P6.
- [ ] No incorpora scraping, analítica, dashboard, atención pública ni soporte administrativo general.
- [ ] A1 no decide ni coordina el flujo de otros agentes.
- [ ] Las integraciones A2-A5 son entradas de contenido o datos, no responsabilidades absorbidas.
- [ ] Las expansiones fuera de HU-010 a HU-014 quedan marcadas como continuidad o backlog P100.

### 10.2 Validación humana

- [ ] La salida queda en estado `borrador`, `pendiente`, `observado`, `rechazado` o `aprobado`.
- [ ] La publicación, envío crítico o emisión sólo avanza con estado `aprobado`.
- [ ] La aprobación registra usuario validador, fecha, decisión y observación.
- [ ] Los rechazos generan retrabajo controlado o edición manual.
- [ ] Certificados y comunicaciones oficiales nunca se emiten sin aprobación previa.

### 10.3 Evidencia y trazabilidad

- [ ] Cada ejecución tiene identificador estable.
- [ ] El registro vincula fuente, usuario, HU, tipo de pieza, versión de prompt, plantilla, output y estado.
- [ ] La evidencia permite reconstruir qué se generó, con qué datos y quién lo validó.
- [ ] Los logs no exponen secretos ni información sensible innecesaria.
- [ ] La evidencia está indexada con nomenclatura estable.

### 10.4 Calidad funcional

- [ ] La pieza generada es clara y usable.
- [ ] El texto respeta tono institucional.
- [ ] El contenido no inventa datos faltantes.
- [ ] El formato se adapta al canal.
- [ ] La prueba cubre datos completos, datos incompletos, rechazo y error técnico.
- [ ] Los defectos se registran con severidad, prioridad, estado y re-prueba.

### 10.5 Seguridad

- [ ] Las credenciales no están hardcoded ni expuestas en repositorio o logs.
- [ ] Existen roles y permisos mínimos en Workspace y backend.
- [ ] Las identidades no humanas tienen propietario y ciclo de vida.
- [ ] Las entradas externas se sanitizan.
- [ ] Se ejecutaron pruebas de prompt injection.
- [ ] El modelo local no tiene acceso directo a acciones críticas.
- [ ] Cualquier fallback externo está aprobado, anonimizado y registrado.

### 10.6 TRL y liberación

- [ ] TRL 3 se demuestra con HU-010/HU-011 funcionando en entorno controlado.
- [ ] TRL 4 se demuestra con HU-010 a HU-014 funcionando en entorno real limitado.
- [ ] No hay defectos críticos abiertos.
- [ ] Los casos críticos de prueba fueron ejecutados.
- [ ] Existe manual o documentación mínima de uso.
- [ ] El paquete de evidencia del gate está completo.

## 11. Métricas de auditoría

| ID | Métrica | Fórmula / medición | Umbral | Momento |
|---|---|---|---|---|
| MA-01 | Validación humana registrada | piezas oficiales aprobadas / piezas oficiales publicadas, enviadas o emitidas | 100% | Por gate y release |
| MA-02 | Trazabilidad completa | acciones con log completo / acciones auditadas | 100% en S2 | Por muestra |
| MA-03 | Defectos críticos abiertos | cantidad de defectos críticos sin cerrar | 0 | Antes de liberar |
| MA-04 | Cumplimiento DoD | checks DoD cumplidos / checks DoD aplicables | 100% para HU cerrada | Por HU |
| MA-05 | Checklist SEU | promedio escala 1-4 | >= 3/4 | G2/G4 |
| MA-06 | Rendimiento | tiempo trigger -> output | < 30 s para contenido | Prueba funcional |
| MA-07 | Rechazo de borradores | borradores rechazados / borradores generados | <= 20% al cierre S2 | Mensual en S2 |
| MA-08 | Seguridad base | controles críticos cumplidos / controles críticos definidos | 100% | Antes de release |
| MA-09 | Cobertura de prueba | casos ejecutados / casos planificados | Pendiente de umbral formal; no liberar con casos críticos sin ejecutar | Por gate |
| MA-10 | Riesgos altos controlados | riesgos altos con mitigación vigente / riesgos altos abiertos | 100% | Revisión de riesgos |

## 12. Muestra mínima recomendada

| Gate | Muestra mínima | Criterio de selección | Observación |
|---|---|---|---|
| Pre-G2 | 1 gacetilla, 1 post, 1 caso de datos incompletos, 1 rechazo humano | HU-010/HU-011 y controles transversales | Puede usar datos controlados si se declara explícitamente |
| G2 | 2 gacetillas, 2 posts, logs, checklist, defectos y evidencia TRL 3 | Salidas distintas y validador registrado | Debe demostrar entorno controlado |
| Pre-G4 | 1 confirmación, 1 interacción LN, 1 certificado, 1 prueba adversarial | HU-012/HU-013/HU-014 y seguridad | Debe incluir integración base y persistencia |
| G4 | Muestra de HU-010 a HU-014, validación SEU, logs, pruebas, defectos, seguridad | Entorno real limitado y usuarios internos | Debe demostrar TRL 4 |
| Extraordinaria | Acciones relacionadas con incidente o cambio | Riesgo materializado, hallazgo crítico o cambio de alcance | Puede ser parcial |

## 13. Registro de hallazgos

| Severidad | Definición | Efecto |
|---|---|---|
| Crítica | Publica/envía/emite sin validación, inventa información crítica, expone credenciales, pierde trazabilidad o declara TRL sin evidencia | Bloquea release y gate |
| Alta | Afecta flujo principal, seguridad, integración, responsable o evidencia esencial | Debe corregirse antes del gate |
| Media | Afecta flujo alternativo, formato, completitud documental o usabilidad sin comprometer seguridad ni evidencia crítica | Puede cerrarse con plan de acción |
| Baja | Mejora menor, redacción, orden documental o evidencia complementaria | No bloquea si queda registrada |

Formato de hallazgo:

| Campo | Descripción |
|---|---|
| ID | `AUD-A1-YYYY-NNN` |
| Situación detectada | Qué se observó, con evidencia |
| Criterio vulnerado | DoD, BPM, seguridad, TRL, HITL, RACI u otro |
| Riesgo / consecuencia | Impacto si no se corrige |
| Severidad | Crítica, alta, media o baja |
| Recomendación | Acción razonable que agrega valor |
| Responsable | Rol institucional o técnico |
| Estado | Abierto, en corrección, corregido, aceptado con riesgo, cerrado |
| Evidencia | Enlace, log, captura, documento o prueba |
| Opinión del área auditada | Comentario de SEU, técnico o director si aplica |
| Reauditoría | Sí / no, fecha tentativa si corresponde |

## 14. Hallazgos potenciales iniciales

Estos hallazgos no se consideran incumplimientos confirmados hasta ejecutar una auditoría formal, pero deben vigilarse desde la preparación.

| ID | Hallazgo potencial | Riesgo | Recomendación |
|---|---|---|---|
| HP-01 | HU-013 puede quedar desalineada entre formulaciones antiguas y criterio vigente | Implementar interfaz equivocada | Auditar HU-013 como email + invitación a chat + registro en Sheets |
| HP-02 | El rol de hub puede interpretarse como orquestación | Sobrealcance y pérdida de defendibilidad | Mantener A1 como consumidor de insumos A2-A5 |
| HP-03 | HU-012 puede automatizar envío sin control suficiente | Comunicación incorrecta o no auditable | Exigir plantilla aprobada, datos validados, registro de envío y control de errores |
| HP-04 | Evidencia tardía o incompleta | TRL no demostrable | Diseñar logs e índice de evidencia desde S1 |
| HP-05 | Métricas de comunicación pueden confundirse con dashboards A5 | Invasión de analítica | Separar logs/evidencia A1 de análisis/KPIs A5 |
| HP-06 | Seguridad declarativa sin prueba | Riesgo de credenciales, permisos o prompt injection | Pedir pruebas concretas de RBAC, secretos, NHI y casos adversariales |
| HP-07 | Plantillas y campos de Sheets pendientes | Pruebas no concluyentes | Bloquear cierre de G1/G2 si no hay esquema mínimo y plantilla validable |
| HP-08 | Responsables nominales no confirmados | Aprobaciones informales | Usar roles institucionales y marcar nombres como pendiente |

## 15. Cadencia

| Momento | Tipo de auditoría | Objetivo | Salida |
|---|---|---|---|
| Antes de iniciar una HU | Revisión de preparación | Confirmar DoD, datos, plantilla, validadores y riesgos | Decisión iniciar / bloquear / spike |
| Antes de G2 | Auditoría parcial S1 | Verificar preparación de evidencia TRL 3 | Lista de bloqueantes |
| G2 | Auditoría de gate TRL 3 | Validar HU-010/HU-011 en entorno controlado | Informe G2 |
| Mitad S2 | Auditoría de automatización | Revisar HU-012/HU-013, logs y seguridad | Informe de riesgos residuales |
| Antes de G4 | Auditoría pre-release | Detectar defectos críticos antes del cierre | Plan correctivo |
| G4 | Auditoría de gate TRL 4 | Validar HU-010 a HU-014 con usuarios internos | Informe G4 y decisión |
| Post-incidente | Auditoría extraordinaria | Revisar causa, impacto y corrección | Informe de incidente y re-prueba |

## 16. Entregables

1. Plan de auditoría vigente.
2. Checklist de auditoría por HU.
3. Matriz BPM-HU-CU-DoD-evidencia-responsable auditada.
4. Registro de hallazgos.
5. Informe de auditoría G2/G4.
6. Índice de evidencias.
7. Registro de acciones correctivas.
8. Acta o decisión de gate TRL.
9. Recomendación de reauditoría cuando existan hallazgos críticos o altos.

## 17. Formato de informe de auditoría

```markdown
# Informe de auditoría - Agente 1 Extension Bot

**Fecha:** Pendiente
**Auditor:** Pendiente
**Gate / versión auditada:** Pendiente
**Alcance:** Pendiente
**Muestra:** Pendiente

## Veredicto

APROBADO / APROBADO CON OBSERVACIONES / REQUIERE REVISIÓN / BLOQUEADO

## Resumen ejecutivo

Pendiente.

## Evidencia revisada

| Evidencia | HU / eje | Resultado | Observación |
|---|---|---|---|
| Pendiente | Pendiente | Pendiente | Pendiente |

## Hallazgos

| ID | Severidad | Situación detectada | Riesgo | Recomendación | Responsable | Estado |
|---|---|---|---|---|---|---|
| Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Abierto |

## Opinión del área auditada

Pendiente.

## Decisión de gate

Pendiente.

## Acciones correctivas

| Acción | Responsable | Fecha objetivo | Evidencia de cierre |
|---|---|---|---|
| Pendiente | Pendiente | Pendiente | Pendiente |

## Reauditoría

Sí / No. Motivo y fecha tentativa: Pendiente.
```

## 18. Acciones inmediatas recomendadas

| Prioridad | Acción | Reduce riesgo | Responsable | Momento sugerido |
|---|---|---|---|---|
| P0 | Crear checklist SEU formal por tipo de pieza | HITL, calidad, TRL | Juan Ignacio Gone + SEU | Antes de G2 |
| P0 | Definir índice de evidencias y nomenclatura | Trazabilidad, CONEAU | Juan Ignacio Gone | Antes de prototipos HU-010/HU-011 |
| P0 | Definir esquema mínimo de log con correlation ID | Trazabilidad, seguridad | Responsable técnico IA | Antes de ejecutar MVP |
| P0 | Cerrar campos mínimos de Sheets y plantillas HU-010/HU-011 | Requisitos, calidad | Juan Ignacio Gone + SEU | Antes de declarar TRL 3 |
| P1 | Preparar casos adversariales de prompt injection | Seguridad | Responsable técnico IA | Antes de G2 |
| P1 | Documentar matriz RBAC y credenciales/NHI | Seguridad, auditoría | Responsable técnico IA | Antes de release |
| P1 | Medir baseline manual de gacetilla/post | Métricas de beneficio | Juan Ignacio Gone + SEU | Antes de afirmar reducción de tiempo |
| P1 | Definir contratos mínimos A2-A5 -> A1 | Alcance, integración | Responsable técnico IA / pares P100 | Antes de integración S2 |

## 19. Pendientes de confirmación

- Fechas oficiales de entrega, defensa y gates académicos.
- Personas nominales para Coordinador, Responsable de Gestión del Conocimiento, Responsable RRSS, administración, validadores y soporte técnico.
- Plantillas institucionales finales de gacetilla, post, mail, newsletter y certificado.
- Campos exactos y permisos de Google Sheets.
- Entorno disponible para Ollama, FastAPI, Google Workspace, Apps Script, PostgreSQL, Celery y Redis.
- Herramienta final para registro de hallazgos, defectos, riesgos y evidencias: Google Sheets, Jira, repositorio Markdown u otra definida por la cátedra/SEU.
- Criterio de muestra para validación SEU y baseline manual.

## 20. Conclusión

El Agente 1 tiene una base documental suficiente para iniciar auditoría interna: alcance, historias, casos de uso, calidad, riesgos, cronograma, métricas y trazabilidad están definidos en artefactos separados pero coherentes. La debilidad principal no es conceptual, sino operativa: falta convertir la validación humana, los logs, las evidencias, los responsables y los controles de seguridad en instrumentos verificables antes de los gates TRL.

La auditoría debe funcionar como control de cierre y como herramienta preventiva. Si se aplica desde S1, permite evitar los fallos más probables: declarar TRL sin evidencia, expandir el alcance de A1, validar por canales informales, publicar sin aprobación o llegar al informe final con documentación correcta pero sin prueba recuperable.
