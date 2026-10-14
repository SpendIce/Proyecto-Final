# Modelo de seguridad de la cuenta Google del Agente 1

Decidido el 13/10/2026 en [Modelo de seguridad de la cuenta Google del Agente 1](https://github.com/SpendIce/Proyecto-Final/issues/64). Alimenta el componente «Google Workspace» del Anexo 3 del laboratorio ([Perfil de seguridad por componente para el Anexo 3 del laboratorio](https://github.com/SpendIce/Proyecto-Final/issues/58)).

**Criterio:** la máxima seguridad alcanzable sin costo con Google Workspace for Education Fundamentals, la edición de la FIE. Lo que exige más se declara «Previsto – no implementado». Lo que Google ya documenta se enlaza y no se reescribe.

**Insumos:**
- Research de controles de Google: rama `research/controles-seguridad-google`, `docs/research/controles-seguridad-google-agente-1.md`.
- Acta de la reunión con DSI del 13/10: `Documentos/Reuniones/DSI-2026-10-13/Acta-DSI-2026-10-13.md`.
- Correo de DSI con la cuenta de servicio: `Documentos/Reuniones/DSI-2026-10-13/Correo-DSI-cuenta-de-servicio.md`.

**ADR:** 0004 (con su enmienda), 0007, 0009, 0010 y 0011.

**Estados:**
- **I:** implementado o a implementar antes de la entrega de los anexos.
- **P:** «Previsto – no implementado».
- **RA:** riesgo aceptado, con quién lo aceptó.

## 1. Mecanismo de identidad

| | |
|---|---|
| **Elegido** | Cuenta de servicio en un proyecto de Google Cloud de DSI, con domain-wide delegation, que se hace pasar por la **cuenta técnica** (`bot_ia1@`). (I) |
| **Motivo** | Es lo que DSI prefiere y ya otorgó. El proyecto es de DSI, así que no queda nada a nombre del autor (ADR 0007). Nadie inicia sesión para operar. |
| **Riesgo** | La delegación se autoriza por client ID para todo el dominio. Con la clave se puede leer y enviar correo, y acceder al Drive, como cualquier cuenta de la FIE. **(RA: DSI, correo del 13/10)**. Google: [162106](https://support.google.com/a/answer/162106?hl=en), [service-account](https://developers.google.com/identity/protocols/oauth2/service-account?hl=en). |
| **Compensación** | Lista cerrada de cuentas por las que el agente puede hacerse pasar. Es un archivo controlado del repo con hashes de las direcciones, entra en el manifest (ADR 0010) y hoy tiene solo a la cuenta técnica. Si el entorno indica otra cuenta, el agente no arranca. Cada token registra en la auditoría por quién se pidió. Un test asegura que no hay otro camino para pedir un token. (I) |
| **Descartado** | (a) Usuario dedicado con OAuth y `drive.file`: el daño posible era el menor, pero el proyecto OAuth estaba a nombre del autor y DSI prefiere la cuenta de servicio. (b) Delegación solo para Gmail y Drive por la cuenta de servicio directa: el correo de toda la FIE seguía expuesto y quedaban dos formas de acceso. (c) Cuenta de servicio sin delegación: no tiene buzón, así que rompe HU-012. |
| **Evolución** | Si la SEU acepta que el agente envíe como `cursoscomplementarios@` o lea ese buzón, se suma a la lista como cambio controlado aprobado por la SEU. Leer ese buzón reemplaza ADR 0004. |

## 2. Autenticación de la cuenta técnica

| | |
|---|---|
| **Elegido** | La ruta del agente no inicia sesión. Cualquier inicio de sesión interactivo de la cuenta técnica es anómalo y dispara una alerta (§6). En el acta de traspaso, DSI resetea la contraseña y no se la da a nadie (ADR 0007). (I) |
| **2SV de la cuenta técnica** | (P). Nadie inicia sesión con ella y no hay llave física disponible. Google: [9176657](https://support.google.com/a/answer/9176657?hl=en). |
| **Recuperación** | Configurada por DSI en la cuenta del agente (DSI-A5). |
| **Rotación de contraseña de rutina** | DSI no rota contraseñas (DSI-A4). Se rota en el acta y ante un incidente. |

## 3. Scopes por ambiente

| | |
|---|---|
| **Elegido** | `drive`, `gmail.send` y `gmail.readonly`: los autorizados en la delegación. Sheets y Docs aceptan `drive`. Se piden los mismos en D2 y D3. (I) |
| **Práctica** | El agente crea todo archivo que usa: planillas, plantillas y la planilla de respuestas de cada Form. Las personas cargan el contenido. Así se puede pasar a `drive.file` sin migrar archivos. |
| **`drive.file`** | (P). Con delegación, solo se pueden pedir scopes que estén autorizados, y cambiarlo es una configuración de DSI. Google: [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth), [Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes). |
| **`gmail.readonly`** | Se mantiene porque `gmail.metadata` no da acceso a los adjuntos de los comprobantes. La lectura se limita al buzón de la cuenta técnica (ADR 0004). |
| **Envío** | La lista de destinatarios de prueba la controla el agente. Restringir la entrega del lado de Google está pedido a DSI (DSI-R4). Si no responde: (P). Google: [2640542](https://support.google.com/a/answer/2640542?hl=en). |

## 4. Custodia, rotación y revocación del secreto

| | |
|---|---|
| **Secreto** | La clave JSON de la cuenta de servicio. |
| **Custodia hasta el traspaso** | En `~/.config/agente1/` con `chmod 600`, fuera del repo, en el host de la demo con disco cifrado. El env file apunta a esa ruta. La copia recibida por correo se borra del buzón (incluida la papelera) y de Descargas una vez instalada. (I) |
| **Custodia después del traspaso** | En la gestión de secretos de la facultad (DSI-G2). |
| **Transporte inicial** | La clave llegó por correo interno del dominio, con TLS. Se confía en ese cifrado. **(RA: el autor y DSI)** |
| **Rotación** | En el acta de traspaso y ante un incidente: DSI crea una clave nueva y borra la anterior. Sin rotación periódica. (I) |
| **Revocación** | La hace DSI: borra o deshabilita la clave, o quita la delegación. DSI no hace pruebas conjuntas de revocación (acta del 13/10). El agente se detiene ante una clave inválida, y eso se prueba de forma reproducible. La revocación del lado de Google remite a [best-practices-for-managing-service-account-keys](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys?hl=en). (I) |
| **Credencial anterior** | El refresh token OAuth se revoca, y el cliente y el proyecto de Google Cloud del autor se eliminan cuando la cuenta de servicio funcione en vivo. No quedan dos credenciales activas. (I) |
| **Alternativas sin clave** | Workload Identity Federation, HSM o TPM: (P). Google: [workload-identity-federation](https://cloud.google.com/iam/docs/workload-identity-federation?hl=en). |

## 5. Propiedad de los recursos

| | |
|---|---|
| **Elegido** | Una unidad compartida de la organización por ambiente (D2 ahora, D3 cuando llegue), administrada por DSI. (I) |
| **Miembros** | Fernando Vera (DSI) como *Manager*. La cuenta técnica como *Content manager*, el mínimo para borrar sus propios respaldos (ADR 0009). El autor como *Content manager* hasta el acta. Después, el operador designado según DSI. La cuenta de servicio **no** es miembro: actúa como la cuenta técnica, así que no se activa el indicador de «externo» que Google muestra para las cuentas de servicio ([60781](https://support.google.com/a/answer/60781?hl=en)). |
| **Uso compartido** | Solo miembros de la FIE. Los miembros no comparten fuera de la unidad y quienes no son miembros no acceden a los archivos. Compartir hacia afuera está permitido a nivel facultad (DSI-R3), así que la restricción se configura en la unidad. Google: [7662202](https://support.google.com/a/answer/7662202?hl=en). |
| **Situación anterior** | La carpeta de D2 es propiedad de `agentesia@`, una cuenta sin dueño conocido, y está compartida con la cuenta técnica. Se migra a la unidad compartida y `agentesia@` queda afuera. Se le pregunta a DSI de quién es. |
| **Descartado** | Dejar los recursos en una carpeta de una cuenta: se pierden si esa cuenta se suspende o se borra. |

## 6. Detección de modificaciones no autorizadas

Reglas de actividad de Fundamentals, **solo de notificación** ([11341109](https://support.google.com/a/answer/11341109?hl=en)), en el centro de alertas. Las configura DSI. (I, pedido a DSI)

1. Inicio de sesión de la cuenta técnica.
2. Cambio de contraseña o de 2SV de la cuenta técnica.
3. Nuevo permiso OAuth otorgado por la cuenta técnica. También compensa DSI-O2 si no responden.
4. Cambio de miembros o de uso compartido en la unidad del agente.
5. Cambios del admin sobre la cuenta técnica.
6. Cambio en la configuración de domain-wide delegation (registro de Admin).

**Destinatarios:** Fernando Vera (DSI) y el autor hasta el acta. Después, DSI y el operador designado; el autor no.

**Registro:** auditoría de Workspace (Admin, User, OAuth, Drive y Gmail), con 6 meses de retención que no se pueden cambiar ([7061566](https://support.google.com/a/answer/7061566?hl=en)). Las acciones del agente aparecen como hechas por la cuenta técnica. El control de cambios cita estas alertas como detección de cambios hechos por fuera del proceso para la clase «configuración de Workspace y credenciales».

**Claves nuevas de la cuenta de servicio:** quedan en los registros de auditoría de Google Cloud del proyecto de DSI, y se consultan como evidencia. Una alerta automática sobre eso: (P), porque su costo no está verificado.

**Del lado del agente:** la huella de la configuración por entorno se registra y avisa ([Registro y aviso de cambios en la configuración por entorno](https://github.com/SpendIce/Proyecto-Final/issues/94)).

**Requieren Standard o Plus (P):** Context-Aware Access, eventos «API call» del registro OAuth, reglas de actividad con acciones, security investigation tool y export a BigQuery.

## 7. Respuesta a incidentes

| | |
|---|---|
| **Detección** | Una alerta de §6, o el agente que se detiene con `workspace_token_exchange_denied`. |
| **Contención** | DSI bloquea la cuenta técnica desde la alerta (DSI-D3). Con la cuenta suspendida, la cuenta de servicio no puede hacerse pasar por ella. Si se sospecha de la clave, DSI la deshabilita. Para el agente es un **cambio de emergencia**: se suspende, no se corrige en caliente. |
| **Reanudación** | (1) DSI rehabilita la cuenta (DSI-D4). (2) DSI rota la clave y resetea la contraseña. (3) Se corre el smoke en vivo. (4) Queda en el changelog como cambio de emergencia. DSI y el operador (el autor hasta el acta) deciden juntos; ninguno de los dos reanuda solo. |
