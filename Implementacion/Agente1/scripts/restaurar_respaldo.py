#!/usr/bin/env python3
"""Restauración del estado local desde un artefacto de respaldo (#86).

Es la otra mitad del respaldo diario (ADR 0009): un procedimiento manual
que el operador corre cuando hay que reconstruir el estado del agente —
pérdida del host, migración— a partir de un archivo
`agente1-respaldo-AAAA-MM-DD.tar.gz` descargado de la carpeta de Drive.
El script no toca la red: el operador trae el artefacto.

Uso:

    python scripts/restaurar_respaldo.py \
        --artefacto agente1-respaldo-2026-10-05.tar.gz \
        --salida salida \
        --registro salida/registro-confirmaciones

Qué hace, en orden y siempre fail-closed:

1. Verifica el manifiesto del artefacto: record `agente1_respaldo_v1`,
   marca `creado_en` con zona y un sha256 por miembro que tiene que
   coincidir byte a byte. Un artefacto que no verifica no escribe nada.
2. Repone cada miembro bajo `--salida` o `--registro` sin pisar lo que ya
   existe: un archivo idéntico se omite y uno distinto se reporta como
   `conflicto` — nunca se pierde estado posterior en silencio. Archivos
   `0600`, directorios `0700`, como el resto del estado del agente.
3. Marca el registro restaurado: toda reserva (`ENVIO_RESERVADO`,
   `EMISION_RESERVADA`) pasa a indeterminada —una reserva restaurada es
   por definición interrumpida— y toda entrada en estado de aprobación
   (`APROBADA`, las parciales, `ENVIO_ENCOLADO`) cuya última transición es
   posterior a la marca del respaldo pasa a `ENVIO_INDETERMINADO`.

Lo que quedó indeterminado no se reenvía ni se emite: es estado terminal
para los dos pipelines. Una persona cruza cada clave contra Gmail
Enviados (y, para certificados, contra el destino de emisión) antes de
decidir. El informe JSON de salida trae las claves marcadas y el log
`logs/respaldo-diario.jsonl` registra la restauración con hashes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.respaldo import (  # noqa: E402
    RespaldoDiarioError,
    restaurar_estado_respaldo,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Restaura el estado local desde un artefacto de respaldo y "
            "marca indeterminadas las aprobaciones posteriores a la marca."
        )
    )
    parser.add_argument(
        "--artefacto",
        type=Path,
        required=True,
        help="archivo agente1-respaldo-AAAA-MM-DD.tar.gz descargado de Drive",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        required=True,
        help="directorio de salida a reconstruir (recibe los miembros salida/)",
    )
    parser.add_argument(
        "--registro",
        type=Path,
        default=None,
        help=(
            "directorio del registro durable de confirmaciones "
            "(obligatorio si el artefacto lo incluye)"
        ),
    )
    args = parser.parse_args(argv)

    try:
        resultado = restaurar_estado_respaldo(
            artefacto_path=args.artefacto,
            directorio_salida=args.salida,
            registro_confirmaciones=args.registro,
        )
    except RespaldoDiarioError as exc:
        print(
            json.dumps(
                {"status": "INVALID", "error_code": exc.code},
                sort_keys=True,
            )
        )
        return 2
    except OSError:
        print(
            json.dumps(
                {"status": "INVALID", "error_code": "respaldo_entrada_inaccesible"},
                sort_keys=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": "OK",
                "marca": resultado.marca,
                "artefacto_sha256": resultado.artefacto_sha256,
                "archivos_restaurados": resultado.archivos_restaurados,
                "archivos_omitidos": resultado.archivos_omitidos,
                "conflictos": list(resultado.conflictos),
                "indeterminados": len(resultado.indeterminados),
                "claves_indeterminadas": list(resultado.indeterminados),
                "audit_path": str(resultado.audit_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
