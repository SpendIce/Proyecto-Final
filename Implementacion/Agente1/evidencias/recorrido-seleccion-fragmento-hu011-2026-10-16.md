# Selección del fragmento de efeméride HU-011 (recorrido offline, 2026-10-16)

**Issues:** #116 (implementación), #97 (decisión de origen), #85 (flujo original).
**HU:** HU-011. Proceso BPM: Proceso 4, comunicación institucional.
**Estado institucional:** PENDIENTE. No hubo sesión con la SEU ni con Historia Viva.
**Estado técnico:** `PROVISIONAL_NO_INSTITUCIONAL`.
**Contratos:** `post_creative_efemeride_v1` (provisional), prompts
`post_*_efemeride_v1` (provisionales) y `historia_viva_v1_1.1.0-rc1`
(`BORRADOR_HISTORIA_VIVA`).
**Generador:** `FakeGenerator` (simulado). **Puerto:** `HistoriaVivaFake` (en
memoria). Sin red, sin credenciales y sin modelo local.

## Qué se corrió

Las dos corridas salen de `Implementacion/Agente1`, sobre el fixture sintético
`data/fragmentos_historia_viva_varios.json` (sha256
`2079ec6fb1ce5880ff478979a6cc082333a02cfa6ad12d27f2739d1f870b126d`). Trae tres
fragmentos con la forma del contrato candidato: `frg-var-001` (precisión día,
1926-08-07, texto de 1315 caracteres), `frg-var-002` (precisión día,
1926-08-08, texto corto) y `frg-var-003` (precisión mes, agosto de 1926). Es el
caso «varios resultados» que el 13/10 fallaba por largo.

Primera corrida, el período del mes (los tres fragmentos son elegibles):

```bash
uv run python scripts/post_efemeride_demo.py \
  --fragmentos data/fragmentos_historia_viva_varios.json \
  --directorio /tmp/demo-a
```

Salida real (exit 0), con las claves largas recortadas donde no aportan:

```json
{"borrador": "/tmp/demo-a/borradores/efemeride-1926-08-01_1926-08-31-fc5b2b35-instagram.md", "error": null, "estado": "PENDIENTE_VALIDACION", "fase": "generacion", "modo": "offline", "objeto_id": "efemeride-1926-08-01_1926-08-31-fc5b2b35-instagram", "procedencia": "synthetic_test"}
{"enlaces": {"descarte": "…entry.000000023=descarte", "publique": "…entry.000000023=publique"}, "fase": "decision", "objeto_id": "efemeride-1926-08-01_1926-08-31-fc5b2b35-instagram"}
{"borrador": null, "error": "La consulta no devolvió material histórico", "estado": "INCOMPLETA", "fase": "sin_material"}
```

El borrador publica un solo fragmento: `frg-var-001` (1315 caracteres) no entra,
`frg-var-002` sí, y `frg-var-003` queda sin usar. Texto exacto del archivo:

```
# BORRADOR — NO PUBLICAR

_Procedencia: material sintético de prueba con la forma del insumo de A2 (Historia Viva). Consulta: desde 1926-08-01 hasta 1926-08-31._

CANAL: instagram
TEXTO:
Un día como hoy quedó escrito en nuestra historia.

Cada efeméride convoca a la comunidad a mirar el camino recorrido y a reconocerse en esa memoria compartida.

Efeméride: agosto de 1926

La gacetilla interna anuncia la primera cursada con inscripción abierta a la comunidad.
Fuente: pie-var-gacetilla-002 / frg-var-002 (8 de agosto de 1926)

El enlace con más contexto está en nuestro perfil.
HASHTAGS:
#FIE #Efemerides #Centenario

REFERENCIAS NO UTILIZADAS
- pie-var-acta-001 / frg-var-001 (7 de agosto de 1926): no entra completa en el canal
- pie-var-nota-003 / frg-var-003 (agosto de 1926): no se usa: el post cita una sola referencia
```

Segunda corrida, la que fallaba por largo (consulta de un día: sólo
`frg-var-001` sustenta la fecha y su texto no entra):

```bash
uv run python scripts/post_efemeride_demo.py \
  --fragmentos data/fragmentos_historia_viva_varios.json \
  --directorio /tmp/demo-b --desde 1926-08-07 --hasta 1926-08-07 --precision dia
```

Salida real (exit 1):

```json
{"borrador": null, "error": "Ningún fragmento elegible entra completo en el canal", "estado": "INCOMPLETA", "fase": "generacion", "modo": "offline", "objeto_id": null, "procedencia": "synthetic_test"}
```

La auditoría (`logs/ejecuciones.jsonl`) separa recuperación, elegibles y
publicados, y deja los motivos de exclusión (referencias y motivos, nunca prosa
de la fuente). Extracto real de la primera corrida:

```
estado=PENDIENTE_VALIDACION resultado=borrador_generado intento=1
hv_fragmentos=3 hv_fragmentos_elegibles=3 hv_fragmentos_publicados=1
hv_piezas_fuente=['pie-var-gacetilla-002']
referencias_excluidas=[{'referencia': 'pie-var-acta-001 / frg-var-001', 'motivo': 'no_entra_completo_en_el_canal'}, {'referencia': 'pie-var-nota-003 / frg-var-003', 'motivo': 'no_utilizada_una_referencia_por_post'}]
```

Y de la segunda, con la causa de extensión distinta de una falla de generación:

```
estado=FALLIDA resultado=reintento_pendiente intento=1 hv_fragmentos=2 hv_fragmentos_elegibles=1 hv_fragmentos_publicados=0
estado=INCOMPLETA resultado=material_no_utilizable intento=2 hv_fragmentos=2 hv_fragmentos_elegibles=1 hv_fragmentos_publicados=0 validation_errors=['length_out_of_range']
```

Suite focalizada:

```bash
uv run pytest -q tests/test_posts_efemeride.py
```

Resultado real: `49 passed in 0.68s`.

## Qué demuestra

- Con varios resultados, el post cita una sola referencia: el primer elegible
  que entra completo, conservando el orden de Historia Viva. `frg-var-001` no
  entra y se prueba el siguiente; `frg-var-002` se publica con su cita
  `pieza / fragmento (expresión temporal)`.
- El filtro temporal corre antes de generar y descarta el solapamiento sin
  contención: la fecha de la fuente tiene que caer dentro del período y la
  precisión declarada se interpreta tal cual (`frg-var-003`, precisión mes,
  queda dentro de agosto y por eso es elegible; un año o una década no
  quedarían dentro de un mes).
- La consulta no se limita a uno: el tope de recuperación viaja en
  `hv_consulta.limite` y `hv_fragmentos` cuenta lo recuperado, distinto de
  `hv_fragmentos_publicados`, que es 0 o 1.
- Sin ningún fragmento que entre, no hay borrador: `INCOMPLETA` /
  `material_no_utilizable` con `validation_errors=['length_out_of_range']`,
  distinguible de la causa temporal (`material_insuficiente`) y de una falla de
  generación (`FALLIDA`).
- Las referencias no utilizadas y su motivo quedan en el borrador, fuera del
  `TEXTO` y de los `HASHTAGS`, así que no entran en el cómputo de extensión.
- El gate de hechos y el reintento acotado siguen vigentes sobre la zona
  creativa del modelo; que la fuente entre no demuestra que el modelo haya
  cumplido el contrato. El borrador sigue `PENDIENTE_VALIDACION`, con la
  decisión de publicación humana y sin publicar nada.

## Qué no demuestra

- **Es un recorrido con generador simulado y puerto en memoria.** El
  `FakeGenerator` devuelve la salida de muestra del script y `HistoriaVivaFake`
  responde por solapamiento; no hay transporte HTTP, ni API real, ni modelo
  local. No se midió grounding, tono ni calidad de redacción.
- **No prueba el recorrido live.** La instancia de `/v1` y el acuerdo del
  contrato con Historia Viva siguen en el issue #17; nada de esto tocó la red.
- **No acredita aceptación institucional ni un TRL.** El contrato creativo, los
  prompts y la política de redes siguen `PROVISIONAL_NO_INSTITUCIONAL`, y la
  decisión de publicación es humana.
