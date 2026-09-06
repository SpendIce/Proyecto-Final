"""Adapter de Sheets: encabezados exactos, filas recortadas por celdas vacías,
ids duplicados, respuestas demasiado grandes y errores de autorización."""

import json
import time

import pytest

from agente1.fuentes import COLUMNAS_GACETILLA, FuenteSolicitudesError
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    GoogleSheetsFuenteSolicitudes,
    RespuestaHttp,
)
from agente1.procesamiento import procesar_solicitud


class TokenFijo:
    def __init__(self, token: str = "TOKEN_ULTRA_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteCaptura:
    def __init__(self, respuesta: RespuestaHttp) -> None:
        self.respuesta = respuesta
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
        return self.respuesta


def respuesta_values(filas: list[list[object]]) -> RespuestaHttp:
    return RespuestaHttp(
        status=200,
        body=json.dumps({"range": "Solicitudes!A1:I20", "values": filas}).encode(),
    )


def fila_valida(id_solicitud: str = "SYN-001") -> list[str]:
    return [
        id_solicitud,
        "Actividad sintética",
        "Caso controlado",
        "2026-08-05",
        "Comunidad ficticia",
        "Equipo de prueba",
        "pruebas@example.invalid",
        "Dataset sintético",
        "Aula ficticia",
    ]


def crear_fuente(
    respuesta: RespuestaHttp,
    *,
    token_provider: TokenFijo | None = None,
    spreadsheet_id: str = "sheet_ID-123",
    rango_a1: str = "'Solicitudes SEU'!A1:I20",
) -> tuple[GoogleSheetsFuenteSolicitudes, TransporteCaptura, TokenFijo]:
    transporte = TransporteCaptura(respuesta)
    tokens = token_provider or TokenFijo()
    fuente = GoogleSheetsFuenteSolicitudes(
        spreadsheet_id=spreadsheet_id,
        rango_a1=rango_a1,
        token_provider=tokens,
        transport=transporte,
        timeout_s=5,
    )
    return fuente, transporte, tokens


def test_sheets_values_get_codifica_range_y_devuelve_fila_unica():
    fuente, transporte, tokens = crear_fuente(
        respuesta_values([list(COLUMNAS_GACETILLA), fila_valida()])
    )
    antes = time.monotonic()

    fila = fuente.obtener("SYN-001")

    assert fila == dict(zip(COLUMNAS_GACETILLA, fila_valida(), strict=True))
    assert tokens.invocaciones == 1
    solicitud = transporte.solicitudes[0]
    assert solicitud["method"] == "GET"
    assert solicitud["host"] == "sheets.googleapis.com"
    assert solicitud["target"] == (
        "/v4/spreadsheets/sheet_ID-123/values/"
        "%27Solicitudes%20SEU%27%21A1%3AI20"
        "?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    )
    assert solicitud["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer TOKEN_ULTRA_SECRETO",
    }
    assert solicitud["body"] is None
    assert solicitud["deadline"] >= antes + 4.9
    assert solicitud["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES


def test_sheets_rellena_celdas_finales_omitidas_por_values_get():
    fila_sin_lugar = fila_valida()[:-1]
    fuente, _, _ = crear_fuente(
        respuesta_values([list(COLUMNAS_GACETILLA), fila_sin_lugar])
    )

    fila = fuente.obtener("SYN-001")

    assert fila["lugar"] == ""


@pytest.mark.parametrize(
    ("filas", "codigo"),
    [
        ([list(COLUMNAS_GACETILLA[:-1]), fila_valida()[:-1]], "sheets_headers_invalid"),
        (
            [
                [*COLUMNAS_GACETILLA[:-1], "fuente"],
                fila_valida(),
            ],
            "sheets_headers_invalid",
        ),
        (
            [list(COLUMNAS_GACETILLA), [*fila_valida(), "extra"]],
            "sheets_row_invalid",
        ),
        (
            [list(COLUMNAS_GACETILLA), [*fila_valida()[:-1], 42]],
            "sheets_row_invalid",
        ),
        (
            [list(COLUMNAS_GACETILLA), fila_valida("SYN-DUP"), fila_valida("SYN-DUP")],
            "source_duplicate_id",
        ),
    ],
)
def test_sheets_rechaza_contrato_tabular_invalido(filas, codigo):
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    with pytest.raises(FuenteSolicitudesError) as error:
        fuente.obtener("SYN-DUP" if codigo == "source_duplicate_id" else "SYN-001")

    assert error.value.code == codigo


def test_sheets_solicitud_inexistente_usa_codigo_cerrado():
    fuente, _, _ = crear_fuente(
        respuesta_values([list(COLUMNAS_GACETILLA), fila_valida()])
    )

    with pytest.raises(FuenteSolicitudesError) as error:
        fuente.obtener("SYN-AUSENTE")

    assert error.value.code == "source_request_not_found"
    assert "SYN-AUSENTE" not in str(error.value)


@pytest.mark.parametrize(
    ("status", "codigo"),
    [
        (401, "workspace_auth_denied"),
        (403, "workspace_auth_denied"),
        (404, "workspace_source_not_found"),
        (429, "workspace_rate_limited"),
        (500, "workspace_unavailable"),
    ],
)
def test_sheets_mapea_http_sin_filtrar_token_o_cuerpo(status, codigo):
    secreto = "correo-secreto@example.invalid"
    fuente, _, _ = crear_fuente(
        RespuestaHttp(status=status, body=secreto.encode())
    )

    with pytest.raises(FuenteSolicitudesError) as error:
        fuente.obtener("SYN-001")

    assert error.value.code == codigo
    assert str(error.value) == codigo
    assert secreto not in str(error.value)
    assert "TOKEN_ULTRA_SECRETO" not in str(error.value)


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (RespuestaHttp(status=200, body=b"no-json-secreto"), "workspace_response_invalid"),
        (RespuestaHttp(status=200, body=b"[]"), "workspace_response_invalid"),
        (RespuestaHttp(status=200, body=b"{}"), "workspace_response_invalid"),
        (
            RespuestaHttp(status=200, body=b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "workspace_response_too_large",
        ),
    ],
)
def test_sheets_rechaza_respuesta_invalida_y_sobredimensionada(respuesta, codigo):
    fuente, _, _ = crear_fuente(respuesta)

    with pytest.raises(FuenteSolicitudesError) as error:
        fuente.obtener("SYN-001")

    assert error.value.code == codigo
    assert "no-json-secreto" not in str(error.value)


@pytest.mark.parametrize(
    ("spreadsheet_id", "rango_a1"),
    [
        ("https://evil.invalid/sheet", "Solicitudes!A1:I20"),
        ("sheet-ok", "Solicitudes!A1:I20\nAuthorization: secreto"),
        ("sheet-ok", ""),
    ],
)
def test_sheets_rechaza_config_que_podria_alterar_host_o_headers(
    spreadsheet_id, rango_a1
):
    transporte = TransporteCaptura(respuesta_values([]))

    with pytest.raises(ValueError, match="configuración de Google Sheets inválida"):
        GoogleSheetsFuenteSolicitudes(
            spreadsheet_id=spreadsheet_id,
            rango_a1=rango_a1,
            token_provider=TokenFijo(),
            transport=transporte,
        )

    assert transporte.solicitudes == []


def test_sheets_rechaza_token_vacio_o_con_inyeccion_sin_invocar_transporte():
    for token in ("", "token\r\nX-Secreto: valor"):
        transporte = TransporteCaptura(respuesta_values([]))
        fuente = GoogleSheetsFuenteSolicitudes(
            spreadsheet_id="sheet-ok",
            rango_a1="Solicitudes!A1:I20",
            token_provider=TokenFijo(token),
            transport=transporte,
        )

        with pytest.raises(FuenteSolicitudesError) as error:
            fuente.obtener("SYN-001")

        assert error.value.code == "workspace_auth_unavailable"
        if token:
            assert token not in str(error.value)
        assert transporte.solicitudes == []


def test_sheets_transport_error_se_redacta_y_no_reintenta():
    class TransporteQueFalla:
        invocaciones = 0

        def request(self, **kwargs):
            self.invocaciones += 1
            raise OSError("TOKEN_ULTRA_SECRETO correo-secreto@example.invalid")

    transporte = TransporteQueFalla()
    fuente = GoogleSheetsFuenteSolicitudes(
        spreadsheet_id="sheet-ok",
        rango_a1="Solicitudes!A1:I20",
        token_provider=TokenFijo(),
        transport=transporte,
    )

    with pytest.raises(FuenteSolicitudesError) as error:
        fuente.obtener("SYN-001")

    assert error.value.code == "workspace_unavailable"
    assert str(error.value) == "workspace_unavailable"
    assert transporte.invocaciones == 1


class GeneratorIntegracion:
    modelo = "fake-integracion"
    num_predict = None

    def __init__(self) -> None:
        self.invocaciones = 0

    def generar(self, prompt: str) -> str:
        self.invocaciones += 1
        return (
            "## TÍTULO\nActividad sintética\n\n"
            "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
            "Organiza: Equipo de prueba\nLugar: Aula ficticia\n\n"
            "## CONTACTO\npruebas@example.invalid\n\n"
            "## BAJADA\nCaso sintético controlado.\n\n"
            "## CUERPO\nLa actividad requiere validación humana."
        )


def test_sheets_se_integra_al_core_con_transporte_fake(tmp_path):
    fuente, _, _ = crear_fuente(
        respuesta_values([list(COLUMNAS_GACETILLA), fila_valida()])
    )
    generator = GeneratorIntegracion()

    resultado = procesar_solicitud(
        fuente=fuente,
        id_solicitud="SYN-001",
        directorio_salida=tmp_path / "salida",
        generator=generator,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    assert generator.invocaciones == 1


@pytest.mark.parametrize(
    ("status", "codigo"),
    [
        (401, "workspace_auth_denied"),
        (503, "workspace_unavailable"),
    ],
)
def test_core_audita_falla_operativa_sheets_sin_generar_ni_filtrar(
    tmp_path, status, codigo
):
    fuente, transporte, _ = crear_fuente(
        RespuestaHttp(
            status=status,
            body=b"TOKEN_ULTRA_SECRETO secreto@example.invalid",
        )
    )
    generator = GeneratorIntegracion()

    resultado = procesar_solicitud(
        fuente=fuente,
        id_solicitud="SYN-001",
        directorio_salida=tmp_path / "salida",
        generator=generator,
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert resultado.correlation_id
    assert generator.invocaciones == 0
    assert len(transporte.solicitudes) == 1
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["resultado"] == "source_failure"
    assert registro["source_error_code"] == codigo
    assert "TOKEN_ULTRA_SECRETO" not in registro_serializado
    assert "secreto@example.invalid" not in registro_serializado
    assert "SYN-001" not in registro_serializado
    assert not (tmp_path / "salida" / "borradores").exists()
