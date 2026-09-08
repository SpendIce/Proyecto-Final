# Corrección de la conformidad estructural de gacetillas — DEF-A1-014

- **Issue:** `SpendIce/Proyecto-Final#5`
- **Fecha:** 2026-09-08
- **Entorno:** local controlado, CPU, `llama3.2:3b` en Ollama loopback,
  `num_predict` 512, temperatura 0.
- **Alcance:** conformidad estructural de HU-010 sobre el dataset sintético
  versionado. No es validación de calidad editorial ni institucional.

## 1. Causa, explicada por actividad

Las tres actividades completas del dataset se dividen exactamente por un dato:

| Actividad | `lugar` en la fuente | Resultado con `gacetilla_v2` |
|---|---|---|
| `SYN-001` | `Aula de prueba` | borrador generado |
| `SYN-003` | vacío | `data_structure` |
| `SYN-005` | vacío | `data_structure` |

`SYN-002` y `SYN-004` no entran: se rechazan antes por contacto y fecha
ausentes, que es el comportamiento esperado.

La plantilla `gacetilla_v2` mostraba la línea del lugar en los dos lugares de
los que un modelo copia forma —el bloque de estructura y el ejemplo
sintético—, con la excepción escrita adentro del placeholder:

```
Lugar: <lugar exacto; omitir esta línea si no está informado>
```

y, en el ejemplo, `Lugar: Aula Ficticia`. Un modelo de 3B replica la forma que
ve: para las filas sin lugar emitía la línea igual, sin valor.

`PATRON_DATOS` admite el bloque con dos líneas o con tres, pero la tercera
tiene que tener contenido. `Lugar:` sin valor no es ninguna de las dos formas,
así que el documento se rechaza como `data_structure`, que es correcto.

Reproducción focalizada del 2026-09-08 con `gacetilla_v2`, dos intentos:

```
intento=1 SYN-003 errores=['data_structure'] ultima_linea_datos='Lugar:'
intento=1 SYN-005 errores=['data_structure'] ultima_linea_datos='Lugar:'
intento=2 SYN-003 errores=['data_structure'] ultima_linea_datos='Lugar:'
intento=2 SYN-005 errores=['data_structure'] ultima_linea_datos='Lugar:'
```

2 de 2 en ambas actividades. No era truncamiento: el documento llegaba
completo y bien formado en las otras cuatro secciones.

## 2. Qué se corrigió

`gacetilla_v3` decide la línea por caso, antes de que el modelo la vea:

- con lugar informado, la estructura pide `Lugar: <lugar exacto>`, el ejemplo
  la muestra, y una regla dice que el bloque lleva exactamente tres líneas;
- sin lugar informado, la línea no aparece ni en la estructura ni en el
  ejemplo, y la regla dice que el bloque lleva exactamente dos líneas y que
  escribir `Lugar:` sin valor es un error de formato.

El bloque de datos fuente sigue mostrando `lugar:` vacío: el modelo tiene que
saber que el dato falta, no que la columna no existe.

**El gate no se tocó.** `PATRON_DATOS`, `_validar_salida` y los códigos de
error quedan como estaban. La corrección está del lado del pedido, no del
control.

## 3. Resultado

Corrida live del 2026-09-08, dos intentos por actividad, `gacetilla_v3`:

| Intento | Actividad | Estado | Errores | Latencia | sha256 del borrador |
|---|---|---|---|---|---|
| 1 | `SYN-001` | `PENDIENTE_VALIDACION` | — | 7,26 s | `4e5d756603ecc246…` |
| 1 | `SYN-003` | `PENDIENTE_VALIDACION` | — | 11,47 s | `9b66c5c662bc71b5…` |
| 1 | `SYN-005` | `PENDIENTE_VALIDACION` | — | 11,16 s | `1c788a3f9759e088…` |
| 2 | `SYN-001` | `PENDIENTE_VALIDACION` | — | 9,56 s | `4e5d756603ecc246…` |
| 2 | `SYN-003` | `PENDIENTE_VALIDACION` | — | 10,32 s | `9b66c5c662bc71b5…` |
| 2 | `SYN-005` | `PENDIENTE_VALIDACION` | — | 11,16 s | `1c788a3f9759e088…` |

6 de 6, con borradores idénticos byte a byte entre intentos. Todas las salidas
quedan `BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.

La corrida se repitió sobre `32a79d9`, después de refactorizar `_construir_prompt`
a un mapa de sustituciones: los seis borradores salieron con los mismos tres
hashes, de modo que el refactor no cambió lo que el modelo recibe. Las latencias
de esa segunda corrida van de 11,45 a 24,88 s; la diferencia con la primera es
carga del host, no del prompt.

Reproducible con `uv run python scripts/reproducir_def_a1_014.py`, que corre
las dos plantillas una al lado de la otra.

## 4. Casos negativos

La tasa de aceptación no subió por relajar el control. Las regresiones
deterministas de `tests/test_procesar_gacetilla.py` verifican que se siguen
rechazando:

| Documento | Código |
|---|---|
| `Lugar:` sin valor, con fuente sin lugar | `data_structure` |
| `Lugar: Inventado`, con fuente sin lugar | `unexpected_place` |
| sin línea `Lugar`, con fuente que sí lo informa | `place_missing` |
| `Lugar: Otra Aula 6`, con fuente que dice `Aula 6` | `place_mismatch` |

Además se verifica que la plantilla no deje marcadores sin resolver y que la
línea del lugar aparezca o no según el caso, en la estructura y en el ejemplo.

## 5. Alcance de esta evidencia

Entorno controlado con datos sintéticos, un modelo y dos intentos por
actividad. No demuestra estabilidad sobre datos reales de la SEU, no constituye
validación institucional y no habilita el Gate G2 ni un nivel TRL.
