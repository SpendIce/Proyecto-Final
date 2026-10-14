# Correo a DSI — seguimiento de la reunión del 13/10/2026

Alimenta: [Reunión con DSI: Workspace, cuenta técnica, cuentas de prueba y host](https://github.com/SpendIce/Proyecto-Final/issues/62) y [Modelo de seguridad de la cuenta Google del Agente 1](https://github.com/SpendIce/Proyecto-Final/issues/64)

Acta: `Acta-DSI-2026-10-13.md` (misma carpeta).

- **Para:** Fernando Vera (DSI)
- **Asunto:** Agente 1 (Extensión Bot): dos consultas pendientes de la reunión del 13/10

Preguntas que cubre: DSI-O2 y DSI-R4 (respondidas «no sabe»), las alertas que salieron del modelo de seguridad (DSI-D1) y quién es `agentesia@`. Actualizado el 13/10 después de resolver el modelo de seguridad (`docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`, ADR 0011). DSI entregó una cuenta de servicio en un proyecto propio, así que **no se pide** la coadministración del proyecto de Google Cloud (DSI-G1), y DSI-A1, A2 y A3 (segundo factor) **no aplican**: nadie inicia sesión con la cuenta técnica. DSI-L3 (equipo o servidor) se gestiona con el laboratorio.

**Fecha límite:** entrega de los anexos al laboratorio. **Reemplazo si no hay respuesta:** O2 y R4 se declaran «Previsto – no implementado» en el Anexo 3. Para R4 rige el control propio del agente (solo envía a la lista de destinatarios de prueba). Para O2, la alerta 3 sobre permisos OAuth nuevos. **Reemplazo de las alertas:** si no se configuran, quedan «Previsto – no implementado», y la detección se apoya en la consulta manual de la auditoría de Workspace.

---

Fernando:

Gracias por la reunión del martes, y a Eduardo por los datos de la cuenta de servicio: el agente va a usar esa cuenta, haciéndose pasar solo por la cuenta del agente. Dejé registradas las respuestas en el acta de la reunión. Me quedaron dos consultas que no pudimos cerrar y dos pedidos:

1. **Otros programas con acceso a la cuenta del agente.** ¿Se puede configurar desde la consola de Google que la cuenta del agente no pueda autorizar a ningún otro programa además del agente? En la consola figura como «Controles de API» → «Acceso de apps de terceros».

2. **Destinatarios autorizados.** ¿Se puede limitar la cuenta del agente para que solo pueda enviar correos a una lista de direcciones autorizadas? En la consola figura como regla de cumplimiento de Gmail o como «Restringir la entrega».

3. **Alertas sobre la cuenta del agente.** Como quedamos, las alertas las recibís vos. ¿Podés configurar estas reglas de actividad, con aviso para vos y para mí hasta el traspaso?
   1. Inicio de sesión de la cuenta del agente (nadie debería iniciar sesión con ella).
   2. Cambio de contraseña o de verificación en dos pasos de esa cuenta.
   3. Permiso nuevo otorgado por esa cuenta a otro programa.
   4. Cambio de miembros o de uso compartido en la unidad compartida del agente.
   5. Cambios de un administrador sobre esa cuenta.
   6. Cambios en la delegación de dominio completo.

4. **Una cuenta que no conozco.** La carpeta de Drive que hoy usa el agente es propiedad de `agentesia@` y está compartida con la cuenta del agente. ¿Sabés de quién es esa cuenta? La carpeta que me pasó Eduardo, ¿es la unidad compartida del agente? Mi idea es pasar todo a la unidad compartida y dejar a `agentesia@` sin acceso.

Si alguna de estas cosas no se puede, o no conviene, me alcanza con saberlo: lo declaro así en la documentación de seguridad para el laboratorio.

Saludos,

Juan Ignacio Goñe
Ingeniería en Informática, FIE (UNDEF)
