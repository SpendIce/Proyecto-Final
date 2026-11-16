-- Prellenado de correo ofrecido al aprobar (ADR 0021, issue #153).
--
-- `prellenado_publicos` registra, en la auditoría de la decisión, los ids
-- de públicos a los que se les ofreció el correo prellenado de Gmail. Son
-- ids del catálogo cerrado, nunca direcciones: las direcciones no viven
-- en la base igual que no viven en el repo. NULL en decisiones sin
-- prellenado (descarte, pedido sin públicos, despliegue sin catálogo).
--
-- Grants: la columna hereda los permisos de tabla ya concedidos en 0005
-- a `agente1_app` (INSERT en auditoría) y a `agente1_mantenimiento`
-- (SELECT de evidencia).
BEGIN;

ALTER TABLE validaciones
    ADD COLUMN prellenado_publicos JSONB;

ALTER TABLE validaciones
    ADD CONSTRAINT validaciones_prellenado_publicos_check
        CHECK (
            prellenado_publicos IS NULL
            OR jsonb_typeof(prellenado_publicos) = 'array'
        );

COMMIT;
