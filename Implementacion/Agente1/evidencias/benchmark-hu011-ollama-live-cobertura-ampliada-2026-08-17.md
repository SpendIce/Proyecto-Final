# Benchmark live HU-011 v4 — cobertura ampliada — 2026-08-17

## Propósito

El corte `HU011-OLLAMA-JSON-SCHEMA-V4-20260817-001` cerró con 6/6 aceptaciones
técnicas sobre **dos** registros y sin casos negativos live. Su propia sección
«Próximo gate» indicaba que la evidencia útil siguiente debía **ampliar
cobertura**, no acumular verdes del mismo caso.

Este corte amplía a las **cinco actividades sintéticas en ambos canales**: tres
completas con generación live y dos incompletas que deben rechazarse antes de
invocar al modelo. Además ejecuta la suite completa fuera del sandbox, que era
el bloqueo declarado en `DEF-A1-009`.

No prueba calidad institucional, SLA, validación SEU ni TRL 3.

## Configuración controlada

| Componente | Valor |
| --- | --- |
| Evidencia | `HU011-OLLAMA-JSON-SCHEMA-V4-COBERTURA-AMPLIADA` |
| Baseline inmediato | `HU011-OLLAMA-JSON-SCHEMA-V4-20260817-001` |
| Runtime | Ollama user-local, loopback, CPU |
| Modelo | `llama3.2:3b` |
| Formato | `json_schema` |
| Hash canónico del schema | `87db650e883b7b2d2f30f210c052d53b9d30d78b87539ceb7b9b314a3fd8bc7f` |
| Temperatura | 0 |
| Timeout | 120 segundos |
| Presupuesto de salida | 112 tokens |
| Runner | `scripts/matriz_hu011_live_v4.py` |

El hash canónico del schema coincide con el del corte v4 anterior: es el mismo
contrato, no una variante relajada.

## Método

Cinco actividades × dos canales = diez ejecuciones. Las tres actividades
completas invocan Ollama con constrained decoding. Las dos incompletas reciben
un generador centinela que lanza excepción si es invocado: si el rechazo previo
fallara, el caso no podría cerrar en `INCOMPLETA`.

A diferencia de la matriz fake, el runner **no aborta ante una salida no
conforme**: registra el resultado observado. El objetivo es medir la tasa real
de conformidad, no ocultarla detrás de un fallo temprano.

## Resultados

| Actividad | Canal | Estado | Latencia | Output hash |
| --- | --- | --- | ---: | --- |
| SYN-001 | Instagram | `PENDIENTE_VALIDACION` | 36,225976 s | `7e817974` |
| SYN-001 | LinkedIn | `PENDIENTE_VALIDACION` | 27,608707 s | `b2d13f18` |
| SYN-002 | Instagram | `INCOMPLETA` | 0,000833 s | — |
| SYN-002 | LinkedIn | `INCOMPLETA` | 0,000538 s | — |
| SYN-003 | Instagram | `PENDIENTE_VALIDACION` | 11,496097 s | `de60df5b` |
| SYN-003 | LinkedIn | `PENDIENTE_VALIDACION` | 11,948116 s | `8731ef8a` |
| SYN-004 | Instagram | `INCOMPLETA` | 0,000827 s | — |
| SYN-004 | LinkedIn | `INCOMPLETA` | 0,000673 s | — |
| SYN-005 | Instagram | `PENDIENTE_VALIDACION` | 9,463110 s | `9237ad33` |
| SYN-005 | LinkedIn | `PENDIENTE_VALIDACION` | 9,922306 s | `044c7de7` |

Resumen:

- seis generaciones live aceptadas de seis;
- cuatro casos negativos conformes de cuatro, sin invocar al modelo;
- seis borradores persistidos, todos en `PENDIENTE_VALIDACION`;
- cero timeouts, errores de transporte o salidas no conformes.

## Reproducibilidad entre corridas independientes

Los cuatro casos compartidos con el corte v4 anterior reprodujeron **el mismo
output hash** en una corrida independiente y posterior:

| Caso | v4 anterior | Este corte | Coincide |
| --- | --- | --- | --- |
| SYN-001 / Instagram | `7e817974…6bb2` | `7e817974` | sí |
| SYN-001 / LinkedIn | `b2d13f18…0bd0` | `b2d13f18` | sí |
| SYN-003 / Instagram | `de60df5b…5b37` | `de60df5b` | sí |
| SYN-003 / LinkedIn | `8731ef8a…0c0b` | `8731ef8a` | sí |

El corte anterior sólo podía afirmar coincidencia entre una repetición
inmediata del mismo prompt dentro de la misma sesión, y declaraba explícitamente
que eso no establecía determinismo general. Esta es la primera evidencia de
reproducibilidad **entre sesiones separadas**, con el modelo recargado en frío.

Sigue sin ser determinismo demostrado en el caso general: son cuatro casos, un
modelo, un host y temperatura 0 con un schema de enum cerrado. El espacio de
salida está deliberadamente restringido a un catálogo, de modo que la
reproducibilidad observada es consistente con el diseño y no debe extrapolarse a
prompts abiertos.

### Lectura inversa: la misma evidencia muestra una limitación grave

Esta reproducibilidad **no debe leerse sólo como una fortaleza**. Los mismos
datos muestran que el modelo no discrimina entre entradas distintas:

| Canal | Actividades distintas | Combinaciones creativas observadas |
| --- | ---: | ---: |
| Instagram | 3 (SYN-001, SYN-003, SYN-005) | **1** |
| LinkedIn | 3 (SYN-001, SYN-003, SYN-005) | **1** |

Las tres actividades produjeron el mismo gancho, la misma prosa, el mismo CTA y
los cuatro hashtags completos en cada canal. El catálogo por canal admite ocho
combinaciones y se utilizó una sola.

A temperatura 0 sobre un enum, el modelo se comporta como **función constante**:
un selector aleatorio produciría más variedad en 0,001 s en lugar de 36 s de
inferencia. Las 6/6 aceptaciones miden conformidad de transporte y contrato,
**no aptitud comunicacional**. Registrado como `DEF-A1-011`.

El enum se introdujo en v4 para resolver el HTTP 400 de compilación de grammar
observado en v3, es decir un problema de **transporte**. La protección contra
invención de hechos no depende de él: la aportan el renderer determinista, que
agrega los hechos por código fuera de la salida del modelo, y el gate de
`_validar_render_estructurado`, que rechaza fechas, dígitos, correos, URLs,
importes, lugares, atribuciones factuales y ecos de inyección en el texto
creativo. El enum no puede presentarse como la solución creativa definitiva.

## Latencia

| Condición | Rango observado |
| --- | ---: |
| Generación live, model cold | 27,608707 – 36,225976 s |
| Generación live, modelo residente | 9,463110 – 11,948116 s |
| Rechazo previo sin invocar al modelo | 0,000538 – 0,000833 s |

El máximo cold de **36,225976 s** supera el máximo de 29,485820 s registrado en
el corte v4 anterior sobre el mismo host y modelo. Esto refuerza `DEF-A1-003`:
la dispersión cold no está acotada y el presupuesto por defecto de 45 segundos
de la CLI queda con menos margen del que sugería la evidencia previa. No se
modifica ningún umbral en este corte; se registra el dato.

Las latencias corresponden a un host CPU concreto sin GPU y **no constituyen un
SLA**.

## Estado de la suite

La suite completa se ejecutó fuera del sandbox: **437 pruebas, 436 verdes y cero
fallas de loopback `EPERM`**. Las 16 fallas `EPERM` registradas previamente eran
ambientales del sandbox y no se reprodujeron.

La única falla restante es `test_packaging.py::test_readme_descubre_incrementos_actuales_y_no_promete_wheel_o_trabajo_ya_hecho`,
que exige que el README declare las migraciones como artefactos versionados del
repositorio. `git ls-files migrations/` confirma que todavía **no** lo están: el
README dice la verdad y el test se anticipa al commit atómico pendiente. No se
debilitó el test ni se alteró el README para forzar el verde.

## Límites

- Los datos son sintéticos y las políticas de canal son provisionales.
- Tres actividades y dos canales no acreditan estabilidad amplia.
- El gate mecánico no evalúa tono, verdad semántica ni pertinencia institucional.
- No existe validación SEU ni revisión humana registrada sobre estos borradores.
- No se invocaron APIs de redes sociales ni se publicó contenido.
- Esta evidencia no habilita declarar HU-011 completa, el Gate G2 ni TRL 3.
