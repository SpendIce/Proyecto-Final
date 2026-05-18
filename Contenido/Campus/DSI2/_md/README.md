# DSI2 Markdown Operativo

Corpus textual generado desde los PDFs de `Contenido/Campus/DSI2/` para busqueda y recuperacion por agentes.

Uso recomendado:
- Buscar primero en esta carpeta con `rg`.
- Priorizar las unidades separadas antes que `carpeta-dsi-ii-escaneada.md`, porque el compilado escaneado es respaldo de baja prioridad.
- Usar el PDF fuente cuando se necesite revisar diagramas, tablas, formato visual o posibles errores de OCR.

Metodo:
- Extraccion inicial con `pdftotext -layout`.
- OCR local con `pdftoppm` + `tesseract -l spa+eng` para las presentaciones DSI2, porque la mayoria no tenia texto embebido suficiente.

