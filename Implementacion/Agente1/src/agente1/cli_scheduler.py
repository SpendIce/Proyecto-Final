"""`agente1 scheduler`: el disparo de las corridas programadas (#84).

El mismo proceso sirve a los dos mecanismos de disparo que el runbook
documenta (`Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md`):

- `agente1 scheduler --una-corrida` es lo que dispara el timer
  `systemd --user`: responde al tick más reciente de la agenda, corre una
  vez y termina. `--ahora` existe para reproducir un disparo en un ensayo.
- `agente1 scheduler --loop` es el bucle con `sleep` a prueba de
  solapamiento para ensayos y hosts sin systemd.

Los flags de la corrida son exactamente los de `insumos-agentes`
(`agregar_argumentos_corrida`), con el mismo contrato: offline exige
`--tabla` y un generador; sobre D2 exige `--live`,
`--confirm-write-workspace` y `--ollama-model`. La agenda se configura por
entorno con `AGENTE1_SCHEDULER_*` (ver `scheduler.py`).

Antes de arrancar en modo operación (`--live`, como lo invocan las unidades
`systemd/`) se verifica la integridad de la versión contra
`manifest-version.json` (#92, ADR 0010): si un archivo controlado difiere, o
si el manifest falta o es inválido, el disparo no arranca y sale con código 2
dejando el motivo en `logs/integridad-arranque.jsonl`. Los ensayos offline y
la suite no verifican: el manifest se regenera al cortar una versión, no en
cada cambio.

Cada disparo deja una línea en `logs/scheduler-corridas.jsonl` bajo
`--directorio`: `inicio_previsto`, `inicio_real`, `fin`, `resultado`
(`completada`, `falla`, `omitida_ventana`, `omitida_lock`,
`omitida_duplicada`) y el bloque `mantenimiento` cuando el slot diario
corrió. Nunca lleva payload ni contenido generado; es la entrada que #88
usa para medir la disponibilidad dentro de la ventana.

El mantenimiento diario corre en la primera corrida en ventana del día:
`purga` (#87, si `AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES` apunta al
registro durable de HU-012) y `respaldo` (#86, si el entorno declara una
carpeta de respaldo con `AGENTE1_RESPALDO_*`), en ese orden para que
ningún respaldo conserve lo que la retención ya venció — si la purga del
día falló, el respaldo del día también falla a propósito y ambos se
reintentan en el tick siguiente. Sin carpeta configurada el respaldo se
asienta `pendiente`, para que el hueco quede a la vista. El disparo
automático nunca envía ni publica: sólo genera borradores y la validación
humana queda intacta.

Códigos de salida: `0` cuando el disparo quedó asentado (`completada` u
`omitida_*`, que son resultados esperados de la agenda); `2` cuando la
corrida falló, la configuración o el log son inválidos, o el lock es
inaccesible, para que systemd y el operador lo distingan.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cli_insumos import (
    agregar_argumentos_corrida,
    corrida_desde_args,
    informe_a_dict,
    validar_argumentos_corrida,
)
from .google_workspace import TransporteHttp
from .manifest_version import IntegridadError
from .scheduler import (
    ConfiguracionScheduler,
    ConfiguracionSchedulerError,
    PasoDiario,
    SchedulerError,
    bucle,
    cargar_configuracion_scheduler,
    disparar,
)
from .workspace_config import ConfiguracionWorkspaceError

# El respaldo diario (#86) existe desde este issue: corre cuando el
# entorno declara una carpeta con `AGENTE1_RESPALDO_*` y queda declarado
# `pendiente` cuando no — el hueco sigue a la vista como antes.
_PREFIJO_RESPALDO = "AGENTE1_RESPALDO_"


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: TransporteHttp | None = None,
    environ: Mapping[str, str] | None = None,
    clock: Callable[[], datetime] | None = None,
    dormir: Callable[[float], None] | None = None,
) -> int:
    """Un disparo o el bucle del scheduler; devuelve el código de salida.

    `clock` y `dormir` son las costuras del bucle para los ensayos: con
    ellas se recorre la agenda entera sin esperar el tiempo real.
    """

    parser = argparse.ArgumentParser(
        prog="agente1 scheduler",
        description=(
            "Disparo de las corridas programadas: responde a un tick de la "
            "agenda (--una-corrida) o espera y repite (--loop), dentro de "
            "la ventana de operación y con lock contra solapamientos."
        ),
    )
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument(
        "--una-corrida",
        action="store_true",
        help="Corre el tick más reciente de la agenda y termina (lo dispara el timer).",
    )
    modo.add_argument(
        "--loop",
        action="store_true",
        help="Bucle: espera al próximo tick, corre y repite (ensayos, hosts sin systemd).",
    )
    parser.add_argument(
        "--ahora",
        metavar="ISO8601",
        help=(
            "Instante al que responde el disparo (por defecto el actual); "
            "sólo aplica con --una-corrida y existe para ensayos."
        ),
    )
    parser.add_argument(
        "--max-disparos",
        type=int,
        metavar="N",
        help="Corta --loop tras N disparos (ensayos); sin valor corre indefinidamente.",
    )
    agregar_argumentos_corrida(parser)
    args = parser.parse_args(argv)

    if args.ahora is not None and not args.una_corrida:
        parser.error("--ahora sólo aplica con --una-corrida")
    if args.max_disparos is not None:
        if not args.loop:
            parser.error("--max-disparos sólo aplica con --loop")
        if args.max_disparos < 1:
            parser.error("--max-disparos debe ser mayor que cero")
    validar_argumentos_corrida(parser, args)

    try:
        config = cargar_configuracion_scheduler(environ)
    except ConfiguracionSchedulerError as exc:
        return _invalida(exc.code)

    try:
        corrida_informe = corrida_desde_args(args, transport=transport)
    except (ConfiguracionWorkspaceError, IntegridadError) as exc:
        return _invalida(exc.code)

    # El scheduler conoce el informe como mapping: `informe_a_dict` es la
    # misma serialización que imprime la corrida manual, y de ella el log
    # sólo republica los conteos cerrados (nunca el detalle por fila).
    def corrida() -> Mapping[str, Any]:
        return informe_a_dict(corrida_informe())

    pasos_diarios, pasos_declarados = _pasos_diarios(
        config, args.directorio, environ
    )
    reloj = clock or (lambda: datetime.now(timezone.utc))
    ahora = reloj()
    if args.ahora:
        try:
            ahora = _parsear_ahora(args.ahora)
        except ConfiguracionSchedulerError as exc:
            return _invalida(exc.code)
    try:
        if args.loop:
            return bucle(
                corrida=corrida,
                config=config,
                directorio=args.directorio,
                pasos_diarios=pasos_diarios,
                pasos_declarados=pasos_declarados,
                dormir=dormir or time.sleep,
                clock=reloj,
                max_disparos=args.max_disparos,
            )
        entrada = disparar(
            ahora=ahora,
            corrida=corrida,
            config=config,
            directorio=args.directorio,
            pasos_diarios=pasos_diarios,
            pasos_declarados=pasos_declarados,
            clock=reloj,
        )
    except SchedulerError as exc:
        return _invalida(exc.code)

    print(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
    return 0 if entrada["resultado"] != "falla" else 2


def _pasos_diarios(
    config: ConfiguracionScheduler,
    directorio_salida: Path,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[PasoDiario], tuple[str, ...]]:
    """Los pasos del slot diario y los declarados que aún no corren.

    `purga` (#87) existe cuando hay registro durable declarado y el script
    está en el checkout; `respaldo` (#86) existe cuando el entorno declara
    una carpeta con `AGENTE1_RESPALDO_*` y el script está — los modos y el
    doble opt-in los resuelve el propio script contra ese entorno. Sin
    carpeta configurada el paso viaja en `pasos_declarados` y se asienta
    `pendiente` cada día, para que el hueco quede a la vista.

    Los dos corren como procesos aparte, en este orden: el respaldo nunca
    corre antes que la purga del día, y si la purga falló el respaldo
    falla a propósito — ningún artefacto puede conservar texto que la
    retención ya venció (ADR 0009).
    """

    env = os.environ if environ is None else environ
    pasos: list[PasoDiario] = []
    # La cadena purga → respaldo viaja por este flag: lo escribe el paso
    # de la purga en cada intento y lo lee el del respaldo antes de subir
    # nada. Sin purga declarada no hay nada que esperar.
    purga_completa = {"ok": True}

    if config.registro_confirmaciones is not None:
        script_purga = (
            config.repo
            / "Implementacion"
            / "Agente1"
            / "scripts"
            / "purgar_registro.py"
        )
        if script_purga.is_file():

            def correr_purga() -> None:
                # Proceso aparte, igual que lo haría una unidad propia: la
                # purga audita en su propio log
                # (`logs/confirmaciones-hu012.jsonl` bajo el directorio de
                # salida) y el scheduler sólo conoce el código.
                resultado = subprocess.run(
                    [
                        sys.executable,
                        str(script_purga),
                        "--registro",
                        str(config.registro_confirmaciones),
                        "--salida",
                        str(directorio_salida),
                    ],
                    cwd=config.repo,
                    env=dict(env),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                purga_completa["ok"] = resultado.returncode == 0
                if not purga_completa["ok"]:
                    raise RuntimeError("purga_registro_error")

            pasos.append(PasoDiario("purga", correr_purga))

    script_respaldo = (
        config.repo
        / "Implementacion"
        / "Agente1"
        / "scripts"
        / "respaldar_estado.py"
    )
    respaldo_configurado = script_respaldo.is_file() and any(
        clave.startswith(_PREFIJO_RESPALDO) for clave in env
    )
    if not respaldo_configurado:
        return pasos, ("respaldo",)

    def correr_respaldo() -> None:
        # Mismo patrón que la purga: subproceso con el entorno heredado
        # (ahí viven `AGENTE1_RESPALDO_*` y la credencial de Workspace) y
        # auditoría propia en `logs/respaldo-diario.jsonl`. La carpeta
        # real de Drive es un opt-in del operador; sin ella el paso corre
        # contra la carpeta fake declarada o falla con código.
        if not purga_completa["ok"]:
            raise RuntimeError("respaldo_tras_purga_fallida")
        comando = [
            sys.executable,
            str(script_respaldo),
            "--salida",
            str(directorio_salida),
        ]
        if config.registro_confirmaciones is not None:
            comando += ["--registro", str(config.registro_confirmaciones)]
        resultado = subprocess.run(
            comando,
            cwd=config.repo,
            env=dict(env),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if resultado.returncode != 0:
            raise RuntimeError("respaldo_diario_error")

    pasos.append(PasoDiario("respaldo", correr_respaldo))
    return pasos, ()


def _parsear_ahora(texto: str) -> datetime:
    try:
        ahora = datetime.fromisoformat(texto)
    except ValueError:
        raise ConfiguracionSchedulerError("scheduler_config_invalid") from None
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    return ahora


def _invalida(code: str) -> int:
    print(
        json.dumps(
            {"estado": "INVALIDA", "error": code},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2
