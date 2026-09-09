#!/usr/bin/env python3
"""Runner del canal de interacción sobre el adapter de planilla offline (#24).

Atiende, una vez, los pedidos pendientes de `<directorio>/pedidos.csv` y
escribe la respuesta de cada uno en `<directorio>/respuestas.csv`. Es el
runner que hace posible la prueba guiada documentada en
`evidencias/recorrido-prueba-guiada-canal-planilla.md`: no abre red, no pide
credenciales y no depende de un modelo instalado.

Usa el generador fake determinista con el contenido ya validado como golden
de `SYN-001` (`golden/SYN-001.md`, el mismo que usa `scripts/smoke.sh`). Por
eso la prueba guiada pide un pedido sobre esa actividad puntual: HU-013 en
este incremento reconoce sólo un identificador explícito en la prosa
(la búsqueda difusa por título es #23, todavía no implementada), y el
generador fake sólo produce contenido que supera el gate de hechos para esa
fila. No es una limitación del canal ni del adapter: es el alcance vigente
del núcleo de interpretación.

Este script no corre en un loop continuo a propósito: cada corrida es una
atención puntual, para que quien hace la demo controle explícitamente cuándo
se procesa la planilla. Volver a invocarlo sobre el mismo directorio atiende
sólo lo que siga pendiente.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agente1.canal import atender_canal
from agente1.canal_planilla import CanalPlanillaOffline
from agente1.destinos import BORRADOR_MARKER
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.procesamiento import FakeGenerator


ROOT = Path(__file__).resolve().parents[1]
DATASET_DEFAULT = ROOT / "data" / "actividades_sinteticas.csv"
GOLDEN_SYN_001 = ROOT / "golden" / "SYN-001.md"


def _fake_output_desde_golden() -> str:
    """Contenido fake ya validado como golden para `SYN-001`.

    Se lee del golden en lugar de duplicar el texto acá, para que este runner
    nunca quede desalineado con el contrato de HU-010 si el golden cambia.
    """

    documento = GOLDEN_SYN_001.read_text(encoding="utf-8")
    return documento.removeprefix(BORRADOR_MARKER).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directorio",
        required=True,
        type=Path,
        help="Carpeta compartida con pedidos.csv y (se crea si no existe) respuestas.csv.",
    )
    parser.add_argument(
        "--csv",
        default=DATASET_DEFAULT,
        type=Path,
        help="Dataset de actividades contra el que se resuelve cada pedido.",
    )
    args = parser.parse_args(argv)

    canal = CanalPlanillaOffline(args.directorio)
    fuente = CsvFuenteSolicitudes(args.csv)
    generator = FakeGenerator(_fake_output_desde_golden())

    resultados = atender_canal(
        canal,
        fuente=fuente,
        directorio_salida=args.directorio,
        generator=generator,
    )

    for resultado in resultados:
        detalle = f" — {resultado.error}" if resultado.error else ""
        print(f"[{resultado.correlation_id}] {resultado.estado}{detalle}")
    print(f"Pedidos atendidos en esta corrida: {len(resultados)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
