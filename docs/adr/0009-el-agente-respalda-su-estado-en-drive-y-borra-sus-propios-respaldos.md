---
status: accepted
---

# El agente respalda su estado en Drive y borra sus propios respaldos vencidos

El estado local del Agente 1 (registro de confirmaciones, logs JSONL, registro de pedidos atendidos y manifests) vive en el host. De ese estado, el que no se puede perder es el registro de confirmaciones: sin él no se sabe qué se envió, y un reintento puede mandar un duplicado a una persona real. Lo demás que importa ya está en Google (Gmail Enviados, respuestas de Forms, Sheets).

Decidimos que **el scheduler local respalda el estado una vez por día**: en la primera corrida de la ventana de operación, sube un archivo nuevo a una carpeta de la cuenta técnica que no se comparte con nadie. Así el RPO queda en un día hábil. Si el respaldo falla, el error queda en la auditoría y se le avisa al operador; la corrida sigue. Al restaurar, toda reserva o aprobación posterior al respaldo se trata como `ENVIO_INDETERMINADO`, y no se reenvía hasta que una persona la cruce contra Gmail Enviados.

**Esto es una excepción acotada a "escribir es siempre crear nuevo; el agente nunca borra".** El agente borra sus propios respaldos más viejos que la ventana de reconciliación (30 días). Solo puede hacerlo en la carpeta de respaldo, identificada por id, y cada borrado queda auditado. La razón es la retención acotada que interpreta lo que la SEU dijo el 22/09 («el sistema no retiene datos»): el texto de los borradores, que incluye datos de la persona, se purga del registro al cerrar el ciclo. Si los respaldos se guardaran indefinidamente, ese dato seguiría existiendo en ellos.

Los respaldos no se cifran del lado del cliente: se confía en el cifrado en reposo de Google y en que la carpeta no se comparte. Cifrar sumaría una clave más para custodiar y rotar en el acta de traspaso sin el autor. Se acepta que el respaldo y Google comparten dominio de falla: el respaldo cubre la pérdida del host, no la suspensión ni el compromiso de la cuenta técnica.

## Considered Options

- **Respaldo manual del operador a un medio externo.** Se descartó porque depende de que alguien se acuerde y porque saca datos personales del dominio de la FIE.
- **Que el operador borre los respaldos vencidos a mano.** Se descartó por la misma razón: si se olvida, la retención acotada deja de cumplirse sin que nadie lo note.
- **Regla de retención de Google Vault.** Se descartó para 2026 porque la configura DSI y no está confirmado que la edición de Workspace de la FIE la incluya. Si la incluye, puede reemplazar el borrado propio sin cambiar la política.
- **Registro que guarde solo hashes, sin el texto.** Se descartó porque impide reconciliar un envío indeterminado con el registro a la vista.

## Consequences

Subir los respaldos y borrar los propios funciona con `drive.file`. La decisión no exige un scope nuevo, y el Modelo de seguridad de la cuenta Google puede bajar el scope actual (`drive`) sin romper el respaldo.
