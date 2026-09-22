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
| `RED-EXT-03` | Extensión | `CONFIRMADO_SEU` 22/09: «sin límite» editorial en ambos canales; el gate conserva `max_chars` como techo técnico interno | `length_out_of_range` | 4.1.1 |
| `RED-HTG-01` | Hashtags | Cantidad entre `min_hashtags` y `max_hashtags` | `hashtag_count_out_of_range` | 4.1.2 |
| `RED-HTG-02` | Hashtags | Sólo etiquetas de la allowlist provisional | `hashtag_not_in_provisional_safety_allowlist` | 4.1.3 |
| `RED-HTG-03` | Hashtags | Sin repeticiones, tampoco por capitalización | `hashtag_duplicate` | 4.1.2 |
| `RED-HTG-04` | Hashtags | Forma válida de etiqueta | `hashtag_invalid` | 4.1.2 |
| `RED-HTG-05` | Hashtags | `CONFIRMADO_SEU` 22/09: allowlist institucional `#FIE #UNDEF #Ingenieria #Cursos #inscripciones`; IG máx. 5, LI sin tope editorial (techo técnico 10) | `hashtag_not_in_provisional_safety_allowlist` | 4.1.3 |
| `RED-REG-01` | Registro | Rechazo de tuteo explícito | `non_rioplatense_register` | 4.1.4 |
| `RED-REG-02` | Registro | `CONFIRMADO_SEU` 22/09: voseo aceptable; el gate rechaza tuteo peninsular o neutro y admite formas como «enterate» o «animate» | `non_rioplatense_register` | 4.1.4 |
| `RED-TON-01` | Tono | Sin léxico promocional ni de urgencia comercial | `unauthorized_promotional_language` | 4.1.5 |
| `RED-TON-02` | Tono | Exclamaciones ≤ `max_exclamaciones` del canal | `unauthorized_exclamation` | 4.1.5 |
| `RED-EMO-01` | Emojis | Emojis ≤ `max_emojis` del canal | `unauthorized_emoji` | 4.1.6 |
| `RED-CTA-01` | CTA | Sin prometer inscripción, registro, reserva, compra ni agenda | `unauthorized_call_to_action` | 4.1.7 |
| `RED-CTA-02` | CTA | Sin afirmar aprobación, publicación, envío ni validación | `unauthorized_action_claim` | 4.1.7 |
| `RED-ALC-01` | Alcance | Sólo canales soportados; el resto se rechaza antes del modelo | `channel_not_allowed` | 4.1 |
| `RED-ALC-02` | Alcance | `reel` fuera de alcance: A1 no genera video, audio ni guion | `channel_not_allowed` | 4.1 |

Las tres reglas nuevas del corte original son `RED-TON-01`, `RED-TON-02` y
`RED-EMO-01`: existían como enunciado en el prompt y ahora existen como
control. Del incremento del 22/09 pasaron a `ACTIVA` con su caso negativo
`RED-EXT-03`, `RED-HTG-05` y `RED-REG-02`, implementando los valores
confirmados por la SEU.

### 3.2 Reglas confirmadas no mecanizables o aún pendientes

| ID | Dimensión | Estado | Punto de la nota SEU |
|---|---|---|---|
| `RED-TON-03` | Tono | `CONFIRMADO_SEU` 22/09: académico en ambos canales, IG con audiencia diferenciada (profesionales en cursos/congresos, más joven en carreras) y LI orientado a público más profesional sin diferenciación fuerte entre plataformas. `NO_MECANIZABLE`: ningún control léxico la reemplaza; se materializa en el prompt v4 y queda a la revisión humana | 4.1.5 |
| `RED-CTA-03` | CTA | `CONFIRMADO_SEU` 22/09: IG link en el perfil, LI link en el post. `NO_MECANIZABLE` como regla general, pero en el contrato cerrado v2 se materializa en el catálogo (`post_creative_catalog_v3`) con CTAs distintos por canal | 4.1.7 y consulta 5.1 |
| `RED-ALC-03` | Alcance | Si la SEU requiere apoyo para reels, qué producto textual corresponde y con qué validación. **No se consultó el 22/09**: sigue abierto y fuera de alcance por `RED-ALC-02` | 4.1 |

Las respuestas del 22/09 provienen del acta de la reunión con el referente
designado (`Validacion-SEU/reunion-seu-2026-09-22.json`, consolidado en
`Respuestas-SEU-Reunion-2026-09-22.md`) y cuentan como `CONFIRMADO_SEU`.

## 4. Parámetros vigentes por canal

| Parámetro | Instagram | LinkedIn | Origen |
|---|---:|---:|---|
| `max_chars` | 1000 | 1000 | Techo técnico interno; editorialmente la SEU confirmó «sin límite» (`RED-EXT-03`) |
| `min_hashtags` | 1 | 1 | Equipo técnico, provisional |
| `max_hashtags` | 5 | 10 | IG: `CONFIRMADO_SEU` 22/09 (máx. 5). LI: techo técnico interno; editorialmente sin tope (`RED-HTG-05`) |
| `max_emojis` | 3 | 0 | IG: `CONFIRMADO_SEU` 22/09 («casi nunca», para datos puntuales). LI: derivado del tono confirmado |
| `max_exclamaciones` | 2 | 0 | Equipo técnico, derivado del tono declarado en cada prompt |

`max_hashtags` es el primer parámetro que diferencia los canales con origen
institucional: el 5 de Instagram es criterio confirmado y el 10 de LinkedIn
es sólo un techo técnico, no un límite editorial definido por la SEU.

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

Varios valores ya provienen de la SEU (hashtags, extensión editorial, voseo,
tono, ubicación del CTA), pero el criterio editorial aplicado —el tono real de
una pieza concreta— no lo verifica ningún control: un control mecánico en
verde significa que la salida respeta el parámetro, no que sea adecuada para
comunicación institucional. `RED-TON-03` existe justamente para dejar
constancia de que la adecuación editorial requiere revisión humana registrada,
que sigue `PENDIENTE` en `DEF-A1-005`.
