# Sincronización de bible — 2026-10-07

## Fuente y método

Se comparó la working source vigente con `/home/spendice/Downloads/Procesos y Agentes SEU - FIE con Backlog técnico (Jira)(2).md`. Para comparar contenido se normalizaron las URIs de imágenes base64; se comparó además el hash SHA-256 de cada una contra `Contenido/bible/assets/procesos-y-agentes/imageN.png`.

La working source `Contenido/bible/Procesos y Agentes.md` se actualizó desde la exportación nueva. Las 18 referencias base64 se normalizaron a rutas de assets ya versionados: las 18 imágenes coinciden byte a byte con las existentes. No se duplicaron ni modificaron assets.

## Resultado para Agente 1

- Cambios textuales: se reinsertan encabezados organizativos, entre ellos `Agente 1 - Notas` y `Notas Diseño - AI 1`, además de encabezados para otras partes del documento. Esto mejora navegación, pero no agrega contenido funcional.
- Sin cambios detectados en las definiciones operativas de A1, historias de usuario, criterios DoD, roles, proceso BPM, integraciones ni infraestructura. En particular, no cambia la frontera PPS/P100 registrada el 2026-09-30 y reiterada el 2026-10-05: HU-015 A1 de certificados/triggers y HU-016/HU-017 quedan fuera del PPS; las ampliaciones de HU-010..HU-014 permanecen dentro, incluida la ampliación de HU-012 a situación de pagos.
- Esta revisión compara texto Markdown. El formato exportado no permite determinar cambios marcados con resaltado o comentarios en el documento vivo.

## Resumen

La versión `(2)` no introduce modificaciones sustantivas que afecten al Agente 1; ordena la estructura y vuelve a incrustar imágenes que ya estaban disponibles localmente.
