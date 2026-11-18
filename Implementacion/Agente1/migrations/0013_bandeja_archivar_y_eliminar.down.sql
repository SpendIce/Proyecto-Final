-- Reversión de 0013: quita las marcas de visibilidad de la bandeja.
--
-- Descarta las marcas registradas —qué se archivó y qué se eliminó— y con
-- ellas toda pieza o lote archivado vuelve a la vista por defecto y toda
-- pieza eliminada reaparece. La estructura y los datos del ciclo de vida
-- no cambian: `estado_web`, prosa y auditoría quedan como estaban. Con
-- datos reales, la reversión exige restaurar el respaldo (ADR 0009) porque
-- la eliminación asentada es evidencia de la decisión humana.

BEGIN;

ALTER TABLE lotes_certificados DROP COLUMN archivada_en;
ALTER TABLE solicitudes DROP COLUMN eliminada_en, DROP COLUMN archivada_en;

COMMIT;
