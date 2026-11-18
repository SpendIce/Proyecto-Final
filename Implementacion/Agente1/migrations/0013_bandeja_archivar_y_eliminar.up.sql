-- Marcas de visibilidad de la bandeja: archivar y eliminar piezas y lotes.
--
-- «Archivar» saca el elemento de la vista por defecto sin borrar nada: se
-- recupera con el filtro «Archivadas». «Eliminar» es la puerta que usa
-- quien creó la pieza para retirar sus piezas de prueba: la pieza no vuelve
-- a ninguna vista de la bandeja, pero la auditoría queda — 0005 no le dio a
-- la aplicación permiso de borrar su propia traza, así que la eliminación
-- es una marca, no un DELETE; la purga diaria vacía después la prosa de lo
-- eliminado, como la de lo cerrado.
--
-- Ninguna marca participa del ciclo de vida: no existe el estado
-- «archivada». `estado_web` sigue siendo la única verdad operativa — vencer,
-- purgar y decidir corren igual sobre una pieza marcada — y la marca sólo
-- decide qué muestra la bandeja. Por eso viajan solas y sin índice nuevo:
-- la bandeja de la SEU es pequeña y ya ordena por actividad.
--
-- Sobre lotes sólo existe `archivada_en`: el lote lleva personas reales y
-- su purga es una decisión institucional posterior a la demo; la interfaz
-- no ofrece eliminarlos.

BEGIN;

ALTER TABLE solicitudes
    ADD COLUMN archivada_en TIMESTAMPTZ,
    ADD COLUMN eliminada_en TIMESTAMPTZ,
    ADD CONSTRAINT solicitudes_archivada_en_check
        CHECK (archivada_en IS NULL OR archivada_en >= creada_en),
    ADD CONSTRAINT solicitudes_eliminada_en_check
        CHECK (eliminada_en IS NULL OR eliminada_en >= creada_en);

ALTER TABLE lotes_certificados
    ADD COLUMN archivada_en TIMESTAMPTZ,
    ADD CONSTRAINT lotes_certificados_archivada_en_check
        CHECK (archivada_en IS NULL OR archivada_en >= creada_en);

-- 0005 concedió UPDATE de toda la tabla `solicitudes` a `agente1_app`, así
-- que las columnas nuevas de `solicitudes` la heredan. Sobre
-- `lotes_certificados`, en cambio, 0010 concedió sólo columnas: la marca
-- nueva viaja con su permiso puntual, como el resto.
GRANT UPDATE (archivada_en) ON lotes_certificados TO agente1_app;

COMMIT;
