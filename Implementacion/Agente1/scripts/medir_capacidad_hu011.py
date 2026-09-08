#!/usr/bin/env python3
"""Prueba de capacidad local de A1 contra el volumen informado por la SEU.

La SEU informó como referencia un mínimo de un reel mensual y dos publicaciones
semanales, con un promedio aproximado de doce publicaciones mensuales. Ese dato
no es un SLA ni una promesa de producción: se usa acá para responder una
pregunta acotada y verificable —¿el modelo local sostiene ese ritmo?— y para
documentar el fallback cuando no lo sostiene.

El runner mide dos cosas distintas y no las mezcla:

1. **Latencia**: cuánto tarda cada generación, separando la primera invocación
   con el modelo frío del resto en caliente.
2. **Conformidad**: cuántas de esas generaciones superan el gate. Una salida
   rechazada consume el mismo tiempo de cómputo que una aceptada, así que la
   capacidad efectiva depende de ambas.

El reel queda fuera del cálculo: A1 no genera video, audio ni guion audiovisual
(`RED-ALC-02` de la política de redes).

No publica, no envía y no usa datos reales. Toda salida exitosa conserva
`BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1 import OllamaGenerator  # noqa: E402
from agente1.fuentes import CsvFuenteSolicitudes  # noqa: E402
from agente1.ollama import DEFAULT_OLLAMA_NUM_PREDICT  # noqa: E402
from agente1.politica_redes import POLICY_VERSION  # noqa: E402
from agente1.posts import (  # noqa: E402
    CONTRATO_CREATIVO_V3,
    procesar_post_estructurado,
)
from agente1.procesamiento import procesar_fila_csv  # noqa: E402


CANALES = ("instagram", "linkedin")
ACTIVIDADES_COMPLETAS = ("SYN-001", "SYN-003", "SYN-005")

# Volumen de referencia comunicado por la SEU el 2026-08-26.
VOLUMEN_SEU = {
    "publicaciones_mensuales_promedio": 12,
    "publicaciones_semanales_minimas": 2,
    "reels_mensuales_minimos": 1,
    "piezas_por_publicacion": {
        "gacetilla": 1,
        "post_instagram": 1,
        "post_linkedin": 1,
    },
    "reel_soportado_por_a1": False,
}
JORNADA_LABORAL_S = 6 * 3600


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _percentil(valores: list[float], fraccion: float) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, int(round(fraccion * (len(ordenados) - 1))))
    return ordenados[indice]


def _resumen_latencias(valores: list[float]) -> dict[str, float | None]:
    return {
        "n": len(valores),
        "min_s": min(valores) if valores else None,
        "p50_s": _percentil(valores, 0.50),
        "p95_s": _percentil(valores, 0.95),
        "max_s": max(valores) if valores else None,
        "media_s": statistics.fmean(valores) if valores else None,
    }


def _generador(modelo: str, args, *, schema: dict[str, object] | None):
    return OllamaGenerator(
        modelo=modelo,
        base_url=args.base_url,
        timeout_s=args.timeout,
        num_predict=args.num_predict,
        format_schema=schema,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mide capacidad local de A1 contra el volumen informado por la SEU."
    )
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--num-predict", type=int, default=DEFAULT_OLLAMA_NUM_PREDICT
    )
    parser.add_argument(
        "--ciclos",
        type=int,
        default=2,
        help="Repeticiones sobre las tres actividades completas.",
    )
    parser.add_argument(
        "--incluir-gacetillas",
        action="store_true",
        help="Agrega una pasada HU-010 por actividad para medir la pieza completa.",
    )
    parser.add_argument(
        "--confirm-live-llm",
        action="store_true",
        required=True,
        help="Opt-in explícito: este runner invoca un modelo local real.",
    )
    args = parser.parse_args()

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "data" / "actividades_sinteticas.csv"
    fuente = CsvFuenteSolicitudes(dataset)
    mediciones: list[dict[str, object]] = []
    orden = 0

    for ciclo in range(args.ciclos):
        for id_solicitud in ACTIVIDADES_COMPLETAS:
            if args.incluir_gacetillas:
                orden += 1
                generator = _generador(args.modelo, args, schema=None)
                inicio = time.perf_counter()
                resultado = procesar_fila_csv(
                    csv_path=dataset,
                    id_solicitud=id_solicitud,
                    directorio_salida=salida / f"ciclo{ciclo}" / id_solicitud / "gacetilla",
                    generator=generator,
                )
                latencia = time.perf_counter() - inicio
                registro = json.loads(
                    resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
                )
                mediciones.append(
                    {
                        "orden": orden,
                        "ciclo": ciclo,
                        "pieza": "gacetilla",
                        "hu": "HU-010",
                        "id_solicitud": id_solicitud,
                        "canal": None,
                        "estado": resultado.estado,
                        "conforme": resultado.borrador_path is not None,
                        "latencia_s": round(latencia, 6),
                        "validation_errors": registro.get("validation_errors"),
                    }
                )
                print(
                    json.dumps(
                        {
                            "pieza": f"gacetilla/{id_solicitud}",
                            "estado": resultado.estado,
                            "latencia_s": round(latencia, 3),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

            for canal in CANALES:
                orden += 1
                generator = _generador(
                    args.modelo, args, schema=CONTRATO_CREATIVO_V3.schema
                )
                inicio = time.perf_counter()
                resultado = procesar_post_estructurado(
                    fuente=fuente,
                    id_solicitud=id_solicitud,
                    canal=canal,
                    directorio_salida=salida / f"ciclo{ciclo}" / id_solicitud / canal,
                    generator=generator,
                    contrato=CONTRATO_CREATIVO_V3,
                )
                latencia = time.perf_counter() - inicio
                registro = json.loads(
                    resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
                )
                mediciones.append(
                    {
                        "orden": orden,
                        "ciclo": ciclo,
                        "pieza": f"post_{canal}",
                        "hu": "HU-011",
                        "id_solicitud": id_solicitud,
                        "canal": canal,
                        "estado": resultado.estado,
                        "conforme": resultado.borrador_path is not None,
                        "latencia_s": round(latencia, 6),
                        "validation_errors": registro.get("validation_errors"),
                    }
                )
                print(
                    json.dumps(
                        {
                            "pieza": f"post_{canal}/{id_solicitud}",
                            "estado": resultado.estado,
                            "conforme": resultado.borrador_path is not None,
                            "latencia_s": round(latencia, 3),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    latencias = [float(item["latencia_s"]) for item in mediciones]
    frias = latencias[:1]
    calientes = latencias[1:]
    conformes = [item for item in mediciones if item["conforme"]]
    errores: dict[str, int] = {}
    for item in mediciones:
        for codigo in item["validation_errors"] or []:
            errores[codigo] = errores.get(codigo, 0) + 1

    piezas_por_publicacion = sum(VOLUMEN_SEU["piezas_por_publicacion"].values())
    generaciones_mensuales = (
        VOLUMEN_SEU["publicaciones_mensuales_promedio"] * piezas_por_publicacion
    )
    tasa_conformidad = len(conformes) / len(mediciones) if mediciones else 0.0
    p50 = _percentil(calientes, 0.50)
    p95 = _percentil(calientes, 0.95)
    intentos_por_pieza_conforme = (
        round(1 / tasa_conformidad, 3) if tasa_conformidad else None
    )

    proyeccion = {
        "generaciones_por_publicacion": piezas_por_publicacion,
        "generaciones_mensuales_sin_reintentos": generaciones_mensuales,
        "intentos_por_pieza_conforme": intentos_por_pieza_conforme,
        "segundos_mensuales_p50_sin_reintentos": (
            round(generaciones_mensuales * p50, 3) if p50 is not None else None
        ),
        "segundos_mensuales_p95_sin_reintentos": (
            round(generaciones_mensuales * p95, 3) if p95 is not None else None
        ),
        "segundos_mensuales_p50_con_reintentos": (
            round(generaciones_mensuales * p50 / tasa_conformidad, 3)
            if p50 is not None and tasa_conformidad
            else None
        ),
        "jornadas_laborales_equivalentes_p50": (
            round(generaciones_mensuales * p50 / JORNADA_LABORAL_S, 4)
            if p50 is not None
            else None
        ),
        "pico_semanal_publicaciones": VOLUMEN_SEU["publicaciones_semanales_minimas"],
        "segundos_pico_semanal_p95": (
            round(
                VOLUMEN_SEU["publicaciones_semanales_minimas"]
                * piezas_por_publicacion
                * p95,
                3,
            )
            if p95 is not None
            else None
        ),
        "reel_incluido": False,
        "nota_reel": (
            "El reel mensual informado por la SEU no entra en el cálculo: A1 no "
            "produce video, audio ni guion audiovisual."
        ),
    }

    resumen = {
        "schema_version": "capacidad_a1_v1",
        "evidence_kind": "CAPACIDAD_LOCAL_LLM",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": "SINTETICA",
        "generator_kind": "OLLAMA_LOCAL_JSON_SCHEMA",
        "model": args.modelo,
        "num_predict": args.num_predict,
        "timeout_s": args.timeout,
        "temperature": 0,
        "creative_contract_version": CONTRATO_CREATIVO_V3.contract_version,
        "policy_document_version": POLICY_VERSION,
        "volumen_seu": VOLUMEN_SEU,
        "volumen_es_sla": False,
        "seu_validated": False,
        "published": False,
        "trl3_claimed": False,
        "artifact_hashes": {
            "dataset_sha256": _sha256(dataset),
            "renderer_source_sha256": _sha256(ROOT / "src" / "agente1" / "posts.py"),
            "policy_sha256": _sha256(
                ROOT
                / "src"
                / "agente1"
                / "politicas"
                / "politica_redes_provisional_v1.json"
            ),
        },
        "totales": {
            "generaciones": len(mediciones),
            "conformes": len(conformes),
            "tasa_conformidad": round(tasa_conformidad, 4),
            "codigos_de_rechazo": dict(sorted(errores.items())),
        },
        "latencia_fria": _resumen_latencias(frias),
        "latencia_caliente": _resumen_latencias(calientes),
        "latencia_por_pieza": {
            pieza: _resumen_latencias(
                [
                    float(item["latencia_s"])
                    for item in mediciones
                    if item["pieza"] == pieza
                ]
            )
            for pieza in sorted({str(item["pieza"]) for item in mediciones})
        },
        "proyeccion_volumen_mensual": proyeccion,
        "mediciones": mediciones,
    }

    destino = salida / "resumen-capacidad.json"
    destino.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(resumen["totales"], ensure_ascii=False), flush=True)
    print(json.dumps(proyeccion, ensure_ascii=False), flush=True)
    print(f"resumen: {destino}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
