"""Puerto de salida: dónde queda un borrador y con qué marca.

`DestinoBorradores` es el único camino por el que sale contenido del agente, y
está deliberadamente limitado a *guardar*: no expone compartir, enviar,
publicar ni cambiar permisos. Que esa capacidad no exista es en sí mismo un
control (ver `auditoria_d2.py`), no un pendiente de implementación.

Decisiones que no se ven en el código:

- **La marca de borrador se valida acá, no sólo se agrega arriba.** Todo
  contenido debe empezar con `BORRADOR_MARKER`; un adapter rechaza cualquier
  texto sin esa cabecera. Así, si alguien construye contenido por otro camino y
  se saltea el pipeline, igual no puede escribirlo como si fuera definitivo.
- **La referencia devuelta es opaca hacia arriba.** El pipeline sólo guarda su
  hash en el log, de modo que un identificador de Google Docs nunca queda
  escrito en la auditoría.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol


# Cabecera obligatoria de todo borrador. La escribe el pipeline y la vuelve a
# verificar el destino: es la única marca que ve una persona al abrir el
# documento y la que audita `auditoria_d2._salidas_son_borradores`.
BORRADOR_MARKER = "# BORRADOR — NO PUBLICAR\n\n"
# Allowlist de identificadores. Se aplica antes de construir cualquier path o
# título de documento, para que un id con `../`, espacios o caracteres de
# control no llegue nunca al sistema de archivos ni a la API remota.
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ReferenciaBorrador:
    """Dónde quedó el borrador, sin exponer su contenido.

    `path` sólo lo completa el adapter local de Markdown; los adapters remotos
    devuelven `referencia` (id del documento) y ningún path, porque no hay un
    archivo local que abrir.
    """

    tipo: str
    referencia: str
    path: Path | None = None

    def __post_init__(self) -> None:
        # Sin saltos de línea: la referencia y el tipo terminan en el log JSONL
        # y en los manifests; un salto permitiría inyectar un registro falso.
        if (
            not self.tipo
            or not self.referencia
            or "\r" in self.tipo
            or "\n" in self.tipo
            or "\r" in self.referencia
            or "\n" in self.referencia
        ):
            raise ValueError("referencia de borrador inválida")


class DestinoBorradores(Protocol):
    """Puerto de escritura. `guardar` es la única operación que existe."""

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador: ...


class DestinoBorradoresError(RuntimeError):
    """Falla de escritura, con pista opcional para reconciliación manual.

    `reconciliation_ref_hash` se completa cuando la escritura quedó a medias y
    puede haber dejado un documento huérfano en el destino (por ejemplo: la
    copia de la plantilla salió bien y el volcado del texto falló). Es un hash,
    no el id: alcanza para que una persona ubique el documento cruzando el
    registro, y no expone el identificador en el log.
    """

    def __init__(
        self,
        code: str,
        *,
        reconciliation_ref_hash: str | None = None,
    ) -> None:
        self.code = code
        self.reconciliation_ref_hash = (
            reconciliation_ref_hash
            if reconciliation_ref_hash is not None
            and HASH_RE.fullmatch(reconciliation_ref_hash)
            else None
        )
        super().__init__(code)


class MarkdownDestinoBorradores:
    """Adapter local: deja el borrador como archivo `.md` bajo `borradores/`."""

    def __init__(self, directorio_salida: Path) -> None:
        self._directorio_salida = directorio_salida

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        _validar_entrada(id_solicitud, contenido)
        directorio_borradores = (self._directorio_salida / "borradores").resolve()
        path = (directorio_borradores / f"{id_solicitud}.md").resolve()
        # Doble control de escape de directorio: el id ya pasó por la allowlist,
        # pero se comprueba también el path resuelto, porque un enlace simbólico
        # en `borradores/` podría apuntar fuera del árbol de salida.
        if not path.is_relative_to(directorio_borradores):
            raise DestinoBorradoresError("destination_contract_invalid")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contenido, encoding="utf-8")
        return ReferenciaBorrador(
            tipo="markdown",
            referencia=str(path),
            path=path,
        )


def validar_entrada_borrador(id_solicitud: str, contenido: str) -> None:
    """Control compartido por los adapters remotos, antes de tocar la red.

    Los adapters de Workspace lo llaman en primer lugar para no gastar una
    llamada HTTP —ni crear un documento— con una entrada que igual sería
    rechazada.
    """

    _validar_entrada(id_solicitud, contenido)


def _validar_entrada(id_solicitud: str, contenido: str) -> None:
    if (
        not isinstance(id_solicitud, str)
        or ID_SOLICITUD_RE.fullmatch(id_solicitud) is None
        or not isinstance(contenido, str)
        or not contenido.startswith(BORRADOR_MARKER)
    ):
        raise DestinoBorradoresError("destination_contract_invalid")
