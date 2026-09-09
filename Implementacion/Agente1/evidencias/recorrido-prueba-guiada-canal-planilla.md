# Recorrido — prueba guiada del canal de interacción (adapter de planilla offline)

## Qué demuestra

- Que una persona de la SEU puede pedirle una gacetilla al Agente 1 escribiendo
  en prosa suelta, en una fila de una planilla, sin usar consola ni conocer un
  identificador técnico.
- Que la respuesta —borrador, repregunta o rechazo— vuelve a la misma persona
  como una fila legible, sin volver a pasar por una terminal.
- Que el canal es un puerto reemplazable: hoy es un CSV en una carpeta, el día
  de mañana puede ser Google Chat o correo, sin tocar el núcleo de
  interpretación (`interpretacion.py`).

## Qué NO demuestra

**Este recorrido no acredita control de acceso.** La columna `identificador`
de `pedidos.csv` es una afirmación de quien escribe la fila, no una identidad
verificada: cualquiera con acceso de escritura al archivo puede poner ahí el
nombre y el rol que quiera. Es la misma decisión documentada en ADR 0002
(`docs/adr/0002-identidad-afirmada-por-el-canal-no-verificada.md`) y en el
vocabulario de `CONTEXT.md` ("recibir un pedido por un buzón no otorga los
permisos de ese buzón"). Lo único que esta prueba certifica sobre identidad es
que el rechazo por rol no habilitado funciona y queda registrado — no que el
sistema sepa quién es la persona.

Tampoco demuestra: identidad institucional, OAuth, Google Chat, Workspace live,
resolución difusa de actividad por título (#23), despacho de post (#22),
estado entre turnos (#25), ni ningún nivel TRL o validación institucional. Es
evidencia técnica y reproducible; la aceptación de la SEU sigue dependiendo de
definiciones que continúan abiertas (ver #18, "Further Notes").

## Antes de empezar

- No hace falta cuenta, contraseña, VPN ni acceso a Google Workspace.
- Hace falta una carpeta compartida entre quien conduce la demo (con una
  terminal y este repositorio clonado) y la persona de la SEU — puede ser una
  carpeta local que se proyecta en pantalla, una carpeta sincronizada
  (Drive/OneDrive apuntando a un directorio local), o simplemente la misma
  máquina.
- La persona de la SEU sólo necesita un editor de planillas (Excel, Google
  Sheets exportado a CSV, LibreOffice Calc) o, si se siente cómoda, un editor
  de texto plano. No necesita saber qué es un identificador de actividad ni
  cómo se llama la actividad en el sistema — sólo necesita mencionarla en su
  pedido con las mismas palabras que usaría al hablar.
- Quien conduce la demo necesita una terminal en `Implementacion/Agente1`.

Este recorrido usa el dataset sintético del repositorio
(`data/actividades_sinteticas.csv`), que sólo tiene actividades ficticias. El
generador es el fake determinista: no sale a red ni depende de un modelo
instalado. El contenido de borrador que produce está pre-validado (mismo texto
que `golden/SYN-001.md`) para la actividad `SYN-001` — "Taller sintético de
vinculación", con fecha 2026-08-05 — así que la prueba guiada debe pedirse
sobre esa actividad puntual. Esto no es una limitación del canal: es que este
incremento (#20/#24) todavía reconoce sólo un identificador explícito en la
prosa, no un título parcial (eso es #23, la búsqueda difusa).

## Paso a paso

### 1. Preparar la carpeta compartida

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-seu-hu013
```

Usar cualquier carpeta; `/tmp/demo-seu-hu013` es sólo un ejemplo. Esa carpeta
es "la planilla": no hace falta Google Sheets, cualquier archivo `.csv` sirve.

### 2. Crear `pedidos.csv` con la fila inicial (o dejar que la escriba la persona)

Columnas: `id_pedido`, `identificador`, `rol`, `texto`.

```bash
cat > /tmp/demo-seu-hu013/pedidos.csv <<'EOF'
id_pedido,identificador,rol,texto
EOF
```

`id_pedido` puede ser cualquier valor corto sin espacios (por ejemplo `1`,
`2`, ...) — es sólo lo que permite emparejar la respuesta con el pedido, la
persona no necesita entender para qué sirve. `identificador` es cómo se
identifica la persona (su nombre, su usuario) y `rol` tiene que ser uno de los
roles habilitados provisionales: `coordinador_seu` o `auxiliar_seu`. Este
campo también lo completa la persona (o quien conduce la demo, indicándole qué
poner); no hay ninguna verificación detrás.

### 3. La persona de la SEU escribe su pedido

Pedirle que agregue una fila con su nombre, su rol, y su pedido **en sus
propias palabras**, mencionando la actividad `SYN-001` de alguna forma
reconocible (puede escribir el identificador tal cual, o incluirlo entre
paréntesis si prefiere una frase más natural — ver nota abajo). Ejemplo real
de fila que funciona:

```csv
1,maria.perez,coordinador_seu,Necesito una gacetilla para la actividad SYN-001 del martes
```

> Nota para quien conduce la demo: como la resolución por título todavía no
> existe (#23), la frase tiene que contener el identificador `SYN-001` en
> alguna parte reconocible (letras-guion-números, como lo escribiría alguien
> copiándolo de la planilla de actividades). Es razonable pedirle a la persona
> que lo intente primero sin el identificador — para que vea la repregunta de
> "no reconocí una actividad" — y después con él, para ver el camino feliz.
> Ambos son parte legítima de la demo.

### 4. Atender la planilla

Quien conduce la demo corre, desde `Implementacion/Agente1`:

```bash
PYTHONPATH=src python scripts/atender_canal_planilla.py --directorio /tmp/demo-seu-hu013
```

Esto atiende **una sola vez** todo lo que esté pendiente en `pedidos.csv` y
escribe la respuesta en `respuestas.csv`, dentro de la misma carpeta. No hace
falta dejarlo corriendo: es una atención puntual, a propósito, para que la
demo tenga un momento claro de "ahora reviso qué contestó el agente".

### 5. La persona de la SEU lee la respuesta

Abrir `respuestas.csv` (mismo formato de planilla). Columnas:
`id_pedido`, `estado`, `referencia_borrador`, `resumen`, `error`.

Con el pedido del paso 3, la fila esperada es:

```csv
id_pedido,estado,referencia_borrador,resumen,error
1,PENDIENTE_VALIDACION,/tmp/demo-seu-hu013/borradores/SYN-001.md,Gacetilla para 'Taller sintético de vinculación' (2026-08-05).,
```

`estado` en `PENDIENTE_VALIDACION` es el camino feliz: hay un borrador nuevo,
todavía sin validar por una persona (esta prueba no habilita ninguna
publicación). `referencia_borrador` apunta al archivo del borrador —
`borradores/SYN-001.md`, dentro de la misma carpeta— y `resumen` es una frase
corta armada con datos ya institucionales (título, fecha), nunca el texto
completo. Abrir ese archivo para mostrarle a la persona el borrador entero.

### 6. Repetir para ver una repregunta o un rechazo

Agregar una segunda fila a `pedidos.csv` sin el identificador
(`Necesito una gacetilla para el taller del martes`, sin `SYN-001`) y volver a
correr el paso 4. La respuesta correspondiente en `respuestas.csv` va a tener
`estado` `INCOMPLETA` y un `error` explicando que no se reconoció un
identificador de actividad explícito.

Para ver el rechazo por rol, agregar una fila con un rol que no sea
`coordinador_seu` ni `auxiliar_seu` (por ejemplo `visitante`). La respuesta
correspondiente tiene `estado` `RECHAZADA` y `error`
"El rol de quien pide no está habilitado para interactuar con el agente". Este
intento también queda registrado — ver paso 7.

### 7. Mostrar el registro de auditoría (opcional, para perfil más técnico)

```bash
cat /tmp/demo-seu-hu013/logs/interpretaciones-hu013.jsonl
```

Cada línea es una interacción: intención clasificada, resultado, si intervino
el modelo (siempre `false` en este incremento), y **`identidad_verificada:
false` en todas las líneas, sin excepción** — es la marca explícita de que
nada de lo anterior acreditó quién es la persona. El texto del pedido nunca
aparece: sólo su hash (`mensaje_hash`).

### 8. Limpieza

```bash
rm -rf /tmp/demo-seu-hu013
```

No queda ningún estado durable fuera de esa carpeta: repetir la demo con una
carpeta nueva empieza de cero.

## Qué mirar si algo no sale como se espera

- **No aparece ninguna fila nueva en `respuestas.csv`.** Revisar que
  `pedidos.csv` tenga el encabezado exacto (`id_pedido,identificador,rol,texto`)
  y que la fila tenga las cuatro columnas. Una fila sin `id_pedido`, sin
  `identificador` o sin `rol` se omite silenciosamente en la lectura (es
  deliberado: no hay forma de responderle a un pedido que todavía no está
  completo) — completar la fila y volver a correr el script la recoge en la
  siguiente pasada.
- **La misma fila vuelve a aparecer como si no se hubiera atendido.** No debería
  pasar: una vez que su `id_pedido` aparece en `respuestas.csv`, el adapter no
  vuelve a leerla como pendiente. Si se ve lo contrario, comparar que el
  `id_pedido` de la fila de `pedidos.csv` sea exactamente el mismo que el de
  `respuestas.csv` (sin espacios de más).
- **Se quiere reintentar la misma actividad.** Agregar una fila nueva con un
  `id_pedido` distinto: cada pedido regenera y produce un borrador nuevo, no
  hay idempotencia ni reserva sobre esto (a diferencia de las confirmaciones de
  HU-012).
