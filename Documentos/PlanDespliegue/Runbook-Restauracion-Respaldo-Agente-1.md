# Runbook de restauración desde respaldo (Agente 1)

- **Estado:** procedimiento manual del operador designado; el agente no lo
  dispara nunca y no usa red (el artefacto se baja de Drive por el canal
  habitual y se trae al host).
- **Alcance:** reconstruir el estado local del agente (directorio de
  salida, registro durable de confirmaciones y base PostgreSQL del canal
  web) desde un artefacto `agente1-respaldo-AAAA-MM-DD.tar.gz`.
- **Relacionados:** ADR 0009 (respaldo y ventana de reconciliación), ADR
  0016 (persistencia del canal web), migración 0012 (cola durable de
  emisiones de certificados web, #168), `Runbook-Scheduler-Agente-1.md`
  §6 y `Runbook-Contenedores-Agente-1.md`.

## 1. Regla de oro: nada corre mientras se restaura

La importación del volcado y la marca de indeterminadas son una sola
transacción `psql` (ningún proceso ve la cola restaurada a medias), pero
hay efectos que la base no puede cancelar: **un worker vivo podría
terminar un envío real durante la restauración y ese correo quedaría
fuera del mundo restaurado**, invisible para la reconciliación. Por eso
la restauración se corre siempre con el agente detenido.

## 2. Detener el agente

En el stack `agente1` de Portainer detener **todos** los servicios que
producen o consumen trabajo (incluido el worker de certificados web):

- `scheduler` (corridas y respaldo diario),
- `worker` (cola del canal web),
- `worker-certificados` (cola durable de emisiones de certificados),
- `web` (acepta pedidos y los encola).

Desde Portainer: *Stacks → agente1* y detener los servicios. Desde la
consola del host, equivalente:

```bash
docker compose -p agente1 stop scheduler worker worker-certificados web
```

`postgres`, `ollama` y `modelo` quedan corriendo: la restauración los
necesita.

## 3. Restaurar

```bash
cd <CHECKOUT>/Implementacion/Agente1
PYTHONPATH=src \
  python scripts/restaurar_respaldo.py \
    --artefacto agente1-respaldo-2026-10-05.tar.gz \
    --salida <directorio-salida> \
    --registro <directorio-registro> \
    --postgres-dsn <DSN-de-la-base-del-canal-web>
```

El script verifica el manifiesto (record, marca `creado_en`, sha256 por
miembro) antes de tocar nada; un artefacto que no verifica se rechaza
entero. Los archivos se reponen **sin pisar lo existente**: idéntico se
omite, distinto se reporta como `conflicto`. El volcado de PostgreSQL se
aplica con `psql --single-transaction` y en la **misma** transacción se
marca la cola durable de emisiones (§5): si algo falla a mitad, la base
queda como estaba: no hay restauración parcial.

Usar el `psql` del stack (cliente 16, como el servidor). Un volcado
generado por un `pg_dump` más nuevo puede traer `SET` que el servidor 16
no reconoce: el restore falla cerrado, sin tocar la base.

## 4. Verificar el informe antes de seguir

Salida `{"status": "OK", ...}` con estos campos:

- `emisiones_pg_indeterminadas`: cuántos trabajos reales de la cola
  durable de emisiones quedaron `INDETERMINADA` (`null` si el artefacto
  no traía volcado; `-1` si el conteo no pudo leerse del `psql`).
- `indeterminados` y `claves_indeterminadas`: reservas y aprobaciones del
  registro de confirmaciones marcadas `ENVIO_INDETERMINADO`.
- `conflictos`: archivos presentes con contenido distinto: revisarlos a
  mano antes de arrancar.
- La auditoría del respaldo (`logs/respaldo-diario.jsonl`, evento
  `restauracion_respaldo`) asienta los mismos conteos con hashes.

Sin `status: OK` no se avanza: el `error_code` dice en qué etapa cayó y
nada quedó aplicado a medias.

## 5. Qué quedó indeterminado y por qué

- **Cola durable de emisiones web (`emisiones_certificados`).** Todo
  trabajo real que el snapshot dejó capaz de enviar (`PENDIENTE`,
  `RESERVADA`, `ENVIANDO`) pasa a `INDETERMINADA` en la misma transacción
  del volcado: terminal, sin reserva posible. Un envío que ocurrió
  después del respaldo no se repite. Lo ya terminado (`EMITIDA`,
  `EMITIDA_PARCIAL`, `FALLIDA`, `INDETERMINADA`, `EXPIRADA`) y los
  trabajos demo no se tocan: el demo no tiene efectos externos y se
  vuelve a pedir si hace falta. Un respaldo anterior a la migración 0012
  no tiene la tabla y la marca es un no-op.
- **Registro de confirmaciones.** Reservas interrumpidas y aprobaciones
  posteriores a la marca del respaldo, `ENVIO_INDETERMINADO` /
  `EMISION_INDETERMINADA` como siempre.

Nada indeterminado se reenvía ni se emite solo: una persona cruza cada
caso contra Gmail Enviados (y, para certificados, el destino de emisión)
antes de decidir. Es el mismo criterio de siempre: el agente no asume ni
el sí ni el no.

Un lote real pendiente o aprobado que vuelve sin trabajo de emisión también queda cercado con un resultado indeterminado: el trabajo pudo crearse y ejecutarse después de la copia. La marca no afirma que se haya enviado nada; exige revisar antes de emitir.

La copia no contiene solicitudes creadas después de su fecha. Antes de habilitar el servicio, el operador debe cruzar las entregas posteriores a esa fecha con Gmail Enviados y conservar el registro de reconciliación. Un pedido que falta en el respaldo no es evidencia de que no haya sido entregado. Esta revisión también es necesaria con respaldos anteriores a la migración 0012.

## 6. Antes de arrancar: permisos del esquema

El volcado se genera con `--no-owner --no-privileges`: las tablas recreadas quedan con el dueño del DSN de restauración y pierden las concesiones. El migrador no vuelve a aplicar una migración ya asentada en la copia. Antes de arrancar, un administrador debe restituir los permisos en el mismo esquema restaurado:

- `0005_roles_canal_web.up.sql`: roles, todos los `GRANT`, el bloque de lectura de secuencias y `ALTER TABLE prosa_transitoria OWNER TO agente1_mantenimiento`. Esta migración admite reaplicación sobre tablas existentes.
- `0009_ajuste_generativo.up.sql`: `GRANT SELECT, INSERT ON ajustes TO agente1_app` y `GRANT SELECT ON ajustes TO agente1_mantenimiento`.
- `0010_lote_certificados_web.up.sql`: todos sus `GRANT` sobre `lotes_certificados`, incluidas las columnas de decisión para la aplicación y las de purga para mantenimiento.
- `0011_permisos_ajuste_prosa.up.sql`: `GRANT UPDATE (id_borrador) ON prosa_transitoria TO agente1_app`.
- `0012_emision_certificados_durable.up.sql`, cuando esa tabla exista: todos sus `GRANT` sobre `emisiones_certificados`.
- `GRANT USAGE ON SCHEMA` del esquema elegido para ambos roles.

De 0009 a 0012 se reaplican únicamente las sentencias de permisos: ejecutar enteras esas migraciones repetiría creación de tablas o columnas. No ampliar a `GRANT ALL`: la aplicación conserva prohibido modificar el texto de prosa o la auditoría. Verificar como mínimo, en el esquema elegido:

```sql
SELECT has_column_privilege('agente1_app', 'prosa_transitoria', 'id_borrador', 'UPDATE'),
       has_column_privilege('agente1_app', 'prosa_transitoria', 'texto', 'UPDATE');
-- Debe devolver true, false.
SELECT tableowner FROM pg_tables
 WHERE schemaname = current_schema() AND tablename = 'prosa_transitoria';
-- Debe devolver agente1_mantenimiento (necesario también para VACUUM).
```

Comprobar además lectura/reserva de la cola como `agente1_app` y lectura de estados como `agente1_mantenimiento`, sin ejecutar entregas. Mantener los servicios detenidos si alguna comprobación falla.

## 7. Recién ahí, arrancar

Con el informe `OK` revisado, los conflictos resueltos y los permisos
reaplicados:

```bash
docker compose -p agente1 start web worker worker-certificados scheduler
```

Los indeterminados quedan visibles para intervención humana: no vuelven a
la cola nunca.

## 8. Volver a la imagen 0.9.0

El rollback conserva la migración 0012: no ejecutar su down ni borrar el registro de emisiones. Detener `worker-certificados` antes del cambio y mantenerlo apagado con la imagen anterior. Una ejecución real interrumpida exige reconciliación; no marcarla pendiente para reintentarla.

Mantener también detenida la purga de certificados del scheduler antiguo: la 0.9.0 purga lotes aprobados sin conocer la cola nueva. Volver de imagen no habilita a retirar listas que una emisión activa o indeterminada todavía necesita. Si Portainer conserva servicios que ya no figuran en el compose anterior, comprobar explícitamente que `worker-certificados` siga detenido. La reversión de imagen y la restauración de un respaldo son procedimientos diferentes.
