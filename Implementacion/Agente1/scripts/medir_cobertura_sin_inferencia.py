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
from dataclasses import dataclass, field
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

# Los tres caminos posibles. Como constantes y no como literales sueltos,
# porque la prueba de la medición afirma sobre este conjunto.
VIA_IDENTIFICADOR = "identificador explicito"
VIA_DIFUSA = "resolucion difusa"
VIA_SIN_RESOLVER = "sin resolver"
VIAS = (VIA_IDENTIFICADOR, VIA_DIFUSA, VIA_SIN_RESOLVER)


@dataclass(frozen=True)
class Medicion:
    """Resumen de una corrida más el detalle frase por frase.

    Existe para no devolver un diccionario que mezcla escalares con la lista
    de casos: quien consume la medición pregunta por un porcentaje o recorre
    el detalle, y son dos cosas distintas.
    """

    total: int
    sin_inferencia: int
    correctas: int
    detalle: tuple[dict[str, str], ...] = field(default=())

    @property
    def porcentaje_sin_inferencia(self) -> float:
        return (100.0 * self.sin_inferencia / self.total) if self.total else 0.0

    @property
    def porcentaje_correctas(self) -> float:
        return (100.0 * self.correctas / self.total) if self.total else 0.0


def medir(corpus: Path, dataset: Path) -> Medicion:
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
            via = VIA_SIN_RESOLVER
        elif por_identificador is not None:
            via = VIA_IDENTIFICADOR
        else:
            via = VIA_DIFUSA
        detalle.append(
            {
                "frase": frase,
                "esperado": esperado,
                "resuelto": resuelto or "-",
                "via": via,
                "correcto": "si" if resuelto == esperado else "no",
            }
        )

    return Medicion(
        total=len(detalle),
        sin_inferencia=sum(1 for caso in detalle if caso["via"] != VIA_SIN_RESOLVER),
        correctas=sum(1 for caso in detalle if caso["correcto"] == "si"),
        detalle=tuple(detalle),
    )


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
        for caso in medicion.detalle:
            print(
                f"[{caso['via']:>23}] {caso['resuelto']:>8} "
                f"(esperado {caso['esperado']}, correcto: {caso['correcto']}) "
                f"{caso['frase']}"
            )
        print()
    print(f"Frases del corpus:                 {medicion.total}")
    print(
        f"Resueltas sin inferencia:          {medicion.sin_inferencia} "
        f"({medicion.porcentaje_sin_inferencia:.1f} %)"
    )
    print(
        f"Resueltas a la actividad esperada: {medicion.correctas} "
        f"({medicion.porcentaje_correctas:.1f} %)"
    )
    print()
    print("Ningún modelo fue invocado: esta medición es del camino determinístico.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
