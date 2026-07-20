from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol


BORRADOR_MARKER = "# BORRADOR — NO PUBLICAR\n\n"
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ReferenciaBorrador:
    tipo: str
    referencia: str
    path: Path | None = None

    def __post_init__(self) -> None:
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
    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador: ...


class DestinoBorradoresError(RuntimeError):
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
    def __init__(self, directorio_salida: Path) -> None:
        self._directorio_salida = directorio_salida

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        _validar_entrada(id_solicitud, contenido)
        directorio_borradores = (self._directorio_salida / "borradores").resolve()
        path = (directorio_borradores / f"{id_solicitud}.md").resolve()
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
    _validar_entrada(id_solicitud, contenido)


def _validar_entrada(id_solicitud: str, contenido: str) -> None:
    if (
        not isinstance(id_solicitud, str)
        or ID_SOLICITUD_RE.fullmatch(id_solicitud) is None
        or not isinstance(contenido, str)
        or not contenido.startswith(BORRADOR_MARKER)
    ):
        raise DestinoBorradoresError("destination_contract_invalid")
