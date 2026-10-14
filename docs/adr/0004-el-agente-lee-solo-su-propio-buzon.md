# El agente lee solo su propio buzon

Los comprobantes de pago llegan como respuestas a `cursoscomplementarios@`, el buzon del Departamento Cursos Complementarios, que no es del Agente 1.

Decidimos que el Departamento configure en su buzon un filtro de Gmail que reenvia esas respuestas al buzon de la cuenta tecnica del agente, y que el agente lea **solo su propio buzon**, con `gmail.readonly` sobre esa cuenta. El Departamento conserva su circuito: sigue recibiendo las respuestas y las reenvia a la Fundacion Savio.

## Considered Options

Se evaluo darle al agente acceso de lectura al buzon del Departamento por delegacion. Ampliaba permisos sobre un buzon ajeno y contradice el principio del **canal de interaccion**: recibir algo por un buzon no otorga los permisos de ese buzon.

Se evaluo que el Departamento cargara a mano en la planilla quien presento comprobante. Era viable sin Gmail, pero deja manual justo el paso que la modificacion de HU-012 busca automatizar.

## Consequences

La asociacion de una respuesta con una persona depende de que el reenvio por filtro conserve el remitente original. Eso se verifica una vez, en vivo, antes de usar el mecanismo con preinscriptos reales.

Lo que el filtro no reenvia, el agente no lo ve. El criterio del filtro (asunto de la preinscripcion con adjunto) es parte del contrato con el Departamento y no se puede cambiar solo de un lado.

## Enmienda (13/10/2026)

La credencial del agente pasó a ser una cuenta de servicio de DSI con domain-wide delegation (ADR 0011). La decisión de este ADR se mantiene: el agente lee solo el buzón de la cuenta técnica y los comprobantes llegan por el filtro de reenvío. Lo que cambia es quién lo garantiza. Antes lo garantizaba Google, porque el agente no tenía delegación. Ahora lo garantiza el propio agente, con la lista cerrada de cuentas por las que puede hacerse pasar. Si la SEU acepta que el agente lea directamente `cursoscomplementarios@`, este ADR se reemplaza.
