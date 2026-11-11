# Modo producción del envío Gmail (#141) y de los renderers (#142)

**Estado institucional:** PENDIENTE (lista real y plantillas aprobadas por tipo a cargo de la SEU)  
**Estado técnico:** implementado y probado con transporte fake; sin envío live.

## Qué cambia

`GmailDestinoConfirmaciones` (`src/agente1/gmail_envio.py`) pasa a tener dos
modos sobre el mismo transporte, el mismo endpoint `gmail.send` y los mismos
controles de MIME, adjunto, idempotencia, deadline y tope de respuesta:

- **Prueba** es el default. Se comporta exactamente como antes: lista
  `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`, cuerpo obligado a empezar con
  `BORRADOR — NO ENVIAR`, prefijo `# BORRADOR — NO PUBLICAR`, rechazo
  `recipient_off_test_list` y auditoría `gmail_test_list`.
- **Producción** es un opt-in explícito. Usa la lista
  `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS`, no exige ni antepone marcas de
  borrador, rechaza con `draft_marker_in_production` un cuerpo que todavía las
  traiga, rechaza con `recipient_off_approved_list` un destinatario fuera de
  la lista y audita `gmail_production`.

La auditoría D2 admite el `POST` de `messages.send` con
`gmail_send.test_list_active` o con `gmail_send.production_active`, nunca con
las dos declaraciones a la vez. Cualquier otra ruta de Gmail sigue prohibida.

## Variables de configuración

| Variable | Obligatoria | Uso |
|---|---|---|
| `AGENTE1_GMAIL_MODO` | No | `prueba` (default, también si falta) o `produccion`. Un valor vacío o desconocido falla con `gmail_mode_invalid`. |
| `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` | En modo prueba | Direcciones separadas por coma. |
| `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS` | En modo producción | Direcciones separadas por coma, aprobadas por la SEU. El agente no la genera ni la versiona. |
| `AGENTE1_PLANTILLAS_APROBADAS_PATH` | En modo producción | Path al JSON de plantillas por tipo (`{"<tipo>": {"asunto", "cuerpo"}}` con variables `{{nombre}}`). Lo consume `cargar_plantillas_aprobadas` (#142). Sin la variable o sin archivo legible: `approved_templates_file_missing`; forma o marcas inválidas: `approved_templates_file_invalid`. |

Ninguna de las dos listas ni el archivo de plantillas se versiona ni se
hardcodea. La lista aprobada y las plantillas por tipo las define la SEU;
ni #141 ni #142 las inventan.

**Que el archivo declare la plantilla no alcanza.** Por la definición del
11/11 (#125, ADR 0019), «aprobada» es un hecho del registro, no del
archivo: en producción una plantilla sólo se usa si su **versión exacta**
tiene una `apruebo_contenido` `registrada` de `APROBADOR_CONTENIDO` en el
registro de decisiones, sobre el objeto `tpl-<tipo>-<hash del texto>`
(`id_version_plantilla`). Sin esa decisión, o con un texto editado después
de aprobado —el hash ya no coincide—, la corrida se rechaza con
`template_version_unapproved` y nada se entrega. Es el mismo circuito que
las plantillas de actividad: el texto vive fuera del repo porque es
redacción de la SEU, y la autorización queda registrada como cualquier
otra validación humana.

## Renderers en modo producción (#142)

#142 cierra el hueco que #141 dejó declarado: los renderers ya no componen
siempre con marcas. El mecanismo vive en
`src/agente1/plantillas_aprobadas.py` y cada circuito lo toma del modo que
corresponda:

El modo tiene una sola fuente en todos los circuitos: **`destino.modo`**.
Un parámetro `modo_envio` sobrevive sólo para componer sin entregar y,
cuando hay destino, tiene que coincidir con él — de lo contrario el
pedido es `send_mode_mismatch` y falla cerrado. El Protocol de destinos
declara `modo`, así que ningún circuito adivina el modo con `getattr`.

- **HU-012 por envío** (`procesar_confirmacion`): en `produccion` el
  cuerpo y el asunto salen de la plantilla aprobada del tipo, inyectada
  en `plantillas_aprobadas`, con su `apruebo_contenido` registrada en
  `decisiones`; sin ella es `approved_template_missing`, con forma que no
  cierra es `approved_template_invalid`, sin la decisión sobre la versión
  exacta es `template_version_unapproved`. `instrucciones_pago` conserva
  su asunto del plan. Un borrador registrado en prueba no sirve para una
  entrega de producción: sale `INVALIDA` con `template_body_mismatch` en
  vez de reescribir en silencio lo que se aprobó.
- **HU-012 por lote** (`recordatorio_pago` y correo de actividad): en
  `produccion` cada ítem se compone desde la plantilla aprobada del tipo
  (`recordatorio_pago`, `correo_actividad`) con la misma exigencia de
  versión registrada. El texto provisional declarado
  `PROVISIONAL_NO_INSTITUCIONAL` nunca viaja sin marca: producción no lo
  poda, lo reemplaza. El lote sigue exigiendo sus autorizaciones propias
  (`APROBADOR_PAGOS` en recordatorios; `apruebo_contenido` del documento
  y `apruebo_lote` en actividad). Un modo desconocido es
  `send_mode_invalid` antes de tocar el registro.
- **HU-014** (`procesar_emision_certificados`): en producción el
  certificado de `aprobacion` sale del diseño SEU ya recibido (#126) sin
  la línea «DOCUMENTO DE PRUEBA» — el flag `marcar_prueba` de
  `generar_pdf_certificado_seu` se apaga sólo ahí —, el de `asistencia`
  se compone desde `certificado_asistencia` y el correo del titular desde
  `correo_certificado`, ambas con la `apruebo_contenido` registrada de su
  versión. Además la custodia tiene que resolver el símbolo y todas las
  firmas del diseño SEU: un recurso faltante es `INVALIDA` con
  `signature_resources_missing` antes de entregar al primer titular —
  ningún PDF sale sin marca y sin firmas. El aviso al aprobador sale sin
  la marca de correo y la muestra adjunta conserva su marca de borrador,
  porque es una muestra. La auditoría declara `plantilla` —la versión
  efectivamente usada, `id_version_plantilla` para `asistencia` en
  producción— y `delivery_mode` igual que en HU-012.
- **Aviso operativo del canal** (`canal_form`): no es una pieza
  institucional; en producción el mismo texto viaja sin la marca, porque
  el destino la rechaza. En prueba conserva la marca de siempre. El aviso
  de respaldo (`GmailAvisoOperador`) quedó fuera del alcance del ticket:
  su marca no cambió.

En todos los casos el default sigue siendo `prueba` y el adapter de
producción queda como última línea: cualquier cuerpo marcado se rechaza con
`draft_marker_in_production` antes de la red.

## Procedimiento de habilitación

1. La SEU aprueba la lista de destinatarios y la plantilla del tipo de
   comunicación que se va a enviar. La aprobación de cada plantilla se
   registra por el circuito existente: una decisión `apruebo_contenido`
   de `APROBADOR_CONTENIDO` en el Form de decisiones sobre el objeto
   `tpl-<tipo>-<hash del texto>` que expone `id_version_plantilla`.
2. Informática escribe la lista aprobada en
   `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS` y las plantillas en el JSON que
   apunta `AGENTE1_PLANTILLAS_APROBADAS_PATH`, en el mismo env file fuera
   del repo que el resto de la configuración. Si el texto cambia, la
   versión nueva necesita una aprobación nueva: la decisión registrada
   queda atada al hash que se aprobó.
3. Se define `AGENTE1_GMAIL_MODO=produccion`. Sin la lista, con la lista vacía
   o con una dirección inválida, `desde_entorno` no construye el destino:
   `gmail_production_list_missing` o `gmail_production_list_invalid`.
4. El cuerpo que se entregue tiene que venir de la plantilla aprobada y sin
   marcas de borrador. Si un pipeline todavía agrega `BORRADOR — NO ENVIAR` o
   `# BORRADOR — NO PUBLICAR`, la entrega se rechaza antes de la red y el
   registro queda `FALLIDA`.
5. Para volver al modo prueba, se quita `AGENTE1_GMAIL_MODO` o se la deja en
   `prueba`. No hace falta tocar código.

## Qué falta para operar en producción

- **Las plantillas institucionales aprobadas.** El mecanismo ya existe
  (#142, ADR 0019) pero las redacciones siguen pendientes. Por la
  definición del 11/11 (#125), cada plantilla la aprueba quien genera la
  pieza: la SEU para las piezas que emite, con la `apruebo_contenido`
  registrada sobre la versión exacta del texto. Quedan pendientes:
  - Los cinco tipos `por_envio` de HU-012 (`inscripcion`, `participacion`,
    `situacion_pagos`, `aprobacion` e `instrucciones_pago`): cuerpo y asunto.
  - La plantilla `correo_actividad` y la de `recordatorio_pago`: el texto
    generado por el circuito sigue siendo la redacción provisional
    `PROVISIONAL_NO_INSTITUCIONAL`, y en producción no viaja ni podada ni
    entera; falta la versión institucional definitiva (`PENDIENTE_SEU`)
    con su aprobación registrada.
  - HU-014: `certificado_asistencia` y `correo_certificado`. El diseño
    del certificado de `aprobacion` ya llegó como plantilla SEU (#126)
    y la emisión de producción lo compone sin marca de prueba; faltan
    `certificado_asistencia` —la variante institucional o la adaptación
    avalada— y la redacción del correo que lleva el PDF, más los
    activos de firma que el despliegue exija (`AGENTE1_CERTIFICADOS_
    RECURSOS_DIR`, custodia fuera del repo): sin ellos, producción
    rechaza la emisión con `signature_resources_missing`.
  - El aviso del canal de pedidos es un mensaje operativo: viaja sin
    marca en producción y no exige plantilla institucional, pero si la
    SEU quisiera fijar su redacción, el mecanismo la admitiría como
    plantilla aprobada. El aviso de respaldo no entró al alcance del
    ticket y conserva su marca en ambos modos.
- **La lista real.** El ticket deja el mecanismo y la validación; las
  direcciones las aprueba la SEU.
- **La prueba live.** No se envió correo real. La verificación es con
  transporte y token fake, sin red.

## Cómo se verifica

```bash
cd Implementacion/Agente1
uv run pytest -q tests/test_gmail_envio.py tests/test_auditoria_seguridad_d2.py
uv run pytest -q
uv run ruff check .
```

Las pruebas cubren, con transporte fake: default intacto, producción sin
lista, lista inválida, destinatario fuera de la lista antes de la red, cuerpo
sin marcas en producción, cuerpo marcado rechazado, marcas obligatorias en
prueba, adjunto válido e inválido, errores HTTP y timeout con el mismo código
que en prueba, y el `delivery_mode` de la auditoría en las dos vías.
