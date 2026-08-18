# Benchmark local Ollama HU-011 JSON Schema v3 — 2026-08-17

## Propósito

Este experimento cambia una sola variable conceptual respecto de structured v2:
el transporte solicita salida restringida por JSON Schema con temperatura cero.
Se conservaron modelo, prompts, contratos, dataset, timeout, `num_predict` y el
plan de seis intentos.

El resultado fue **INCOMPATIBLE_RUNTIME_SCHEMA**. Las seis solicitudes fueron
rechazadas por Ollama antes de comenzar la inferencia. No se generó ningún
borrador y no se alcanzó el renderer determinista.

## Configuración controlada

| Componente | Valor |
| --- | --- |
| Evidencia | `HU011-OLLAMA-JSON-SCHEMA-V3-20260817-001` |
| Baseline | `HU011-OLLAMA-STRUCTURED-V2-20260817-001` |
| Runtime | Ollama `0.32.14-1`, user-local y limitado a loopback |
| Modelo | `llama3.2:3b`, GGUF Q4_K_M |
| Formato | `json_schema` |
| Hash canónico del schema de formato | `bcadefe75f4aba1e0ad6247ae881f162a029f1fa4495566827230fd4b37ef4e5` |
| Temperatura | 0 |
| Timeout | 120 segundos |
| Presupuesto de salida | 112 tokens |
| Intentos | seis, sin reintentos automáticos |

Los componentes permanecieron sin cambios durante la captura y quedaron
identificados mediante IDs opacos y hashes. Structured v2 y el transporte JSON
Schema todavía no estaban integrados al base commit; no se afirma lo contrario.

## Método solicitado y condición efectiva

Se programaron Instagram y LinkedIn bajo model cold, modelo residente y mismo
prompt warm. Sin embargo, el runtime rechazó el schema al preparar la grammar:

- las dos primeras solicitudes cargaron el modelo y fallaron antes de inferir;
- las cuatro restantes volvieron a rechazar el schema;
- ningún prompt fue evaluado y no existió una condición warm efectiva.

Por eso las etiquetas cold, resident y warm describen el plan ejecutado, no una
comparación válida de caché del modelo.

## Resultado

| Canal | Condición solicitada | Latencia | Resultado | Borradores |
| --- | --- | ---: | --- | ---: |
| Instagram | model cold y prompt cold | 5,116467 s | `error_generacion` | 0 |
| Instagram | modelo residente y prompt cold | 0,241783 s | `error_generacion` | 0 |
| Instagram | mismo prompt warm | 0,232705 s | `error_generacion` | 0 |
| LinkedIn | model cold y prompt cold | 6,410774 s | `error_generacion` | 0 |
| LinkedIn | modelo residente y prompt cold | 0,263261 s | `error_generacion` | 0 |
| LinkedIn | mismo prompt warm | 0,230939 s | `error_generacion` | 0 |

Resumen:

- cero salidas aceptadas de seis;
- seis rechazos de API de seis;
- cero timeouts y cero errores de red;
- cero borradores inválidos persistidos;
- cero inferencias iniciadas.

El diagnóstico local fue HTTP 400 durante la conversión de JSON Schema a
grammar. El patrón de hashtags contiene un escape de clase que esta versión del
runtime no puede compilar y devuelve `UNSUPPORTED_ESCAPE_IN_PATTERN`. El adapter
cerró la operación como `error_generacion` sin exponer el cuerpo remoto en los
logs de aplicación.

## Comparación v2 frente a v3

| Corte | Aceptadas | Rechazadas | Código dominante | Inferencia | Latencia observada |
| --- | ---: | ---: | --- | --- | --- |
| structured v2 | 0 | 6 | `json_invalid` | sí | 13,932053 a 42,836248 s |
| JSON Schema v3 | 0 | 6 | `error_generacion` | no | 0,230939 a 6,410774 s |

La menor latencia v3 **NO es una mejora**: mide un rechazo previo a inferencia.
No corresponde comparar calidad, warm cache ni performance generativa entre
ambos cortes.

## Próximo cambio controlado

Antes de repetir hay que volver compatible el schema con la grammar del runtime,
sin relajar el gate de aplicación. El cambio mínimo defendible es reemplazar el
patrón problemático por una restricción compatible y mantener la allowlist
posterior de hashtags. Luego debe repetirse el mismo plan de seis intentos como
un experimento nuevo, nunca sobrescribiendo v3.

## Límites

- Los datos son sintéticos.
- V3 no evaluó la capacidad generativa del modelo con JSON Schema.
- No hubo borrador para evaluación humana.
- No existe validación SEU.
- Las políticas y el catálogo siguen siendo provisionales.
- Esta evidencia no habilita declarar HU-011 completa, Gate G2 ni TRL 3.
