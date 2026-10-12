---
status: accepted (provisional, a confirmar con Direccion de Carrera junto con el ADR 0005)
---

# Decisiones humanas por segundo formulario con objetos pendientes declarados

El ADR 0005 define el modelo de identidad del canal por formularios: Google verifica el correo y el padron externo autoriza el rol. Quedaba por decidir como viaja y como se valida cada **decision** (publicacion de una pieza de difusion, aprobacion de plantilla por rol, aprobacion de lote con habilitacion de envios), y como se descarta un link alterado.

Decidimos que el segundo Form tenga tres campos prellenados por el link —tipo, objeto y decision— sobre un **catalogo cerrado** de pares (tipo, decision), y que el objeto solo sea valido si el agente lo **declaro pendiente** al emitir el correo que trae el link. El registro es append-only en dos archivos JSONL del directorio de estado: `decisiones-pendientes.jsonl` (que el emisor del correo abre) y `decisiones-procesadas.jsonl` (la auditoria de respuestas, registradas o rechazadas con su codigo). Registrar no dispara nada: la difusion y el envio los hace una persona; el registro es la evidencia.

El rol que cada decision exige es parte del catalogo, no un dato que viaja en el link: semantica al Responsable de Gestion del Conocimiento, utilitaria al Coordinador de Extension, publicacion a cualquiera de los dos roles designados (acta del 22/09). El correo del borrador listo trae los dos links de publicacion; el de plantilla trae un link por rol; el de lote trae el link de aprobacion.

## Considered Options

Se evaluo firmar los links (un MAC sobre el valor prellenado) para detectar la alteracion criptograficamente. Se descarto: exige distribuir y rotar un secreto, y el registro de pendientes ya cierra el caso que importa —un id inventado nunca fue declarado, asi que se rechaza sin necesidad de firma. La firma tampoco cubriria un id real re-asignado a otra decision, que el catalogo y el padron si rechazan.

Se evaluo inferir el objeto desde el correo del respondiente (por ejemplo, «el ultimo borrador enviado a esa direccion»). Se descarto porque hace ambiguo que se decidio y porque la declaracion explicita deja trazabilidad directa entre el correo emitido y la decision registrada.

Se evaluo dejar la eleccion de decision como una pregunta abierta del Form sin prellenar. Se descarto: un catalogo cerrado leido del link permite distinguir un link alterado de una decision valida, y quita la posibilidad de errores de carga.

## Consequences

Todo emisor de un correo con link de decision tiene que declarar el pendiente primero: el adapter del canal de pedidos lo hace solo para publicaciones, y los emisores de plantilla y de lote lo haran cuando existan (#73, #75). Un pendiente nunca declarado equivale a un link muerto: la respuesta llega y se rechaza como `objeto_inexistente`, registrada igual.

El registro de decisiones es una lista de eventos, no un estado final: dos decisiones contradictorias sobre el mismo objeto quedan las dos y la interpretacion del conjunto (una plantilla esta aprobada cuando existen las dos decisiones) es del consumidor del registro.

La correspondencia entre correo verificado y rol sigue siendo tan fuerte como el padron: quien lo mantiene decide quien puede registrar cada decision. Eso ya lo dice el ADR 0005 y este mecanismo no lo empeora ni lo mejora.
