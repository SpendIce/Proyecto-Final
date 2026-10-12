#!/usr/bin/env python3
"""Runner del canal de pedidos por Google Form (#71).

Atiende, una vez, los pedidos pendientes de la hoja de respuestas del Form:
lee las filas nuevas, las pasa al núcleo y escribe la respuesta del canal —
un correo de aviso al correo verificado del pedido más una línea en el
registro local de atendidos. Cada corrida es puntual a propósito: quien
opera la demo decide cuándo corre el bucle; relanzarlo atiende sólo lo que
siga pendiente.

Dos modos, como en `workspace_e2e.py`:

- **offline** (default): la "hoja" es un CSV local con la misma forma de
  columnas (marca temporal, correo, pedido), el aviso se escribe en
  `avisos-offline.jsonl` bajo el directorio de estado en lugar de salir por
  Gmail, y el borrador queda en `borradores/` como Markdown. No abre red ni
  usa credenciales. El padrón sigue siendo un archivo externo —`--padron`
  o `AGENTE1_PADRON_ROLES_PATH`— porque la autorización por rol se ensaya
  igual que en producción, no se simula.
- **live**: requiere `--live` y `--confirm-write-workspace` juntos, y el
  ambiente D2 en `AGENTE1_WORKSPACE_AMBIENTE`. La configuración sale del
  entorno (`AGENTE1_WORKSPACE_*` para la fuente de actividades, la carpeta
  y la plantilla de Drive; `AGENTE1_FORM_PEDIDOS_*` para la hoja de
  respuestas y el Form; `AGENTE1_PADRON_ROLES_PATH` para el padrón;
  `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` para la lista de prueba del aviso) y
  el token de su propia variable. Nada de eso se pasa por argv, porque los
  argumentos quedan visibles en la lista de procesos.

El correo de «borrador listo» adjunta además los links «lo publiqué / lo
descarté» del segundo Form, «Registro de decisiones» (#72): en offline con
ids de mentira y el registro en `<directorio>/estado-decisiones/`; en live
sólo si el entorno declara `AGENTE1_FORM_DECISIONES_*`. Las respuestas de
ese Form las procesa `scripts/registrar_form_decisiones.py`.

La salida es un JSON por pedido más un resumen: estados, códigos y hashes,
nunca prosa ni correos en claro.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from agente1.canal import atender_canal
from agente1.canal_form import (
    ATENDIDOS_NOMBRE,
    CanalFormError,
    CanalFormPedidos,
    LectorValoresCsv,
    PadronRoles,
    cargar_configuracion_canal_form,
    cargar_padron_roles_csv,
    crear_lector_respuestas,
)
from agente1.decisiones_form import (
    EnlacesDecisiones,
    FORM_DECISIONES_PREFIX,
    RegistroDecisiones,
    cargar_configuracion_form_decisiones,
)
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.gmail_envio import GmailDestinoConfirmaciones, GmailEnvioError
from agente1.google_workspace import (
    GoogleDrivePlantillaDestinoBorradores,
    GoogleSheetsFuenteSolicitudes,
)
from agente1.ollama import OllamaGenerator
from agente1.procesamiento import FakeGenerator
from agente1.workspace_auth import construir_token_provider
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    cargar_configuracion_workspace,
)
from agente1.workspace_e2e import RunnerWorkspaceError


ROOT = Path(__file__).resolve().parents[1]
DATASET_DEFAULT = ROOT / "data" / "actividades_sinteticas.csv"
FICHA_SYN_001 = ROOT / "golden" / "SYN-001.ficha.md"
AVISOS_OFFLINE_NOMBRE = "avisos-offline.jsonl"


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


class _DestinoAvisosArchivo:
    """Destino de avisos del modo offline: un JSONL en vez de `gmail.send`.

    Implementa el puerto `DestinoConfirmaciones` escribiendo cada aviso —
    con su destinatario, porque la única forma de revisar un aviso offline
    es leerlo— en `avisos-offline.jsonl` bajo el directorio de estado. No
    toca la red: el ensayo del canal no envía correo de verdad aunque el
    contenido sea el mismo que Gmail mandaría.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        registro = {
            "idempotency_key": idempotency_key,
            "destinatario": destinatario,
            "asunto": asunto,
            "cuerpo": cuerpo,
        }
        with self._path.open("a", encoding="utf-8") as archivo:
            archivo.write(
                json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n"
            )


def _fake_output_desde_golden() -> str:
    """Ficha golden ya validada de `SYN-001` como salida del modelo fake.

    Mismo criterio que `atender_canal_planilla.py`: en offline el núcleo
    sólo produce un borrador que pasa el gate para esa actividad, porque el
    generator simulado devuelve esta ficha. No es una limitación del canal.
    """

    return FICHA_SYN_001.read_text(encoding="utf-8").strip()


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _cargar_padron(args: argparse.Namespace) -> PadronRoles:
    """El padrón es un archivo externo en los dos modos: `--padron` si se
    pasó (ruta local, nada secreto en argv) o la variable de entorno."""

    if args.padron is not None:
        return cargar_padron_roles_csv(args.padron)
    return PadronRoles.desde_entorno()


def _enlaces_decisiones(
    directorio: Path,
    *,
    config=None,
) -> EnlacesDecisiones:
    """Puente al segundo Form (#72): declara pendientes y mintea links.

    En offline los ids del Form son de mentira —el contrato se ensaya igual—
    y el registro comparte directorio con `scripts/registrar_form_decisiones.py`
    para que la decisión encuentre después el objeto declarado. En live la
    config sale del entorno y se exige completa: un link con un entry mal
    cargado produciría decisiones que no validan.
    """

    registro = RegistroDecisiones(directorio)
    if config is None:
        return EnlacesDecisiones(
            registro=registro,
            form_id="form_decisiones_offline",
            entry_tipo="entry.000000021",
            entry_objeto="entry.000000022",
            entry_decision="entry.000000023",
        )
    return EnlacesDecisiones(
        registro=registro,
        form_id=config.form_id,
        entry_tipo=config.entry_tipo,
        entry_objeto=config.entry_objeto,
        entry_decision=config.entry_decision,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Atiende los pedidos del Form una vez. Por defecto corre offline "
            "con un CSV de respuestas; live requiere doble opt-in y D2."
        )
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        default=ROOT / "tmp" / "atender-canal-form",
        help="Salida de la corrida: borradores, logs, estado del canal y avisos offline.",
    )
    parser.add_argument(
        "--respuestas-csv",
        type=Path,
        help="CSV que imita la hoja de respuestas del Form (marca temporal, correo, pedido). Requerido en offline.",
    )
    parser.add_argument(
        "--padron",
        type=Path,
        help="Ruta al padrón de roles (CSV correo,rol). Si no se pasa, se lee AGENTE1_PADRON_ROLES_PATH.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DATASET_DEFAULT,
        help="Dataset de actividades contra el que se resuelve cada pedido (offline).",
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-write-workspace", action="store_true")
    parser.add_argument("--modelo", default="llama3.1:8b")
    try:
        args = parser.parse_args(argv)
        if not args.live and args.confirm_write_workspace:
            raise RunnerWorkspaceError("runner_live_not_enabled")
        if not args.live and args.respuestas_csv is None:
            raise RunnerWorkspaceError("runner_offline_csv_required")

        directorio_estado = args.directorio / "estado-canal-form"
        directorio_decisiones = args.directorio / "estado-decisiones"

        if args.live:
            config_ws = cargar_configuracion_workspace()
            if config_ws.ambiente != "D2":
                raise RunnerWorkspaceError("runner_live_environment_invalid")
            config_form = cargar_configuracion_canal_form()
            token_provider = construir_token_provider(
                timeout_s=config_ws.timeout_s
            )
            # Token pedido antes de cualquier lectura: si la credencial no
            # sirve, la corrida falla al preparar y no a mitad de camino.
            token = token_provider.obtener_access_token()
            if not isinstance(token, str) or not token.strip():
                raise RunnerWorkspaceError("runner_live_auth_unavailable")
            padron = _cargar_padron(args)
            # El segundo Form (#72) es opt-in en live: si el entorno declara
            # `AGENTE1_FORM_DECISIONES_*` el correo de borrador listo trae los
            # links «lo publiqué / lo descarté»; si no hay nada configurado el
            # canal de pedidos corre igual, sin enlaces de decisión.
            decisiones_live = None
            if any(
                clave.startswith(FORM_DECISIONES_PREFIX) for clave in os.environ
            ):
                decisiones_live = _enlaces_decisiones(
                    directorio_decisiones,
                    config=cargar_configuracion_form_decisiones(),
                )
            canal = CanalFormPedidos(
                lector=crear_lector_respuestas(
                    config=config_form,
                    token_provider=token_provider,
                ),
                padron=padron,
                avisos=GmailDestinoConfirmaciones.desde_entorno(
                    token_provider=token_provider,
                    timeout_s=config_ws.timeout_s,
                ),
                directorio_estado=directorio_estado,
                form_id=config_form.form_id,
                entry_id=config_form.entry_id,
                decisiones=decisiones_live,
            )
            fuente = GoogleSheetsFuenteSolicitudes(
                spreadsheet_id=config_ws.spreadsheet_id,
                rango_a1=config_ws.rango_a1,
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
            )
            destino = GoogleDrivePlantillaDestinoBorradores(
                plantilla_id=config_ws.template_id,
                carpeta_id=config_ws.folder_id,
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
            )
            generator = OllamaGenerator(modelo=args.modelo)
            resumen_config: dict[str, object] = {
                "workspace": config_ws.resumen_seguro(),
                "canal_form": config_form.resumen_seguro(),
                "form_decisiones": (
                    decisiones_live is not None
                ),
            }
            modo = "live_write_opt_in"
        else:
            padron = _cargar_padron(args)
            canal = CanalFormPedidos(
                lector=LectorValoresCsv(args.respuestas_csv),
                padron=padron,
                avisos=_DestinoAvisosArchivo(
                    directorio_estado / AVISOS_OFFLINE_NOMBRE
                ),
                directorio_estado=directorio_estado,
                form_id="form_offline_demo",
                entry_id="entry.000000001",
                # Offline el circuito completo se ensaya siempre: el aviso
                # trae los links del Form de decisiones y el objeto queda
                # declarado para `registrar_form_decisiones.py`.
                decisiones=_enlaces_decisiones(directorio_decisiones),
            )
            fuente = CsvFuenteSolicitudes(args.csv)
            destino = None  # MarkdownDestinoBorradores por defecto del núcleo
            generator = FakeGenerator(_fake_output_desde_golden())
            resumen_config = {"modo_offline": True}
            modo = "offline_fake"

        resultados = atender_canal(
            canal,
            fuente=fuente,
            directorio_salida=args.directorio,
            generator=generator,
            destino=destino,
        )
    except ConfiguracionWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (RunnerWorkspaceError, CanalFormError) as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (FuenteSolicitudesError, GmailEnvioError) as exc:
        _emitir({"estado": "FALLIDA", "resultado": exc.code})
        return 3
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3

    for resultado in resultados:
        _emitir(
            {
                "correlation_id": resultado.correlation_id,
                "estado": resultado.estado,
                "intencion": resultado.intencion,
            }
        )
    _emitir(
        {
            "atendidos": len(resultados),
            "modo": modo,
            "registro_atendidos": ATENDIDOS_NOMBRE,
            "config": resumen_config,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
