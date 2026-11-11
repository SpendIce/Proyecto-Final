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
- El lifecycle por pieza pierde los estados parciales: `PENDIENTE_VALIDACION → APROBADA | RECHAZADA` con una sola decisión; una decisión de un rol ajeno queda `INVALIDA` y no habilita nada, y una decisión repetida es `DUPLICADA`.
- La aprobación del lote de certificados exige dos cosas a la vez: el rol `APROBADOR_CONTENIDO` y que el correo de la decisión sea el de quien generó el lote (el solicitante). Un `apruebo_lote` de otro correo se descalifica como `aprobador_no_es_generador` y el de otro rol como `aprobador_rol_no_autorizado`; ninguno habilita la emisión.
- Se conserva intacto el resto del circuito: trazabilidad de actor (correo hasheado + rol) en el registro durable, atado a la versión/hash exacta del objeto, invalidación por cambio de contenido, rechazo, marca de prueba y destinos cercados. Nadie sin autorización habilita una acción.

## Considered Options

- **Conservar el par semántica + utilitaria y agregar el rol de pagos.** Se descartó porque contradice la definición vigente: la aprobación es una sola decisión de la persona autorizada, no un par de roles.
- **Inventar un «aprobador final de certificados» distinto del cargador.** Se descartó: la definición elimina explícitamente esa figura y prohíbe inventar identidades para cumplir un circuito.
- **Que el lote de certificados lo apruebe cualquier correo con el rol.** Se descartó: «lo aprueba quien lo genera» ata la decisión al correo del solicitante, igual que un gestor firma lo que arma; además conserva la separación de un actor externo aprobando el lote que cargó otro, pero como una sola persona.

## Consequences

- El Form de decisiones concentra el contenido en un solo rol: `publicacion` (`publique`/`descarte`), `plantilla` y `linea_descriptiva` (`apruebo_contenido`) y `lote` (`apruebo_lote`). Los lotes de pagos no pasan por ese catálogo: viajan como `AprobacionHumana` del circuito de `recordatorios.py` con rol `APROBADOR_PAGOS`.
- Los nombres de rol son provisionales y el mapeo a las personas (Juan Manuel, Josefina, Leandro) vive sólo en el padrón institucional que mantiene la SEU; el repositorio versiona únicamente el padrón sintético.
- El ADR 0005 sigue vigente en su mecanismo (identidad verificada por el Form + rol por padrón); el conjunto de roles del acta del 22/09 que menciona queda reemplazado por esta designación.
- El ADR 0008 sigue vigente en su mecanismo (objetos pendientes y links por decisión); la asignación de roles y decisiones del catálogo que fijaba queda reemplazada. El ADR 0003 conserva su decisión de fondo (estado de pago derivado), pero el control que llama «aprobación utilitaria del lote de recordatorios» pasa a ser la aprobación del lote de pagos por su responsable.
- Queda pendiente institucional: la SEU confirmar el padrón real, los correos de las personas autorizadas y cualquier delegación adicional.
