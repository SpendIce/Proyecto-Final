-- Revierte 0010: el lote de certificados de la web vuelve a no existir.
--
-- El `down` descarta los lotes guardados, sus listas de cierre y las
-- decisiones registradas. Con datos reales, volver a la versión anterior
-- exige restaurar el respaldo (ADR 0009): la aprobación del lote es
-- evidencia de la validación humana y no se reconstruye desde otro lado.
BEGIN;

-- Los grants de la tabla y de sus columnas se van con ella.
DROP TABLE lotes_certificados;

COMMIT;
