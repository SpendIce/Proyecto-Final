"""Las migraciones SQL imponen en la base las mismas invariantes que el puerto
en memoria: el borrador atado al output_hash de su ejecución, ninguna validación
anterior al borrador que juzga, ningún contenido ni credencial persistido y un
trigger que rechaza timestamps futuros. Cada rollback deshace en orden inverso."""

from pathlib import Path


MIGRACIONES = Path(__file__).parents[1] / "migrations"


def test_migracion_forward_define_tablas_y_controles_minimos() -> None:
    sql = (MIGRACIONES / "0001_persistencia_agente1.up.sql").read_text(encoding="utf-8")

    for tabla in (
        "solicitudes",
        "ejecuciones",
        "borradores",
        "validaciones",
        "defectos",
        "eventos_ejecucion",
    ):
        assert f"CREATE TABLE {tabla}" in sql
    assert "TIMESTAMPTZ" in sql
    assert "UNIQUE (idempotency_key)" in sql
    assert "UNIQUE (correlation_id)" in sql
    assert "CHECK (estado IN" in sql
    assert "eliminado_en TIMESTAMPTZ" in sql
    assert "contenido" not in sql.lower()
    assert "email" not in sql.lower()
    assert "token" not in sql.lower()
    assert "CHECK ((estado = 'ABIERTO' AND cerrado_en IS NULL)" in sql
    assert "OR (estado = 'CERRADO' AND cerrado_en IS NOT NULL))" in sql
    assert "id_solicitud ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'" in sql
    assert "idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}$'" in sql
    assert "hu ~ '^HU-[0-9]{3}$'" in sql
    assert "fuente_tipo IN ('csv', 'fixture', 'google_sheets', 'jsonl_replay')" in sql
    assert "resultado IN (" in sql
    assert "error_code ~ '^[a-z][a-z0-9_]{0,63}$'" in sql
    assert "canal IN ('gacetilla', 'instagram', 'linkedin')" in sql
    assert "tipo ~ '^[a-z][a-z0-9_]{0,63}$'" in sql
    assert "estado = 'INICIADA' AND resultado IS NULL" in sql
    assert "AND output_hash IS NULL AND error_code IS NULL" in sql
    assert "AND resultado = 'borrador_generado'" in sql
    assert "AND output_hash IS NOT NULL AND error_code IS NULL" in sql


def test_rollback_elimina_solamente_objetos_del_spike_en_orden_inverso() -> None:
    sql = (MIGRACIONES / "0001_persistencia_agente1.down.sql").read_text(
        encoding="utf-8"
    )
    tablas = (
        "eventos_ejecucion",
        "defectos",
        "validaciones",
        "borradores",
        "ejecuciones",
        "solicitudes",
    )

    posiciones = [sql.index(f"DROP TABLE {tabla}") for tabla in tablas]
    assert posiciones == sorted(posiciones)


def test_migracion_0002_ata_el_borrador_al_output_hash_de_su_ejecucion() -> None:
    sql = (MIGRACIONES / "0002_integridad_referencial_borradores.up.sql").read_text(
        encoding="utf-8"
    )

    # La clave foránea compuesta es la única defensa estructural que impide
    # colgar un borrador de una ejecución FALLIDA, INCOMPLETA o INICIADA:
    # esos estados tienen output_hash NULL por el CHECK de 0001.
    assert "UNIQUE (id_ejecucion, output_hash)" in sql
    assert "FOREIGN KEY (id_ejecucion, output_hash)" in sql
    assert "REFERENCES ejecuciones (id_ejecucion, output_hash)" in sql


def test_migracion_0002_impide_validaciones_anteriores_al_borrador() -> None:
    sql = (MIGRACIONES / "0002_integridad_referencial_borradores.up.sql").read_text(
        encoding="utf-8"
    )

    assert "UNIQUE (id_borrador, creada_en)" in sql
    assert "borrador_creada_en TIMESTAMPTZ NOT NULL" in sql
    assert "FOREIGN KEY (id_borrador, borrador_creada_en)" in sql
    assert "CHECK (registrada_en >= borrador_creada_en)" in sql


def test_migracion_0002_no_persiste_contenido_ni_credenciales() -> None:
    sql = (MIGRACIONES / "0002_integridad_referencial_borradores.up.sql").read_text(
        encoding="utf-8"
    )

    assert "contenido" not in sql.lower()
    assert "email" not in sql.lower()
    assert "token" not in sql.lower()


def test_rollback_0002_revierte_en_orden_inverso_a_la_migracion() -> None:
    sql = (MIGRACIONES / "0002_integridad_referencial_borradores.down.sql").read_text(
        encoding="utf-8"
    )
    objetos = (
        "validaciones_no_preceden_al_borrador",
        "validaciones_borrador_creada_fk",
        "borrador_creada_en",
        "borradores_id_creada_key",
        "borradores_ejecucion_output_fk",
        "ejecuciones_id_output_hash_key",
    )

    posiciones = [sql.index(objeto) for objeto in objetos]
    assert posiciones == sorted(posiciones)


def test_migracion_0003_rechaza_timestamps_futuros_con_trigger() -> None:
    sql = (MIGRACIONES / "0003_rechazo_timestamps_futuros.up.sql").read_text(
        encoding="utf-8"
    )

    assert "RETURNS TRIGGER" in sql
    assert "timestamp_controlado > CURRENT_TIMESTAMP" in sql
    assert "ERRCODE = '23514'" in sql
    assert "ejecuciones_rechazan_creada_en_futura" in sql
    assert "validaciones_rechazan_registrada_en_futura" in sql
    assert "UPDATE OF creada_en ON ejecuciones" in sql
    assert "UPDATE OF registrada_en ON validaciones" in sql
    assert "CHECK (" not in sql


def test_rollback_0003_elimina_triggers_antes_de_la_funcion() -> None:
    sql = (MIGRACIONES / "0003_rechazo_timestamps_futuros.down.sql").read_text(
        encoding="utf-8"
    )
    objetos = (
        "validaciones_rechazan_registrada_en_futura",
        "ejecuciones_rechazan_creada_en_futura",
        "agente1_rechazar_timestamp_futuro",
    )

    posiciones = [sql.index(objeto) for objeto in objetos]
    assert posiciones == sorted(posiciones)
