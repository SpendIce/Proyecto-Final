---
status: accepted
---

# Área emisora y firma de área separadas; público como catálogo de grupos que no cambia el texto

**Amplía la [ADR 0012](0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md) sin reemplazarla.** Todo lo que la 0012 decide sobre tipo, modo y forma sigue vigente; esta ADR decide quién firma el pie y a quién se envía la pieza, dos hechos del pedido que la 0012 no modelaba.

La SEU y el autor del PPS definieron el 11/11/2026 tres cosas sobre el pedido de un FIE Informa ([issue #154](https://github.com/SpendIce/Proyecto-Final/issues/154)):

1. Existe un **área FIE** en el padrón de áreas emisoras para las comunicaciones generales que no son de un área en particular (un fallecimiento, el estacionamiento). Su firma de pie es exactamente *«Facultad de Ingeniería del Ejército»*.
2. El pedido elige **el área** y, **por separado**, **si la pieza lleva firma de área**. Las salidas académicas, por ejemplo, las emite la Secretaría Académica pero la pieza va sin firma de área. El bloque institucional fijo de la FIE (`firmante` en las formas) va siempre, con o sin firma de área.
3. Quien pide elige **uno o más públicos destinatarios de un catálogo cerrado y versionado**. Un público es un **grupo de correo de Workspace** (un tipo de cuenta), no una lista de personas. El público **sólo decide a quién se envía**: queda declarado en la solicitud y visible en la revisión, pero nunca entra a un prompt ni cambia el texto generado.

Decidimos modelarlos como tres contratos independientes:

1. **Área y firma son dos campos del pedido.** El área sigue saliendo del padrón cerrado (`areas_emisoras`, ahora en `v2` con el área `fie`); la firma de área es una opción booleana separada con default *sí*, que conserva el comportamiento de siempre en las formas que imprimen el área. Con la firma desactivada la forma omite el área del pie y conserva el bloque `firmante` institucional.
2. **Los públicos son un padrón cerrado versionado, como las áreas.** `publicos_destinatarios_v1` lleva sólo `id` y `nombre` y arranca con el único público confirmado (`alumnos_ingenieria`). Sumar un público es agregar una entrada en una versión nueva del catálogo. **Las direcciones de los grupos no se versionan**: el repo es público, así que la correspondencia id → dirección del grupo queda fuera, igual que el padrón de roles del ADR 0005.
3. **El público es del pedido, no de la pieza.** Lo valida el canal contra el catálogo, queda declarado en la estructura de la solicitud y en el registro, y se muestra en el aviso de revisión. Una barrera explícita (`CAMPOS_DEL_PEDIDO_NO_DE_LA_PIEZA`) lo excluye de cualquier prompt: decidir el destinatario no es un hecho del texto.

## Considered Options

- **Firma de área como un área más del padrón** («sin firma» como pseudo-área). Se descartó porque confunde dos decisiones: el aviso sí lo emite la Secretaría Académica aunque la pieza no la firme. El área se confirma en el pedido igual.
- **Heredar el público del campo de texto libre** (`publico`, `destinatarios`) que algunas entradas usaban para redactar («a la comunidad educativa»). Se descartó porque una frase de la pieza no es un destinatario de envío: el que el texto diga «comunidad» no elige ningún grupo. La frase queda donde estaba, como dato del pedido; el público de envío es un campo nuevo y cerrado.
- **Versionar las direcciones de los grupos en el catálogo.** Se descartó porque el repo es público y una dirección de grupo de Workspace no es un dato que convenga publicar; el catálogo declara la opción, no el destinatario técnico.
- **Pasar el público al prompt para «orientar el tono».** Se descartó por la definición misma: el público no cambia el texto. Si entrara al prompt podría cambiarlo —un modelo recibe lo que recibe— y además sería un hecho del pedido disfrazado de dato de la pieza.
- **Reusar el padrón de áreas para los públicos.** Se descartó porque son dominios distintos con cambios independientes: un área nueva no crea un grupo de destinatarios y un público nuevo no emite comunicaciones.

## Consequences

- `areas_emisoras` queda en `v2` con el área `fie`; la `v1` queda versionada para trazabilidad y el código usa la `v2`.
- Las formas de `aviso_de_otra_area`, `convocatoria_interna` y `newsletter` ganan `pie_condicion` en su versión `v2`; el renderer sube a `gacetilla_forma_declarada_v5`. La difusión de actividad conserva su forma `v1`: su pie es la firma institucional fija de siempre, no un área del pedido, así que la opción no le aplica.
- El contrato de la hoja de respuestas sube a `canal_form_respuestas_v3` con las columnas `firma_de_area` y `publicos`; las filas de las versiones anteriores se leen igual, sin esas columnas.
- El público aparece en la estructura del pedido, en el registro de atendidos y en el aviso de revisión (con el nombre del catálogo), y en ningún otro lado. Los tests lo prueban sobre el prompt real del pipeline.
- Cambio de contratos versionados, sin corte de versión del agente: la SEU no revisó todavía el Form y la interfaz v3 sigue provisional.
