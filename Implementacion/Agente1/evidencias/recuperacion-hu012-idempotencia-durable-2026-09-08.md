# Recuperación idempotente de HU-012 — corte 2026-09-08

- **Issue:** `SpendIce/Proyecto-Final#9`
- **Alcance:** recorte offline de HU-012. No incorpora capacidad de envío real.
- **Entorno:** local controlado, datos sintéticos, sin red.

## 1. Qué faltaba

El ciclo de vida de HU-012 ya separaba generación, aprobación, reserva y
entrega, y el registro en memoria impedía entregar dos veces dentro de una
misma corrida. Lo que no cubría es el caso que importa: el proceso muere entre
reservar el envío y saber el resultado. Al reiniciar no quedaba rastro, y un
reintento volvía a entregar.

## 2. Registro durable

`RegistroConfirmacionesArchivo` guarda el estado en disco, un archivo por clave
de idempotencia.

`crear` escribe el contenido en un temporal y lo publica con `os.link`. `link`
falla si el destino existe, lo que da la semántica de «crear una vez» entre
procesos, y publica el registro ya completo.

**Hallazgo durante la implementación:** la primera versión usaba `O_EXCL`
directo sobre el archivo final. Eso alcanza para la exclusión pero deja el
archivo visible y vacío entre la creación y la escritura. La prueba de
creaciones concurrentes lo detectó: el proceso que perdía la carrera leía el
archivo justo en esa ventana, encontraba un registro ilegible y el pipeline
abortaba con `registro de idempotencia inconsistente`. Con `os.link` la ventana
no existe. La prueba fallaba de forma intermitente —cinco de doce corridas—, que
es exactamente el perfil de una carrera y la razón para repetirla en vez de
darla por buena la primera vez.

`transicionar` toma `flock` sobre un `.lock` por clave y no sobre el `.json`:
el registro se escribe con `os.replace`, así que un lock tomado sobre el `.json`
quedaría sobre el inodo viejo y dejaría entrar a un segundo proceso.

Un registro ilegible se trata como ausente, no como vacío. Devolver un registro
con campos por defecto convertiría un archivo corrupto en un estado válido, y
desde ahí se podría transicionar a entrega.

El directorio queda `0700` y los archivos `0600`: el registro guarda el texto
del borrador. La línea de auditoría sigue llevando sólo hashes, sin
destinatario, sin cuerpo y sin nombre.

## 3. Reconciliación

`reconciliar_envios_reservados` cierra las reservas colgadas **sin volver a
entregar**.

Una reserva interrumpida es indeterminada por definición: nadie puede afirmar
si la entrega ocurrió. Reintentar sería apostar a que no, y el costo de
equivocarse es una confirmación duplicada a una persona real. La reconciliación
mueve el registro a `ENVIO_INDETERMINADO`, un estado desde el cual el pipeline
no transiciona, para que una persona decida con el registro a la vista.

## 4. Cobertura

`tests/test_confirmaciones_durables.py`, 18 pruebas:

| Caso | Qué verifica |
|---|---|
| Estados observables | Generación, aprobación y entrega producen estados distintos |
| Idempotencia tras reinicio | Un registro nuevo sobre el mismo directorio no vuelve a entregar |
| Rechazo persistente | Una confirmación rechazada no se puede aprobar después del reinicio |
| Permisos | Directorio `0700`, archivos `0600` |
| Clave inválida | Una clave que no es un sha256 no elige dónde se escribe |
| Registro corrupto | Se trata como ausente y no habilita transición a entrega |
| Reserva interrumpida | Se reconcilia a `ENVIO_INDETERMINADO` sin entregar |
| Post-reconciliación | El pipeline no vuelve a entregar desde ese estado |
| Estados terminales | La reconciliación no toca lo ya entregado ni lo fallido |
| Concurrencia de entrega | Ocho intentos simultáneos producen una sola entrega |
| Concurrencia de creación | Ocho intentos simultáneos crean un solo borrador |
| Destinatario inválido | No deja rastro en el registro |
| Datos incompletos | No dejan rastro en el registro |
| Auditoría | Sin destinatario, sin nombre y sin cuerpo |
| Adapter productivo | Ni una subclase del fake habilita entrega |

Las dos pruebas de concurrencia se repitieron 20 veces sin fallas después de la
corrección, y la suite completa quedó en **588 pruebas verdes** con
`uv run pytest -q`.

## 5. Lo que este incremento no hace

No existe adapter de correo productivo: la única entrega posible sigue siendo
contra `DestinoConfirmacionesFake`, verificado por tipo exacto. Ningún origen de
inscripción habilita envío, porque ninguno está confirmado por la SEU
(`DEF-A1-015`). No hay validación institucional, plantilla aprobada ni evidencia
de TRL: el incremento es técnico y offline.
