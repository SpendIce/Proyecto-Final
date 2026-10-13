#!/usr/bin/env python3
"""Respaldo diario del estado local del agente en Drive (#86, ADR 0009).

Empaqueta el estado declarado —registro durable de confirmaciones, los
JSONL de `logs/`, `insumos-procesados.jsonl`, el estado del canal Form, el
registro de decisiones y la cola de envíos— en un `.tar.gz` con manifiesto
de hashes y lo sube como archivo nuevo a la carpeta de respaldo de la
cuenta técnica. Después borra los respaldos propios que vencieron la
ventana de reconciliación (30 días): la única excepción a «el agente no
borra», cercada a esa carpeta, a la convención `agente1-respaldo-*.tar.gz`
y al marker `appProperties`, y auditada con hash y fecha.

Uso:

    python scripts/respaldar_estado.py \
        --salida salida \
        [--registro salida/registro-confirmaciones]

`--registro` es el directorio del registro durable de HU-012 (el mismo que
declara `AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES`); si no se pasa, el
artefacto lleva sólo el estado del directorio de salida.

La carpeta de respaldo y el canal del aviso salen del entorno, prefijo
`AGENTE1_RESPALDO_` (ver `respaldo.cargar_configuracion_respaldo`):

- `AGENTE1_RESPALDO_CARPETA_FAKE=<dir>` — modo offline declarado: un
  directorio local ocupa el lugar de la carpeta de Drive con el mismo
  contrato (crear nuevo, listar los propios, borrar los vencidos). El
  aviso al operador queda en `logs/avisos-operador-offline.jsonl`, sin
  correo ni red.
- `AGENTE1_RESPALDO_CARPETA_ID=<id>` + `AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA=SI`
  + `AGENTE1_RESPALDO_AVISO_DESTINATARIO=<correo>` — modo live: la carpeta
  real de Drive y el correo del operador, que tiene que estar en la lista
  de prueba de Gmail (`AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`). Las tres
  variables juntas son el doble opt-in de escritura real: nadie sube nada
  por una variable sola. La credencial es la de siempre
  (`construir_token_provider`), con `drive.file` y sin scopes nuevos.

El scheduler local (#84) invoca este comando una vez por día hábil en la
primera corrida en ventana, después de la purga (#87). Exit 0 cuando el
paso quedó asentado en la auditoría (`logs/respaldo-diario.jsonl`), 2
ante cualquier falla: el scheduler la marca `falla`, la reintenta en el
tick siguiente y la corrida sigue su camino.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.gmail_envio import (  # noqa: E402
    GmailDestinoConfirmaciones,
    cargar_destinatarios_prueba,
)
from agente1.google_workspace import TransporteHttp  # noqa: E402
from agente1.respaldo import (  # noqa: E402
    AVISOS_OFFLINE_NOMBRE,
    AvisoOperadorJsonl,
    CarpetaRespaldoLocal,
    ConfiguracionRespaldoError,
    GmailAvisoOperador,
    GoogleDriveRespaldoDiario,
    RespaldoDiarioError,
    cargar_configuracion_respaldo,
    correr_respaldo_diario,
)
from agente1.workspace_auth import construir_token_provider  # noqa: E402
from agente1.workspace_config import ConfiguracionWorkspaceError  # noqa: E402


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    transport: TransporteHttp | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Respalda el estado local en la carpeta configurada y borra "
            "los respaldos propios vencidos."
        )
    )
    parser.add_argument(
        "--salida",
        type=Path,
        required=True,
        help="directorio de salida del agente (queda bajo salida/ en el artefacto)",
    )
    parser.add_argument(
        "--registro",
        type=Path,
        default=None,
        help="directorio del registro durable de confirmaciones (opcional)",
    )
    parser.add_argument(
        "--ahora",
        default=None,
        help=(
            "instante ISO-8601 con zona horaria que queda como marca del "
            "respaldo (default: ahora UTC); fijo sólo para corridas "
            "reproducibles"
        ),
    )
    args = parser.parse_args(argv)

    ahora = None
    if args.ahora is not None:
        try:
            ahora = datetime.fromisoformat(args.ahora.replace("Z", "+00:00"))
        except ValueError:
            ahora = None
        if ahora is None or ahora.tzinfo is None:
            return _invalida("respaldo_arguments_invalid")

    try:
        config = cargar_configuracion_respaldo(environ)
    except ConfiguracionRespaldoError as exc:
        return _invalida(exc.code)
    if config is None:
        return _invalida("respaldo_config_incomplete")

    try:
        if config.carpeta_id is not None:
            # Modo live: el token se pide por operación adentro del adapter;
            # la pre-verificación sólo comprueba que la credencial existe,
            # sin tocar la red.
            token_provider = construir_token_provider(environ)
            destino = GoogleDriveRespaldoDiario(
                carpeta_id=config.carpeta_id,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            )
            permitidos = cargar_destinatarios_prueba(environ)
            assert config.aviso_destinatario is not None
            if config.aviso_destinatario.strip().lower() not in permitidos:
                # El aviso tiene que poder salir: un destinatario fuera de
                # la lista de prueba sería rechazado justo cuando avisa.
                return _invalida("respaldo_aviso_off_test_list")
            aviso = GmailAvisoOperador(
                destinatario=config.aviso_destinatario,
                destino=GmailDestinoConfirmaciones(
                    destinatarios_permitidos=permitidos,
                    token_provider=token_provider,
                    transport=transport,
                ),
            )
        else:
            # Modo fake declarado: la carpeta local y el aviso JSONL, sin
            # red y sin afirmar que se subió a Drive.
            assert config.carpeta_fake is not None
            destino = CarpetaRespaldoLocal(config.carpeta_fake)
            aviso = AvisoOperadorJsonl(
                args.salida / "logs" / AVISOS_OFFLINE_NOMBRE
            )
    except ConfiguracionWorkspaceError as exc:
        return _invalida(exc.code)
    except OSError:
        return _invalida("respaldo_entrada_inaccesible")

    try:
        resultado = correr_respaldo_diario(
            directorio_salida=args.salida,
            destino=destino,
            registro_confirmaciones=args.registro,
            aviso=aviso,
            ahora=ahora,
        )
    except RespaldoDiarioError as exc:
        return _invalida(exc.code)
    except OSError:
        return _invalida("respaldo_entrada_inaccesible")

    print(
        json.dumps(
            {
                "status": "OK",
                "nombre": resultado.nombre,
                "subido": resultado.subido,
                "omitido_existente": resultado.omitido_existente,
                "artefacto_sha256": resultado.artefacto_sha256,
                "archivos": resultado.archivos,
                "eliminados": len(resultado.eliminados),
                "modo": config.modo,
                "audit_path": str(resultado.audit_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _invalida(code: str) -> int:
    print(
        json.dumps(
            {"status": "INVALID", "error_code": code},
            sort_keys=True,
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
