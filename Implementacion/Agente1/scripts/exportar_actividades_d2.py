#!/usr/bin/env python3
"""Exporta la pestaña de actividades de D2 a un CSV consumible por el agente.

La pestaña de actividades de D2 es la fuente operativa: el Agente 1 la lee en
sólo lectura (decisión #54: lee actividades, no las crea). Este script vuelca
su rango configurado a un CSV con el encabezado exacto de
`COLUMNAS_ACTIVIDADES_V2`, que `CsvFuenteSolicitudes` puede consumir sin
ninguna transformación intermedia. Sirve como copia de respaldo offline y
como insumo para pruebas y matrices.

Junto al CSV se escribe un sidecar `<nombre>.meta.json` que registra cuándo
se produjo la exportación y sobre qué commit del repositorio: la trazabilidad
de un artefacto versionado exige ambas piezas (`schema_version`,
`fecha_exportacion`, `commit_base`, `filas`, `csv_sha256`).

Uso:

    python scripts/exportar_actividades_d2.py \\
        --spreadsheet-id <ID> --rango "Actividades!A1:O200" \\
        --salida data/actividades_d2.csv [--commit <sha>] [--fecha <iso>]

El token sale del proveedor de acceso por entorno (`cargar_token_provider`)
cuando está disponible; para pruebas se inyecta un transporte falso a la
función `exportar_actividades`, que es la unidad testeable. El script nunca
escribe en la planilla: la única operación de Workspace que usa es `values
.get`, la misma lectura del adapter de fuente.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.fuentes import (  # noqa: E402
    COLUMNAS_ACTIVIDADES_V2,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)

SCHEMA_VERSION_MANIFIESTO = "exportacion_actividades_d2_v1"
COLUMNAS_CONTRATO = "actividades_planilla_v2"


def exportar_actividades(
    *,
    fuente: FuenteSolicitudes,
    csv_path: Path,
    commit_base: str,
    fecha_exportacion: datetime,
) -> dict[str, object]:
    """Vuelca `fuente.enumerar()` a `csv_path` y escribe el sidecar `.meta.json`.

    El CSV queda en el contrato exacto de `COLUMNAS_ACTIVIDADES_V2`: mismo
    orden de columnas, campos vacíos como cadena vacía. No se escribe nada
    más en el CSV (ni comentarios ni filas de metadatos) para que
    `CsvFuenteSolicitudes(csv_path)` lo pueda leer tal cual; la fecha y el
    commit van en el sidecar.

    Devuelve el manifest para que el llamador lo controle o lo imprima.
    """

    filas = fuente.enumerar()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=list(COLUMNAS_ACTIVIDADES_V2))
        writer.writeheader()
        for fila in filas:
            writer.writerow(
                {columna: fila.get(columna, "") for columna in COLUMNAS_ACTIVIDADES_V2}
            )

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION_MANIFIESTO,
        "columnas_contrato": COLUMNAS_CONTRATO,
        "columnas": list(COLUMNAS_ACTIVIDADES_V2),
        "fecha_exportacion": fecha_exportacion.astimezone(
            timezone.utc
        ).isoformat(),
        "commit_base": commit_base,
        "filas": len(filas),
        "csv_path": csv_path.name,
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    meta_path = csv_path.with_suffix(csv_path.suffix + ".meta.json")
    meta_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _commit_actual(repo_root: Path) -> str:
    """Commit de la base sobre la que se produjo la exportación."""

    try:
        resultado = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise FuenteSolicitudesError("export_commit_unavailable") from error
    commit = resultado.stdout.strip()
    if not commit:
        raise FuenteSolicitudesError("export_commit_unavailable")
    return commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--rango", required=True)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument(
        "--commit",
        default=None,
        help="Commit de la base a registrar (por defecto, `git rev-parse HEAD`).",
    )
    parser.add_argument(
        "--fecha",
        default=None,
        help="Fecha de exportación ISO 8601 (por defecto, el instante actual UTC).",
    )
    args = parser.parse_args()

    from agente1.google_workspace import GoogleSheetsFuenteSolicitudes
    from agente1.workspace_auth import construir_token_provider

    fuente = GoogleSheetsFuenteSolicitudes(
        spreadsheet_id=args.spreadsheet_id,
        rango_a1=args.rango,
        token_provider=construir_token_provider(),
    )
    commit_base = args.commit or _commit_actual(REPO_ROOT)
    if args.fecha is not None:
        fecha_exportacion = datetime.fromisoformat(args.fecha)
        if fecha_exportacion.tzinfo is None:
            fecha_exportacion = fecha_exportacion.replace(tzinfo=timezone.utc)
    else:
        fecha_exportacion = datetime.now(timezone.utc)

    manifest = exportar_actividades(
        fuente=fuente,
        csv_path=args.salida.resolve(),
        commit_base=commit_base,
        fecha_exportacion=fecha_exportacion,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
