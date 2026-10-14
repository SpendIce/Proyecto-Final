# Ciclo `up` → `down` → esquema original — PostgreSQL efímero

- **Fecha:** 2026-10-14
- **Issue:** #95 (CI prueba las migraciones `down`; reversión de #66).
- **Motor:** PostgreSQL 16.15 (`postgres:16-alpine`) en un contenedor efímero
  local, puerto 55432, eliminado al terminar.
- **Cliente:** `psql` 18.6.
- **Datos:** ninguno. El ciclo crea un esquema desechable (`agente1_mig_<pid>`),
  lo usa como `search_path` y lo borra; nunca toca `public` ni datos
  institucionales.
- **Alcance:** verifica que el `down` de cada migración devuelva el esquema al
  estado previo. No integra un adapter PostgreSQL al producto, no prueba
  concurrencia, performance, permisos DSI ni respaldo/restauración, y no
  acredita TRL.

## Comando ejecutado

```bash
docker run -d --rm --name agente1-pg -e POSTGRES_PASSWORD=postgres \
  -p 55432:5432 postgres:16-alpine
cd Implementacion/Agente1
AGENTE1_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/postgres" \
  uv run pytest -q tests/test_migraciones_down_ciclo.py
```

El procedimiento de la prueba está en `tests/test_migraciones_down_ciclo.py`:
para cada migración crea el esquema, aplica las `up` hasta ella, toma un
snapshot canónico del motor (tablas, columnas, secuencias, constraints,
índices, triggers, funciones vía `information_schema` y `pg_get_*def`), aplica
su `up` y su `down`, y exige que el snapshot final sea idéntico al anterior.

## Resultado

```
tests/test_migraciones_down_ciclo.py::test_toda_migracion_declara_su_reversibilidad PASSED
tests/test_migraciones_down_ciclo.py::test_down_devuelve_el_esquema_anterior[0001_persistencia_agente1] PASSED
tests/test_migraciones_down_ciclo.py::test_down_devuelve_el_esquema_anterior[0002_integridad_referencial_borradores] PASSED
tests/test_migraciones_down_ciclo.py::test_down_devuelve_el_esquema_anterior[0003_rechazo_timestamps_futuros] PASSED

4 passed in 1.39s
```

Esquema comparado por migración (líneas del snapshot): `0001` 0 (= esquema
vacío, antes y después); `0002` 126; `0003` 134.

Suite completa con el servicio levantado: **2010 passed in 54.74s**.

## Control negativo (la prueba no es vacía)

Se eliminó a mano la línea `DROP FUNCTION agente1_rechazar_timestamp_futuro();`
del `down` de `0003` y se repitió la corrida con el DSN definido: **1 failed,
3 passed**, con el `FUNCTION agente1_rechazar_timestamp_futuro` reportado como
presente sólo en el estado previo. Restaurado el archivo, `git status` quedó
limpio. Esto confirma que el ciclo detecta un `down` que no deshace su `up`.

## Sin base

Sin `AGENTE1_POSTGRES_DSN`, la suite determinista corre igual: **2007 passed, 3
skipped**. El ciclo de migraciones se saltea porque no hay adapter PostgreSQL
cableado al producto.

## Hashes de las migraciones probadas (sha256)

| Archivo | sha256 |
| --- | --- |
| `0001_persistencia_agente1.up.sql` | `b87d67dc6c0220f73d61b0c44417d397e56d1a715be57d817960feef4a023b14` |
| `0001_persistencia_agente1.down.sql` | `a576d7b8ad9eeb18068f50c04956b5bf0a5304a87c8c26df1311479f236fa0a0` |
| `0002_integridad_referencial_borradores.up.sql` | `50b73789fc6065feb11c9fae9193bd6578ef79a46733dfb0a23fe3c48700d7d5` |
| `0002_integridad_referencial_borradores.down.sql` | `24caa7a9a9c2001280f48a17339f1898fc63af2c63a06ad61dbac358d104bb7a` |
| `0003_rechazo_timestamps_futuros.up.sql` | `aed22abf995168bda154b790a4a1a45afbd7dc3fddafe9f5a6c85e128144d72d` |
| `0003_rechazo_timestamps_futuros.down.sql` | `41980a7780ec285ffbfcc728dfbbfd59a009fde62dcb22c4630711c42f1e2867` |

## Límites

El job `agente1-ci` (GitHub Actions) **no se ejecutó**: no hay runner disponible
en este host. El workflow se modificó para levantar el servicio
`postgres:16-alpine` y se validó sintácticamente (`yaml.safe_load`), pero su
corrida en el runner queda pendiente de un push/PR.
