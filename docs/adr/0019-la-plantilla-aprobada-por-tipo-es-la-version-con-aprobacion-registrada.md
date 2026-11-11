---
status: accepted
---

# En producción la plantilla aprobada por tipo es la versión del texto que tiene la aprobación de contenido registrada

El modo producción de los renderers ([issue #142](https://github.com/SpendIce/Proyecto-Final/issues/142)) exige componer cada pieza desde una plantilla aprobada por tipo, sin marcas de borrador. La revisión del PR #160 detectó que cargar el texto desde un archivo declarado por `AGENTE1_PLANTILLAS_APROBADAS_PATH` no alcanza: «aprobada» no puede inferirse de que el texto exista en un archivo, porque el glosario («Plantilla aprobada», «Validación humana») exige que la aprobación quede registrada, y la definición del 11/11/2026 ([#125](https://github.com/SpendIce/Proyecto-Final/issues/125), ADR 0018) fija el circuito que la registra.

## Decisión

El texto de las plantillas por tipo vive fuera del repo, en el archivo que declara `AGENTE1_PLANTILLAS_APROBADAS_PATH`, porque es redacción de la SEU y no código. Pero en producción una plantilla sólo se usa si **la versión exacta de su texto tiene una `apruebo_contenido` `registrada` del rol `APROBADOR_CONTENIDO`** en el registro de decisiones (`decisiones_form`), el mismo circuito que ya aprueba las plantillas de actividad:

- El objeto de la decisión es el id de la versión de la plantilla, `tpl-<tipo>-<hash del texto íntegro>` (`id_version_plantilla`). Deriva del tipo y del hash del asunto más el cuerpo, igual que el `plantilla_id` del circuito de actividad deriva del documento: aprobar ese objeto es aprobar esa redacción exacta.
- Un cambio de texto produce un id distinto, así que la decisión registrada queda atada a la versión aprobada: una edición posterior del archivo no «hereda» la aprobación y el lote se rechaza con `template_version_unapproved` antes de componer nada.
- Sin la plantilla del tipo en el archivo es `approved_template_missing`; con forma inválida (asunto obligatorio vacío, variables que el circuito no completa) es `approved_template_invalid`; sin la decisión registrada es `template_version_unapproved`. Los dos archivos de falla (`approved_templates_file_missing`, `approved_templates_file_invalid`) cubren la carga, no la autorización.

Los tipos del mecanismo son los cinco `por_envio` de HU-012, `recordatorio_pago`, `correo_actividad`, `certificado_asistencia` y `correo_certificado`. `certificado_aprobacion` no entra: su diseño institucional ya llegó como composición reproducible en ADR 0017.

## Considered Options

- **Aceptar el archivo como prueba de aprobación.** Se descartó: el archivo lo edita quien opera el despliegue y no deja rastro de quién avaló el texto; una plantilla «aprobada» por existir viola la exigencia del glosario de que la validación humana queda registrada.
- **Versionar las plantillas en el repo.** Se descartó: el texto es redacción de la SEU, igual que el DOCX del certificado de ADR 0017 vive en custodia, y cambiar una redacción no debería exigir un commit.
- **Un segundo archivo de hashes aprobados junto al de textos.** Se descartó porque duplica el mecanismo que ya existe: el registro de decisiones ya ata decisiones a objetos identificados por hash, con rol, resultado y trazabilidad. Inventar un registro paralelo tendría dos fuentes de verdad para la misma autorización.

## Consequences

- `decisiones_form.py` exporta `decision_registrada`: la consulta exacta por tipo, objeto, decisión `registrada` y rol que todos los circuitos de producción comparten.
- `plantillas_aprobadas.py` concentra la carga del archivo, el id de versión, la validación de forma y el render `{{variable}}` sin llaves sueltas; los circuitos (HU-012, recordatorios, actividad, HU-014) no repiten la mecánica.
- En producción todo texto provisional declarado `PROVISIONAL_NO_INSTITUCIONAL` queda fuera: los renderers no podan marcas de un borrador para entregarlo; sin plantilla aprobada y registrada del tipo no se compone nada.
- El operador del despliegue necesita, para cada tipo en producción: el texto en el archivo de plantillas y el `apruebo_contenido` registrado sobre su versión. Falta cualquiera de los dos y la corrida se rechaza antes de entregar.
- Queda pendiente institucional: la SEU redactar las plantillas por tipo (confirmaciones `por_envio`, `recordatorio_pago`, `correo_actividad`, `certificado_asistencia`, `correo_certificado`) y registrar su aprobación por el circuito del Form de decisiones.
