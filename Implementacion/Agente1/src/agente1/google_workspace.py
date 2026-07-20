from __future__ import annotations

from dataclasses import dataclass
from http.client import HTTPException, HTTPSConnection
import json
import math
import re
import time
from typing import Protocol
from urllib.parse import quote

from .fuentes import (
    COLUMNAS_GACETILLA,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)


SHEETS_HOST = "sheets.googleapis.com"
MAX_WORKSPACE_RESPONSE_BYTES = 1_048_576
MAX_WORKSPACE_TIMEOUT_S = 120.0
ID_RE = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


class AccessTokenProvider(Protocol):
    def obtener_access_token(self) -> str: ...


@dataclass(frozen=True)
class RespuestaHttp:
    status: int
    body: bytes


class TransporteHttp(Protocol):
    def request(
        self,
        *,
        method: str,
        host: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        deadline: float,
        max_response_bytes: int,
    ) -> RespuestaHttp: ...


class GoogleSheetsFuenteSolicitudes(FuenteSolicitudes):
    def __init__(
        self,
        *,
        spreadsheet_id: str,
        rango_a1: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            not isinstance(spreadsheet_id, str)
            or ID_RE.fullmatch(spreadsheet_id) is None
            or not isinstance(rango_a1, str)
            or not 1 <= len(rango_a1) <= 256
            or any(ord(caracter) < 32 or ord(caracter) == 127 for caracter in rango_a1)
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Google Sheets inválida")
        self._spreadsheet_id = spreadsheet_id
        self._rango_a1 = rango_a1
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def obtener(self, id_solicitud: str) -> dict[str, str]:
        if not isinstance(id_solicitud, str) or ID_SOLICITUD_RE.fullmatch(
            id_solicitud
        ) is None:
            raise FuenteSolicitudesError("source_request_invalid")
        token = self._obtener_token()
        target = (
            f"/v4/spreadsheets/{self._spreadsheet_id}/values/"
            f"{quote(self._rango_a1, safe='')}"
            "?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
        )
        try:
            respuesta = self._transport.request(
                method="GET",
                host=SHEETS_HOST,
                target=target,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                body=None,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise FuenteSolicitudesError("workspace_response_too_large") from None
        except Exception:
            raise FuenteSolicitudesError("workspace_unavailable") from None

        if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
            raise FuenteSolicitudesError("workspace_response_too_large")
        if respuesta.status != 200:
            raise FuenteSolicitudesError(_codigo_http(respuesta.status))
        try:
            documento = json.loads(respuesta.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise FuenteSolicitudesError("workspace_response_invalid") from None
        if not isinstance(documento, dict) or not isinstance(
            documento.get("values"), list
        ):
            raise FuenteSolicitudesError("workspace_response_invalid")
        return _buscar_fila(documento["values"], id_solicitud)

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise FuenteSolicitudesError("workspace_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise FuenteSolicitudesError("workspace_auth_unavailable")
        return token


class HttpsWorkspaceTransport:
    def request(
        self,
        *,
        method: str,
        host: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        deadline: float,
        max_response_bytes: int,
    ) -> RespuestaHttp:
        connection: HTTPSConnection | None = None
        try:
            connection = HTTPSConnection(host, 443, timeout=_tiempo_restante(deadline))
            connection.request(method, target, body=body, headers=headers)
            _ajustar_timeout(connection, deadline)
            response = connection.getresponse()
            contenido = bytearray()
            while len(contenido) <= max_response_bytes:
                _ajustar_timeout(connection, deadline)
                restante = max_response_bytes + 1 - len(contenido)
                chunk = response.read1(min(65_536, restante))
                if not chunk:
                    break
                contenido.extend(chunk)
            if len(contenido) > max_response_bytes:
                raise _RespuestaDemasiadoGrande
            return RespuestaHttp(status=response.status, body=bytes(contenido))
        except (HTTPException, OSError, TimeoutError):
            raise RuntimeError("workspace_unavailable") from None
        finally:
            if connection is not None:
                connection.close()


class _RespuestaDemasiadoGrande(Exception):
    pass


def _buscar_fila(values: list[object], id_solicitud: str) -> dict[str, str]:
    if not values or not isinstance(values[0], list):
        raise FuenteSolicitudesError("sheets_headers_invalid")
    encabezados = values[0]
    if tuple(encabezados) != COLUMNAS_GACETILLA:
        raise FuenteSolicitudesError("sheets_headers_invalid")

    filas_por_id: dict[str, dict[str, str]] = {}
    for fila_cruda in values[1:]:
        if (
            not isinstance(fila_cruda, list)
            or len(fila_cruda) > len(COLUMNAS_GACETILLA)
            or any(not isinstance(valor, str) for valor in fila_cruda)
        ):
            raise FuenteSolicitudesError("sheets_row_invalid")
        fila_completa = [
            *fila_cruda,
            *([""] * (len(COLUMNAS_GACETILLA) - len(fila_cruda))),
        ]
        if not any(fila_completa):
            continue
        identificador = fila_completa[0]
        if ID_SOLICITUD_RE.fullmatch(identificador) is None:
            raise FuenteSolicitudesError("sheets_row_invalid")
        if identificador in filas_por_id:
            raise FuenteSolicitudesError("source_duplicate_id")
        filas_por_id[identificador] = dict(
            zip(COLUMNAS_GACETILLA, fila_completa, strict=True)
        )
    try:
        return filas_por_id[id_solicitud]
    except KeyError:
        raise FuenteSolicitudesError("source_request_not_found") from None


def _codigo_http(status: int) -> str:
    if status in {401, 403}:
        return "workspace_auth_denied"
    if status == 404:
        return "workspace_source_not_found"
    if status == 429:
        return "workspace_rate_limited"
    return "workspace_unavailable"


def _tiempo_restante(deadline: float) -> float:
    restante = deadline - time.monotonic()
    if restante <= 0:
        raise TimeoutError
    return restante


def _ajustar_timeout(connection: HTTPSConnection, deadline: float) -> None:
    restante = _tiempo_restante(deadline)
    connection.timeout = restante
    if connection.sock is not None:
        connection.sock.settimeout(restante)
