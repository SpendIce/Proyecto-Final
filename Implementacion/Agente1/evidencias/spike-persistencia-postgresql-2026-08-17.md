# Spike de persistencia PostgreSQL — Agente 1

**Fecha de corte:** 2026-08-17  
**Alcance:** diseño y prueba contractual offline  
**Estado:** `PREPARADO_NO_EJECUTADO`

## 1. Objetivo y límite epistemológico

Este spike prepara un puerto de persistencia y SQL versionado para registrar el
ciclo de vida de solicitudes, ejecuciones, borradores, validaciones, defectos y
eventos. No instala PostgreSQL, no agrega drivers, no abre una conexión y no
ejecuta migraciones. Por lo tanto, **no demuestra operación PostgreSQL**, no
reemplaza los JSONL actuales y no aporta por sí solo evidencia de TRL 3.

El artefacto ejecutable hoy es el adapter en memoria usado por contract tests.
El SQL queda preparado para una validación posterior en un PostgreSQL efímero y,
recién después, en el entorno que DSI autorice.

## 2. Frontera del módulo

`RepositorioEjecuciones` modela operaciones completas del caso de uso, no CRUD
de tablas:

1. `iniciar`: crea solicitud y ejecución en forma idempotente;
2. `completar`: cambia el resultado y, si corresponde, crea el borrador y evento;
3. `registrar_validacion`: actualiza validación, borrador, ejecución y evento;
4. `registrar_defecto`: crea defecto y su evento auditable;
5. `obtener_por_idempotencia`: permite cortar reintentos duplicados;
6. `eliminar_logicamente_anteriores`: aplica retención sin perder trazabilidad.

El adapter no persiste textos de entrada, prompts, cuerpos, emails, contactos ni
tokens. Conserva identificadores técnicos, estados, timestamps zonados, códigos,
hashes SHA-256 y referencias ya hasheadas. El contenido continúa bajo la
responsabilidad de Sheets, Drive/Docs y los borradores locales.

## 3. Invariantes

- `idempotency_key` y `correlation_id` son únicos.
- Identificadores, HU, fuente, canal, resultado y códigos se validan contra
  regex o allowlists cerradas; el tipo de evento se deriva internamente y nunca
  copia texto provisto por el caller.
- Reutilizar una clave con otra solicitud, hash, HU, fuente o correlación falla;
  una repetición idéntica devuelve la ejecución existente.
- Una solicitud conserva su `input_hash`, fuente y fecha original: otra ejecución
  no puede cambiarle la fuente ni presentarse con una fecha anterior.
- Sólo `INICIADA` puede pasar al resultado de generación.
- `PENDIENTE_VALIDACION` exige borrador y `output_hash` coincidentes.
- Una ejecución fallida o incompleta no puede crear borrador.
- Una validación sólo se registra una vez y sólo sobre un borrador pendiente.
- Todos los timestamps incluyen zona horaria; PostgreSQL usa `TIMESTAMPTZ`.
- Ninguna operación acepta timestamps futuros respecto de su reloj. Validación
  y defecto no pueden preceder al agregado que justifican; corte y eliminación
  también deben respetar el orden temporal.
- La retención sólo alcanza ejecuciones terminales, marca `eliminado_en` y no
  hace `DELETE` operativo; nunca elimina un borrador pendiente de validación.

## 4. Atomicidad prevista para PostgreSQL

Cada método mutante corresponde a **una transacción**. El adapter futuro debe
usar consultas parametrizadas y este orden:

### Inicio idempotente

1. `BEGIN` con aislamiento `READ COMMITTED`;
2. insertar/validar solicitud;
3. insertar ejecución con las restricciones únicas;
4. si hay conflicto de idempotencia, leer la fila existente y comparar la firma;
5. insertar `ejecucion_iniciada`;
6. `COMMIT`, o `ROLLBACK` ante cualquier diferencia/error.

### Resultado y validación

1. bloquear la ejecución/borrador con `SELECT ... FOR UPDATE`;
2. validar el estado de origen;
3. actualizar estado y crear registros dependientes;
4. insertar el evento en la misma transacción;
5. confirmar solamente si todas las sentencias tienen éxito.

Las constraints SQL constituyen la última defensa estructural y lexical; sus
allowlists de resultado/error se alinean con el puerto, pero no sustituyen sus
transiciones ni controles temporales bajo lock. `SERIALIZABLE` agregaría costo y
reintentos; no se justifica mientras el flujo bloquee por agregado y las claves
únicas arbitren duplicados.

## 5. Migraciones

- Forward: `migrations/0001_persistencia_agente1.up.sql`.
- Rollback destructivo del spike: `migrations/0001_persistencia_agente1.down.sql`.

El rollback sólo es defendible antes de almacenar evidencia real. Después de un
piloto debe reemplazarse por una migración compensatoria o exportación aprobada;
no se debe destruir trazabilidad institucional para volver de versión.

Validación pendiente antes de aceptar el adapter PostgreSQL:

1. ejecutar forward y rollback en una base efímera vacía;
2. volver a ejecutar forward luego del rollback;
3. correr los mismos contract tests contra ambos adapters;
4. probar carreras sobre `idempotency_key` y `correlation_id`;
5. medir latencia y verificar el plan de índices;
6. revisar backup, restauración, retención y permisos con DSI.

## 6. Fallback JSONL y migración futura

Los JSONL existentes son evidencia append-only, no una base transaccional. Ante
indisponibilidad futura de PostgreSQL se propone un **spool separado**, todavía
no implementado:

- un envelope versionado por operación, sin contenido sensible;
- `event_id`, idempotency key, correlation ID, timestamp, tipo y hashes;
- escritura durable local y permisos mínimos;
- replay ordenado e idempotente; nunca asumir éxito por haber escrito el spool;
- estado visible `PERSISTENCIA_DIFERIDA`, sin habilitar publicación o envío.

Plan de migración sin ejecutar:

1. congelar y hashear cada JSONL fuente;
2. validar schema, duplicados y timestamps en un dry-run;
3. transformar sólo metadatos compatibles a envelopes versionados;
4. importar por lotes transaccionales usando idempotency keys derivadas;
5. reconciliar conteos y hashes; aislar filas inválidas sin descartarlas;
6. emitir manifest y acta técnica; conservar originales según retención aprobada.

No se debe inferir una validación SEU histórica desde un log de generación. Una
validación sólo ingresa si existe evidencia separada con decisión, checklist y
referencia opaca del validador.

## 7. Trazabilidad Gantt, DoD y TRL

| Elemento | Aporte del spike | Lo que falta | Estado |
|---|---|---|---|
| Sprint 3 / persistencia | Puerto, adapter memoria, esquema y rollback | PostgreSQL/driver, adapter, prueba efímera y DSI | `PREPARADO` |
| HU-010/HU-011 / trazabilidad | Estados, hashes, correlación, idempotencia y eventos | Integración con runners y evidencia live | `PARCIAL` |
| DoD técnico | Contract tests offline y checks estáticos SQL | Contract tests reales, backup/restore y performance | `PENDIENTE` |
| Gate G2 / TRL 3 | No lo eleva | Conformidad Ollama, Workspace live, validación SEU y decisión formal | `PENDIENTE` |

## 8. Decisión de continuidad

No integrar este puerto al core ni reemplazar JSONL hasta que el runner end-to-end
esté estabilizado y exista una prueba del adapter PostgreSQL. La alternativa de
adoptar ahora PostgreSQL brinda constraints y consultas, pero agrega operación,
credenciales, backup y recuperación. Mantener JSONL por el momento reduce costo,
pero no ofrece transacciones ni arbitraje robusto de concurrencia. El spike deja
ambos caminos explícitos sin fingir una necesidad ya validada.
