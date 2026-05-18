# Diagrama de Gantt - Agente 1 Extension Bot

Este artefacto contiene un cronograma de referencia para el desarrollo e implementacion del Agente 1 del Proyecto Centenario, refinado como plan iterativo no cascada. La version principal esta en formato Mermaid, compatible con Mermaid Live Editor:

- `diagrama-gantt-agente-1.mmd`: fuente Mermaid recomendada y canonica.
- `mermaid-live-url.txt`: enlace codificado para abrir la version Mermaid en Mermaid Live Editor; regenerar si cambia la fuente Mermaid.
- `diagrama-gantt-agente-1.puml`: version PlantUML sincronizada, conservada como respaldo local.

## Supuestos usados

- El alcance principal corresponde al Proyecto de Juan Ignacio Gone: Agente 1 Extension Bot durante el ano academico 2026, dividido en S1 y S2.
- Las fechas se toman como referencia documental del anteproyecto vigente: S1 Mar-Jul 2026 y S2 Ago-Dic 2026. Las fechas oficiales de catedra siguen pendientes de confirmacion.
- S3 y S4 de 2027 se muestran solo como proyeccion P100 fuera del alcance del Proyecto Gone, para mantener continuidad con la progresion TRL 5-6.
- El Agente 1 se mantiene dentro del Proceso 4, Comunicacion y Difusion Institucional. Puede recibir insumos de A2-A5, pero no actua como orquestador.
- La validacion humana es obligatoria antes de publicar, enviar o emitir comunicaciones institucionales o certificados.
- La planificacion no se organiza como cascada. Cada HU relevante se expresa como ciclo con diseno acotado, prototipo, validacion, ajuste y evidencia.
- El primer semestre mantiene el MVP acotado a HU-010 y HU-011, con ciclos separados de gacetillas y posts, y gate TRL 3.
- El segundo semestre incorpora HU-012, HU-013 y HU-014 en ciclos incrementales, refina HU-010/HU-011 con feedback y separa contratos/mocks A2-A5 de la integracion progresiva real.

## Evaluacion metodologica

**Veredicto:** APROBADO CON OBSERVACIONES.

El cronograma anterior era defendible como referencia de alto nivel, pero la agrupacion por `Ingenieria`, `Diseno`, `Prototipos`, `Implementacion` y `Validacion` podia leerse como un ciclo en cascada, aun cuando las fechas se solapaban. La version refinada mantiene los hitos y semestres del anteproyecto, pero organiza el trabajo por incrementos verificables:

- S1 Ciclo 0: alcance, plataforma minima y equipo validador.
- S1 Ciclo 1: HU-010 gacetillas.
- S1 Ciclo 2: HU-011 posts RRSS.
- S2 Ciclo 3: HU-012 confirmaciones.
- S2 Ciclo 4: HU-013 lenguaje natural interno.
- S2 Ciclo 5: HU-014 certificados.
- S2 cierre: contratos/mocks A2-A5, integracion progresiva, pruebas SEU, ajustes e informe final.

Los guardarrailes de Kanban, BPM/RACI/DoD, validacion humana, evidencia SEU, seguridad y logs quedan como actividades transversales para sostener trazabilidad CONEAU y evitar que la validacion aparezca solamente al final.

## Fuentes consultadas

- `CLAUDE.md` y `.claude/persistence.md`: alcance vigente del workspace y foco en Juan Ignacio Gone + Agente 1.
- `Agentes/extension_bot_experto.md`: identidad, funciones, exclusiones, historias HU-010 a HU-014, DoD e infraestructura por semestre.
- `Agentes/arquitectura_multiagente_experto.md` y `Contenido/Definicion/arquitectura-multiagente.md`: arquitectura P100, flujo Actividad -> Comunicacion, dependencias E1, integracion A2-A5 e infraestructura.
- `Contenido/bible/Procesos y Agentes.md`: Proceso 4, RACI, backlog E2, DoD global, TRL, validacion humana y criterios transversales.
- `Contenido/Definicion/criterios-evaluacion-cicerchia.md`: criterios de evaluacion, progresion TRL, restricciones tecnologicas y DoD.
- `Contenido/Campus/INDEX.md` y `Contenido/Campus/DSI2/_md/03-planificacion.md`: uso de EDT/WBS, hitos, responsables, calendario y diagramas de Gantt como herramienta de planificacion.
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`: EDT, entregables por semestre, hitos y planificacion mensual.

## Trazabilidad minima

| Actividad Gantt | Proceso BPM | HU / requisito | DoD / evidencia esperada | Responsable institucional |
|---|---|---|---|---|
| Guardarrailes transversales | P4, apoyo P3/P5/P6 | Alcance A1, dependencias HU-001/HU-002 | Tablero Kanban, matriz BPM/RACI/DoD, validacion humana, logs y controles de seguridad | Coordinador de Extension / Responsable Gestion del Conocimiento / Responsable Tecnico |
| S1 Ciclo 0 | P4 | Alcance, plataforma minima, equipo validador | Anteproyecto, matriz de alcance/exclusiones, base Sheets/Drive/Apps Script, evidencia inicial TRL 3 | Coordinador de Extension / Responsable Gestion del Conocimiento |
| S1 Ciclo 1 | P4 | HU-010 | Plantilla de gacetilla, spike Sheets -> Docs, prototipo, prueba, validacion SEU y evidencia DoD | Responsable Gestion del Conocimiento |
| S1 Ciclo 2 | P4 | HU-011 | Criterios IG/LinkedIn, prototipo de posts, validacion SEU, ajuste de prompts y gate TRL 3 | Responsable Gestion del Conocimiento / Responsable Redes Sociales |
| S2 Ciclo 3 | P4/P5 | HU-012 | Trigger Sheets, email Gmail, registro de envio, logs persistentes y validacion interna | Responsable Tecnico / Personal SEU |
| S2 Ciclo 4 | P4/P3 | HU-013 | Email de inicio, invitacion a chat, registro en Sheets y validacion de usabilidad interna | Responsable Tecnico / Personal SEU |
| S2 Ciclo 5 | P5/P4 | HU-014 | Plantilla, generacion PDF, aprobacion manual, log de emision y prueba controlada | Coordinador de Extension / Administracion |
| S2 integracion y cierre | P4/P5 | Gate TRL 4 | Contratos/mocks A2-A5, integracion progresiva, checklist SEU 1-4, ajustes, transferencia e informe final | Coordinador de Extension |

## Pendientes de confirmacion

- Fechas oficiales de entrega y defensa.
- Disponibilidad concreta del personal SEU para validaciones de S1 y S2.
- Personas nominales asignadas a cada rol RACI.
- Criterios de aceptacion finales acordados con usuario para cada HU.

## Uso en Mermaid Live

```bash
xdg-open https://mermaid.live/
```

Luego abrir `diagrama-gantt-agente-1.mmd` y usar su contenido como fuente del diagrama.

## Renderizado Mermaid local

```bash
mmdc -p Documentos/Gantt/puppeteer-config.json -i Documentos/Gantt/diagrama-gantt-agente-1.mmd -o Documentos/Gantt/diagrama-gantt-agente-1-mermaid.svg -w 1800 -H 1400
mmdc -p Documentos/Gantt/puppeteer-config.json -i Documentos/Gantt/diagrama-gantt-agente-1.mmd -o Documentos/Gantt/diagrama-gantt-agente-1-mermaid.png -w 1800 -H 1400
```

## Renderizado PlantUML local

La version PlantUML de respaldo se puede regenerar asi, si se necesita:

```bash
JAVA_TOOL_OPTIONS=-Djava.awt.headless=true plantuml -tpng Documentos/Gantt/diagrama-gantt-agente-1.puml
JAVA_TOOL_OPTIONS=-Djava.awt.headless=true plantuml -tsvg Documentos/Gantt/diagrama-gantt-agente-1.puml
```
