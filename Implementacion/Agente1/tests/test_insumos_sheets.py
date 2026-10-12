"""Escritor de estado de la pestaña «Insumos de agentes» y su configuración.

Es el primer write a Sheets del repo: un único `values.update` por fila sobre
`C{n}:D{n}`, `valueInputOption=RAW`, token por operación, allowlist de
planilla+pestaña fijada al construir y errores por código sin contenido.
"""

import csv
import json
from pathlib import Path
from urllib.parse import unquote

import pytest

from agente1.google_workspace import RespuestaHttp
from agente1.insumos_corrida import EscrituraEstadoError
from agente1.insumos_sheets import (
    EscritorEstadoCsv,
    GoogleSheetsEscritorEstadoInsumos,
    cargar_configuracion_insumos,
)
from agente1.workspace_config import ConfiguracionWorkspaceError


class TokenFijo:
    def __init__(self, token: str = "TOKEN_ULTRA_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TokenQueFalla:
    def obtener_access_token(self) -> str:
        raise RuntimeError("sin token")


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


class TransporteQueFalla:
    def request(self, **kwargs):
        raise OSError("connection reset")


def respuesta_update_ok() -> RespuestaHttp:
    return RespuestaHttp(
        status=200,
        body=json.dumps(
            {
                "spreadsheetId": "s1",
                "updatedRange": "'Insumos de agentes'!C2:D2",
                "updatedRows": 1,
                "updatedColumns": 2,
                "updatedCells": 2,
            }
        ).encode("utf-8"),
    )


def escritor(transport) -> GoogleSheetsEscritorEstadoInsumos:
    return GoogleSheetsEscritorEstadoInsumos(
        spreadsheet_id="planilla_d2",
        hoja="Insumos de agentes",
        token_provider=TokenFijo(),
        transport=transport,
    )


def test_escritura_hace_un_values_update_acotado() -> None:
    transporte = TransporteCaptura(respuesta_update_ok())
    escritor(transporte).escribir_estado(
        numero_fila=7, estado="rechazado", detalle="producer_not_allowed"
    )

    (solicitud,) = transporte.solicitudes
    assert solicitud["method"] == "PUT"
    assert solicitud["host"] == "sheets.googleapis.com"
    target = unquote(solicitud["target"])
    assert "/v4/spreadsheets/planilla_d2/values/'Insumos de agentes'!C7:D7" in target
    assert "valueInputOption=RAW" in solicitud["target"]
    cuerpo = json.loads(solicitud["body"].decode("utf-8"))
    assert cuerpo["values"] == [["rechazado", "producer_not_allowed"]]
    assert cuerpo["range"] == "'Insumos de agentes'!C7:D7"
    assert solicitud["headers"]["Authorization"] == "Bearer TOKEN_ULTRA_SECRETO"


def test_token_se_pide_por_operacion() -> None:
    transporte = TransporteCaptura(respuesta_update_ok())
    token = TokenFijo()
    w = GoogleSheetsEscritorEstadoInsumos(
        spreadsheet_id="planilla_d2",
        hoja="Insumos de agentes",
        token_provider=token,
        transport=transporte,
    )
    w.escribir_estado(numero_fila=2, estado="rechazado", detalle="insumo_ausente")
    w.escribir_estado(numero_fila=3, estado="aceptado sin flujo", detalle="evento")

    assert token.invocaciones == 2


def test_contenido_escrito_nunca_lleva_payload() -> None:
    transporte = TransporteCaptura(respuesta_update_ok())
    escritor(transporte).escribir_estado(
        numero_fila=2,
        estado="borrador generado",
        detalle="https://docs.google.com/document/d/doc-1/edit",
    )

    cuerpo = json.loads(transporte.solicitudes[0]["body"].decode("utf-8"))
    serializado = json.dumps(cuerpo)
    assert "payload" not in serializado
    assert "provenance" not in serializado


@pytest.mark.parametrize(
    "numero_fila,estado,detalle,codigo",
    [
        (1, "rechazado", "x", "insumos_fila_invalida"),
        (0, "rechazado", "x", "insumos_fila_invalida"),
        ("2", "rechazado", "x", "insumos_fila_invalida"),
        (2, "publicado", "x", "estado_fila_invalid"),
        (2, "rechazado", "", "detalle_invalid"),
        (2, "rechazado", "linea\nrota", "detalle_invalid"),
        (2, "rechazado", "x" * 501, "detalle_invalid"),
    ],
)
def test_escritura_fuera_de_contrato_se_rechaza_sin_red(
    numero_fila, estado, detalle, codigo
) -> None:
    transporte = TransporteCaptura(respuesta_update_ok())
    with pytest.raises(EscrituraEstadoError) as exc:
        escritor(transporte).escribir_estado(
            numero_fila=numero_fila, estado=estado, detalle=detalle
        )
    assert exc.value.code == codigo
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    "status,codigo",
    [
        (401, "workspace_auth_denied"),
        (403, "workspace_auth_denied"),
        (404, "workspace_source_not_found"),
        (429, "workspace_rate_limited"),
        (500, "workspace_unavailable"),
    ],
)
def test_errores_http_se_traducen_a_codigos_cerrados(status, codigo) -> None:
    transporte = TransporteCaptura(RespuestaHttp(status=status, body=b"{}"))
    with pytest.raises(EscrituraEstadoError) as exc:
        escritor(transporte).escribir_estado(
            numero_fila=2, estado="rechazado", detalle="x"
        )
    assert exc.value.code == codigo


def test_respuesta_sin_updatedcells_es_invalida() -> None:
    transporte = TransporteCaptura(
        RespuestaHttp(status=200, body=b'{"updatedCells": 1}')
    )
    with pytest.raises(EscrituraEstadoError) as exc:
        escritor(transporte).escribir_estado(
            numero_fila=2, estado="rechazado", detalle="x"
        )
    assert exc.value.code == "workspace_response_invalid"


def test_falla_de_transporte_es_unavailable() -> None:
    with pytest.raises(EscrituraEstadoError) as exc:
        escritor(TransporteQueFalla()).escribir_estado(
            numero_fila=2, estado="rechazado", detalle="x"
        )
    assert exc.value.code == "workspace_unavailable"


def test_falla_de_token_es_auth_unavailable() -> None:
    w = GoogleSheetsEscritorEstadoInsumos(
        spreadsheet_id="planilla_d2",
        hoja="Insumos de agentes",
        token_provider=TokenQueFalla(),
        transport=TransporteCaptura(respuesta_update_ok()),
    )
    with pytest.raises(EscrituraEstadoError) as exc:
        w.escribir_estado(numero_fila=2, estado="rechazado", detalle="x")
    assert exc.value.code == "workspace_auth_unavailable"


def test_construccion_rechaza_config_invalida() -> None:
    with pytest.raises(ValueError):
        GoogleSheetsEscritorEstadoInsumos(
            spreadsheet_id="id con espacios",
            hoja="Insumos de agentes",
            token_provider=TokenFijo(),
            transport=TransporteCaptura(respuesta_update_ok()),
        )
    with pytest.raises(ValueError):
        GoogleSheetsEscritorEstadoInsumos(
            spreadsheet_id="planilla_d2",
            hoja="hoja'con'comillas",
            token_provider=TokenFijo(),
            transport=TransporteCaptura(respuesta_update_ok()),
        )


# --- Escritor CSV offline -----------------------------------------------------


def test_escritor_csv_actualiza_solo_estado_y_detalle(tmp_path: Path) -> None:
    csv_path = tmp_path / "insumos.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["insumo", "cargado_por", "estado", "detalle"])
        writer.writerow(["{}", "ope-1", "", ""])
        writer.writerow(["{}", "ope-2", "", ""])

    EscritorEstadoCsv(csv_path).escribir_estado(
        numero_fila=3, estado="aceptado sin flujo", detalle="evento"
    )

    with csv_path.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[1] == ["{}", "ope-1", "", ""]
    assert filas[2] == ["{}", "ope-2", "aceptado sin flujo", "evento"]


def test_escritor_csv_rechaza_fila_fuera_del_alto(tmp_path: Path) -> None:
    csv_path = tmp_path / "insumos.csv"
    csv_path.write_text("insumo,cargado_por,estado,detalle\n{}", encoding="utf-8")
    with pytest.raises(EscrituraEstadoError) as exc:
        EscritorEstadoCsv(csv_path).escribir_estado(
            numero_fila=9, estado="rechazado", detalle="x"
        )
    assert exc.value.code == "insumos_fila_invalida"


# --- Configuración por entorno -------------------------------------------------


def entorno_insumos(**extras) -> dict[str, str]:
    base = {
        "AGENTE1_WORKSPACE_SPREADSHEET_ID": "planilla_d2",
        "AGENTE1_INSUMOS_RANGO_A1": "'Insumos de agentes'!A1:D200",
    }
    base.update(extras)
    return base


def test_configuracion_insumos_acepta_rango_acotado() -> None:
    config = cargar_configuracion_insumos(entorno_insumos())

    assert config.spreadsheet_id == "planilla_d2"
    assert config.hoja == "Insumos de agentes"
    assert config.rango_a1 == "'Insumos de agentes'!A1:D200"
    assert config.ultima_fila == 200
    resumen = config.resumen_seguro()
    assert "planilla_d2" not in json.dumps(resumen)


def test_configuracion_insumos_incompleta() -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_configuracion_insumos({"AGENTE1_WORKSPACE_SPREADSHEET_ID": "x"})
    assert exc.value.code == "insumos_config_incomplete"


@pytest.mark.parametrize(
    "rango",
    [
        "'Insumos de agentes'!A1:E200",   # más columnas: otra pestaña
        "'Insumos de agentes'!B2:D200",   # no arranca en A1
        "'Insumos de agentes'!A1:D1",     # sin espacio para datos
        "A1:D200",                        # sin nombre de pestaña
        "'Insumos de agentes'!A:D",       # rango abierto
    ],
)
def test_configuracion_insumos_rechaza_rangos_fuera_del_contrato(rango) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_configuracion_insumos(entorno_insumos(AGENTE1_INSUMOS_RANGO_A1=rango))
    assert exc.value.code == "insumos_config_invalid"


def test_configuracion_insumos_rechaza_claves_desconocidas() -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_configuracion_insumos(
            entorno_insumos(AGENTE1_INSUMOS_OTRA_CLAVE="x")
        )
    assert exc.value.code == "insumos_config_unknown_key"
