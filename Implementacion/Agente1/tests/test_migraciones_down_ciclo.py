"""Ciclo ``up`` → ``down`` → esquema original de las migraciones del Agente 1.

El ticket #95 (reversión de #66) exige que la suite pruebe las migraciones
``down`` para que volver a la versión anterior pueda revertir el esquema sin
restaurar el respaldo de Drive: para cada migración, aplicar las ``up`` hasta
ella, aplicar su ``down`` y verificar que el esquema del motor queda igual que
antes de aplicarla.

Estas pruebas **ejecutan SQL contra un PostgreSQL real**, no leen el texto de
los ``.sql`` (de eso ya se ocupan ``test_migraciones_persistencia.py``). Por eso
necesitan una base viva, que el job ``agente1-ci`` levanta como servicio y a la
que apunta la variable de entorno ``AGENTE1_POSTGRES_DSN``. Sin esa variable —el
caso de ``uv run pytest`` en una máquina sin base— el ciclo se saltea: no hay
adapter PostgreSQL cableado al producto y la suite determinista no debe exigir
un motor.

El ciclo no toca ``public``: crea un esquema desechable por corrida, lo usa como
``search_path`` y lo borra al final, así que nunca destruye datos de la base a la
que apunte el DSN.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

MIGRACIONES = Path(__file__).parents[1] / "migrations"
PSQL = shutil.which("psql")


@dataclass(frozen=True)
class Reversion:
    """Clasificación de reversibilidad de una migración (ADR 0009).

    ``pierde_datos`` marca un ``down`` que descarta filas almacenadas. La regla
    del procedimiento de reversión es que un ``down`` que pierde datos o que no
    es reversible obliga a restaurar el respaldo de Drive; ``requiere_restaurar``
    materializa esa regla y se verifica abajo para toda migración declarada.
    """

    reversible: bool
    pierde_datos: bool
    requiere_restaurar_respaldo: bool
    nota: str


# Clasificación por migración. Es la fuente que el procedimiento de reversión
# (`Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md`) refleja en
# prosa. Una migración nueva exige una entrada acá o la suite falla.
REVERSIBILIDAD: dict[str, Reversion] = {
    "0001_persistencia_agente1": Reversion(
        reversible=True,
        pierde_datos=True,
        requiere_restaurar_respaldo=True,
        nota=(
            "El `down` elimina las seis tablas del esquema operativo: revierte "
            "la estructura pero descarta toda fila almacenada. Con datos reales, "
            "volver a la versión anterior exige restaurar el respaldo (ADR 0009)."
        ),
    ),
    "0002_integridad_referencial_borradores": Reversion(
        reversible=True,
        pierde_datos=False,
        requiere_restaurar_respaldo=False,
        nota=(
            "El `down` elimina la columna desnormalizada `borrador_creada_en` y "
            "sus restricciones; ese valor se reconstruye desde "
            "`borradores.creada_en`, así que no se pierde información de "
            "negocio. Reabre las brechas de integridad referencial que 0002 "
            "cerró: sólo es defendible antes de almacenar evidencia "
            "institucional real."
        ),
    ),
    "0003_rechazo_timestamps_futuros": Reversion(
        reversible=True,
        pierde_datos=False,
        requiere_restaurar_respaldo=False,
        nota=(
            "El `down` sólo elimina dos triggers y su función: no toca datos. "
            "Volver a 0002 alcanza sin restaurar el respaldo."
        ),
    ),
}


# Snapshot canónico del esquema. Se arma en el servidor con `pg_get_*def`, que
# devuelve texto estable y no depende de la versión del cliente. `:'sch'` es una
# variable de psql que se pasa con `-v sch=<esquema>`.
CONSULTA_SNAPSHOT = """
SELECT 'TABLE ' || table_name
  FROM information_schema.tables WHERE table_schema = :'sch'
UNION ALL
SELECT 'COLUMN ' || table_name || '.' || column_name || ' ' || data_type
       || ' null=' || is_nullable
       || ' def=' || coalesce(column_default, '-')
       || ' ident=' || is_identity
  FROM information_schema.columns WHERE table_schema = :'sch'
UNION ALL
SELECT 'SEQUENCE ' || sequence_name || ' ' || data_type || ' ' || start_value
       || ' ' || increment
  FROM information_schema.sequences WHERE sequence_schema = :'sch'
UNION ALL
SELECT 'CONSTRAINT ' || conname || ' ' || contype::text || ' '
       || pg_get_constraintdef(oid)
  FROM pg_constraint WHERE connamespace = (:'sch')::regnamespace
UNION ALL
SELECT 'INDEX ' || indexname || ' ' || indexdef
  FROM pg_indexes WHERE schemaname = :'sch'
UNION ALL
SELECT 'TRIGGER ' || t.tgname || ' ' || pg_get_triggerdef(t.oid)
  FROM pg_trigger t
  JOIN pg_class c ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = :'sch' AND NOT t.tgisinternal
UNION ALL
SELECT 'FUNCTION ' || p.proname || ' ' || pg_get_functiondef(p.oid)
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = :'sch'
ORDER BY 1
"""


def _nombres_de_migracion() -> list[str]:
    """Nombres base (``NNNN_descripcion``) de las migraciones del repositorio."""
    sufijo = ".up.sql"
    return sorted(p.name[: -len(sufijo)] for p in MIGRACIONES.glob(f"*{sufijo}"))


def _psql(
    dsn: str,
    esquema: str,
    *,
    sql: str | None = None,
    archivo: Path | None = None,
    capturar: bool = False,
) -> str:
    """Corre ``psql`` en el esquema indicado como ``search_path``.

    ``ON_ERROR_STOP=1`` convierte cualquier error de SQL en salida distinta de
    cero, que acá se traduce en un fallo de la prueba.
    """
    assert PSQL is not None
    comando = [PSQL, dsn, "-X", "-q", "-v", "ON_ERROR_STOP=1"]
    if sql is not None:
        comando += ["-c", sql]
    if archivo is not None:
        comando += ["-f", str(archivo)]
    entorno = dict(os.environ, PGOPTIONS=f"-c search_path={esquema}")
    proceso = subprocess.run(comando, env=entorno, capture_output=True, text=True)
    if proceso.returncode != 0:
        objetivo = archivo.name if archivo is not None else (sql or "").strip()
        raise AssertionError(
            f"psql falló con código {proceso.returncode} sobre `{objetivo}`:\n"
            f"{proceso.stderr.strip()}"
        )
    return proceso.stdout if capturar else ""


def _snapshot(dsn: str, esquema: str) -> str:
    """Texto canónico del estado del esquema, para comparar antes y después."""
    assert PSQL is not None
    proceso = subprocess.run(
        [
            PSQL, dsn, "-X", "-q", "-tA", "-v", "ON_ERROR_STOP=1",
            "-v", f"sch={esquema}", "-f", "-",
        ],
        env=dict(os.environ, PGOPTIONS=f"-c search_path={esquema}"),
        input=CONSULTA_SNAPSHOT,
        capture_output=True,
        text=True,
    )
    if proceso.returncode != 0:
        raise AssertionError(
            f"no se pudo leer el esquema `{esquema}`:\n{proceso.stderr.strip()}"
        )
    return proceso.stdout


def _motivo_skip() -> str | None:
    if not os.environ.get("AGENTE1_POSTGRES_DSN"):
        return (
            "AGENTE1_POSTGRES_DSN no está definida: el ciclo `up`/`down` exige un "
            "PostgreSQL real que el job `agente1-ci` levanta como servicio"
        )
    if PSQL is None:
        return "el cliente `psql` no está disponible en este entorno"
    return None


def test_toda_migracion_declara_su_reversibilidad() -> None:
    """Una migración nueva sin clasificación (o sin `down`) rompe la suite."""
    nombres = _nombres_de_migracion()
    assert nombres, "no se encontró ninguna migración en migrations/"

    faltantes = [nombre for nombre in nombres if nombre not in REVERSIBILIDAD]
    assert not faltantes, (
        f"migraciones sin clasificación de reversibilidad en REVERSIBILIDAD: {faltantes}"
    )
    sobrantes = [nombre for nombre in REVERSIBILIDAD if nombre not in nombres]
    assert not sobrantes, (
        f"REVERSIBILIDAD clasifica migraciones que no existen: {sobrantes}"
    )

    for nombre in nombres:
        assert (MIGRACIONES / f"{nombre}.up.sql").is_file()
        assert (MIGRACIONES / f"{nombre}.down.sql").is_file(), (
            f"{nombre} no tiene `down`: no se puede revertir el esquema"
        )

    # La regla de #95 y del ADR 0009: si el `down` pierde datos o no es
    # reversible, el procedimiento obliga a restaurar el respaldo de Drive.
    for nombre, reversion in REVERSIBILIDAD.items():
        exigido = reversion.pierde_datos or not reversion.reversible
        assert reversion.requiere_restaurar_respaldo == exigido, (
            f"{nombre}: requiere_restaurar_respaldo debe ser {exigido} para "
            "coincidir con la regla de reversión"
        )


@pytest.mark.parametrize("nombre", _nombres_de_migracion())
def test_down_devuelve_el_esquema_anterior(nombre: str) -> None:
    """`up` hasta ``nombre``, su `down`, y el esquema queda idéntico a antes."""
    motivo = _motivo_skip()
    if motivo is not None:
        pytest.skip(motivo)

    dsn = os.environ["AGENTE1_POSTGRES_DSN"]
    nombres = _nombres_de_migracion()
    indice = nombres.index(nombre)
    esquema = f"agente1_mig_{os.getpid()}"

    try:
        _psql(
            dsn,
            esquema,
            sql=f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE; '
            f'CREATE SCHEMA "{esquema}";',
        )

        # Estado anterior a la migración bajo prueba: las `up` previas ya aplicadas.
        for previo in nombres[:indice]:
            _psql(dsn, esquema, archivo=MIGRACIONES / f"{previo}.up.sql")
        antes = _snapshot(dsn, esquema)

        _psql(dsn, esquema, archivo=MIGRACIONES / f"{nombre}.up.sql")
        _psql(dsn, esquema, archivo=MIGRACIONES / f"{nombre}.down.sql")
        despues = _snapshot(dsn, esquema)

        assert despues == antes, (
            f"el `down` de {nombre} no devuelve el esquema al estado previo.\n"
            "Sólo en el estado posterior:\n"
            + "\n".join(
                sorted(set(despues.splitlines()) - set(antes.splitlines()))
            )
            + "\nSólo en el estado previo:\n"
            + "\n".join(
                sorted(set(antes.splitlines()) - set(despues.splitlines()))
            )
        )
    finally:
        # La limpieza no debe tapar el fallo real si la conexión se cayó.
        try:
            _psql(dsn, esquema, sql=f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE;')
        except AssertionError:
            pass
