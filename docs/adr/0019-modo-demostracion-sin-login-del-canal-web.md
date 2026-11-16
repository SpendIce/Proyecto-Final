---
status: accepted
confirmed_by: Juan Ignacio Goñe
confirmed_on: 2026-11-16
---

# Modo demostración sin login del canal web

La presentación de cursada es el **18/11/2026** y el canal web no puede
arrancar con su login real: DSI todavía no entregó el dominio, el HTTPS
ni el cliente OAuth de Google que habilitan el ADR 0014
([issue #62](https://github.com/SpendIce/Proyecto-Final/issues/62)). El
16/11/2026 Juani decidió desplegar la web **sin login por ahora** para la
demo, con una forma de ingreso que no finja verificación y que no deje
material marcado como si la hubiera tenido.

Decidimos agregar un modo separado, `AGENTE1_WEB_MODO_DEMO=si`, que
reemplaza la verificación del ID token de Google por **la elección de una
identidad de una lista cerrada del padrón de roles**. El formulario de
ingreso ofrece un «Entrar como» con los correos declarados y el rol que
el padrón les da; el POST acepta sólo un correo de esa lista que siga
teniendo rol vigente, y el rol lo resuelve siempre el servidor, nunca el
navegador.

## Salvaguardas

- **Vencimiento declarado y acotado.** `AGENTE1_WEB_DEMO_HASTA` es
  obligatoria, no acepta una fecha pasada ni una a más de 14 días del
  arranque. Pasada la fecha, todo request responde 503 con la página
  «La demostración venció» —salvo los estáticos que la página necesita—
  y las sesiones demo quedan inválidas aunque el contenedor siga
  corriendo.
- **Lista cerrada del padrón.** `AGENTE1_WEB_DEMO_CORREOS` es obligatoria
  y el arranque exige que cada correo tenga rol en el padrón; si el
  padrón cambia en caliente, el POST lo vuelve a consultar.
- **Sin señales de otro modo.** No convive con
  `AGENTE1_WEB_MODO_PRUEBA=si` ni con `AGENTE1_WEB_GOOGLE_CLIENT_ID`, y
  exige cookie `Secure`.
- **Aviso visible.** Todas las páginas llevan la banda fija «Modo
  demostración: sin verificación de identidad · vence el DD/MM/AAAA».
- **Exposición limitada por despliegue.** Puede correr dentro del
  contenedor y en `0.0.0.0` del contenedor: el compose publica el puerto
  sólo en `127.0.0.1` del host y el acceso entra por `tailscale serve`
  (HTTPS dentro del tailnet) o túnel SSH. El aislamiento lo hace el
  despliegue, no un bind de loopback.
- **Trazabilidad honesta.** La sesión marca su origen `demo` (el real
  marca `google`), la solicitud se asienta con canal `web-demo`
  (migración 0006) y la auditoría HU-013 suma `origen_identidad`: lo
  creado en la demo **nunca figura como identidad verificada por
  Google**. La bandeja, el worker, el vencimiento y la purga tratan
  `web-demo` igual que `web`: el origen declara cómo entró la solicitud,
  no una clase distinta de trabajo.

## Por qué no se reusa el modo prueba

El modo prueba (`AGENTE1_WEB_MODO_PRUEBA=si`) existe para desarrollo y
evidencia: su verificador fake acepta tokens inventados y por eso el
arranque lo bloquea **a propósito** cuando hay señal de un despliegue
real —cookie `Secure`, host que no sea loopback o el contenedor. La demo
necesita justo lo contrario: correr en el contenedor y exponerse fuera de
loopback. Relajar las salvaguardas del modo prueba lo abriría al tráfico
real con un verificador que no verifica nada, y escondería la demo detrás
de un modo que declaró desde el diseño que no es desplegable. Un modo
nuevo con su propia cerca es más honesto que un modo viejo con las
salvaguardas bajadas.

## Qué se pierde

**La identidad no se verifica.** Elegir un correo de la lista no prueba
nada sobre quién está del otro lado, así que una sesión demo no sirve
como evidencia de identidad y el material que genera no puede citarse
como «pedido de X». Es una excepción temporal al ADR 0005 (la identidad
verificada es la condición del rol del padrón) y al ADR 0014 (el canal
web verifica identidad Google): mientras el modo demo esté activo, el
canal web funciona sin la verificación que esos ADR exigen. Por eso la
trazabilidad marca el origen en cada lugar que la registra y la banda lo
dice en cada página.

## Cuándo se retira

El modo demo es temporario y se retira apenas llegue el dominio, el HTTPS
y el cliente OAuth de DSI (#62): se apaga la variable, se despliega el
modo real y las solicitudes `web-demo` completan su ciclo con la
retención vigente. La fecha `DEMO_HASTA` es el segundo límite: si el
dominio no llega antes, el modo deja de servir solo. El retiro del modo
queda documentado con su salida del `compose`, del script y de las
salvaguardas de arranque.

## Considered Options

- **Desplegar el modo prueba relajando sus salvaguardas.** Se descartó
  por lo anterior: el modo prueba declaró desde el diseño que no es
  desplegable, y aflojarlo lo expondría con un verificador fake a tráfico
  real.
- **Un usuario demo único con clave.** Se descartó porque agrega una
  credencial que compartir y no mejora la honestidad: la identidad seguiría
  sin verificarse.
- **Esperar a DSI y no desplegar nada.** Se descartó porque la
  presentación de cursada es el 18/11/2026 y el canal web es la pieza
  central del recorrido.

## Consequences

- El canal web gana un tercer modo de arranque con su propia cerca:
  `modo_demo` en `ConfiguracionWeb`, `validar_configuracion` con padrón y
  reloj inyectados, y las variables `AGENTE1_WEB_MODO_DEMO`,
  `AGENTE1_WEB_DEMO_HASTA` y `AGENTE1_WEB_DEMO_CORREOS` en el stack.
- `solicitudes.canal` suma `web-demo` (migración 0006): todo lo que la
  retención y la bandeja hacen con `web` aplica igual, y el `down` aborta
  en voz alta si quedan filas `web-demo` porque reclasificarlas como
  `web` las mentiría verificadas.
- La auditoría HU-013 suma `origen_identidad` (`google`/`demo`/`null`
  para los canales que no la declaran); `identidad_verificada` sigue en
  `false` en este incremento y nunca sube por la vía demo.
- El modo prueba y el modo real no cambian: sus salvaguardas y su flujo
  quedan intactos y el modo demo no comparte la ruta del verificador.
