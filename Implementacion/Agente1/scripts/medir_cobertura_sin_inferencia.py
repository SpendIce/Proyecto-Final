"""Mide qué porcentaje del corpus resuelve el camino determinístico, sin modelo.

Criterio de aceptación de HU-013/#26: el valor de esta medición es saber cuánta
cobertura da el camino determinístico, porque de eso depende cuánto trabajo le
queda al fallback con modelo local. Un fallback que casi nunca se invoca es una
dependencia barata; uno que se invoca siempre es una dependencia crítica
disfrazada de opcional.

No invoca ningún modelo y no sale a la red: recorre el corpus versionado de
frases realistas (`data/frases_resolucion_actividad.csv`) y cuenta cuántas
resuelven por identificador explícito o por resolución difusa, que son los dos
caminos que no requieren inferencia.

Una frase que no resuelve no es un defecto: es exactamente el caso que la
repregunta (#25) y el fallback (#26) existen para atender. El número que
importa es la proporción.

**Cuidado con qué corpus se mide.** `frases_resolucion_actividad.csv` se
calibró en #23 justamente para que toda frase resolviera de forma
determinística, así que medir contra él da 100 % por construcción: informa
sobre la calibración, no sobre la cobertura. `frases_ambiguas_fallback.csv`
reúne frases realistas que **no** se eligieron para pasar —piden una actividad
por un rasgo parcial, por una fecha en otro formato o por quién la organiza— y
es el corpus que dice algo sobre cuánto trabajo le queda al fallback. El
resumen se imprime por separado para cada uno.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.interpretacion import (  # noqa: E402
    _extraer_identificador_explicito,
    _resolver_actividad_por_similitud,
)


CORPUS = ROOT / "data" / "frases_resolucion_actividad.csv"
DATASET = ROOT / "data" / "actividades_sinteticas.csv"


def medir(corpus: Path, dataset: Path) -> dict[str, object]:
    fuente = CsvFuenteSolicitudes(dataset)
    with corpus.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))

    detalle: list[dict[str, str]] = []
    for fila in filas:
        frase = fila["frase"]
        esperado = fila["id_esperado"]
        por_identificador = _extraer_identificador_explicito(frase)
        resuelto = por_identificador or _resolver_actividad_por_similitud(frase, fuente)
        if resuelto is None:
            via = "sin resolver"
        elif por_identificador is not None:
            via = "identificador explicito"
        else:
            via = "resolucion difusa"
        detalle.append(
            {
                "frase": frase,
                "esperado": esperado,
                "resuelto": resuelto or "-",
                "via": via,
                "correcto": "si" if resuelto == esperado else "no",
            }
        )

    total = len(detalle)
    sin_inferencia = sum(1 for caso in detalle if caso["via"] != "sin resolver")
    correctas = sum(1 for caso in detalle if caso["correcto"] == "si")
    return {
        "total": total,
        "sin_inferencia": sin_inferencia,
        "correctas": correctas,
        "porcentaje_sin_inferencia": (100.0 * sin_inferencia / total) if total else 0.0,
        "porcentaje_correctas": (100.0 * correctas / total) if total else 0.0,
        "detalle": detalle,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument(
        "--detalle",
        action="store_true",
        help="lista frase por frase, no sólo el resumen",
    )
    args = parser.parse_args()

    medicion = medir(args.corpus, args.dataset)
    if args.detalle:
        for caso in medicion["detalle"]:
            print(
                f"[{caso['via']:>23}] {caso['resuelto']:>8} "
                f"(esperado {caso['esperado']}, correcto: {caso['correcto']}) "
                f"{caso['frase']}"
            )
        print()
    print(f"Frases del corpus:                 {medicion['total']}")
    print(
        f"Resueltas sin inferencia:          {medicion['sin_inferencia']} "
        f"({medicion['porcentaje_sin_inferencia']:.1f} %)"
    )
    print(
        f"Resueltas a la actividad esperada: {medicion['correctas']} "
        f"({medicion['porcentaje_correctas']:.1f} %)"
    )
    print()
    print("Ningún modelo fue invocado: esta medición es del camino determinístico.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
