# Identidad afirmada por el canal, no verificada

El caso de uso de interaccion interna exige rechazar y registrar el intento cuando quien pide no tiene permisos, y el backlog institucional pide ingreso con credenciales y permisos segun rol. Pero la identidad institucional depende de OAuth y de recursos de infraestructura que son un **bloqueante externo** abierto: no hay forma de verificar a nadie hoy.

Decidimos que el **canal de interaccion** afirme quien pide y con que rol, y que el nucleo **exija** ese dato, lo registre y lo use para decidir, **sin verificarlo**. El campo esta presente y es obligatorio desde el primer dia; lo que falta es la prueba de que sea cierto.

Esto permite implementar y probar hoy el rechazo por rol insuficiente, y el dia que exista identidad institucional el adapter llena el mismo campo con algo verificado, sin tocar el nucleo.

## Considered Options

Se evaluo no modelar identidad hasta tener OAuth, y se descarto porque deja sin implementar ni probar un flujo alternativo que el caso de uso exige, y porque agregarla despues obligaria a reabrir el nucleo.

Se evaluo un padron local que mapee identidad a rol tratado como fuente de verdad, y se descarto porque es la misma afirmacion no verificada disfrazada de verificacion real. La bible advierte exactamente contra esa confusion: recibir un pedido en un buzon no otorga los permisos de ese buzon, y conviene no solapar la capa del canal con la del backend.

## Consequences

Un lector del codigo va a encontrar un campo de identidad que nadie valida criptograficamente y puede tomarlo por un defecto. No lo es: es deliberado, y la unica correccion valida es reemplazar el adapter por uno que verifique, nunca agregar una verificacion falsa en el nucleo.

Ninguna evidencia producida en este estado acredita control de acceso. La autorizacion es modelada y trazable, no probada.
