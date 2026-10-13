---
status: accepted
---

# El agente no arranca si sus archivos controlados no coinciden con su versión

Después del traspaso, el Agente 1 corre en un host que opera Informática, lo evolucionan alumnos que el autor no conoce y lo dispara un scheduler local sin nadie mirando. Un prompt, una política de redes o un contrato editado a mano en ese host cambian lo que el agente redacta o lo que deja pasar el gate, sin PR, sin evidencia de regresión y sin que la auditoría registre que la pieza salió de otra cosa.

Decidimos que **cada versión del agente lleva un manifest con el sha256 de todo lo controlado que vive en el repo**: código, prompts, políticas, contratos, migraciones y `uv.lock`. Al arrancar en modo operación (scheduler o corrida `--live`), el agente lo compara con los archivos del host y, **si alguno no coincide, no arranca**: registra en la auditoría el archivo, el hash esperado y el encontrado. En desarrollo y en la suite no se verifica. Cada registro de auditoría lleva la versión del agente y el hash del manifest, así que cualquier pieza puede rastrearse hasta lo que la produjo.

La configuración por entorno (IDs de planillas y Forms, scopes) queda fuera de este fail-closed. Informática la cambia legítimamente sin pasar por el repo, y frenar el arranque por eso solo le agrega fricción a una rotación. Su huella, sin secretos, se compara con la de la corrida anterior: si cambió, se registra y se avisa al operador. El control real de esa clase está del lado de Google.

## Considered Options

- **Arrancar, avisar y registrar.** Se descartó porque un agente que corre solo con un prompt alterado ya produjo borradores antes de que alguien lea el aviso, y el resto del sistema es fail-closed.
- **Fail-closed solo para lo que toca el gate o llega a un destinatario.** Se descartó porque obliga a mantener una frontera entre clases de archivos que el código no garantiza: un cambio en un módulo "inocuo" puede alterar el gate.
- **Exigir `git status` limpio sobre un tag.** Se descartó porque depende de que el host tenga `.git` y de que nadie lo manipule, y la operación de Informática no tiene por qué clonar el repo.
- **Fail-closed también para la configuración por entorno, con una huella esperada declarada aparte.** Se descartó porque la misma persona edita las dos cosas: no agrega control, solo fricción.

## Consequences

Toda modificación en el host exige cortar una versión nueva o volver a la anterior: el operador no puede "probar algo" en caliente. `scripts/manifest_corte.py` deja de mantener su propia lista de fuentes y referencia la versión y su manifest.
