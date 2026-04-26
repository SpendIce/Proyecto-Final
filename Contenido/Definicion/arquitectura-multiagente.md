# Arquitectura Multiagente — Proyecto Centenario (P100)

## Definicion oficial consolidada

Documento de referencia consolidado con toda la informacion de arquitectura extraida de los archivos oficiales de la bible del proyecto.

---

## 1. Descripcion del sistema

El sistema se basa en una arquitectura modular de 5 agentes inteligentes especializados, orquestados mediante mecanismos event-driven y procesos batch, integrados sobre infraestructura institucional de bajo costo. Cada agente cumple funciones especificas alineadas a los procesos de extension universitaria de la FIE, garantizando automatizacion progresiva, trazabilidad, escalabilidad y soporte a la toma de decisiones.

---

## 2. Los 5 agentes

| Codigo | Nombre | Proceso | Epic | Funcion central |
|--------|--------|---------|------|-----------------|
| A1 | Extension Bot | P4 — Comunicacion | E2 | Generar y automatizar contenido institucional |
| A2 | Historia Viva | P7 — Conocimiento | E4 | Repositorio historico, indexacion semantica, efemerides |
| A3 | Vinculacion y Congresos | P2 — Vinculacion | E5 | Monitoreo de oportunidades, reportes, contactos |
| A4 | Atencion a Futuros Estudiantes | P9 — Atencion | E6 | Respuestas automaticas multicanal |
| A5 | Analiticas de Extension | P8 — Monitoreo | E3 | Extraccion RRSS, KPIs, dashboards |

---

## 3. Modelo de orquestacion

### Principio
No hay agente central. Orquestacion basada en eventos y procesos.

### Tipo: Event-driven + Batch hibrido

| Tipo | Uso |
|------|-----|
| Event-driven | Formularios, emails, acciones de usuario |
| Batch | Extraccion RRSS, KPIs, procesos periodicos |

### Componentes

| Componente | Rol |
|------------|-----|
| Google Apps Script | Orquestador principal (triggers, automatizaciones) |
| Scheduler | Triggers time-driven y event-driven |
| APIs | Internas (Google Workspace) y externas (RRSS) |
| Google Sheets | Bus de datos entre agentes |
| Celery + Redis | Orquestacion asincronica backend |

---

## 4. Flujos de orquestacion

### Flujo 1 — Actividad → Comunicacion
Formulario → Sheets → Trigger → Apps Script → A1 → Contenido → Validacion humana → Publicacion

### Flujo 2 — RRSS → Analitica
Scheduler → A5 (SDC) → APIs RRSS → Normalizacion → Sheets (ANEXO 2) → Dashboards → Alertas

### Flujo 3 — Repositorio historico
Documento → Drive → Trigger → A2 → Indexacion → Generacion de contenido

### Flujo 4 — Vinculacion
A3 monitorea fuentes → Oportunidades → Sheets → Notificacion mail

### Flujo 5 — Atencion
Consulta (mail/web) → A4 → Respuesta automatica → Registro

### Flujo 6 — KPIs integrados
Datos (Sheets + RRSS) → A5 → Procesamiento → Looker Studio → Alertas

---

## 5. Interacciones entre agentes

| Origen | Destino | Proposito |
|--------|---------|-----------|
| A5 | A1 | Limpieza / enriquecimiento de texto de RRSS |
| A2 | A1 | Contenido historico para difusion |
| A3 | A1 | Difusion de eventos detectados |
| A4 | A1 | Generacion de respuestas complejas |

**Observacion:** A1 funciona como hub de comunicacion (recibe de A2, A3, A4, A5 para generar contenido), pero no es orquestador.

---

## 6. Interfaces tecnicas

### Entrada
- Google Forms (inscripciones, propuestas)
- Gmail (comunicacion formal, consultas)
- APIs RRSS (Meta Graph API, LinkedIn API)
- Google Drive (documentos, triggers de carga)

### Salida
- Google Sheets (datos estructurados, bus)
- Google Docs (documentos generados)
- Dashboards (Looker Studio, Metabase/Superset)
- Correos / publicaciones

---

## 7. Stack tecnologico

### Plataforma institucional
Google Workspace: Gmail, Drive, Docs, Sheets, Calendar, Forms, Meet, Sites, Apps Script

### Backend
Python 3.x, FastAPI, PyTest

### IA y NLP
Ollama (local), LLaMA 3 8B / Mistral 7B, LangChain, LlamaIndex

### Orquestacion
Google Apps Script (triggers), Celery + Redis (colas asincronicas), Cron jobs

### Bases de datos
SQLite (dev), PostgreSQL (preproduccion/produccion)

### Contenedores
Docker / Docker Compose

### Cloud (contingencia)
Render, Railway, Fly.io

### Observabilidad
Logging estructurado Python, Prometheus + Grafana (Ano 2)

### Analitica
Metabase / Apache Superset, Google Looker Studio

### Almacenamiento
Nextcloud / Google Drive, Google Sheets

---

## 8. Infraestructura por semestre

### S1 — Ano 1 (TRL 3)
- **Agentes:** A1 (inicio)
- **Infra:** Servidor local, Docker, Ollama, Google Workspace, Cron + Celery inicial, logs basicos
- **Objetivo:** Prototipo funcional

### S2 — Ano 1 (TRL 4)
- **Agentes:** A1 (consolidacion), A2 (implementacion), A5 parcial
- **Infra:** + PostgreSQL, Apps Script, Celery + Redis, LlamaIndex
- **Objetivo:** Validacion en entorno real interno

### S3 — Ano 2 (TRL 5)
- **Agentes:** + A3, A4 (implementacion)
- **Infra:** + Cloud low-cost, WhatsApp Business API, APIs IA externas
- **Objetivo:** Operacion real + interaccion externa

### S4 — Ano 2 (TRL 6)
- **Agentes:** Todos (integracion total)
- **Infra:** + Metabase/Superset completo, Prometheus/Grafana, backups externos
- **Objetivo:** Multiagente orquestado + analitica completa

---

## 9. Requisitos no funcionales

| Requisito | Criterio |
|-----------|----------|
| **Performance** | Batch RRSS < 1 min, contenido < 30s, atencion < 15s |
| **Seguridad** | APIs oficiales, credenciales seguras (.env/vault), acceso por rol |
| **Disponibilidad** | Scheduler, reintentos automaticos, tolerancia a fallos parciales |
| **Escalabilidad** | Modular, incremental, contenedores, agentes desacoplados |
| **Trazabilidad** | Logs de ejecucion/errores/resultados, auditoria CONEAU |
| **Usabilidad** | Interfaces simples (Sheets, Forms, correo), lenguaje natural interno |

---

## 10. Costos

### Ano 1 (TRL 3-4): USD 180-1.400
- Hardware/Software/IA local: $0
- Cloud: USD 0-180, APIs IA: USD 120-600, Backups: USD 60-120, HW adicional: USD 200-500

### Ano 2 (TRL 5-6): USD 780-2.900
- Hardware/Software/IA local: $0
- Cloud: USD 180-360, APIs IA: USD 360-1.200, WhatsApp: USD 120-300, Backups: USD 120-240, HW adicional: USD 300-800

---

## 11. Backlog y priorizacion

### Semestre 1 (MVP)
- E1 — Plataforma Base (HU-001, 002, 003)
- E2 — Agente 1 (HU-010, 011)
- E3 — Agente 5 (HU-020, 021, 022)

### Semestre 2
- E2 — Agente 1 (HU-012, 013, 014)
- E3 — Agente 5 (HU-023, 024)
- E4 — Agente 2 (HU-030, 031)

### Ano 2
- E5 — Agente 3 (HU-040, 041)
- E6 — Agente 4 (HU-050, 051)
- Integracion total

### Dependencias clave
- HU-001 → base de datos (prerequisito global)
- HU-002 → todas las automatizaciones
- HU-020 → APIs habilitadas
- HU-024 → datos previos

---

## 12. Exclusiones

- No reemplazo del personal
- No automatizacion sin validacion humana en contenidos criticos
- No infraestructura de alto costo
- No integracion con sistemas externos complejos no definidos

---

## 13. Criterios de aceptacion globales

- Automatizacion efectiva (> X%)
- Reduccion de tiempos operativos
- Integridad de datos (> 95%)
- Disponibilidad del sistema
- Aceptacion por usuarios finales

---

## 14. Fuentes

- `Contenido/bible/Procesos y Agentes.md`
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.pdf`
- `Contenido/bible/mailinstitucional.pdf`
