"""Reproduce `DEF-A1-014` y muestra el efecto del arreglo, actividad por actividad.

Corre las tres actividades completas del dataset sintético con la plantilla
vigente y, para comparar, con la plantilla `gacetilla_v2` que producía el
rechazo. Muestra la última línea del bloque `DATOS DE LA ACTIVIDAD`, que es
donde se ve la causa: v2 emite `Lugar:` sin valor para las filas sin lugar, y
el gate de estructura lo rechaza.

Necesita un Ollama local ya iniciado con el modelo descargado.

El lado vigente pasa por el pipeline público, así que sus rechazos son los que
registra la auditoría de verdad. El lado histórico arma el prompt viejo y llama
al generador directo, porque la API pública —correctamente— ya no ofrece manera
de pedir esa plantilla.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import OllamaGenerator, procesar_fila_csv  # noqa: E402

ACTIVIDADES = ("SYN-001", "SYN-003", "SYN-005")
# Sólo para mostrar qué escribió el modelo; el veredicto lo da el pipeline.
BLOQUE_DATOS = re.compile(
    r"## DATOS DE LA ACTIVIDAD\n(?P<datos>.+?)\n\n", flags=re.DOTALL
)


def _ultima_linea_de_datos(texto: str) -> str:
    encontrado = BLOQUE_DATOS.search(texto)
    if encontrado is None:
        return "(sin bloque de datos)"
    return encontrado.group("datos").strip().splitlines()[-1]


def _corrida_vigente(csv_path: Path, generador, intento: int) -> None:
    for identificador in ACTIVIDADES:
        with TemporaryDirectory() as temporal:
            resultado = procesar_fila_csv(
                csv_path=csv_path,
                id_solicitud=identificador,
                directorio_salida=Path(temporal),
                generator=generador,
            )
            registro = json.loads(
                Path(resultado.log_path).read_text(encoding="utf-8").strip().splitlines()[-1]
            )
            ultima = (
                _ultima_linea_de_datos(
                    Path(resultado.borrador_path).read_text(encoding="utf-8")
                )
                if resultado.borrador_path
                else "(sin borrador)"
            )
        print(
            f"  intento={intento} {identificador} estado={registro['estado']:22s} "
            f"errores={registro.get('validation_errors', [])} "
            f"ultima_linea_datos={ultima!r}"
        )


def _corrida_historica(filas: dict[str, dict[str, str]], generador, intento: int) -> None:
    plantilla = (
        files("agente1").joinpath("prompts", "gacetilla_v2.txt").read_text(encoding="utf-8")
    )
    for identificador in ACTIVIDADES:
        fila = filas[identificador]
        datos = "\n".join(f"{campo}: {valor}" for campo, valor in fila.items())
        salida = generador.generar(plantilla.replace("{datos_fuente}", datos))
        print(
            f"  intento={intento} {identificador} lugar_fuente={fila['lugar']!r:18s} "
            f"ultima_linea_datos={_ultima_linea_de_datos(salida.strip() + chr(10) * 2)!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--intentos", type=int, default=2)
    args = parser.parse_args()

    csv_path = ROOT / "data" / "actividades_sinteticas.csv"
    filas = {
        registro["id_solicitud"]: registro
        for registro in csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines())
    }
    generador = OllamaGenerator(modelo=args.modelo, timeout_s=120)

    print("=== gacetilla_v2 (antes): sólo la salida cruda del modelo")
    for intento in range(1, args.intentos + 1):
        _corrida_historica(filas, generador, intento)

    print()
    print("=== plantilla vigente: pipeline completo, con el veredicto del gate")
    for intento in range(1, args.intentos + 1):
        _corrida_vigente(csv_path, generador, intento)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
