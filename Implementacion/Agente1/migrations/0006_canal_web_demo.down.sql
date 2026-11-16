-- Revierte 0006: `web-demo` sale del vocabulario de `solicitudes.canal`
-- y el esquema vuelve al estado de 0005.
--
-- Si quedan filas `web-demo`, el `ADD CONSTRAINT` de `canal_check` aborta
-- la transacción en voz alta: el `down` nunca reclasifica una solicitud
-- demo como `web` (la mentiría verificada, ADR 0019). El retiro de la
-- demostración define qué se hace con esas filas antes de revertir.
BEGIN;

ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_web_campos_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_web_campos_check
        CHECK (
            canal <> 'web'
            OR (
                solicitante_hash IS NOT NULL
                AND rol IS NOT NULL
                AND tipo_pieza IS NOT NULL
                AND estado_web IS NOT NULL
                AND ultima_actividad_en IS NOT NULL
            )
        );

ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_canal_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_canal_check
        CHECK (canal IN ('planilla', 'form', 'web'));

COMMIT;
