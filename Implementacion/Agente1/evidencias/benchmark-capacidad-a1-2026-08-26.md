# Prueba de capacidad local de A1 contra el volumen informado por la SEU (2026-08-26)

- **Runner:** `scripts/medir_capacidad_hu011.py`
- **Modelo:** `llama3.2:3b` local, CPU, temperatura 0, decodificación por JSON Schema en HU-011
- **Contrato creativo:** `post_creative_output_v3`
- **Política aplicada:** `politica_redes_provisional_v1`
- **Datos:** tres actividades sintéticas completas (`SYN-001`, `SYN-003`, `SYN-005`)
- **Límite:** no hubo publicación, envío, Workspace, datos reales ni revisión SEU. Esta evidencia no acredita TRL 3.

## 1. Pregunta que responde

La SEU informó como referencia un mínimo de un reel mensual y dos publicaciones
semanales, con un promedio aproximado de doce publicaciones mensuales. La
pregunta acotada es si el modelo local sostiene ese ritmo. El dato de volumen no
es un SLA ni una promesa de producción.

**Modelo de volumen usado:** una publicación equivale a tres generaciones —una
gacetilla, un post de Instagram y un post de LinkedIn—, de modo que doce
publicaciones mensuales son **36 generaciones**. El reel queda fuera del
cálculo: A1 no produce video, audio ni guion audiovisual (`RED-ALC-02`).

## 2. Cortes ejecutados

| Corte | `num_predict` | Piezas | Propósito |
|---|---:|---:|---|
| A | 112 | 18 (2 ciclos con gacetillas) | Medir la configuración vigente |
| B | 300 | 9 (1 ciclo con gacetillas) | Verificar si los rechazos de A eran truncamiento |

## 3. Latencia

| Métrica | Corte A (`np=112`) | Corte B (`np=300`) |
|---|---:|---:|
| Primera generación, modelo frío | 42,339894 s | 17,710831 s |
| Caliente — mínimo | 14,051473 s | 15,139787 s |
| Caliente — p50 | 19,485706 s | 21,266593 s |
| Caliente — p95 | 40,183906 s | 26,925730 s |
| Caliente — máximo | 41,347126 s | 26,925730 s |

La latencia por pieza en el corte B: gacetilla p50 15,570735 s, post de
Instagram p50 19,785380 s, post de LinkedIn p50 24,394919 s.

## 4. Proyección sobre el volumen informado

| Escenario | Corte A | Corte B |
|---|---:|---:|
| 36 generaciones mensuales a p50, sin reintentos | 701,485 s (≈ 11,7 min) | 765,597 s (≈ 12,8 min) |
| 36 generaciones mensuales a p95, sin reintentos | 1446,621 s (≈ 24,1 min) | 969,326 s (≈ 16,2 min) |
| Pico de una semana (2 publicaciones = 6 generaciones) a p95 | 241,103 s (≈ 4,0 min) | 161,554 s (≈ 2,7 min) |
| Equivalente en jornadas laborales de 6 h, a p50 | 0,0325 | 0,0354 |

**El tiempo de cómputo no es la restricción.** El volumen mensual informado
consume del orden de doce minutos de inferencia local, menos del 4 % de una
jornada. Aun multiplicando el volumen por diez, el host local seguiría
alcanzando.

## 5. Conformidad: la restricción real

| Corte | Generaciones | Conformes | Tasa |
|---|---:|---:|---:|
| A (`np=112`) | 18 | 2 | 11,11 % |
| B (`np=300`) | 9 | 1 | 11,11 % |

Códigos de rechazo observados:

| Código | Corte A | Corte B | Lectura |
|---|---:|---:|---|
| `json_invalid` | 10 | 0 | **Era truncamiento**, no incapacidad del modelo |
| `data_structure` | 4 | 2 | Gacetilla de `SYN-003` y `SYN-005`; se repite en ambos cortes |
| `source_fact_in_creative_field` | 2 | 6 | Fuga de hechos de la fuente al texto creativo |
| `non_rioplatense_register` | 2 | 6 | Tuteo |
| `unauthorized_fact_claim` | 0 | 1 | Atribución factual no autorizada |
| `unauthorized_exclamation` | 0 | 1 | Regla nueva `RED-TON-02` |

## 6. Hallazgo principal

**El `num_predict=112` vigente estaba enmascarando las fallas de contenido
detrás de fallas de transporte.** Con 300 tokens de presupuesto, los diez
`json_invalid` del corte A desaparecen por completo: el modelo sí sostiene el
objeto JSON exigido por el contrato v3.

Lo que aparece debajo es peor de leer y más útil de conocer: con la salida ya
bien formada, **6 de 6 posts** fugaron un hecho de la fuente al texto creativo y
**6 de 6** usaron tuteo. No es una falla intermitente sino sistemática en las
tres actividades y en los dos canales.

Esto corrige parcialmente la lectura del benchmark
`benchmark-hu011-ollama-v3-regresion-2026-08-26.md`, que atribuyó los 0/6 a que
«el modelo no mantuvo el objeto JSON exigido». La causa inmediata era el
presupuesto de decodificación; la causa de fondo es de aptitud comunicacional y
sigue abierta.

Corresponde además señalar por qué esto no contradice el corte del 17/08, que
había registrado 4/6 aceptaciones con v3: aquel corte es anterior a los
controles incorporados el 26/08 por `DEF-A1-012` —tuteo, CTA de circuito no
autorizado, modalidad `remoto` y fragmentos significativos del título—. Con el
gate reforzado, salidas que antes pasaban ahora se rechazan. El gate no
empeoró: mejoró su detección, y lo que cambió es lo que se puede afirmar.

Los rechazos `data_structure` de las gacetillas de `SYN-003` y `SYN-005`, en
cambio, **no** son truncamiento: se reproducen igual con 300 tokens. Quedan como
hallazgo separado sobre HU-010.

## 7. Fallback documentado

Con el gate fail-closed, una generación no conforme termina `FALLIDA`, no crea
borrador y no persiste contenido. El fallback operativo es, en este orden:

1. **Reintento acotado.** Sobre la tasa observada de 11,11 %, se necesitan del
   orden de nueve intentos por pieza conforme: unas 1,9 h de cómputo mensual a
   p50. Sigue siendo viable en tiempo, pero es un mal criterio de calidad,
   porque acepta la primera salida que pasa el gate mecánico.
2. **Redacción humana.** Si la pieza no supera el gate en los reintentos
   previstos, la redacta una persona. A1 no degrada sus controles para producir
   una salida.
3. **Nunca:** relajar el schema, el gate de hechos o el control de registro para
   subir la tasa. Ese camino convertiría un problema de aptitud en un riesgo de
   publicación.

## 8. Consecuencias

- `DEF-A1-003` puede cerrarse en su componente de latencia: hay matriz repetible
  cold/warm y proyección contra el volumen informado. Falta la aceptación
  institucional del umbral y el host objetivo.
- Se abre la necesidad de revisar `num_predict`: 112 es demasiado bajo para el
  contrato v3 y produce rechazos que no informan sobre el contenido.
- La conformidad de contenido de HU-011 permanece abierta y depende de criterios
  editoriales de la SEU (`DEF-A1-007`) y de aptitud del modelo (`DEF-A1-011`).

## 9. Reproducción

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache python scripts/medir_capacidad_hu011.py \
  --salida salida/capacidad --ciclos 2 --incluir-gacetillas --confirm-live-llm
```

Requiere un Ollama local ya iniciado con el modelo descargado. El resumen
machine-readable queda en `salida/.../resumen-capacidad.json`, ignorado por Git
para no versionar contenido generado. Hashes de los artefactos del corte:

| Artefacto | SHA-256 |
|---|---|
| `data/actividades_sinteticas.csv` | `fe5d712f5f41e777b5daa02ac1de0b23bfde64e0cc61433d9a89d3c0977d98f4` |
| `src/agente1/posts.py` | `4dbf4b35b51f0f9956b3cc52a916137eae7293ac9a4ce7480fd299a7a36621a5` |
| `src/agente1/politicas/politica_redes_provisional_v1.json` | `d58c1be1c9778b101719b91de7b32941a2f6e2efbcea3b554472216c548469bd` |
