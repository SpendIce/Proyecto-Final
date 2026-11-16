-- Modo demostración del canal web (ADR 0019, issue #149): `web-demo` se
-- suma al vocabulario de `solicitudes.canal` para que lo creado sin
-- verificación de Google quede marcado como tal — mismo ciclo de vida y
-- misma retención que `web`, jamás como identidad verificada.
BEGIN;

ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_canal_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_canal_check
        CHECK (canal IN ('planilla', 'form', 'web', 'web-demo'));

ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_web_campos_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_web_campos_check
        CHECK (
            canal NOT IN ('web', 'web-demo')
            OR (
                solicitante_hash IS NOT NULL
                AND rol IS NOT NULL
                AND tipo_pieza IS NOT NULL
                AND estado_web IS NOT NULL
                AND ultima_actividad_en IS NOT NULL
            )
        );

COMMIT;
