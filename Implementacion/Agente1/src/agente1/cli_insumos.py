"""Subcomando `insumos-agentes`: la corrida de insumos por línea de comandos.

Corrida manual del punto de entrada push del ADR 0008. Por defecto trabaja
offline: `--tabla` apunta a un CSV con la misma forma que la pestaña
`Insumos de agentes` (`LectorValoresCsv` + `EscritorEstadoCsv`), así la
corrida completa —validación, despacho, idempotencia, escritura de estado—
se ensaya sin red y sin tocar D2.

El modo en vivo se pide con `--live` **y** `--confirm-write-workspace`
juntos (doble opt-in, igual que `workspace_e2e`): lee la pestaña real por
`GoogleSheetsLectorValores`, escribe el estado de cada fila por
`GoogleSheetsEscritorEstadoInsumos` y deja los borradores en la carpeta de
Drive configurada. La configuración sale del entorno: las
`AGENTE1_WORKSPACE_*` de siempre (planilla, plantilla, carpeta, token o el
trío OAuth) más `AGENTE1_INSUMOS_RANGO_A1` con el rango `'Nombre'!A1:D<n>`
de la pestaña. En vivo el generador es obligatoriamente un modelo de Ollama:
un fake produciría borradores sintéticos dentro de recursos reales.

`--directorio` es obligatorio en ambos modos: ahí vive
`insumos-procesados.jsonl` (la idempotencia por `correlation_id`), el log
del pipeline y los borradores Markdown cuando el destino es local.

El informe es JSON con claves ordenadas por stdout: conteos cerrados y una
entrada por fila con su desenlace y los metadatos del envelope —nunca el
payload ni el contenido generado. Código de salida `0` si la corrida
produjo informe, `2` si la tabla, la configuración o el registro fallaron,
con el código cerrado en `error`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .canal_form import LectorValoresCsv
from .google_workspace import (
    GoogleDrivePlantillaDestinoBorradores,
    GoogleSheetsLectorValores,
    TransporteHttp,
)
from .insumos_corrida import (
    CorridaInsumosError,
    FlujoEventoGacetilla,
    InformeCorridaInsumos,
    RegistroInsumosArchivo,
    ResultadoFilaInsumo,
    correr_insumos,
)
from .insumos_sheets import (
    EscritorEstadoCsv,
    GoogleSheetsEscritorEstadoInsumos,
    cargar_configuracion_insumos,
)
from .ollama import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_NUM_PREDICT,
    DEFAULT_OLLAMA_TIMEOUT_S,
    MAX_OLLAMA_TIMEOUT_S,
    OllamaGenerator,
)
from .procesamiento import FakeGenerator
from .workspace_auth import construir_token_provider
from .workspace_config import (
    ConfiguracionWorkspaceError,
    cargar_configuracion_workspace,
)


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: TransporteHttp | None = None,
) -> int:
    """Corre la corrida de insumos y devuelve el código de salida del proceso.

    `transport` es la costura de los adapters de Workspace: en producción
    queda `None` y se usa HTTPS real; en las pruebas se inyecta el transporte
    falso y el modo `--live` se ejercita entero sin red.
    """

    parser = argparse.ArgumentParser(
        prog="agente1 insumos-agentes",
        description=(
            "Corrida de insumos de agentes: lee la pestaña «Insumos de "
            "agentes», valida cada fila contra agente1.insumo.v1, despacha "
            "por tipo y escribe el estado en la misma fila."
        ),
    )
    parser.add_argument(
        "--tabla",
        type=Path,
        help=(
            "CSV offline con la forma de la pestaña (encabezado "
            "insumo,cargado_por,estado,detalle). Obligatorio sin --live."
        ),
    )
    parser.add_argument(
        "--directorio",
        required=True,
        type=Path,
        help=(
            "Directorio de salida: registro de idempotencia "
            "(insumos-procesados.jsonl), logs del pipeline y borradores "
            "locales cuando el destino es Markdown."
        ),
    )
    generator_group = parser.add_mutually_exclusive_group(required=True)
    generator_group.add_argument(
        "--fake-output",
        help="Salida fija del generador determinista (sólo offline).",
    )
    generator_group.add_argument(
        "--ollama-model",
        help="Modelo de Ollama para el flujo de gacetilla (obligatorio en --live).",
    )
    parser.add_argument("--ollama-base-url", default=DEFAULT_OLLAMA_BASE_URL)
    parser.add_argument(
        "--ollama-timeout",
        default=DEFAULT_OLLAMA_TIMEOUT_S,
        type=_timeout_ollama,
        metavar="SEGUNDOS",
    )
    parser.add_argument(
        "--ollama-num-predict",
        default=DEFAULT_OLLAMA_NUM_PREDICT,
        type=int,
        metavar="TOKENS",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Lee y escribe la planilla D2 real (exige --confirm-write-workspace).",
    )
    parser.add_argument(
        "--confirm-write-workspace",
        action="store_true",
        help="Confirma que la corrida puede escribir en la planilla real.",
    )
    args = parser.parse_args(argv)

    if args.live:
        if args.tabla is not None:
            parser.error("--live no admite --tabla")
        if args.confirm_write_workspace is not True:
            parser.error("--live exige --confirm-write-workspace")
        if args.ollama_model is None:
            parser.error("--live exige --ollama-model")
    else:
        if args.confirm_write_workspace:
            parser.error("--confirm-write-workspace sólo aplica con --live")
        if args.tabla is None:
            parser.error("sin --live se exige --tabla")

    try:
        if args.live:
            lector, escritor, destino = _dependencias_live(transport=transport)
        else:
            lector = LectorValoresCsv(args.tabla)
            escritor = EscritorEstadoCsv(args.tabla)
            destino = None
        generator = (
            FakeGenerator(args.fake_output)
            if args.fake_output is not None
            else OllamaGenerator(
                modelo=args.ollama_model,
                base_url=args.ollama_base_url,
                timeout_s=args.ollama_timeout,
                num_predict=args.ollama_num_predict,
            )
        )
        informe = correr_insumos(
            lector=lector,
            escritor=escritor,
            registro=RegistroInsumosArchivo(args.directorio),
            despachos={
                "evento": FlujoEventoGacetilla(
                    generator=generator,
                    directorio_salida=args.directorio,
                    destino=destino,
                )
            },
        )
    except (CorridaInsumosError, ConfiguracionWorkspaceError) as exc:
        return _invalida(exc.code)
    except OSError:
        return _invalida("entrada_inaccesible")
    print(json.dumps(informe_a_dict(informe), ensure_ascii=False, sort_keys=True))
    return 0


def _dependencias_live(
    *, transport: TransporteHttp | None
) -> tuple[
    GoogleSheetsLectorValores,
    GoogleSheetsEscritorEstadoInsumos,
    GoogleDrivePlantillaDestinoBorradores,
]:
    """Los tres adapters reales. Único punto donde la corrida sale a la red.

    El token se pide acá, antes de devolver nada, para que un problema de
    credenciales aparezca al preparar la corrida y no a mitad de camino, con
    parte de las filas ya procesadas (mismo criterio que `workspace_e2e`).
    """

    config = cargar_configuracion_workspace()
    insumos = cargar_configuracion_insumos()
    token_provider = construir_token_provider(timeout_s=config.timeout_s)
    try:
        token_provider.obtener_access_token()
    except Exception:
        raise ConfiguracionWorkspaceError("workspace_auth_unavailable") from None
    try:
        return (
            GoogleSheetsLectorValores(
                spreadsheet_id=insumos.spreadsheet_id,
                rango_a1=insumos.rango_a1,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            ),
            GoogleSheetsEscritorEstadoInsumos(
                spreadsheet_id=insumos.spreadsheet_id,
                hoja=insumos.hoja,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            ),
            GoogleDrivePlantillaDestinoBorradores(
                plantilla_id=config.template_id,
                carpeta_id=config.folder_id,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            ),
        )
    except ValueError:
        raise ConfiguracionWorkspaceError("insumos_config_invalid") from None


def informe_a_dict(informe: InformeCorridaInsumos) -> dict[str, object]:
    """Serializa el informe: metadatos de cada fila, nunca el payload."""

    return {
        "estado": informe.estado,
        "contrato_insumos": informe.contract_version,
        "filas_leidas": informe.filas_leidas,
        "filas_nuevas": informe.filas_nuevas,
        "filas_escritas": informe.filas_escritas,
        "filas_omitidas": informe.filas_omitidas,
        "filas_bloqueadas": informe.filas_bloqueadas,
        "filas_fallidas": informe.filas_fallidas,
        "filas": [_fila_a_dict(fila) for fila in informe.filas],
    }


def _fila_a_dict(fila: ResultadoFilaInsumo) -> dict[str, object]:
    return {
        "fila": fila.fila,
        "desenlace": fila.desenlace,
        "estado": fila.estado_fila,
        "detalle": fila.detalle,
        "codigo": fila.codigo,
        "producer": fila.producer,
        "correlation_id": fila.correlation_id,
        "payload_type": fila.payload_type,
        "data_origin": fila.data_origin,
        "cargado_por": fila.cargado_por,
        "via_registro": fila.via_registro,
    }


def _invalida(code: str) -> int:
    print(
        json.dumps(
            {"estado": "INVALIDA", "error": code},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2


def _timeout_ollama(value: str) -> float:
    try:
        timeout_s = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un número") from None
    if not 0 < timeout_s <= MAX_OLLAMA_TIMEOUT_S:
        raise argparse.ArgumentTypeError(
            "debe ser mayor que 0 y menor o igual a 120"
        )
    return timeout_s
