---
status: accepted
confirmed_by: Juan Ignacio Goñe
confirmed_on: 2026-11-16
---

# Aprobar ofrece el correo prellenado en Gmail, sin enviar

El recorrido del canal web (#153) termina con la pieza aprobada en su
Doc, pero el paso siguiente —llevarla a los públicos del pedido— quedaba
afuera del sistema y a mano. El 16/11/2026 Juani definió el cierre: al
aprobar, el sistema ofrece **abrir Gmail en modo redactar con los
destinatarios en Cco, el asunto y el cuerpo ya cargados desde la
revisión aprobada**, y la persona revisa y envía ella.

Decidimos que **aprobar prepara el correo en el cliente de la persona,
sin que el agente envíe nada**: no hay `gmail.send`, no hay borradores
por API, no se pide el scope `gmail.compose`. La aprobación sigue sin
publicar ni enviar —modifica la Q6 de #153 sólo en el sentido— y el
envío real queda, como toda decisión de difusión, en manos de una
persona.

## Cómo funciona

- **Los públicos del pedido son las audiencias.** El pedido elige públicos
  del catálogo cerrado, que pasa a `publicos_destinatarios_v2` con los 18
  grupos del listado institucional (la v1 queda versionada para
  trazabilidad). El contrato lleva id y nombre, nunca direcciones: la
  correspondencia id → dirección y los `usos_candidatos` por audiencia
  viven **fuera del repo**, en el catálogo `AGENTE1_AUDIENCIAS_PATH`
  (misma doctrina que el padrón de roles y ADR 0015). Las 18 audiencias
  nacen `PENDIENTE_SEU` y la interfaz lo marca: el correo las lleva
  igual, porque el envío lo decide la persona, no el agente.
- **El arranque es fail-closed.** Con el catálogo declarado, `crear_app`
  exige que todo id del contrato v2 tenga dirección en él; un id sin
  mapeo cierra el arranque nombrando el id, nunca la dirección. Sin la
  variable, el prellenado queda apagado y `/correo` muestra el motivo.
- **Aprobar abre la pestaña del correo.** El click de «Aprobar» dispara
  un `window.open` hacia `/solicitudes/{id}/correo` en el mismo gesto,
  antes de que viaje el POST, así que el bloqueador de ventanas no lo
  frena. La pestaña espera la decisión (releé el estado hasta que la
  solicitud cierra) y, con la aprobación asentada, la misma ruta
  redirige a Gmail; si la decisión no quedó aprobada, muestra el motivo
  en vez de redirigir. Si el popup se pierde, la página aprobada ofrece
  «Abrir en Gmail» de todos modos: el botón es el camino robusto y la
  apertura automática, la cortesía.
- **La cuenta la elige la persona.** La ruta desnuda envuelve el compose
  en `accounts.google.com/AccountChooser?continue=<url>`; el parámetro
  no tiene documentación oficial, así que el bloque ofrece además
  «Abrir con la cuenta \<correo de la sesión\>» con `authuser=<correo>`,
  que sí es un parámetro estable de Gmail.
- **El cuerpo es el de la revisión aprobada.** Su texto y su hash, no un
  re-render: si la URL supera `MAX_URL_COMPOSE` (7000, margen empírico
  que incluye el recodificado de `continue`), el cuerpo no viaja en la
  URL y el bloque ofrece «Copiar cuerpo» por Clipboard API con el aviso
  «pegá el cuerpo en el correo». Si la prosa ya se purgó, `/correo`
  muestra el motivo en vez de inventar un cuerpo.
- **Los destinatarios van siempre en `bcc`** (Cco): un reply-all a una
  lista institucional no debe salir de este flujo, y la URL nunca lleva
  `to`.
- **La ruta tiene la misma puerta que la decisión**: sesión viva y rol
  aprobador — quien no puede aprobar no ve el bloque ni obtiene el
  redirect. Las direcciones sólo viajan dentro de la URL de Gmail del
  aprobador: nunca en el HTML, en logs ni en la base.

## Trazabilidad

La auditoría de la decisión registra que se ofreció el prellenado y a
qué ids de públicos (`validaciones.prellenado_publicos`, migración
0008): ids del catálogo, nunca direcciones. **No hay registro de
envío** —el sistema no puede saber si la persona envió— y no se
inventa uno.

## Considered Options

- **Enviar por API (`gmail.send` o `gmail.compose` + send).** Se
  descartó por definición de Juani del 16/11: la aprobación no envía, y
  enviar por API exigiría un scope que el diseño no pide y le quitaría a
  la persona la última revisión del correo que sale con su cuenta.
- **Crear el borrador por API (`gmail.compose`).** Se descartó por lo
  mismo: sigue siendo escritura en el buzón de la persona y un scope que
  el flujo no necesita — la URL de composición lo resuelve sin nada.
- **`mailto:` con `bcc`.** Se descartó porque dispara el cliente de
  correo por defecto, no Gmail en el navegador, y algunos clientes no
  respetan `bcc` del protocolo.
- **Confiar sólo en `AccountChooser`.** Se descartó al no encontrar
  documentación oficial del parámetro `continue`: la opción
  `authuser=<correo>` queda como camino verificado, y el bloque ofrece
  ambos.

## Consequences

- `publicos_destinatarios_v2` trae los 18 públicos (sólo id y nombre);
  `canal_form` y la web validan contra ella y la hoja de respuestas suma
  `canal_form_respuestas_v4`, mismas columnas que la v3 con la pregunta
  de públicos apuntando al catálogo nuevo. La v1 y la v3 quedan
  versionadas para trazabilidad.
- `agente1/audiencias.py` carga el catálogo externo fail-closed y arma
  la URL de composición: módulo puro, sin red ni `gmail_envio`.
- `crear_app` recibe `catalogo_audiencias`; con él, valida la cobertura
  del contrato al arranque y habilita la preselección de públicos por
  `usos_candidatos` en «Nuevo pedido», el bloque «Preparar correo» y
  `/solicitudes/{id}/correo`.
- `scripts/servidor_web.py` declara `AGENTE1_AUDIENCIAS_PATH` y cierra
  con `web_audiencias_invalid` si el archivo no carga; el compose lo
  apunta dentro del directorio de config del host, montado `ro`.
- `validaciones` suma `prellenado_publicos` (migración 0008,
  `down` con pérdida clasificada como restauración obligatoria).
- El envío sigue fuera del sistema: la aprobación cierra el recorrido
  de difusión del agente y abre el correo en manos de la persona.
