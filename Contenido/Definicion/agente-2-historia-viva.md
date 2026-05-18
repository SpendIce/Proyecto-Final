# Agente 2 — Historia Viva / Centenario AI

## Definicion oficial del Proyecto Centenario (P100)

Documento de referencia consolidado con toda la informacion extraida de los archivos oficiales de la bible del proyecto.

---

## 1. Identidad del agente

| Campo | Valor |
|-------|-------|
| **Nombre oficial** | Agente 2 — Historia Viva |
| **Nombre alternativo** | Centenario AI |
| **Codigo interno** | A2 |
| **Proceso asociado** | Proceso 7 — Gestion del Conocimiento y Memoria Institucional |
| **Tipo de proceso** | Continuo — acumulativo |
| **Epic en backlog** | EPIC E4 — Agente 2 (Historia Viva) |

---

## 2. Proposito

Registrar, organizar y explotar el conocimiento institucional de la Facultad de Ingenieria del Ejercito (FIE). Funciona como el repositorio historico inteligente de la Secretaria de Extension Universitaria (SEU), permitiendo la ingesta, indexacion semantica, recuperacion y reutilizacion de documentos institucionales.

---

## 3. Funciones principales (segun documentacion oficial)

### 3.1 Ingesta de documentos institucionales
- Carga de documentos historicos al repositorio
- Soporte para multiples formatos (PDF, DOCX, etc.)
- Almacenamiento en Google Drive / Nextcloud institucional

### 3.2 Indexacion semantica
- Indexacion basica y avanzada de documentos
- Busqueda semantica sobre el corpus institucional
- Metadatos obligatorios: fecha, tipo, origen

### 3.3 Generacion de contenido historico
- Generacion automatica de efemerides institucionales
- Produccion de contenidos historicos para difusion
- Apoyo a la reconstruccion de la historia institucional

### 3.4 Recuperacion inteligente de informacion
- Busqueda y consulta sobre el repositorio
- Recuperacion de contenido relevante para reutilizacion
- Respuestas basadas en documentos indexados

---

## 4. Alcance funcional (seccion 1.3 del documento de alcance)

Textual de la documentacion oficial:

> **B. Repositorio historico (Agente 2)**
> - Ingesta de documentos institucionales
> - Indexacion semantica
> - Generacion de: efemerides, contenidos historicos
> - Recuperacion inteligente de informacion

---

## 5. Proceso asociado: Proceso 7 — Gestion del Conocimiento y Memoria Institucional

### Modelo
Continuo — acumulativo

### Objetivo del proceso
Registrar, organizar y explotar conocimiento institucional.

### Control de calidad
- Repositorio actualizado
- Accesibilidad
- Trazabilidad historica

### RACI del proceso

| Rol | Responsabilidad |
|-----|----------------|
| Coordinador de Extension | **A** |
| Responsable de Gestion del Conocimiento de Extension | **R** |
| Directores de carrera | **C** |
| Secretario de Extension | **I** |

**Nota tecnica:** el Responsable Tecnico de Sistemas / Automatizacion participa en la implementacion y mantenimiento de infraestructura, pero la RACI institucional del Proceso 7 queda centrada en coordinacion y gestion del conocimiento.

---

## 6. Software asociado (mapeo oficial)

### Herramientas principales
- Google Drive (repositorio central)
- Google Docs (documentacion estructurada)
- Google Sites (portal historico)

### Open source complementario
- PostgreSQL (indexacion avanzada)

---

## 7. Infraestructura tecnica

### Stack tecnologico definido
- **LlamaIndex** — framework para indexacion y recuperacion semantica (RAG)
- **PostgreSQL** — base de datos para indexacion avanzada
- **Ollama** — motor de IA local para generacion de contenido
- **Nextcloud / Google Drive** — almacenamiento de documentos
- **Docker** — contenedorizacion (opcional en Ano 1)
- **Python + FastAPI** — backend
- **Celery + Redis** — orquestacion asincronica

### Modelo de IA
- Ejecucion local con Ollama
- Modelos livianos: LLaMA 3 8B / Mistral 7B
- Sin dependencia de APIs externas de pago (principio de soberania de datos)

---

## 8. Historias de usuario (backlog oficial)

### HU-030 (P1, 8 SP) — Indexar documentos historicos

**Como** Secretaria
**quiero** indexar documentos historicos
**para** su reutilizacion

**DoD:**
- Carga en Drive
- Indexacion basica

### HU-031 (P2, 5 SP) — Generar efemerides

**Como** sistema
**quiero** generar efemerides
**para** difusion institucional

### DoD especifico para historias de Repositorio (tipo 2.4)

- Documento almacenado correctamente
- Metadatos completos: fecha, tipo, origen
- Indexacion funcional (busqueda posible)
- Recuperacion de contenido correcta
- No duplicacion de registros
- Validacion con caso real de consulta

---

## 9. Cronograma de implementacion

| Semestre | Estado | TRL | Actividad |
|----------|--------|-----|-----------|
| S1 (Ano 1) | No incluido | — | No forma parte del MVP |
| **S2 (Ano 1)** | **Implementacion** | **TRL 4** | Repositorio historico institucional |
| S3-S4 (Ano 2) | Consolidacion | TRL 5-6 | Integracion total con demas agentes |

### Nota del director de carrera (mail del 20/03/2026)
> "El Agente 2 todavia no se ha definido en cuanto a prioridad. Cuando lo determine con la Secr Ext, te pasare informacion."

Esto indica que la prioridad del Agente 2 esta sujeta a definicion con la Secretaria de Extension. No es parte del MVP del Semestre 1.

---

## 10. Interacciones con otros agentes

### Agente 2 como ORIGEN (envia datos a otros)

| Destino | Proposito |
|---------|-----------|
| **Agente 1 (Extension Bot)** | Contenido historico para difusion |

### Agente 2 como DESTINO (recibe datos de otros)

No se definen interacciones explicitas donde el Agente 2 reciba datos de otros agentes. Su input principal es:
- Documentos subidos a Google Drive
- Triggers automaticos al detectar nuevos documentos

### Flujo de orquestacion (Flujo 3)

1. Documento se sube a Drive
2. Trigger activa al Agente 2
3. Indexacion del documento
4. Generacion de contenido (efemerides, resumen, etc.)

---

## 11. Validacion con la Secretaria (checklist oficial)

### Carga de informacion
- Es facil cargar documentos o informacion
- No se pierden datos relevantes

### Busqueda y uso
- Se puede encontrar informacion rapidamente
- Los contenidos recuperados son utiles
- Permite reutilizar informacion institucional

### Valor institucional
- Ayuda a reconstruir historia institucional
- Apoya la generacion de contenidos (ej. efemerides)

### Tabla de validacion oficial

| ID | Historia | Tipo | Validacion | Instrumento | Evidencia | Responsable |
|----|----------|------|------------|-------------|-----------|-------------|
| HU-030 | Repositorio documental | Datos | Carga simple | Prueba real | Documento cargado | Coordinacion |
| HU-031 | Recuperacion de info | Conocimiento | Se encuentra info relevante | Caso de uso | Resultado busqueda | Coordinacion |

---

## 12. Criterios de aceptacion transversales

- Integracion con Google Workspace
- Logs activos
- Validacion por Secretaria
- Tiempos de ejecucion aceptables
- Calidad del output (contenido o datos)

---

## 13. Exclusiones (aplican a todo el sistema)

- No reemplazo del personal
- No automatizacion sin validacion humana en contenidos criticos
- No infraestructura de alto costo
- No integracion con sistemas externos complejos no definidos

---

## 14. Dependencias clave

- **HU-001** (estructura base en Drive/Sheets) — prerequisito obligatorio
- **HU-002** (automatizaciones Apps Script) — necesario para triggers
- Disponibilidad de documentos historicos digitalizados
- Configuracion de LlamaIndex + PostgreSQL

---

## 15. Riesgos identificados

| Riesgo | Mitigacion |
|--------|-----------|
| Documentos historicos no digitalizados | Plan de digitalizacion progresiva |
| Calidad variable de documentos | Normalizacion en ingesta |
| Prioridad aun no definida por SEU | Comenzar diseno mientras se define |
| Dependencia de LlamaIndex | Modularidad, abstraccion del framework |
| Volumen de datos creciente | PostgreSQL escalable |

---

## 16. Nivel TRL esperado

| Nivel | Descripcion | Criterio |
|-------|-------------|----------|
| TRL 3 | Prueba de concepto | Funciona en entorno controlado, caso simple validado |
| **TRL 4** | **Prototipo** | **Funciona en entorno real limitado, integrado con sistema base, validado por usuarios internos** |
| TRL 5 | Validacion operativa | Usado en procesos reales, estable, usuarios lo adoptan |
| TRL 6 | Operacion consolidada | Funciona de forma sostenida, metricas de impacto disponibles |

Meta para fin de Ano 1: **TRL 4**

---

## 17. Fuentes de esta documentacion

- `Contenido/bible/Procesos y Agentes.md` — definiciones de procesos, mapeo agentes-procesos, backlog, DoD, infraestructura
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.pdf` — mail del director de carrera con asignaciones y prioridades
- `Contenido/bible/mailinstitucional.pdf` — mismo correo institucional
