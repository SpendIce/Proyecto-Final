"""Reproduce `DEF-A1-014` y muestra el efecto del arreglo, actividad por actividad.

Corre las tres actividades completas del dataset sintético contra las dos
plantillas —la v2 que producía el rechazo y la v3 vigente— y muestra la última
línea del bloque `DATOS DE LA ACTIVIDAD`, que es donde se ve la causa.

Necesita un Ollama local ya iniciado con el modelo descargado.

La comparación es el punto: el gate de estructura no cambió entre una corrida y
la otra. Lo que cambió es que la plantilla dejó de mostrarle al modelo una línea
`Lugar:` que después le pedía omitir.
"""

from __future__ import annotations

import argparse
import csv
import sys
from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import OllamaGenerator  # noqa: E402
from agente1.procesamiento import (  # noqa: E402
    PATRON_BORRADOR,
    PROMPT_VERSION,
    _construir_prompt,
    _validar_salida,
)

ACTIVIDADES = ("SYN-001", "SYN-003", "SYN-005")


def _prompt_v2(fila: dict[str, str]) -> str:
    """La plantilla anterior, sin ninguna decisión por caso."""

    plantilla = (
        files("agente1").joinpath("prompts", "gacetilla_v2.txt").read_text(encoding="utf-8")
    )
    datos = "\n".join(f"{campo}: {valor}" for campo, valor in fila.items())
    return plantilla.replace("{datos_fuente}", datos)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--intentos", type=int, default=2)
    args = parser.parse_args()

    filas = {
        registro["id_solicitud"]: registro
        for registro in csv.DictReader(
            (ROOT / "data" / "actividades_sinteticas.csv").read_text(
                encoding="utf-8"
            ).splitlines()
        )
    }
    generador = OllamaGenerator(modelo=args.modelo, timeout_s=120)

    for etiqueta, construir in (
        ("gacetilla_v2 (antes)", _prompt_v2),
        (f"{PROMPT_VERSION} (vigente)", _construir_prompt),
    ):
        print(f"=== {etiqueta}")
        for intento in range(1, args.intentos + 1):
            for identificador in ACTIVIDADES:
                fila = filas[identificador]
                salida = generador.generar(construir(fila)).strip()
                errores = _validar_salida(salida, fila)
                match = PATRON_BORRADOR.fullmatch(salida)
                ultima = (
                    match.group("datos").strip().splitlines()[-1]
                    if match
                    else "(sin estructura)"
                )
                print(
                    f"  intento={intento} {identificador} "
                    f"lugar_fuente={fila['lugar']!r:18s} "
                    f"errores={errores} ultima_linea_datos={ultima!r}"
                )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
