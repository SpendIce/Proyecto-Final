# Medición del presupuesto de decodificación — DEF-A1-013

- **Issue:** `SpendIce/Proyecto-Final#4`
- **Fecha:** 2026-09-08
- **Entorno:** local controlado, CPU, `llama3.2:3b` en Ollama loopback.
- **Alcance:** dimensionamiento de `num_predict` contra el contrato creativo
  vigente. No es una medición de calidad de contenido ni de conformidad.

## 1. Qué se estaba midiendo mal

`num_predict=112` cortaba la salida del contrato v3 antes de cerrar el objeto
JSON. El parser recibía texto incompleto y lo registraba como `json_invalid`,
de modo que el benchmark del 2026-08-26 atribuía al modelo una falla que era de
configuración. Un presupuesto corto no produce un error propio: produce un
diagnóstico equivocado.

La corrección parcial a 300 hizo desaparecer los `json_invalid` y dejó ver las
fallas reales de contenido, pero seguía siendo un valor elegido por resultado
observado, no derivado del contrato.

## 2. Cómo se midió

`/api/generate` con `raw: true` y `num_predict: 1`. En esa forma
`prompt_eval_count` devuelve la tokenización exacta del texto enviado, sin
plantilla de chat: sirve para medir cuánto cuesta un documento sin depender de
lo que el modelo genere.

El documento medido es el más grande que admite `post_creative_output_v3`:
`gancho` 160, `prosa` 500 y `cta` 160 caracteres, más los cuatro hashtags del
enum. Serializado sin espacios da **924 caracteres**.

Reproducible con `uv run python scripts/medir_presupuesto_decodificacion.py`
contra un Ollama local con el modelo descargado. El script termina con código 2
si una corrida mide un extremo peor que el versionado, para que la evidencia no
envejezca en silencio.

Los mismos números quedan como dato en `presupuesto.MEDICION_DOCUMENTO_MAXIMO_V3`,
para que la regresión pueda verificar la cota contra la medición en lugar de
contra sí misma.

## 3. Resultado

Mismo documento de 924 caracteres, cuatro estilos de redacción:

| Estilo del texto | tokens | caracteres por token |
|---|---|---|
| Prosa institucional | 233 | 3,966 |
| Prosa con acentuación densa | 228 | 4,053 |
| Palabras de una y dos letras | 308 | 3,000 |
| Mayúsculas y signos de puntuación | 482 | 1,917 |

El mismo contrato, con el mismo largo en caracteres, cuesta entre 228 y 482
tokens según cómo esté escrito. Esa dispersión es la razón por la que un
presupuesto "que anduvo en una corrida" no alcanza como justificación.

Para el documento mínimo del contrato (179 caracteres) el rango es 52 a 77
tokens, con la misma forma: el extremo malo lo marca el estilo con mayúsculas y
puntuación.

## 4. Presupuesto adoptado

`presupuesto_minimo_num_predict` divide los caracteres del documento máximo por
el extremo malo medido. El 1,917 observado se versiona redondeado hacia abajo
como 1,91, para que el presupuesto derivado nunca quede por debajo de lo que la
medición ya vio: **484 tokens** para v2 y v3.

`DEFAULT_OLLAMA_NUM_PREDICT` pasa de 300 a **512**, que cubre los 484
requeridos con 5,8 % de margen.

El rango configurable pasa a 32–1024. El piso queda bajo a propósito: una
corrida de evidencia tiene que poder elegir un presupuesto insuficiente para
demostrar el agotamiento, como hace la sección 5. Lo que protege a una baseline
no es el rango sino el default y su regresión. El techo sube porque con 512
quedaba pegado a los 484 requeridos: un contrato apenas más largo se habría
quedado sin ninguna configuración válida. El techo acota una generación
desbocada; el límite efectivo en la práctica lo pone el timeout.

Subir el techo casi no cuesta, porque `num_predict` es un tope y no una meta:
la latencia la fija la cantidad de tokens que el modelo llega a emitir. Corrida
live sobre `SYN-001`, misma fila y mismo modelo:

| `num_predict` | resultado | latencia | sha256 del borrador |
|---|---|---|---|
| 300 | `borrador_generado` | 10,32 s | `645922b6db9fb263…` |
| 512 | `borrador_generado` | 11,81 s | `645922b6db9fb263…` |

Mismo borrador byte a byte y latencia dentro del ruido de dos corridas en CPU.

## 5. Lo que la cota no resuelve

Ningún presupuesto finito garantiza que toda salida posible termine. Por eso el
adapter detecta `done_reason == "length"` —que Ollama devuelve junto con
`done: true`, razón por la cual el corte pasaba inadvertido— y lo reporta como
`PresupuestoAgotadoError`. El pipeline lo registra con `resultado` propio,
`presupuesto_agotado`, en lugar de mezclarlo con `error_generacion` o dejarlo
llegar al parser como `json_invalid`.

Verificación live del 2026-09-08 sobre `SYN-001` con `num_predict=32`:

```
resultado=presupuesto_agotado  estado=FALLIDA  num_predict=32  latencia_s=25,03
```

Sin borrador y sin datos de la actividad en el registro. La auditoría conserva
el valor efectivo de `num_predict`, que es lo que hace accionable el
diagnóstico, y no incorpora prompt ni contenido.

## 6. Alcance de esta evidencia

Entorno controlado con datos sintéticos. No demuestra conformidad de contenido,
no cierra `DEF-A1-014`, no constituye validación de la SEU y no habilita el
Gate G2 ni un nivel TRL.
