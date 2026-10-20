# Modo producción del envío Gmail (#141)

**Estado institucional:** PENDIENTE (lista real y plantilla por tipo a cargo de la SEU)  
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

Ninguna de las dos listas se versiona ni se hardcodea. La lista aprobada y la
plantilla por tipo las define la SEU; este ticket no las inventa.

## Procedimiento de habilitación

1. La SEU aprueba la lista de destinatarios y la plantilla del tipo de
   comunicación que se va a enviar.
2. Informática escribe la lista aprobada en
   `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS`, en el mismo env file fuera del
   repo que el resto de la configuración.
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

- **La plantilla aprobada por tipo.** Los renderers actuales de HU-012,
  HU-014 y del canal de pedidos arman el cuerpo con `BORRADOR — NO ENVIAR`.
  El adapter de producción los rechaza a propósito. Falta parametrizar esos
  renderers para que, en producción, compongan el cuerpo de la plantilla
  aprobada sin marca. Es una decisión de contenido de la SEU, no de este
  ticket.
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
