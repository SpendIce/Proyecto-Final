#!/usr/bin/env python3
"""Runner del registro de decisiones por Google Form (#72).

Lee, una vez, las respuestas nuevas del segundo Form («Registro de
decisiones»): valida cada una contra el padrón de roles y el catálogo de
decisiones, y la deja en la auditoría (`decisiones-procesadas.jsonl`), sea
registrada o rechazada con su código. El agente no ejecuta nada a partir de
una decisión: la difusión la hace la persona y el registro es la evidencia
(#52).

Dos modos, como `atender_canal_form.py`:

- **offline** (default): la "hoja" es un CSV local con la misma forma de
  columnas (marca temporal, correo, tipo, objeto, decisión). No abre red.
  El padrón sigue siendo archivo externo —`--padron` o
  `AGENTE1_PADRON_ROLES_PATH`— porque la autorización por rol se ensaya
  igual que en producción.
- **live**: requiere `--live` y `--confirm-write-workspace` juntos. La
  configuración sale del entorno (`AGENTE1_FORM_DECISIONES_*` para la hoja
  y el Form; `AGENTE1_PADRON_ROLES_PATH` para el padrón) y el token de su
  propia variable. Nada de eso va por argv.

`--declarar tipo:objeto_id` abre un objeto a decisión e imprime los links
prellenados del tipo: es lo que hacen los correos del agente al emitir una
decisión (el canal de pedidos lo hace solo para publicaciones; acá queda
el camino manual para plantillas y lotes). El objeto declarado es lo que el
lector va a aceptar después: un id que no fue declarado se rechaza como
`objeto_inexistente`.

La salida es un JSON por respuesta procesada más un resumen: resultados,
códigos y hashes, nunca correos en claro.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agente1.canal_form import (
    CanalFormError,
    LectorValoresCsv,
    PadronRoles,
    cargar_padron_roles_csv,
)
from agente1.decisiones_form import (
    PENDIENTES_NOMBRE,
    PROCESADAS_NOMBRE,
    TIPOS_DECISION,
    CanalFormDecisiones,
    DecisionesFormError,
    EnlacesDecisiones,
    RegistroDecisiones,
    cargar_configuracion_form_decisiones,
    crear_lector_decisiones,
)
from agente1.fuentes import FuenteSolicitudesError
from agente1.google_workspace import ID_RE
from agente1.workspace_auth import construir_token_provider
from agente1.workspace_config import ConfiguracionWorkspaceError
from agente1.workspace_e2e import RunnerWorkspaceError

ROOT = Path(__file__).resolve().parents[1]

# Ids de mentira del modo offline: el contrato con el Form se ensaya igual
# (minteo de links y lectura por columnas), sólo que sin red.
_FORM_ID_OFFLINE = "form_decisiones_offline"
_ENTRY_TIPO_OFFLINE = "entry.000000021"
_ENTRY_OBJETO_OFFLINE = "entry.000000022"
_ENTRY_DECISION_OFFLINE = "entry.000000023"


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _cargar_padron(args: argparse.Namespace) -> PadronRoles:
    """El padrón es un archivo externo en los dos modos."""

    if args.padron is not None:
        return cargar_padron_roles_csv(args.padron)
    return PadronRoles.desde_entorno()


def _parsear_declaracion(declaracion: str) -> tuple[str, str]:
    """`tipo:objeto_id` desde argv; el id nunca lleva espacios ni prosa."""

    tipo, separador, objeto_id = declaracion.partition(":")
    tipo = tipo.strip()
    objeto_id = objeto_id.strip()
    if (
        not separador
        or tipo not in TIPOS_DECISION
        or ID_RE.fullmatch(objeto_id) is None
    ):
        raise RunnerWorkspaceError("runner_declaracion_invalid")
    return tipo, objeto_id


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Registra las decisiones del segundo Form una vez. Por defecto "
            "corre offline con un CSV de respuestas; live requiere doble "
            "opt-in."
        )
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        default=ROOT / "tmp" / "atender-canal-form",
        help=(
            "Directorio de trabajo compartido: el estado del registro va en "
            "<directorio>/estado-decisiones/. Para el circuito completo "
            "(pedido -> correo con links -> decisión) tiene que ser el mismo "
            "directorio que usó scripts/atender_canal_form.py."
        ),
    )
    parser.add_argument(
        "--respuestas-csv",
        type=Path,
        help=(
            "CSV que imita la hoja de respuestas del Form de decisiones "
            "(marca temporal, correo, tipo, objeto, decisión). Requerido "
            "en offline."
        ),
    )
    parser.add_argument(
        "--padron",
        type=Path,
        help=(
            "Ruta al padrón de roles (CSV correo,rol). Si no se pasa, se lee "
            "AGENTE1_PADRON_ROLES_PATH."
        ),
    )
    parser.add_argument(
        "--declarar",
        action="append",
        default=[],
        metavar="TIPO:OBJETO_ID",
        help=(
            "Declara un objeto pendiente de decisión y emite sus links "
            "prellenados (repetible). Ej.: lote:lote-2026-10, "
            "plantilla:confirmacion_inscripcion_v1."
        ),
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-write-workspace", action="store_true")
    try:
        args = parser.parse_args(argv)
        if not args.live and args.confirm_write_workspace:
            raise RunnerWorkspaceError("runner_live_not_enabled")
        if not args.live and args.respuestas_csv is None:
            raise RunnerWorkspaceError("runner_offline_csv_required")

        directorio_decisiones = args.directorio / "estado-decisiones"
        registro = RegistroDecisiones(directorio_decisiones)

        if args.live:
            config = cargar_configuracion_form_decisiones()
            token_provider = construir_token_provider(
                timeout_s=config.timeout_s
            )
            # Token pedido antes de cualquier lectura: si la credencial no
            # sirve, la corrida falla al preparar y no a mitad de camino.
            token = token_provider.obtener_access_token()
            if not isinstance(token, str) or not token.strip():
                raise RunnerWorkspaceError("runner_live_auth_unavailable")
            lector = crear_lector_decisiones(
                config,
                token_provider=token_provider,
                transport=None,
            )
            enlazador = EnlacesDecisiones(
                registro=registro,
                form_id=config.form_id,
                entry_tipo=config.entry_tipo,
                entry_objeto=config.entry_objeto,
                entry_decision=config.entry_decision,
            )
            resumen_config: dict[str, object] = {
                "form_decisiones": config.resumen_seguro()
            }
            modo = "live_write_opt_in"
        else:
            lector = LectorValoresCsv(args.respuestas_csv)
            enlazador = EnlacesDecisiones(
                registro=registro,
                form_id=_FORM_ID_OFFLINE,
                entry_tipo=_ENTRY_TIPO_OFFLINE,
                entry_objeto=_ENTRY_OBJETO_OFFLINE,
                entry_decision=_ENTRY_DECISION_OFFLINE,
            )
            resumen_config = {"modo_offline": True}
            modo = "offline_fake"

        for declaracion in args.declarar:
            tipo, objeto_id = _parsear_declaracion(declaracion)
            enlaces = enlazador.declarar_y_enlaces(
                tipo=tipo, objeto_id=objeto_id
            )
            _emitir(
                {
                    "declarado": {
                        "tipo": tipo,
                        "objeto_id": objeto_id,
                        "enlaces": enlaces,
                    }
                }
            )

        padron = _cargar_padron(args)
        canal = CanalFormDecisiones(
            lector=lector, padron=padron, registro=registro
        )
        resultados = canal.atender()
    except ConfiguracionWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (RunnerWorkspaceError, DecisionesFormError, CanalFormError) as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except FuenteSolicitudesError as exc:
        _emitir({"estado": "FALLIDA", "resultado": exc.code})
        return 3
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3

    for resultado in resultados:
        _emitir(
            {
                "id_respuesta": resultado.id_respuesta,
                "resultado": resultado.resultado,
                "rechazo_codigo": resultado.rechazo_codigo,
                "tipo": resultado.tipo,
                "objeto_id": resultado.objeto_id,
                "decision": resultado.decision,
                "rol": resultado.rol,
                "rol_origen": resultado.rol_origen,
                "timestamp": resultado.timestamp,
            }
        )
    _emitir(
        {
            "procesadas": len(resultados),
            "modo": modo,
            "registro_decisiones": PROCESADAS_NOMBRE,
            "registro_pendientes": PENDIENTES_NOMBRE,
            "config": resumen_config,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
