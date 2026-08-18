# Benchmark local Ollama HU-011 JSON Schema v4 — 2026-08-17

## Propósito

Este experimento corrige la incompatibilidad observada en v3 mediante un único
cambio: el schema de hashtags reemplaza el patrón no soportado por un enum
exacto. Se conservaron modelo, prompts, dataset, transporte JSON Schema,
temperatura, timeout, `num_predict` y el plan de seis intentos.

El resultado fue **seis aceptaciones técnicas de seis**, todas en estado
`PENDIENTE_VALIDACION`. Esto prueba que el slice local produjo borradores
conformes al contrato mecánico bajo estas condiciones. No prueba calidad
institucional, estabilidad amplia, SLA, aprobación SEU ni TRL 3.

## Configuración controlada

| Componente | Valor |
| --- | --- |
| Evidencia | `HU011-OLLAMA-JSON-SCHEMA-V4-20260817-001` |
| Baseline inmediato | `HU011-OLLAMA-JSON-SCHEMA-V3-20260817-001` |
| Runtime | Ollama `0.32.14-1`, user-local y limitado a loopback |
| Modelo | `llama3.2:3b`, GGUF Q4_K_M |
| Formato | `json_schema` |
| Hash canónico del schema | `87db650e883b7b2d2f30f210c052d53b9d30d78b87539ceb7b9b314a3fd8bc7f` |
| Temperatura | 0 |
| Timeout | 120 segundos |
| Presupuesto de salida | 112 tokens |
| Intentos | seis, sin reintentos automáticos |

Los ocho componentes permanecieron sin cambios durante la captura y quedaron
identificados mediante IDs opacos y hashes. El slice todavía no estaba
integrado al base commit; el manifest no afirma lo contrario.

## Método

Por cada canal se ejecutaron exactamente tres condiciones:

1. model cold y prompt cold con `SYN-001`;
2. modelo residente y prompt distinto con `SYN-003`;
3. repetición inmediata del mismo prompt con `SYN-003`.

No se realizaron intentos adicionales. Cada salida atravesó el JSON Schema, el
parser, la allowlist creativa, el renderer determinista y el gate final antes de
persistirse como borrador.

## Resultados

| Canal | Condición | Latencia | Estado | Output hash |
| --- | --- | ---: | --- | --- |
| Instagram | model cold y prompt cold | 23,209642 s | `PENDIENTE_VALIDACION` | `7e817974...6bb2` |
| Instagram | modelo residente y prompt cold | 9,544299 s | `PENDIENTE_VALIDACION` | `de60df5b...5b37` |
| Instagram | mismo prompt warm | 7,035854 s | `PENDIENTE_VALIDACION` | `de60df5b...5b37` |
| LinkedIn | model cold y prompt cold | 29,485820 s | `PENDIENTE_VALIDACION` | `b2d13f18...0bd0` |
| LinkedIn | modelo residente y prompt cold | 9,953283 s | `PENDIENTE_VALIDACION` | `8731ef8a...0c0b` |
| LinkedIn | mismo prompt warm | 7,715143 s | `PENDIENTE_VALIDACION` | `8731ef8a...0c0b` |

Resumen:

- seis salidas aceptadas técnicamente de seis;
- cero rechazos, timeouts o errores de transporte;
- seis borradores persistidos y cero borradores inválidos;
- hashes idénticos entre prompt cold y same-prompt warm para `SYN-003` dentro
  de cada canal.

Los borradores y datos de contacto no se versionan en este paquete. El manifest
conserva sólo IDs opacos, correlation IDs, versiones y hashes.

## Comparación v2, v3 y v4

| Corte | Aceptadas | Rechazadas | Resultado dominante | Inferencia | Latencia |
| --- | ---: | ---: | --- | --- | --- |
| structured v2 | 0 | 6 | `json_invalid` | sí | 13,932053 a 42,836248 s |
| JSON Schema v3 | 0 | 6 | `error_generacion` | no | 0,230939 a 6,410774 s |
| JSON Schema v4 | 6 | 0 | `borrador_generado` | sí | 7,035854 a 29,485820 s |

V3 no constituye una comparación de performance porque rechazó el schema antes
de inferencia. Frente a v2, v4 muestra que constrained decoding con un schema
compatible evitó las seis respuestas JSON inválidas en esta muestra. Se trata de
dos registros y una sola repetición same-prompt por canal: NO alcanza para
afirmar estabilidad general.

## Lectura técnica

- El enum exacto resolvió la incompatibilidad de grammar sin quitar la allowlist
  posterior de la aplicación.
- Cold fue más lento que las condiciones con modelo residente en ambos canales.
- La repetición same-prompt produjo el mismo output hash por canal, pero una sola
  repetición no establece determinismo general.
- Todos los resultados conservan `PENDIENTE_VALIDACION`; el éxito mecánico no
  reemplaza revisión humana.

## Próximo gate

Corresponde ampliar la matriz a más entradas sintéticas y ejecutar el checklist
humano. Cualquier política definitiva de tono, hashtags o canal debe provenir de
la SEU. No hace falta repetir este mismo caso hasta acumular verdes: la evidencia
útil siguiente debe ampliar cobertura o validar calidad.

## Límites

- Los datos son sintéticos.
- Sólo se usaron dos registros.
- No existe validación SEU.
- Las políticas y el catálogo son provisionales.
- Las latencias no son un SLA.
- Esta evidencia no habilita declarar HU-011 completa, Gate G2 ni TRL 3.
