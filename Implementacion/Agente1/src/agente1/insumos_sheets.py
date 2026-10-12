"""Adapters de la pestaña «Insumos de agentes» de la planilla D2.

`GoogleSheetsEscritorEstadoInsumos` es **el primer write a Sheets del repo**:
hasta acá el agente sólo leía `values.get`. La superficie se mantiene mínima
a propósito:

- un único endpoint, `values.update`, con `valueInputOption=RAW`;
- un único rango por llamada, `C{fila}:D{fila}` de la pestaña configurada —
  las dos columnas que la corrida posee (`estado`, `detalle`), nunca la
  columna `insumo` ni `cargado_por`, que son del productor;
- planilla y pestaña fijadas al construir, como toda allowlist del agente;
- token efímero por operación, deadline absoluto, tope de respuesta y
  errores por código, heredados de la misma tabla de traducción que usan los
  lectores.

`EscritorEstadoCsv` es la réplica offline: misma operación sobre un CSV con
la misma forma tabular, para corridas y pruebas sin red. El lector de ese
camino es el `LectorValoresCsv` de `canal_form`.

La configuración vive en el entorno bajo el prefijo `AGENTE1_INSUMOS_`: la
planilla es la misma `AGENTE1_WORKSPACE_SPREADSHEET_ID` de siempre y el rango
A1 de la pestaña va en `AGENTE1_INSUMOS_RANGO_A1` (por ejemplo
`'Insumos de agentes'!A1:D500`). El rango debe ser exactamente `A1:D<n>` con
`n >= 2`: cuatro columnas fijas y un techo de filas conocido, igual que el
rango de actividades.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    SHEETS_HOST,
    AccessTokenProvider,
    HttpsWorkspaceTransport,
    ID_RE,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
    _codigo_http,
)
from .insumos_corrida import (
    COLUMNAS_INSUMOS_AGENTES_V1,
    ESTADOS_FILA,
    MAX_DETALLE_CHARS,
    EscrituraEstadoError,
)
from .workspace_config import ConfiguracionWorkspaceError


SPREADSHEET_ID_ENV = "AGENTE1_WORKSPACE_SPREADSHEET_ID"
RANGO_INSUMOS_ENV = "AGENTE1_INSUMOS_RANGO_A1"
_INSUMOS_PREFIX = "AGENTE1_INSUMOS_"
_INSUMOS_ALLOWED_KEYS = frozenset({RANGO_INSUMOS_ENV})
# El rango de la pestaña es exactamente `A1:D<n>`: cubre las cuatro columnas
# del contrato desde el encabezado y acota cuántas filas puede sondear una
# corrida. Otro rango —más columnas, otra celda inicial— es otra pestaña.
_RANGO_INSUMOS_RE = re.compile(
    r"(?:'(?P<hoja_q>[^'\r\n]{1,100})'|(?P<hoja>[A-Za-z0-9_ -]{1,100}))"
    r"!A1:D(?P<ultima>[1-9][0-9]*)\Z"
)
# Primera fila escribible: la 1 es el encabezado del contrato tabular.
_FILA_MINIMA = 2


class GoogleSheetsEscritorEstadoInsumos:
    """Escribe `estado` y `detalle` de una fila de la pestaña de insumos.

    Cada `escribir_estado` hace un único `values.update` sobre
    `'{hoja}'!C{fila}:D{fila}` con `valueInputOption=RAW`: dos celdas, una
    fila, una operación. No hay forma de escribir otra pestaña, otra
    columna ni más de una fila por llamada — la allowlist es el propio
    método. El `RAW` garantiza además que un detalle que empiece con `=` o
    `+` quede como texto literal y nunca como fórmula.

    El `estado` debe ser uno de los tres del contrato de fila y el `detalle`
    una línea acotada: escribir cualquier otra cosa es un defecto del
    llamador y se rechaza antes de gastar la llamada HTTP.
    """

    def __init__(
        self,
        *,
        spreadsheet_id: str,
        hoja: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            not isinstance(spreadsheet_id, str)
            or ID_RE.fullmatch(spreadsheet_id) is None
            or not isinstance(hoja, str)
            or not 1 <= len(hoja) <= 100
            or "'" in hoja
            or any(ord(c) < 32 or ord(c) == 127 for c in hoja)
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración del escritor de insumos inválida")
        self._spreadsheet_id = spreadsheet_id
        self._hoja = hoja
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def escribir_estado(
        self, *, numero_fila: int, estado: str, detalle: str
    ) -> None:
        celda_estado, celda_detalle = _validar_escritura(
            numero_fila=numero_fila, estado=estado, detalle=detalle
        )
        token = self._obtener_token()
        rango = f"'{self._hoja}'!C{numero_fila}:D{numero_fila}"
        body = json.dumps(
            {
                "range": rango,
                "majorDimension": "ROWS",
                "values": [[celda_estado, celda_detalle]],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            respuesta = self._transport.request(
                method="PUT",
                host=SHEETS_HOST,
                target=(
                    f"/v4/spreadsheets/{self._spreadsheet_id}/values/"
                    f"{quote(rango, safe='')}?valueInputOption=RAW"
                ),
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                body=body,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise EscrituraEstadoError("workspace_response_too_large") from None
        except Exception:
            # `from None`: el traceback puede contener la URL con el id de la
            # planilla, y los errores terminan en el informe.
            raise EscrituraEstadoError("workspace_unavailable") from None

        if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
            raise EscrituraEstadoError("workspace_response_too_large")
        if respuesta.status != 200:
            raise EscrituraEstadoError(_codigo_http(respuesta.status))
        try:
            documento = json.loads(respuesta.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EscrituraEstadoError("workspace_response_invalid") from None
        # Se confirma el efecto, no sólo el 200: un update que no reporte las
        # dos celdas actualizadas deja la fila en estado desconocido.
        if not isinstance(documento, dict) or documento.get("updatedCells") != 2:
            raise EscrituraEstadoError("workspace_response_invalid")

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise EscrituraEstadoError("workspace_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise EscrituraEstadoError("workspace_auth_unavailable")
        return token


class EscritorEstadoCsv:
    """Réplica offline del escritor: mismo contrato sobre un CSV local.

    Reescribe el archivo completo de forma atómica (temporal + `os.replace`)
    actualizando sólo las columnas `estado` y `detalle` de la fila pedida;
    las demás filas y columnas quedan como estaban. Una fila fuera del alto
    actual es `insumos_fila_invalida`, igual que en la pestaña real.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def escribir_estado(
        self, *, numero_fila: int, estado: str, detalle: str
    ) -> None:
        celda_estado, celda_detalle = _validar_escritura(
            numero_fila=numero_fila, estado=estado, detalle=detalle
        )
        try:
            with self._path.open(encoding="utf-8", newline="") as archivo:
                filas = [list(fila) for fila in csv.reader(archivo)]
        except OSError:
            raise EscrituraEstadoError("insumos_tabla_inaccesible") from None
        if numero_fila > len(filas):
            raise EscrituraEstadoError("insumos_fila_invalida")
        fila = filas[numero_fila - 1]
        while len(fila) < len(COLUMNAS_INSUMOS_AGENTES_V1):
            fila.append("")
        fila[2], fila[3] = celda_estado, celda_detalle
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(filas)
        _escritura_atomica_texto(self._path, buffer.getvalue())


@dataclass(frozen=True, repr=False)
class ConfiguracionInsumos:
    """Planilla y pestaña de insumos, validadas de una sola vez."""

    spreadsheet_id: str
    hoja: str
    rango_a1: str
    ultima_fila: int

    def resumen_seguro(self) -> dict[str, object]:
        return {
            "spreadsheet_ref_hash": hashlib.sha256(
                self.spreadsheet_id.encode("utf-8")
            ).hexdigest(),
            "range_hash": hashlib.sha256(
                self.rango_a1.encode("utf-8")
            ).hexdigest(),
        }


def cargar_configuracion_insumos(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionInsumos:
    """Lee `AGENTE1_INSUMOS_*` + la planilla compartida, con errores cerrados.

    Mismo contrato que los otros loaders de configuración: claves propias
    desconocidas se rechazan, un entorno incompleto o mal formado falla con
    código y sin el valor adentro.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave
        for clave in env
        if clave.startswith(_INSUMOS_PREFIX) and clave not in _INSUMOS_ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionWorkspaceError("insumos_config_unknown_key")
    if not (env.get(SPREADSHEET_ID_ENV) or "").strip() or not (
        env.get(RANGO_INSUMOS_ENV) or ""
    ).strip():
        raise ConfiguracionWorkspaceError("insumos_config_incomplete")

    spreadsheet_id = env[SPREADSHEET_ID_ENV]
    rango_a1 = env[RANGO_INSUMOS_ENV]
    match = _RANGO_INSUMOS_RE.fullmatch(rango_a1)
    if (
        ID_RE.fullmatch(spreadsheet_id) is None
        or match is None
        or int(match["ultima"]) < _FILA_MINIMA
    ):
        raise ConfiguracionWorkspaceError("insumos_config_invalid")
    return ConfiguracionInsumos(
        spreadsheet_id=spreadsheet_id,
        hoja=match["hoja_q"] or match["hoja"],
        rango_a1=rango_a1,
        ultima_fila=int(match["ultima"]),
    )


def _validar_escritura(
    *, numero_fila: int, estado: str, detalle: str
) -> tuple[str, str]:
    """Contrato de las dos celdas antes de cualquier I/O.

    La fila 1 es el encabezado: no se escribe nunca. El estado es del
    vocabulario cerrado; el detalle es una línea de a lo sumo
    `MAX_DETALLE_CHARS` (enlace, código o tipo), suficiente para lo que la
    corrida escribe y corto para cualquier otra cosa.
    """

    if (
        isinstance(numero_fila, bool)
        or not isinstance(numero_fila, int)
        or numero_fila < _FILA_MINIMA
    ):
        raise EscrituraEstadoError("insumos_fila_invalida")
    if estado not in ESTADOS_FILA:
        raise EscrituraEstadoError("estado_fila_invalid")
    if (
        not isinstance(detalle, str)
        or not detalle
        or len(detalle) > MAX_DETALLE_CHARS
        or "\r" in detalle
        or "\n" in detalle
    ):
        raise EscrituraEstadoError("detalle_invalid")
    return estado, detalle


def _escritura_atomica_texto(path: Path, contenido: str) -> None:
    """Reescribe un archivo de forma atómica dentro del mismo directorio."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as temporal:
        temporal.write(contenido)
        nombre_temporal = temporal.name
    os.replace(nombre_temporal, path)
