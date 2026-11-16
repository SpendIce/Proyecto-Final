-- Deshace 0008: la columna de prellenado de `validaciones` se cae con su
-- CHECK. La decisión registrada no se toca.
BEGIN;

ALTER TABLE validaciones
    DROP COLUMN prellenado_publicos;

COMMIT;
