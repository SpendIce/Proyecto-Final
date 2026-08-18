# Benchmark HU-011 contrato v3 — redacción libre — 2026-08-17

## Propósito

`DEF-A1-011` registró que el catálogo enum de `post_creative_output_v2` reducía
la salida a ocho combinaciones por canal, de las cuales la corrida live utilizó
**una sola** en tres actividades distintas. Este corte prueba el contrato
`post_creative_output_v3`, que deja al modelo **redactar** en lugar de
seleccionar.

La propiedad de seguridad no se apoya en el enum: los hechos institucionales los
agrega un renderer determinista fuera de la salida del modelo, y el gate de
`_parsear_creatividad_estructurada` rechaza fechas, dígitos, correos, URLs,
importes, lugares, atribuciones factuales y ecos de inyección. Ese gate **no se
debilitó**.

## Configuración

| Componente | Valor |
| --- | --- |
| Contrato | `post_creative_output_v3` (sin catálogo) |
| Prompts | `post_instagram_structured_v3`, `post_linkedin_structured_v3` |
| Modelo | `llama3.2:3b`, temperatura 0, formato `json_schema` |
| Presupuesto de salida | 512 tokens |
| Runner | `scripts/matriz_hu011_live_v4.py --contrato v3 --num-predict 512` |

## Iteraciones y diagnóstico

| Corte | Aceptadas | Error dominante | Causa identificada |
| --- | ---: | --- | --- |
| v3, `num_predict` 112 | 0/6 | `json_invalid` | truncamiento del JSON por presupuesto de tokens |
| v3, `num_predict` 512 | 0/6 | `unauthorized_place` | falso positivo del patrón de lugar |
| v3, 512 + patrón corregido | **4/6** | `source_fact_in_creative_field` | fuga real de hechos, gate funcionando |

### `json_invalid` no era el contrato

`num_predict` 112 se calibró para seleccionar frases cortas de catálogo. Con
redacción libre, `prosa` admite hasta quinientos caracteres y la generación se
cortaba a mitad de cadena. Prueba directa sobre el mismo prompt: con 112 la
salida terminó en `...oportunidad de conect` y falló con *Unterminated string*;
con 512 el JSON resultó válido. `minLength` **no** rompió la compilación de
grammar: hubo inferencia real en ambos casos, a diferencia del HTTP 400 de
v3-experimental.

### `unauthorized_place` era un falso positivo del patrón

`PATRON_REFERENCIA_LUGAR` usaba `\S+` como objeto del sintagma:

```
\b(?:en|desde|hacia)\s+(?:(?:el|la|los|las|un|una)\s+)?\S+
```

Eso marcaba **cualquier sintagma preposicional del español**. Sobre un texto
generado real, con `lugar` vacío en la fuente, capturó `en un mundo`, `En esta`
y `en esta`; ninguno es un lugar. Con catálogo cerrado el defecto era invisible,
porque las frases fijas fueron redactadas para esquivarlo.

El patrón se acotó a una lista cerrada de sustantivos de lugar (aula, sede,
campus, salón, sala, auditorio, edificio, predio, pabellón, anfiteatro,
laboratorio, biblioteca, instituto, facultad, universidad, escuela, colegio,
centro, club, teatro, museo, hotel, dirección, calle, avenida, piso, oficina).
Trece casos de discriminación quedan cubiertos por pruebas.

Las otras dos defensas de lugar **no se tocaron**: `PATRON_LUGAR_PROPIO` sigue
capturando nombres propios tras `en`/`desde`, `PATRON_LUGAR_ETIQUETADO` sigue
capturando `Lugar:`, y el lugar informado por la fuente se compara aparte con
`source_fact_in_creative_field`.

## Resultado

| Actividad | Canal | Estado | Latencia |
| --- | --- | --- | ---: |
| SYN-001 | Instagram | `FALLIDA` (`source_fact_in_creative_field`) | 14,101 s |
| SYN-001 | LinkedIn | `PENDIENTE_VALIDACION` | 18,251 s |
| SYN-002 | ambos | `INCOMPLETA` sin invocar al modelo | ~0,001 s |
| SYN-003 | Instagram | `PENDIENTE_VALIDACION` | 16,812 s |
| SYN-003 | LinkedIn | `PENDIENTE_VALIDACION` | 17,223 s |
| SYN-004 | ambos | `INCOMPLETA` sin invocar al modelo | ~0,001 s |
| SYN-005 | Instagram | `FALLIDA` (`source_fact_in_creative_field`) | 16,255 s |
| SYN-005 | LinkedIn | `PENDIENTE_VALIDACION` | 16,753 s |

Cuatro aceptadas de seis; cuatro negativos conformes de cuatro. **Los dos
rechazos son el gate funcionando**: el modelo repitió un hecho de la fuente en el
texto creativo y el borrador no se creó.

## Variedad obtenida

Los cuatro borradores aceptados produjeron textos distintos entre sí y
adaptados a la actividad y al canal, frente a **una sola combinación** en v2:

| Corte | Combinaciones creativas distintas en 3 actividades |
| --- | ---: |
| v2, catálogo cerrado | 1 por canal |
| v3, redacción libre | 1 por borrador aceptado |

El modelo pasó a discriminar entre entradas: LinkedIn produjo registro
profesional sobre vinculación académica y redes de investigación, Instagram
produjo registro cercano.

## Riesgos nuevos que introduce v3

Liberar la redacción reintroduce riesgos que el corsé de v2 evitaba. Observados
directamente en esta corrida:

1. **Registro lingüístico incorrecto.** El modelo escribe en tuteo neutro
   («¿Estás listo?», «Inscríbete», «Únete») pese a que el prompt de Instagram
   pide voseo rioplatense. Para una institución argentina esto requiere
   corrección humana.
2. **Modalidad filtrada.** Una salida usó «seminario remoto».
   `PATRON_HECHO_CREATIVO` cubre `modalidad`, `presencial` y `virtual`, pero no
   `remoto`.
3. **Proceso sugerido inexistente.** «¡Inscríbete ahora!» sugiere un circuito de
   inscripción que puede no existir.
4. **Fuga parcial de hechos.** `_contiene_hecho` compara el campo completo
   normalizado, de modo que «taller» por sí solo no coincide con «Taller
   sintético de vinculación». El gate detecta repetición literal del campo, no
   paráfrasis ni fragmentos.

Ninguno de estos riesgos existía con el catálogo cerrado, y ninguno es
detectable por un gate léxico de forma completa. **Confirman que la validación
humana de la SEU no es un trámite sino un control de diseño**, y refuerzan
`DEF-A1-005` y `DEF-A1-007`.

## Estado

- Contrato v2 **intacto**: sigue rechazando texto fuera de catálogo, con prueba
  de regresión propia.
- Suite completa: **453 pruebas, 452 verdes**; la única falla es el test de
  consistencia del README sobre migraciones versionadas, anterior a este corte.
- v3 queda `PROVISIONAL_NO_INSTITUCIONAL` y **no** reemplaza a v2 por defecto:
  `procesar_post_estructurado` sigue usando v2 salvo que se pase `contrato`.

## Límites

- Datos sintéticos, tres actividades, dos canales, un modelo y un host.
- Cuatro aceptaciones de seis no acreditan una tasa de conformidad estable.
- Las políticas de tono, longitud y hashtags siguen sin definición SEU.
- No hubo validación humana ni publicación.
- Esta evidencia no habilita declarar HU-011 completa, el Gate G2 ni TRL 3.
