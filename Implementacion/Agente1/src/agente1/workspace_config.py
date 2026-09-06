"""Configuración de Workspace por entorno, validada de una sola vez.

Todo lo que el agente puede tocar en Google —qué planilla, qué rango, qué
plantilla, qué carpeta— viene de variables de entorno y se valida acá antes de
construir ningún adapter. No hay valores por defecto para los identificadores:
un entorno incompleto falla, no cae en un recurso "de prueba" implícito.

Decisiones que no se ven en el código:

- **Se rechazan las variables desconocidas con el prefijo del agente**
  (`workspace_config_unknown_key`). Un `AGENTE1_WORKSPACE_SPREADSHEET` mal
  tipeado no debe ignorarse en silencio dejando activa la configuración
  anterior: es justo el error que llevaría a leer la planilla equivocada.
- **`max_response_bytes` debe coincidir exactamente con el límite del módulo
  de Workspace.** No es configurable en la práctica: se pide en el entorno para
  que quede explícito y asentado en la evidencia, pero cualquier otro valor se
  rechaza.
- **El token va aparte, en su propia variable, y nunca en esta estructura.**
  `resumen_seguro()` es lo único que se publica en reportes: sólo hashes de los
  identificadores, para poder probar que dos corridas usaron los mismos
  recursos sin revelar cuáles son.
- **`repr=False` en la dataclass**: evita que un `print` o un traceback
  impriman los identificadores reales.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import math
import os
import re

from .google_workspace import (
    DOCS_HOST,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    SHEETS_HOST,
)


DRIVE_HOST = "www.googleapis.com"
TOKEN_ENV = "AGENTE1_WORKSPACE_ACCESS_TOKEN"
_PREFIX = "AGENTE1_WORKSPACE_"
_REQUIRED_KEYS = frozenset(
    {
        "AGENTE1_WORKSPACE_AMBIENTE",
        "AGENTE1_WORKSPACE_SPREADSHEET_ID",
        "AGENTE1_WORKSPACE_RANGO_A1",
        "AGENTE1_WORKSPACE_FOLDER_ID",
        "AGENTE1_WORKSPACE_TEMPLATE_ID",
        "AGENTE1_WORKSPACE_TIMEOUT_S",
        "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES",
    }
)
_ALLOWED_KEYS = _REQUIRED_KEYS | {TOKEN_ENV}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
# Rango A1 completo y acotado: exige nombre de hoja y celdas inicial y final
# (`'Respuestas'!A1:I500`). No se admite un rango abierto —ni una hoja entera—
# para que la lectura tenga un techo conocido y no dependa de cuánto crezca la
# planilla.
_A1_RE = re.compile(
    r"(?:'[^'\r\n]{1,100}'|[A-Za-z0-9_ -]{1,100})!"
    r"[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*\Z"
)


class ConfiguracionWorkspaceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class ConfiguracionWorkspace:
    ambiente: str
    spreadsheet_id: str
    rango_a1: str
    folder_id: str
    template_id: str
    timeout_s: float
    max_response_bytes: int
    sheets_host: str = SHEETS_HOST
    docs_host: str = DOCS_HOST
    drive_host: str = DRIVE_HOST

    def resumen_seguro(self) -> dict[str, object]:
        """Vista publicable de la configuración: hashes en vez de identificadores.

        Es lo que se adjunta a reportes y evidencias. Permite verificar que una
        corrida usó los recursos autorizados —comparando hashes contra los
        declarados— sin exponer las URLs de la planilla ni de la carpeta.
        """

        return {
            "ambiente": self.ambiente,
            "endpoints": [self.sheets_host, self.docs_host, self.drive_host],
            "spreadsheet_ref_hash": _hash(self.spreadsheet_id),
            "folder_ref_hash": _hash(self.folder_id),
            "template_ref_hash": _hash(self.template_id),
            "range_hash": _hash(self.rango_a1),
            "timeout_s": self.timeout_s,
            "max_response_bytes": self.max_response_bytes,
        }


class TokenEntornoProvider:
    """Proveedor opt-in para un token efímero; no almacena ni muestra el valor."""

    __slots__ = ()

    def obtener_access_token(self) -> str:
        token = os.environ.get(TOKEN_ENV, "")
        if (
            not token
            or token != token.strip()
            or "\r" in token
            or "\n" in token
            or len(token.encode("utf-8")) > 8192
        ):
            raise ConfiguracionWorkspaceError("workspace_token_unavailable")
        return token

    def __repr__(self) -> str:
        return "TokenEntornoProvider(<redacted>)"


def cargar_configuracion_workspace(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionWorkspace:
    """Lee y valida el entorno. Falla con un código, nunca con datos adentro.

    `environ` inyectable para poder probar sin tocar el entorno real del
    proceso. Los mensajes de error son códigos (`workspace_config_invalid`) y
    no dicen qué variable ni con qué valor falló: ese detalle terminaría en
    logs de CI.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave for clave in env if clave.startswith(_PREFIX) and clave not in _ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionWorkspaceError("workspace_config_unknown_key")
    if any(clave not in env for clave in _REQUIRED_KEYS):
        raise ConfiguracionWorkspaceError("workspace_config_incomplete")

    try:
        ambiente = env["AGENTE1_WORKSPACE_AMBIENTE"]
        spreadsheet_id = env["AGENTE1_WORKSPACE_SPREADSHEET_ID"]
        rango_a1 = env["AGENTE1_WORKSPACE_RANGO_A1"]
        folder_id = env["AGENTE1_WORKSPACE_FOLDER_ID"]
        template_id = env["AGENTE1_WORKSPACE_TEMPLATE_ID"]
        timeout_s = float(env["AGENTE1_WORKSPACE_TIMEOUT_S"])
        max_response_bytes = int(env["AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ConfiguracionWorkspaceError("workspace_config_invalid") from None

    if (
        ambiente not in {"D2", "D3"}
        or _ID_RE.fullmatch(spreadsheet_id) is None
        or _ID_RE.fullmatch(folder_id) is None
        or _ID_RE.fullmatch(template_id) is None
        or _A1_RE.fullmatch(rango_a1) is None
        or not math.isfinite(timeout_s)
        or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        or max_response_bytes != MAX_WORKSPACE_RESPONSE_BYTES
    ):
        raise ConfiguracionWorkspaceError("workspace_config_invalid")

    return ConfiguracionWorkspace(
        ambiente=ambiente,
        spreadsheet_id=spreadsheet_id,
        rango_a1=rango_a1,
        folder_id=folder_id,
        template_id=template_id,
        timeout_s=timeout_s,
        max_response_bytes=max_response_bytes,
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
