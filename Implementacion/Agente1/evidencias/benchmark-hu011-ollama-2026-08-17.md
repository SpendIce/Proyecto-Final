# Benchmark local Ollama HU-011 — 2026-08-17

## Propósito y alcance

Este documento registra la ejecución técnica local de HU-011 para borradores de
Instagram y LinkedIn con `llama3.2:3b`. Los insumos fueron sintéticos, las
políticas de canal siguen marcadas como `PROVISIONAL_NO_INSTITUCIONAL` y ninguna
salida fue publicada.

El resultado es **NO CONFORME**: el runtime respondió en los seis intentos, pero
ninguna respuesta superó el contrato técnico y, por diseño, no se generó ningún
borrador. Esto demuestra que el fail-closed funciona frente a una salida del
modelo que omite o altera hechos; no demuestra calidad institucional, aprobación
SEU ni TRL 3.

## Entorno observado

| Componente | Valor |
| --- | --- |
| Runtime | Ollama `0.32.14-1`, paquete Arch firmado y runtime user-local aislado |
| CPU | Intel Core i7-1180G7, 4 núcleos y 8 hilos |
| Memoria | 15 GiB de RAM |
| Backend | CPU; no se utilizó GPU |
| Modelo | `llama3.2:3b`, GGUF Q4_K_M |
| Historia y canales | HU-011 — Instagram y LinkedIn |
| Datos | `SYN-001` y `SYN-003`, origen simulado |
| Límite por generación | 120 s y 112 tokens |

Los hashes del runtime, modelo, prompts, contrato, pipeline y dataset se
conservan en el manifest de evidencia `HU011-OLLAMA-20260817-001`. No se
versionan prompts renderizados, cuerpos rechazados, contactos, secretos ni
rutas del host o del repositorio.

El pipeline coincidía con el base commit `22b54740e` **al momento de la
captura**. Después se modificó el procesador para incorporar una allowlist de
errores Drive; Ollama no se volvió a ejecutar. Por eso esta evidencia no afirma
coincidencia con el worktree posterior y conserva los hashes históricos del
pipeline realmente evaluado.

## Método y límite de intentos

Se fijó antes de ejecutar un máximo de **seis generaciones, sin reintentos
automáticos**: tres condiciones por canal.

1. `model-cold-prompt-cold`: se descargó el modelo de memoria mediante
   `ollama stop` antes de la corrida.
2. `model-resident-prompt-cold`: con el modelo ya residente se cambió de
   `SYN-001` a `SYN-003`, generando un prompt diferente.
3. `same-prompt-warm`: se repitió inmediatamente el mismo canal y `SYN-003`.

No se aumentó el presupuesto ni se repitieron intentos después del resultado:
hacerlo sin una hipótesis y un cambio controlado habría ocultado la falta de
conformidad del baseline.

## Resultados

| Canal | Condición | Latencia | Estado | Motivos principales |
| --- | --- | ---: | --- | --- |
| Instagram | model cold + prompt cold | 29,232839 s | `FALLIDA` | omitió título, fecha, organización, contacto y lugar |
| Instagram | modelo residente + prompt cold | 14,441819 s | `FALLIDA` | omitió fecha y contacto e introdujo un número no autorizado |
| Instagram | mismo prompt warm | 5,667962 s | `FALLIDA` | omitió fecha, organización y contacto |
| LinkedIn | model cold + prompt cold | 29,629090 s | `FALLIDA` | omitió fecha y contacto e introdujo un número no autorizado |
| LinkedIn | modelo residente + prompt cold | 13,133735 s | `FALLIDA` | omitió fecha y contacto e introdujo un número no autorizado |
| LinkedIn | mismo prompt warm | 15,358180 s | `FALLIDA` | omitió fecha y contacto e introdujo un número no autorizado |

No hubo timeouts ni errores de transporte. Hubo **cero salidas aceptadas de
seis** y **seis salidas rechazadas de seis** como `salida_no_conforme`. Las
correlation IDs y los códigos completos están en el manifest.

## Lectura técnica

- La instalación local y el adapter HTTP fueron operables en ambos canales.
- El estado warm redujo marcadamente la latencia en Instagram, pero no volvió
  conforme la respuesta. En LinkedIn tampoco produjo una mejora consistente.
- El modelo 3B con este prompt y presupuesto no preservó de manera confiable los
  hechos literales obligatorios.
- El gate actuó correctamente: no guardó borradores cuando faltaban hechos o
  aparecía un número ajeno a la fuente.

La conclusión NO es “HU-011 funciona con Ollama”. La conclusión correcta es:
**el transporte local funciona y el control fail-closed contiene las salidas no
conformes, pero el baseline generativo real todavía no produce un borrador
aceptable**.

## Próximo experimento controlado

Antes de volver a ejecutar conviene definir un único cambio medible, por ejemplo:

1. respuesta estructurada con campos separados y render determinista; o
2. un prompt revisado que obligue a copiar primero los hechos requeridos; o
3. comparar un modelo local distinto bajo el mismo contrato y dataset.

Cada alternativa debe mantener el mismo gate, fijar de antemano el número de
intentos y registrar tanto aceptaciones como rechazos. Aumentar tokens y repetir
hasta obtener un verde no constituye evidencia reproducible.

## Limitaciones y estado institucional

- Los datos fueron exclusivamente sintéticos.
- La conformidad estructural no equivale a tono o calidad institucional.
- No hubo salida aceptada que pudiera pasar al checklist humano.
- No existe validación de responsables de la SEU.
- Las políticas de Instagram y LinkedIn no están aprobadas institucionalmente.
- Las latencias observadas corresponden a este host y no constituyen un SLA.
- Esta evidencia **no habilita declarar HU-011 completa, Gate G2 ni TRL 3**.
