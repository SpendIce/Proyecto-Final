import hashlib
import json

import pytest

from agente1.destinos import BORRADOR_MARKER, DestinoBorradoresError
from agente1.fuentes import COLUMNAS_GACETILLA
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    GoogleDocsDestinoBorradores,
    RespuestaHttp,
)
from agente1.procesamiento import FakeGenerator, procesar_solicitud


class TokenFijo:
    def __init__(self, token: str = "TOKEN_DOCS_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteSecuencia:
    def __init__(self, respuestas: list[RespuestaHttp | Exception]) -> None:
        self.respuestas = respuestas
        self.solicitudes: list[dict[str, object]] = []

    def request(self, **kwargs) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        respuesta = self.respuestas[len(self.solicitudes) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def crear_destino(
    respuestas: list[RespuestaHttp | Exception],
) -> tuple[GoogleDocsDestinoBorradores, TransporteSecuencia, TokenFijo]:
    transporte = TransporteSecuencia(respuestas)
    tokens = TokenFijo()
    destino = GoogleDocsDestinoBorradores(
        token_provider=tokens,
        transport=transporte,
        timeout_s=5,
    )
    return destino, transporte, tokens


def test_docs_crea_borrador_y_luego_inserta_texto_con_deadline_compartida():
    destino, transporte, tokens = crear_destino(
        [
            RespuestaHttp(200, b'{"documentId":"doc_ID-123"}'),
            RespuestaHttp(200, b'{"replies":[{}]}'),
        ]
    )
    contenido = BORRADOR_MARKER + "Contenido validado.\n"

    referencia = destino.guardar("SYN-001", contenido)

    assert referencia.tipo == "google_docs"
    assert referencia.referencia == "doc_ID-123"
    assert referencia.path is None
    assert tokens.invocaciones == 1
    assert len(transporte.solicitudes) == 2
    crear, actualizar = transporte.solicitudes
    assert crear["method"] == "POST"
    assert crear["host"] == "docs.googleapis.com"
    assert crear["target"] == "/v1/documents"
    assert crear["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer TOKEN_DOCS_SECRETO",
        "Content-Type": "application/json; charset=utf-8",
    }
    assert json.loads(crear["body"]) == {
        "title": "BORRADOR — NO PUBLICAR — SYN-001"
    }
    assert actualizar["method"] == "POST"
    assert actualizar["host"] == "docs.googleapis.com"
    assert actualizar["target"] == "/v1/documents/doc_ID-123:batchUpdate"
    assert json.loads(actualizar["body"]) == {
        "requests": [
            {"insertText": {"location": {"index": 1}, "text": contenido}}
        ]
    }
    assert crear["deadline"] == actualizar["deadline"]
    assert crear["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES


def test_docs_rechaza_contenido_sin_marker_antes_del_token_y_transporte():
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", "Texto no validado")

    assert error.value.code == "destination_contract_invalid"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (RespuestaHttp(403, b"secreto@example.invalid"), "docs_auth_denied"),
        (RespuestaHttp(429, b"secreto@example.invalid"), "docs_rate_limited"),
        (RespuestaHttp(503, b"secreto@example.invalid"), "docs_unavailable"),
        (RespuestaHttp(200, b"no-json-secreto"), "docs_response_invalid"),
        (RespuestaHttp(200, b"{}"), "docs_response_invalid"),
        (
            RespuestaHttp(200, b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "docs_response_too_large",
        ),
    ],
)
def test_docs_falla_create_sin_reintentar_ni_filtrar(respuesta, codigo):
    destino, transporte, _ = crear_destino([respuesta])

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    assert error.value.code == codigo
    assert error.value.reconciliation_ref_hash is None
    assert len(transporte.solicitudes) == 1
    assert "secreto@example.invalid" not in str(error.value)
    assert "TOKEN_DOCS_SECRETO" not in str(error.value)


@pytest.mark.parametrize(
    "segunda_respuesta",
    [
        RespuestaHttp(500, b"cuerpo-remoto-secreto@example.invalid"),
        OSError("TOKEN_DOCS_SECRETO cuerpo-remoto"),
        RespuestaHttp(200, b"no-json"),
    ],
)
def test_docs_falla_update_con_hash_de_reconciliacion_y_sin_retry(
    segunda_respuesta,
):
    destino, transporte, _ = crear_destino(
        [RespuestaHttp(200, b'{"documentId":"doc_huerfano-123"}'), segunda_respuesta]
    )

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    assert error.value.code == "docs_update_failed_orphaned"
    assert error.value.reconciliation_ref_hash == hashlib.sha256(
        b"doc_huerfano-123"
    ).hexdigest()
    assert len(transporte.solicitudes) == 2
    assert "doc_huerfano-123" not in str(error.value)


def test_core_audita_docs_huerfano_sin_id_token_contenido_o_body(tmp_path):
    destino, _, _ = crear_destino(
        [
            RespuestaHttp(200, b'{"documentId":"doc_huerfano-secreto"}'),
            RespuestaHttp(500, b"body-remoto-secreto@example.invalid"),
        ]
    )
    fila = dict(
        zip(
            COLUMNAS_GACETILLA,
            [
                "SYN-DOCS",
                "Actividad Docs",
                "Caso controlado",
                "2026-08-05",
                "Comunidad ficticia",
                "Equipo de prueba",
                "pruebas@example.invalid",
                "Dataset sintético",
                "",
            ],
            strict=True,
        )
    )

    class FuenteFalsa:
        def obtener(self, id_solicitud: str):
            return fila

    contenido = (
        "## TÍTULO\nActividad Docs\n\n"
        "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
        "Organiza: Equipo de prueba\n\n"
        "## CONTACTO\npruebas@example.invalid\n\n"
        "## BAJADA\nCaso sintético controlado.\n\n"
        "## CUERPO\nLa actividad requiere validación humana."
    )

    resultado = procesar_solicitud(
        fuente=FuenteFalsa(),
        id_solicitud="SYN-DOCS",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
        destino=destino,
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["resultado"] == "destination_failure"
    assert registro["destination_error_code"] == "docs_update_failed_orphaned"
    assert registro["reconciliation_ref_hash"]
    for secreto in [
        "doc_huerfano-secreto",
        "TOKEN_DOCS_SECRETO",
        "body-remoto",
        "pruebas@example.invalid",
        contenido,
    ]:
        assert secreto not in registro_serializado
