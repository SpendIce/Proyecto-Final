# Respuesta del Agente 1 a la rc2 y a `RESPUESTA-PEDIDOS.md`

Responde a `RESPUESTA-PEDIDOS.md` (13-oct-2026). La escribe Juan Ignacio Goñe.

## rc2: PASA

`RESULTADO.md` va adjunto: **Veredicto `PASA`** sobre la `1.1.0-rc2`, huella `a0082324…52a7f0ea`, que coincide con
`CONGELADO.sha256`. Pasan 57/57 escenarios y 39/39 casos del cliente. Para la rc2 el cliente no necesitó cambios: ya
tenía `newsletter` y `correo`. El 30/10 vuelvo a correr el script contra el tag `contrato-a1/v1.1.0`.

Quedo de acuerdo con las seis respuestas. La 5 (HU-030 después del PPS) va así en los anexos, y para el 18/11 el Agente 1
sigue leyendo la planilla de actividades de la SEU.

## Lo que me pediste

| Tema | Respuesta |
| ---- | --------- |
| Sesión presencial | **Sí, el martes 27/10.** La hora la coordinamos por mensaje. El recorrido de seis pasos que propusiste me sirve tal cual |
| Día de la prueba de laboratorio (2–6/11) | Todavía no lo tengo: el laboratorio no confirmó. Te aviso apenas lo sepa |
| C16: en qué momento registra el Aporte el Agente 1 | **Al publicarse**: cuando una persona autorizada registra la decisión de publicación (`publique`) en el Form de decisiones sobre una pieza que citó fuentes de Historia Viva (nunca al generar el borrador ni si se descarta) |

## Pedido nuevo: una prueba corta de lectura antes del 23/10

El 23/10 entrego los anexos al laboratorio (fecha propuesta, todavía sin confirmar) y ahí declaro Historia Viva como
**demo en vivo**. Hasta hoy el cliente del Agente 1 solo habló con el mock. No quiero declarar en vivo una integración que
nunca tocó tu API, así que te pido una prueba corta **antes del 23/10**, aparte del 27/10.

- **Cuándo:** el día que te quede mejor entre el **lunes 19 y el jueves 22/10**. Unos 30 minutos.
- **Dónde:** presencial, con tu hotspot, igual que en el laboratorio y en la mesa. Así probamos también la red de la demo.
- **Token:** solo `fragmentos:leer` y `piezas:leer`, emitido en el momento y revocado al terminar.

Recorrido:

1. Sin token da 401. Con token, `GET /v1/fragmentos` y `GET /v1/piezas/{pieza_id}` dan 200. Una Pieza no Validada da 404.
2. El Agente 1 consulta un período de noviembre y arma el borrador del post de efeméride con la Pieza que devuelva. Si
   todavía no tenés cargadas las de noviembre, me sirve cualquier Pieza Validada con fecha de día o de mes.

Idempotencia, 422, cupos, rotación y `X-Solicitud-Id` quedan para el 27/10, como propusiste.

Si no llegás antes del 23/10, mantenemos el 27/10 y en los anexos lo pongo como «demo en vivo, a verificar contra la API
real el 27/10».

## Cómo carga el token el Agente 1

Como propusiste: el token se carga directo en una variable de entorno y nunca se escribe en un archivo. Ajusté el
cliente: antes lo leía de un archivo y ahora lo toma de **`AGENTE1_HV_TOKEN`**. La URL va en **`AGENTE1_HV_BASE_URL`**
(no `HV_BASE_URL`). El token no aparece en logs ni en errores. El `RESULTADO.md` adjunto ya corre con este cambio.

Lo único que cambia respecto de lo que escribiste: el cliente toma la variable al arrancar, así que en la rotación del
27/10 (paso 5) vuelvo a arrancar el proceso con el token nuevo. Las corridas de la sesión son cortas, así que no molesta.
