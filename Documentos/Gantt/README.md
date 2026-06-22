# Diagrama de Gantt - Agente 1 Extension Bot

Este artefacto contiene la vista principal del cronograma del proyecto de Juan Ignacio Gone para el Agente 1, Extension Bot. La fuente editable recomendada es Mermaid:

- `diagrama-gantt-agente-1.mmd`: Gantt principal, enfocado en el ano 2026 y organizado por primer y segundo semestre.
- `diagrama-gantt-implementacion-semanal.mmd`: vista detallada semana a semana del plan de implementacion (1 jul - 30 nov 2026). Arranca con un bootstrap minimo y el MVP (HU-010/HU-011, Gate TRL 3) y sigue con robustecimiento, HU-012/HU-013/HU-014, integracion A2-A5, pruebas y Gate TRL 4. Es el plan operativo de implementacion y codificacion; no reemplaza al Gantt anual, lo expande.
- `diagrama-gantt-agente-1.puml`: respaldo PlantUML sincronizado con la vista Mermaid.
- `visor-gantt-agente-1.html`: visor didactico y editable en navegador; permite filtrar, editar tareas y exportar nuevamente la fuente Mermaid.
- `visor-gantt-implementacion-semanal.html`: visor de solo lectura para la vista semanal de implementacion (1 jul - 30 nov 2026). Self-contained (sin servidor ni dependencias externas), con eje por mes y por semana, grupos de sprint con su objetivo, barras coloreadas por sprint, hitos de DoD/gate como diamantes y tooltip con fechas y duracion. Incluye filtros: chips por sprint (toggle), botones Todos/Ninguno, casilla "Solo hitos" y buscador de tareas por texto. Pensado para lectura rapida en presentacion; la fuente de verdad sigue siendo `diagrama-gantt-implementacion-semanal.mmd`.
- `mermaid-live-url.txt`: enlace codificado para abrir la vista en Mermaid Live Editor; regenerar si cambia la fuente Mermaid.

Los PNG/SVG existentes son artefactos renderizados. No son fuente de verdad y no se regeneran automaticamente despues de cambios documentales.

Los nombres visibles de tareas priorizan lectura humana para presentacion y revision con la SEU. La trazabilidad tecnica queda preservada en la estructura por secciones, fechas, hitos, README y fuentes documentales, no en prefijos largos dentro de cada barra.

## Enfoque del cronograma

La vista principal cubre el proyecto del Agente 1 durante 2026 y deja febrero de 2027 solo como ventana maxima de entrega final, demostracion o transferencia si la catedra o la agenda institucional lo requieren. La continuidad P100 posterior queda fuera del alcance directo del proyecto de Gone.

## Supuestos usados

- El alcance corresponde al Agente 1 Extension Bot: agente de comunicacion institucional de la SEU dentro del Proceso 4.
- El Agente 1 puede recibir insumos de A2-A5, pero no orquesta el sistema multiagente.
- El primer semestre de 2026 se concentra en anteproyecto, alcance, diseno, trazabilidad, preparacion tecnica y MVP controlado de HU-010/HU-011.
- La firma del anteproyecto por la SEU se incluye como hito al 30 de junio de 2026.
- El segundo semestre de 2026 se concentra en implementacion, robustecimiento, integracion progresiva, pruebas, validacion SEU, release candidata TRL 4, informe final y cierre anual.
- Febrero de 2027 se modela como cierre maximo: observaciones finales, paquete final, demo y transferencia operativa al P100.
- Toda publicacion, envio oficial o emision de certificados requiere validacion humana previa.
- Los gates TRL no se declaran por avance narrativo: requieren outputs, logs, checklist SEU, defectos gestionados y evidencia recuperable.
- Las fechas oficiales de entrega, presentacion y disponibilidad de validadores siguen pendientes de confirmacion.

## Estructura del Gantt

| Periodo | Foco | Resultado esperado |
|---|---|---|
| S1 Mar-Jul 2026 | Anteproyecto, diseno, gobierno, datos, arquitectura, plantillas y MVP controlado | Anteproyecto entregado, firma SEU a fin de junio, diseno validable, HU-010/HU-011 con evidencia y gate TRL 3 |
| S2 Ago-Dic 2026 | Desarrollo, automatizacion, robustecimiento, integracion, pruebas y validacion | HU-012/HU-013/HU-014 operativas, pruebas ejecutadas, gate TRL 4 e informe final |
| Feb 2027 | Cierre final maximo | Observaciones finales incorporadas, demo, paquete final y transferencia P100 |

## Trazabilidad minima

| Bloque Gantt | Proceso / alcance | Evidencia esperada |
|---|---|---|
| S1 Gobierno y anteproyecto | Alcance A1, Proceso 4, exclusiones, agenda academica | Anteproyecto, firma SEU, baseline documental, tablero Kanban, minutas, matriz de riesgos |
| S1 Diseno funcional | HU-010 a HU-014, HITL, RACI, DoD | Casos de uso, estados, trazabilidad, arquitectura, planes complementarios |
| S1 Preparacion tecnica | Plataforma base, Google Workspace, datos, logs | Entorno local, diccionario Sheets, plantillas SEU, correlation ID, indice de evidencias |
| S1 MVP HU-010/HU-011 | Gacetillas y posts RRSS | Outputs controlados, pruebas de datos, validacion humana, logs y checklist |
| S1 Gate TRL 3 | Cierre de MVP controlado | Informe de avance, defectos, evidencias y decision de gate |
| S2 Desarrollo base | Robustecimiento tecnico y refinamiento S1 | Persistencia, colas, permisos, secretos, logging y auditoria |
| S2 HU-012/HU-013/HU-014 | Confirmaciones, lenguaje natural interno, certificados | Email de prueba, transcript/captura, PDF, aprobacion manual y logs |
| S2 Integracion y pruebas | A2-A5 como fuentes, no como orquestacion | Contratos/mocks, integracion progresiva, pruebas unitarias/integracion/sistema/seguridad |
| S2 Validacion y release | Usuarios SEU y gate TRL 4 | Checklist 1-4, defectos cerrados, regresion, paquete de evidencias, informe final |
| Feb 2027 | Entrega final maxima A1 | Observaciones cerradas, demo, paquete final y transferencia operativa |

## Fuentes consultadas

- `CLAUDE.md` y `.claude/persistence.md`: foco vigente del workspace y reglas locales.
- `Agentes/extension_bot_experto.md`: alcance, exclusiones, HU-010 a HU-014, DoD e infraestructura por semestre.
- `Agentes/arquitectura_multiagente_experto.md` y `Contenido/Definicion/arquitectura-multiagente.md`: infraestructura por semestre, TRL e integracion con A2-A5.
- `Contenido/bible/Procesos y Agentes.md`: Proceso 4, backlog, validacion humana, RACI, DoD y criterios transversales.
- `Contenido/Definicion/criterios-evaluacion-cicerchia.md`: restricciones, progresion TRL y evidencia esperada.
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`: EDT, entregables por semestre, hitos y planificacion mensual.
- `Documentos/CasosUso/`, `Documentos/DiagramaClases/` y `Documentos/DiagramaSecuencia/`: comportamiento funcional, estados, actores y trazabilidad tecnica.
- Planes complementarios del Agente 1: calidad, riesgos, comunicaciones, auditoria, estados, despliegue e integracion.
- `Contenido/Campus/DSI1/_md/` y `Contenido/Campus/DSI2/_md/`: planificacion, control, riesgos, calidad, liberacion, comunicaciones y pruebas.

## Pendientes de confirmacion

- Fechas oficiales de entrega, presentacion y cierre.
- Responsables nominales y suplentes para validacion SEU por HU.
- Plantillas institucionales definitivas, campos finales de Sheets y ubicacion formal de logs.
- Disponibilidad concreta del entorno tecnico y de usuarios internos para pruebas TRL 4.

## Uso en Mermaid Live

```bash
xdg-open https://mermaid.live/
```

Luego abrir `diagrama-gantt-agente-1.mmd` y usar su contenido como fuente del diagrama.

## Uso del visor editable

Abrir `visor-gantt-agente-1.html` en el navegador. El visor funciona sin servidor local y sin dependencias externas: renderiza la fuente Mermaid embebida, permite buscar por tarea, filtrar por semestre/bloque/hito, editar campos desde el panel lateral y exportar un nuevo `diagrama-gantt-agente-1.mmd`.

El navegador no puede guardar directamente sobre el repo por seguridad. Si se hacen cambios en el visor, exportar el `.mmd` y reemplazar la fuente editable solo despues de revisar que el contenido siga respetando el alcance, los hitos y las fechas confirmadas.

## Renderizado Mermaid local

```bash
mmdc -p Documentos/Gantt/puppeteer-config.json -i Documentos/Gantt/diagrama-gantt-agente-1.mmd -o Documentos/Gantt/diagrama-gantt-agente-1-mermaid.svg -w 3200 -H 2600
mmdc -p Documentos/Gantt/puppeteer-config.json -i Documentos/Gantt/diagrama-gantt-agente-1.mmd -o Documentos/Gantt/diagrama-gantt-agente-1-mermaid.png -w 3200 -H 2600
```

## Renderizado PlantUML local

La version PlantUML de respaldo se puede regenerar asi, si se necesita:

```bash
JAVA_TOOL_OPTIONS=-Djava.awt.headless=true plantuml -tpng Documentos/Gantt/diagrama-gantt-agente-1.puml
JAVA_TOOL_OPTIONS=-Djava.awt.headless=true plantuml -tsvg Documentos/Gantt/diagrama-gantt-agente-1.puml
```
