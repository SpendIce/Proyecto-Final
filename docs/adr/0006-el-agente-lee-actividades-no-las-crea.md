---
status: accepted (la parte de Historia Viva es una propuesta pendiente con Ignacio, #17)
---

# El Agente 1 lee actividades, no las crea

Una **actividad** de extension nace de dos documentos: una propuesta (Word) y despues un informe de actividad (PDF), que puede cambiar datos de la propuesta. Un diseno del 07/10 (`Documentos/PoC/Registro-Actividades-Fuentes-Documentales-v1.md`) proponia que el Agente 1 vinculara los dos documentos, extrajera los datos con procedencia por campo y resolviera las discrepancias antes de generar.

Decidimos que el Agente 1 **solo lee** actividades ya resueltas, una fila por actividad, desde una planilla de actividades con contrato versionado. Crear la actividad a partir de sus documentos es ingesta, y la bible se la asigna a **Historia Viva** (HU-030: "ingeste, procese y catalogue [...] la informacion dispersa de las actividades"). El Agente 1 guarda la procedencia por actividad (un link al documento vigente), no por campo.

## Considered Options

- **El Agente 1 crea la actividad desde los documentos.** Se descarto porque duplica en el Agente 1 un trabajo de otro agente, y porque declararlo en la mesa final obligaba a mostrar en vivo una extraccion de documentos que no se llegaba a asegurar antes del 18/11.
- **Seguir con el contrato de nueve columnas.** Se descarto porque no puede llevar las fechas separadas, la modalidad, la duracion ni el enlace de inscripcion sin mezclarlos en la descripcion, y el recorrido de la demo con NotebookLM Nivel 2 los necesita.

## Consequences

Mientras el contrato con Historia Viva no este cerrado, la planilla de actividades de D2 es un insumo provisional declarado que carga una persona: hoy el autor del PPS, despues la SEU. La original es esa planilla, no el repositorio, porque en la realidad los datos de actividades los genera la SEU. Las pruebas y el respaldo offline leen una copia CSV exportada.

Se le propone a Ignacio que Historia Viva guarde tambien las actividades vigentes, no solo las historicas. Si no acepta, la planilla queda como fuente de la SEU y el Agente 1 no cambia: lee por el mismo puerto y solo cambia el adapter.

El plan de pago de HU-012 (#38) es una excepcion ya decidida: conserva procedencia por dato.
