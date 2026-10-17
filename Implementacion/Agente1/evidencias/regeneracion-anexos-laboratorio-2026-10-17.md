# Regeneración de los anexos de laboratorio (#123)

- **Estado:** anexos 1, 2 y 3 regenerados sobre el estado real del sistema en
  el corte del 17/10/2026; la forma y los tipos siguen sin aprobación
  institucional de la SEU
- **Alcance:** los tres perfiles y las proyecciones Markdown, las entregas DOCX
  sobre las plantillas oficiales 2025 y esta nota; no se tocaron la LaTeX del
  anteproyecto, el manifest de versión ni las plantillas de
  `Contenido/DocumentacionAnteproyecto`
- **Relacionados:** decisión #120 (refactor ya, regenerar una vez) e issue #123,
  con base en #121 (formas declaradas), #111 (set de dos ejes) y #122 (tipo en
  el canal)

## 1. Foto declarada

La foto de esta regeneración es el corte del 17/10/2026 sobre la base
`3e392c5` (2026-10-17, el merge de #122): contiene los siete tipos de gacetilla
declarados (#121), el set de evaluación de dos ejes (#111) y el tipo en el
canal (#122). El inventario de componentes no tiene cambios desde `293db20`
(14/10). La cita anterior (`98be859`, 12/10/2026) quedó coherente en los tres
perfiles y en los tres scripts generadores: la foto que revisa el laboratorio
es la de este corte, y el Anexo 1 declara el alcance nuevo de los siete tipos
(dos que generan prosa: `difusion_de_actividad` y `saludo_o_efemeride`; cinco
que extraen y confirman: `cronica_de_evento`, `aviso_de_otra_area`,
`convocatoria_interna`, `fallecimiento` y `newsletter`).

## 2. Qué cambió en los documentos fuente

- `Perfil-Calidad-Sistema-Demostracion-v1.md`: filas de Interpretación
  (catálogo `intenciones_v4`), Generación (los siete tipos, su modo y su gate
  por tipo, con `test_gacetillas_formas.py` como evidencia), foto y conteo de
  suite (2281 casos verdes, 8 saltados).
- `Perfil-Seguridad-Sistema-Demostracion-v1.md`: contratos de catálogo y
  fallback citados en su versión vigente (`intenciones_v4`,
  `interpretacion_fallback_v4`).
- `scripts/anexo1_presentacion.py` y `scripts/anexo2_calidad.py`: foto y
  declaración del alcance de los siete tipos en el Anexo 1, incluido el ítem
  "no demostrado" por la forma sin aprobación de la SEU
  (`PROVISIONAL_NO_INSTITUCIONAL`).
- Regeneradas las proyecciones `Anexo1-Presentacion-v1.md`,
  `Anexo2-Calidad-Proyeccion-v1.md` y `Anexo3-Seguridad-Proyeccion-v1.md`.

## 3. Verificación ejecutada

Desde `Implementacion/Agente1`:

```
$ uv run pytest -q
2281 passed, 8 skipped in 60.51s (0:01:00)

$ uv run ruff check .
All checks passed!

$ uv run pytest -q tests/test_gacetillas_formas.py
28 passed in 0.25s
```

Las matrices declaradas como paso en vivo corrieron offline con salida en
`/tmp/opencode/corte-anexos-2026-10-17/`:

```
$ uv run python scripts/matriz_hu010.py --salida <dir>/matriz-hu010
{"status": "OK", "summary": "<dir>/matriz-hu010/matriz.json"}
  totals: 5 casos, 2 incompletas rechazadas antes del modelo, 3 pendiente de validación;
  el manifest hashea forma, prompt, contrato, dataset y runner (corte `3e392c5`)

$ uv run python scripts/matriz_hu011_v2.py --salida <dir>/matriz-hu011
{"status": "OK", "summary_ref": "matriz.json"}   10 ejecuciones: 6 PENDIENTE_VALIDACION y 4 rechazadas incompletas

$ uv run python scripts/matriz_hu012.py --salida <dir>/matriz-hu012
{"status": "OK", ...}   con aprobación parcial no hay encolado; DUPLICADA en re-corrida

$ uv run python scripts/matriz_hu014.py --salida <dir>/matriz-hu014
{"status": "OK", ...}   circuito de certificados pendiente, doble aprobación, emisión, DUPLICADA
```

El paso en vivo del canal de planilla corrió de verdad con tres pedidos
(camino feliz, repregunta y rechazo por rol):

```
$ uv run python scripts/atender_canal_planilla.py --directorio <dir>/canal
[4d52cfe4] PENDIENTE_VALIDACION        <- borrador de difusión sin la frase fija de invitación
[a5884b0a] PENDIENTE_DESAMBIGUACION    <- cinco candidatas con identificadores
[051ab1ee] RECHAZADA — El rol de quien pide no está habilitado…
```

El renderer nuevo queda evidenciado en la pieza del camino feliz: el
borrador de `canal/borradores/SYN-001.md` empieza con `BORRADOR — NO PUBLICAR`,
trae el asunto y la introducción desde la fuente, y no contiene la frase fija
«La Facultad de Ingeniería del Ejército invita…» que #121 sacó del renderer.
El registro JSONL de la corrida tiene el contrato nuevo
(`gacetilla_entrada_difusion_de_actividad_v1`) con hashes.

El paso en vivo de control de pagos corrió con el plan sintético versionado y
un buzón armado con las mismas respuestas sintéticas del fixture de prueba
(`ana.perez@example.test`, `nadie@example.test` en `example.invalid`):

```
$ uv run python -m agente1 control-pagos --plan data/plan_pagos_notebooklm_n2.csv \
    --padron data/padron_pagos_sintetico.csv --buzon <dir>/buzon
{"estado": "OK"} 3 preinscriptos, 1 respuesta no asociada (remitente_sin_coincidencia)
```

El circuito offline del Form de decisiones corrió con el padrón del recorrido:

```
$ uv run python scripts/atender_canal_form.py --directorio <dir>/form \
    --respuestas-csv <dir>/form/pedidos.csv --padron <dir>/form/padron.csv
{"atendidos": 1, "modo": "offline_fake"}

$ uv run python scripts/registrar_form_decisiones.py --directorio <dir>/form \
    --respuestas-csv <dir>/form/decisiones.csv --padron <dir>/form/padron.csv
{"resultado": "registrada"}
{"resultado": "rechazada", "rechazo_codigo": "fuera_de_padron"}
{"resultado": "rechazada", "rechazo_codigo": "objeto_inexistente"} (id inventado)
{"resultado": "rechazada", "rechazo_codigo": "objeto_inexistente"} (lote sin declarar)
```

La auditoría de seguridad corrió contra el manifiesto sintético versionado:

```
$ uv run python scripts/auditar_seguridad_d2.py --manifest data/security_d2_manifest.synthetic.json \
    --reporte <dir>/reporte-seguridad.json
{"status": "PASS"}  checks: logs_redacted, resources_allowlisted,
remote_errors_redacted, no_distribution_endpoints
```

## 4. Entregas DOCX (corte del 17/10/2026)

Generadas sobre las plantillas oficiales 2025 de
`Contenido/DocumentacionAnteproyecto/Revision-Laboratorio-2025/` (sin
modificarlas), en la carpeta `Documentos/Laboratorio/Entrega-2026-10-23/`:

| Archivo | Bytes | Plantilla oficial |
|---|---|---|
| `Anexo1-Presentacion.docx` | 31733 | `3.1 - Anexo 1 - Presentación 2025.docx` |
| `Anexo2-Calidad.docx` | 19939 | `3.2 - Anexo 2 - Calidad 2025.docx` |
| `Anexo3-Seguridad.docx` | 25041 | `3.3 - Anexo 3 - Seguridad 2025.docx` |

## 5. Pasos declarados que no corrieron en este corte

Los pasos live con credencial D2, modelo local o cuenta de servicio quedan
declarados como paso, no como corrida (igual que su declaratoria en los
perfiles): `atender_canal_form.py --live`, `registrar_form_decisiones.py
--live`, `workspace_e2e.py --live --confirm-write-workspace`, `smoke_ollama.sh`
y toda corrida contra Ollama; la medición de capacidad y de conformidad con
modelo real sigue siendo la del 23/09.

## 6. Límites y pendiente

- **El inventario no registra todavía el refactor de #121.** El módulo
  `gacetillas.py` (renderer único y formas) no figura aún en
  `Documentos/Inventario/Inventario-Componentes-Sistema-Demostracion-v1.md` y
  su regla «se actualiza en el mismo commit en que entra un componente» quedó
  incumplida por #121/#122. La foto declarada aquí queda igualmente trazada al
  corte `3e392c5`; actualizar la fila del inventario es un ticket separado.
- **La forma sigue sin validación institucional.** La forma de cada
  tipo está marcada `PROVISIONAL_NO_INSTITUCIONAL` y el set de evaluación (#111)
  la tiene como PENDIENTE_SEU en su congelamiento.
- **El manifest del set de evaluación sigue congelado.** Su `slots_por_tipo`
  declara lo que declaraba al cortar; no se tocó (es la decisión registrada en
  `forma-declarada-y-modo-por-tipo-2026-10-17.md`).
