from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol


COLUMNAS_GACETILLA = (
    "id_solicitud",
    "titulo",
    "descripcion",
    "fecha",
    "publico",
    "organiza",
    "contacto",
    "fuente",
    "lugar",
)


class FuenteSolicitudes(Protocol):
    def obtener(self, id_solicitud: str) -> dict[str, str]: ...


class FuenteSolicitudesError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CsvFuenteSolicitudes:
    def __init__(self, path: Path) -> None:
        self._path = path

    def obtener(self, id_solicitud: str) -> dict[str, str]:
        coincidencias: list[dict[str, str]] = []
        with self._path.open(encoding="utf-8", newline="") as archivo:
            reader = csv.DictReader(archivo)
            encabezados = reader.fieldnames or []
            if len(encabezados) != len(set(encabezados)):
                raise FuenteSolicitudesError("source_contract_invalid")
            for fila in reader:
                if None in fila:
                    raise FuenteSolicitudesError("source_contract_invalid")
                if fila.get("id_solicitud") == id_solicitud:
                    coincidencias.append(
                        {
                            clave: fila.get(clave) or ""
                            for clave in COLUMNAS_GACETILLA
                        }
                    )
        if not coincidencias:
            raise FuenteSolicitudesError("source_request_not_found")
        if len(coincidencias) > 1:
            raise FuenteSolicitudesError("source_duplicate_id")
        return coincidencias[0]
