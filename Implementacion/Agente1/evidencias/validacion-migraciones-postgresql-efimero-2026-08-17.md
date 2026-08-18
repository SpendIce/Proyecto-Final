# Validación de migraciones sobre PostgreSQL efímero — 2026-08-17

**Alcance:** ejecución real del SQL del spike de persistencia
**Estado previo:** `PREPARADO_NO_EJECUTADO`
**Estado tras este corte:** `EJECUTADO_EN_EFIMERO` — puntos 1 y 2 del checklist del spike cerrados

## 1. Qué demuestra y qué no

El spike `spike-persistencia-postgresql-2026-08-17.md` dejó el SQL preparado sin
ejecutarlo nunca y afirmaba que las constraints constituían «la última defensa
estructural y lexical». Este corte **ejecuta** ese SQL contra PostgreSQL 16 real
y **verifica esa afirmación caso por caso**.

No demuestra operación institucional: la base es efímera, en contenedor local,
sin datos reales, sin backup, sin permisos DSI y sin adapter Python. No reemplaza
los JSONL ni aporta por sí solo evidencia de TRL 3.

## 2. Entorno

| Componente | Valor |
| --- | --- |
| Motor | PostgreSQL 16 (`postgres:16-alpine`) |
| Modo | contenedor efímero local, descartado al finalizar |
| Datos | sintéticos, generados en el propio corte |
| Adapter Python | **no existe**; las pruebas son SQL directo |

## 3. Ciclo forward / rollback / forward

Checklist del spike, puntos 1 y 2:

| Paso | Resultado | Verificación |
| --- | --- | --- |
| Forward `0001` sobre base vacía | OK | 6 tablas, 14 índices, 44 CHECK, 5 FK, 4 UNIQUE |
| Rollback `0001` | OK | 0 tablas restantes |
| Forward `0001` nuevamente | OK | 6 tablas |

Las tablas creadas son `solicitudes`, `ejecuciones`, `borradores`,
`validaciones`, `defectos` y `eventos_ejecucion`.

## 4. Invariantes que el SQL sí hace cumplir

Doce intentos de inserción inválida fueron rechazados por el motor:

| Intento | Resultado |
| --- | --- |
| `idempotency_key` duplicada | RECHAZADO |
| `correlation_id` duplicado | RECHAZADO |
| `INICIADA` con `output_hash` | RECHAZADO |
| `PENDIENTE_VALIDACION` sin `output_hash` | RECHAZADO |
| Estado fuera de la allowlist (`PUBLICADA`) | RECHAZADO |
| `hu` con formato inválido | RECHAZADO |
| `finalizada_en` anterior a `creada_en` | RECHAZADO |
| `INICIADA` con `finalizada_en` | RECHAZADO |
| Canal de borrador fuera de allowlist (`twitter`) | RECHAZADO |
| `input_hash` no hexadecimal | RECHAZADO |
| `fuente_tipo` no permitida (`scraping`) | RECHAZADO |
| Decisión de validación fuera de allowlist | RECHAZADO |

## 5. Brechas estructurales encontradas

Cinco invariantes documentadas en el spike **no** estaban cubiertas por el
esquema. En filas limpias, el motor aceptó cada una:

| # | Invariante documentada | `0001` |
| --- | --- | --- |
| 1 | Una ejecución fallida o incompleta no puede crear borrador | no aplicada |
| 2 | El `output_hash` del borrador corresponde al de su ejecución | no aplicada |
| 3 | Una validación no puede preceder al borrador que evalúa | no aplicada |
| 4 | Ningún timestamp de validación en el futuro | no aplicada |
| 5 | Ninguna ejecución con `creada_en` futura | no aplicada |

Con `0001` sola quedaron persistidos **tres borradores colgados de ejecuciones
en estado inválido** y **una validación con fecha futura**.

Nota metodológica: dos rechazos observados en la primera pasada resultaron ser
**falsos positivos**, producidos por las restricciones `UNIQUE` de
`borradores.id_ejecucion` y `validaciones.id_borrador` y no por la invariante que
se pretendía probar. Se repitieron sobre filas limpias antes de concluir. Un
rechazo sólo cuenta como evidencia si se identifica **qué constraint** lo produjo.

## 6. Migración `0002` — corrección

`0002_integridad_referencial_borradores.up.sql` cierra las brechas 1, 2 y 3.

Las brechas 1 y 2 se cierran con **una sola restricción**. `0001` ya garantiza
por CHECK que `output_hash` es `NOT NULL` únicamente en `PENDIENTE_VALIDACION`,
`APROBADA` o `RECHAZADA`. Como `borradores.output_hash` es `NOT NULL`, una clave
foránea compuesta sobre `(id_ejecucion, output_hash)` obliga a que el hash
coincida y, por transitividad, a que la ejecución referenciada esté en un estado
de borrador válido.

La brecha 3 se cierra desnormalizando `borrador_creada_en` en `validaciones`,
atándola al agregado original con una clave foránea compuesta y comparándola con
un CHECK inmutable.

### Verificación con atribución de constraint

| Caso | Resultado | Constraint que actúa |
| --- | --- | --- |
| Borrador sobre ejecución `FALLIDA` | RECHAZADO | `borradores_ejecucion_output_fk` |
| Borrador sobre ejecución `INCOMPLETA` | RECHAZADO | `borradores_ejecucion_output_fk` |
| Borrador sobre ejecución `INICIADA` | RECHAZADO | `borradores_ejecucion_output_fk` |
| Borrador con `output_hash` distinto | RECHAZADO | `borradores_ejecucion_output_fk` |
| Borrador legítimo | ACEPTADO | — |
| Validación anterior al borrador | RECHAZADO | `validaciones_no_preceden_al_borrador` |
| Validación con fecha de borrador falsa | RECHAZADO | `validaciones_borrador_creada_fk` |
| Validación legítima | ACEPTADO | — |

Estado final: un borrador, una validación, **cero huérfanos**. El camino feliz no
se rompió. El rollback de `0002` ejecuta limpio.

## 7. Brechas 4 y 5 — decisión pendiente, no cerrada

Los controles de timestamp futuro **no** se agregaron. Requerirían `now()` dentro
de un CHECK, es decir una función no inmutable.

Se verificó empíricamente que PostgreSQL 16 acepta y aplica
`CHECK (ts <= now())` al insertar, y que en la dirección «no futuro» es seguro
ante restauración, porque un timestamp pasado sigue siendo pasado. Aun así es un
antipatrón documentado y el spike ya asigna los controles temporales al puerto
bajo lock.

Queda como **decisión explícita para revisión**, no como brecha silenciada. Hoy
esas dos invariantes dependen únicamente del puerto Python: cualquier escritura
directa a la base puede violarlas.

## 8. Pendiente del checklist del spike

| Punto | Estado |
| --- | --- |
| 1. Forward y rollback en base efímera | **cerrado** |
| 2. Forward nuevamente tras rollback | **cerrado** |
| 3. Mismos contract tests contra ambos adapters | pendiente — no existe adapter PostgreSQL |
| 4. Carreras sobre `idempotency_key` y `correlation_id` | pendiente |
| 5. Latencia y plan de índices | pendiente |
| 6. Backup, restauración, retención y permisos con DSI | pendiente — bloqueado externamente |

## 9. Límites

- La base fue efímera y se descartó; no hay entorno persistente.
- No existe adapter PostgreSQL, driver ni integración con el core.
- Los JSONL siguen siendo el registro operativo vigente.
- No se probaron concurrencia, backup, restauración ni permisos.
- Esta evidencia no acredita el Gate G2 ni TRL 3.
