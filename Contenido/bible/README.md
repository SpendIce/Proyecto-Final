# Fuentes Bible — Markdown operativo

Usar los Markdown como working sources para busqueda y lectura agentica; conservar los PDFs como evidencia original y para formato visual exacto.

| PDF | Markdown | Paginas | Palabras |
|---|---|---:|---:|
| `PROYECTO-FIE 2026-2027 - Cicerchia César.pdf` | `PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md` | 20 | 6405 |
| `Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf` | `Procesos y Agentes.md` | 169 | 34151 |
| `Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA.pdf` | `Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md` | 3 | 933 |
| `mailinstitucional.pdf` | `mailinstitucional.md` | 3 | 0 |
| `ANEXO 2 - Planilla de control de impacto y repercusiones Redes sociales FIE (1) IA.xlsx.pdf` | `ANEXO 2 - Planilla de control de impacto y repercusiones Redes sociales FIE.md` | — (planilla) | ~1091 filas |

Nota: `Procesos y Agentes SEU - FIE con Backlog tecnico Jira.pdf` queda como copia histórica local de 138 páginas. La fuente vigente para trabajo textual es la versión completa de 169 páginas listada arriba.

Nota (2026-08-18): se incorporaron dos documentos nuevos a la bible.

1. Actualizacion de `Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf` (169 paginas, +~5000 palabras respecto de la version anterior indexada). Contenido nuevo relevante: Plan de Pruebas Unitarias completo (CP01-CP22, 3 etapas) — ya conocido y documentado en `Agentes/extension_bot_experto.md` — mas 4 Escenarios de Prueba end-to-end nuevos (EP01-EP04) y la historia HU-016 (certificados disparados por Eventos, complementa HU-015 que cubre Cursos). Detalle en `Agentes/extension_bot_experto.md`.
2. `ANEXO 2 - Planilla de control de impacto y repercusiones Redes sociales FIE (1) IA.xlsx.pdf` (nuevo). Contiene: (a) el roadmap Año1/Año2 por TRL, ya documentado en `Agentes/arquitectura_multiagente_experto.md`; (b) una historia de usuario SMART detallada para el Agente 5 (extraccion de RRSS); (c) un registro historico real de publicaciones FIE 2025-2026 con el esquema de columnas exacto que exige el formato ANEXO 2. Resumen curado en `Contenido/bible/ANEXO 2 - Planilla de control de impacto y repercusiones Redes sociales FIE.md` (el PDF conserva el detalle fila por fila).

Nota (2026-09-08): `Procesos y Agentes.md` se reemplazo por el export Markdown nativo del documento vivo, en lugar de la extraccion `pdftotext` anterior.

**Que cambio.** Estructura, no definiciones. La extraccion previa tenia **1 heading** y 163 filas de tabla rotas; el export tiene **627 headings** y 378 filas de tabla bien formadas. Se recuperan **~3.121 palabras** (31.030 -> 34.151) que `pdftotext` habia perdido o mezclado, casi todas contenido tabular: las matrices RACI de los nueve procesos, la Matriz de Definicion Tecnica de Procesos, la Matriz de Interacciones y Dependencias, la tabla STRIDE de ciberseguridad y la seccion `Notas Diseno - AI 1 / Diseno de Sistemas Informaticos 2` del Agente 1 (requisitos funcionales y no funcionales, CU01-CU14, CP01-CP22, EP01-EP04, hitos con costos).

**Que NO cambio.** Ninguna definicion de alcance, HU, DoD, exclusion ni criterio de gate. Se verificaron una por una las definiciones que gobiernan el Agente 1 —HU-010 a HU-016, exclusiones, limites del Agente 1, validacion SEU, TRL— y son identicas. En particular HU-013 conserva su DoD original: *"Interfaz simple (prompt en Sheet o Doc)"* y *"Respuesta generada usable"*, sin mencion de chat ni de invitacion por email.

**Imagenes.** El export traia 18 imagenes embebidas en base64 (617 KB, 72 % del archivo), lo que hacia inutilizable el Markdown para busqueda. Se extrajeron a `assets/procesos-y-agentes/imageN.png` y las referencias del documento apuntan a esos archivos. El `.md` bajo de 856 KB a 240 KB sin perder contenido.

**Advertencia sobre el documento vivo.** El LEAME del documento declara que las modificaciones se senalan con resaltado amarillo. El resaltado **no sobrevive** a la exportacion a Markdown ni a PDF, de modo que ni este `.md` ni el PDF permiten distinguir que se modifico en la ultima revision. Para saberlo hay que abrir el Google Doc original.
