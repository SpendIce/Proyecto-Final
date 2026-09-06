"""Puerto de entrada: de dónde salen los datos de una solicitud.

El agente nunca inventa datos de una actividad: los lee de una fuente externa
que la institución controla. `FuenteSolicitudes` es el puerto y cada adapter
—CSV local, Google Sheets— resuelve el mismo contrato: dado un `id_solicitud`,
devolver exactamente una fila con las columnas de `COLUMNAS_GACETILLA`.

Decisiones que no se ven en el código:

- **La fuente es de sólo lectura.** No hay ninguna operación de escritura en
  este puerto: el agente no marca filas como procesadas ni corrige datos en la
  planilla. Si algo está mal en el origen, lo corrige una persona.
- **Los errores viajan como código, no como texto.** `FuenteSolicitudesError`
  lleva un `code` estable (`source_request_not_found`, `sheets_row_invalid`, …)
  porque ese código se escribe en el log de auditoría, y el mensaje de una
  excepción podría arrastrar contenido de la fila hacia el registro.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol


# Orden y nombres de las columnas del contrato de entrada. Es una tupla y no un
# conjunto porque el adapter de Sheets compara el encabezado posicionalmente:
# una planilla con las mismas columnas en otro orden se rechaza en lugar de
# leerse mal. Cambiar esta tupla es cambiar el contrato con la SEU.
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
    """Puerto de lectura de solicitudes.

    Un adapter devuelve la fila pedida o levanta `FuenteSolicitudesError`. No
    debe devolver `None` ni una fila vacía para un id inexistente: la ausencia
    es un error explícito (`source_request_not_found`) para que quede asentada
    en la auditoría en vez de derivar en una generación sin datos.
    """

    def obtener(self, id_solicitud: str) -> dict[str, str]: ...


class FuenteSolicitudesError(ValueError):
    """Falla de lectura identificada por un código estable de auditoría."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CsvFuenteSolicitudes:
    """Adapter sobre un CSV local; es la fuente usada en pruebas y matrices."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def obtener(self, id_solicitud: str) -> dict[str, str]:
        # Se recorre el archivo entero en lugar de cortar en la primera
        # coincidencia: un id repetido es un defecto del dataset y debe
        # rechazarse (`source_duplicate_id`), no resolverse eligiendo una fila
        # cualquiera. Con datasets de prueba el costo es irrelevante.
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
