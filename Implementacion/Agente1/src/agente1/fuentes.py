"""Puerto de entrada: de dónde salen los datos de una actividad.

El agente nunca inventa datos de una actividad: los lee de una fuente externa
que la institución controla (decisión #54: el agente lee actividades, no las
crea). `FuenteSolicitudes` es el puerto y cada adapter —la pestaña de
actividades de D2 vía Google Sheets, el CSV exportado— resuelve el mismo
contrato: dado un `id_actividad`, devolver exactamente una fila con las
columnas de `COLUMNAS_ACTIVIDADES_V2`. El puerto también sabe enumerar el
catálogo completo con esa misma forma de fila, para quien necesita buscar una
actividad sin conocer su identificador.

Decisiones que no se ven en el código:

- **La fuente es de sólo lectura.** No hay ninguna operación de escritura en
  este puerto: el agente no marca filas como procesadas ni corrige datos en la
  planilla. Enumerar tampoco la agrega: es otra forma de leer, no de escribir.
  Si algo está mal en el origen, lo corrige una persona —el Agente 1 lee
  actividades, no las crea ni las mantiene.
- **Los errores viajan como código, no como texto.** `FuenteSolicitudesError`
  lleva un `code` estable (`source_request_not_found`, `sheets_row_invalid`, …)
  porque ese código se escribe en el log de auditoría, y el mensaje de una
  excepción podría arrastrar contenido de la fila hacia el registro. La
  enumeración usa el mismo vocabulario de códigos que la lectura por id.
- **`fuente` es un enlace, no un descriptor.** En v2 la columna `fuente`
  apunta al documento/informe vigente de la actividad en Drive: la
  procedencia es por actividad, no por campo.
- **`id_solicitud` y `id_actividad` no son lo mismo.** El contrato identifica
  actividades con `id_actividad`. Los módulos que gestionan pedidos y
  ejecuciones de comunicación siguen llamando `id_solicitud` a su propia
  clave de solicitud: es el vocabulario interno del pipeline, no de la
  planilla de actividades.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol

# Orden y nombres de las columnas del contrato de la planilla de actividades
# (v2). Es una tupla y no un conjunto porque el adapter de Sheets compara el
# encabezado posicionalmente: una planilla con las mismas columnas en otro
# orden se rechaza en lugar de leerse mal. Cambiar esta tupla es cambiar el
# contrato con la SEU.
#
# Campos agregados por v2: `fecha_fin`, `fecha_limite_inscripcion`, `hora`,
# `modalidad`, `duracion_horas` y `enlace_inscripcion` (que reemplaza al
# `enlace` que el renderer ya soportaba). Arancel y cuotas quedan en la
# planilla de pagos (#38), unida por `id_actividad`. La planilla no decide
# qué campos son obligatorios: cada contrato de pieza (gacetilla, post)
# declara los suyos.
COLUMNAS_ACTIVIDADES_V2 = (
    "id_actividad",
    "titulo",
    "descripcion",
    "fecha_inicio",
    "fecha_fin",
    "fecha_limite_inscripcion",
    "hora",
    "modalidad",
    "duracion_horas",
    "publico",
    "organiza",
    "contacto",
    "fuente",
    "enlace_inscripcion",
    "lugar",
)


class FuenteSolicitudes(Protocol):
    """Puerto de lectura de actividades.

    Un adapter devuelve la fila pedida o levanta `FuenteSolicitudesError`. No
    debe devolver `None` ni una fila vacía para un id inexistente: la ausencia
    es un error explícito (`source_request_not_found`) para que quede asentada
    en la auditoría en vez de derivar en una generación sin datos.

    `enumerar` devuelve el catálogo completo con la misma forma de fila que
    `obtener` (una lista de dicts con las claves de `COLUMNAS_ACTIVIDADES_V2`).
    Es la operación que habilita construir un índice para búsqueda difusa sin
    que el contenido de la fuente llegue a un prompt: quien enumera se queda
    con datos estructurados, nunca con texto libre para interpretar. Sigue
    siendo de sólo lectura y usa los mismos códigos de error que `obtener`.
    """

    def obtener(self, id_actividad: str) -> dict[str, str]: ...

    def enumerar(self) -> list[dict[str, str]]: ...


class FuenteSolicitudesError(ValueError):
    """Falla de lectura identificada por un código estable de auditoría."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _leer_filas_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Lee el CSV entero y devuelve encabezados crudos más filas normalizadas.

    Valida exactamente lo que ya validaba `obtener` antes de este prefactor
    (encabezados sin duplicar, ninguna fila desalineada) y nada más: no
    compara el conjunto de columnas contra `COLUMNAS_ACTIVIDADES_V2` acá,
    porque `obtener` nunca lo exigió y esta función es compartida con él. Ese
    chequeo adicional, cuando hace falta, lo hace quien llama.
    """

    filas: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as archivo:
        reader = csv.DictReader(archivo)
        encabezados = reader.fieldnames or []
        if len(encabezados) != len(set(encabezados)):
            raise FuenteSolicitudesError("source_contract_invalid")
        for fila in reader:
            if None in fila:
                raise FuenteSolicitudesError("source_contract_invalid")
            filas.append(
                {clave: fila.get(clave) or "" for clave in COLUMNAS_ACTIVIDADES_V2}
            )
    return encabezados, filas


class CsvFuenteSolicitudes:
    """Adapter sobre un CSV local; es la fuente usada en pruebas y matrices.

    El CSV es una copia exportada de la pestaña de actividades de D2 para
    trabajo offline: el mismo contrato `COLUMNAS_ACTIVIDADES_V2`, ninguna
    transformación intermedia.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def obtener(self, id_actividad: str) -> dict[str, str]:
        # Se recorre el archivo entero en lugar de cortar en la primera
        # coincidencia: un id repetido es un defecto del dataset y debe
        # rechazarse (`source_duplicate_id`), no resolverse eligiendo una fila
        # cualquiera. Con datasets de prueba el costo es irrelevante.
        _, filas = _leer_filas_csv(self._path)
        coincidencias = [
            fila for fila in filas if fila["id_actividad"] == id_actividad
        ]
        if not coincidencias:
            raise FuenteSolicitudesError("source_request_not_found")
        if len(coincidencias) > 1:
            raise FuenteSolicitudesError("source_duplicate_id")
        return coincidencias[0]

    def enumerar(self) -> list[dict[str, str]]:
        # A diferencia de `obtener`, acá el conjunto de columnas sí se compara
        # contra el contrato: enumerar sirve para construir un índice sobre
        # todo el catálogo, y una planilla con otra forma podría ser la
        # planilla equivocada. Es la misma lógica que ya aplica el adapter de
        # Sheets al comparar el encabezado del rango.
        encabezados, filas = _leer_filas_csv(self._path)
        if set(encabezados) != set(COLUMNAS_ACTIVIDADES_V2):
            raise FuenteSolicitudesError("source_contract_invalid")
        # Un id duplicado en el catálogo completo invalida cualquier índice
        # que se construya sobre él, aunque nadie lo haya pedido todavía.
        ids_vistos: set[str] = set()
        for fila in filas:
            if fila["id_actividad"] in ids_vistos:
                raise FuenteSolicitudesError("source_duplicate_id")
            ids_vistos.add(fila["id_actividad"])
        return filas
