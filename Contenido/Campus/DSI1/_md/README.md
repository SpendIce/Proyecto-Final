# DSI1 Markdown Operativo

Corpus textual generado desde los PDFs de `Contenido/Campus/DSI1/` para busqueda y recuperacion por agentes.

Uso recomendado:
- Buscar primero en esta carpeta con `rg`.
- Usar el PDF fuente cuando se necesite revisar diagramas, tablas, formato visual o posibles errores de extraccion.
- Cada archivo Markdown incluye su PDF fuente y conteo de palabras extraidas.

Metodo:
- Extraccion directa con `pdftotext -layout` cuando el PDF tenia texto embebido.
- OCR local con `pdftoppm` + `tesseract -l spa+eng` para `unidad-iii-i.md`, porque la extraccion directa era insuficiente.

