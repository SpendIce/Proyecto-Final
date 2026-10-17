---
status: accepted
---

# La gacetilla declara su tipo, su modo y su forma

**Amplía la [ADR 0001](0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md) sin reemplazarla.** Todo lo que la 0001 decide sobre la solicitud en lenguaje natural sigue vigente: el catálogo es cerrado, la entrada no es confiable y una solicitud que no corresponde a una intención del catálogo se rechaza sin aproximarse a la más parecida.

El Agente 1 prepara **gacetillas** para el canal FIE Informa. Hasta ahora el catálogo tenía **una** intención para eso (`generar_gacetilla`) y el renderer producía **una sola forma de pieza**: arrancaba con la frase fija *«La Facultad de Ingeniería del Ejército invita a {público} a participar de la siguiente actividad»*, agregada siempre que la fila tuviera `público`. El corpus de la SEU muestra que el canal lleva **siete clases de pieza** —difusión de actividad, crónica, aviso de otra área, convocatoria interna, saludo o efeméride, fallecimiento y newsletter— y que cada una tiene su propio esqueleto, su propio firmante y su propia lógica. El contrato de entrada también era de forma *actividad*: exigía `modalidad`, `duracion_horas` y `enlace_inscripcion`, que un aviso no tiene, y no tenía dónde poner el día, la hora y el lugar de un responso.

Consecuencia verificada el 2026-10-16: el mismo pipeline aplicado a otra clase de pieza produce una pieza falsa. Un aviso de estacionamiento sale como invitación a participar, firmado por un área que no lo emitió; una crónica de un hecho ya ocurrido sale como invitación a algo que todavía no pasó, o sea al revés de la verdad.

Decidimos que **la pieza declara su tipo, y el tipo declara su modo y su forma**. En concreto:

1. **El catálogo sigue cerrado y ahora declara tipos.** El tipo de gacetilla es un conjunto cerrado que viaja declarado en la solicitud, nunca deducido y presentado como hecho. Las intenciones `generar_newsletter` y `generar_mail` dejan de ser intenciones: un newsletter es un **tipo** de gacetilla, y un mail es el canal, no una pieza distinta. Queda una sola intención para la gacetilla, con el tipo como parámetro cerrado.
2. **El modelo nunca escribe hechos institucionales.** El firmante, el pie, las etiquetas y las fórmulas fijas de cada tipo se declaran en una **forma declarada** versionada por tipo, y el agente la copia. El modelo aporta la prosa del cuerpo **sólo en los tipos cuyo modo es «genera»**; en los tipos cuyo modo es «extrae y confirma», los datos los carga quien pide y el agente sólo los formatea. Ningún tipo presenta como propio un hecho que no venga de una fuente declarada.
3. **Ningún tipo se presenta como habilitado sin su forma y su pipeline.** Un tipo sin forma declarada y sin pipeline construido se declara como tal y no se ejecuta, igual que el estado `NO_APLICADA_PENDIENTE_PIPELINE` de las intenciones.

El tipo es, entonces, el eje: selecciona la forma declarada, el firmante, el contrato de entrada, las reglas de gate propias del tipo y el modo de producción. Cuáles de los siete tipos entran al PPS lo decide el issue [#106](https://github.com/SpendIce/Proyecto-Final/issues/106); esta ADR decide el mecanismo, no la lista.

## Considered Options

- **Una intención por tipo de gacetilla.** Se descartó porque infla el catálogo con cosas que no son intenciones distintas: pedir «una gacetilla» es una sola intención, no siete. Además obligaría a que la clasificación determinística adivine el tipo antes de que exista, que es exactamente la aproximación que la 0001 prohíbe.
- **Un tipo libre, inferido de la prosa.** Se descartó por la misma razón: si el tipo selecciona forma, firmante y gate, no puede ser texto libre. El tipo se declara o se confirma, nunca se asume.
- **Mantener el marco en el código y parametrizarlo por tipo.** Se descartó porque cada tipo nuevo obligaría a tocar el mismo archivo del renderer, y el marco dejaría de estar bajo el control de cambios y bajo la verificación de integridad del arranque (ADR 0010), que sí alcanzan a los contratos.
- **Dejar que el modelo escriba también el marco.** Se descartó porque el firmante y las fórmulas institucionales son hechos, y el modelo no es fuente de hechos. Es el bug que esta decisión corrige.
- **Un contrato de entrada único con todos los campos opcionales.** Se descartó porque nadie sabría qué es obligatorio para cada tipo, y el renderer terminaría inventando para llenar los huecos. Es exactamente lo que pasó con el contrato de forma actividad.
- **Un gate por tipo, duplicado.** Se descartó porque los invariantes de la casa (marca de borrador, largo, registro, sin proceso interno, sin hechos inventados) son comunes, y duplicarlos garantiza que se desincronicen.

## Consequences

- El tipo de gacetilla entra al contrato de intenciones y al contrato de entrada. Es un cambio **Mayor** de la versión del agente: sube `X` y hay que revisar todo lo que consume el catálogo.
- Cada tipo tiene **su archivo** de forma declarada, con su `schema_version`. Dar de alta un tipo es agregar un archivo, no editar uno compartido, y cada tipo queda con su propia huella en el manifest de versión.
- El **canal** gana un campo de tipo y la actividad pasa a ser un **campo condicional**: sólo se pregunta si el tipo es de una actividad. El último ítem de la lista de actividades es «no es una actividad», que no da de alta nada: sólo lleva a los tipos que no necesitan actividad. El agente sigue sin crear ni registrar actividades.
- La frase fija de invitación **sale** del renderer. La introducción de la pieza la aporta la prosa del modelo en los tipos que generan, y en los que extraen y confirman no hay introducción que generar.
- El **área emisora** sale de una lista cerrada versionada, como el padrón de roles del ADR 0005, porque determina el firmante.
- La pieza declara en su bloque de procedencia cuándo sus hechos vienen de la solicitud y no de la fuente institucional de actividades, para que quien valida lo vea y no sólo quede en la auditoría.
- Los anexos de laboratorio que citan la salida del renderer **se regeneran**: la salida cambia y lo declarado tiene que coincidir con lo que corre.
- La ruta dic–feb hereda el alta de los tipos que la SEU priorice, cada uno con su forma, su prompt si genera, su gate y sus regresiones.
