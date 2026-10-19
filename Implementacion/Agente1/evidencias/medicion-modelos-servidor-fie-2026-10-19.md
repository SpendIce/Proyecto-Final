# Medición de modelos locales en el servidor de la facultad: HU-010 y HU-011

- **Fecha:** 2026-10-19, corrida presencial desde la red de la facultad.
- **Host:** `labredesfie`, el servidor de la facultad. Es el **host del sistema de
  demostración**: la cátedra no admite la demo en localhost (19/10, ver #119), así que
  no se mide en la laptop.

  | Componente | Valor |
  |---|---|
  | CPU | Intel Xeon E-2224G, 4 núcleos / 4 hilos, 3,5–4,7 GHz, AVX2 y FMA |
  | GPU | ninguna |
  | RAM | 31 GB (≈30 GB libres antes de la corrida), 8 GB de swap |
  | Disco | 914 GB en `/` (≈727 GB libres) |
  | SO | Ubuntu 22.04.5 LTS, kernel 5.15.0-198 |
  | Ollama | 0.40.6 (corrida A) y 0.32.14 (corrida B), en espacio de usuario, loopback |
  | Python | 3.12.15 (venv de uv) |

  El servidor es compartido con servicios del laboratorio de redes (OVN/OVS, libvirt,
  docker, apache). La carga previa era ≈0,05 y no hubo otra carga relevante durante la
  corrida. El usuario `jgone` no tiene sudo: Ollama corre como proceso del usuario y
  no como servicio.
- **Código:** `cff6a16` (gacetilla de difusión `gacetilla_v8` con renderer de mail;
  posts `post_input_v2`, `post_deterministic_renderer_v5`, contrato creativo
  `post_creative_output_v3`).
- **Pesos:** `llama3.2:3b` (`a80c4f17acd5`) y `llama3.1:8b` (`46e0c10c039e`). Tienen
  las mismas capas que los modelos de la laptop de las mediciones de agosto y septiembre.
- **Alcance:** datos sintéticos (`data/actividades_sinteticas.csv`). No es validación
  SEU, no mide calidad editorial y no acredita Gate G2 ni TRL. Responde el ticket #50.

## 1. Qué se corrió

Dos runners versionados, sin tocar código de producción. Cada corrida usa los dos
modelos en secuencia y descarga de memoria el modelo anterior antes de empezar.

| Runner | Qué mide | Parámetros |
|---|---|---|
| `scripts/medir_conformidad_v3.py` | HU-011 v3, la misma matriz del 23/09: 6 casos completos y 4 negativos | `--timeout 600 --num-predict 512 --temperature 0 --format json_schema --variante-prompt baseline --guardar-respuestas`, reintento del pipeline activo |
| `scripts/medir_capacidad_hu011.py` | HU-010 (gacetilla + mail) y HU-011 (Instagram y LinkedIn) por pieza, latencia y conformidad | `--ciclos 2 --incluir-gacetillas --timeout 120` (tope del adapter), `num_predict` 512 por defecto |

- **Corrida A:** Ollama 0.40.6, la versión vigente al 19/10.
- **Corrida B:** Ollama 0.32.14, la versión del runtime de la laptop en las mediciones
  anteriores. Repite exactamente lo mismo para separar el efecto de la versión de
  Ollama del efecto del host y del código.

La latencia por llamada sale del log de Ollama, que registra la duración de cada
`POST /api/generate`. Es el valor que limita `timeout_s`, porque el adapter aplica el
timeout por llamada. La latencia por pieza la mide el runner e incluye los reintentos.
La RAM se muestreó cada 2 s con el RSS del runner (`llama-server` en 0.40.6) y la
memoria usada del host.

## 2. Conformidad

| Medición | 3b, Ollama 0.40.6 | 3b, Ollama 0.32.14 | 8b, Ollama 0.40.6 | 8b, Ollama 0.32.14 | Referencia laptop 23/09 |
|---|---|---|---|---|---|
| HU-011 v3, aceptadas (matriz del 23/09) | 0/6 | 1/6 | 2/6 | 1/6 | 3b 1/6 · 8b 4/6 |
| HU-011 v3, casos negativos conformes | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| HU-010 `gacetilla_v8` + mail, conformes | **6/6** | **6/6** | 5/6 | 4/6 | sin medición previa de v8 |
| HU-011 en capacidad, Instagram | 0/6 | 0/6 | **6/6** | **6/6** | — |
| HU-011 en capacidad, LinkedIn | 0/6 | 0/6 | 0/6 | 0/6 | — |

Códigos de rechazo más frecuentes:

- **HU-011 con 3b:** `non_rioplatense_register` (12 en capacidad, con las dos
  versiones), `source_fact_in_creative_field` y `unauthorized_fact_claim`.
- **HU-011 con 8b:** `source_fact_in_creative_field`, que aparece en todas las piezas de
  LinkedIn, y `unauthorized_fact_claim`.
- **HU-010 con 8b:** `unauthorized_fact_in_prose`, siempre en `SYN-001`. Con 3b no hubo
  rechazos de gacetilla.

## 3. Latencia

Latencia por llamada al modelo, en segundos:

| Modelo y versión | n | p50 | p95 | Máximo | Llamadas > 45 s | Llamadas > 60 s |
|---|---:|---:|---:|---:|---:|---:|
| 3b, 0.40.6 | 42 | 23 | 37 | **41** | 0 | 0 |
| 3b, 0.32.14 | 42 | 23 | 39 | **40** | 0 | 0 |
| 8b, 0.40.6 | 33 | 31–37 | 72–75 | **78** | 5 | 3 |
| 8b, 0.32.14 | 36 | 34–38 | 79–80 | **88** | 7 | 4 |

Latencia por pieza, con reintentos, en la corrida A (0.40.6):

| Pieza | 3b, p50 / máximo | 8b, p50 / máximo |
|---|---|---|
| Gacetilla + mail (HU-010) | 20 s / 41 s | 39 s / 79 s |
| Post Instagram | 44 s / 52 s | 29 s / 31 s |
| Post LinkedIn | 48 s / 48 s | 63 s / 63 s |

La corrida B da valores equivalentes (gacetilla 8b, máximo 88 s; LinkedIn 8b, p50 71 s).

**La versión de Ollama no cambia la velocidad: cambia el texto.** Las latencias de las
dos corridas coinciden dentro del ruido. La conformidad sí se mueve: el 3b pasa de 0/6
a 1/6 y el 8b de 2/6 a 1/6 en HU-011 v3.

**`timeout_s` necesario:**

- **3b:** la llamada más lenta fue de 41 s. El default del adapter, 45 s, deja menos de
  4 s de margen. Ya se cortó a 45 s el 28/09, con el host cargado.
- **8b:** la llamada más lenta fue de 88 s. **Con el default de 45 s el 8b no funciona en
  este host**: corta entre 5 y 7 llamadas por corrida.
- **Tope:** al medir, el adapter aceptaba hasta 120 s (`MAX_OLLAMA_TIMEOUT_S`).
- **Cambio posterior (mismo día):** el default pasó a 180 s y el tope a 300 s. Se derivaron del peor caso
  de los logs de `ollama serve` con el 8b: 22 tokens/s de prompt, 5 tokens/s de generación (cerca de la
  mitad de las llamadas cae a ~5, las demás quedan en ~10) y prompts de hasta 1189 tokens.
  Así, 512 tokens de `num_predict` llevan ~156 s y 1024, ~258 s. Ver el comentario sobre las constantes en `ollama.py`.

Las llamadas más lentas del 8b son las dos primeras gacetillas del ciclo 0 (`SYN-001` y
`SYN-003`): 75–88 s, contra 37–40 s para las mismas actividades en el ciclo 1. La diferencia es consistente con la reutilización del
caché de prompt de Ollama. Para fijar el timeout hay que tomar el caso frío, porque una
actividad nueva no tiene caché.

## 4. RAM

| Modelo | RSS del runner, máximo | Memoria usada del host, pico |
|---|---:|---:|
| 3b | ≈3,1–3,3 GB | ≈3,8–3,9 GB |
| 8b | ≈5,9–6,0 GB | ≈6,7–6,8 GB |

En la corrida B, la fase de HU-011 v3 con 3b llegó a 8,7 GB porque el servidor 0.40.6
todavía tenía el 8b cargado de la corrida A (`keep_alive` de 5 min). Ese valor no se
toma como RAM del 3b. Con 31 GB en el host, **la memoria no es restricción para
ninguno de los dos modelos**.

## 5. Lectura

- **HU-010 es estable con 3b:** 12/12 entre las dos corridas, con la gacetilla vigente
  (`v8`) y el renderer de mail. Es la primera medición de la v8 con un modelo real. El
  8b es más lento y menos conforme en gacetillas (9/12): su único rechazo, siempre en
  el mismo caso, es una afirmación fáctica en la prosa.
- **En HU-011 el 8b ya no es lo que era el 23/09.** Con el código vigente (contrato de
  entrada v2 y gate que revisa más campos fuente) baja a 1–2/6 en la matriz v3. En
  capacidad, el 8b resuelve Instagram (12/12) y falla LinkedIn (0/12). El 3b no
  resuelve ninguno de los dos canales en redacción libre.
- **La comparación con la laptop del 23/09 no aísla el host.** También cambiaron el
  código y la versión de Ollama, y la corrida B muestra que la versión sola alcanza
  para mover ±1 caso con `temperature 0`. Con n=6, una diferencia de un caso es ruido
  de runtime, no una propiedad del modelo.
- **Latencia contra volumen:** con 3b, las 36 generaciones mensuales del volumen SEU
  insumen ≈26 min a p50 sin reintentos. Con 8b, ≈24 min. No es restricción de
  capacidad.
- **R-TEC-01:** su alarma («latencia > 30 s sostenida») queda disparada en este host
  para los posts de HU-011 (salvo Instagram con 8b, ≈29 s) y para las gacetillas con 8b.

## 6. Qué decide esto y qué no

Esta evidencia no elige modelo ni configuración: eso lo decide #51. Le entrega:

- conformidad por HU y por canal con los dos modelos en el host de la demo;
- el `timeout_s` mínimo por modelo: más de 41 s con 3b y más de 88 s con 8b;
- que la versión de Ollama hay que congelarla junto con el modelo, porque cambia el
  resultado aunque no cambie la velocidad;
- que la RAM no restringe.

Queda para #118 el recorrido completo de HU-010..HU-014 en el servidor: HU-012
(plantilla de actividad), HU-013 (interpretación) y HU-014 (línea descriptiva) también
llaman al modelo y no se midieron acá.

## 7. Datos crudos

Están en `salida/` (ignorado por Git). Las respuestas crudas del modelo quedan aparte,
en `respuestas-crudas/`.

| Archivo | `evidence_id` | SHA-256 |
|---|---|---|
| `salida/medicion-fieserver-2026-10-19/v3-llama3-2-3b/medicion-v3.json` | `HU011-V3-LLAMA3-2-3B-FIESERVER-2026-10-19` | `593417c13745e818f5e6dee90b4c599a588a6e9daa1d40c1554a9584a71b5bbb` |
| `salida/medicion-fieserver-2026-10-19/v3-llama3-1-8b/medicion-v3.json` | `HU011-V3-LLAMA3-1-8B-FIESERVER-2026-10-19` | `91448d887ce8974df2294f8b85a964a945a424a7f0837e28a2356ddff6ecad79` |
| `salida/medicion-fieserver-2026-10-19/cap-llama3-2-3b/resumen-capacidad.json` | — | `957778d9f79563421467fa36a53f334ad0590d952df7fd3affec674b98c49b7a` |
| `salida/medicion-fieserver-2026-10-19/cap-llama3-1-8b/resumen-capacidad.json` | — | `02e96476d7844198568ae6532f1a276199b901a47b3f94c300722c854cd05224` |
| `salida/medicion-fieserver-ollama03214-2026-10-19/v3-llama3-2-3b/medicion-v3.json` | `HU011-V3-LLAMA3-2-3B-FIESERVER-OLLAMA03214-2026-10-19` | `d88db1009814679946192b560524786d85f3d00ac74fadf0edbaca768ef11ae3` |
| `salida/medicion-fieserver-ollama03214-2026-10-19/v3-llama3-1-8b/medicion-v3.json` | `HU011-V3-LLAMA3-1-8B-FIESERVER-OLLAMA03214-2026-10-19` | `723b8af86c6ddced25ee9f41476a1c770a182eba45c35114ca9257b96a09d48b` |
| `salida/medicion-fieserver-ollama03214-2026-10-19/cap-llama3-2-3b/resumen-capacidad.json` | — | `3bd9326332efc38c9d501a5d63407f1bb4da3c9a475bb5e4871b76de22850b1a` |
| `salida/medicion-fieserver-ollama03214-2026-10-19/cap-llama3-1-8b/resumen-capacidad.json` | — | `38e11cef535b52bd01f448a0778a99a07ffff42438e648c063049c7689bf90b3` |

Cada directorio tiene además `host.txt`, `ram.csv` (y `ram-runner.csv` en la corrida A)
y `ollama-serve.log`, de donde salen las latencias por llamada. Los scripts de la
corrida están en `salida/scripts-medicion-50/`.
