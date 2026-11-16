"""Puertos del Doc por solicitud del canal web (#153, ADR 0016).

`ExportadorDocs` es lo que la app necesita del mundo Drive: el texto
plano del Doc de una solicitud, para «Traer cambios» y para verificar el
hash antes de decidir. `DocsCanalMemoria` es el fake que comparten el
worker y la app en desarrollo y evidencia: un Drive en memoria donde la
marca de la solicitud es la clave, como en el adapter real.

El adapter real (`google_workspace.GoogleDocsDestinoPorMarca`)
implementa el destino por marca y el exportador sobre la API de Drive;
acá no hay código de producción además de los contratos.
"""

from __future__ import annotations

from typing import Protocol

from ..destinos import (
    ReferenciaBorrador,
    ResultadoDestinoPorMarca,
)


class ExportadorDocs(Protocol):
    """Lo que la app le pide al Doc: su texto plano y su revisión vigente."""

    def exportar_texto(self, doc_ref: str) -> str: ...

    def head_revision(self, doc_ref: str) -> str | None: ...


class DocsCanalMemoria:
    """Drive en memoria para el canal web: destino por marca + exportador.

    La marca de la solicitud indexa el Doc, como `appProperties` en el
    adapter real: `buscar_o_crear` reutiliza el documento y el texto que
    exporta es el último escrito — igual contrato de idempotencia.
    `editar` simula la mano de una persona en Docs, para las pruebas.
    """

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self._por_marca: dict[str, str] = {}
        self.compartidos: list[tuple[str, str]] = []
        self._consecutivo = 0

    def buscar_o_crear(
        self,
        *,
        marca: str,
        id_solicitud: str,
        contenido: str,
        nombre: str | None,
    ) -> ResultadoDestinoPorMarca:
        doc_ref = self._por_marca.get(marca)
        if doc_ref is None:
            self._consecutivo += 1
            doc_ref = f"doc-{marca}-{self._consecutivo}"
            doc = {
                "ref": ReferenciaBorrador(
                    tipo="docs_fake", referencia=doc_ref
                ),
                "head_num": 1,
                "head": "head-1",
                "nombre": nombre,
            }
            self.docs[doc_ref] = doc
            self._por_marca[marca] = doc_ref
        doc = self.docs[doc_ref]
        doc["contenido"] = contenido
        return ResultadoDestinoPorMarca(
            referencia=doc["ref"],
            doc_ref=doc_ref,
            doc_url=(
                f"https://docs.google.com/document/d/{doc_ref}/edit"
            ),
            head_revision_id=doc["head"],
            texto_documento=contenido,
        )

    def exportar_texto(self, doc_ref: str) -> str:
        doc = self.docs.get(doc_ref)
        if doc is None:
            from ..destinos import DestinoBorradoresError

            raise DestinoBorradoresError("drive_resource_not_found")
        return doc.get("contenido", "")

    def head_revision(self, doc_ref: str) -> str | None:
        doc = self.docs.get(doc_ref)
        if doc is None:
            from ..destinos import DestinoBorradoresError

            raise DestinoBorradoresError("drive_resource_not_found")
        return doc.get("head")

    def compartir(self, doc_ref: str, correo: str) -> None:
        if doc_ref not in self.docs:
            from ..destinos import DestinoBorradoresError

            raise DestinoBorradoresError("drive_resource_not_found")
        self.compartidos.append((doc_ref, correo))

    def editar(self, doc_ref: str, contenido: str) -> None:
        """La mano de la persona en el Doc: cambia texto y revisión de Drive."""
        doc = self.docs[doc_ref]
        doc["contenido"] = contenido
        doc["head_num"] = int(doc.get("head_num", 1)) + 1
        doc["head"] = f"head-{doc['head_num']}"
