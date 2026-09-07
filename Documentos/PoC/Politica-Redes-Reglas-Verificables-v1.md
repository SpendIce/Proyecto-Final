# Política de redes convertida en reglas verificables — HU-011

- **Fecha:** 2026-08-26
- **Proceso BPM:** P4 — Comunicación y Difusión Institucional
- **HU:** HU-011
- **Defecto asociado:** `DEF-A1-007`
- **Estado:** `PROVISIONAL_NO_INSTITUCIONAL`
- **Artefacto:** `Implementacion/Agente1/src/agente1/politicas/politica_redes_provisional_v1.json`
- **Regresión:** `Implementacion/Agente1/tests/test_politica_redes.py`
- **Clasificación:** reglas técnicas provisionales, sin aprobación editorial de la SEU ni datos personales o secretos.

## 1. Problema que resuelve

Hasta este corte la política de redes vivía en tres lugares que podían
contradecirse sin que nada lo detectara: valores fijos en el código, texto
declarativo en los prompts y pedidos en prosa dentro de la nota a la SEU. El
caso más claro era el prompt de LinkedIn, que exigía «sin emojis, sin
exclamaciones y sin lenguaje publicitario» sin que ningún control verificara
ninguna de las tres cosas.

Este incremento convierte la política en un artefacto único, versionado y
parametrizado, del que se derivan a la vez los límites que aplica el gate, los
límites que se le informan al modelo en el prompt y el inventario de lo que
todavía falta definir.

## 2. Qué significa «verificable» acá

Cada regla declara una de tres aplicaciones, y ninguna se puede confundir con
otra:

| Aplicación | Significado | Efecto en la suite |
|---|---|---|
| `ACTIVA` | El gate la aplica y hay un caso negativo que la observa | Debe existir regresión que produzca su código de validación |
| `NO_APLICADA_PENDIENTE_SEU` | La regla está identificada pero el criterio institucional no existe | No puede declarar código de gate ni presentarse como cumplida |
| `NO_MECANIZABLE` | Requiere juicio editorial humano | Queda explícita como límite del control automático |

La prueba `test_toda_regla_activa_tiene_caso_negativo_de_regresion` cierra el
circuito: agregar una regla `ACTIVA` al artefacto sin su caso negativo hace
fallar la suite. Es decir, no se puede declarar una política cumplida sin
demostrarla.

## 3. Inventario de reglas

### 3.1 Reglas aplicadas y verificadas

| ID | Dimensión | Regla | Código de validación | Punto de la nota SEU |
|---|---|---|---|---|
| `RED-EXT-01` | Extensión | Texto renderizado + hashtags ≤ `max_chars` del canal | `length_out_of_range` | 4.1.1 |
| `RED-EXT-02` | Extensión | Gancho, prosa y CTA dentro de los límites del contrato creativo | `creative_field_invalid` | 4.1.1 |
| `RED-HTG-01` | Hashtags | Cantidad entre `min_hashtags` y `max_hashtags` | `hashtag_count_out_of_range` | 4.1.2 |
| `RED-HTG-02` | Hashtags | Sólo etiquetas de la allowlist provisional | `hashtag_not_in_provisional_safety_allowlist` | 4.1.3 |
| `RED-HTG-03` | Hashtags | Sin repeticiones, tampoco por capitalización | `hashtag_duplicate` | 4.1.2 |
| `RED-HTG-04` | Hashtags | Forma válida de etiqueta | `hashtag_invalid` | 4.1.2 |
| `RED-REG-01` | Registro | Rechazo de tuteo explícito | `non_rioplatense_register` | 4.1.4 |
| `RED-TON-01` | Tono | Sin léxico promocional ni de urgencia comercial | `unauthorized_promotional_language` | 4.1.5 |
| `RED-TON-02` | Tono | Exclamaciones ≤ `max_exclamaciones` del canal | `unauthorized_exclamation` | 4.1.5 |
| `RED-EMO-01` | Emojis | Emojis ≤ `max_emojis` del canal | `unauthorized_emoji` | 4.1.6 |
| `RED-CTA-01` | CTA | Sin prometer inscripción, registro, reserva, compra ni agenda | `unauthorized_call_to_action` | 4.1.7 |
| `RED-CTA-02` | CTA | Sin afirmar aprobación, publicación, envío ni validación | `unauthorized_action_claim` | 4.1.7 |
| `RED-ALC-01` | Alcance | Sólo canales soportados; el resto se rechaza antes del modelo | `channel_not_allowed` | 4.1 |
| `RED-ALC-02` | Alcance | `reel` fuera de alcance: A1 no genera video, audio ni guion | `channel_not_allowed` | 4.1 |

Las tres reglas nuevas de este corte son `RED-TON-01`, `RED-TON-02` y
`RED-EMO-01`: existían como enunciado en el prompt y ahora existen como
control.

### 3.2 Reglas identificadas que la SEU debe definir

| ID | Dimensión | Qué falta | Punto de la nota SEU |
|---|---|---|---|
| `RED-EXT-03` | Extensión | Extensión diferenciada por canal. Hoy Instagram y LinkedIn comparten 1.000 caracteres, lo que evidencia un marcador de posición | 4.1.1 |
| `RED-HTG-05` | Hashtags | Etiquetas institucionales reales que reemplacen a las cuatro genéricas provisionales | 4.1.3 |
| `RED-REG-02` | Registro | Decisión entre voseo rioplatense, tuteo neutro o tercera persona | 4.1.4 |
| `RED-TON-03` | Tono | Adecuación editorial del tono por canal. `NO_MECANIZABLE`: ningún control léxico la reemplaza | 4.1.5 |
| `RED-CTA-03` | CTA | CTA admisible cuando exista circuito de inscripción, y su destino autorizado | 4.1.7 y consulta 5.1 |
| `RED-ALC-03` | Alcance | Si la SEU requiere apoyo para reels, qué producto textual corresponde y con qué validación | 4.1 |

## 4. Parámetros vigentes por canal

| Parámetro | Instagram | LinkedIn | Origen |
|---|---:|---:|---|
| `max_chars` | 1000 | 1000 | Equipo técnico, provisional |
| `min_hashtags` | 1 | 1 | Equipo técnico, provisional |
| `max_hashtags` | 10 | 10 | Equipo técnico, provisional |
| `max_emojis` | 3 | 0 | Equipo técnico, derivado del tono declarado en cada prompt |
| `max_exclamaciones` | 2 | 0 | Equipo técnico, derivado del tono declarado en cada prompt |

Los valores de emojis y exclamaciones son los primeros parámetros que **sí**
diferencian los canales entre sí. Los tres primeros siguen siendo idénticos, y
esa igualdad es exactamente la evidencia de que falta criterio editorial.

## 5. Reel: qué se decidió y qué no

La SEU informó un mínimo de un reel mensual. A1 no produce video, audio ni
guion audiovisual, de modo que el reel no es un canal soportado: una solicitud
con ese canal termina `INVALIDA` antes de invocar al modelo, con
`channel_not_allowed`. Esto no es una limitación transitoria de implementación
sino una declaración de alcance (`RED-ALC-02`), y por eso el reel tampoco entra
en el cálculo de capacidad.

Lo que queda abierto (`RED-ALC-03`) es si la SEU espera algún apoyo textual de
A1 para reels —por ejemplo un guion o un copy de acompañamiento—; en ese caso
haría falta definir el producto y su circuito de validación antes de
implementar nada.

## 6. Límite de esta entrega

Ningún valor de este artefacto fue aprobado por la SEU. Un control mecánico en
verde significa que la salida respeta un parámetro provisional del equipo
técnico, no que sea adecuada para comunicación institucional. `RED-TON-03`
existe justamente para dejar constancia de que la adecuación editorial requiere
revisión humana registrada, que sigue `PENDIENTE` en `DEF-A1-005`.

Cuando la SEU responda el punto 4.1 de la nota, el cambio es de datos y no de
arquitectura: se actualizan los parámetros y las aplicaciones en el artefacto,
las reglas que hoy están pendientes pasan a `ACTIVA` con su caso negativo, y la
suite verifica el resultado.
