-- Cierra dos brechas estructurales detectadas al ejecutar 0001 contra un
-- PostgreSQL efímero el 2026-08-17. Antes de esta migración el esquema aceptaba
-- borradores colgados de ejecuciones FALLIDA, INCOMPLETA o INICIADA, y permitía
-- que el output_hash del borrador difiriera del de su ejecución. El puerto en
-- Python impedía ambos casos, pero las constraints no los cubrían y el spike las
-- declara "última defensa estructural".
--
-- Los controles de timestamp futuro NO se agregan acá: exigirían now() dentro de
-- un CHECK, que es una función no inmutable. Continúan siendo responsabilidad del
-- puerto bajo lock, tal como documenta el spike.

BEGIN;

-- Blanco de la clave foránea compuesta. id_ejecucion ya es PRIMARY KEY, así que
-- esta restricción no reduce la cardinalidad: sólo habilita la referencia.
ALTER TABLE ejecuciones
    ADD CONSTRAINT ejecuciones_id_output_hash_key
    UNIQUE (id_ejecucion, output_hash);

-- Invariantes 1 y 2 con una sola restricción. `ejecuciones` ya garantiza por
-- CHECK que output_hash es NOT NULL únicamente en PENDIENTE_VALIDACION,
-- APROBADA o RECHAZADA. Como borradores.output_hash es NOT NULL, esta clave
-- foránea obliga a que el hash coincida y, por transitividad, a que la ejecución
-- referenciada esté en un estado de borrador válido.
ALTER TABLE borradores
    ADD CONSTRAINT borradores_ejecucion_output_fk
    FOREIGN KEY (id_ejecucion, output_hash)
    REFERENCES ejecuciones (id_ejecucion, output_hash);

-- Invariante 3: una validación no puede preceder al borrador que evalúa.
-- Se desnormaliza la fecha de creación del borrador para poder compararla
-- dentro de un CHECK inmutable, y una clave foránea compuesta impide que ese
-- valor se desincronice del agregado original.
ALTER TABLE borradores
    ADD CONSTRAINT borradores_id_creada_key
    UNIQUE (id_borrador, creada_en);

ALTER TABLE validaciones
    ADD COLUMN borrador_creada_en TIMESTAMPTZ NOT NULL;

ALTER TABLE validaciones
    ADD CONSTRAINT validaciones_borrador_creada_fk
    FOREIGN KEY (id_borrador, borrador_creada_en)
    REFERENCES borradores (id_borrador, creada_en);

ALTER TABLE validaciones
    ADD CONSTRAINT validaciones_no_preceden_al_borrador
    CHECK (registrada_en >= borrador_creada_en);

COMMIT;
