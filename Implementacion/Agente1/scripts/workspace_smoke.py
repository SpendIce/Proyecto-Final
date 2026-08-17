#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import uuid

from agente1.fuentes import FuenteSolicitudesError
from agente1.google_workspace import GoogleSheetsFuenteSolicitudes
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
    cargar_configuracion_workspace,
)


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # No repetir argv: puede contener secretos aportados por error.
        self.exit(2, "error: argumentos inválidos\n")


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description="Valida configuración Workspace; el acceso live es opt-in y read-only."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Ejecuta una lectura real de Sheets (nunca escribe ni publica).",
    )
    parser.add_argument(
        "--id-solicitud",
        help="ID a buscar; requerido únicamente con --live.",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        # argparse mantiene su código, pero nunca serializamos argumentos recibidos.
        return int(error.code)

    correlation_id = str(uuid.uuid4())
    try:
        config = cargar_configuracion_workspace()
    except ConfiguracionWorkspaceError as error:
        _emitir({"resultado": error.code})
        return 2

    if not args.live:
        if args.id_solicitud is not None:
            _emitir({"resultado": "validation_request_invalid"})
            return 2
        _emitir(
            {
                "ambiente": config.ambiente,
                "correlation_id": correlation_id,
                "modo": "validacion",
                "resultado": "configuracion_valida",
                "recursos": config.resumen_seguro(),
            }
        )
        return 0

    if not args.id_solicitud:
        _emitir({"resultado": "live_request_invalid"})
        return 2

    try:
        # Falla antes de abrir red y diferencia configuración/auth de HTTP remoto.
        TokenEntornoProvider().obtener_access_token()
        fuente = GoogleSheetsFuenteSolicitudes(
            spreadsheet_id=config.spreadsheet_id,
            rango_a1=config.rango_a1,
            token_provider=TokenEntornoProvider(),
            timeout_s=config.timeout_s,
        )
        fuente.obtener(args.id_solicitud)
    except ConfiguracionWorkspaceError:
        _emitir(
            {
                "correlation_id": correlation_id,
                "modo": "live_read_only",
                "resultado": "workspace_auth_unavailable",
            }
        )
        return 3
    except FuenteSolicitudesError as error:
        _emitir(
            {
                "correlation_id": correlation_id,
                "modo": "live_read_only",
                "resultado": error.code,
            }
        )
        return 4

    _emitir(
        {
            "ambiente": config.ambiente,
            "correlation_id": correlation_id,
            "modo": "live_read_only",
            "resultado": "lectura_confirmada",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
