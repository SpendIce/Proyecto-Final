"""Adapter Gmail del puerto `BuzonPropio` (#43): la consulta acotada contra
`/gmail/v1/users/me/messages`, la paginación con tope explícito, los adjuntos
hasheados en memoria vía `attachments.get`, el mapeo de errores HTTP a códigos
`gmail_*`, la omisión de un mensaje borrado entre lista y lectura, y la
equivalencia de resultado con el buzón `.eml` sobre el mismo conjunto de
mensajes — incluida la corrida de control de pagos completa. También fija la
regla de la auditoría D2: el host de Gmail sólo pasa con GET de lectura del
usuario `me`. Todo con transporte fake: ninguna prueba toca la red.
"""

import base64
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

import pytest

from agente1.auditoria_d2 import auditar_manifest
from agente1.buzon import BuzonPropioEml, BuzonPropioError
from agente1.buzon_gmail import GoogleGmailBuzonPropio
from agente1.google_workspace import (
    GMAIL_HOST,
    MAX_WORKSPACE_RESPONSE_BYTES,
    RespuestaHttp,
    _RespuestaDemasiadoGrande,
)
from agente1.pagos import (
    correr_control_pagos,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
)


CONSULTA = 'subject:"Pre-Inscripción" has:attachment'
FECHA_TEXTO = "Sun, 20 Sep 2026 10:00:00 +0000"
FECHA = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)

PDF_A = b"%PDF-1.4 comprobante A"
PDF_B = b"%PDF-1.4 comprobante B"
PNG_A = b"\x89PNG captura A"


def b64(datos: bytes) -> str:
    """Base64url sin padding, como lo devuelve Gmail en `data`."""
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


class TokenFijo:
    def __init__(self, token: str = "TOKEN_ULTRA_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteGmailFake:
    """Transporte fake enrutado por (método, host, path).

    Cada ruta es una `RespuestaHttp` fija o un callable que recibe los
    parámetros del query — para servir páginas distintas según `pageToken` —
    y las solicitudes quedan grabadas para verificar forma de ruta, método,
    deadline y que el adapter nunca sale de los tres endpoints de lectura.
    """

    def __init__(self, rutas: dict | None = None) -> None:
        self.rutas = rutas or {}
        self.solicitudes: list[dict[str, object]] = []

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
        self.solicitudes.append(
            {
                "method": method,
                "host": host,
                "target": target,
                "headers": headers,
                "body": body,
                "deadline": deadline,
                "max_response_bytes": max_response_bytes,
            }
        )
        path = urlsplit(target).path
        ruta = self.rutas.get((method, host, path))
        if ruta is None:
            raise AssertionError(f"request inesperado: {method} {host}{target}")
        if callable(ruta):
            return ruta(parse_qs(urlsplit(target).query))
        return ruta


def respuesta_json(documento: dict, status: int = 200) -> RespuestaHttp:
    return RespuestaHttp(
        status=status, body=json.dumps(documento).encode("utf-8")
    )


def respuesta_lista(ids: list[str], next_page: str | None = None) -> RespuestaHttp:
    documento: dict[str, object] = {
        "messages": [{"id": mid} for mid in ids],
        "resultSizeEstimate": len(ids),
    }
    if next_page is not None:
        documento["nextPageToken"] = next_page
    return respuesta_json(documento)


def respuesta_mensaje(
    *,
    message_id: str = "m1",
    remitente: str | None = "Ana Pérez <ana.perez@example.test>",
    asunto: str = "Re: Pre-Inscripción NotebookLM Nivel 2",
    fecha: str | None = FECHA_TEXTO,
    rfc_message_id: str | None = "<m1@example.test>",
    partes: list[dict] | None = None,
) -> RespuestaHttp:
    """Arma la respuesta `format=full` de un mensaje multipart/mixed."""
    headers = []
    if remitente is not None:
        headers.append({"name": "From", "value": remitente})
    if asunto is not None:
        headers.append({"name": "Subject", "value": asunto})
    if fecha is not None:
        headers.append({"name": "Date", "value": fecha})
    if rfc_message_id is not None:
        headers.append({"name": "Message-ID", "value": rfc_message_id})
    if partes is None:
        partes = [
            {
                "mimeType": "text/plain",
                "filename": "",
                "body": {"data": b64("Adjunto el comprobante.".encode()), "size": 23},
            }
        ]
    return respuesta_json(
        {
            "id": message_id,
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": headers,
                "parts": partes,
            },
        }
    )


def parte_adjunta(
    nombre: str, mime: str, att_id: str, *, datos: bytes | None = None
) -> dict:
    """Una parte declarada adjunta. `datos` alimenta la ruta del attachment."""
    return {
        "mimeType": mime,
        "filename": nombre,
        "headers": [
            {
                "name": "Content-Disposition",
                "value": f'attachment; filename="{nombre}"',
            }
        ],
        "body": {"attachmentId": att_id, "size": len(datos or b"")},
    }


def parte_texto() -> dict:
    return {
        "mimeType": "text/plain",
        "filename": "",
        "body": {"data": b64("Adjunto el comprobante.".encode()), "size": 23},
    }


def crear_buzon(
    transporte: TransporteGmailFake,
    *,
    tokens: TokenFijo | None = None,
    consulta: str = CONSULTA,
    **kwargs,
) -> tuple[GoogleGmailBuzonPropio, TokenFijo]:
    tokens = tokens or TokenFijo()
    return (
        GoogleGmailBuzonPropio(
            consulta=consulta,
            token_provider=tokens,
            transport=transporte,
            timeout_s=5,
            **kwargs,
        ),
        tokens,
    )


def rutas_basicas(
    mensajes: dict[str, RespuestaHttp], adjuntos: dict[str, RespuestaHttp] | None = None
) -> dict:
    """Rutas de un buzón sin paginar: lista + un get por mensaje + attachments."""
    rutas: dict = {}
    ids = list(mensajes)

    def lista(params: dict) -> RespuestaHttp:
        assert "pageToken" not in params
        return respuesta_lista(ids)

    rutas[("GET", GMAIL_HOST, "/gmail/v1/users/me/messages")] = lista
    for message_id, respuesta in mensajes.items():
        rutas[("GET", GMAIL_HOST, f"/gmail/v1/users/me/messages/{message_id}")] = (
            respuesta
        )
    for att_id, respuesta in (adjuntos or {}).items():
        rutas[
            (
                "GET",
                GMAIL_HOST,
                f"/gmail/v1/users/me/messages/m1/attachments/{att_id}",
            )
        ] = respuesta
    return rutas


# --- Consulta acotada y metadatos -------------------------------------------------


def test_lista_por_consulta_acotada_y_devuelve_metadatos():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("comprobante.pdf", "application/pdf", "att-1"),
                    ]
                )
            },
            {"att-1": respuesta_json({"data": b64(PDF_A), "size": len(PDF_A)})},
        )
    )
    buzon, tokens = crear_buzon(transporte)
    antes = time.monotonic()

    mensajes = buzon.listar()

    assert tokens.invocaciones == 1
    assert len(mensajes) == 1
    mensaje = mensajes[0]
    assert mensaje.remitente == "ana.perez@example.test"
    assert mensaje.asunto == "Re: Pre-Inscripción NotebookLM Nivel 2"
    assert mensaje.fecha == FECHA
    assert mensaje.message_id == "m1@example.test"
    assert len(mensaje.adjuntos) == 1
    adjunto = mensaje.adjuntos[0]
    assert adjunto.tipo == "application/pdf"
    assert adjunto.sha256 == hashlib.sha256(PDF_A).hexdigest()
    assert adjunto.nombre == "comprobante.pdf"

    lista, lectura, adjunto_get = transporte.solicitudes
    for solicitud in transporte.solicitudes:
        assert solicitud["method"] == "GET"
        assert solicitud["host"] == GMAIL_HOST
        assert solicitud["body"] is None
        assert solicitud["headers"] == {
            "Accept": "application/json",
            "Authorization": "Bearer TOKEN_ULTRA_SECRETO",
        }
        assert solicitud["deadline"] == lista["deadline"]
        assert solicitud["deadline"] >= antes + 4.9
        assert solicitud["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES
    assert urlsplit(lista["target"]).path == "/gmail/v1/users/me/messages"
    params = parse_qs(urlsplit(lista["target"]).query)
    assert params["q"] == [CONSULTA]
    assert params["maxResults"] == ["100"]
    assert params["fields"] == ["messages(id),nextPageToken"]
    assert lectura["target"].startswith("/gmail/v1/users/me/messages/m1?")
    assert parse_qs(urlsplit(lectura["target"]).query)["format"] == ["full"]
    assert adjunto_get["target"].startswith(
        "/gmail/v1/users/me/messages/m1/attachments/att-1?"
    )


def test_todos_los_requests_son_get_de_lectura_del_usuario_me():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("a.pdf", "application/pdf", "att-1"),
                    ]
                )
            },
            {"att-1": respuesta_json({"data": b64(PDF_A)})},
        )
    )
    buzon, _ = crear_buzon(transporte)

    buzon.listar()

    # Las tres formas de ruta permitidas por la auditoría, y nada más.
    formas = {urlsplit(s["target"]).path for s in transporte.solicitudes}
    assert formas == {
        "/gmail/v1/users/me/messages",
        "/gmail/v1/users/me/messages/m1",
        "/gmail/v1/users/me/messages/m1/attachments/att-1",
    }
    assert all(s["method"] == "GET" for s in transporte.solicitudes)


# --- Paginación -------------------------------------------------------------------


def test_paginacion_sigue_next_page_token_hasta_agotarlo():
    def lista(params: dict) -> RespuestaHttp:
        if "pageToken" not in params:
            return respuesta_lista(["m1"], next_page="PAGINA-2")
        assert params["pageToken"] == ["PAGINA-2"]
        return respuesta_lista(["m2"])

    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): lista,
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): respuesta_mensaje(
                message_id="m1", rfc_message_id="<m1@example.test>"
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m2"): respuesta_mensaje(
                message_id="m2", rfc_message_id="<m2@example.test>"
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    mensajes = buzon.listar()

    assert [m.message_id for m in mensajes] == ["m1@example.test", "m2@example.test"]
    listados = [
        s for s in transporte.solicitudes
        if urlsplit(s["target"]).path == "/gmail/v1/users/me/messages"
    ]
    assert len(listados) == 2


def test_paginacion_excedida_falla_cerrado_sin_leer_mensajes():
    def lista(params: dict) -> RespuestaHttp:
        return respuesta_lista(["m1"], next_page="PAGINA-2")

    transporte = TransporteGmailFake(
        {("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): lista}
    )
    buzon, _ = crear_buzon(transporte, tope_mensajes=1)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_paginacion_excedida"
    # Se cortó en el tope: ningún mensaje llegó a leerse.
    assert len(transporte.solicitudes) == 1


def test_una_pagina_que_supera_el_tope_tambien_falla():
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1", "m2", "m3"])
            )
        }
    )
    buzon, _ = crear_buzon(transporte, tope_mensajes=2)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_paginacion_excedida"


def test_exactamente_el_tope_sin_pagina_siguiente_no_falla():
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1", "m2"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): respuesta_mensaje(
                message_id="m1", rfc_message_id="<m1@example.test>"
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m2"): respuesta_mensaje(
                message_id="m2", rfc_message_id="<m2@example.test>"
            ),
        }
    )
    buzon, _ = crear_buzon(transporte, tope_mensajes=2)

    assert len(buzon.listar()) == 2


# --- Adjuntos ---------------------------------------------------------------------


def test_mensaje_sin_adjunto_no_pide_attachments_ni_partes_extra():
    transporte = TransporteGmailFake(
        rutas_basicas({"m1": respuesta_mensaje()})
    )
    buzon, _ = crear_buzon(transporte)

    mensajes = buzon.listar()

    assert mensajes[0].adjuntos == ()
    # Lista + lectura del mensaje; ningún attachments.get.
    assert len(transporte.solicitudes) == 2


def test_mensaje_simple_no_multipart_sin_adjuntos():
    """Un correo de texto plano no es multipart: el payload raíz es la pieza
    de cuerpo, sin `parts` y posiblemente sin `filename`."""
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): respuesta_json(
                {
                    "id": "m1",
                    "payload": {
                        "mimeType": "text/plain",
                        "headers": [
                            {"name": "From", "value": "ana.perez@example.test"},
                            {"name": "Subject", "value": "Re: Pre-Inscripción"},
                            {"name": "Message-ID", "value": "<m1@example.test>"},
                        ],
                        "body": {"data": b64("hola".encode()), "size": 4},
                    },
                }
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    mensaje = buzon.listar()[0]

    assert mensaje.remitente == "ana.perez@example.test"
    assert mensaje.adjuntos == ()
    assert len(transporte.solicitudes) == 2


def test_adjunto_en_linea_se_hashea_sin_request_extra():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        {
                            "mimeType": "image/png",
                            "filename": "captura.png",
                            "headers": [
                                {
                                    "name": "Content-Disposition",
                                    "value": 'inline; filename="captura.png"',
                                }
                            ],
                            "body": {"data": b64(PNG_A), "size": len(PNG_A)},
                        },
                    ]
                )
            }
        )
    )
    buzon, _ = crear_buzon(transporte)

    mensajes = buzon.listar()

    assert len(mensajes[0].adjuntos) == 1
    assert mensajes[0].adjuntos[0].sha256 == hashlib.sha256(PNG_A).hexdigest()
    assert mensajes[0].adjuntos[0].tipo == "image/png"
    assert len(transporte.solicitudes) == 2


def test_adjunto_que_supera_el_tope_de_respuesta_falla():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("grande.pdf", "application/pdf", "att-g"),
                    ]
                )
            },
            {
                "att-g": RespuestaHttp(
                    status=200, body=b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)
                )
            },
        )
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_response_too_large"


def test_transporte_que_corta_por_tope_tambien_falla_como_too_large():
    def grande(_params):
        raise _RespuestaDemasiadoGrande

    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): respuesta_mensaje(
                partes=[
                    parte_texto(),
                    parte_adjunta("grande.pdf", "application/pdf", "att-g"),
                ]
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1/attachments/att-g"): (
                grande
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_response_too_large"


def test_el_contenido_del_adjunto_no_llega_al_mensaje():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("c.pdf", "application/pdf", "att-1"),
                    ]
                )
            },
            {"att-1": respuesta_json({"data": b64(b"CONTENIDO-SECRETO-PDF")})},
        )
    )
    buzon, _ = crear_buzon(transporte)

    mensaje = buzon.listar()[0]

    serializado = repr(mensaje)
    assert "CONTENIDO-SECRETO-PDF" not in serializado
    assert not hasattr(mensaje, "cuerpo")
    assert not hasattr(mensaje.adjuntos[0], "datos")


# --- Errores y casos límite ---------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "codigo"),
    [
        (401, "gmail_auth_denied"),
        (403, "gmail_auth_denied"),
        (404, "gmail_source_not_found"),
        (429, "gmail_rate_limited"),
        (500, "gmail_unavailable"),
    ],
)
def test_errores_http_del_listado_se_mapean_sin_filtrar_cuerpo(status, codigo):
    secreto = "correo-secreto@example.invalid"
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): RespuestaHttp(
                status=status, body=secreto.encode()
            )
        }
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == codigo
    assert str(excinfo.value) == codigo
    assert secreto not in str(excinfo.value)
    assert "TOKEN_ULTRA_SECRETO" not in str(excinfo.value)


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_errores_http_en_la_lectura_del_mensaje_se_mapean(status):
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): RespuestaHttp(
                status=status, body=b"secreto"
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    esperado = {
        401: "gmail_auth_denied",
        403: "gmail_auth_denied",
        429: "gmail_rate_limited",
        500: "gmail_unavailable",
    }[status]
    assert excinfo.value.code == esperado


def test_mensaje_borrado_entre_lista_y_lectura_se_omite():
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1", "m2"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): RespuestaHttp(
                status=404, body=b"{}"
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m2"): respuesta_mensaje(
                message_id="m2", rfc_message_id="<m2@example.test>"
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    mensajes = buzon.listar()

    assert [m.message_id for m in mensajes] == ["m2@example.test"]


def test_adjunto_desaparecido_es_falla_no_hash_vacio():
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("c.pdf", "application/pdf", "att-x"),
                    ]
                )
            },
            {"att-x": RespuestaHttp(status=404, body=b"{}")},
        )
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_source_not_found"


def test_falla_de_transporte_se_redacta_y_no_se_reintenta():
    class TransporteQueFalla:
        invocaciones = 0

        def request(self, **kwargs):
            self.invocaciones += 1
            raise OSError("TOKEN_ULTRA_SECRETO correo-secreto@example.invalid")

    transporte = TransporteQueFalla()
    buzon = GoogleGmailBuzonPropio(
        consulta=CONSULTA,
        token_provider=TokenFijo(),
        transport=transporte,
        timeout_s=5,
    )

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_unavailable"
    assert str(excinfo.value) == "gmail_unavailable"
    assert transporte.invocaciones == 1


@pytest.mark.parametrize(
    "respuesta",
    [
        RespuestaHttp(status=200, body=b"no-json-secreto"),
        RespuestaHttp(status=200, body=b"[]"),
        RespuestaHttp(status=200, body=b'"texto"'),
        RespuestaHttp(status=200, body=b'{"messages": [{"id": "con barra/" }]}'),
        RespuestaHttp(status=200, body=b'{"messages": "no-lista"}'),
    ],
)
def test_respuestas_de_listado_invalidas_se_rechazan(respuesta):
    transporte = TransporteGmailFake(
        {("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): respuesta}
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_response_invalid"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"payload": "no-dict"},
        {"payload": {"mimeType": "multipart/mixed"}},
        {"payload": {"mimeType": "multipart/mixed", "headers": "no-lista"}},
        {
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [{"name": "Subject"}],
            }
        },
        {
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [],
                "parts": [{"filename": "x.pdf"}],
            }
        },
    ],
)
def test_mensajes_con_estructura_invalida_se_rechazan(payload):
    transporte = TransporteGmailFake(
        {
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): (
                respuesta_lista(["m1"])
            ),
            ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages/m1"): respuesta_json(
                {"id": "m1", **payload}
            ),
        }
    )
    buzon, _ = crear_buzon(transporte)

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_response_invalid"


def test_token_invalido_no_dispara_requests():
    for token in ("", "token\r\nX-Secreto: valor"):
        transporte = TransporteGmailFake()
        buzon = GoogleGmailBuzonPropio(
            consulta=CONSULTA,
            token_provider=TokenFijo(token),
            transport=transporte,
            timeout_s=5,
        )

        with pytest.raises(BuzonPropioError) as excinfo:
            buzon.listar()

        assert excinfo.value.code == "gmail_auth_unavailable"
        assert transporte.solicitudes == []


def test_provider_que_falla_mapea_a_auth_unavailable_sin_requests():
    class ProviderRoto:
        def obtener_access_token(self) -> str:
            raise RuntimeError("secreto")

    transporte = TransporteGmailFake()
    buzon = GoogleGmailBuzonPropio(
        consulta=CONSULTA,
        token_provider=ProviderRoto(),
        transport=transporte,
        timeout_s=5,
    )

    with pytest.raises(BuzonPropioError) as excinfo:
        buzon.listar()

    assert excinfo.value.code == "gmail_auth_unavailable"
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"consulta": ""},
        {"consulta": "q\nAuthorization: x"},
        {"consulta": "x" * 513},
        {"consulta": CONSULTA, "tope_mensajes": 0},
        {"consulta": CONSULTA, "tope_mensajes": 5_001},
        {"consulta": CONSULTA, "tope_mensajes": "500"},
        {"consulta": CONSULTA, "tamano_pagina": 0},
        {"consulta": CONSULTA, "tamano_pagina": 501},
        {"consulta": CONSULTA, "timeout_s": 0},
        {"consulta": CONSULTA, "timeout_s": 121},
        {"consulta": CONSULTA, "timeout_s": float("nan")},
    ],
)
def test_config_invalida_falla_al_construir_sin_requests(kwargs):
    transporte = TransporteGmailFake()

    with pytest.raises(ValueError, match="configuración de Gmail inválida"):
        GoogleGmailBuzonPropio(
            token_provider=TokenFijo(), transport=transporte, **kwargs
        )

    assert transporte.solicitudes == []


# --- Equivalencia con el buzón .eml ---------------------------------------------------

ASUNTO = "Pre-Inscripción NotebookLM Nivel 2"
ACTIVIDAD_ID = "EJEMPLO-NOTEBOOKLM-N2"


def escribir_eml(
    directorio: Path,
    nombre: str,
    *,
    remitente: str | None,
    asunto: str,
    message_id: str,
    fecha: datetime | None,
    adjuntos: tuple[tuple[str, str, bytes], ...] = (),
) -> None:
    mensaje = EmailMessage()
    if remitente is not None:
        mensaje["From"] = remitente
    mensaje["Subject"] = asunto
    if fecha is not None:
        mensaje["Date"] = format_datetime(fecha)
    mensaje["Message-ID"] = message_id
    mensaje.set_content("Adjunto el comprobante.")
    for nombre_adjunto, tipo, datos in adjuntos:
        principal, subtipo = tipo.split("/")
        mensaje.add_attachment(
            datos, maintype=principal, subtype=subtipo, filename=nombre_adjunto
        )
    (directorio / nombre).write_bytes(mensaje.as_bytes())


def caso_compartido(tmp_path: Path):
    """El mismo conjunto de mensajes en carpeta `.eml` y en rutas Gmail."""
    buzon_dir = tmp_path / "buzon"
    buzon_dir.mkdir()
    mensajes_eml = (
        dict(
            nombre="ana.eml",
            remitente="Ana Pérez <ana.perez@example.test>",
            asunto=f"Re: {ASUNTO}",
            message_id="<m-ana@example.test>",
            fecha=FECHA,
            adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
        ),
        dict(
            nombre="bruno.eml",
            remitente="bruno.garcia@example.test",
            asunto=f"Re: {ASUNTO}",
            message_id="<m-bruno@example.test>",
            fecha=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
            adjuntos=(("captura.png", "image/png", PNG_A),),
        ),
        dict(
            nombre="sin-adjunto.eml",
            remitente="ana.perez@example.test",
            asunto=f"Re: {ASUNTO}",
            message_id="<m-sin@example.test>",
            fecha=datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc),
            adjuntos=(),
        ),
        dict(
            nombre="desconocido.eml",
            remitente="nadie@example.test",
            asunto="Re: Consulta por otro curso",
            message_id="<m-otro@example.test>",
            fecha=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
            adjuntos=(("comprobante.pdf", "application/pdf", PDF_B),),
        ),
    )
    for spec in mensajes_eml:
        nombre = spec.pop("nombre")
        escribir_eml(buzon_dir, nombre, **spec)

    gmail_ids = ["m-ana", "m-bruno", "m-sin", "m-otro"]
    adjuntos_gmail = {
        "m-ana": ("comprobante.pdf", "application/pdf", "att-ana", PDF_A),
        "m-bruno": ("captura.png", "image/png", "att-bruno", PNG_A),
        "m-otro": ("comprobante.pdf", "application/pdf", "att-otro", PDF_B),
    }
    fechas_gmail = {
        "m-ana": FECHA_TEXTO,
        "m-bruno": "Sat, 19 Sep 2026 10:00:00 +0000",
        "m-sin": "Mon, 21 Sep 2026 10:00:00 +0000",
        "m-otro": "Fri, 18 Sep 2026 10:00:00 +0000",
    }
    metas = {
        "m-ana": ("Ana Pérez <ana.perez@example.test>", f"Re: {ASUNTO}", "<m-ana@example.test>"),
        "m-bruno": ("bruno.garcia@example.test", f"Re: {ASUNTO}", "<m-bruno@example.test>"),
        "m-sin": ("ana.perez@example.test", f"Re: {ASUNTO}", "<m-sin@example.test>"),
        "m-otro": ("nadie@example.test", "Re: Consulta por otro curso", "<m-otro@example.test>"),
    }
    rutas: dict = {
        ("GET", GMAIL_HOST, "/gmail/v1/users/me/messages"): respuesta_lista(
            gmail_ids
        )
    }
    for gmail_id in gmail_ids:
        remitente, asunto, rfc_id = metas[gmail_id]
        partes = [parte_texto()]
        if gmail_id in adjuntos_gmail:
            nombre_att, mime, att_id, datos = adjuntos_gmail[gmail_id]
            partes.append(parte_adjunta(nombre_att, mime, att_id, datos=datos))
            rutas[
                (
                    "GET",
                    GMAIL_HOST,
                    f"/gmail/v1/users/me/messages/{gmail_id}/attachments/{att_id}",
                )
            ] = respuesta_json({"data": b64(datos), "size": len(datos)})
        rutas[("GET", GMAIL_HOST, f"/gmail/v1/users/me/messages/{gmail_id}")] = (
            respuesta_mensaje(
                message_id=gmail_id,
                remitente=remitente,
                asunto=asunto,
                fecha=fechas_gmail[gmail_id],
                rfc_message_id=rfc_id,
                partes=partes,
            )
        )
    return buzon_dir, TransporteGmailFake(rutas)


def test_equivalencia_de_listar_con_el_buzon_eml(tmp_path):
    buzon_dir, transporte = caso_compartido(tmp_path)
    buzon_gmail, _ = crear_buzon(transporte)

    via_eml = BuzonPropioEml(buzon_dir).listar()
    via_gmail = buzon_gmail.listar()

    clave = lambda m: m.message_id
    assert sorted(via_eml, key=clave) == sorted(via_gmail, key=clave)


def test_la_corrida_da_el_mismo_informe_con_eml_o_con_gmail(tmp_path):
    buzon_dir, transporte = caso_compartido(tmp_path)
    buzon_gmail, _ = crear_buzon(transporte)

    plan_path = tmp_path / "plan.csv"
    plan_path.write_text(
        "campo,valor,procedencia,evidencia\n"
        f"actividad_id,{ACTIVIDAD_ID},SUPUESTO_TECNICO,\n"
        "actividad,Curso sintético,OBSERVADO_DOCUMENTO,\n"
        f"asunto_preinscripcion,{ASUNTO},SUPUESTO_TECNICO,\n"
        "fecha_inicio,2026-10-05,OBSERVADO_DOCUMENTO,\n"
        "fecha_limite_inscripcion,2026-09-29,OBSERVADO_DOCUMENTO,\n"
        "cantidad_cuotas,1,OBSERVADO_DOCUMENTO,\n"
        "cuota_1_monto,20000,OBSERVADO_DOCUMENTO,\n"
        "cuota_1_vencimiento,,DESCONOCIDO,\n",
        encoding="utf-8",
    )
    padron_path = tmp_path / "padron.csv"
    padron_path.write_text(
        "id_inscripcion,actividad_id,nombre_destinatario,email_destinatario,bonificado\n"
        f"PRE-001,{ACTIVIDAD_ID},Ana Pérez,ana.perez@example.test,no\n"
        f"PRE-002,{ACTIVIDAD_ID},Bruno García,bruno.garcia@example.test,no\n",
        encoding="utf-8",
    )
    plan = cargar_plan_pagos_csv(plan_path)
    padron = cargar_padron_csv(padron_path, actividad_id=plan.actividad_id)

    informe_eml = correr_control_pagos(
        plan=plan, padron=padron, buzon=BuzonPropioEml(buzon_dir), hoy=date(2026, 9, 22)
    )
    informe_gmail = correr_control_pagos(
        plan=plan, padron=padron, buzon=buzon_gmail, hoy=date(2026, 9, 22)
    )

    assert informe_eml == informe_gmail
    ana = next(s for s in informe_gmail.situaciones if s.id_inscripcion == "PRE-001")
    assert ana.cuotas_cubiertas == 1
    assert len(informe_gmail.no_asociadas) == 1


# --- Auditoría D2: el host de Gmail sólo para lectura del usuario `me` -----------------


def _manifest_con_calls(http_calls: list[dict]) -> dict:
    return {
        "schema_version": "security-d2-manifest-v1",
        "run_id": "D2-SYN-001",
        "mode": "offline_fake",
        "allowlist": {
            "spreadsheet": ["sheet-permitida"],
            "folder": ["folder-permitida"],
            "template": ["template-permitida"],
        },
        "sensitive": {
            "tokens": ["token-ultrasecreto"],
            "prompts": ["prompt completo privado"],
            "contacts": ["persona@fie.undef.edu.ar"],
            "bodies": ["cuerpo remoto privado"],
        },
        "resources": [
            {"kind": "spreadsheet", "id": "sheet-permitida"},
        ],
        "http_calls": http_calls,
        "logs": [],
        "remote_errors": [],
        "outputs": [
            {
                "status": "PENDIENTE_VALIDACION",
                "content": "# BORRADOR — NO PUBLICAR\n\nTexto sintético.",
            }
        ],
        "revocation_probe": {
            "simulated": True,
            "result": "BLOCKED",
            "error_code": "workspace_auth_denied",
            "draft_created": False,
        },
    }


def _check_endpoints(manifest: dict) -> bool:
    reporte = auditar_manifest(manifest)
    checks = {check["id"]: check for check in reporte["checks"]}
    return checks["no_distribution_endpoints"]["passed"]


@pytest.mark.parametrize(
    "target",
    [
        "/gmail/v1/users/me/messages",
        "/gmail/v1/users/me/messages?q=x%20has%3Aattachment&maxResults=100",
        "/gmail/v1/users/me/messages/m-abc123?format=full&fields=id,payload",
        "/gmail/v1/users/me/messages/m-abc123/attachments/att_x9-0?fields=data",
    ],
)
def test_auditoria_admite_solo_lecturas_del_buzon_propio(target):
    manifest = _manifest_con_calls(
        [{"method": "GET", "host": "gmail.googleapis.com", "target": target}]
    )

    assert _check_endpoints(manifest) is True


@pytest.mark.parametrize(
    ("method", "host", "target"),
    [
        # Envío restringido (#40): `send` sólo pasa con `gmail_send.test_list_active`
        # declarada en el manifest; esta base no la declara, así que sigue fallando.
        ("POST", "gmail.googleapis.com", "/gmail/v1/users/me/messages/send"),
        ("POST", "gmail.googleapis.com", "/gmail/v1/users/me/messages/abc/modify"),
        ("POST", "gmail.googleapis.com", "/gmail/v1/users/me/messages/abc/trash"),
        # Lectura con forma que no es del buzón propio.
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me/labels"),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me/messages/abc/modify"),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me/messages/send"),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me/threads"),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me"),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users"),
        # Otro usuario: el agente sólo lee su propio buzón (ADR 0004).
        (
            "GET",
            "gmail.googleapis.com",
            "/gmail/v1/users/cursoscomplementarios@fie.undef.edu.ar/messages",
        ),
        ("GET", "gmail.googleapis.com", "/gmail/v1/users/me/messages/../../admin"),
        ("GET", "gmail.googleapis.com", "/gmail/v2/users/me/messages"),
        ("GET", "gmail.googleapis.com", "/upload/gmail/v1/users/me/messages"),
        ("GET", "gmail.googleapis.com", "gmail/v1/users/me/messages"),
        # DELETE u otros métodos nunca.
        ("DELETE", "gmail.googleapis.com", "/gmail/v1/users/me/messages/abc"),
        ("PUT", "gmail.googleapis.com", "/gmail/v1/users/me/messages/abc"),
        # Otro host que se parece.
        ("GET", "mail.google.com", "/gmail/v1/users/me/messages"),
    ],
)
def test_auditoria_rechaza_gmail_fuera_de_lectura_propia(method, host, target):
    manifest = _manifest_con_calls(
        [{"method": method, "host": host, "target": target}]
    )

    assert _check_endpoints(manifest) is False


def test_auditoria_acepta_gmail_auth_denied_como_resultado_de_revocacion():
    """La prueba de revocación del scope `gmail.readonly` se reporta con el
    código del adapter de lectura, igual que las de Workspace."""
    manifest = _manifest_con_calls([])
    manifest["revocation_probe"]["error_code"] = "gmail_auth_denied"

    reporte = auditar_manifest(manifest)

    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["revocation_blocks"]["passed"] is True


def test_auditoria_admite_las_llamadas_que_el_adapter_realmente_hace():
    """Las solicitudes grabadas por el transporte fake durante `listar()` pasan
    el control tal cual: las rutas del adapter son las rutas permitidas."""
    transporte = TransporteGmailFake(
        rutas_basicas(
            {
                "m1": respuesta_mensaje(
                    partes=[
                        parte_texto(),
                        parte_adjunta("c.pdf", "application/pdf", "att-1"),
                    ]
                )
            },
            {"att-1": respuesta_json({"data": b64(PDF_A)})},
        )
    )
    buzon, _ = crear_buzon(transporte)
    buzon.listar()

    manifest = _manifest_con_calls(
        [
            {
                "method": s["method"],
                "host": s["host"],
                "target": s["target"],
            }
            for s in transporte.solicitudes
        ]
    )

    assert _check_endpoints(manifest) is True
