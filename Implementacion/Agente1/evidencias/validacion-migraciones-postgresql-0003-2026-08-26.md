# Validación PostgreSQL efímera — migraciones 0001 a 0003

- **Fecha:** 2026-08-26
- **Motor:** PostgreSQL 16 (`postgres:16-alpine`)
- **Datos:** sintéticos; contenedor local efímero eliminado al finalizar.
- **Alcance:** regresión del esquema SQL. No integra un adapter Python, no usa
  datos institucionales, no sustituye JSONL y no acredita TRL 3.

## Secuencia ejecutada

1. Forward `0001_persistencia_agente1`, `0002_integridad_referencial_borradores`
   y `0003_rechazo_timestamps_futuros` sobre una base vacía: **OK**.
2. Camino válido: solicitud, ejecución `PENDIENTE_VALIDACION`, borrador y
   validación aprobada: **OK**.
3. `UPDATE ejecuciones SET creada_en = CURRENT_TIMESTAMP + INTERVAL '1 hour'`:
   **RECHAZADO** por `agente1_rechazar_timestamp_futuro`, con mensaje
   `timestamp futuro no permitido para creada_en`.
4. Inserción de una validación con `registrada_en` una hora futura:
   **RECHAZADO** por el mismo trigger, con mensaje
   `timestamp futuro no permitido para registrada_en`.
5. Rollback `0003 → 0002 → 0001`: **OK**; `information_schema.tables` en
   `public` informó **0 tablas**.
6. Forward final `0001 → 0002 → 0003`: **OK**; quedaron **6 tablas** y los
   **2 triggers** temporales esperados.

## Conclusión

La migración `0003` cierra la brecha estructural de timestamps futuros para
escrituras directas sobre `ejecuciones.creada_en` y
`validaciones.registrada_en`. El control es una defensa de base de datos
complementaria al puerto Python; no reemplaza las pruebas futuras de
concurrencia, performance, backup/restauración, permisos DSI ni operación
institucional.
