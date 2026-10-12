# Medición HU-011 v3 con prompt reformulado a instrucciones positivas

- **Fecha:** 2026-09-23
- **Entorno:** local controlado, CPU, `llama3.2:3b` en Ollama loopback,
  `temperature=0`, `num_predict=512`, `json_schema`.
- **Alcance:** probar la hipótesis de que la no-conformidad residual de v3
  (1/6 del 22/09) se debe a que el prompt expresa sus reglas como
  prohibiciones nombrando los literales prohibidos, lo que los activa. La
  variante `positivo` del medidor reescribe esas reglas como especificación
  positiva. No es validación SEU ni medición de calidad editorial.

## 1. Qué se cambió

Variante nueva `--variante-prompt positivo` en
`scripts/medir_conformidad_v3.py`. Opera sobre el prompt ya renderizado; la
plantilla `post_*_structured_v4` no se tocó:

- El bloque `PROHIBIDO ABSOLUTAMENTE` (11 categorías con sus literales:
  «inscríbete», «regístrate», «únete», «descubre», «puedes», «remoto»,
  «gratuito», etc.) se reemplaza por `REGLAS DE REDACCIÓN`, que describe qué
  es el texto: se escribe completo en palabras, la actividad se nombra en
  forma genérica, la invitación es atemporal, describe sólo la invitación, el
  CTA remite al enlace, vocabulario académico y sobrio.
- Las instrucciones de registro pasan a positivo: en lugar de prohibir tuteo
  con ejemplos, declaran el voseo como forma objetivo con imperativos
  permitidos («sumate», «participá», «conocé», «enterate», «acercate»,
  «animáte») y la impersonal como escape («se invita», «te invitamos»).
- «sin incluir URLs» pasa a «nombrado en palabras»; «lo que no podés es
  copiar su título literal ni sus datos» pasa a «siempre en forma genérica».
- Ninguna forma prohibida queda nombrada en el prompt.

## 2. Resultado

`salida/medicion-v3-positivo-2026-09-23/medicion-v3.json` (evidencia
`HU011-V3-POSITIVO-2026-09-23`), misma matriz y parámetros que el 22/09, con
el reintento del pipeline activo:

| Caso | Canal | Intentos | Resultado | Errores del intento terminal |
|---|---|---|---|---|
| SYN-001 | instagram | 2 | FALLIDA | `unauthorized_number`, `unauthorized_place` |
| SYN-001 | linkedin | 2 | FALLIDA | `unauthorized_number`, `unauthorized_place`, `non_rioplatense_register`, `unauthorized_fact_claim` |
| SYN-002 | ambos | 0 | INCOMPLETA | caso negativo, conforme |
| SYN-003 | instagram | 2 | FALLIDA | `non_rioplatense_register`, `unauthorized_fact_claim` |
| SYN-003 | linkedin | 1 | PENDIENTE_VALIDACION | — |
| SYN-004 | ambos | 0 | INCOMPLETA | caso negativo, conforme |
| SYN-005 | instagram | 2 | FALLIDA | `source_fact_in_creative_field`, `non_rioplatense_register`, `unauthorized_fact_claim`, `unauthorized_promotional_language` |
| SYN-005 | linkedin | 2 | FALLIDA | `source_fact_in_creative_field`, `unauthorized_number`, `unauthorized_call_to_action`, `unauthorized_fact_claim` |

**1/6 aceptadas**, igual que el baseline v4 y que la corrida con reintento.
Los 4 casos negativos quedan conformes.

## 3. Distribución de fallas vs baseline del 22/09

| Código del gate | Baseline v4 (22/09) | Positivo (23/09) |
|---|---:|---:|
| `non_rioplatense_register` | 5 | 3 |
| `source_fact_in_creative_field` | 2 | 2 |
| `unauthorized_fact_claim` | 2 | 4 |
| `unauthorized_number` | 0 | 3 |
| `unauthorized_place` | 0 | 2 |
| `unauthorized_call_to_action` | 0 | 1 |
| `unauthorized_promotional_language` | 0 | 1 |

## 4. Lectura del resultado

- **La hipótesis de activación de literales tiene apoyo parcial.** El tuteo
  bajó de 5 a 3 casos y el modelo adoptó las formas objetivo declaradas
  («Se invita», «sumate», «conocé», «participá»). Los literales que el v4
  nombraba dos veces dejaron de dominar la distribución; quedan residuales
  «puedes», «conoce», «descubre».
- **Las prohibiciones no eran sólo ruido: cargaban el inventario de
  reglas.** Al retirarlas aparecieron categorías que el baseline no
  violaba: dígitos y fechas («5 de agosto de 2026, a las 10:00 AM»),
  lugares («la Aula de prueba», «sede central»), atribución («La SEU
  organiza», «El Área de Prueba presenta»), modalidad («seminario remoto»),
  gratuidad («es gratuito») y un título inventado («El taller de
  innovación»). La consigna positiva «se escribe completo en palabras, los
  datos los agrega el sistema» no alcanzó para retener esas restricciones.
- **Las fallas ya no tienen causa dominante.** El baseline fallaba
  concentrado (tuteo 5/6); la variante positiva falla dispersa, con siete
  códigos distintos repartidos en cinco casos. Eso es lo que se espera
  cuando el conjunto de restricciones simultáneas excede la capacidad del
  modelo de 3B: cada formulación retiene una parte y pierde otra.
- **Consecuencia para la decisión de modelo:** el resultado refuerza la
  lectura del 22/09 —la brecha es obediencia/capacidad del modelo, no del
  gate ni de una regla mal definida— y descarta la palanca «sólo positivas»
  como suficiente. La variante intermedia pendiente (prohibiciones que
  nombran la clase pero no el literal) aislaría activación de literal vs
  negación; few-shot con ejemplos SEU, un modelo mayor o fine-tuning siguen
  siendo las palancas con más recorrido, todas condicionadas a #14 o a
  decisión humana.

## 5. Alcance de esta evidencia

Datos sintéticos, un modelo, una corrida por caso con el reintento del
pipeline. Nada acá acredita conformidad editorial, validación SEU, Gate G2
ni TRL.
