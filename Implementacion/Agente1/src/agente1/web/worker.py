"""Worker de generación del canal web (ADR 0016, issue #149).

Corre fuera de la respuesta HTTP: toma una ejecución reservada por vez
(`SELECT ... FOR UPDATE SKIP LOCKED` con plazo) y la despacha por
`interpretar_solicitud` con el `DespachoGacetilla` estructurado del
pedido, para los siete tipos: la misma clasificación determinística del
texto, el mismo gate de rol y la misma auditoría HU-013 que cualquier
otro canal, sin caminos paralelos en la app.

Recuperación: si el proceso cae entre el Doc y el asiento, la reserva
vence y otra corrida retoma el trabajo; el destino busca el Doc por la
marca de la solicitud en sus propiedades antes de crear uno, así que la
segunda corrida reutiliza el mismo documento (ADR 0016, prueba 1).

Decisiones que no se ven en el código:

- **El límite de reintentos se mide por reservas tomadas.** Una falla
  reportada por el pipeline (gate rechazado, datos incompletos, tipo no
  disponible) cierra la ejecución de inmediato: no tiene sentido volver a
  intentar lo mismo. Una excepción no prevista sí reintenta, pero con
  tope `MAX_INTENTOS`: al agotarse, la ejecución queda `FALLIDA` con
  `error_generacion` y la solicitud `ERROR`, visible en la bandeja, en
  vez de colgar para siempre.
- **El log nunca lleva prosa ni identidad**: una línea por falla con el
  código estable, el id de la ejecución y el intento — los identificadores
  ya son opacos y el detalle del motivo queda en el resultado durable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ..destinos import ReferenciaBorrador
from ..fuentes import FuenteSolicitudes
from ..gacetillas import requiere_actividad
from ..interpretacion import (
    DespachoGacetilla,
    IdentidadSolicitante,
    interpretar_solicitud,
)
from ..procesamiento import Generator
from .persistencia import RepositorioWeb, TrabajoWeb

logger = logging.getLogger(__name__)

MAX_INTENTOS = 3

# Estado del pipeline → cierre durable de la ejecución. Los códigos son el
# vocabulario cerrado del esquema (`ejecuciones.resultado`): un resultado
# fuera de la lista rompe el CHECK, así que el mapa es exhaustivo.
_CIERRE_POR_ESTADO = {
    "INCOMPLETA": ("INCOMPLETA", "datos_incompletos"),
    "INVALIDA": ("FALLIDA", "source_invalid"),
    "RECHAZADA": ("FALLIDA", "channel_invalid"),
    "FALLIDA": ("FALLIDA", "error_generacion"),
    "PENDIENTE_DESAMBIGUACION": ("FALLIDA", "error_generacion"),
}


class FalloGeneracion(RuntimeError):
    """El pipeline reportó una falla esperada: la ejecución queda cerrada."""

    def __init__(self, estado: str, resultado: str) -> None:
        self.estado = estado
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
    """Despacha el trabajo por `interpretar_solicitud` y vuelca el resultado.

    El `DespachoGacetilla` declara el tipo de la lista cerrada, la
    actividad de los tipos con ficha y los campos confirmados del pedido;
    el texto del mensaje es derivado y lleva la descripción del pedido
    como dato no privilegiado (ADR 0001): la clasificación la lee, el
    prompt nunca.
    """
    destino_marcado = _DestinoMarcado(destino, marca=trabajo.id_solicitud)
    if requiere_actividad(trabajo.tipo_pieza):
        texto = f"gacetilla actividad {trabajo.actividad_ref}"
    else:
        texto = f"gacetilla {trabajo.tipo_pieza}"
    if trabajo.descripcion:
        texto = f"{texto}. {trabajo.descripcion}"
    resultado = interpretar_solicitud(
        texto=texto,
        solicitante=IdentidadSolicitante(
            identificador=trabajo.solicitante_hash, rol=trabajo.rol
        ),
        fuente=fuente,
        directorio_salida=directorio_salida,
        generator=generator,
        destino=destino_marcado,
        despacho_gacetilla=DespachoGacetilla(
            tipo=trabajo.tipo_pieza,
            id_solicitud=trabajo.id_solicitud,
            actividad=trabajo.actividad_ref,
            campos={
                clave: str(valor)
                for clave, valor in trabajo.campos.get("pieza", {}).items()
            },
        ),
    )
    estado, resultado_codigo = _CIERRE_POR_ESTADO.get(
        resultado.estado, ("FALLIDA", "error_generacion")
    )
    if resultado.estado != "PENDIENTE_VALIDACION":
        raise FalloGeneracion(estado, resultado_codigo)
    if (
        destino_marcado.ultimo is None
        or destino_marcado.ultimo_contenido is None
    ):
        raise FalloGeneracion("FALLIDA", "error_generacion")
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
    max_intentos: int = MAX_INTENTOS,
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
        logger.warning(
            "worker_fallo id_ejecucion=%s resultado=%s",
            trabajo.id_ejecucion,
            fallo.resultado,
        )
        repositorio.fallar_trabajo(
            id_ejecucion=trabajo.id_ejecucion,
            id_solicitud=trabajo.id_solicitud,
            estado=fallo.estado,
            resultado=fallo.resultado,
            ahora=ahora,
        )
        return trabajo
    except Exception:
        # Error de infraestructura o caída: la reserva vence y otra corrida
        # retoma sin duplicar el Doc, hasta el tope de reintentos; después
        # la ejecución queda cerrada y la solicitud visible «Con error».
        if trabajo.intentos >= max_intentos:
            logger.warning(
                "worker_sin_reintento id_ejecucion=%s intentos=%s",
                trabajo.id_ejecucion,
                trabajo.intentos,
            )
            repositorio.fallar_trabajo(
                id_ejecucion=trabajo.id_ejecucion,
                id_solicitud=trabajo.id_solicitud,
                resultado="error_generacion",
                ahora=ahora,
            )
        else:
            logger.warning(
                "worker_error_no_previsto id_ejecucion=%s intento=%s",
                trabajo.id_ejecucion,
                trabajo.intentos,
            )
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
