# Criterios de Evaluacion — Director de Carrera (Cicerchia)

Documento de referencia que consolida los criterios con los que el CR(R) Ing Cesar Daniel Cicerchia evalua el Proyecto Centenario (P100). Extraido de la bible oficial del proyecto, actualizada con el PDF `Contenido/bible/Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`.

---

## 1. Alineacion CONEAU

Toda decision de diseno o implementacion debe poder justificarse frente a una evaluacion universitaria:

- **Trazabilidad documental completa** — cada funcionalidad tiene evidencia verificable
- **Indicadores sistematicos** — no basta con que funcione, debe poder medirse
- **Evidencia de uso** — logs, outputs, registros de validacion
- **Documentacion funcional** — manual breve de usuario, documentacion minima
- **Validacion formal registrada** — actas, checklists firmados, capturas

### Vicios a evitar (criterio CONEAU)
- Actividades sin registro ni evaluacion
- Dependencia de personas clave (no institucionalizado)
- Falta de indicadores
- Comunicacion informal o inconsistente
- Ausencia de integracion con docencia e investigacion
- Baja trazabilidad documental

---

## 2. Mapeo obligatorio a procesos BPM

Toda funcionalidad del sistema debe trazar a uno de los 9 procesos definidos:

| # | Proceso | Tipo | Agente asociado |
|---|---------|------|-----------------|
| 1 | Planificacion Estrategica de Extension | Estrategico — ciclico anual (PDCA) | A5 |
| 2 | Vinculacion con el medio (Institucional y Jurisdiccional) | Relacional — continuo | A3 |
| 3 | Diseno y Gestion de Actividades de Extension | Operativo — por proyectos | A1 |
| 4 | Comunicacion y Difusion Institucional | Continuo — multicanal | A1 |
| 5 | Gestion de Programas, Cursos y Diplomaturas | Ciclo completo | A1, A4 |
| 6 | Gestion de Eventos Academicos | Por evento (tipo proyecto) | A3, A1 |
| 7 | Gestion del Conocimiento y Memoria Institucional | Continuo — acumulativo | A2 |
| 8 | Monitoreo, Evaluacion y Mejora Continua | Analitico — continuo | A5 |
| 9 | Atencion a la Comunidad y Aspirantes / postulantes | Servicio — multicanal | A4 |

**Regla:** si una funcionalidad no mapea a ningun proceso, no pertenece al alcance. Si mapea a un proceso pero se asigna al agente incorrecto, hay una inconsistencia.

Cada proceso tiene su RACI definido. Las funcionalidades deben respetar la responsabilidad asignada en la tabla RACI del proceso correspondiente.

### Capa transversal de soporte

La version ampliada previa de la bible agregaba una capa de **Interfaces de Soporte Inter-secretaria** para canalizar tareas administrativas ajenas a la funcion sustantiva de extension hacia el Dpto. Apoyo. Incluye, entre otros, orden del dia, ceremonial y protocolo, planes de necesidades de adquisiciones, proveedores del Estado, presupuestos preliminares, aprovisionamiento e inventarios. Esa capa no aparece en el PDF vigente de 16 paginas enfocado en Agente 1; si se reactivara, no debe confundirse con el nucleo sustantivo del P100.

---

## 3. Exclusiones del sistema (lineas rojas)

Estas exclusiones son **no negociables**:

1. **No reemplazo del personal** — el sistema asiste, no sustituye
2. **No automatizacion sin validacion humana en contenidos criticos** — siempre hay un paso de revision humana
3. **No infraestructura de alto costo** — prioridad a open source, Google Workspace institucional, ejecucion local
4. **No integracion con sistemas externos complejos no definidos** — solo lo que esta explicitamente en el alcance

---

## 4. Progresion TRL (Technology Readiness Level)

No se aceptan promesas. Se exige evidencia por nivel:

| TRL | Nombre | Criterio de evidencia |
|-----|--------|----------------------|
| 3 | Prueba de concepto | Funciona en entorno controlado, caso simple validado, sin necesidad de robustez total |
| 4 | Prototipo | Funciona en entorno real limitado, integrado con sistema base, validado por usuarios internos |
| 5 | Validacion operativa | Usado en procesos reales, estable en multiples ejecuciones, usuarios lo adoptan |
| 6 | Operacion consolidada | Funciona de forma sostenida, metricas de impacto disponibles, sin intervencion tecnica constante |

### Cronograma TRL por semestre
- **S1 (Ano 1):** TRL 3 — prototipos funcionales basicos
- **S2 (Ano 1):** TRL 4 — validacion en entorno real interno
- **S3 (Ano 2):** TRL 5 — operacion real + interaccion externa
- **S4 (Ano 2):** TRL 6 — consolidacion, analitica y escalado

---

## 5. Restricciones tecnologicas

### Prioridades (en orden)
1. **Google Workspace institucional (UNDEF)** — plataforma central
2. **Open source liviano** — complemento obligatorio
3. **Bajo costo** — base gratuita, erogaciones excepcionales y controladas
4. **Soberania de datos** — ejecucion local con Ollama, modelos livianos (LLaMA 3 8B, Mistral 7B)
5. **Sin dependencia de APIs externas de pago** como base (uso experimental/comparativo permitido)

### Stack validado
- Python + FastAPI (backend)
- PostgreSQL (datos)
- Ollama (IA local)
- LangChain / LlamaIndex (frameworks RAG)
- Docker (contenedorizacion)
- Celery + Redis (orquestacion asincronica)
- Google Apps Script (automatizacion ligera)
- Metabase / Looker Studio (visualizacion)

---

## 6. Criterios de aceptacion transversales

Toda historia de usuario, sin excepcion, debe cumplir:

- Integracion con Google Workspace
- Logs activos
- Validacion por Secretaria
- Tiempos de ejecucion aceptables
- Calidad del output (contenido o datos)
- Cuando involucra datos institucionales, integridad verificable entre CONEAU GLOBAL, SIU y/o repositorio de Memoria Institucional, segun corresponda

---

## 7. Definition of Done (DoD)

### DoD Global (base obligatoria para TODAS las historias)

Una historia se considera DONE solo si cumple:

- Implementacion funcional completa
- Sin errores criticos en ejecucion
- Logs registrados
- Integracion con el sistema (Sheets / APIs / agentes)
- Documentacion minima (que hace, como usarlo)
- Pruebas realizadas
- Validacion por usuario de la Secretaria (cuando aplica)

### DoD por tipo de historia

| Tipo | Criterios adicionales clave |
|------|---------------------------|
| Automatizacion | Trigger configurado, ejecucion sin intervencion manual, manejo de errores, sin duplicaciones, 2 ejecuciones reales validadas |
| Integracion API | API oficial (no scraping no autorizado), OAuth implementado, rate limits manejados, datos completos sin truncamiento, normalizacion UTF-8 |
| Generacion de contenido | Texto coherente, formato institucional, sin hallucinations, al menos 1 validacion por usuario |
| Repositorio | Documento almacenado, metadatos completos (fecha/tipo/origen), indexacion funcional, sin duplicacion, validacion con caso real |
| Datos/Sheets | Columnas exactas, tipos consistentes, sin caracteres corruptos, compatible con dashboards, ejemplo real cargado |
| Dashboards/KPIs | Fuente conectada, KPIs calculados correctamente, visualizaciones legibles, actualizacion automatica |
| Atencion/Chatbot | Respuestas correctas para casos frecuentes, lenguaje adecuado, fallback implementado, registro de interaccion |
| Seguridad | Control de permisos, credenciales no expuestas, acceso restringido por rol |
| Orquestacion | Flujo end-to-end sin intervencion manual, logs punta a punta, sin perdida de datos en transito |

### DoD para auditoria (CONEAU)

Cuando aplique, agregar:
- Evidencia de uso (logs, outputs)
- Documentacion funcional
- Manual breve de usuario
- Trazabilidad de datos
- Validacion formal registrada

### DoD transversal agregado

La version ampliada previa de la bible explicita dos criterios transversales:

- **Validacion de integridad institucional:** las historias que cruzan sistemas institucionales deben verificar consistencia y trazabilidad del dato.
- **DoD de datos para Agente 5:** completitud, metadatos obligatorios, normalizacion y compatibilidad con dashboards/reportes son parte del cierre de historias de monitoreo.

---

## 8. Estrategia de desarrollo iterativa

Cicerchia define 5 etapas por ciclo iterativo:

1. **Relevamiento y analisis de necesidades institucionales** — entrevistas y talleres con personal de la SEU para identificar procesos criticos, tareas repetitivas, flujos de informacion
2. **Diseno conceptual y funcional de los agentes** — arquitectura modular, roles de cada agente, entradas/salidas, criterios de interaccion
3. **Prototipado y desarrollo incremental** — tecnologias de bajo costo, modelos de lenguaje livianos, open source, desarrollo incremental desde agente basico hacia avanzados
4. **Validacion en entorno real** — prueba en situaciones reales de la Secretaria: desempeno, utilidad, impacto operativo, aceptacion por usuarios
5. **Ajuste, documentacion y transferencia** — documentacion tecnica y operativa, manuales de uso para personal no tecnico, facilitar adopcion y sostenibilidad

---

## 9. Validacion con la SEU (checklist)

### Validaciones funcionales
- Calidad de textos generados
- Exactitud de datos RRSS
- Utilidad de dashboards
- Pertinencia de respuestas

### Validaciones operativas
- Tiempo de ejecucion
- Facilidad de uso
- Integracion con procesos actuales

### Validaciones estrategicas
- Mejora en productividad
- Incremento de difusion
- Mejora en toma de decisiones

### Escala de validacion
1 = No cumple | 2 = Cumple parcialmente | 3 = Cumple adecuadamente | 4 = Cumple completamente

### Instrumento por historia

Cada HU tiene definido: validacion (usuario), instrumento, evidencia y responsable. Ver tabla completa en `Contenido/bible/Procesos y Agentes.md`, seccion "Validacion con SEU".

---

## 10. Dependencias clave del sistema

- **HU-001** → base de toda la estructura (Drive/Sheets)
- **HU-002** → base de todas las automatizaciones (Apps Script)
- **HU-020** → requiere APIs habilitadas
- **HU-024** → requiere datos previos
- **HU-025** → integridad SIU / CONEAU GLOBAL / repositorio de Memoria Institucional, cuando se alcance esa integracion
- **HU-015, HU-052, HU-060** → historias agregadas en version ampliada previa sobre ceremonial, ventanilla virtual de egresados y soporte administrativo; requieren validacion de alcance antes de incorporarlas al MVP

---

## 11. Priorizacion oficial (Ano 1)

### Semestre 1 (MVP)
- E1 (plataforma base completa)
- E2 parcial (HU-010, HU-011 — comunicacion automatizada)
- E3 parcial (HU-020, HU-021, HU-022 — extraccion RRSS)

### Semestre 2
- E2 (resto de Agente 1)
- E3 (dashboards + alertas)
- E4 (inicio repositorio — Agente 2)

### Historias agregadas fuera del MVP base en version ampliada previa
- **HU-015:** Gestion de ceremonial y protocolo con control humano, asociada al Agente 3.
- **HU-025:** Registro e integridad CONEAU, asociada al Agente 5.
- **HU-052:** Ventanilla virtual de egresados, asociada al Agente 4.
- **HU-060:** Optimizacion burocratica de soporte administrativo, dentro de la capa de soporte inter-secretaria.

Estas historias no aparecen en la version vigente de 16 paginas de `Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`; tratarlas como backlog historico/ampliado hasta nueva confirmacion institucional.

---

## Fuentes

- `Contenido/bible/Procesos y Agentes.md`
- `Contenido/bible/Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.pdf`
- `Contenido/bible/mailinstitucional.pdf`
