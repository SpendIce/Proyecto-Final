#!/usr/bin/env python3
"""Runner de la emisión de certificados HU-014 con lista de cierre (#75).

Corre el circuito de `agente1.certificados_emision` para una actividad:
lee la lista de cierre, exige la línea descriptiva aprobada (#74) y la
aprobación del lote por el Form de decisiones (#72), y entrega un PDF por
titular. Es el disparo manual del mismo circuito que despacha la intención
`emitir_certificados` del canal de pedidos; el disparo automático al
cerrar la actividad es HU-015 y queda fuera de este ticket.

Dos modos, como en `atender_canal_form.py`:

- **offline** (default): la lista de cierre es un CSV local con la misma
  forma de columnas (`nombre,apellido,dni,mail,tratamiento,condicion`), la
  línea descriptiva se lee de `--linea` (un archivo fuera del repo, tal
  como la va a entregar #74) y el correo se escribe en
  `entregas-certificados-offline.jsonl` en lugar de salir por Gmail — del
  adjunto queda sólo el sha256, no el PDF. Las decisiones de línea y de
  lote se registran a mano en `<directorio>/estado-decisiones/` (el mismo
  directorio que usa `registrar_form_decisiones.py`), así el recorrido
  completo se ensaya sin red.
- **live**: requiere `--live` y `--confirm-write-workspace` juntos, el
  ambiente D2 y el entorno configurado: `AGENTE1_WORKSPACE_*` para la
  cuenta técnica, `AGENTE1_FORM_DECISIONES_*` para el segundo Form,
  `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` para la lista de prueba, y las
  variables propias del circuito:
    `AGENTE1_CERTIFICADOS_LISTA_SHEET_ID`   Sheet D2 de la lista de cierre
    `AGENTE1_CERTIFICADOS_LISTA_RANGO_A1`   rango A1 de esa lista
    `AGENTE1_CERTIFICADOS_LINEA_PATH`       archivo con la línea aprobada
    `AGENTE1_CERTIFICADOS_APROBADOR`        correo del rol utilitario
    `AGENTE1_CERTIFICADOS_SOLICITANTE`      correo de quien cargó la lista
  Todo eso sale del entorno y nunca de argv, igual que el resto de la
  configuración institucional.

La salida es un JSON por corrida: estado, conteos y códigos, nunca datos
de las personas de la lista.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.canal_form import LectorValoresCsv
from agente1.certificados_emision import (
    DestinoCorreoArchivo,
    procesar_emision_certificados,
)
from agente1.decisiones_form import (
    EnlacesDecisiones,
    RegistroDecisiones,
    cargar_configuracion_form_decisiones,
)
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.gmail_envio import GmailDestinoConfirmaciones, GmailEnvioError
from agente1.google_workspace import (
    GoogleSheetsFuenteSolicitudes,
    GoogleSheetsLectorValores,
)
from agente1.workspace_auth import construir_token_provider
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    cargar_configuracion_workspace,
)
from agente1.workspace_e2e import RunnerWorkspaceError


DATASET_DEFAULT = ROOT / "data" / "actividades_sinteticas.csv"
ENTREGAS_OFFLINE_NOMBRE = "entregas-certificados-offline.jsonl"
CERT_PREFIX = "AGENTE1_CERTIFICADOS_"


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


class ConfiguracionCertificadosError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _env_requerido(nombre: str) -> str:
    valor = os.environ.get(nombre, "")
    if not isinstance(valor, str) or not valor.strip():
        raise ConfiguracionCertificadosError("certificados_config_missing")
    return valor.strip()


def _linea_desde_path(path: Path | None) -> str | None:
    """La línea descriptiva viene de un archivo externo, nunca de argv."""

    if path is None or not path.is_file():
        return None
    texto = path.read_text(encoding="utf-8").strip()
    return texto or None


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Corre la emisión de certificados de una actividad sobre su "
            "lista de cierre. Por defecto offline; live exige doble opt-in."
        )
    )
    parser.add_argument("--actividad", required=True)
    parser.add_argument(
        "--directorio",
        type=Path,
        default=ROOT / "tmp" / "emitir-certificados",
        help="Salida de la corrida: log de emisión, estado de decisiones y entregas offline.",
    )
    parser.add_argument(
        "--lista-csv",
        type=Path,
        help="CSV que imita la lista de cierre (offline).",
    )
    parser.add_argument(
        "--linea",
        type=Path,
        help="Archivo de texto con la línea descriptiva aprobada (offline).",
    )
    parser.add_argument(
        "--aprobador",
        help="Correo del rol utilitario que aprueba el lote (offline).",
    )
    parser.add_argument(
        "--solicitante",
        help="Correo de quien pidió la emisión y cargó la lista (offline).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DATASET_DEFAULT,
        help="Dataset de actividades (offline).",
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-write-workspace", action="store_true")
    try:
        args = parser.parse_args(argv)
        if not args.live and args.confirm_write_workspace:
            raise RunnerWorkspaceError("runner_live_not_enabled")
        if not args.live and (
            args.lista_csv is None
            or not args.aprobador
            or not args.solicitante
        ):
            raise RunnerWorkspaceError("runner_offline_args_required")

        directorio_decisiones = args.directorio / "estado-decisiones"
        registro = RegistroDecisiones(directorio_decisiones)

        if args.live:
            config_ws = cargar_configuracion_workspace()
            if config_ws.ambiente != "D2":
                raise RunnerWorkspaceError("runner_live_environment_invalid")
            config_decisiones = cargar_configuracion_form_decisiones()
            token_provider = construir_token_provider(
                timeout_s=config_ws.timeout_s
            )
            token = token_provider.obtener_access_token()
            if not isinstance(token, str) or not token.strip():
                raise RunnerWorkspaceError("runner_live_auth_unavailable")
            enlaces = EnlacesDecisiones(
                registro=registro,
                form_id=config_decisiones.form_id,
                entry_tipo=config_decisiones.entry_tipo,
                entry_objeto=config_decisiones.entry_objeto,
                entry_decision=config_decisiones.entry_decision,
            )
            lector_lista = GoogleSheetsLectorValores(
                spreadsheet_id=_env_requerido(
                    CERT_PREFIX + "LISTA_SHEET_ID"
                ),
                rango_a1=_env_requerido(CERT_PREFIX + "LISTA_RANGO_A1"),
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
            )
            linea = _linea_desde_path(
                Path(_env_requerido(CERT_PREFIX + "LINEA_PATH"))
            )
            correo_aprobador = _env_requerido(CERT_PREFIX + "APROBADOR")
            solicitante = _env_requerido(CERT_PREFIX + "SOLICITANTE")
            destino = GmailDestinoConfirmaciones.desde_entorno(
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
            )
            # La actividad se lee de la misma planilla D2 que alimenta los
            # demás pipelines; la lista de cierre es una Sheet aparte.
            fuente = GoogleSheetsFuenteSolicitudes(
                spreadsheet_id=config_ws.spreadsheet_id,
                rango_a1=config_ws.rango_a1,
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
            )
            resumen_config: dict[str, object] = {
                "workspace": config_ws.resumen_seguro(),
                "form_decisiones": config_decisiones.resumen_seguro(),
            }
            modo = "live_write_opt_in"
        else:
            enlaces = EnlacesDecisiones(
                registro=registro,
                form_id="form_decisiones_offline",
                entry_tipo="entry.000000021",
                entry_objeto="entry.000000022",
                entry_decision="entry.000000023",
            )
            lector_lista = LectorValoresCsv(args.lista_csv)
            linea = _linea_desde_path(args.linea)
            correo_aprobador = args.aprobador
            solicitante = args.solicitante
            destino = DestinoCorreoArchivo(
                args.directorio / "estado-canal-form" / ENTREGAS_OFFLINE_NOMBRE
            )
            fuente = CsvFuenteSolicitudes(args.csv)
            resumen_config = {"modo_offline": True}
            modo = "offline_fake"

        resultado = procesar_emision_certificados(
            id_actividad=args.actividad,
            fuente=fuente,
            lector_lista=lector_lista,
            linea_descriptiva=linea,
            registro_decisiones=registro,
            enlaces=enlaces,
            destino=destino,
            correo_aprobador=correo_aprobador,
            solicitante_correo=solicitante,
            directorio_salida=args.directorio,
        )
    except ConfiguracionWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except ConfiguracionCertificadosError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except RunnerWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (FuenteSolicitudesError, GmailEnvioError) as exc:
        _emitir({"estado": "FALLIDA", "resultado": exc.code})
        return 3
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3

    _emitir(
        {
            "estado": resultado.estado,
            "correlation_id": resultado.correlation_id,
            "emitidas": resultado.emitidas,
            "entregas_fallidas": resultado.entregas_fallidas,
            "error": resultado.error,
            "resumen": resultado.resumen,
            "log_path": resultado.log_path,
            "modo": modo,
            "config": resumen_config,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
