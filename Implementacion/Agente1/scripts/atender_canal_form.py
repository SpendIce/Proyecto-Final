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

Un pedido «emití los certificados de <actividad>» (#75) despacha al
circuito de lote de cierre de `certificados_emision`, cableado sólo cuando
hay lista declarada: en offline con `--lista-csv` (más `--aprobador` y, si
hay, `--linea`), en live con las variables `AGENTE1_CERTIFICADOS_*` sobre
la Sheet D2 de la lista. Las entregas de título van al mismo medio que el
aviso: Gmail con lista de prueba en live, `entregas-certificados-offline.jsonl`
en offline.

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
from agente1.certificados_emision import (
    DestinoCorreoArchivo,
    construir_emisor_certificados,
)
from agente1.decisiones_form import (
    EnlacesDecisiones,
    FORM_DECISIONES_PREFIX,
    RegistroDecisiones,
    cargar_configuracion_form_decisiones,
)
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.gmail_envio import GmailDestinoConfirmaciones, GmailEnvioError
from agente1.pagos import (
    ControlPagosError,
    PlanPago,
    cargar_plan_pagos_csv,
)
from agente1.google_workspace import (
    GoogleDrivePlantillaDestinoBorradores,
    GoogleSheetsFuenteSolicitudes,
    GoogleSheetsLectorValores,
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
ENTREGAS_CERTIFICADOS_NOMBRE = "entregas-certificados-offline.jsonl"
CERT_PREFIX = "AGENTE1_CERTIFICADOS_"


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


# Salida del generator fake para la intención `generar_plantilla_actividad`
# (#73): prosa descriptiva sin un solo dato — todo valor viaja como
# `{{variable}}`— porque el gate de `plantilla_actividad_v1` descarta la
# salida entera ante un dígito, una fecha, un importe, un correo o un
# enlace en el texto. Hay una variante por cada forma del pedido:
#
# - con plan de pago, el contrato exige `{{detalle_cuotas}}` y
#   `{{medios_pago}}`; sin plan esas variables están prohibidas. El fake
#   elige mirando el prompt — el listado de variables requeridas que el
#   pipeline le armó al modelo—, igual que un modelo real decidiría.
_SALIDA_PLANTILLA_BASE = (
    "Hola {{nombre_destinatario}},\n\n"
    "Te escribimos por tu preinscripción a {{actividad}}, que comienza el "
    "{{fecha_inicio}}.\n\n"
    "La propuesta acerca contenidos y herramientas de la facultad a la "
    "comunidad, con un formato abierto y pensado para quienes se acercan "
    "por primera vez. Las instancias de trabajo combinan encuentros "
    "guiados con espacios de consulta, y el equipo docente acompaña a "
    "cada participante durante todo el recorrido.\n"
)
_SALIDA_PLANTILLA_CIERRE = "\nContacto: {{contacto}}\n"
_SALIDA_PLANTILLA_BLOQUE_PLAN = (
    "\nEl valor y las formas de pago de la actividad son:\n"
    "{{detalle_cuotas}}\n"
    "Medios de pago: {{medios_pago}}.\n"
    "{{bonificaciones}}\n"
)


class _GeneradorOffline:
    """Generator fake del modo offline, con una salida por tipo de pieza.

    Reconoce el prompt de plantilla de actividad por su `PROMPT_VERSION`
    declarada en el propio texto que el pipeline le pasa al modelo, y
    devuelve la variante con o sin bloque de plan según las variables
    requeridas que el prompt enumera. Para cualquier otro prompt devuelve
    la ficha golden, como `FakeGenerator`.
    """

    modelo = "fake-offline"

    def __init__(self, salida_gacetilla: str) -> None:
        self._salida_gacetilla = salida_gacetilla

    def generar(self, prompt: str) -> str:
        if "PROMPT_VERSION: plantilla_actividad_generacion_v1" in prompt:
            # El bloque de pago sólo va si el prompt declara la actividad
            # arancelada en sus DATOS_JSON: la mención de {{detalle_cuotas}}
            # en la base no alcanza para distinguir, porque está en el
            # texto del prompt cualquiera sea el plan.
            bloque_plan = (
                _SALIDA_PLANTILLA_BLOQUE_PLAN
                if '"arancelada": true' in prompt
                else ""
            )
            return (
                _SALIDA_PLANTILLA_BASE + bloque_plan + _SALIDA_PLANTILLA_CIERRE
            )
        return self._salida_gacetilla


def _planes_desde_csvs(rutas: list[Path]) -> dict[str, PlanPago]:
    """Mapa actividad → PlanPago a partir de los `--plan-csv` recibidos.

    Cada archivo es un plan en formato largo (`cargar_plan_pagos_csv`); el
    mapa se arma por `actividad_id`, la misma llave con la que el núcleo
    resuelve el plan de una actividad. Dos planes sobre la misma actividad
    son un error de configuración, no un dato a deducir.
    """

    planes: dict[str, PlanPago] = {}
    for ruta in rutas:
        plan = cargar_plan_pagos_csv(ruta)
        if plan.actividad_id in planes:
            raise ControlPagosError("plan_actividad_duplicada")
        planes[plan.actividad_id] = plan
    return planes


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


def _linea_desde_path(path: Path | None) -> str | None:
    """La línea descriptiva viene de un archivo externo, nunca de argv."""

    if path is None or not path.is_file():
        return None
    texto = path.read_text(encoding="utf-8").strip()
    return texto or None


def _emisor_offline(
    args: argparse.Namespace,
    *,
    fuente,
    directorio_decisiones: Path,
    directorio_salida: Path,
    directorio_estado: Path,
):
    """Emisor del pedido «emití los certificados» en modo offline (#75).

    Se cablea sólo cuando la corrida trae una lista de cierre (`--lista-csv`);
    sin ella, el pedido de emisión termina `emisor_no_configurado` igual que
    cualquier otro despacho sin medio. La línea descriptiva se lee de
    `--linea` si está, igual que la va a entregar #74: si falta, el circuito
    responde `linea_descriptiva_ausente`, no inventa el texto.
    """

    if args.lista_csv is None:
        return None
    if not args.aprobador:
        raise RunnerWorkspaceError("runner_offline_aprobador_required")
    registro = RegistroDecisiones(directorio_decisiones)
    return construir_emisor_certificados(
        fuente=fuente,
        lector_lista=LectorValoresCsv(args.lista_csv),
        linea_descriptiva=_linea_desde_path(args.linea),
        registro_decisiones=registro,
        enlaces=_enlaces_decisiones(directorio_decisiones),
        destino=DestinoCorreoArchivo(
            directorio_estado / ENTREGAS_CERTIFICADOS_NOMBRE
        ),
        correo_aprobador=args.aprobador,
        directorio_salida=directorio_salida,
    )


def _emisor_live(
    *,
    fuente,
    token_provider,
    timeout_s: float,
    directorio_decisiones: Path,
    directorio_salida: Path,
):
    """Emisor live: Sheet D2 de lista, línea por archivo y Gmail con lista.

    Opt-in como el segundo Form: sin `AGENTE1_CERTIFICADOS_LISTA_SHEET_ID`
    el despacho de `emitir_certificados` queda sin medio configurado. El
    resto de la config del circuito sale del entorno y es obligatoria.
    """

    if not os.environ.get(CERT_PREFIX + "LISTA_SHEET_ID", "").strip():
        return None
    requeridas = (
        "LISTA_RANGO_A1",
        "LINEA_PATH",
        "APROBADOR",
    )
    for clave in requeridas:
        if not os.environ.get(CERT_PREFIX + clave, "").strip():
            raise RunnerWorkspaceError("certificados_config_missing")
    registro = RegistroDecisiones(directorio_decisiones)
    return construir_emisor_certificados(
        fuente=fuente,
        lector_lista=GoogleSheetsLectorValores(
            spreadsheet_id=os.environ[CERT_PREFIX + "LISTA_SHEET_ID"].strip(),
            rango_a1=os.environ[CERT_PREFIX + "LISTA_RANGO_A1"].strip(),
            token_provider=token_provider,
            timeout_s=timeout_s,
        ),
        linea_descriptiva=_linea_desde_path(
            Path(os.environ[CERT_PREFIX + "LINEA_PATH"].strip())
        ),
        registro_decisiones=registro,
        enlaces=_enlaces_decisiones(
            directorio_decisiones,
            config=cargar_configuracion_form_decisiones(),
        ),
        destino=GmailDestinoConfirmaciones.desde_entorno(
            token_provider=token_provider,
            timeout_s=timeout_s,
        ),
        correo_aprobador=os.environ[CERT_PREFIX + "APROBADOR"].strip(),
        directorio_salida=directorio_salida,
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
    parser.add_argument(
        "--lista-csv",
        type=Path,
        help="CSV de la lista de cierre de certificados (offline, #75). Si se pasa, cablea el despacho de `emitir_certificados`.",
    )
    parser.add_argument(
        "--linea",
        type=Path,
        help="Archivo de texto con la línea descriptiva aprobada (offline, #75).",
    )
    parser.add_argument(
        "--aprobador",
        help="Correo del rol utilitario que aprueba el lote de cierre (offline, #75).",
    )
    parser.add_argument(
        "--plan-csv",
        type=Path,
        action="append",
        default=[],
        help=(
            "Plan de pago en formato largo (offline, repetible). Habilita "
            "las variables de cuotas y medios en `generar_plantilla_actividad` "
            "para la actividad del plan."
        ),
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
            emisor = _emisor_live(
                fuente=fuente,
                token_provider=token_provider,
                timeout_s=config_ws.timeout_s,
                directorio_decisiones=directorio_decisiones,
                directorio_salida=args.directorio,
            )
            # En live el plan de pago no llega a la interpretación: el
            # adapter de la pestaña «Plan de pagos» existe en pagos_sheets
            # pero su cableado al canal queda pendiente. Sin plan, las
            # variables de cuotas y medios están prohibidas — la plantilla
            # sale sin ofrecer un plan que el agente no vio.
            planes_pago = None
            resumen_config: dict[str, object] = {
                "workspace": config_ws.resumen_seguro(),
                "canal_form": config_form.resumen_seguro(),
                "form_decisiones": (
                    decisiones_live is not None
                ),
                "certificados": emisor is not None,
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
            generator = _GeneradorOffline(_fake_output_desde_golden())
            emisor = _emisor_offline(
                args,
                fuente=fuente,
                directorio_decisiones=directorio_decisiones,
                directorio_salida=args.directorio,
                directorio_estado=directorio_estado,
            )
            planes_pago = _planes_desde_csvs(args.plan_csv)
            resumen_config = {
                "modo_offline": True,
                "certificados": emisor is not None,
                "planes_pago": len(planes_pago),
            }
            modo = "offline_fake"

        resultados = atender_canal(
            canal,
            fuente=fuente,
            directorio_salida=args.directorio,
            generator=generator,
            destino=destino,
            emisor_certificados=emisor,
            planes_pago=planes_pago,
        )
    except ConfiguracionWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (RunnerWorkspaceError, CanalFormError) as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (FuenteSolicitudesError, GmailEnvioError, ControlPagosError) as exc:
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
