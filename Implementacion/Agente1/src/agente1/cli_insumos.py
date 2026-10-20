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
Drive configurada. Es el modo operación, así que antes de tocar la red
verifica la integridad de la versión contra el manifest (#92, ADR 0010): un
árbol alterado, o un manifest ausente o inválido, no arranca. También compara
la huella de la configuración por entorno con la de la corrida anterior y, si
cambió, la asienta y avisa al operador sin frenar el arranque (#94, ADR 0010).
La configuración sale del entorno: las
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

El armado del parser, la validación cruzada y la composición de la corrida
(`agregar_argumentos_corrida`, `validar_argumentos_corrida`,
`corrida_desde_args`) están factorizados porque el subcomando `scheduler`
(#84) dispara exactamente la misma corrida con la misma interfaz: lo que
cambia entre la corrida manual y la programada es quién la dispara, no qué
corre.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Sequence

from .canal_form import LectorValoresCsv
from .config_entorno import (
    AvisoConfiguracion,
    AvisoConfiguracionGmail,
    cargar_destinatario_aviso,
    revisar_configuracion_al_arrancar,
)
from .gmail_envio import GmailDestinoConfirmaciones
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
from .manifest_version import IntegridadError, verificar_integridad_al_arrancar
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
    ConfiguracionWorkspace,
    ConfiguracionWorkspaceError,
    cargar_configuracion_workspace,
)


def agregar_argumentos_corrida(parser: argparse.ArgumentParser) -> None:
    """Los flags de la corrida de insumos, compartidos con `scheduler`.

    Mismo contrato en los dos comandos: `--tabla` y un generador para el
    camino offline, `--live` + `--confirm-write-workspace` + modelo Ollama
    para el camino sobre D2, y `--directorio` para el registro de
    idempotencia, los borradores locales y el estado del scheduler.
    """

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


def validar_argumentos_corrida(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Las reglas cruzadas del contrato: live exige doble opt-in y modelo."""

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


def corrida_desde_args(
    args: argparse.Namespace, *, transport: TransporteHttp | None = None
) -> Callable[[], InformeCorridaInsumos]:
    """La corrida ya cableada según los flags.

    Es la composición que comparten la corrida manual y el disparo del
    scheduler (#84): mismo lector, mismo escritor, mismo mapa de despachos
    y mismo registro de idempotencia. Devuelve un callable sin argumentos
    para que el scheduler no conozca los adapters.
    """

    if args.live:
        lector, escritor, destino = _dependencias_live(
            transport=transport, directorio=args.directorio
        )
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

    def corrida() -> InformeCorridaInsumos:
        return correr_insumos(
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

    return corrida


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
    agregar_argumentos_corrida(parser)
    args = parser.parse_args(argv)
    validar_argumentos_corrida(parser, args)

    try:
        informe = corrida_desde_args(args, transport=transport)()
    except (CorridaInsumosError, ConfiguracionWorkspaceError, IntegridadError) as exc:
        return _invalida(exc.code)
    except OSError:
        return _invalida("entrada_inaccesible")
    print(json.dumps(informe_a_dict(informe), ensure_ascii=False, sort_keys=True))
    return 0


def _dependencias_live(
    *, transport: TransporteHttp | None, directorio: Path
) -> tuple[
    GoogleSheetsLectorValores,
    GoogleSheetsEscritorEstadoInsumos,
    GoogleDrivePlantillaDestinoBorradores,
]:
    """Los tres adapters reales. Único punto donde la corrida sale a la red.

    Antes de pedir el token se valida la configuración y se verifica la
    **integridad de la versión** (#92, ADR 0010): el modo operación no arranca
    si un archivo controlado no coincide con el manifest. El gate va después
    de la configuración y antes de la red, así una corrida de ensayo sin
    configuración —o la suite— no exige manifest, y ninguna corrida real sale
    a Google con el árbol alterado.

    El token se pide acá, antes de devolver nada, para que un problema de
    credenciales aparezca al preparar la corrida y no a mitad de camino, con
    parte de las filas ya procesadas (mismo criterio que `workspace_e2e`).
    """

    config = cargar_configuracion_workspace()
    insumos = cargar_configuracion_insumos()
    verificar_integridad_al_arrancar(directorio_salida=directorio)
    # El directorio de salida viaja al provider para que cada token emitido
    # deje el sha256 de la cuenta suplantada y la versión del agente en
    # `logs/cuenta-suplantada.jsonl` (ADR 0011).
    token_provider = construir_token_provider(
        timeout_s=config.timeout_s,
        directorio_auditoria=directorio,
    )
    try:
        token_provider.obtener_access_token()
    except Exception:
        raise ConfiguracionWorkspaceError("workspace_auth_unavailable") from None
    # Registro y aviso del cambio de configuración por entorno (#94, ADR 0010).
    # Va después del gate y de la credencial, porque avisar es una llamada a
    # Google y ninguna corrida real sale con el árbol alterado; no frena el
    # arranque si el aviso falla.
    _revisar_configuracion(
        config=config,
        directorio=directorio,
        transport=transport,
        token_provider=token_provider,
    )
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


def _revisar_configuracion(
    *,
    config: ConfiguracionWorkspace,
    directorio: Path,
    transport: TransporteHttp | None,
    token_provider: object,
) -> None:
    """Asienta la huella de la configuración y avisa si cambió (#94, ADR 0010).

    No frena el arranque: ni el aviso ni la escritura del registro levantan
    hacia el llamador. El fail-closed es del árbol de archivos
    (`verificar_integridad_al_arrancar`), no de la configuración por entorno.
    El aviso sale por `gmail.send`, cercado por la lista de prueba (D12).
    """

    try:
        revisar_configuracion_al_arrancar(
            config=config,
            directorio_salida=directorio,
            aviso=_aviso_configuracion(
                transport=transport, token_provider=token_provider
            ),
        )
    except OSError:
        # El registro vive en el mismo directorio que la corrida: si no se
        # puede escribir, la corrida falla igual por sus propios logs y este
        # aviso no tiene que ser lo que la detenga (ADR 0010).
        return


def _aviso_configuracion(
    *, transport: TransporteHttp | None, token_provider: object
) -> AvisoConfiguracion | None:
    """El aviso al operador, si el entorno declara su dirección.

    Sin dirección declarada —o sin la lista de prueba de Gmail— no hay aviso:
    el cambio igual queda en la auditoría como `aviso=no_configurado`. La
    dirección se valida contra la lista al entregar, como cualquier correo del
    agente, así que una dirección de fuera de la lista falla con su código.
    """

    try:
        destinatario = cargar_destinatario_aviso()
        if destinatario is None:
            return None
        # El modo y la lista salen del mismo entorno que el resto del envío:
        # sin `AGENTE1_GMAIL_MODO` esto es la lista de prueba de siempre.
        destino = GmailDestinoConfirmaciones.desde_entorno(
            token_provider=token_provider,
            transport=transport,
        )
    except ConfiguracionWorkspaceError:
        return None
    return AvisoConfiguracionGmail(destinatario=destinatario, destino=destino)


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
            f"debe ser mayor que 0 y menor o igual a {MAX_OLLAMA_TIMEOUT_S:g}"
        )
    return timeout_s
