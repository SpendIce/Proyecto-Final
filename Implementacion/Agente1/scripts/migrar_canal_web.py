#!/usr/bin/env python3
"""Migrador one-shot del canal web (ADR 0016, issue #149).

Es el paso de bootstrap del despliegue: aplica en orden las migraciones
`*.up.sql` que falten y, después, asigna las claves de los roles que crea la
0005. Corre una vez por despliegue, antes de `web` y `worker`, y no reintenta.

Decisiones que no se ven en el código:

- **Habla con el motor por `psql`, no por `psycopg`.** La imagen de runtime
  del Agente 1 no instala dependencias de terceros; el cliente 16 sí está
  (lo usa el respaldo diario). Así el mismo script corre en la imagen y en la
  suite sin agregar un paquete al runtime.
- **La credencial viaja por el entorno del subproceso**, igual que
  `entorno_libpq` en `agente1/respaldo.py`: arma `PG*` desde el DSN y las
  claves de rol las lee `psql` con `\\getenv`. Ni el DSN ni las claves pasan
  por argv ni se imprimen.
- **Cada migración y su fila de control van en una sola transacción.** Los
  `.up.sql` traen su propio `BEGIN`/`COMMIT`; se les quita el par externo y se
  envuelve el cuerpo con la inserción en `migraciones_aplicadas`, para que una
  caída entre la migración y el asiento no la reaplique.
- **Una migración ya aplicada que cambió de sha256 falla cerrado.** No se
  reaplica ni se actualiza el control: alguien editó historia que la base ya
  tiene.

Entorno:

- `AGENTE1_POSTGRES_ADMIN_DSN` (obligatoria): DSN del superusuario de la base.
- `AGENTE1_POSTGRES_APP_PASSWORD` (obligatoria): clave de `agente1_app`.
- `AGENTE1_POSTGRES_MANTENIMIENTO_PASSWORD` (obligatoria): clave de
  `agente1_mantenimiento`.

Uso:

    python scripts/migrar_canal_web.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MIGRACIONES = ROOT / "migrations"
TABLA_CONTROL = "migraciones_aplicadas"


@dataclass(frozen=True)
class Migracion:
    version: str
    ruta: Path
    sha256: str


# Rol → variable del stack y código de error si falta.
CLAVES_ROLES = {
    "agente1_app": (
        "AGENTE1_POSTGRES_APP_PASSWORD",
        "migrar_clave_app_ausente",
    ),
    "agente1_mantenimiento": (
        "AGENTE1_POSTGRES_MANTENIMIENTO_PASSWORD",
        "migrar_clave_mantenimiento_ausente",
    ),
}

SQL_CONTROL = f"""
CREATE TABLE IF NOT EXISTS {TABLA_CONTROL} (
    version text PRIMARY KEY,
    aplicada_en timestamptz NOT NULL DEFAULT now(),
    sha256 text NOT NULL
);
"""

# `psql` recibe las claves por `\getenv` y las interpola con `:'variable'`,
# que es un literal SQL correctamente escapado. El valor nunca viaja por argv.
SQL_ROLES = """
\\getenv clave_app AGENTE1_POSTGRES_APP_PASSWORD
\\getenv clave_mantenimiento AGENTE1_POSTGRES_MANTENIMIENTO_PASSWORD
BEGIN;
ALTER ROLE agente1_app PASSWORD :'clave_app';
ALTER ROLE agente1_mantenimiento PASSWORD :'clave_mantenimiento';
COMMIT;
"""


class MigracionError(Exception):
    """Falla del migrador: el `main` la traduce a un código estructurado."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _invalida(code: str) -> int:
    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


_VARIABLES_LIBPQ = {
    "host": "PGHOST",
    "hostaddr": "PGHOSTADDR",
    "port": "PGPORT",
    "user": "PGUSER",
    "password": "PGPASSWORD",
    "dbname": "PGDATABASE",
    "options": "PGOPTIONS",
    "application_name": "PGAPPNAME",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "passfile": "PGPASSFILE",
    "service": "PGSERVICE",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
}


def _parsear_clave_valor(dsn: str) -> dict[str, str]:
    """Pares `clave=valor` de libpq, con comillas simples y `\\` de escape."""
    valores: dict[str, str] = {}
    i, largo = 0, len(dsn)
    while True:
        while i < largo and dsn[i].isspace():
            i += 1
        if i >= largo:
            break
        inicio = i
        while i < largo and dsn[i] not in "= \t\r\n":
            i += 1
        clave = dsn[inicio:i]
        while i < largo and dsn[i].isspace():
            i += 1
        if not clave or i >= largo or dsn[i] != "=":
            raise MigracionError("migrar_dsn_admin_invalido")
        i += 1
        while i < largo and dsn[i].isspace():
            i += 1
        valor: list[str] = []
        if i < largo and dsn[i] == "'":
            i += 1
            while i < largo and dsn[i] != "'":
                if dsn[i] == "\\":
                    i += 1
                    if i >= largo:
                        raise MigracionError("migrar_dsn_admin_invalido")
                valor.append(dsn[i])
                i += 1
            if i >= largo:
                raise MigracionError("migrar_dsn_admin_invalido")
            i += 1
        else:
            while i < largo and not dsn[i].isspace():
                if dsn[i] == "\\":
                    i += 1
                    if i >= largo:
                        raise MigracionError("migrar_dsn_admin_invalido")
                valor.append(dsn[i])
                i += 1
        valores[clave] = "".join(valor)
    return valores


def entorno_libpq(dsn: str) -> dict[str, str]:
    """Variables `PG*` del cliente a partir del DSN, sin pasar por argv.

    El runtime no tiene `psycopg`, así que el DSN se parsea con la biblioteca
    estándar: se acepta la forma URL (`postgresql://...`) y la forma
    `clave=valor` de libpq, con el mismo escape que usa `make_conninfo`.
    """
    if dsn.startswith(("postgresql://", "postgres://")):
        try:
            partes = urlsplit(dsn)
            puerto = partes.port
        except ValueError as exc:
            raise MigracionError("migrar_dsn_admin_invalido") from exc
        entorno: dict[str, str] = {}
        if partes.hostname:
            entorno["PGHOST"] = partes.hostname
        if puerto:
            entorno["PGPORT"] = str(puerto)
        if partes.username:
            entorno["PGUSER"] = unquote(partes.username)
        if partes.password:
            entorno["PGPASSWORD"] = unquote(partes.password)
        base = unquote(partes.path.lstrip("/"))
        if base:
            entorno["PGDATABASE"] = base
        opciones = parse_qs(partes.query)
        for clave, variable in _VARIABLES_LIBPQ.items():
            if opciones.get(clave):
                entorno[variable] = opciones[clave][0]
        return entorno

    entorno = {}
    for clave, valor in _parsear_clave_valor(dsn).items():
        variable = _VARIABLES_LIBPQ.get(clave)
        if variable:
            entorno[variable] = valor
    if not entorno:
        raise MigracionError("migrar_dsn_admin_invalido")
    return entorno


def _psql(
    dsn: str,
    *,
    codigo: str,
    entorno_base: Mapping[str, str],
    sql: str | None = None,
    script: str | None = None,
    variables: Mapping[str, str] | None = None,
    entorno_extra: Mapping[str, str] | None = None,
) -> str:
    """Corre `psql` con el DSN en el entorno y devuelve su stdout.

    `sql` va por `-c`; `script` va por stdin cuando hay meta-comandos
    (`\\getenv`) o varias sentencias. Un fallo se traduce al código del
    llamador: el stderr del cliente no se imprime para no filtrar la
    credencial.
    """
    psql = shutil.which("psql")
    if psql is None:
        raise MigracionError("migrar_cliente_psql_ausente")
    comando = [psql, "-X", "-q", "-tA", "-v", "ON_ERROR_STOP=1"]
    if variables:
        for nombre, valor in variables.items():
            comando += ["-v", f"{nombre}={valor}"]
    if sql is not None:
        comando += ["-c", sql]
    else:
        comando += ["-f", "-"]
    entorno = dict(entorno_base)
    entorno.update(entorno_libpq(dsn))
    if entorno_extra:
        entorno.update(entorno_extra)
    proceso = subprocess.run(
        comando,
        input=script,
        capture_output=True,
        text=True,
        env=entorno,
    )
    if proceso.returncode != 0:
        raise MigracionError(codigo)
    return proceso.stdout


def _migraciones() -> list[Migracion]:
    """Versión, ruta y sha256 de cada `*.up.sql`, en orden de nombre."""
    archivos = sorted(MIGRACIONES.glob("*.up.sql"))
    if not archivos:
        raise MigracionError("migrar_migraciones_ausentes")
    return [
        Migracion(
            version=archivo.name[: -len(".up.sql")],
            ruta=archivo,
            sha256=hashlib.sha256(archivo.read_bytes()).hexdigest(),
        )
        for archivo in archivos
    ]


def _cuerpo_sin_transaccion(texto: str) -> str:
    """Quita el `BEGIN;`/`COMMIT;` externo del `.up.sql`.

    Las migraciones traen su propio par de transacción. Para que la fila de
    control entre en la misma transacción, el cuerpo se envuelve afuera y el
    par interno se descarta. Fuera del par sólo puede haber comentarios.
    """
    lineas = texto.splitlines()
    inicio = next(
        (i for i, linea in enumerate(lineas) if linea.strip().upper() == "BEGIN;"),
        None,
    )
    fin = next(
        (
            i
            for i in range(len(lineas) - 1, -1, -1)
            if lineas[i].strip().upper() == "COMMIT;"
        ),
        None,
    )
    if inicio is None or fin is None or fin <= inicio:
        raise MigracionError("migrar_migracion_invalida")
    for linea in lineas[:inicio] + lineas[fin + 1 :]:
        limpia = linea.strip()
        if limpia and not limpia.startswith("--"):
            raise MigracionError("migrar_migracion_invalida")
    return "\n".join(lineas[inicio + 1 : fin])


def _aplicadas(dsn: str, entorno_base: Mapping[str, str]) -> dict[str, str]:
    """Las versiones ya aplicadas según la tabla de control, creándola si falta."""
    _psql(
        dsn,
        codigo="migrar_control_fallido",
        entorno_base=entorno_base,
        sql=SQL_CONTROL,
    )
    salida = _psql(
        dsn,
        codigo="migrar_control_fallido",
        entorno_base=entorno_base,
        sql=f"SELECT version || '|' || sha256 FROM {TABLA_CONTROL}",
    )
    aplicadas: dict[str, str] = {}
    for linea in salida.splitlines():
        version, separador, sha = linea.partition("|")
        if separador:
            aplicadas[version] = sha
    return aplicadas


def _aplicar(
    dsn: str, migracion: Migracion, entorno_base: Mapping[str, str]
) -> None:
    """Aplica una migración y asienta su versión y hash en la misma transacción."""
    cuerpo = _cuerpo_sin_transaccion(migracion.ruta.read_text(encoding="utf-8"))
    script = (
        "BEGIN;\n"
        f"{cuerpo}\n"
        f"INSERT INTO {TABLA_CONTROL} (version, sha256)"
        " VALUES (:'version', :'sha');\n"
        "COMMIT;\n"
    )
    _psql(
        dsn,
        codigo="migrar_migracion_fallida",
        entorno_base=entorno_base,
        script=script,
        variables={"version": migracion.version, "sha": migracion.sha256},
    )


def _asignar_claves(
    dsn: str,
    claves: Mapping[str, str],
    entorno_base: Mapping[str, str],
) -> None:
    """Asigna la clave de cada rol en una transacción, vía `\\getenv` de psql."""
    _psql(
        dsn,
        codigo="migrar_roles_fallidos",
        entorno_base=entorno_base,
        script=SQL_ROLES,
        entorno_extra={
            variable: claves[rol]
            for rol, (variable, _codigo) in CLAVES_ROLES.items()
        },
    )


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Migrador one-shot del canal web (ADR 0016)."
    )
    parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_ADMIN_DSN", "").strip()
    if not dsn:
        return _invalida("migrar_dsn_admin_ausente")
    claves: dict[str, str] = {}
    for rol, (variable, codigo) in CLAVES_ROLES.items():
        valor = entorno.get(variable, "")
        if not valor:
            return _invalida(codigo)
        claves[rol] = valor

    try:
        migraciones = _migraciones()
        previas = _aplicadas(dsn, entorno)
        for migracion in migraciones:
            if (
                migracion.version in previas
                and previas[migracion.version] != migracion.sha256
            ):
                return _invalida("migrar_sha256_distinto")
        nuevas: list[str] = []
        for migracion in migraciones:
            if migracion.version not in previas:
                _aplicar(dsn, migracion, entorno)
                nuevas.append(migracion.version)
        _asignar_claves(dsn, claves, entorno)
    except MigracionError as exc:
        return _invalida(exc.code)

    print(
        json.dumps(
            {
                "status": "OK",
                "aplicadas": nuevas,
                "ya_aplicadas": len(migraciones) - len(nuevas),
                "roles": sorted(CLAVES_ROLES),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
