-- Revierte 0010: el lote de certificados de la web vuelve a no existir.
--
-- El `down` descarta los lotes guardados, sus listas de cierre y las
-- decisiones registradas. Con datos reales, volver a la versión anterior
-- exige restaurar el respaldo (ADR 0009): la aprobación del lote es
-- evidencia de la validación humana y no se reconstruye desde otro lado.
BEGIN;

REVOKE SELECT, INSERT, UPDATE ON lotes_certificados FROM agente1_app;
REVOKE SELECT ON lotes_certificados FROM agente1_mantenimiento;

DROP TABLE lotes_certificados;

COMMIT;
