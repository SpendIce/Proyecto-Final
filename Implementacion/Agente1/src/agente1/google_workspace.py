from __future__ import annotations

from dataclasses import dataclass
import hashlib
from http.client import HTTPException, HTTPSConnection
import json
import math
import re
import time
from typing import Protocol
from urllib.parse import quote

from .destinos import (
    DestinoBorradores,
    DestinoBorradoresError,
    ReferenciaBorrador,
    validar_entrada_borrador,
)
from .fuentes import (
    COLUMNAS_GACETILLA,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)


SHEETS_HOST = "sheets.googleapis.com"
DOCS_HOST = "docs.googleapis.com"
DRIVE_HOST = "www.googleapis.com"
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


class GoogleDocsDestinoBorradores(DestinoBorradores):
    def __init__(
        self,
        *,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Google Docs inválida")
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        validar_entrada_borrador(id_solicitud, contenido)
        token = self._obtener_token()
        deadline = time.monotonic() + self._timeout_s
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        create_body = json.dumps(
            {"title": f"BORRADOR — NO PUBLICAR — {id_solicitud}"},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            create_response = self._transport.request(
                method="POST",
                host=DOCS_HOST,
                target="/v1/documents",
                headers=headers,
                body=create_body,
                deadline=deadline,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise DestinoBorradoresError("docs_response_too_large") from None
        except Exception:
            raise DestinoBorradoresError("docs_unavailable") from None
        documento = _validar_create_docs(create_response)
        document_id = documento["documentId"]
        reconciliation_ref_hash = hashlib.sha256(document_id.encode("utf-8")).hexdigest()
        update_body = json.dumps(
            {
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": contenido,
                        }
                    }
                ]
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            update_response = self._transport.request(
                method="POST",
                host=DOCS_HOST,
                target=f"/v1/documents/{document_id}:batchUpdate",
                headers=headers,
                body=update_body,
                deadline=deadline,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
            _validar_update_docs(update_response)
        except Exception:
            raise DestinoBorradoresError(
                "docs_update_failed_orphaned",
                reconciliation_ref_hash=reconciliation_ref_hash,
            ) from None
        return ReferenciaBorrador(
            tipo="google_docs",
            referencia=document_id,
        )

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise DestinoBorradoresError("workspace_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise DestinoBorradoresError("workspace_auth_unavailable")
        return token


class GoogleDrivePlantillaDestinoBorradores(DestinoBorradores):
    """Copia una plantilla allowlisted y antepone un borrador en la copia."""

    def __init__(
        self,
        *,
        plantilla_id: str,
        carpeta_id: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            not isinstance(plantilla_id, str)
            or ID_RE.fullmatch(plantilla_id) is None
            or not isinstance(carpeta_id, str)
            or ID_RE.fullmatch(carpeta_id) is None
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Google Drive inválida")
        self._plantilla_id = plantilla_id
        self._carpeta_id = carpeta_id
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        validar_entrada_borrador(id_solicitud, contenido)
        update_body = json.dumps(
            {
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": contenido,
                        }
                    }
                ]
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(update_body) > MAX_WORKSPACE_RESPONSE_BYTES:
            raise DestinoBorradoresError("drive_request_too_large")
        token = self._obtener_token()
        deadline = time.monotonic() + self._timeout_s
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        copy_body = json.dumps(
            {
                "name": f"BORRADOR — NO PUBLICAR — {id_solicitud}",
                "parents": [self._carpeta_id],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            copy_response = self._transport.request(
                method="POST",
                host=DRIVE_HOST,
                target=(
                    f"/drive/v3/files/{self._plantilla_id}/copy"
                    "?supportsAllDrives=true&ignoreDefaultVisibility=true&fields=id"
                ),
                headers=headers,
                body=copy_body,
                deadline=deadline,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise DestinoBorradoresError("drive_response_too_large") from None
        except Exception:
            raise DestinoBorradoresError("drive_unavailable") from None
        copia = _validar_copy_drive(copy_response)
        document_id = copia["id"]
        reconciliation_ref_hash = hashlib.sha256(document_id.encode("utf-8")).hexdigest()
        try:
            update_response = self._transport.request(
                method="POST",
                host=DOCS_HOST,
                target=f"/v1/documents/{document_id}:batchUpdate",
                headers=headers,
                body=update_body,
                deadline=deadline,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
            _validar_update_docs(update_response)
        except Exception:
            raise DestinoBorradoresError(
                "docs_update_failed_orphaned",
                reconciliation_ref_hash=reconciliation_ref_hash,
            ) from None
        return ReferenciaBorrador(
            tipo="google_drive_template",
            referencia=document_id,
        )

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise DestinoBorradoresError("workspace_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise DestinoBorradoresError("workspace_auth_unavailable")
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


def _validar_create_docs(respuesta: RespuestaHttp) -> dict[str, str]:
    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise DestinoBorradoresError("docs_response_too_large")
    if not 200 <= respuesta.status < 300:
        raise DestinoBorradoresError(_codigo_docs_create(respuesta.status))
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DestinoBorradoresError("docs_response_invalid") from None
    if (
        not isinstance(documento, dict)
        or not isinstance(documento.get("documentId"), str)
        or ID_RE.fullmatch(documento["documentId"]) is None
    ):
        raise DestinoBorradoresError("docs_response_invalid")
    return documento


def _validar_copy_drive(respuesta: RespuestaHttp) -> dict[str, str]:
    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise DestinoBorradoresError("drive_response_too_large")
    if not 200 <= respuesta.status < 300:
        if respuesta.status in {401, 403}:
            codigo = "drive_auth_denied"
        elif respuesta.status == 404:
            codigo = "drive_resource_not_found"
        elif respuesta.status == 429:
            codigo = "drive_rate_limited"
        else:
            codigo = "drive_unavailable"
        raise DestinoBorradoresError(codigo)
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DestinoBorradoresError("drive_response_invalid") from None
    if (
        not isinstance(documento, dict)
        or not isinstance(documento.get("id"), str)
        or ID_RE.fullmatch(documento["id"]) is None
    ):
        raise DestinoBorradoresError("drive_response_invalid")
    return documento


def _validar_update_docs(respuesta: RespuestaHttp) -> None:
    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise DestinoBorradoresError("docs_response_too_large")
    if not 200 <= respuesta.status < 300:
        raise DestinoBorradoresError("docs_update_failed_orphaned")
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DestinoBorradoresError("docs_update_failed_orphaned") from None
    if not isinstance(documento, dict):
        raise DestinoBorradoresError("docs_update_failed_orphaned")


def _codigo_docs_create(status: int) -> str:
    if status in {401, 403}:
        return "docs_auth_denied"
    if status == 429:
        return "docs_rate_limited"
    return "docs_unavailable"


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
