#!/usr/bin/env python3
"""Servidor del canal web del Agente 1 (issue #149, ADR 0014/0016).

Levanta la app FastAPI con uvicorn. Todo lo institucional llega por
entorno; el repositorio no guarda client IDs, dominios ni credenciales:

- `AGENTE1_POSTGRES_DSN` (obligatoria): DSN de la base con las
  migraciones 0004+ aplicadas; en producción conecta como `agente1_app`.
- `AGENTE1_WEB_GOOGLE_CLIENT_ID` (obligatoria en modo real): el client
  ID que DSI entrega (#62). Declarado junto a `AGENTE1_WEB_MODO_PRUEBA=si`
  es un fallo de arranque: el modo prueba no convive con un client ID.
- `AGENTE1_WEB_DOMINIO` (obligatoria en modo real): dominio `hd`
  institucional exigido al token. Sin dominio el canal cierra el
  arranque, porque `hd` es el único límite de la cuenta.
- `AGENTE1_PADRON_ROLES_CSV` (obligatoria): padrón de roles (ADR 0005).
- `AGENTE1_TABLA` (obligatoria): CSV de actividades de la fuente, para el
  select condicional del pedido.
- `AGENTE1_WEB_MODO_PRUEBA=si`: verificador fake sin Google — el token
  `prueba:<correo>` ingresa con ese correo sintético. Sólo desarrollo y
  evidencia: el arranque se niega si corre con cookie `Secure`, con host
  que no sea loopback o dentro del contenedor (`AGENTE1_CONTENEDOR=si`,
  que declara el compose).
- `AGENTE1_WEB_COOKIE_SECURE=no`: permite probar por HTTP local. Default
  `si`, como exige la cookie `Secure` del diseño.
- `AGENTE1_WEB_HOST` / `AGENTE1_WEB_PORT`: escucha (default 127.0.0.1:8080).
- `AGENTE1_WEB_CORREOS_PRUEBA`: correos sintéticos habilitados por el
  verificador fake, separados por coma (`a@example.invalid,b@…`).

Uso:

    python scripts/servidor_web.py
"""

from __future__ import annotations

import argparse
import functools
import os
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _invalida(code: str) -> int:
    import json

    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Servidor del canal web del Agente 1 (ADR 0014/0016)."
    )
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument(
        "--una-ruta",
        action="store_true",
        help="Construye la app y verifica el arranque sin levantar uvicorn.",
    )
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    padron_csv = entorno.get("AGENTE1_PADRON_ROLES_CSV")
    tabla = entorno.get("AGENTE1_TABLA")
    if not dsn or not padron_csv or not tabla:
        return _invalida("web_config_incomplete")

    from agente1.canal_form import cargar_padron_roles_csv
    from agente1.fuentes import CsvFuenteSolicitudes
    from agente1.web.app import (
        CLIENT_ID_PRUEBA,
        ConfiguracionInvalida,
        ConfiguracionWeb,
        crear_app,
    )
    from agente1.web.persistencia import RepositorioWeb, conectar

    modo_prueba = entorno.get("AGENTE1_WEB_MODO_PRUEBA", "").lower() == "si"
    if modo_prueba:
        from agente1.web.identidad import (
            IdentidadVerificada,
            VerificadorFake,
        )

        identidades = {}
        for correo in entorno.get(
            "AGENTE1_WEB_CORREOS_PRUEBA", ""
        ).split(","):
            correo = correo.strip()
            if correo:
                identidades[f"prueba:{correo}"] = IdentidadVerificada(
                    sub=f"prueba-sub-{correo}", correo=correo, hd=None
                )
        verificador = VerificadorFake(identidades)
        # Si el entorno declara un client ID de Google a la vez que el
        # modo prueba, la config llega con él y `validar_configuracion`
        # cierra el arranque: el modo prueba no convive con un client ID.
        client_id = (
            entorno.get("AGENTE1_WEB_GOOGLE_CLIENT_ID") or CLIENT_ID_PRUEBA
        )
    else:
        from agente1.web.identidad import VerificadorGoogle

        client_id = entorno.get("AGENTE1_WEB_GOOGLE_CLIENT_ID")
        dominio = entorno.get("AGENTE1_WEB_DOMINIO")
        if not client_id:
            return _invalida("web_google_client_id_ausente")
        if not dominio:
            return _invalida("web_dominio_ausente")
        verificador = VerificadorGoogle(
            client_id=client_id, dominio=dominio
        )

    try:
        padron = cargar_padron_roles_csv(Path(padron_csv))
    except Exception:
        return _invalida("web_padron_invalid")
    try:
        actividades = CsvFuenteSolicitudes(Path(tabla)).enumerar()
    except Exception:
        return _invalida("web_fuente_invalid")

    host = args.host or entorno.get("AGENTE1_WEB_HOST", "127.0.0.1")
    config = ConfiguracionWeb(
        google_client_id=client_id,
        dominio_hd=entorno.get("AGENTE1_WEB_DOMINIO") or None,
        modo_prueba=modo_prueba,
        cookie_secure=entorno.get("AGENTE1_WEB_COOKIE_SECURE", "si") != "no",
    )
    repositorio = RepositorioWeb(functools.partial(conectar, dsn))
    try:
        app = crear_app(
            config=config,
            verificador=verificador,
            padron=padron,
            repositorio=repositorio,
            actividades=actividades,
            host=host,
            en_contenedor=(
                entorno.get("AGENTE1_CONTENEDOR", "").lower() == "si"
            ),
        )
    except ConfiguracionInvalida:
        return _invalida("web_config_insegura")
    if args.una_ruta:
        print('{"status": "OK"}')
        return 0

    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=args.port or int(entorno.get("AGENTE1_WEB_PORT", "8080")),
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
