---
updated: 2026-05-11
---

# Proyecto Final — Estado

## Tema
Proyecto Centenario (P100) — sistema multiagente de inteligencia artificial para la FIE/UNDEF, con foco documental actual en el Agente 1: Extension Bot.

## Estado actual
- [x] Incorporar fuentes base del proyecto y material de campus.
- [x] Consolidar perfiles expertos en `Agentes/`.
- [x] Incorporar material DSI1/DSI2 al indice del campus y crear perfil experto para documentacion de sistemas.
- [x] Definir arquitectura multiagente P100 de referencia.
- [x] Definir alcance del Agente 1 — Extension Bot.
- [x] Elaborar anteproyecto vigente en LaTeX para Juan Ignacio Gone.
- [ ] Validar el anteproyecto contra la bible, criterios Cicerchia y lineamientos de catedra.
- [ ] Registrar fechas oficiales de entrega cuando Nacho las confirme.

## Fechas importantes
_(pendiente: verificar con Nacho o con consignas oficiales antes de asumir fechas)_

## Notas
- Procedencia del repo: copia clonada desde el trabajo de Ignacio Becerra Mas Roca; esta copia se adapto para Juan Ignacio Gone y Agente 1.
- Estado de versionado: la adaptacion y agregados actuales pueden estar sin commit; no tratar borrados/renombres de archivos de Becerra como accidentales sin verificar.
- Foco actual: documentacion para Agente 1 / Extension Bot, no implementacion de software.
- Entregable principal: `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`.
- Fuentes de verdad: `Contenido/bible/Procesos y Agentes.md`, definiciones consolidadas en `Contenido/Definicion/`, perfiles en `Agentes/`, e indice del campus en `Contenido/Campus/INDEX.md`.
- Bible actualizada desde PDF vigente: `Contenido/bible/Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`; `Contenido/bible/Procesos y Agentes.md` queda como working source textual para busqueda y agentes. La version vigente verificada ahora tiene 16 paginas y se concentra en Agente 1 / Extension Bot: problema SEU, usuarios, modelo de negocio, requisitos funcionales/no funcionales, interacciones A2-A5, metodologia Scrum, cronograma y CU01-CU13 con actores. La copia historica `Procesos y Agentes SEU - FIE con Backlog tecnico Jira.pdf` conserva una version local anterior de 138 paginas.
- Corpus Markdown bible: usar `Contenido/bible/README.md` para ubicar `PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`, `Procesos y Agentes.md`, `Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md` y `mailinstitucional.md` antes de abrir PDFs institucionales.
- Corpus Markdown Campus general: usar `Contenido/Campus/_md/README.md` para PDFs del campus fuera de DSI1/DSI2; los dos modulos propedeuticos PPS 2026 fueron OCRizados localmente porque `pdftotext` solo exponia numeracion de paginas.
- Material DSI incorporado: `Contenido/Campus/DSI1/` para requisitos, UML, diseno, interfaces, implantacion y pruebas; `Contenido/Campus/DSI2/` para planificacion, estimacion, control, riesgos, calidad, comunicaciones, indicadores, auditoria y liberacion.
- Corpus Markdown DSI: usar `Contenido/Campus/DSI1/_md/` y `Contenido/Campus/DSI2/_md/` antes de abrir PDFs; DSI2 fue OCRizado localmente porque las presentaciones no exponian texto suficiente con `pdftotext`.
- Perfil nuevo: `Agentes/documentacion_sistemas_experto.md`, pensado como subagente unico con modos internos por artefacto para evitar fragmentar trazabilidad entre producto y gestion.
- Agente 1: comunicacion institucional de SEU. MVP S1: HU-010 gacetillas y HU-011 posts RRSS. S2: HU-012 confirmaciones, HU-013 lenguaje natural interno, HU-014 certificados con validacion humana.
- Restricciones criticas: no reemplazar personal, no publicar sin validacion humana, no usar infraestructura de alto costo, no agregar integraciones externas complejas no definidas.
