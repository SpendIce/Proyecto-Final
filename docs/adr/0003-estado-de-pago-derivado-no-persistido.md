# Estado de pago derivado, no persistido

HU-012 tiene que informar cuantas cuotas pago cada preinscripto o inscripto y mandar un **recordatorio de pago** a quien no presento comprobante. El 22/09 la SEU confirmo la minimizacion de datos: los correos de los destinatarios llegan para el envio y no se persisten.

Decidimos que el Agente 1 **no guarde el estado de pago por persona**. En cada corrida lo recalcula a partir de cuatro fuentes: el **plan de pago** de la actividad, el padron, los **comprobantes presentados** que hay en el buzon propio del agente y las **novedades de pago** que carga el Departamento. Los recordatorios de pago no agregan persistencia propia: pasan por el circuito de HU-012 y persisten lo mismo que cualquier notificacion (el registro por clave hash con asunto y cuerpo del borrador, y el destinatario en la cola mientras el envio esta pendiente). No existe un registro de pagos.

La fuente de verdad del pago queda donde ya estaba: los correos bajo custodia institucional en Workspace y el registro del Departamento.

## Considered Options

Se evaluo un registro de pagos propio del agente, con un estado por persona y por cuota. Es lo obvio, pero obliga a retener datos personales durante semanas contra lo confirmado por la SEU, y duplica una informacion cuyo dueno es el Departamento. Si las dos copias se desincronizan, no queda claro cual vale.

## Consequences

Un lector del codigo va a ver que el agente vuelve a leer el buzon en cada corrida y que no hay tabla de pagos, y puede tomarlo por una ineficiencia. Es deliberado: agregar una tabla de pagos reabre la decision de minimizacion con la SEU.

Si un correo se borra del buzon del agente, la cuota vuelve a figurar como pendiente. El control es la aprobacion utilitaria del lote de recordatorios. Lo que no se puede deducir de los correos lo corrige el Departamento con una novedad de pago, nunca el agente.
