#!/usr/bin/env python3
"""Mide un modelo local en los usos del Agente 1 que #50 no cubrió (#51).

#50 midió HU-010 y HU-011 con `medir_capacidad_hu011.py`. Acá se miden, con
el mismo criterio —la pieza pasa o no pasa su gate— y sobre el host de la
demo, los otros tres lugares donde el agente llama al modelo:

1. **HU-014, línea descriptiva** del certificado (`generar_linea_descriptiva`).
2. **HU-012, plantilla de actividad** para los correos (`procesar_plantilla_actividad`),
   con y sin plan de pagos. Las filas que el gate de entrada frena antes del
   modelo (`INCOMPLETA`) no cuentan para la conformidad y se informan aparte.
3. **Canal, fallback de interpretación** (`_interpretar_con_modelo`) sobre
   `frases_ambiguas_fallback.csv`: pasa sólo si el JSON es válido, la intención
   es `generar_gacetilla` y los términos llevan a la actividad esperada por la
   misma resolución determinística del canal.

No publica, no envía, no usa Workspace ni datos reales. Los borradores quedan
en `--salida` para revisión humana; el resumen no lleva texto generado.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.interpretacion import (  # noqa: E402
    _buscar_actividad_con_terminos,
    _interpretar_con_modelo,
)
from agente1.linea_descriptiva import generar_linea_descriptiva  # noqa: E402
from agente1.ollama import (  # noqa: E402
    DEFAULT_OLLAMA_NUM_PREDICT,
    DEFAULT_OLLAMA_TIMEOUT_S,
    OllamaGenerator,
)
from agente1.pagos import cargar_plan_pagos_csv  # noqa: E402
from agente1.plantillas_actividad import procesar_plantilla_actividad  # noqa: E402

DATA = ROOT / "data"
CSV_SINTETICAS = DATA / "actividades_sinteticas.csv"
CSV_NBLM = DATA / "actividades_notebooklm_n2_sinteticas.csv"
PLAN_NBLM = DATA / "plan_pagos_notebooklm_n2.csv"
FRASES = DATA / "frases_ambiguas_fallback.csv"
ESTADO_OK = "PENDIENTE_VALIDACION"


def _filas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def _percentil(valores: list[float], q: float) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, max(0, round(q * (len(ordenados) - 1))))
    return round(ordenados[indice], 2)


def _resumen(todos: list[dict[str, object]]) -> dict[str, object]:
    # Una fila que el gate de entrada frena (`INCOMPLETA`) nunca llega al
    # modelo: no cuenta para la conformidad del modelo, se informa aparte.
    casos = [c for c in todos if c.get("estado") != "INCOMPLETA"]
    latencias = [float(c["latencia_s"]) for c in casos]
    errores: dict[str, int] = {}
    for caso in casos:
        if not caso["ok"]:
            clave = str(caso.get("error") or "sin_detalle")
            errores[clave] = errores.get(clave, 0) + 1
    return {
        "n": len(casos),
        "conformes": sum(1 for c in casos if c["ok"]),
        "p50_s": _percentil(latencias, 0.5),
        "p95_s": _percentil(latencias, 0.95),
        "max_s": round(max(latencias), 2) if latencias else None,
        "media_s": round(statistics.fmean(latencias), 2) if latencias else None,
        "errores": errores,
        "excluidas_entrada": len(todos) - len(casos),
    }


def _medir_hu014(gen, salida: Path, ciclos: int) -> list[dict[str, object]]:
    filas = _filas(CSV_SINTETICAS) + _filas(CSV_NBLM)
    casos = []
    for ciclo in range(ciclos):
        for fila in filas:
            inicio = time.perf_counter()
            resultado = generar_linea_descriptiva(
                fila=fila, directorio_salida=salida / "hu014", generator=gen
            )
            casos.append(
                {
                    "hu": "HU-014",
                    "ciclo": ciclo,
                    "caso": fila["id_actividad"],
                    "ok": resultado.estado == ESTADO_OK,
                    "estado": resultado.estado,
                    "error": resultado.error,
                    "latencia_s": round(time.perf_counter() - inicio, 3),
                }
            )
    return casos


def _medir_hu012(gen, salida: Path, ciclos: int) -> list[dict[str, object]]:
    plan = cargar_plan_pagos_csv(PLAN_NBLM)
    actividades = [(CSV_SINTETICAS, f["id_actividad"], None) for f in _filas(CSV_SINTETICAS)]
    actividades += [(CSV_NBLM, f["id_actividad"], plan) for f in _filas(CSV_NBLM)]
    casos = []
    for ciclo in range(ciclos):
        for csv_path, id_actividad, plan_actividad in actividades:
            inicio = time.perf_counter()
            resultado = procesar_plantilla_actividad(
                fuente=CsvFuenteSolicitudes(csv_path),
                id_solicitud=id_actividad,
                directorio_salida=salida / "hu012" / f"ciclo-{ciclo}",
                generator=gen,
                planes_pago=(
                    {id_actividad: plan_actividad} if plan_actividad is not None else None
                ),
            )
            casos.append(
                {
                    "hu": "HU-012",
                    "ciclo": ciclo,
                    "caso": id_actividad,
                    "con_plan": plan_actividad is not None,
                    "ok": resultado.estado == ESTADO_OK,
                    "estado": resultado.estado,
                    "error": resultado.error,
                    "latencia_s": round(time.perf_counter() - inicio, 3),
                }
            )
    return casos


def _medir_canal(gen, ciclos: int) -> list[dict[str, object]]:
    fuente = CsvFuenteSolicitudes(CSV_SINTETICAS)
    frases = _filas(FRASES)
    casos = []
    for ciclo in range(ciclos):
        for indice, fila in enumerate(frases):
            inicio = time.perf_counter()
            terminos = _interpretar_con_modelo(fila["frase"], gen)
            latencia = round(time.perf_counter() - inicio, 3)
            if terminos is None:
                ok, error, resuelta = False, "salida_invalida", None
            elif terminos.intencion != "generar_gacetilla":
                ok, error, resuelta = False, f"intencion:{terminos.intencion}", None
            else:
                resuelta = _buscar_actividad_con_terminos(
                    fila["frase"], terminos.terminos, fuente
                )
                ok = resuelta == fila["id_esperado"]
                error = None if ok else "actividad_no_resuelta"
            casos.append(
                {
                    "hu": "canal",
                    "ciclo": ciclo,
                    "caso": f"frase-{indice + 1}",
                    "esperado": fila["id_esperado"],
                    "resuelta": resuelta,
                    "ok": ok,
                    "error": error,
                    "latencia_s": latencia,
                }
            )
    return casos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=DEFAULT_OLLAMA_TIMEOUT_S)
    parser.add_argument("--num-predict", type=int, default=DEFAULT_OLLAMA_NUM_PREDICT)
    parser.add_argument("--ciclos", type=int, default=2)
    parser.add_argument("--sin-thinking", action="store_true")
    parser.add_argument(
        "--solo", choices=("hu014", "hu012", "canal"), action="append"
    )
    parser.add_argument("--confirm-live-llm", action="store_true", required=True)
    args = parser.parse_args()

    gen = OllamaGenerator(
        modelo=args.modelo,
        base_url=args.base_url,
        timeout_s=args.timeout,
        num_predict=args.num_predict,
        think=False if args.sin_thinking else None,
    )
    salida = args.salida
    salida.mkdir(parents=True, exist_ok=True)
    partes = args.solo or ["hu014", "hu012", "canal"]
    casos: list[dict[str, object]] = []
    resumen: dict[str, object] = {
        "modelo": args.modelo,
        "think": gen.think,
        "timeout_s": args.timeout,
        "num_predict": args.num_predict,
        "ciclos": args.ciclos,
    }
    for parte in partes:
        if parte == "hu014":
            nuevos = _medir_hu014(gen, salida, args.ciclos)
        elif parte == "hu012":
            nuevos = _medir_hu012(gen, salida, args.ciclos)
        else:
            nuevos = _medir_canal(gen, args.ciclos)
        casos.extend(nuevos)
        resumen[parte] = _resumen(nuevos)
        print(json.dumps({parte: resumen[parte]}, ensure_ascii=False), flush=True)

    with (salida / "casos.jsonl").open("w", encoding="utf-8") as archivo:
        for caso in casos:
            archivo.write(json.dumps(caso, ensure_ascii=False, sort_keys=True) + "\n")
    (salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
