#!/usr/bin/env python3
"""Medición del nivel verificado de los SLO desde la auditoría (#88).

Lee los registros que la operación ya deja bajo un directorio de salida —
el log del scheduler (#84), los logs de generación, el registro de
atendidos del canal de pedidos, el de decisiones del segundo Form, el de
lotes y el registro durable de confirmaciones— y calcula los cinco
indicadores de la resolución #65 sobre un rango de fechas:

- disponibilidad: corridas programadas completadas a tiempo / corridas
  programadas de la agenda;
- tiempo de atención: p95 del Form de pedido al aviso;
- latencia por pieza: p95 de `latencia_s` por tipo (objetivo pendiente
  de #50/#51, se declara así);
- aprobación → envío: p95 de la doble aprobación al envío dentro de la
  ventana, con `ENVIO_INDETERMINADO` como incidente;
- integridad del gate: toda pieza en validación humana con gate aprobado.

El script **no mide contenido ni inventa números**: donde la muestra no
alcanza `muestra_minima` declara `muestra insuficiente (n=...)` y donde
falta una fuente declara el hueco —la marca temporal del Form de pedido,
por ejemplo, sólo entra al registro como hash, así que la medición de
tiempo de atención pide el CSV de respuestas exportado a la fecha de
corte por `--respuestas-csv`. La agenda y la ventana se leen de
`AGENTE1_SCHEDULER_*` con `cargar_configuracion_scheduler`, igual que el
scheduler; no hay claves duplicadas.

La salida por stdout es el reporte JSON (`nivel_verificado_slo_v1`) con
rango, configuración efectiva, `n` de cada indicador, nivel medido o
declaración, objetivo y huecos. `--md` escribe además el corte en
markdown, listo para versionar en `evidencias/` con el comando exacto
que lo produjo. Nada de esto escribe en las fuentes.

Uso::

    PYTHONPATH=src python scripts/medir_nivel_slo.py \
      --directorio salida/insumos-d2 \
      --desde 2026-10-12 --hasta 2026-10-16 \
      --respuestas-csv respuestas-form.csv \
      --md evidencias/nivel-verificado-slo-2026-10-16.md
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from agente1.medicion_slo import (
    MUESTRA_MINIMA_DEFAULT,
    FuentesAuditoria,
    medir_nivel_slo,
    render_markdown,
)
from agente1.scheduler import (
    ConfiguracionSchedulerError,
    cargar_configuracion_scheduler,
)


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"fecha inválida: {texto!r} (esperado AAAA-MM-DD)"
        ) from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Mide el nivel verificado de los SLO (#65) sobre los "
            "registros de auditoría de un directorio de salida. "
            "Configuración de agenda por AGENTE1_SCHEDULER_*."
        )
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        required=True,
        help="directorio de salida de la operación (contiene logs/ y "
        "borradores/)",
    )
    parser.add_argument(
        "--desde", type=_fecha, required=True, help="fecha inicial AAAA-MM-DD"
    )
    parser.add_argument(
        "--hasta", type=_fecha, required=True, help="fecha final AAAA-MM-DD"
    )
    parser.add_argument(
        "--ahora",
        default=None,
        help="instante de corte ISO-8601 (default: ahora). Los ticks y "
        "eventos posteriores al corte no entran a las muestras; el flag "
        "existe para reproducir un corte.",
    )
    parser.add_argument(
        "--respuestas-csv",
        type=Path,
        default=None,
        help="CSV de respuestas del Form de pedidos exportado a la fecha "
        "de corte (marca temporal, correo, pedido). Sin él el indicador "
        "de tiempo de atención se declara sin_fuente.",
    )
    parser.add_argument(
        "--estado-canal",
        type=Path,
        default=None,
        help="directorio del registro de atendidos del canal "
        "(default: <directorio>/estado-canal-form)",
    )
    parser.add_argument(
        "--estado-decisiones",
        type=Path,
        default=None,
        help="directorio del registro de decisiones del segundo Form "
        "(default: <directorio>/estado-decisiones)",
    )
    parser.add_argument(
        "--registro-confirmaciones",
        type=Path,
        default=None,
        help="directorio del registro durable de envíos (default: "
        "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES si está declarada, "
        "sino <directorio>/registro-confirmaciones)",
    )
    parser.add_argument(
        "--muestra-minima",
        type=int,
        default=MUESTRA_MINIMA_DEFAULT,
        help="observaciones mínimas para publicar un nivel "
        f"(default: {MUESTRA_MINIMA_DEFAULT})",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=None,
        help="escribe la evidencia en markdown en esta ruta, con el "
        "comando que la produjo",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.hasta < args.desde:
        parser.error("--hasta no puede ser anterior a --desde")
    if args.muestra_minima <= 0:
        parser.error("--muestra-minima tiene que ser positiva")

    try:
        config = cargar_configuracion_scheduler()
    except ConfiguracionSchedulerError as exc:
        parser.exit(2, f"error de configuración del scheduler: {exc.code}\n")

    if args.ahora is None:
        corte = datetime.now(timezone.utc)
    else:
        try:
            corte = datetime.fromisoformat(args.ahora)
        except ValueError:
            parser.error("--ahora inválido (esperado ISO-8601)")
        if corte.tzinfo is None:
            corte = corte.replace(tzinfo=timezone.utc)

    registro = (
        args.registro_confirmaciones
        or config.registro_confirmaciones
        or (args.directorio / "registro-confirmaciones")
    )
    fuentes = FuentesAuditoria(
        directorio=args.directorio,
        estado_canal=args.estado_canal
        or (args.directorio / "estado-canal-form"),
        estado_decisiones=args.estado_decisiones
        or (args.directorio / "estado-decisiones"),
        registro_confirmaciones=registro,
        respuestas_csv=args.respuestas_csv,
    )

    reporte = medir_nivel_slo(
        fuentes=fuentes,
        desde=args.desde,
        hasta=args.hasta,
        config=config,
        corte=corte,
        muestra_minima=args.muestra_minima,
    )
    reporte["comando"] = " ".join(
        shlex.quote(parte) for parte in (["medir_nivel_slo.py"] + (argv or sys.argv[1:]))
    )

    print(json.dumps(reporte, ensure_ascii=False, indent=2, sort_keys=True))

    if args.md is not None:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(
            render_markdown(reporte, comando=reporte["comando"]),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
