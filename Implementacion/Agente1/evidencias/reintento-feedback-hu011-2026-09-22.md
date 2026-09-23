# Reintento acotado con feedback de regla en HU-011

- **Issue:** `SpendIce/Proyecto-Final#37` (mapa wayfinder #30)
- **Fecha:** 2026-09-22
- **Entorno:** local controlado, CPU, `llama3.2:3b` en Ollama loopback,
  `temperature=0`, `num_predict=512`, `json_schema`.
- **Alcance:** cerrar la brecha de obediencia del modelo que dejó la
  re-medición del 22/09 (`medicion-hu011-v3-post-seu-2026-09-22.md`, 1/6):
  tuteo (`non_rioplatense_register`), palabras distintivas del título
  (`source_fact_in_creative_field`) y un hecho inventado
  (`unauthorized_fact_claim`). No es validación SEU ni medición de calidad.

## 1. Qué se implementó

`_procesar_post` hacía un solo intento: generaba, validaba con el gate y
terminaba `FALLIDA`. Ahora, sólo en el camino estructurado (contratos v2/v3),
si el primer intento cae **exclusivamente por códigos de contenido**
(`CODIGOS_REINTENTABLES`), el pipeline regenera una vez más —tope total: 2
intentos— con un prompt que agrega esas reglas como instrucción adicional.

El feedback se compone en `_prompt_con_feedback_reglas`: un bloque
`CORRECCION_OBLIGATORIA` con una instrucción por código caído
(`INSTRUCCION_REINTENTO_POR_CODIGO`), insertado antes de `DATOS_JSON_INICIO`
—la misma técnica que `scripts/medir_conformidad_v3.py` usa para sus
variantes—. La plantilla versionada no se toca. El bloque nombra la regla
(`[non_rioplatense_register]`) pero **no cita el literal rechazado**: repetir
«inscríbete» o «sintético» en la corrección le sugeriría al modelo la palabra
que tiene que evitar. Con `temperature=0` el segundo prompt tiene que ser
distinto del primero o produciría la misma salida.

## 2. Qué se reintenta y qué no

Reintentables —describen decisiones de redacción del modelo, corregibles con
la instrucción: `non_rioplatense_register`, `source_fact_in_creative_field`,
`unauthorized_fact_claim`, `unauthorized_date`, `unauthorized_number`,
`unauthorized_email`, `unauthorized_url`, `unauthorized_amount`,
`unauthorized_place`, `unauthorized_action_claim`,
`unauthorized_call_to_action`, `unauthorized_emoji`,
`unauthorized_exclamation`, `unauthorized_promotional_language`,
`prompt_injection_echo`, `creative_field_invalid`,
`creative_slot_not_in_catalog`, los cuatro códigos de hashtags y
`length_out_of_range`.

No reintentables —deterministas o de infraestructura, un segundo intento no
los corrige: el parseo (`output_empty`, `json_invalid`, `json_duplicate_key`,
`json_too_large`, `json_types_invalid`, `json_fields_invalid`), las
invariantes internas del renderer (`renderer_invariant_violation`,
`document_structure`), `presupuesto_agotado`, `error_generacion` y toda falla
previa a la generación (fuente, canal, datos incompletos, política
incompatible). El camino heredado `text-v1` no reintenta.

## 3. Auditoría

Cada intento deja su línea en `logs/ejecuciones.jsonl`, ordenada por el campo
`intento` (0 = la ejecución cayó antes de invocar al generador). El intento
fallido no terminal se registra como `resultado: "reintento_pendiente"` —el
mismo vocabulario que la cola de envíos de HU-012— y la línea terminal
conserva los resultados de siempre: una `salida_no_conforme` con `intento: 2`
está agotada tras reintento; con `intento: 1` cayó en el primero. El log no
copia la prosa rechazada ni datos de la actividad.

`scripts/medir_conformidad_v3.py` se ajustó para consumir todas las capturas
de cada caso (una por intento) y reporta `intentos` por caso; los conteos de
`eval_count` suman los intentos, que es el costo real del mecanismo.

## 4. Regresión

`tests/test_posts_reintento.py` (12 pruebas): conformidad en el segundo
intento, reintento agotado con evidencia de los dos intentos, no-reintento en
parseo/presupuesto/transporte, presupuesto agotado en el reintento, cobertura
de v2, y `text-v1` intacto. El gate no se debilitó: los casos negativos de la
matriz siguen `INCOMPLETA`/`FALLIDA` y `test_politica_redes.py` sigue en
verde. Suite: 915 pruebas en verde; el único fallo es
`test_el_presupuesto_del_fallback_se_deriva_del_contrato` (HU-013), preexistente
a este cambio.

## 5. Re-medición live con el reintento activo

`salida/medicion-v3-reintento-2026-09-22/medicion-v3.json` (evidencia
`HU011-V3-REINTENTO-2026-09-22`), misma matriz y parámetros que la corrida
previa:

| Caso | Canal | Intentos | Resultado | Errores del intento terminal |
|---|---|---|---|---|
| SYN-001 | instagram | 2 | FALLIDA `salida_no_conforme` | `source_fact_in_creative_field`, `non_rioplatense_register` |
| SYN-001 | linkedin | 2 | FALLIDA `salida_no_conforme` | `source_fact_in_creative_field`, `non_rioplatense_register` |
| SYN-002 | ambos | 0 | INCOMPLETA `required_fields_missing` | caso negativo, conforme |
| SYN-003 | instagram | 2 | FALLIDA `salida_no_conforme` | `non_rioplatense_register` |
| SYN-003 | linkedin | 1 | PENDIENTE_VALIDACION | — |
| SYN-004 | ambos | 0 | INCOMPLETA `required_fields_missing` | caso negativo, conforme |
| SYN-005 | instagram | 2 | FALLIDA `salida_no_conforme` | `source_fact_in_creative_field`, `unauthorized_call_to_action`, `unauthorized_fact_claim` |
| SYN-005 | linkedin | 2 | FALLIDA `salida_no_conforme` | `source_fact_in_creative_field`, `unauthorized_fact_claim`, `unauthorized_exclamation` |

**1/6 aceptadas**, igual que la corrida sin reintento. El mecanismo funcionó
como está diseñado —cada falla de contenido reintentó una vez con feedback,
los negativos no invocaron al modelo (`intento: 0`) y los errores del segundo
intento difieren de los del primero, así que el prompt con feedback sí movió
la salida—, pero `llama3.2:3b` sigue emitiendo tuteo y fragmentos del título
aun con la regla nombrada. La brecha residual ya no es un intento ausente:
queda en la obediencia del modelo de 3B, y las palancas siguientes (few-shot,
otro modelo, fine-tuning) son una decisión distinta a esta.

## 6. Alcance de esta evidencia

Datos sintéticos, un modelo, un reintento por caso. Nada acá acredita
conformidad editorial, validación SEU, Gate G2 ni TRL.
