# Correo de DSI — cuenta de servicio del Agente 1 (13/10/2026)

Alimenta: [Modelo de seguridad de la cuenta Google del Agente 1](https://github.com/SpendIce/Proyecto-Final/issues/64)

Evidencia de que DSI configuró la identidad del agente y aceptó su alcance. Se transcriben solo los datos que no son secretos. **No se versionan** la clave privada (adjunto `.json`), el client ID de la cuenta de servicio ni el enlace a la carpeta de Drive.

- **De:** Eduardo Sepúlveda (DSI)
- **Para:** Juan Ignacio Goñe
- **Cc:** Fernando Vera Batista, responsable de DSI
- **Fecha:** 13/10/2026, 10:17
- **Asunto:** Credenciales y datos de integración Google Workspace - App IA
- **Transporte:** dentro del dominio, firmado por `undef.edu.ar`, cifrado estándar (TLS)

## Qué configuró DSI

- Una cuenta de servicio en un proyecto de Google Cloud **de DSI**, con su clave privada enviada como adjunto.
- **Domain-wide delegation** autorizada en Workspace para esa cuenta de servicio, con estos scopes:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.send`
  - `https://www.googleapis.com/auth/drive`
- La cuenta por la que se indica hacerse pasar es la **cuenta técnica** del Agente 1 (`bot_ia1@`).
- Una carpeta de Drive para la integración.

## Alcance que se acepta

La delegación se autoriza por client ID y para todo el dominio. Google no la limita a la cuenta técnica: quien tenga la clave puede leer y enviar correo, y acceder al Drive, como cualquier cuenta de la FIE. DSI otorgó ese acceso a sabiendas, y el autor del PPS lo adopta como **riesgo aceptado por DSI**. La restricción a la cuenta técnica la impone el Agente 1 (lista cerrada de cuentas por las que puede hacerse pasar, como cambio controlado). La clave circuló por correo interno del dominio; se confía en el cifrado del transporte y se borra del buzón y de la carpeta de descargas una vez instalada en el host.
