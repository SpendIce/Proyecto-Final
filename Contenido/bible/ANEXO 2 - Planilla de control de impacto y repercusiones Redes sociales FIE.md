# ANEXO 2 — Planilla de control de impacto y repercusiones Redes sociales FIE

Fuente original: `Contenido/bible/ANEXO 2 - Planilla de control de impacto y repercusiones Redes sociales FIE (1) IA.xlsx.pdf` (documento nuevo, incorporado 2026-08-18).

Nota operativa: este Markdown es un **resumen curado**, no un mirror linea por linea. La planilla original tiene 3 pestañas: LÉAME (roadmap), Notas de requerimientos - P100 (una HU de ejemplo) y ANEXO 2 2025 / ANEXO 2 2026 (registro historico real de publicaciones, ~1080 filas). El registro historico fila por fila queda solo en el PDF: es evidencia de formato, no contenido que un agente necesite leer completo.

---

## 1. Pestaña LÉAME — roadmap Año1/Año2 por TRL

Contenido ya documentado en `Agentes/arquitectura_multiagente_experto.md` (seccion "Ano 1 (TRL 3-4)" / "Ano 2 (TRL 5-6)" y "Niveles TRL como marco de validacion"). Este PDF confirma la misma secuencia, sin cambios de fondo:

- **Año 1 — Cimientos IA y Operación Interna SEU (TRL 3-4):** Agente 1 (prioridad, reduce carga operativa inmediata) + Agente 2 (paralelo, base de conocimiento para todos los demas agentes) + Dashboard basico (valida arquitectura multiagente con base en Agente 5).
- **Año 2 — Interacción Externa y Analítica Avanzada (TRL 5-6):** Agente 3 (eventos/certificados), Agente 4 (WhatsApp Business), Agente 5 (evaluacion de impacto final + tablero estrategico).
- **Justificación explícita:** no se pueden generar analiticas profundas (A5) ni atender masivamente al publico (A4) sin antes tener recoleccion eficiente (A1) y un repositorio confiable (A2). Esto refuerza por que A1 es el foco vigente de este workspace.

No requiere accion adicional: la definicion de TRL (escala NASA 1-9, fuente citada: `argentina.gob.ar/cnea/vinculaciontecnologica/niveles-de-madurez-tecnologica`) coincide con la ya usada en la bible.

---

## 2. Pestaña "Notas de requerimientos - P100" — HU SMART para Agente 5

Esta pestaña es contenido **nuevo y mas concreto** que lo que ya figuraba como HU-020/HU-021/HU-022 en el backlog (`Agentes/arquitectura_multiagente_experto.md`, seccion Backlog). Amplia esas historias con criterios de aceptacion accionables:

**Historia (Como Coordinadora de Extensión):**
> Quiero que un usuario designado pueda extraer de manera automática datos de diferentes redes sociales (Instagram, Facebook, LinkedIn) y almacenarlos en una planilla similar al ANEXO 2 (columna Copy con metadatos) para reducir los tiempos de recolección de RRSS y realizar su análisis de impacto.

**Criterios de aceptación detallados (no estaban en el backlog previo):**
- **Conectividad:** conexión exitosa a APIs oficiales (o scraping autorizado) de Instagram, Facebook y LinkedIn; extracción configurable por rango de días/meses.
- **Integridad del Copy y metadatos:** texto completo sin truncar; metadatos obligatorios = fecha de publicación, red de origen, URL del post, tipo de contenido (imagen/video/carrusel — carrusel definido explícitamente como secuencia de elementos vinculados a un mismo ID de publicación).
- **Formato de salida:** debe volcarse en planilla que respete exactamente el orden de columnas del ANEXO 2 (ver esquema abajo); columna "Copy" limpia de caracteres que rompan el formato de celda.
- **Automatización:** ejecución con un clic o programada (ej. lunes 8:00 AM) sin intervención manual; notificación si una cuenta pierde conexión o requiere re-autenticación.
- **Rendimiento:** extracción total de las 3 redes con límite de tiempo configurable ([X] minutos).

**Uso sugerido:** estos criterios son directamente reutilizables como DoD ampliado de HU-020/HU-021/HU-022 en el backlog de Agente 5. No corresponden a Agente 1 (que no hace scraping ni extracción de RRSS — ver exclusiones en `Agentes/extension_bot_experto.md`).

La pestaña también incluye una explicación pedagógica del filtro SMART (Specific/Measurable/Achievable/Relevant/Time-bound) aplicada a historias de usuario — material de apoyo metodológico, no requisito nuevo del proyecto.

---

## 3. Pestañas "ANEXO 2 2025" / "ANEXO 2 2026" — esquema de columnas y evidencia real

Registro histórico real de publicaciones institucionales de la FIE (enero 2025 a marzo 2026 al momento del corte), organizado por mes. Columnas exactas:

| Columna | Contenido |
|---|---|
| Efeméride/Académico | Nombre/título de la publicación |
| Mes / Día | Fecha |
| Medio de comunicación | Instagram / Facebook / LinkedIn (marcado con x) |
| Copy | Texto completo de la publicación |
| Hashtag | Hashtags usados |
| Tipo de publicación | Pieza, Reel, Carrusel, Posteo |
| Categoría | Efemérides, Académica, Cursos, Ingresos, Congreso, Evento, Convenio, Taller, etc. |
| Reacciones Instagram / Facebook / LinkedIn | Métricas por red (Me gusta, comentarios, compartidos, interacciones) |

**Por qué importa para este proyecto:**
- Es el **formato objetivo exacto** que Agente 5 debe reproducir automáticamente (HU-021: "estructurar datos en formato ANEXO 2").
- Es **material de referencia de tono institucional** para Agente 1: los ~150+ Copy reales (ej. gacetillas de inscripciones, efemérides, congresos CAIM/CAIFE, diplomaturas) muestran el estilo, largo y convenciones de hashtag que HU-010/HU-011 deben imitar al generar gacetillas y posts. Puede usarse como few-shot / banco de ejemplos al definir prompts, sin necesidad de indexar las 1080 filas en la bible.
- Confirma que el "Medio de comunicación" se limita a Instagram, Facebook y LinkedIn (coincide con el alcance ya definido en Proceso 4).

El detalle fila por fila (todas las publicaciones 2025-2026 con sus métricas) queda únicamente en el PDF — no se transcribe aquí para evitar sedimento; consultarlo directamente cuando se necesiten ejemplos concretos de Copy o métricas de una publicación puntual.
