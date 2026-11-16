"""Parser de DSN del migrador del canal web (#149, ADR 0016).

Estas pruebas no necesitan PostgreSQL: fijan que el DSN se convierta en
variables `PG*` sin pasar la credencial por argv. El caso de la clave con
comillas y barra invertida es el que `make_conninfo` produce y el que el
parser de libpq tiene que devolver igual.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from psycopg import conninfo

ROOT = Path(__file__).resolve().parents[1]


def _cargar_modulo():
    spec = importlib.util.spec_from_file_location(
        "migrar_canal_web_dsn", ROOT / "scripts" / "migrar_canal_web.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


modulo = _cargar_modulo()


def test_url_con_password_escapada_y_opciones() -> None:
    entorno = modulo.entorno_libpq(
        "postgresql://admin:p%40ss%2Fword@base.invalid:5433/agente1"
        "?sslmode=require&connect_timeout=7"
    )
    assert entorno == {
        "PGHOST": "base.invalid",
        "PGPORT": "5433",
        "PGUSER": "admin",
        "PGPASSWORD": "p@ss/word",
        "PGDATABASE": "agente1",
        "PGSSLMODE": "require",
        "PGCONNECT_TIMEOUT": "7",
    }


def test_clave_valor_de_make_conninfo_con_comillas_y_barra() -> None:
    dsn = conninfo.make_conninfo(
        host="base.invalid",
        port=5432,
        user="admin",
        password="a'b\\c d",
        dbname="agente1",
    )
    assert modulo.entorno_libpq(dsn) == {
        "PGHOST": "base.invalid",
        "PGPORT": "5432",
        "PGUSER": "admin",
        "PGPASSWORD": "a'b\\c d",
        "PGDATABASE": "agente1",
    }


@pytest.mark.parametrize(
    "dsn",
    [
        "sin-igual",
        "host='sin cerrar",
        "",
    ],
)
def test_dsn_invalido_falla_cerrado(dsn: str) -> None:
    with pytest.raises(modulo.MigracionError) as exc:
        modulo.entorno_libpq(dsn)
    assert exc.value.code == "migrar_dsn_admin_invalido"
