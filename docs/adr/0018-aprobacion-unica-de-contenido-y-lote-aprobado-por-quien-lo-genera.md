---
status: accepted (roles provisionales; el padron institucional queda pendiente de la SEU)
---

# Una sola persona autorizada aprueba el contenido; el lote de certificados lo aprueba quien lo genera; los lotes de pagos los aprueba Leandro

Por la designación vigente (Juani, 11/11/2026, [issue #125](https://github.com/SpendIce/Proyecto-Final/issues/125)):

- Una pieza de contenido la aprueba **una sola persona autorizada** —Juan Manuel o Josefina, por delegación de la Secretaría—; no se exige un segundo actor ni dos decisiones (semántica + utilitaria) de personas distintas.
- El **lote de certificados lo aprueba quien lo genera**, igual que el resto de las piezas. Se elimina el pendiente de «aprobador final de certificados». El gate se mantiene: sin esa aprobación registrada no hay emisión.
- Leandro aprueba los **lotes de pagos** (HU-012).

Esta decisión reemplaza al circuito de doble aprobación que el CU10 del bible y el diseño de HU-012 habían fijado (semántica del Responsable de Gestión del Conocimiento + utilitaria del Coordinador de Extensión, en cualquier orden) y a la regla histórica que impedía a quien cargaba la lista de cierre aprobar el lote que generaba.

## Decisión

- El padrón lleva un rol autorizado de contenido (`APROBADOR_CONTENIDO`) con la decisión `apruebo_contenido`, y un rol de pagos (`APROBADOR_PAGOS`) para los lotes de HU-012. Los roles `RESPONSABLE_GESTION_CONOCIMIENTO`/`COORDINADOR_EXTENSION` y las decisiones `apruebo_semantica`/`apruebo_utilitaria` salen del circuito vigente.
- Pedir o generar el lote de certificados exige el rol `APROBADOR_CONTENIDO`: un rol operativo que lo intente recibe un rechazo explícito, no un lote que nadie puede aprobar. Por eso `APROBADOR_CONTENIDO` también queda habilitado para pedir piezas en el contrato de intenciones, lo que rompe el invariante «un rol operativo que pide piezas no puede decidir sobre ellas» de forma deliberada y documentada: pedir/generar el lote es el acto que después habilita su propia aprobación.
- El lifecycle por pieza pierde los estados parciales: `PENDIENTE_VALIDACION → APROBADA | RECHAZADA` con una sola decisión; una decisión de un rol ajeno queda `INVALIDA` y no habilita nada, y una decisión repetida es `DUPLICADA`.
- La aprobación del lote de certificados exige dos cosas a la vez: el rol `APROBADOR_CONTENIDO` y que el correo de la decisión sea el de quien generó el lote (el solicitante). Un `apruebo_lote` de otro correo se descalifica como `aprobador_no_es_generador` y el de otro rol como `aprobador_rol_no_autorizado`; ninguno habilita la emisión. La misma verificación es la única que corre en las dos vías (`certificados_emision` por lote y `certificados` por documento).
- Compatibilidad con lo heredado: un registro durable en `APROBADA_SEMANTICA`/`APROBADA_UTILITARIA` se lee como `PENDIENTE_VALIDACION` (acepta `apruebo_contenido` y deja diagnóstico en el log); las decisiones `apruebo_semantica`/`apruebo_utilitaria` y los roles reemplazados que lleguen por el Form se rechazan con código `rol_reemplazado`, no se ignoran; un padrón con roles que ya no existen frena el arranque con `padron_rol_desconocido`.
- Se conserva intacto el resto del circuito: trazabilidad de actor (correo hasheado + rol) en el registro durable, atado a la versión/hash exacta del objeto, invalidación por cambio de contenido, rechazo, marca de prueba y destinos cercados. Nadie sin autorización habilita una acción.

## Considered Options

- **Conservar el par semántica + utilitaria y agregar el rol de pagos.** Se descartó porque contradice la definición vigente: la aprobación es una sola decisión de la persona autorizada, no un par de roles.
- **Inventar un «aprobador final de certificados» distinto del cargador.** Se descartó: la definición elimina explícitamente esa figura y prohíbe inventar identidades para cumplir un circuito.
- **Que el lote de certificados lo apruebe cualquier correo con el rol.** Se descartó: «lo aprueba quien lo genera» ata la decisión al correo del solicitante, igual que un gestor firma lo que arma; dejarlo abierto a cualquier correo del rol autorizado permitiría que otro apruebe un lote que no generó, justo lo que la definición elimina.

## Consequences

- El Form de decisiones concentra el contenido en un solo rol: `publicacion` (`publique`/`descarte`), `plantilla` y `linea_descriptiva` (`apruebo_contenido`) y `lote` (`apruebo_lote`). Los lotes de pagos no pasan por ese catálogo: viajan como `AprobacionHumana` del circuito de `recordatorios.py` con rol `APROBADOR_PAGOS`.
- El contrato de intenciones v5 habilita a `APROBADOR_CONTENIDO` para pedir piezas (genera los lotes de certificados que después aprueba) y no a `APROBADOR_PAGOS`, que no pide piezas: sólo decide sobre su circuito de recordatorios.
- Los nombres de rol son provisionales y el mapeo a las personas (Juan Manuel, Josefina, Leandro) vive sólo en el padrón institucional que mantiene la SEU; el repositorio versiona únicamente el padrón sintético.
- El ADR 0005 sigue vigente en su mecanismo (identidad verificada por el Form + rol por padrón); el conjunto de roles del acta del 22/09 que menciona queda reemplazado por esta designación.
- El ADR 0008 sigue vigente en su mecanismo (objetos pendientes y links por decisión); la asignación de roles y decisiones del catálogo que fijaba queda reemplazada. El ADR 0003 conserva su decisión de fondo (estado de pago derivado), pero el control que llama «aprobación utilitaria del lote de recordatorios» pasa a ser la aprobación del lote de pagos por su responsable.
- El ADR 0017 queda modificado en su premisa de aprobación: donde afirmaba que el lote de certificados reutiliza «las mismas dos aprobaciones de la línea descriptiva», ahora vale una sola aprobación de contenido para la línea y una `apruebo_lote` de quien generó el lote.
- Queda pendiente institucional: la SEU confirmar el padrón real, los correos de las personas autorizadas y cualquier delegación adicional.
