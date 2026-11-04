# Creación como tarea principal — revisión del 04/11/2026

Juani confirmó que NotebookLM es organizado por el Departamento de Cursos Complementarios y pidió que la interfaz priorice crear contenido: formulario como inicio, asunto sin precargar, descripción principal y eliminación del aviso de actividad no necesaria. Se incorporó esa reacción a las tres variantes del prototipo.

El asunto comienza vacío, es editable y opcional. La descripción sirve como contenido o contexto de redacción. En tipos de datos confirmados se solicitan los campos del contrato; no se infieren hechos desde un asunto ni se reutiliza el texto de una muestra anterior. Si no se escribe un asunto, difusión conserva el título de su actividad y el resto usa el nombre del tipo. El acceso a pedidos anteriores y las acciones de revisión/ajuste quedan como continuación del trabajo.

## Comprobaciones

| Caso | Resultado | LLM | Latencia |
|---|---|---|---:|
| cronica_de_evento | completado | No: composición de datos confirmados | 0 s |
| aviso_de_otra_area | completado | No: composición de datos confirmados | 0 s |
| saludo_o_efemeride | completado | Sí | 114.46 s |
| difusion_de_actividad | fallido | No: composición de datos confirmados | 300.1 s |

Crónica y aviso usaron los datos ingresados y no las muestras históricas. El saludo se generó con la descripción del pedido como contexto. La primera integración de saludo había pasado la descripción como cuerpo confirmado y dio `hecho_perdido`; se corrigió esa conexión sin retirar controles. Se conserva ese resultado de diagnóstico en la evidencia JSON.

**NotebookLM ya no se rechaza por organizador faltante:** el pedido fue admitido, pero la llamada al generador no completó dentro de la ventana de 300 s (resultado `fallido`, `RuntimeError`, latencia 300,10 s). No se creó otra revisión ni se sustituyó por un texto simulado. Este ensayo no permite concluir por sí solo la causa del retraso ni la calidad de una pieza que no se obtuvo.

La comprobación final de Chromium pasó: inicio en nuevo pedido, asunto opcional vacío y editable, descripción usada aun sin asunto, organizador visible, aviso de actividad retirado, tres variantes a 390 px y sin errores JavaScript. No se hizo otra llamada al LLM para esa comprobación final. Calidad humana y validación SEU: pendientes; los datos sintéticos usados para probar controles de formulario no se cuentan como evaluación humana.

## Limpieza solicitada

`deslop` se limitó al diff del prototipo contra el merge-base de su rama descartable con `origin/main`. Normalizó imports/formato y quitó una captura redundante de `JSONDecodeError`, ya cubierta por `ValueError`. El formato conservó el AST y Ruff pasó. No hubo cambios de comportamiento dentro de la limpieza; los cambios funcionales anteriores responden a la revisión de interfaz de Juani.

Quedó señalado para revisión, por lectura de `pollJob` y `render`, que el sondeo redibuja la pantalla completa y podría quitar el foco al escribir otro pedido durante una generación. No se modificó dentro de deslop. La skill `autoreview` no está instalada; esta limpieza y las comprobaciones declaradas no se presentan como ejecución de ese gate ni como aprobación del código productivo.

## Salidas capturadas

### cronica_de_evento

Estado: `completado`. Calidad humana: pendiente.

```text
Asunto: Recorrida de prueba por laboratorios

NOTICIAS FIE

El equipo de prueba recorrió los laboratorios y conoció las tareas de extensión.

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### aviso_de_otra_area

Estado: `completado`. Calidad humana: pendiente.

```text
Asunto: Acceso de prueba al aula

Se informa a la comunidad educativa que el aula de prueba no está habilitada, hasta nuevo aviso.

Muchas gracias

Secretaría Académica

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### saludo_o_efemeride

Estado: `completado`. Calidad humana: pendiente.

```text
Asunto: Saludo a la comunidad educativa

Queremos agradecer a toda la comunidad educativa por el compromiso constante con la educación pública. Su dedicación es fundamental para seguir construyendo juntos un futuro mejor.

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### difusion_de_actividad

Estado: `fallido`. Calidad humana: pendiente.

No hubo una pieza generada para revisar.
