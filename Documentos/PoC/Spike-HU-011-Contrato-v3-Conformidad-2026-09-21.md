# Spike HU-011: diagnóstico de conformidad del contrato v3

- **Fecha:** 2026-09-21
- **Pregunta que responde:** por qué `post_creative_output_v2` (catálogo
  cerrado) acepta 6/6 y `post_creative_output_v3` (redacción libre) acepta
  0/6, en qué regla falla exactamente cada generación, con qué severidad, y
  qué opciones técnicas existen para llevar a la SEU.
- **Modo de ejecución:** live, contra `llama3.2:3b` en Ollama `0.32.14`
  user-local sobre CPU (loopback `127.0.0.1:11434`). El runtime se restauró en
  `.runtime/` del worktree (ignorado por Git) a partir del runtime user-local
  ya probado en el checkout principal; no se descargó ni instaló nada nuevo.
- **Datos:** `Implementacion/Agente1/data/actividades_sinteticas.csv`: cinco
  actividades sintéticas, tres completas y dos incompletas, sobre dos canales
  (`instagram`, `linkedin`). Ningún dato es real.
- **Qué no se tocó:** código de producción, contratos, prompts versionados ni
  `politica_redes_provisional_v1.json`. Las variaciones se hicieron por
  instrumentación: `Implementacion/Agente1/scripts/medir_conformidad_v3.py`
  replica el transporte del adapter con los parámetros abiertos
  (`temperature`, `num_predict`, `format`, bloques extra de prompt) y ejecuta
  el pipeline real `procesar_post_estructurado` sin modificarlo.
- **Límites:** ninguna salida se publicó ni compartió; toda aceptación queda
  `PENDIENTE_VALIDACION` con `BORRADOR — NO PUBLICAR`. Este spike mide
  conformidad mecánica y no acredita calidad editorial, validación SEU, Gate
  G2 ni TRL 3.

## 1. Reproducción de la falla

Se corrió la matriz oficial `scripts/matriz_hu011_live_v4.py` en este host:

| Contrato | Generaciones | Aceptadas | Negativos conformes | Resultado |
|---|---:|---:|---:|---|
| `post_creative_output_v2` (catálogo cerrado) | 6 | **6/6** | 4/4 | conforme |
| `post_creative_output_v3` (redacción libre) | 6 | **0/6** | 4/4 | NO_CONFORME |

La corrida v3 reprodujo el corte 2026-09-08 **código por código en los seis
casos**: cada caso obtuvo exactamente los mismos `validation_errors` que
`evidencias/manifest-hu011-live-v3-2026-09-08.json`. La brecha es estable y
reproducible, no una fluctuación del runtime.

Latencias v3 en esta corrida: 23,6 a 63,8 s por generación (las dos primeras
incluyen carga del modelo en frío).

## 2. Clasificación de fallos por categoría y por regla

Códigos observados en la baseline v3 (6 generaciones), con su categoría
estructural y su regla del artefacto de política cuando existe:

| Código del gate | Categoría | Regla de política | Casos afectados |
|---|---|---|---:|
| `source_fact_in_creative_field` | gate de hechos | (sin RED-*; es el gate de grounding) | **6/6** |
| `non_rioplatense_register` | política de redes | `RED-REG-01` | **5/6** |
| `unauthorized_exclamation` | política de redes | `RED-TON-02` | 2/6 |
| `unauthorized_fact_claim` | gate de hechos | (patrón `PATRON_HECHO_CREATIVO`) | 1/6 |

Detalle por caso (baseline v3, runner oficial y medidor coinciden):

| Caso | Canal | Errores | Literal que disparó el gate |
|---|---|---|---|
| SYN-001 | instagram | `source_fact`, `non_rioplatense` | fragmento del título: `taller`; tuteos: `Inscríbete`, `Únete` |
| SYN-001 | linkedin | `source_fact`, `non_rioplatense`, `unauthorized_exclamation` | fragmentos: `taller`, `sintético`; campo `publico` completo; tuteo: `Inscríbete`, `Únete` |
| SYN-003 | instagram | `source_fact`, `non_rioplatense` (+`unauthorized_exclamation` en una corrida) | fragmento: `jornada`; tuteo: `Únete` |
| SYN-003 | linkedin | `source_fact`, `non_rioplatense` | fragmento: `jornada`; tuteo: `Únete` |
| SYN-005 | instagram | `source_fact`, `non_rioplatense`, `unauthorized_fact_claim` | fragmentos: `seminario`, `remoto`, `sintético` (título completo en una corrida); tuteos: `Inscríbete`, `Únete`; hecho: `remoto` |
| SYN-005 | linkedin | `source_fact`, `non_rioplatense`, `unauthorized_fact_claim`, `unauthorized_exclamation` | fragmentos: `seminario`, `remoto`; tuteos: `Inscríbete`, `Únete`, `Participa`; hecho: `remoto` |

### Lectura por capa

- **Parseo: no es la causa.** Con `format=json_schema` las seis salidas fueron
  JSON válido con la forma del contrato; `done_reason=stop` en todas. El modo
  de falla `json_invalid` del corte 2026-08-26 era truncamiento por
  `num_predict=112`, ya cerrado en `DEF-A1-013`.
- **Presupuesto de decodificación: descartado.** Las seis respuestas emitieron
  entre 126 y 181 tokens (`eval_count`), muy por debajo de 512. Una corrida con
  `num_predict=1024` produjo respuestas **byte-idénticas**: el presupuesto es
  un tope que nunca se alcanzó, no una variable del resultado.
- **Gate de contenido: causa dominante.** `source_fact_in_creative_field`
  aparece en 6/6. El disparador concreto es `_contiene_fragmento_significativo`:
  el modelo escribe palabras de cinco o más letras del título (`taller`,
  `jornada`, `seminario`, `remoto`, `vinculación`, `sintético`) porque son los
  sustantivos de dominio naturales para referirse a la actividad. En
  SYN-001/linkedin además repitió el campo `publico` completo.
- **Política de redes: segunda causa.** `RED-REG-01` (tuteo) en 5/6 con los
  literales `Inscríbete`, `Únete`, `Participa`: formas que el prompt ya
  prohíbe por nombre y el modelo produce igual. `RED-TON-02` (exclamaciones)
  en 2/6: LinkedIn admite cero y el modelo usa `!`; Instagram admite dos y una
  salida usó tres.

Hay una regla dominante por capa (`source_fact` en gate de hechos, `RED-REG-01`
en política de redes), no dispersión: los errores restantes son cola.

## 3. Variaciones probadas y su efecto

Todas sobre el contrato v3 sin modificarlo, ejecutadas por
`medir_conformidad_v3.py` (salidas crudas en `salida/spike-medida-*/`, ignorado
por Git; resúmenes en `medicion-v3.json` de cada corrida). Las variantes de
prompt insertan un bloque extra antes de `DATOS_JSON_INICIO`:

- `voseo`: ejemplos concretos de imperativos rioplatenses permitidos
  (`sumate`, `participá`, `conocé`, `acercate`, `animáte`, `enterate`) más una
  lista ampliada de tuteos prohibidos y la indicación de preferir forma
  impersonal ante la duda.
- `antihechos`: recordatorio de que el sistema agrega título, fecha,
  organización, lugar y contacto por su cuenta, y que el texto no puede
  repetir ni una palabra de cinco o más letras del título.
- `voseo_antihechos`: ambos bloques.

| Corrida | Temp | num_predict | format | Variante | Aceptadas | Errores por código |
|---|---:|---:|---|---|---:|---|
| baseline | 0 | 512 | json_schema | base | 0/6 | `source_fact` 6, `non_riop` 5, `exclam` 2, `fact_claim` 2 |
| baseline | 0 | **1024** | json_schema | base | 0/6 | idéntico; respuestas byte-idénticas a 512 |
| baseline | **0,7** | 512 | json_schema | base, 2 reps | 0/12 | `non_riop` 11, `source_fact` 11, `exclam` 3, `fact_claim` 3, `number` 2, `place` 1 |
| prompt | 0 | 512 | json_schema | `voseo` | **1/6** | `source_fact` 5, `place` 2, `fact_claim` 1; **`non_riop` 0** |
| prompt | 0 | 512 | json_schema | `antihechos` | 0/6 | `non_riop` 6, `exclam` 3; **`source_fact` 1** |
| prompt | 0 | 512 | json_schema | `voseo_antihechos` | **3/6** | `source_fact` 3, resto 0 |
| prompt | 0 | 512 | json_schema | `voseo_antihechos`, 2 reps | **6/12** | `source_fact` 6, resto 0 (idéntico por caso entre reps) |
| formato | 0 | 512 | **none** | `voseo_antihechos` | 4/6 | `source_fact` 1, `json_invalid` 1, `creative_field` 1 |
| formato | 0 | 512 | **json** | `voseo_antihechos` | 3/6 | `source_fact` 3, `creative_field` 1 |
| combinada | **0,7** | 512 | json_schema | `voseo_antihechos`, 2 reps | 4/12 | `source_fact` 4, `exclam` 3, `non_riop` 2, `fact_claim` 1, `place` 1 |

Total: 90 generaciones live en el spike (78 del medidor más las 12 de las
matrices oficiales v2/v3 de la sección 1) y 48 ejecuciones de casos negativos,
todas conformes (`INCOMPLETA` sin invocar al modelo).

### Qué se aprende de cada variación

1. **`num_predict` mayor: nulo.** Las respuestas con 1024 son byte-idénticas;
  el modelo termina en ~130-180 tokens. El presupuesto queda descartado como
  variable del resultado.
2. **Temperatura mayor: empeora.** A 0,7 la tasa sigue en cero sobre el prompt
  vigente y aparecen errores nuevos (`unauthorized_number` por dígitos en el
  texto, `unauthorized_place` por "en el aula"). Sobre el prompt reforzado la
  tasa baja de 3/6 a 4/12 con dispersión residual: el muestreo agrega ruido,
  no conformidad.
3. **Bloque de voseo: resuelve `RED-REG-01` por completo a temp 0** (5/6 a
  0/6). El modelo responde a ejemplos concretos de imperativos permitidos, no
  a la prohibición declamada. Efecto colateral medido: migra a formas que el
  patrón no lista: aparecen `descubre`, `puedes`, `podrás`, `comparte` en
  borradores **aceptados**. Es decir, el gate de registro tiene falsos
  negativos por construcción (la lista cubre ocho imperativos); la conformidad
  mecánica sobrestima el registro real. El fallo pasa de "detectado" a
  "invisible para el gate", que es peor para la evidencia.
4. **Bloque antihechos: reduce la fuga a un tercio** (6/6 a 1-2/6) pero no la
  elimina: quedan `jornada` y `vinculación`, sustantivos del propio título que
  el modelo usa como nombre del tipo de actividad. La regla de fragmentos es
  estructuralmente estricta frente a títulos cuyas palabras son vocabulario de
  dominio; pedirle al modelo que no diga "jornada" en la invitación a una
  jornada es casi pedirle que no nombre el objeto.
5. **El enforcement por grammar sostiene la forma, no el contenido.** Con
  `format=none` reaparece `json_invalid` (el modelo antepone prosa al objeto)
  y con `format=json` reaparece `creative_field_invalid` (un `gancho` de 167
  caracteres supera `maxLength=160`, que el grammar sí impone). La conformidad
  de contenido no mejora por quitar el schema; el parseo sí empeora.
6. **Variedad residual:** a temp 0 el gancho aceptado "¡Sumate a nuestra
  comunidad de aprendizaje!" se repite idéntico en SYN-001 y SYN-005. v3 mejora
  sobre v2 (una sola combinación en todo el corte, `DEF-A1-011`) pero la
  variedad entre actividades sigue siendo pobre en decodificación greedy.

## 4. Dónde falla, con qué severidad

| Capa | Estado medido | Severidad de la brecha |
|---|---|---|
| Parseo del JSON | 0 fallos con `json_schema` (1/6 sin schema) | resuelta por transporte v4 |
| Presupuesto de decodificación | agotamiento 0; eval_count ≤ 181 << 512 | descartada (`DEF-A1-013` cerrado) |
| Gate de hechos: fragmento del título | 6/6 baseline; 1-3/6 con prompt reforzado | **dominante y estructural** |
| Política de redes: `RED-REG-01` (registro) | 5/6 baseline; 0/6 con bloque de voseo | dominante, corregible por prompt |
| Política de redes: `RED-TON-02` (exclamaciones) | 2-3/6 según corrida | menor, fluctuante |
| Gate de hechos: `unauthorized_fact_claim` (`remoto`, `digital`) | 1-3/6 | menor, ligada al título SYN-005 |

El 0/6 no es un fracaso único sino la conjunción de dos fallas independientes:
el modelo no separa el objeto de la invitación del título, y no respeta el
registro rioplatense. Ambas responden a reforzamiento de prompt, pero ninguna
queda en cero de forma estable, y la corrección de registro expone falsos
negativos del gate léxico.

## 5. Opciones para llevar a la SEU

La decisión editorial (qué registro es aceptable, si "descubre" cuenta como
falta, si el post puede nombrar el tipo de actividad) corresponde a la SEU y
este spike no la sustituye. Lo que aporta es la medición de cada alternativa
técnica, su costo y su efecto sobre la trazabilidad.

### Opción A: incorporar los bloques de refuerzo a las plantillas v3

Reescribir la sección de tono de `post_instagram_structured_v3` y
`post_linkedin_structured_v3` con ejemplos concretos de voseo permitido y la
prohibición explícita de repetir fragmentos del título (los bloques medidos
acá).

- **Evidencia:** `non_rioplatense_register` 5/6→0/6, `source_fact` 6/6→3/6,
  aceptación 0/6→3/6 a temp 0 (estable entre repeticiones) y 4/12 a temp 0,7.
- **Costo técnico:** bajo. Edición de dos plantillas versionadas, sin tocar
  contrato, gate ni política; la versión de prompt ya queda registrada en cada
  línea de auditoría (`prompt_version`).
- **Impacto en trazabilidad:** ninguno negativo; el cambio es visible por
  versión de prompt y hash.
- **Riesgo residual:** la aceptación sube pero incluye texto con tuteo que el
  gate no detecta (`descubre`, `puedes`): mejorar el prompt sin ampliar el
  patrón convierte fallos visibles en invisibles. Si se adopta, conviene
  revisar con la SEU si `PATRON_TUTEO` debe crecer (lista ampliada revisable)
  o si el registro se confía íntegramente a la revisión humana.

### Opción B: revisar la regla de fragmentos del título

`_contiene_fragmento_significativo` rechaza cualquier palabra de cinco o más
letras del título. La medición muestra que los disparos son sustantivos de
dominio ("jornada", "vinculación", "taller"), no fuga de datos sensibles:
esos mismos datos los copia el renderer en la sección de hechos.

- **Variantes posibles:** exigir dos o más palabras consecutivas del título,
  o mantener una lista editorial de sustantivos de dominio permitidos
  aprobada por la SEU (título completo y datos como fecha/organización/
  contacto seguirían prohibidos).
- **Costo técnico:** medio. Cambio en el gate con regresiones nuevas; el
  código `source_fact_in_creative_field` se conserva pero con umbral distinto,
  lo que exige versionar la semántica del control.
- **Impacto en trazabilidad:** relajar la regla deja pasar paráfrasis del
  título en la zona creativa (un riesgo editorial, no de datos: el renderer
  garantiza que los hechos verdaderos están presentes de todas formas). La
  duplicación "título en prosa + título en hechos" es una decisión de forma,
  no de seguridad, y conviene que la tome la SEU.
- **Evidencia a favor:** con los bloques de prompt ya incorporados, esta regla
  es el único código que queda (6/12 en la corrida estable).

### Opción C: catálogo cerrado ampliado (v2.5)

Extender `post_creative_output_v2` con un catálogo curado más amplio por canal
y combinarlo con una selección determinista (por hash de solicitud o por
rotación), dejando al LLM fuera de la redacción.

- **Costo técnico:** medio-bajo en código; alto en trabajo editorial: cada
  frase del catálogo la tiene que redactar y aprobar una persona.
- **Impacto en trazabilidad:** máximo: toda salida es una combinación
  versionada de frases aprobadas, conformidad 6/6 por construcción.
- **Limitación medida:** con temperatura 0 el modelo elige siempre la misma
  opción (`DEF-A1-011`); un selector determinista daría la misma variedad en
  ~0,001 s sin inferencia. Si se adopta, el rol del LLM queda reducido a
  ninguno en este paso, lo que conviene declarar explícitamente ante la SEU
  para no presentar una selección como redacción.

### Opción D: mantener v3 como experimental y operar sobre v2 con revisión SEU

Dejar v2 como contrato operativo del MVP (ya mide 6/6) y declarar v3 como
línea de investigación que no bloquea el gate G2.

- **Costo técnico:** nulo; es el estado actual.
- **Impacto en trazabilidad:** ninguno nuevo.
- **Contra:** no resuelve `DEF-A1-011` (el catálogo se comporta como función
  constante) ni produce borradores con variedad real; la conformidad 6/6 de v2
  es conformidad de transporte sobre un texto fijo, lo cual la SEU debería
  evaluar conscientemente en el checklist de `DEF-A1-005`.

## 6. Recomendación técnica (no editorial)

La combinación medida más favorable es **A + revisión informada de B**: el
refuerzo de prompt deja una única regla residual (`source_fact` por fragmento
del título, 3/6), y esa regla es justamente la que requiere criterio editorial
(no una decisión técnica) porque su costo actual es rechazar prosa que
menciona el tipo de actividad. Se sugiere presentar a la SEU las muestras
aceptadas y rechazadas de las corridas `voseo_antihechos` (guardadas en
`salida/`, reproducibles) junto con la pregunta concreta: ¿un post de
invitación puede nombrar "la jornada" o debe referirla sólo como "esta
propuesta"? Esa respuesta define si B es un ajuste de umbral o una lista de
sustantivos permitidos.

## 7. Cómo reproducir

```bash
# Runtime (una vez): el binario y los modelos viven en .runtime/ (ignorado).
OLLAMA_MODELS="$PWD/.runtime/models" .runtime/ollama-root/usr/bin/ollama serve

# Baseline oficial (matriz v4):
PYTHONPATH=src python3 scripts/matriz_hu011_live_v4.py \
  --salida salida/<dir> --contrato v3 --confirm-live-llm

# Medición diagnóstica con variantes:
PYTHONPATH=src python3 scripts/medir_conformidad_v3.py \
  --salida salida/<dir> --contrato v3 \
  --variante-prompt voseo_antihechos --temperature 0 \
  --num-predict 512 --format json_schema \
  --repeticiones 2 --guardar-respuestas --confirm-live-llm
```

## 8. Límites del spike

- Un solo modelo (`llama3.2:3b`), un solo host CPU, dos canales, cinco casos
  sintéticos. Las tasas no se generalizan a otro modelo ni a datos reales.
- Las corridas a temp 0 son deterministas dentro del proceso de servidor (la
  repetición de la mejor variante dio errores idénticos caso a caso). Entre
  procesos, o al cambiar la serialización del `format` schema, se observó
  deriva menor: el medidor en baseline difirió del runner oficial sólo en
  SYN-001/linkedin (`non_rioplatense_register` y `unauthorized_exclamation`
  ausentes), sin cambiar el 0/6 ni las reglas dominantes.
- Las variantes de prompt son instrumentación: no modificaron plantillas,
  contratos ni políticas versionadas.
- Las respuestas crudas quedan en `salida/` (ignorado por Git); el JSON de
  cada corrida sólo registra códigos, literales de patrón, conteos y hashes.
- Nada de lo medido acredita validación SEU, Gate G2 ni TRL 3.
