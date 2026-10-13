# Correo a DSI — seguimiento de la reunión del 13/10/2026

Alimenta: [Reunión con DSI: Workspace, cuenta técnica, cuentas de prueba y host](https://github.com/SpendIce/Proyecto-Final/issues/62) y [Modelo de seguridad de la cuenta Google del Agente 1](https://github.com/SpendIce/Proyecto-Final/issues/64)

Acta: `Acta-DSI-2026-10-13.md` (misma carpeta).

- **Para:** Fernando Vera (DSI)
- **Asunto:** Agente 1 (Extensión Bot): dos consultas pendientes de la reunión del 13/10

Preguntas que cubre: DSI-O2 y DSI-R4 (respondidas «no sabe»), más la cuenta para la coadministración del proyecto de Google Cloud (DSI-G1). DSI-A1, A2 y A3 (segundo paso con llave física) **no** van en este correo: dependen de si la cuenta del agente pasa a ser una cuenta de servicio (DSI-O4), y eso se decide en el modelo de seguridad. Si se mantiene el usuario dedicado, van en un segundo correo. DSI-L3 (equipo o servidor) se gestiona con el laboratorio.

**Fecha límite:** entrega de los anexos al laboratorio. **Reemplazo si no hay respuesta:** O2 y R4 se declaran «Previsto – no implementado» en el Anexo 3. Para R4 rige el control propio del agente (solo envía a la lista de destinatarios de prueba). Para O2, la alerta de DSI sobre la cuenta (DSI-D1).

---

Fernando:

Gracias por la reunión del martes. Dejé registradas las respuestas en el acta de la reunión. Me quedaron dos consultas que no pudimos cerrar, y un pedido:

1. **Otros programas con acceso a la cuenta del agente.** ¿Se puede configurar desde la consola de Google que la cuenta del agente no pueda autorizar a ningún otro programa además del agente? En la consola figura como «Controles de API» → «Acceso de apps de terceros».

2. **Destinatarios autorizados.** ¿Se puede limitar la cuenta del agente para que solo pueda enviar correos a una lista de direcciones autorizadas? En la consola figura como regla de cumplimiento de Gmail o como «Restringir la entrega».

3. **Coadministración del proyecto de Google Cloud.** Como quedamos, los sumo ya como coadministradores del proyecto con el que se conecta el agente. ¿Con qué cuenta o grupo de la facultad los agrego?

Si alguna de las dos primeras no se puede, o no conviene, me alcanza con saberlo: lo declaro así en la documentación de seguridad para el laboratorio.

Saludos,

Juan Ignacio Goñe
Ingeniería en Informática, FIE (UNDEF)
