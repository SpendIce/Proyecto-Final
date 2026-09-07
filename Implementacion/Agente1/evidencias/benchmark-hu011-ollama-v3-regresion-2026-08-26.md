# Benchmark HU-011 v3 — regresión local Ollama (2026-08-26)

- **Modelo:** `llama3.2:3b` local, CPU, temperatura 0, `num_predict=112`.
- **Contrato:** `post_creative_output_v3` (redacción libre).
- **Datos:** cinco actividades sintéticas, dos incompletas.
- **Límite:** no hubo publicación, envío, Workspace, datos reales ni revisión
  SEU. Esta evidencia no acredita TRL 3.

## Preparación del runtime

El runtime local conservaba el modelo y el binario, pero cinco enlaces de
librerías compartidas faltaban en `.runtime/ollama-root`. Se restauraron dentro
de ese directorio ignorado por Git. Una inferencia mínima posterior respondió
correctamente, por lo que la matriz mide el modelo y el contrato, no una caída
del transporte.

## Resultado

| Métrica | Resultado |
|---|---:|
| Generaciones intentadas | 6 |
| Generaciones técnicamente aceptadas | 0 |
| Casos negativos correctos | 4/4 |
| Borradores creados | 0 |
| Latencia mínima de generación | 17,604647 s |
| Latencia máxima de generación | 39,702252 s |

Los cinco rechazos `json_invalid` muestran que el modelo no mantuvo el objeto
JSON exigido en este corte v3. La sexta salida fue bloqueada por
`source_fact_in_creative_field`, `non_rioplatense_register` y
`unauthorized_fact_claim`: el gate fail-closed evitó persistir un borrador no
conforme.

## Lectura técnica

El corte es **NO_CONFORME** para la generación live v3. No se debe relajar el
schema, los controles de hechos ni los controles de registro para convertirlo
en verde. La latencia máxima queda por debajo del timeout local de 45 segundos,
pero la dispersión entre 17,6 y 39,7 segundos y la aceptación 0/6 mantienen
abierto `DEF-A1-003` y no permiten declarar un SLA.

El resumen machine-readable y los borradores inexistentes permanecen en
`salida/`, ignorados por Git, para no versionar contenido generado.
