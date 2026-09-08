# Regresión consolidada y evidencia del corte 2026-09-08

- **Issue:** `SpendIce/Proyecto-Final#6`
- **Commit del corte:** `9d02a4f`
- **Alcance:** HU-010 y HU-011 en entorno local controlado con datos
  sintéticos.
- **Manifest de reconstrucción:** `evidencias/manifest-corte-2026-09-08.json`

## 1. Cómo leer este corte

Tres cosas distintas se registran por separado, porque se rompen por motivos
distintos y se arreglan de maneras distintas:

1. **Suite determinista.** No toca la red ni el modelo. Verifica contratos,
   gates, auditoría y caminos de falla.
2. **Benchmarks live.** Invocan un modelo local real. Miden latencia y
   conformidad mecánica sobre datos sintéticos.
3. **Dependencias institucionales.** Validación de la SEU, identidad y permisos
   de DSI, criterio del Gate G2. Ninguna se demuestra acá.

Mezclarlas produce afirmaciones que no se sostienen: una suite verde no dice
nada sobre la calidad del texto, y una corrida live conforme no dice nada sobre
aceptación institucional.

## 2. Suite determinista

`uv run pytest -q` sobre `9d02a4f`: **534 pruebas, todas verdes**.

Ese número describe el corte; no es un contrato. La suite se mide por lo que
cubre, no por su cardinalidad, y ninguna prueba fija la cantidad total. El
conteo sirve para notar una pérdida de cobertura entre cortes, no para
declararla suficiente.

Regresiones incorporadas en este corte:

| Defecto | Pruebas | Qué impiden |
|---|---|---|
| `DEF-A1-013` | 15 | Aceptar un presupuesto de decodificación que no cubre el documento máximo del contrato, y confundir el agotamiento con un fallo de generación |
| `DEF-A1-014` | 6 | Volver a pedirle al modelo una línea `Lugar:` que el gate rechaza, y aflojar los cuatro controles negativos de lugar |

Los cortes históricos de 451, 457 y 513 pruebas quedan como referencia y no
describen la candidata vigente.

## 3. Benchmarks live

Todos con `llama3.2:3b` local en CPU, temperatura 0, Ollama en loopback,
`num_predict` 512 por defecto.

### 3.1 HU-010 — gacetillas

Dos intentos por actividad sobre las tres actividades completas, con
`gacetilla_v3`:

| Configuración | Conformidad | Latencia | Reproducibilidad |
|---|---|---|---|
| `num_predict` 512, `gacetilla_v3` | 6/6 borradores | 7,26 a 11,47 s | borradores idénticos byte a byte entre intentos |

Los dos casos incompletos del dataset —`SYN-002` sin contacto y `SYN-004` sin
fecha— se siguen rechazando antes de invocar al modelo.

Detalle y hashes por borrador en
`evidencias/correccion-gacetillas-lugar-ausente-2026-09-08.md`.

### 3.2 HU-011 — posts

Dos contratos creativos, ejecutados por separado porque miden cosas distintas:

| Contrato | Aceptadas | Negativos conformes | Latencia | Errores observados |
|---|---|---|---|---|
| `post_creative_output_v2` (catálogo cerrado) | 6/6 | 4/4 | 7,87 a 19,13 s | ninguno en los casos positivos |
| `post_creative_output_v3` (redacción libre) | 0/6 | 4/4 | 14,24 a 35,09 s | `source_fact_in_creative_field` 6, `non_rioplatense_register` 6, `unauthorized_exclamation` 2, `unauthorized_fact_claim` 1 |

Manifests: `evidencias/manifest-hu011-live-v2-2026-09-08.json` y
`evidencias/manifest-hu011-live-v3-2026-09-08.json`.

**El 0/6 de v3 es el resultado esperado del cierre de `DEF-A1-013`, no una
regresión nueva.** Con `num_predict=112` esas seis generaciones se rechazaban
como `json_invalid`, es decir por truncamiento, y la falla de contenido quedaba
tapada. Con presupuesto suficiente aparece lo que realmente pasa: el modelo
mete hechos de la fuente en los campos creativos y escribe en un registro que
no es rioplatense. El gate los detecta y los rechaza, que es su trabajo.

Esto no contradice el corte del 2026-08-17, que registró 4/6 para v3: aquel
corte corrió antes de las regresiones de registro y tuteo que `DEF-A1-012`
incorporó el 26/08. Son gates distintos sobre el mismo contrato, no dos
mediciones del mismo control.

La brecha de contenido de v3 queda registrada en `DEF-A1-011` y `DEF-A1-007`,
que dependen de criterios que la SEU todavía no definió. No es un defecto que
el equipo técnico pueda cerrar por su cuenta.

### 3.3 Límites de los benchmarks

- Las latencias son de un host CPU concreto y no constituyen un SLA.
- La conformidad es mecánica: no demuestra verdad semántica, calidad editorial
  ni adecuación institucional.
- Un solo modelo, un solo dataset sintético, dos intentos por caso.

## 4. Reconstrucción del corte

`evidencias/manifest-corte-2026-09-08.json` registra el commit padre, la
configuración efectiva del adapter y el sha256 de las catorce fuentes
versionadas de las que depende cualquier corrida: dataset, contratos, política
de redes, prompts y los módulos que generan y validan.

El manifest no copia borradores, prompts renderizados, datos de actividades ni
identificadores institucionales. Un hash alcanza para verificar que una fuente
no cambió; copiar el contenido sería arrastrar material que la evidencia no
necesita.

Se regenera con `uv run python scripts/manifest_corte.py --corte AAAA-MM-DD`.

## 5. Estado de defectos en el alcance de la baseline

Cero defectos `CRITICA` abiertos, y cero defectos técnicos en estado `ABIERTO`.

| Estado | Defectos |
|---|---|
| `RESUELTO_TECNICO` | `DEF-A1-004`, `DEF-A1-008`, `DEF-A1-010`, `DEF-A1-013`, `DEF-A1-014` |
| `RESUELTO_PENDIENTE_VALIDACION` | `DEF-A1-003`, `DEF-A1-011`, `DEF-A1-012` |
| `CERRADO` | `DEF-A1-009` |
| `BLOQUEADO_EXTERNO` | `DEF-A1-001`, `DEF-A1-002`, `DEF-A1-005`, `DEF-A1-006`, `DEF-A1-007`, `DEF-A1-015` |

Los seis `BLOQUEADO_EXTERNO` no son defectos de software: son decisiones,
permisos o validaciones que aporta una contraparte institucional. Están
rastreados en los issues #14, #15, #16 y #17.

## 6. Lo que este corte no demuestra

- **Workspace live.** No hay OAuth, credenciales, identificadores
  institucionales ni una corrida real contra Google Workspace. Los adapters
  siguen verificados sólo offline (`DEF-A1-001`).
- **Validación de la SEU.** No existe acta, puntaje ni decisión registrada
  sobre ninguna muestra (`DEF-A1-005`).
- **Gate G2 y TRL 3.** No hay criterio de evidencia mínima ni decisión go/no-go
  registrada (`DEF-A1-006`).

Toda salida generada queda `BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.
