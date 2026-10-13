# Pedidos del Agente 1 a Historia Viva

Acompaña a `RESULTADO.md` (veredicto `PASA`) y a `PREGUNTAS.md`. Lo escribe Juan Goñe. `PREGUNTAS.md` responde lo que
Historia Viva propone; este archivo reúne lo que el Agente 1 necesita de Historia Viva y que ninguna pregunta cubre.

**Por qué hay apuro.** El Agente 1 tiene su propia fecha de corte para Historia Viva: la entrega de los anexos al
laboratorio, propuesta para el **23/10**. La revisión de laboratorio con demo presencial cae entre el 2 y el 6/11 y la
mesa final es el **18/11**. Si para el 23/10 no hay una instancia de Historia Viva con la que el Agente 1 pueda hablar por
HTTP, el post de efeméride se muestra en la mesa solo como contrato, sin demo en vivo. El fake no se usa en la demo.

## 1. Instancia para la demo

El contrato dice que la API real corre en tu PC (DEC-119), sin servidor ni túnel, y que la prueba se hace en la misma
red. Para mostrar el post de efeméride en vivo necesito una de estas dos cosas:

- **(a)** Que tu PC con Historia Viva esté en la misma red que mi laptop durante la prueba de laboratorio (2–6/11, día a
  confirmar) y durante la mesa final del 18/11.
- **(b)** Otra forma de llegar a la instancia que vos prefieras.

Necesito saber antes del 23/10 si alguna de las dos es posible. Si ninguna lo es, Historia Viva queda declarada como
contrato en los anexos.

## 2. Token

Un token con alcance **`fragmentos:leer` y `piezas:leer`**, nada más. No pido `aportes:escribir` porque los aportes no
entran en la demo del 18/11. Tampoco pido `efemerides:leer`, porque el Agente 1 no consume efemérides ni relatos (ver
C48-1). Lo necesito entregado por fuera de banda, nunca en un repo: decime el canal. El cliente lo lee en cada pedido,
así que una rotación no me obliga a reiniciar nada.

## 3. Sesión presencial

Una fecha **antes del 30/10** para la sesión que propone el contrato: idempotencia real, cupos, 422, rotación de token
y `X-Solicitud-Id` igual a `solicitud_id`. El cliente y la prueba de contrato ya están listos para correr contra
`http://<tu-PC>:8000` cambiando `HV_BASE_URL`.

## 4. Material para la efeméride de la demo

El post de efeméride consulta `GET /v1/fragmentos` por período. Si no hay Piezas Validadas con fechas que caigan en el
período consultado, el resultado es `sinResultados` y no se genera ningún post. Pido que la instancia de la demo tenga
**al menos unas Piezas Validadas con fecha de día o mes en el mes de noviembre** (cualquier año). Sirven tanto para la
prueba del 2–6/11 como para el 18/11. Si además tienen `pagina` o `seccion`, la cita sale completa.

## 5. Actividades vigentes (HU-030)

Sigue pendiente la propuesta que te pasé: que Historia Viva guarde también las **actividades vigentes** de extensión,
no solo las históricas, con procedencia por campo, y que el Agente 1 las lea por consulta. Hasta tener respuesta, el
Agente 1 lee una planilla provisional. Necesito un sí, un no o un «después del PPS» para declararlo en los anexos.

## 6. Puntos abiertos del esquema `Aporte` antes del congelado

`TipoContenido` y `Canal` están marcados como «punto abierto» en el YAML. El Agente 1 genera gacetillas, posts y
newsletters. Propongo:

- `TipoContenido`: sumar **`newsletter`**. `comunicado` me sirve tal como está aunque no lo use. Confirmaciones y
  certificados no se aportan, porque llevan datos personales.
- `Canal`: sumar **`correo`**, que es el canal de la newsletter.

Si esto no entra en la 1.1.0, puede ir en una 1.2.0 aditiva: los aportes no se usan antes del 18/11.
