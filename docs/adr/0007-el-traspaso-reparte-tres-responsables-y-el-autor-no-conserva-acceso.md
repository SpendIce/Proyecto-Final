---
status: accepted
---

# El traspaso reparte el Agente 1 en tres responsables y el autor no conserva acceso

Despues de la presentacion final el autor del PPS egresa, y el Agente 1 tiene que seguir funcionando y evolucionando sin el. Decidimos repartirlo en tres responsables: el **responsable de operacion** es la Direccion de la carrera de Ingenieria en Informatica, que designa un operador en el acta; el **dueno funcional** es la SEU; el **responsable de evolucion** son los alumnos de la carrera que continuan el P100. La administracion del Workspace (recuperacion, revocacion y suspension de la cuenta tecnica) sigue siendo de DSI en cualquier caso. En el acta el operador cambia la contrasena y el segundo factor de la cuenta tecnica, revoca el refresh token y genera un client secret nuevo, y se prueba que el sistema funciona con las credenciales del autor ya revocadas. El autor no conserva ningun acceso heredado.

## Considered Options

- **DSI como responsable de operacion.** Es lo que se espera por ser quien administra el Workspace. Se descarto como punto de partida porque el P100 es un proyecto de la carrera y quien decide sobre el es su director. La Direccion puede delegar la ejecucion en DSI; si lo hace, el operador designado es DSI y nada del diseno cambia.
- **Dos responsables (operacion y evolucion).** Se descarto porque deja sin dueno las plantillas aprobadas, el padron de roles, la lista de cierre y quien aprueba cada pieza. Eso no es operar ni cambiar codigo, y sin un dueno funcional el control de cambios no tiene quien apruebe el contenido.
- **El autor conserva acceso como respaldo.** Se descarto porque es justo la dependencia personal que el traspaso quiere eliminar, y porque la unica prueba fuerte de que no existe es que el sistema funcione con su acceso revocado.

## Consequences

- Desde ahora ningun recurso nuevo puede quedar a nombre del autor, las credenciales tienen que poder rotarse sin el, y el segundo factor de la cuenta tecnica no puede estar en un dispositivo suyo.
- Toda la documentacion de operacion se escribe para "el operador designado", sin suponer quien es.
- Se entrega lo que haya en febrero: si el agente opera, el receptor lo continua; si no, queda listo para operar. Entre la presentacion final y el inicio de clases se suspende por defecto, salvo que el operador ya este designado y acepte.
- El repositorio del Agente 1 se extrae del workspace academico del autor con su historia. Donde vive lo decide la Direccion de carrera.
