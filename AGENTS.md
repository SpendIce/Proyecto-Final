# Codex Setup — Proyecto Final / Proyecto Centenario

## Idioma y tono
- Trabajar siempre en espanol rioplatense, con registro academico cuando se redacten entregables.
- Usar terminos tecnicos en ingles solo cuando sean convencion del area: agent, RAG, LLM, trigger, backend, DoD, TRL.
- No inventar datos institucionales, fechas, requisitos, prioridades ni evidencia. Si falta informacion, marcarlo como pendiente o pedir confirmacion.

## Alcance del workspace
Este directorio es un sistema de elaboracion documental para el Proyecto Centenario (P100) de la FIE/UNDEF. El foco actual es el Proyecto de Juan Ignacio Gone sobre el Agente 1, Extension Bot: agente de comunicacion institucional para la Secretaria de Extension Universitaria.

El repo fue clonado originalmente desde el trabajo de Ignacio Becerra Mas Roca. Las referencias historicas a Becerra pueden aparecer en archivos base, definiciones compartidas o artefactos LaTeX, pero no definen el foco vigente de este workspace. Para este repo, priorizar siempre Juan Ignacio Gone + Agente 1.

El objetivo principal del agente de trabajo en este repo es ayudar a producir, revisar y mantener documentacion academica y tecnica, especialmente el anteproyecto, definiciones de alcance, arquitectura, criterios de evaluacion y material de respaldo.

## Fuentes de verdad
Leer en este orden segun la tarea:
1. `CLAUDE.md` para reglas locales, estructura y routing.
2. `.claude/persistence.md` para estado durable del proyecto.
3. `Agentes/extension_bot_experto.md` para el alcance del Agente 1.
4. `Agentes/arquitectura_multiagente_experto.md` y `Contenido/Definicion/arquitectura-multiagente.md` para arquitectura P100.
5. `Agentes/evaluador_cicerchia.md` y `Contenido/Definicion/criterios-evaluacion-cicerchia.md` para validar decisiones.
6. `Contenido/bible/Procesos y Agentes.md` para procesos, RACI, backlog, DoD, TRL, exclusiones y criterios institucionales.
7. `Contenido/Campus/INDEX.md` antes de abrir PDFs del campus.
8. `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` para el entregable principal vigente.

## Reglas de trabajo
- Mantener al Agente 1 dentro del Proceso 4 como agente de comunicacion institucional. Puede recibir insumos de A2-A5, pero no es orquestador del sistema.
- Respetar las exclusiones: no reemplazo de personal, no publicacion sin validacion humana, no infraestructura de alto costo, no integraciones externas complejas no definidas.
- Al revisar o proponer contenido, mapear cada decision a proceso BPM, historia de usuario, DoD, TRL, evidencia y responsable cuando aplique.
- Para tareas de anteproyecto, preservar la estructura oficial de 20 secciones y el formato LaTeX existente.
- Antes de buscar en `Contenido/Campus/`, usar `Contenido/Campus/INDEX.md`; evitar busquedas amplias sobre PDFs binarios.
- No borrar ni regenerar artefactos LaTeX existentes salvo pedido explicito.
- La carpeta `Documentos/Anteproyecto/` contiene archivos generados por LaTeX; distinguir entre fuente `.tex`/`.bib` y artefactos `.aux`, `.bbl`, `.log`, `.out`, `.toc`, `.pdf`.
- El worktree puede estar sucio porque la adaptacion desde Becerra hacia Gone todavia no fue commiteada. No revertir borrados, renombres ni agregados vinculados a esa migracion sin pedir confirmacion.

## Comandos utiles
- Listar fuentes Markdown: `rg --files -g '*.md'`
- Buscar sin PDFs: `rg -n --glob '!*.pdf' --glob '!*.docx' '<termino>'`
- Ver cambios actuales: `git status --short`
- Ver cambios de un archivo: `git diff -- <archivo>`

## Setup de agentes
- Los perfiles expertos versionados viven en `Agentes/`.
- `.agents/` queda reservado para setup operativo de agentes o equipos.
- `.codex/` queda reservado para notas y atajos especificos de Codex.
- `.claude/` conserva estado durable y aprendizajes de sesiones.
