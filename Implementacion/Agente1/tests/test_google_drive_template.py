"""Adapter de plantilla en Drive: la copia va a la carpeta autorizada, el título
lleva la marca de borrador, y una falla al volcar el texto informa el hash de
reconciliación en vez de dejar el error sin rastro."""

import hashlib
import json

import pytest

from agente1.destinos import BORRADOR_MARKER, DestinoBorradoresError
from agente1.fuentes import COLUMNAS_GACETILLA
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    GoogleDrivePlantillaDestinoBorradores,
    RespuestaHttp,
)
from agente1.procesamiento import FakeGenerator, procesar_solicitud


class TokenFijo:
    def __init__(self, token: str = "TOKEN_DRIVE_SECRETO") -> None:
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
) -> tuple[GoogleDrivePlantillaDestinoBorradores, TransporteSecuencia, TokenFijo]:
    transporte = TransporteSecuencia(respuestas)
    tokens = TokenFijo()
    destino = GoogleDrivePlantillaDestinoBorradores(
        plantilla_id="template_ALLOWLIST-123",
        carpeta_id="folder_ALLOWLIST-456",
        token_provider=tokens,
        transport=transporte,
        timeout_s=5,
    )
    return destino, transporte, tokens


def test_drive_copia_plantilla_en_carpeta_y_luego_inserta_borrador():
    destino, transporte, tokens = crear_destino(
        [
            RespuestaHttp(200, b'{"id":"doc_copiado-789"}'),
            RespuestaHttp(200, b'{"replies":[{}]}'),
        ]
    )
    contenido = BORRADOR_MARKER + "Contenido validado.\n"

    referencia = destino.guardar("SYN-001", contenido)

    assert referencia.tipo == "google_drive_template"
    assert referencia.referencia == "doc_copiado-789"
    assert referencia.path is None
    assert tokens.invocaciones == 1
    assert len(transporte.solicitudes) == 2
    copiar, actualizar = transporte.solicitudes
    assert copiar["method"] == "POST"
    assert copiar["host"] == "www.googleapis.com"
    assert copiar["target"] == (
        "/drive/v3/files/template_ALLOWLIST-123/copy"
        "?supportsAllDrives=true&ignoreDefaultVisibility=true&fields=id"
    )
    assert copiar["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer TOKEN_DRIVE_SECRETO",
        "Content-Type": "application/json; charset=utf-8",
    }
    assert json.loads(copiar["body"]) == {
        "name": "BORRADOR — NO PUBLICAR — SYN-001",
        "parents": ["folder_ALLOWLIST-456"],
    }
    assert actualizar["method"] == "POST"
    assert actualizar["host"] == "docs.googleapis.com"
    assert actualizar["target"] == "/v1/documents/doc_copiado-789:batchUpdate"
    assert json.loads(actualizar["body"]) == {
        "requests": [
            {"insertText": {"location": {"index": 1}, "text": contenido}}
        ]
    }
    assert copiar["deadline"] == actualizar["deadline"]
    assert copiar["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES


def test_drive_rechaza_borrador_sin_marker_antes_de_token_o_red():
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", "Texto no controlado")

    assert error.value.code == "destination_contract_invalid"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_drive_rechaza_request_mayor_a_un_mib_antes_de_token_o_red():
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar(
            "SYN-001",
            BORRADOR_MARKER + ("x" * MAX_WORKSPACE_RESPONSE_BYTES),
        )

    assert error.value.code == "drive_request_too_large"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (RespuestaHttp(403, b"TOKEN_DRIVE_SECRETO"), "drive_auth_denied"),
        (RespuestaHttp(404, b"template_ALLOWLIST-123"), "drive_resource_not_found"),
        (RespuestaHttp(429, b"folder_ALLOWLIST-456"), "drive_rate_limited"),
        (RespuestaHttp(503, b"contenido-remoto"), "drive_unavailable"),
        (RespuestaHttp(200, b"no-json"), "drive_response_invalid"),
        (RespuestaHttp(200, b"{}"), "drive_response_invalid"),
        (
            RespuestaHttp(200, b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "drive_response_too_large",
        ),
    ],
)
def test_drive_falla_copy_sin_reintentar_ni_exponer_datos(respuesta, codigo):
    destino, transporte, _ = crear_destino([respuesta])

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    assert error.value.code == codigo
    assert error.value.reconciliation_ref_hash is None
    assert len(transporte.solicitudes) == 1
    for secreto in [
        "TOKEN_DRIVE_SECRETO",
        "template_ALLOWLIST-123",
        "folder_ALLOWLIST-456",
        "contenido-remoto",
    ]:
        assert secreto not in str(error.value)


@pytest.mark.parametrize(
    "segunda_respuesta",
    [
        RespuestaHttp(500, b"cuerpo-remoto-secreto@example.invalid"),
        OSError("TOKEN_DRIVE_SECRETO cuerpo-remoto"),
        RespuestaHttp(200, b"no-json"),
    ],
)
def test_drive_reporta_copia_huerfana_con_hash_y_sin_retry(segunda_respuesta):
    destino, transporte, _ = crear_destino(
        [RespuestaHttp(200, b'{"id":"doc_huerfano-789"}'), segunda_respuesta]
    )

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    assert error.value.code == "docs_update_failed_orphaned"
    assert error.value.reconciliation_ref_hash == hashlib.sha256(
        b"doc_huerfano-789"
    ).hexdigest()
    assert len(transporte.solicitudes) == 2
    for secreto in ["doc_huerfano-789", "TOKEN_DRIVE_SECRETO", "cuerpo-remoto"]:
        assert secreto not in str(error.value)


@pytest.mark.parametrize(
    ("plantilla_id", "carpeta_id"),
    [
        ("", "folder-1"),
        ("template/escape", "folder-1"),
        ("template-1", "folder?query"),
    ],
)
def test_drive_rechaza_ids_fuera_de_allowlist(plantilla_id, carpeta_id):
    with pytest.raises(ValueError, match="configuración de Google Drive inválida"):
        GoogleDrivePlantillaDestinoBorradores(
            plantilla_id=plantilla_id,
            carpeta_id=carpeta_id,
            token_provider=TokenFijo(),
        )


def test_drive_no_invoca_acciones_de_compartir_enviar_publicar_o_borrar():
    destino, transporte, _ = crear_destino(
        [
            RespuestaHttp(200, b'{"id":"doc_copiado-789"}'),
            RespuestaHttp(200, b'{"replies":[]}'),
        ]
    )

    destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    solicitudes = transporte.solicitudes
    assert [solicitud["method"] for solicitud in solicitudes] == ["POST", "POST"]
    serializado = json.dumps(solicitudes, default=str)
    for accion_prohibida in [
        "/permissions",
        "sendNotificationEmail",
        "publish",
        "shared",
        '"method": "DELETE"',
        '"method": "PATCH"',
    ]:
        assert accion_prohibida not in serializado


def test_core_audita_drive_403_con_codigo_seguro_sin_filtrar_datos(tmp_path):
    destino, _, _ = crear_destino(
        [RespuestaHttp(403, b"TOKEN_DRIVE_SECRETO template_ALLOWLIST-123")]
    )
    fila = dict(
        zip(
            COLUMNAS_GACETILLA,
            [
                "SYN-DRIVE",
                "Actividad Drive",
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
        "## TÍTULO\nActividad Drive\n\n"
        "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
        "Organiza: Equipo de prueba\n\n"
        "## CONTACTO\npruebas@example.invalid\n\n"
        "## BAJADA\nCaso sintético controlado.\n\n"
        "## CUERPO\nLa actividad requiere validación humana."
    )

    resultado = procesar_solicitud(
        fuente=FuenteFalsa(),
        id_solicitud="SYN-DRIVE",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
        destino=destino,
    )

    assert resultado.estado == "FALLIDA"
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["destination_error_code"] == "drive_auth_denied"
    for secreto in [
        "TOKEN_DRIVE_SECRETO",
        "template_ALLOWLIST-123",
        "folder_ALLOWLIST-456",
        "pruebas@example.invalid",
        contenido,
    ]:
        assert secreto not in registro_serializado


@pytest.mark.parametrize("token", ["", " TOKEN", "TOKEN\nINJECTADO"])
def test_drive_rechaza_token_invalido_sin_invocar_red(token):
    transporte = TransporteSecuencia([])
    destino = GoogleDrivePlantillaDestinoBorradores(
        plantilla_id="template-1",
        carpeta_id="folder-1",
        token_provider=TokenFijo(token),
        transport=transporte,
    )

    with pytest.raises(DestinoBorradoresError) as error:
        destino.guardar("SYN-001", BORRADOR_MARKER + "Texto.\n")

    assert error.value.code == "workspace_auth_unavailable"
    assert transporte.solicitudes == []
