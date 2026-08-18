# Benchmark local Ollama HU-011 structured v2 — 2026-08-17

## Propósito y alcance

Este documento registra un experimento nuevo sobre el flujo seguro structured
v2 de HU-011 para Instagram y LinkedIn. El modelo debía producir únicamente la
selección creativa JSON; los hechos institucionales quedaban reservados al
renderer determinista.

El resultado fue **NO CONFORME**: las seis respuestas fueron rechazadas como
`json_invalid`. No se creó ningún borrador y el renderer final no recibió una
selección creativa aceptada. Esto verifica el comportamiento fail-closed, pero
no demuestra viabilidad generativa de structured v2 con este presupuesto.

## Configuración fijada antes de ejecutar

| Componente | Valor |
| --- | --- |
| Evidencia | `HU011-OLLAMA-STRUCTURED-V2-20260817-001` |
| Runtime | Ollama `0.32.14-1`, user-local y limitado a loopback |
| Backend | CPU, sin GPU |
| Modelo | `llama3.2:3b`, GGUF Q4_K_M |
| Entrada | `post_input_v1` |
| Salida creativa | `post_creative_output_v2` |
| Renderer | `post_deterministic_renderer_v2` |
| Catálogo | `post_creative_catalog_v2` |
| Datos | `SYN-001` y `SYN-003`, origen simulado |
| Deadline total | 120 segundos |
| Presupuesto de salida | 112 tokens |
| Intentos | seis, sin reintentos automáticos |

El deadline de 120 segundos evita convertir el costo cold observado previamente
en un corte artificial y coincide con el máximo admitido por el adapter. Los
112 tokens mantienen comparabilidad con el baseline v1 y parecían razonables
para un objeto creativo menor que una pieza completa. Son parámetros de este
experimento, no umbrales institucionales ni una afirmación de suficiencia.

Structured v2 aún no estaba integrado al base commit al iniciar el experimento.
Por eso los componentes se identificaron mediante hashes capturados antes de la
primera generación y verificados nuevamente después de la sexta. Permanecieron
sin cambios durante toda la captura.

## Método

Por cada canal se ejecutaron exactamente tres condiciones:

1. `model-cold-prompt-cold`: descarga explícita del modelo de memoria antes de
   la generación con `SYN-001`.
2. `model-resident-prompt-cold`: modelo residente y prompt distinto mediante
   `SYN-003`.
3. `same-prompt-warm`: repetición inmediata del mismo canal y `SYN-003`.

Se alcanzó el límite predefinido de seis intentos. No se cambió el presupuesto
ni se repitieron generaciones para buscar un resultado verde.

## Resultados

| Canal | Condición | Latencia | Estado | Código | Borradores |
| --- | --- | ---: | --- | --- | ---: |
| Instagram | model cold y prompt cold | 42,836248 s | `FALLIDA` | `json_invalid` | 0 |
| Instagram | modelo residente y prompt cold | 18,381072 s | `FALLIDA` | `json_invalid` | 0 |
| Instagram | mismo prompt warm | 14,130929 s | `FALLIDA` | `json_invalid` | 0 |
| LinkedIn | model cold y prompt cold | 37,958424 s | `FALLIDA` | `json_invalid` | 0 |
| LinkedIn | modelo residente y prompt cold | 18,442998 s | `FALLIDA` | `json_invalid` | 0 |
| LinkedIn | mismo prompt warm | 13,932053 s | `FALLIDA` | `json_invalid` | 0 |

Resumen:

- cero salidas aceptadas de seis;
- seis salidas rechazadas de seis;
- cero timeouts y cero errores de transporte;
- cero borradores inválidos persistidos;
- cero outputs aceptados con hash, porque ningún borrador atravesó el gate.

Las correlation IDs, versiones y hashes opacos se conservan en el manifest de
evidencia asociado. No se incluyen prompts renderizados, respuestas rechazadas,
contactos, secretos ni rutas del host o del repositorio.

## Lectura técnica

- El transporte local volvió a responder en ambos canales y condiciones.
- La caché redujo latencia respecto del estado cold, pero no produjo JSON
  aceptable.
- Structured v2 contuvo el problema: el modelo no puede introducir hechos en un
  borrador si su selección creativa no supera primero el contrato.
- El renderer está versionado y configurado, pero estas corridas no prueban su
  salida live porque ninguna respuesta llegó a esa etapa.

La conclusión correcta es: **structured v2 mejora la frontera de seguridad,
pero `llama3.2:3b` con 112 tokens no produjo JSON aceptable en este corte**.

## Próximo experimento controlado

El siguiente intento debe cambiar una sola variable y volver a fijar el límite
antes de ejecutar. Las alternativas más defendibles son:

1. usar una capacidad nativa de salida JSON en el adapter, manteniendo modelo,
   prompts, dataset y presupuesto; o
2. aumentar únicamente `num_predict`, manteniendo los demás componentes y
   verificando si `json_invalid` provenía de una respuesta incompleta.

No corresponde elegir una explicación sin capturar de manera segura el motivo
de terminación. Tampoco corresponde repetir hasta obtener un verde.

## Límites institucionales

- Los datos son sintéticos.
- No hubo borrador aceptado para evaluación humana.
- No existe validación SEU.
- Las políticas de canal y el catálogo creativo son provisionales.
- Las latencias no constituyen un SLA.
- Esta evidencia no habilita declarar HU-011 completa, Gate G2 ni TRL 3.
