<!--
Plantilla de PR del Agente 1 (issue #96). Completá cada sección y borrá lo que no
aplique. El circuito completo de cambios controlados está en CONTEXT.md (término
"Cambio controlado") y en la decisión #66.

Un PR que solo toca documentación también pasa el check requerido `agente1-ci`:
el workflow siempre corre y, si no hay cambios bajo `Implementacion/Agente1/`,
saltea la suite y reporta conforme.
-->

## Qué cambia y por qué

<!-- Una o dos oraciones: qué se modifica y para qué. -->

## Issue

<!-- Obligatorio. -->
- Issue: #

## Clase del cambio

Marcá todas las que apliquen. La clase define quién aprueba (decisión #66) y si
el corte de versión es Mayor, Menor o Parche
(`Implementacion/Agente1/PROCEDIMIENTO-CORTE-DE-VERSION.md`).

- [ ] **Código** — `src/`, `tests/`, `migrations/`, `scripts/`, `systemd/`, `uv.lock`, `pyproject.toml`.
- [ ] **Prompts y parámetros de inferencia** — prompts, modelo, `num_predict`, temperatura, presupuesto de decodificación.
- [ ] **Criterios de contenido de la SEU** — políticas de redes, tono, reglas de gate, catálogo de contenido. Siguen su propio circuito de aprobación; este PR lo reconoce, no lo duplica.
- [ ] **Contratos** — schemas y contratos de interfaz (insumos, planilla, Historia Viva, tipos de notificación).
- [ ] **Configuración de Workspace y credenciales** — IDs, scopes, cuenta técnica, unidad compartida.

<!-- Los cambios que se le piden a DSI en la consola de Google no cortan versión:
     se anotan en la sección *Configuración* de Implementacion/Agente1/CHANGELOG.md
     al pedirlos (fecha, motivo y quién aprobó), no en este PR. -->

## Si es un prompt o un parámetro de inferencia

<!-- Completá solo si marcaste esa clase; si no, borrá esta sección. -->

- HU afectada: HU-
- [ ] Adjunto la **matriz de regresión de la HU afectada**, corrida contra la versión nueva del prompt/parámetro.
- Resultado: <!-- p. ej. 6/6 conformes, o los códigos que quedan NO_CONFORME y su motivo -->

## Versión y manifest de versión

Rutas controladas (las que el manifest hashea): `src/` (incluye prompts,
políticas y contratos), `migrations/`, `uv.lock`, `pyproject.toml`, `scripts/`,
`systemd/`. Regla, número y comandos:
`Implementacion/Agente1/PROCEDIMIENTO-CORTE-DE-VERSION.md`.

- [ ] Este PR **no** toca rutas controladas.
- [ ] Este PR toca rutas controladas y **corta versión**: subí `[project].version` en `pyproject.toml`, regeneré el manifest (`cd Implementacion/Agente1 && uv run python scripts/manifest_version.py --salida manifest-version.json`) y agregué la entrada al `CHANGELOG.md`. Versión nueva: `0._._`.
- [ ] Este PR toca rutas controladas y **no** corta versión: dejo constancia de que `manifest-version.json` queda en el último corte, **por diseño** (sección 3 del procedimiento). Entre versiones el host corre la versión etiquetada anterior, no `main`.

## Evidencia de verificación

<!-- Obligatorio: pegá el resultado real, no una promesa. -->

- [ ] `cd Implementacion/Agente1 && uv run pytest -q` — resultado: <!-- N verdes -->
- [ ] `cd Implementacion/Agente1 && uv run ruff check .` — sin hallazgos.
- [ ] Otra evidencia: <!-- p. ej. `uv run pytest -q tests/test_migraciones_down_ciclo.py` con PostgreSQL efímero, corrida live en D2, medición de conformidad -->

## Revisión con `/code-review`

Práctica **recomendada**, no check requerido. Corré `/code-review` sobre la rama
antes de pedir el merge.

- Resultado de `/code-review`: <!-- hallazgo o "sin bloqueantes" -->

## Checklist

- [ ] El PR referencia un issue.
- [ ] La clase del cambio y quién aprueba coinciden con la decisión #66.
- [ ] No hay secretos ni datos institucionales en el diff (IDs internos, correo de la cuenta técnica, tokens, client secret).
- [ ] Si el cambio toca lo que se instala en el host, se cortó la versión según el procedimiento (paso 6: tag sobre `main`).
