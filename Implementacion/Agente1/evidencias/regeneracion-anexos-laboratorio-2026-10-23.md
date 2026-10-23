# Regeneración de los anexos de laboratorio (#147)

- **Estado:** anexos 1, 2 y 3 regenerados sobre el estado del 23/10/2026, con el sistema en contenedores en el servidor de la facultad. Listos para revisión de Juani antes del envío (fecha límite: fin de la cursada, 25/11).
- **Foto declarada:** corte del 23/10/2026, versión del agente **0.5.4** (tag `agente1-v0.5.4`). Reemplaza la foto del 17/10 (`3e392c5`), que describía la laptop como host.
- **Entrega:** `Documentos/Laboratorio/Entrega/` (`Anexo1-Presentacion.docx`, `Anexo2-Calidad.docx`, `Anexo3-Seguridad.docx`), sobre las plantillas oficiales 2025. La carpeta deja de llevar fecha: el envío no fue el 23/10.

## Qué cambió en las tablas fuente

**Perfil de seguridad** (Anexo 3):
- **Aislamiento de ejecución del modelo:** de `C` a `A`. Ollama corre en su contenedor, sin root, con sistema de archivos de sólo lectura y modelos montados en sólo lectura.
- **Modelo local sin salida a internet:** suma la barrera del despliegue, la red interna sin egreso, verificada en el servidor.
- **Límites de recursos de los contenedores:** de `C` a `B`. Hay techo de memoria y de procesos; no hay límite de CPU, a propósito.
- **Host de demostración D3:** de `C` a `A + RA`. Corre en el servidor; el riesgo aceptado es un solo host y el reinicio del servidor sin probar.
- **Custodia y transporte del secreto:** se corrige «disco cifrado». El disco no está cifrado, así que pasa a `RA` con control compensatorio, y la OAuth figura dada de baja.
- **Filas nuevas:**
  - «Ejecución en contenedores endurecidos» (`A`). Se declara en el Anexo 3 en lugar de «Control de cambios: CI, cobertura y linter».
  - «Riesgo aceptado de la administración de Docker» (`A + RA`).
- **Ajustadas para el contenedor:** el manifest (también verifica dentro del contenedor), los secretos (no entran a la imagen) y el smoke de identidad, que ahora está ejecutado.

**Perfil de calidad** (anexos 1 y 2):
- **Corrección del contenido generado:** de `B` a `A`. Con `gemma4:e4b`: 48/48 y 18/18 en la medición de #51, y 6/6, 4/4 y 8/8 desde el contenedor.
- **Comportamiento temporal y utilización de recursos:** de `C` a `B`.
- **Disponibilidad:** de `C` a `B`, por el reinicio automático verificado.
- **Aprendizaje y asistencia:** de `C` a `B`, porque el manual existe (#81).
- **Analizabilidad y capacidad de prueba:** de `B` a `A`, porque hay CI, linter y cobertura (#90).
- **Instalabilidad:** de `B` a `A`, por el despliegue por CI y Portainer.
- **Recuperabilidad, interoperabilidad y adaptabilidad:** actualizadas con la evidencia del 23/10.
- **Celdas pendientes:** vuelven a la lista vigente (#88, #56, #100) y declaran las cerradas desde la foto anterior.

**Scripts generadores** (`scripts/anexo1_presentacion.py`, `anexo2_calidad.py`, `anexo3_seguridad.py`, `anexos_seleccion.py`): foto, enfoque (ejecución aislada, sistema en el servidor), estado TRL demostrado y no demostrado, brecha de HU-011 cerrada en el gate, ruta de la entrega y selección de Sistema. Son archivos controlados, por eso este cambio es la versión 0.5.4.

## Verificación

- La suite y el linter están verdes. Los tests de los anexos validan que la selección resuelve contra las tablas fuente reales.
- Las tres entregas se generaron sobre las plantillas oficiales. Extrayendo el texto de los `.docx`:
  - ninguna mención de la laptop ni de la base `3e392c5`;
  - el Anexo 1 declara el contenedor, la versión 0.5.4 y `gemma4:e4b`;
  - el Anexo 3 lista «Ejecución en contenedores endurecidos».
- Los anexos 2 y 3 llevan sólo los ítems: los niveles los completa el laboratorio.

## Pendiente antes del envío

- Revisión de Juani de los tres `.docx`.
- Si la base cambia antes del envío, se regeneran los tres juntos con la foto nueva.
