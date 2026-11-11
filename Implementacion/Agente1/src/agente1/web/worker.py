"""Worker de generación del canal web (ADR 0016, issue #149).

Corre fuera de la respuesta HTTP: toma una ejecución reservada por vez
(`SELECT ... FOR UPDATE SKIP LOCKED` con plazo), genera la pieza con el
núcleo vigente —`interpretar_solicitud` para difusión de actividad, las
seams declaradas `confirmar_pieza`/`generar_pieza` para el resto— y deja
el estado durable en la base.

Recuperación: si el proceso cae entre el Doc y el asiento, la reserva
vence y otra corrida retoma el trabajo; el destino busca el Doc por la
marca de la solicitud en sus propiedades antes de crear uno, así que la
segunda corrida reutiliza el mismo documento (ADR 0016, prueba 1).

Una falla reportada por el pipeline (gate rechazado, datos incompletos)
cierra la ejecución como `FALLIDA` y la solicitud queda `ERROR`. Una
excepción no prevista no toca el estado: la reserva vence sola y el
trabajo vuelve a ser tomable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ..destinos import BORRADOR_MARKER, ReferenciaBorrador
from ..fuentes import FuenteSolicitudes
from ..gacetillas import (
    confirmar_pieza,
    generar_pieza,
    modo_de,
    nombre_doc,
    requiere_actividad,
)
from ..interpretacion import IdentidadSolicitante, interpretar_solicitud
from ..procesamiento import Generator
from .persistencia import RepositorioWeb, TrabajoWeb


class FalloGeneracion(RuntimeError):
    """El pipeline reportó una falla esperada: la ejecución queda FALLIDA."""

    def __init__(self, resultado: str) -> None:
        self.resultado = resultado
        super().__init__(resultado)


@dataclass(frozen=True)
class ResultadoDestinoWeb:
    """Lo que devuelve el destino por marca: referencia y metadatos del Doc."""

    referencia: ReferenciaBorrador
    doc_ref: str
    head_revision_id: str | None


class DestinoPorMarca(Protocol):
    """Puerto del destino «un Doc por solicitud» (ADR 0016).

    Antes de crear, busca por la marca de la solicitud en las propiedades
    del documento: una segunda corrida sobre la misma solicitud reutiliza
    el Doc existente y vuelca el contenido en él, nunca crea otro.
    """

    def buscar_o_crear(
        self,
        *,
        marca: str,
        id_solicitud: str,
        contenido: str,
        nombre: str | None,
    ) -> ResultadoDestinoWeb: ...


class DestinoPorMarcaMemoria:
    """Destino fake para desarrollo, pruebas y evidencia.

    Un dict en memoria hace de Drive: la marca es la clave, así que una
    recreación sobre la misma solicitud reutiliza el documento.
    """

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    def buscar_o_crear(
        self,
        *,
        marca: str,
        id_solicitud: str,
        contenido: str,
        nombre: str | None,
    ) -> ResultadoDestinoWeb:
        doc = self.docs.get(marca)
        if doc is None:
            ref = ReferenciaBorrador(
                tipo="docs_fake", referencia=f"doc-{marca}"
            )
            doc = {"ref": ref, "head": "head-1", "nombre": nombre}
            self.docs[marca] = doc
        doc["contenido"] = contenido
        return ResultadoDestinoWeb(
            referencia=doc["ref"],
            doc_ref=doc["ref"].referencia,
            head_revision_id=doc["head"],
        )


class _DestinoMarcado:
    """Adapter `DestinoBorradores` que ata el Doc a la solicitud web.

    Envuelve al `DestinoPorMarca` para que el pipeline —que sólo conoce
    `guardar`— termine escribiendo en el Doc marcado de la solicitud, sin
    saber que existe.
    """

    def __init__(self, destino: DestinoPorMarca, *, marca: str) -> None:
        self._destino = destino
        self._marca = marca
        self.ultimo: ResultadoDestinoWeb | None = None
        self.ultimo_contenido: str | None = None

    def guardar(
        self,
        id_solicitud: str,
        contenido: str,
        *,
        nombre: str | None = None,
    ) -> ReferenciaBorrador:
        resultado = self._destino.buscar_o_crear(
            marca=self._marca,
            id_solicitud=id_solicitud,
            contenido=contenido,
            nombre=nombre,
        )
        self.ultimo = resultado
        self.ultimo_contenido = contenido
        return resultado.referencia


def _generar_pieza(
    trabajo: TrabajoWeb,
    *,
    fuente: FuenteSolicitudes,
    generator: Generator,
    directorio_salida: Path,
    destino: DestinoPorMarca,
) -> tuple[str, ResultadoDestinoWeb]:
    """Corre el pipeline del tipo y devuelve (texto, destino del Doc)."""
    destino_marcado = _DestinoMarcado(destino, marca=trabajo.id_solicitud)
    if requiere_actividad(trabajo.tipo_pieza):
        # Mismo despacho que el Form: texto determinístico del pedido,
        # interpretar_solicitud decide (fuente, gate, destino, auditoría).
        resultado = interpretar_solicitud(
            texto=f"gacetilla actividad {trabajo.actividad_ref}",
            solicitante=IdentidadSolicitante(
                identificador=trabajo.solicitante_hash, rol=trabajo.rol
            ),
            fuente=fuente,
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino_marcado,
        )
        if resultado.estado != "PENDIENTE_VALIDACION":
            raise FalloGeneracion("error_generacion")
    else:
        campos = {
            clave: str(valor)
            for clave, valor in trabajo.campos.get("pieza", {}).items()
        }
        if modo_de(trabajo.tipo_pieza) == "genera":
            pieza, errores = generar_pieza(
                trabajo.tipo_pieza, campos, generator
            )
        else:
            pieza, errores = confirmar_pieza(trabajo.tipo_pieza, campos)
        if errores or not pieza:
            raise FalloGeneracion("salida_no_conforme")
        contenido = f"{BORRADOR_MARKER}{pieza}"
        nombre = nombre_doc(
            trabajo.tipo_pieza, campos, datetime.now().date()
        )
        destino_marcado.guardar(
            trabajo.id_solicitud, contenido, nombre=nombre
        )
    if (
        destino_marcado.ultimo is None
        or destino_marcado.ultimo_contenido is None
    ):
        raise FalloGeneracion("error_generacion")
    return destino_marcado.ultimo_contenido, destino_marcado.ultimo


def correr_una_vez(
    *,
    repositorio: RepositorioWeb,
    worker_id: str,
    fuente: FuenteSolicitudes,
    generator: Generator,
    directorio_salida: Path,
    destino: DestinoPorMarca,
    plazo_segundos: int = 300,
    ahora: datetime | None = None,
) -> TrabajoWeb | None:
    """Un ciclo del worker: reserva, genera y asienta. `None` si no hay trabajo."""
    trabajo = repositorio.tomar_trabajo(
        worker_id=worker_id,
        plazo_segundos=plazo_segundos,
        ahora=ahora,
    )
    if trabajo is None:
        return None
    try:
        texto, resultado_destino = _generar_pieza(
            trabajo,
            fuente=fuente,
            generator=generator,
            directorio_salida=directorio_salida,
            destino=destino,
        )
    except FalloGeneracion as fallo:
        repositorio.fallar_trabajo(
            id_ejecucion=trabajo.id_ejecucion,
            id_solicitud=trabajo.id_solicitud,
            resultado=fallo.resultado,
            ahora=ahora,
        )
        return trabajo
    except Exception:
        # Caída o error de infraestructura: no se toca el estado; la
        # reserva vence y otra corrida retoma sin duplicar el Doc.
        return trabajo
    repositorio.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=trabajo.id_solicitud,
        texto_generado=texto,
        referencia=resultado_destino.doc_ref,
        doc_ref=resultado_destino.doc_ref,
        head_revision_id=resultado_destino.head_revision_id,
        ahora=ahora,
    )
    return trabajo
