"""Bootstrap del canal web contra PostgreSQL real (ADR 0016, #149).

El migrador es lo que un despliegue sin shell en el host ejecuta una sola
vez: aplica las migraciones pendientes desde una base vacía y asigna las
claves de los roles que crea la 0005. Estas pruebas corren contra un
PostgreSQL efímero, como el resto de la suite del canal, y cada caso usa
una base desechable para no compartir tablas con los demás.

Sin ``AGENTE1_POSTGRES_DSN`` ni ``psql`` el módulo se saltea: el migrador
habla con el motor por el cliente oficial, igual que el contenedor.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import conninfo

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
PSQL = shutil.which("psql")

pytestmark = pytest.mark.skipif(
    not DSN or PSQL is None,
    reason="sin AGENTE1_POSTGRES_DSN o psql (servicio de CI o base local)",
)

CLAVES = {
    "agente1_app": "clave-app-" + uuid.uuid4().hex[:8],
    "agente1_mantenimiento": "clave-mant-" + uuid.uuid4().hex[:8],
}
VERSIONES = [
    "0001_persistencia_agente1",
    "0002_integridad_referencial_borradores",
    "0003_rechazo_timestamps_futuros",
    "0004_canal_web_agente1",
    "0005_roles_canal_web",
]


def _cargar_modulo():
    spec = importlib.util.spec_from_file_location(
        "migrar_canal_web", ROOT / "scripts" / "migrar_canal_web.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def modulo():
    return _cargar_modulo()


def _cargar_entrypoint():
    spec = importlib.util.spec_from_file_location(
        "contenedor_entrypoint_migrar",
        ROOT / "scripts" / "contenedor_entrypoint.py",
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture()
def base():
    """Base desechable del cluster de la suite; se borra siempre al final."""
    nombre = f"migrar_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE DATABASE "{nombre}"')
    info = conninfo.conninfo_to_dict(DSN)
    info["dbname"] = nombre
    dsn = conninfo.make_conninfo(**info)
    try:
        yield dsn
    finally:
        admin.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
        admin.close()


def _dsn_rol(dsn: str, rol: str) -> str:
    info = conninfo.conninfo_to_dict(dsn)
    info["user"] = rol
    info["password"] = CLAVES[rol]
    return conninfo.make_conninfo(**info)


def _entorno(dsn: str, **reemplazos: str | None) -> dict[str, str]:
    entorno = {
        "AGENTE1_POSTGRES_ADMIN_DSN": dsn,
        "AGENTE1_POSTGRES_APP_PASSWORD": CLAVES["agente1_app"],
        "AGENTE1_POSTGRES_MANTENIMIENTO_PASSWORD": CLAVES[
            "agente1_mantenimiento"
        ],
    }
    for clave, valor in reemplazos.items():
        if valor is None:
            entorno.pop(clave, None)
        else:
            entorno[clave] = valor
    return entorno


def _correr(modulo, dsn: str, **reemplazos: str | None) -> int:
    return modulo.main([], environ=_entorno(dsn, **reemplazos))


def _tablas(dsn: str) -> set[str]:
    with psycopg.connect(dsn) as conn:
        return {
            fila[0]
            for fila in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
        }


def test_base_vacia_aplica_todo_y_los_roles_loguean(modulo, base, capfd) -> None:
    """Base vacía → 0001–0005 aplicadas y cada rol conecta con su clave."""
    assert _correr(modulo, base) == 0
    salida, _ = capfd.readouterr()
    resultado = json.loads(salida)
    assert resultado["status"] == "OK"
    assert resultado["aplicadas"] == VERSIONES
    assert resultado["ya_aplicadas"] == 0

    tablas = _tablas(base)
    assert {"solicitudes", "migraciones_aplicadas"} <= tablas

    for rol in CLAVES:
        with psycopg.connect(_dsn_rol(base, rol)) as conn:
            usuario = conn.execute("SELECT current_user").fetchone()[0]
        assert usuario == rol


def test_la_tabla_de_control_tiene_version_marca_y_sha(modulo, base) -> None:
    """La tabla de control es la que declara el ADR para no reaplicar."""
    assert _correr(modulo, base) == 0
    with psycopg.connect(base) as conn:
        columnas = {
            fila[0]: fila[1]
            for fila in conn.execute(
                "SELECT column_name, data_type"
                " FROM information_schema.columns"
                " WHERE table_name = 'migraciones_aplicadas'"
            ).fetchall()
        }
        filas = conn.execute(
            "SELECT count(*) FROM migraciones_aplicadas"
        ).fetchone()[0]
    assert columnas == {
        "version": "text",
        "aplicada_en": "timestamp with time zone",
        "sha256": "text",
    }
    assert filas == len(VERSIONES)


def test_segunda_corrida_no_aplica_nada(modulo, base, capfd) -> None:
    """Idempotencia: la segunda corrida asienta que no hay nada pendiente."""
    assert _correr(modulo, base) == 0
    capfd.readouterr()

    assert _correr(modulo, base) == 0
    salida, _ = capfd.readouterr()
    resultado = json.loads(salida)
    assert resultado["status"] == "OK"
    assert resultado["aplicadas"] == []
    assert resultado["ya_aplicadas"] == len(VERSIONES)


def test_sha_cambiado_falla_cerrado_sin_reaplicar(
    modulo, base, monkeypatch, tmp_path, capfd
) -> None:
    """Una migración ya aplicada que cambió de contenido no se reaplica."""
    assert _correr(modulo, base) == 0
    capfd.readouterr()

    copia = tmp_path / "migrations"
    shutil.copytree(ROOT / "migrations", copia)
    alterada = copia / "0002_integridad_referencial_borradores.up.sql"
    texto = alterada.read_text(encoding="utf-8")
    alterada.write_text(
        texto.replace(
            "\nCOMMIT;\n",
            "\nCREATE TABLE mutacion_prohibida (id int);\nCOMMIT;\n",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(modulo, "MIGRACIONES", copia)

    assert _correr(modulo, base) == 2
    salida, _ = capfd.readouterr()
    assert json.loads(salida)["error_code"] == "migrar_sha256_distinto"
    assert "mutacion_prohibida" not in _tablas(base)


@pytest.mark.parametrize(
    ("variable", "codigo"),
    [
        ("AGENTE1_POSTGRES_ADMIN_DSN", "migrar_dsn_admin_ausente"),
        ("AGENTE1_POSTGRES_APP_PASSWORD", "migrar_clave_app_ausente"),
        (
            "AGENTE1_POSTGRES_MANTENIMIENTO_PASSWORD",
            "migrar_clave_mantenimiento_ausente",
        ),
    ],
)
def test_falta_de_configuracion_falla_antes_de_tocar_la_base(
    modulo, base, capfd, variable: str, codigo: str
) -> None:
    """Sin DSN o sin alguna clave, la base queda intacta y el código es claro."""
    assert _correr(modulo, base, **{variable: None}) == 2
    salida, _ = capfd.readouterr()
    assert json.loads(salida)["error_code"] == codigo
    assert _tablas(base) == set()


def test_dsn_invalido_falla_sin_tocar_la_base(modulo, base, capfd) -> None:
    """Un DSN que no se puede parsear no abre conexión ni crea el control."""
    assert _correr(modulo, "no-es-un-dsn") == 2
    salida, _ = capfd.readouterr()
    assert json.loads(salida)["error_code"] == "migrar_dsn_admin_invalido"
    assert _tablas(base) == set()


def test_las_claves_no_aparecen_en_stdout_ni_stderr(modulo, base, capfd) -> None:
    """Las claves viajan por entorno del cliente, nunca por la salida."""
    assert _correr(modulo, base) == 0
    salida, error = capfd.readouterr()
    for clave in CLAVES.values():
        assert clave not in salida
        assert clave not in error


def test_el_entrypoint_ejecuta_el_bootstrap_completo(
    modulo, base, tmp_path, monkeypatch
) -> None:
    """`migrar` a través del entrypoint aplica el esquema y asigna claves."""
    entrypoint = _cargar_entrypoint()
    monkeypatch.setattr(entrypoint, "verificar", lambda estado: None)
    entorno = {
        clave: valor
        for clave, valor in os.environ.items()
        if clave != "AGENTE1_ENV_FILE"
    }
    entorno.update(_entorno(base))
    entorno["AGENTE1_ESTADO"] = str(tmp_path)
    entorno["AGENTE1_OLLAMA_UPSTREAM"] = ""

    assert entrypoint.main(["migrar"], entorno) == 0
    assert {"solicitudes", "migraciones_aplicadas"} <= _tablas(base)
    for rol in CLAVES:
        with psycopg.connect(_dsn_rol(base, rol)) as conn:
            assert conn.execute("SELECT current_user").fetchone()[0] == rol
