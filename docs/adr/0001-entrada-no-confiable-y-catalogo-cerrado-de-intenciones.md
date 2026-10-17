# Entrada no confiable y catalogo cerrado de intenciones

HU-013 permite que una persona de la SEU le pida algo al Agente 1 en prosa libre. A diferencia de HU-010 y HU-011 —donde el texto libre del formulario es un **dato a transcribir**, delimitado en el prompt y contrastable contra los hechos fuente por el gate— en HU-013 la prosa es **una instruccion cuyo proposito es cambiar el comportamiento**. Esa diferencia invalida la defensa existente: no hay hecho fuente contra el cual comparar, y no se puede distinguir estructuralmente una instruccion legitima de una inyectada.

Decidimos que una **solicitud en lenguaje natural** nunca llegue como instruccion al modelo generador. Se interpreta primero a una **intencion** tomada de un catalogo cerrado; los parametros de generacion salen siempre de fuentes que la institucion controla. Una solicitud que no corresponde a ninguna intencion del catalogo se rechaza: no se aproxima a la mas parecida.

La interpretacion es determinista primero y usa el modelo como fallback ante lo ambiguo, validando igual su salida contra el catalogo. La busqueda difusa de la actividad tambien es determinista, sobre un indice normalizado: **el contenido de la planilla nunca entra a un prompt**. Para resolver la actividad, el modelo solo extrae terminos de busqueda estructurados a partir de la prosa. La enmienda siguiente permite ademas proponer una intencion, sin habilitar su despacho.

El efecto es que el texto inyectado solo puede producir una intencion valida o un rechazo, nunca una instruccion nueva.

## Considered Options

Se evaluo dejar que el modelo interpretara libremente la solicitud, y se descarto: paga inferencia y superficie de ataque para una decision ternaria.

Se evaluo tambien un matcher puramente deterministico sin modelo, y se descarto por el lado opuesto: el DoD exige que la interfaz sea usable por personal no tecnico, y un matcher rigido convierte la historia en una linea de comandos con sinonimos.

La resolucion difusa de la actividad **por el modelo sobre las filas** se descarto explicitamente: una fila maliciosa podria alterar el comportamiento del agente. Resuelta por codigo, el peor caso es elegir mal una actividad —un borrador equivocado, visible de inmediato y bloqueado igual por el gate de hechos y por la validacion humana.

## Consequences

El catalogo cerrado obliga a mantenimiento: cuando existan pipelines de newsletter y de correo institucional, hay que agregar sus intenciones. Para que esa obligacion no dependa de que alguien lea un comentario, las intenciones sin pipeline se versionan en el contrato con estado `NO_APLICADA_PENDIENTE_PIPELINE`, siguiendo el patron de la politica de redes, y la suite falla si alguien activa una sin su regresion.

Si el modelo local no esta disponible, el camino determinista sigue funcionando: el agente degrada en cobertura, no en disponibilidad.

## Enmienda aceptada el 16/10/2026: propuesta de intencion con confirmacion humana

Decision de Juani en [Decidir si el modelo puede recuperar un pedido cuya clasificacion deterministica fallo](https://github.com/SpendIce/Proyecto-Final/issues/27). Cuando la clasificacion deterministica no reconoce el pedido, el modelo puede proponer exclusivamente `generar_gacetilla` o `generar_post`, con salida estructurada validada contra el catalogo. No revisa una intencion ya reconocida ni recupera por aproximacion acciones conocidas fuera de alcance. Una propuesta no genera un borrador: requiere confirmacion expresa de la persona. Si no hay propuesta valida o el modelo no esta disponible, se pide reformular.

En el canal actual, la propuesta se devuelve por correo al solicitante con un enlace al mismo Form, prellenado con una solicitud explicita construida por codigo a partir de la intencion permitida y de identificadores de actividades resueltas contra la fuente institucional. Abrir el enlace no ejecuta nada. La persona revisa, puede editar y envia el Form; ese envio constituye un pedido nuevo, con identidad del canal, rol, permisos, actividad y gates verificados nuevamente. La propuesta no tiene un vencimiento propio de quince minutos ni depende de un estado pendiente entre turnos. La referencia al pedido original sirve para trazabilidad, no como autorizacion. Los enlaces y avisos no copian prosa libre del usuario o del modelo. Si faltan actividad o canal, se utiliza el circuito de aclaracion correspondiente.

La confirmacion del tipo de pieza no sustituye la validacion humana del contenido ni habilita publicacion, envio o emision. Las otras intenciones conservan su circuito actual. Se acepta el costo de un intercambio Form → correo → Form para recuperar errores de tipeo sin convertir la salida del modelo en una orden ejecutable. Se descarta exigir un selector de pieza en el Form como solucion de este ticket.

Esta enmienda registra el comportamiento acordado; su implementacion y evidencia quedan pendientes de [HU-013: proponer intencion y confirmar por correo y Form](https://github.com/SpendIce/Proyecto-Final/issues/115).
