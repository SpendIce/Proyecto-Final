# Procedimiento de reversión — Agente 1

- **Estado:** vigente para el esquema 0001–0003; se actualiza con cada migración nueva.
- **Alcance:** cómo volver a la versión anterior del Agente 1 revirtiendo el esquema
  sin restaurar el respaldo de Drive, y cuándo esa vía no alcanza.
- **Relacionados:** ADR 0009 (respaldo diario y retención), ADR 0010 (arranque
  fail-closed por manifest de versión), decisión #66 (control de cambios),
  issue #95 (CI prueba las migraciones `down`). El manual de operación (#81)
  cita este documento; no lo reemplaza.

## 1. Qué se revierte

Volver a la versión anterior del Agente 1 tiene dos partes independientes:

1. **La versión del agente.** El host reinstala la versión etiquetada anterior.
   Como el agente no arranca si sus archivos controlados no coinciden con el
   manifest de su versión (ADR 0010), no alcanza con copiar el código: hay que
   volver al conjunto completo (código, prompts, políticas, contratos,
   migraciones y `uv.lock`) que corresponde a esa versión.
2. **El esquema de la base.** Cada migración numerada en
   `Implementacion/Agente1/migrations/` tiene su archivo `down` que deshace su
   `up`. Aplicar los `down` en orden inverso deja el esquema en el estado que la
   versión anterior espera.

Este documento trata la segunda parte. La prueba mecánica de que los `down`
devuelven el esquema al estado previo vive en
`Implementacion/Agente1/tests/test_migraciones_down_ciclo.py` y la corre el job
`agente1-ci`: para cada migración aplica las `up` hasta ella, aplica su `down` y
exige que el esquema quede idéntico al anterior. Si un `down` se rompe, la suite
falla.

## 2. Regla de decisión

**Alcanza con aplicar el `down`** cuando la migración que se revierte no
descarta filas almacenadas y el estado que quedó en el host sigue siendo válido
para la versión anterior. Es el caso de las migraciones que sólo agregan
restricciones, columnas derivadas, triggers o funciones.

**Hay que restaurar el respaldo de Drive (ADR 0009)** cuando el `down` descarta
datos que no se pueden reconstruir. En ese caso el `down` recupera la
*estructura* anterior pero no la información, y la única copia confiable de esa
información es el respaldo diario.

La clasificación es un dato versionado: cada migración se declara en
`REVERSIBILIDAD` dentro de `tests/test_migraciones_down_ciclo.py`, y la suite
falla si una migración nueva no trae su declaración o si un `down` que pierde
datos no queda marcado como «restaurar respaldo». Esta tabla refleja esa
declaración; ante cualquier divergencia manda el código.

| Migración | `down` reversible | ¿Pierde datos? | Vía de reversión |
| --- | --- | --- | --- |
| `0001_persistencia_agente1` | Sí (estructura) | **Sí** — elimina las seis tablas del esquema operativo | **Restaurar el respaldo** si hay filas; el `down` sólo sirve sobre una base vacía |
| `0002_integridad_referencial_borradores` | Sí | No — elimina la columna derivada `borrador_creada_en` y sus restricciones (se reconstruye desde `borradores.creada_en`) | Alcanza con el `down` |
| `0003_rechazo_timestamps_futuros` | Sí | No — elimina dos triggers y su función | Alcanza con el `down` |

Nota sobre `0002`: aunque no pierde información de negocio, su `down` **reabre
las brechas de integridad referencial** que la migración cerró. Revirtiendo
`0002` la base vuelve a aceptar borradores colgados de ejecuciones `FALLIDA`,
`INCOMPLETA` o `INICIADA`, y validaciones anteriores al borrador. Por eso sólo es
defendible mientras no haya evidencia institucional real almacenada; si la hay,
conviene restaurar el respaldo en lugar de revertir el esquema contra una base
con datos.

## 3. Procedimiento

### 3.1 Revertir sin restaurar el respaldo

1. Suspender el agente (no corregir en caliente; ver «Cambio de emergencia» en
   `CONTEXT.md`).
2. Confirmar con la tabla de la sección 2 que las migraciones a revertir no
   pierden datos.
3. Aplicar los `down` en orden inverso al de las `up`, con un cliente SQL y
   `ON_ERROR_STOP=1` para que un error frene en el acto.
4. Reinstalar la versión anterior del agente según su manifest (ADR 0010) y
   arrancar.
5. Registrar el cambio en la auditoría: qué versión se dejó, qué migraciones se
   revirtieron y quién lo autorizó, siguiendo el circuito de cambio controlado
   (#66).

### 3.2 Restaurar el respaldo

Cuando el `down` descarta datos (sección 2):

1. Suspender el agente.
2. Restaurar el último respaldo diario de la carpeta de la cuenta técnica
   (ADR 0009).
3. Tratar toda reserva o aprobación posterior al respaldo como
   `ENVIO_INDETERMINADO`: no reenviar hasta cruzarla contra Gmail Enviados
   (ADR 0009).
4. Reinstalar la versión anterior del agente y arrancar.
5. Registrar el incidente y la restauración en la auditoría.

### 3.3 Verificar la reversibilidad antes de desplegar

El ciclo de migraciones se puede correr a mano contra un PostgreSQL efímero,
igual que lo hace `agente1-ci`:

```bash
docker run -d --rm --name agente1-pg -e POSTGRES_PASSWORD=postgres \
  -p 55432:5432 postgres:16-alpine
cd Implementacion/Agente1
AGENTE1_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/postgres" \
  uv run pytest -q tests/test_migraciones_down_ciclo.py
```

Sin la variable `AGENTE1_POSTGRES_DSN` el caso se saltea: no hay adapter
PostgreSQL cableado al producto y la suite determinista no exige un motor.

## 4. Nota para el manual de operación (#81)

> **#81 — citar en el manual:** la sección «Reversión» del manual de operación
> debe enlazar a `Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md`
> para el detalle de cuándo alcanza el `down` y cuándo se restaura el respaldo,
> sin repetir la tabla ni el procedimiento.
