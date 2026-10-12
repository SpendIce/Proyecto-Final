# Medición HU-011 v3: comparación de modelos locales

- **Fecha:** 2026-09-23
- **Entorno:** local controlado, CPU (sin GPU dedicada), Ollama loopback,
  `temperature=0`, `num_predict=512`, `json_schema`, `--variante-prompt
  baseline`, reintento del pipeline activo.
- **Alcance:** verificar si la brecha de obediencia del contrato v3 (1/6 con
  `llama3.2:3b`) se reduce con los modelos de la clase que la infraestructura
  P100 prevé (la biblio define LLaMA 3 8B / Mistral 7B). No es validación
  SEU ni medición de calidad editorial.

## 1. Resultado por modelo

Misma matriz, mismos parámetros, mismo gate. Un intento por caso más el
reintento con feedback del pipeline (#37).

| Modelo | Aceptadas | Casos negativos conformes | Latencia por generación (CPU) |
|---|---|---|---|
| `llama3.2:3b` (dev) | 1/6 | 4/4 | 26–111 s |
| `llama3.1:8b` | **4/6** | 4/4 | 40–160 s |
| `mistral:7b` | **0/6** | 4/4 | 116–240 s |

Evidencias: `salida/medicion-v3-llama31-8b-2026-09-23/medicion-v3.json`
(`HU011-V3-LLAMA31-8B-2026-09-23`) y
`salida/medicion-v3-mistral7b-2026-09-23/medicion-v3.json`
(`HU011-V3-MISTRAL7B-2026-09-23`).

## 2. Detalle llama3.1:8b

| Caso | Canal | Intentos | Resultado | Errores del intento terminal |
|---|---|---|---|---|
| SYN-001 | instagram | 2 | FALLIDA | `unauthorized_place`, `non_rioplatense_register` |
| SYN-001 | linkedin | 1 | PENDIENTE_VALIDACION | — |
| SYN-003 | instagram | 1 | PENDIENTE_VALIDACION | — |
| SYN-003 | linkedin | 1 | PENDIENTE_VALIDACION | — |
| SYN-005 | instagram | 2 | PENDIENTE_VALIDACION | — |
| SYN-005 | linkedin | 2 | FALLIDA | `unauthorized_fact_claim` |

Residuales: «en la universidad» (referencia a lugar genérico), «Descubre»
(tuteo en el segundo intento), «ofrece una oportunidad» (atribución).
El reintento con feedback funcionó por primera vez: SYN-005 instagram pasó
en el segundo intento; con el 3B nunca corrigió.

## 3. Detalle mistral:7b

0/6 — todos los casos fallaron. Conteo de códigos: `source_fact_in_creative_field`
6/6 (copia datos y palabras del título en todos), `non_rioplatense_register`
5/6, `unauthorized_emoji` 4/6 (emite emojis aun con límite cero en LinkedIn),
`unauthorized_fact_claim` 2, `unauthorized_exclamation` 2,
`unauthorized_number` 1, `unauthorized_place` 1. Peor que el modelo de
desarrollo de 3B.

## 4. Lectura

- **El tamaño ayuda pero no es la variable suficiente.** Entre dos modelos
  de la misma clase documentada (7-8B), uno cuadruplica la conformidad y el
  otro cae a cero. La conformidad depende del modelo concreto —entrenamiento
  de instrucción y competencia en español rioplatense—, no sólo del conteo
  de parámetros.
- **`llama3.1:8b` es el primer modelo que produce borradores conformes de
  forma mayoritaria en el camino de redacción libre.** Con el gate intacto,
  el 4/6 significa que la tasa de retrabajo humano baja de "casi todo se
  rechaza" a "la mitad o más llega usable al validador".
- **El residuo del 8B es de categorías suaves** (una referencia de lugar
  genérica, un tuteo, un verbo de atribución) — el tipo de desviación que el
  few-shot con ejemplos aprobados SEU (#14) está pensado para cerrar.
- **La conclusión se sostiene por medición, no por suposición:** la misma
  corrida que muestra la mejora de 8B muestra que mistral:7b empeora.
  Cambiar de modelo es una decisión que hay que medir antes de adoptarla.
- **Latencia:** en CPU el 8B tarda ~1,5-2,5x el 3B (40-160 s por
  generación). Para el volumen SEU (~36 generaciones/mes) sigue siendo
  irrelevante como costo; el benchmark de capacidad del 26/08 ya mostraba
  que la latencia no es el cuello de botella.

## 5. Alcance de esta evidencia

Datos sintéticos, una corrida por modelo y caso, CPU sin GPU. Nada acá
acredita conformidad editorial, validación SEU, Gate G2 ni TRL. La
infraestructura P100 prevista (servidor local, modelos livianos) sigue siendo
decisión de Dirección; esta medición informa esa decisión con datos.
