"""Semilla ficticia del lote de certificados de la demostración (#168).

La misma semilla la siembra el script de consola
(`scripts/demo_lote_certificados.py`) y el POST del modo demostración en
`web/demo_certificados.py`: misma actividad, mismas personas y el mismo
`objeto_lote` determinista, así que una vía devuelve el lote que la otra
ya creó y la marca de demostración vale para las dos.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .canal_form import hash_correo
from .certificados_emision import (
    PersonaCierre,
    hash_lista_cierre,
    objeto_lote_cierre,
)
from .fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from .manifest_version import raiz_agente
from .web.certificados_web import LoteCertificados, LoteCertificadosError

ACTIVIDAD_DEMO = "FIE-DIF-02"
CANTIDAD_DEMO = 6
CANTIDAD_MINIMA = 5
CANTIDAD_MAXIMA = 8
HORAS_DEMO = "24"
MODALIDAD_DEMO = "presencial"
LINEA_DEMO = (
    "Curso introductorio sobre herramientas de inteligencia artificial "
    "para organizar y analizar información institucional."
)
CODIGO_ACTIVIDAD_AUSENTE = "demo_actividad_ausente"

CORPUS_ACTIVIDADES = (
    raiz_agente() / "data" / "corpus-fie-informa-difusiones.csv"
)
ACTIVIDADES_SINTETICAS = (
    raiz_agente() / "data" / "actividades_sinteticas.csv"
)

_CAMPOS_ACTIVIDAD = (
    "titulo",
    "duracion_horas",
    "modalidad",
    "fecha_inicio",
    "fecha_fin",
    "organiza",
)
_REQUERIDOS_FICHA = ("titulo", "fecha_inicio", "organiza")


class RepositorioLotesDemoPuerto(Protocol):
    """El `crear` idempotente del circuito real de lotes, no una vía aparte."""

    def crear(
        self,
        *,
        id_actividad: str,
        actividad: dict[str, str],
        personas: tuple[PersonaCierre, ...],
        linea_descriptiva: str,
        generada_por_hash: str,
        ahora: datetime | None = None,
    ) -> LoteCertificados: ...


def personas_demo(cantidad: int = CANTIDAD_DEMO) -> tuple[PersonaCierre, ...]:
    """Filas ficticias, marcadas como tales y sin correos reales."""
    return tuple(
        PersonaCierre(
            nombre=f"Persona Ficticia {indice}",
            apellido="Demo",
            dni=f"900000{indice:02d}",
            mail=f"persona.ficticia.{indice}@example.invalid",
            tratamiento="Sra." if indice % 2 == 0 else "Sr.",
            condicion="aprobacion",
        )
        for indice in range(1, cantidad + 1)
    )


def rutas_respaldo() -> tuple[Path, Path]:
    """Los datasets del repo, en el orden que usa la siembra."""
    return (CORPUS_ACTIVIDADES, ACTIVIDADES_SINTETICAS)


def datos_actividad(fila: Mapping[str, str]) -> dict[str, str] | None:
    """Ficha del lote desde una fila de la fuente, o `None` si no sirve.

    La carga horaria y la modalidad se completan con los valores
    declarados de demo cuando la fila no los trae; si falta título,
    fecha de inicio u organiza, la fila no alcanza.
    """
    datos = {
        campo: str(fila.get(campo, "") or "").strip()
        for campo in _CAMPOS_ACTIVIDAD
    }
    if not datos["duracion_horas"]:
        datos["duracion_horas"] = HORAS_DEMO
    if not datos["modalidad"]:
        datos["modalidad"] = MODALIDAD_DEMO
    if not all(datos[campo] for campo in _REQUERIDOS_FICHA):
        return None
    return datos


def fila_actividad_csv(
    ruta: Path | str, id_actividad: str
) -> Mapping[str, str] | None:
    """La fila cruda de la actividad en el CSV, o `None` si no se pudo leer."""
    try:
        return CsvFuenteSolicitudes(Path(str(ruta))).obtener(id_actividad)
    except (FuenteSolicitudesError, OSError):
        return None


def actividad_demo(
    actividades: Iterable[Mapping[str, str]] | None,
    *,
    rutas: Iterable[Path | str] | None = None,
) -> dict[str, str]:
    """La ficha de `ACTIVIDAD_DEMO`, igual que en el script de consola.

    Primero la fuente ya cargada por la app —`AGENTE1_TABLA`, la misma
    que alimenta el select del pedido— y después los datasets del repo
    (corpus y sintéticas), en ese orden. Si la actividad no está en
    ninguno o ninguna fila alcanza, `demo_actividad_ausente`.
    """
    for fila in actividades or ():
        if str(fila.get("id_actividad", "")).strip() == ACTIVIDAD_DEMO:
            datos = datos_actividad(fila)
            if datos is not None:
                return datos
    for ruta in rutas if rutas is not None else rutas_respaldo():
        fila = fila_actividad_csv(ruta, ACTIVIDAD_DEMO)
        if fila is None:
            continue
        datos = datos_actividad(fila)
        if datos is not None:
            return datos
    raise LoteCertificadosError(CODIGO_ACTIVIDAD_AUSENTE)


OBJETO_LOTE_DEMO = objeto_lote_cierre(
    ACTIVIDAD_DEMO, hash_lista_cierre(personas_demo())
)
ID_LOTE_DEMO = f"lote-{OBJETO_LOTE_DEMO[:16]}"

_HASHES_LISTA_DEMO = frozenset(
    hash_lista_cierre(personas_demo(cantidad))
    for cantidad in range(CANTIDAD_MINIMA, CANTIDAD_MAXIMA + 1)
)


def es_lote_demo(lote: LoteCertificados) -> bool:
    """Marca explícita: si el lote salió de la semilla ficticia.

    Compara el `objeto_lote` con el canónico de la `id_actividad` del
    propio lote para cada lista demo válida —`personas_demo(5..8)`, el
    rango del script—, así que cubre la semilla del botón y todas las
    variantes `--actividad`/`--cantidad`. Lo que matchea son siempre los
    datos ficticios de la semilla, no una heurística de correos, y la
    marca sobrevive a la purga porque `id_actividad` y `objeto_lote`
    quedan en la fila.
    """
    return any(
        lote.objeto_lote
        == objeto_lote_cierre(lote.id_actividad, hash_lista)
        for hash_lista in _HASHES_LISTA_DEMO
    )


def crear_lote_demo(
    repositorio: RepositorioLotesDemoPuerto,
    *,
    id_actividad: str,
    actividad: dict[str, str],
    personas: tuple[PersonaCierre, ...],
    generador_correo: str,
) -> LoteCertificados:
    """Siembra el lote ficticio; si ya existe, devuelve el existente.

    La idempotencia es la del repositorio —`ON CONFLICT` sobre
    `objeto_lote`—: el mismo alta repetida devuelve la misma fila sin
    tocar su estado ni su decisión. `generador_correo` identifica a
    quien siembra: es quien después lo aprueba (ADR 0018).
    """
    return repositorio.crear(
        id_actividad=id_actividad,
        actividad=actividad,
        personas=personas,
        linea_descriptiva=LINEA_DEMO,
        generada_por_hash=hash_correo(generador_correo),
    )


__all__ = [
    "ACTIVIDAD_DEMO",
    "ACTIVIDADES_SINTETICAS",
    "CANTIDAD_DEMO",
    "CANTIDAD_MAXIMA",
    "CANTIDAD_MINIMA",
    "CODIGO_ACTIVIDAD_AUSENTE",
    "CORPUS_ACTIVIDADES",
    "HORAS_DEMO",
    "ID_LOTE_DEMO",
    "LINEA_DEMO",
    "MODALIDAD_DEMO",
    "OBJETO_LOTE_DEMO",
    "RepositorioLotesDemoPuerto",
    "actividad_demo",
    "crear_lote_demo",
    "datos_actividad",
    "es_lote_demo",
    "fila_actividad_csv",
    "personas_demo",
    "rutas_respaldo",
]
