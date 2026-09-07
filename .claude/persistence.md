---
updated: 2026-09-06
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
- Foco actual: implementacion del MVP del Agente 1 en `Implementacion/Agente1/` (Python, sin framework web). La nota previa "no implementacion de software" quedo obsoleta.
- Estado de implementacion al 2026-09-06: suite de 513 pruebas verdes fuera del sandbox con `uv run pytest -q`. HU-010 y HU-011 producen borradores offline y con Ollama local (`llama3.2:3b`, constrained decoding por JSON Schema); HU-012 es slice offline. Toda salida queda `BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.
- Politica de redes HU-011 versionada como inventario de reglas verificables en `Implementacion/Agente1/src/agente1/politicas/politica_redes_provisional_v1.json`: 20 reglas, 14 `ACTIVA` con codigo de gate y caso negativo obligatorio, 5 `NO_APLICADA_PENDIENTE_SEU`, 1 `NO_MECANIZABLE`. La suite falla si se agrega una regla activa sin regresion. Doc: `Documentos/PoC/Politica-Redes-Reglas-Verificables-v1.md`.
- Matriz operativa HU-012 por origen en `src/agente1/contracts/matriz_origenes_inscripcion_v1.json` + `origenes_inscripcion.py`: cuatro origenes, procedencia por campo, decision de envio fail-closed. Ningun campo esta `CONFIRMADO_SEU` y ningun origen habilita envio. Doc: `Documentos/PoC/Matriz-Operativa-HU-012-Origenes-Inscripcion-v1.md`.
- Prueba de capacidad del 2026-08-26 (`evidencias/benchmark-capacidad-a1-2026-08-26.md`): el volumen informado por la SEU (12 publicaciones/mes = 36 generaciones) cuesta ~12 min de computo local. El cuello de botella NO es la latencia sino la conformidad de contenido.
- Hallazgo critico del corte de capacidad: `num_predict=112` truncaba la salida y enmascaraba fallas de contenido como `json_invalid`. Con 300 los `json_invalid` desaparecen y aparece lo real: 6/6 posts fugaron un hecho de la fuente y usaron tuteo. Registrado como `DEF-A1-013`. No bajar `num_predict` sin regresion.
- Ollama local se levanta con: `OLLAMA_MODELS=$PWD/.runtime/models ./.runtime/ollama-root/usr/bin/ollama serve`. La suite se corre de forma reproducible con `uv run pytest -q`; las dependencias de desarrollo y su lockfile estan versionados.
- FastAPI, LangGraph, Celery y Redis estan DIFERIDOS por decision documentada en `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`: no son condicion para el gate. No reintroducirlos sin necesidad operativa validada.
- Bloqueantes reales son institucionales, no tecnicos: Workspace live (OAuth/DSI), validacion SEU y criterio del Gate G2. Ver `Documentos/PoC/Registro-Defectos-Agente-1.md`.
- Runtime local: Ollama user-local en `Implementacion/Agente1/.runtime/` (ignorado por Git) con `llama3.2:3b` ya descargado. Docker disponible para PostgreSQL efimero.
- Entregable principal: `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`.
- Fuentes de verdad: `Contenido/bible/Procesos y Agentes.md`, definiciones consolidadas en `Contenido/Definicion/`, perfiles en `Agentes/`, e indice del campus en `Contenido/Campus/INDEX.md`.
- Bible actualizada desde PDF vigente: `Contenido/bible/Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`; `Contenido/bible/Procesos y Agentes.md` queda como working source textual para busqueda y agentes. La version completa vigente verificada tiene 169 paginas e integra mapa de procesos SEU, notas de diseno de agentes, ciberseguridad, backlog tecnico Jira, DoD, validacion SEU e infraestructura. La copia historica `Procesos y Agentes SEU - FIE con Backlog tecnico Jira.pdf` conserva una version local anterior de 138 paginas.
- Corpus Markdown bible: usar `Contenido/bible/README.md` para ubicar `PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`, `Procesos y Agentes.md`, `Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md` y `mailinstitucional.md` antes de abrir PDFs institucionales.
- Corpus Markdown Campus general: usar `Contenido/Campus/_md/README.md` para PDFs del campus fuera de DSI1/DSI2; los dos modulos propedeuticos PPS 2026 fueron OCRizados localmente porque `pdftotext` solo exponia numeracion de paginas.
- Material DSI incorporado: `Contenido/Campus/DSI1/` para requisitos, UML, diseno, interfaces, implantacion y pruebas; `Contenido/Campus/DSI2/` para planificacion, estimacion, control, riesgos, calidad, comunicaciones, indicadores, auditoria y liberacion.
- Corpus Markdown DSI: usar `Contenido/Campus/DSI1/_md/` y `Contenido/Campus/DSI2/_md/` antes de abrir PDFs; DSI2 fue OCRizado localmente porque las presentaciones no exponian texto suficiente con `pdftotext`.
- Perfil nuevo: `Agentes/documentacion_sistemas_experto.md`, pensado como subagente unico con modos internos por artefacto para evitar fragmentar trazabilidad entre producto y gestion.
- Agente 1: comunicacion institucional de SEU. MVP S1: HU-010 gacetillas y HU-011 posts RRSS. S2: HU-012 confirmaciones, HU-013 lenguaje natural interno, HU-014 certificados con validacion humana.
- Restricciones criticas: no reemplazar personal, no publicar sin validacion humana, no usar infraestructura de alto costo, no agregar integraciones externas complejas no definidas.
