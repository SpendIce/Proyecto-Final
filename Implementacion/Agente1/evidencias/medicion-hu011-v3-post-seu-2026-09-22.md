# Re-medición HU-011 v3 tras los criterios SEU confirmados del 22/09

- **Issue:** `SpendIce/Proyecto-Final#31` (mapa #30)
- **Fecha:** 2026-09-22
- **Entorno:** local controlado, CPU, `llama3.2:3b` en Ollama loopback.
- **Alcance:** verificar si los criterios confirmados por la SEU el 22/09
  (`CONFIRMADO_SEU` por acta) cierran el 0/6 del contrato v3 registrado en el
  spike del 08/09, y re-medir los tokens de `MEDICION_DOCUMENTO_MAXIMO_V3`
  contra el contrato vigente (923 caracteres). No es medición de calidad
  editorial ni validación SEU.

## 1. Qué cambió antes de medir

El 22/09 la SEU confirmó en reunión los dos criterios que causaban el 0/6 del
spike del 08/09: los posts **pueden nombrar la actividad genéricamente** y el
**voseo es aceptable**. El mismo día se implementaron: el gate dejó de tratar
los sustantivos genéricos de actividad como fragmentos del título
(`SUSTANTIVOS_GENERICOS_ACTIVIDAD`) y el patrón de registro se reorientó a
tuteo (`PATRON_TUTEO` ampliado); los prompts estructurados pasaron a v4 con
tono académico, audiencia diferenciada, CTA por canal y allowlist
institucional de hashtags. Esta medición corre ese pipeline vigente, sin
transformaciones de prompt (`--variante-prompt baseline`).

## 2. Resultado de conformidad

`medicion-v3-post-seu-2026-09-22/medicion-v3.json` (evidencia
`HU011-V3-POST-SEU-2026-09-22`), un intento por caso, `temperature=0`,
`num_predict=512`, `json_schema`:

| Caso | Canal | Resultado | Literales que dispararon |
|---|---|---|---|
| SYN-001 | instagram | FALLIDA `non_rioplatense_register` | tuteos: `Descubre`, `Únete` |
| SYN-001 | linkedin | FALLIDA `source_fact_in_creative_field`, `non_rioplatense_register` | tuteo: `Inscríbete`; fragmentos: `sintético`, `vinculación` |
| SYN-002 | ambos | INCOMPLETA `required_fields_missing` | caso negativo, conforme |
| SYN-003 | instagram | FALLIDA `non_rioplatense_register` | tuteos: `Descubre`, `Únete` |
| SYN-003 | linkedin | **PENDIENTE_VALIDACION** | `jornada` presente y admitida como genérica |
| SYN-004 | ambos | INCOMPLETA `required_fields_missing` | caso negativo, conforme |
| SYN-005 | instagram | FALLIDA `source_fact_in_creative_field`, `non_rioplatense_register`, `unauthorized_fact_claim` | tuteos: `Conoce`, `descubre`, `puedes`, `Únete`; fragmentos: `remoto`, `seminario` |
| SYN-005 | linkedin | FALLIDA `non_rioplatense_register`, `unauthorized_fact_claim` | tuteos: `descubre`, `sabes` |

**1/6 aceptadas** (vs 0/6 del 08/09). Los 4 casos negativos quedan conformes.
Latencias 26–74 s en CPU; `eval_count` máximo observado 188 << 512.

## 3. Lectura del resultado

- **El gate quedó con la semántica correcta.** SYN-003 LinkedIn pasa con
  `jornada` en el texto: la exclusión de sustantivos genéricos funciona como
  la SEU la definió. El voseo ya no se penaliza; lo que cae es tuteo real
  (`Descubre`, `Únete`, `Inscríbete`, `Conoce`, `sabes`), que la SEU no
  autorizó. `non_rioplatense_register` sigue siendo el código dominante (5/6),
  pero ahora detecta una desviación real del modelo y no un criterio
  indefinido.
- **El residuo es conformidad generativa, no de criterio.** El modelo sigue
  emitiendo tuteo y copiando palabras distintivas del título (`sintético`,
  `vinculación`, `remoto`) a pesar de los prompts v4, y en SYN-005 aparece
  `unauthorized_fact_claim` (invención de hechos).
- **El pipeline hace un solo intento.** `_procesar_post` genera una vez y
  rechaza; no existe un bucle de reintento que alimente al modelo con la regla
  que cayó. Es la palanca más barata disponible antes de few-shot o
  fine-tuning: reintento acotado con feedback de la regla rechazada, con el
  mismo presupuesto derivado del contrato y la misma auditoría.

## 4. Re-medición del presupuesto de decodificación

`scripts/medir_presupuesto_decodificacion.py --contrato v3` sobre el documento
máximo vigente (923 caracteres):

| Estilo del texto | tokens | caracteres por token |
|---|---|---|
| Prosa institucional | 236 | 3,911 |
| Prosa con acentuación densa | 231 | 3,996 |
| Palabras de una y dos letras | 311 | 2,968 |
| Mayúsculas y signos de puntuación | 485 | 1,903 |

El extremo medido (1,903) es peor que el versionado (1,91): la corrida terminó
con código 2, como está diseñada. `MEDICION_DOCUMENTO_MAXIMO_V3` quedó
actualizada con los cuatro pares (923, tokens) y
`CHARS_POR_TOKEN_MENOS_FAVORABLE` bajó de 1,91 a **1,90**. El presupuesto
derivado del contrato sube de 484 a **486 tokens**; `DEFAULT_OLLAMA_NUM_PREDICT
= 512` sigue cubriéndolo con ~5 % de margen y no requirió cambios.
`tests/test_presupuesto.py` queda en verde (17 pruebas).

## 5. Alcance de esta evidencia

Entorno controlado con datos sintéticos. El 1/6 no acredita conformidad de
contenido ni validación SEU: la revisión asincrónica del paquete regenerado
sigue en curso (DEF-A1-005) y el criterio formal del Gate G2 sigue pendiente
(DEF-A1-006). Lo que sí queda demostrado es que las dos confirmaciones de la
SEU están correctamente implementadas en el gate, y que la brecha restante es
de obediencia del modelo a las instrucciones — no de reglas mal definidas.
