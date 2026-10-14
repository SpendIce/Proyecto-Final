---
status: accepted
---

# El agente se hace pasar solo por su cuenta técnica con una cuenta de servicio de DSI

El Agente 1 necesita leer y escribir en Drive, Sheets y Docs, enviar correo y leer su buzón. Hasta el 13/10 lo hacía con un usuario dedicado (la **cuenta técnica**) y un refresh token OAuth emitido por un proyecto de Google Cloud a nombre del autor. En la reunión del 13/10, DSI dijo que prefería una cuenta de servicio, y ese mismo día la entregó configurada. Está en un proyecto de DSI, tiene **domain-wide delegation** autorizada para `gmail.readonly`, `gmail.send` y `drive`, y se indica que debe hacerse pasar por la cuenta técnica.

Decidimos que **la credencial del agente es esa cuenta de servicio, y que el agente se hace pasar solo por las cuentas de una lista cerrada**, que hoy tiene únicamente a la cuenta técnica. La lista vive en el repo como archivo controlado, con el hash de cada dirección y no la dirección en claro. Entra en el manifest de la versión (ADR 0010), así que sumar una cuenta es un cambio controlado que aprueba la SEU como dueña funcional. El entorno indica por quién se hace pasar el agente. Si esa cuenta no está en la lista, el agente no arranca. Cada token registra en la auditoría por quién se pidió.

La delegación se autoriza por client ID y para todo el dominio: Google no la limita a la cuenta técnica. Quien tenga la clave puede leer y enviar correo, y acceder al Drive, como cualquier cuenta de la FIE. **DSI otorgó ese acceso y aceptó ese riesgo** (correo del 13/10, `Documentos/Reuniones/DSI-2026-10-13/Correo-DSI-cuenta-de-servicio.md`). El Anexo 3 lo declara como riesgo aceptado por DSI, y la lista cerrada es la compensación que aplica el agente.

## Considered Options

- **Mantener el usuario dedicado con OAuth y `drive.file`.** Si se roba la credencial, se compromete solo el buzón y los archivos del agente. Además, la cuenta queda alcanzada por las políticas del dominio (2SV, API Controls). Se descartó porque DSI ya otorgó y prefiere la cuenta de servicio, y porque el proyecto OAuth está a nombre del autor, que es lo que ADR 0007 prohíbe.
- **Cuenta de servicio recortada:** delegación solo para Gmail, y Drive por la cuenta de servicio directa sobre la unidad compartida. Se descartó porque el correo de toda la FIE seguía expuesto, sumaba una segunda forma de acceso y exigía que DSI cambiara lo que ya había configurado.
- **Cuenta de servicio sin delegación.** Se descartó porque una cuenta de servicio no tiene buzón: no puede enviar las confirmaciones ni leer los comprobantes de HU-012.

## Consequences

- Nadie inicia sesión con la cuenta técnica, así que la 2SV no protege la ruta del agente. Cualquier inicio de sesión de esa cuenta dispara una alerta, y en el acta DSI resetea la contraseña sin dársela a nadie.
- La credencial OAuth anterior se da de baja cuando la cuenta de servicio funcione en vivo: se revoca el refresh token y se eliminan el cliente y el proyecto del autor.
- Las rotaciones y revocaciones de la clave las hace DSI, porque el proyecto es suyo. El agente muestra que se detiene ante una clave inválida, y la revocación del lado de Google remite a su documentación.
- Los scopes son los autorizados: `drive`, `gmail.send` y `gmail.readonly`. `drive.file` queda previsto, y por eso el agente sigue creando todo archivo que usa.
- Si la SEU acepta que el agente envíe como `cursoscomplementarios@` o lea su buzón, entra sumando esa cuenta a la lista. Leer ese buzón reemplaza ADR 0004.
