"""Transporte HTTP de `/v1`: pedidos que arma y traducción de fallas.

Corre contra un servidor HTTP local en memoria (127.0.0.1, puerto efímero):
sin red externa ni credenciales. La prueba contra el mock Prism del contrato
vive en `contrato/`."""

from __future__ import annotations

import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlsplit

import pytest

from agente1.historia_viva import Aporte, ConsultaFragmentos, HistoriaVivaError
from agente1.historia_viva_http import (
    ConfiguracionHistoriaVivaError,
    TransporteHistoriaVivaHttp,
    cargar_configuracion_historia_viva,
    construir_cliente_historia_viva,
)

TOKEN = "hv_0123abcd_" + "a" * 43


class Servidor:
    """Responde con lo que fija cada prueba y registra lo que recibió."""

    def __init__(self) -> None:
        self.status = 200
        self.cuerpo: object = {"total": 0, "limite": 10, "fragmentos": []}
        self.cabeceras = {"Content-Type": "application/json"}
        self.recibidos: list[dict] = []
        servidor = self

        class Manejador(BaseHTTPRequestHandler):
            def _responder(self) -> None:
                largo = int(self.headers.get("Content-Length") or 0)
                servidor.recibidos.append(
                    {
                        "metodo": self.command,
                        "ruta": self.path,
                        "cabeceras": dict(self.headers),
                        "cuerpo": self.rfile.read(largo) if largo else b"",
                    }
                )
                datos = (
                    servidor.cuerpo
                    if isinstance(servidor.cuerpo, bytes)
                    else json.dumps(servidor.cuerpo).encode("utf-8")
                )
                self.send_response(servidor.status)
                for nombre, valor in servidor.cabeceras.items():
                    self.send_header(nombre, valor)
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)

            do_GET = _responder
            do_POST = _responder

            def log_message(self, *args: object) -> None:
                pass

        self._http = HTTPServer(("127.0.0.1", 0), Manejador)
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}"
        self._hilo = threading.Thread(
            target=self._http.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self._hilo.start()

    def cerrar(self) -> None:
        self._http.shutdown()
        self._http.server_close()


@pytest.fixture
def servidor():
    s = Servidor()
    yield s
    s.cerrar()


def transporte(servidor: Servidor, **kwargs) -> TransporteHistoriaVivaHttp:
    return TransporteHistoriaVivaHttp(servidor.url, lambda: TOKEN, **kwargs)


def error(status: int, codigo: str, **cabeceras: str) -> tuple[int, dict, dict]:
    return (
        status,
        {"codigo": codigo, "mensaje": "texto remoto que no debe salir", "solicitud_id": "req_01ABC"},
        {"Content-Type": "application/json", **cabeceras},
    )


def aporte(**cambios: object) -> Aporte:
    campos = {
        "clave_idempotencia": "clave-0001",
        "tipo_contenido": "gacetilla",
        "canal": "ninguno",
        "titulo": "Título",
        "cuerpo": "Cuerpo",
        "piezas_fuente": ("pza_001",),
        "fragmentos_fuente": ("frg_001",),
    }
    campos.update(cambios)
    return Aporte(**campos)


# --- Pedidos ------------------------------------------------------------------


def test_la_busqueda_manda_solo_los_parametros_del_contrato(servidor: Servidor) -> None:
    transporte(servidor).get_fragmentos(
        ConsultaFragmentos(
            texto="convenio UTN",
            desde=date(2015, 1, 1),
            hasta=date(2019, 12, 31),
            tipo="convenio",
            limite=5,
        ),
        timeout=5,
    )

    (pedido,) = servidor.recibidos
    partes = urlsplit(pedido["ruta"])
    assert partes.path == "/v1/fragmentos"
    assert dict(parse_qsl(partes.query)) == {
        "q": "convenio UTN",
        "desde": "2015-01-01",
        "hasta": "2019-12-31",
        "tipo": "convenio",
        "limite": "5",
    }
    assert pedido["cabeceras"]["Authorization"] == f"Bearer {TOKEN}"


def test_el_aporte_lleva_idempotency_key_y_canal_nulo(servidor: Servidor) -> None:
    servidor.status = 201
    servidor.cuerpo = {"aporte_id": "apt_1"}

    respuesta = transporte(servidor).post_aporte(aporte(), timeout=5)

    (pedido,) = servidor.recibidos
    assert pedido["metodo"] == "POST"
    assert pedido["cabeceras"]["Idempotency-Key"] == "clave-0001"
    assert json.loads(pedido["cuerpo"]) == {
        "titulo": "Título",
        "cuerpo": "Cuerpo",
        "tipo_contenido": "gacetilla",
        "canal": None,
        "piezas_fuente": ["pza_001"],
        "fragmentos_fuente": ["frg_001"],
    }
    assert respuesta.repetido is False


def test_un_200_en_el_aporte_es_una_clave_repetida(servidor: Servidor) -> None:
    servidor.cuerpo = {"aporte_id": "apt_1"}

    assert transporte(servidor).post_aporte(aporte(), timeout=5).repetido is True


def test_el_id_de_pieza_no_escapa_del_path(servidor: Servidor) -> None:
    servidor.cuerpo = {}

    transporte(servidor).get_pieza("pza_1/../../admin", timeout=5)

    assert servidor.recibidos[0]["ruta"] == "/v1/piezas/pza_1%2F..%2F..%2Fadmin"


def test_el_token_se_pide_en_cada_envio(servidor: Servidor) -> None:
    tokens = iter([TOKEN, "hv_ffffffff_" + "b" * 43])
    t = TransporteHistoriaVivaHttp(servidor.url, lambda: next(tokens))

    t.get_pieza("pza_1", timeout=5)
    t.get_pieza("pza_1", timeout=5)

    assert [r["cabeceras"]["Authorization"] for r in servidor.recibidos] == [
        f"Bearer {TOKEN}",
        "Bearer hv_ffffffff_" + "b" * 43,
    ]


@pytest.mark.parametrize("token", ["", "hv_1\r\nX-Inyectada: 1", "dos partes"])
def test_un_token_inutilizable_no_sale(servidor: Servidor, token: str) -> None:
    t = TransporteHistoriaVivaHttp(servidor.url, lambda: token)

    with pytest.raises(HistoriaVivaError) as excinfo:
        t.get_pieza("pza_1", timeout=5)

    assert excinfo.value.code == "historia_viva_unauthorized"
    assert servidor.recibidos == []


@pytest.mark.parametrize(
    "extra",
    [
        {"Authorization": "Bearer otro"},
        {"idempotency-key": "x"},
        {"Prefer": "code=200\r\nX: 1"},
        {"Mal nombre": "x"},
    ],
)
def test_las_cabeceras_extra_no_pisan_las_propias(extra: dict) -> None:
    with pytest.raises(ValueError):
        TransporteHistoriaVivaHttp("http://127.0.0.1:4010", lambda: TOKEN, cabeceras_extra=extra)


def test_las_cabeceras_extra_viajan(servidor: Servidor) -> None:
    transporte(servidor, cabeceras_extra={"Prefer": "code=200, example=convenio"}).get_pieza(
        "pza_1", timeout=5
    )

    assert servidor.recibidos[0]["cabeceras"]["Prefer"] == "code=200, example=convenio"


@pytest.mark.parametrize(
    "base_url",
    ["ftp://hv.local", "http://", "http://hv.local/?x=1", "http://usuario@hv.local", "hv.local"],
)
def test_una_base_url_invalida_se_rechaza(base_url: str) -> None:
    with pytest.raises(ValueError):
        TransporteHistoriaVivaHttp(base_url, lambda: TOKEN)


# --- Traducción de fallas -----------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "codigo", "esperado"),
    [
        (400, "parametros_invalidos", "historia_viva_request_invalid"),
        (400, "idempotency_key_reutilizada", "historia_viva_request_invalid"),
        (400, "fuente_inexistente", "historia_viva_request_invalid"),
        (404, "ruta_inexistente", "historia_viva_request_invalid"),
        (401, "token_invalido", "historia_viva_unauthorized"),
        (403, "operacion_no_permitida", "historia_viva_forbidden"),
        (422, "aporte_rechazado", "historia_viva_aporte_rechazado"),
        (429, "limite_superado", "historia_viva_rate_limited"),
        (503, "servicio_no_disponible", "historia_viva_unavailable"),
        (418, "codigo_que_no_existe", "historia_viva_request_invalid"),
        (500, "codigo_que_no_existe", "historia_viva_unavailable"),
    ],
)
def test_se_decide_por_codigo_con_default_por_familia(
    servidor: Servidor, status: int, codigo: str, esperado: str
) -> None:
    servidor.status, servidor.cuerpo, servidor.cabeceras = error(status, codigo)

    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_fragmentos(ConsultaFragmentos(texto="abc"), timeout=5)

    assert excinfo.value.code == esperado
    assert excinfo.value.solicitud_id == "req_01ABC"
    assert "texto remoto" not in str(excinfo.value)


def test_retry_after_llega_como_segundos(servidor: Servidor) -> None:
    servidor.status, servidor.cuerpo, servidor.cabeceras = error(
        429, "limite_superado", **{"Retry-After": "30"}
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_pieza("pza_1", timeout=5)

    assert excinfo.value.reintentar_en == 30


def test_un_retry_after_con_fecha_no_se_interpreta(servidor: Servidor) -> None:
    servidor.status, servidor.cuerpo, servidor.cabeceras = error(
        503, "servicio_no_disponible", **{"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_pieza("pza_1", timeout=5)

    assert excinfo.value.reintentar_en is None


def test_pieza_no_disponible_es_ausencia_y_ruta_inexistente_es_error(
    servidor: Servidor,
) -> None:
    servidor.status, servidor.cuerpo, servidor.cabeceras = error(404, "pieza_no_disponible")
    assert transporte(servidor).get_pieza("pza_1", timeout=5) is None

    servidor.status, servidor.cuerpo, servidor.cabeceras = error(404, "ruta_inexistente")
    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_pieza("pza_1", timeout=5)
    assert excinfo.value.code == "historia_viva_request_invalid"


def test_un_error_sin_cuerpo_json_cae_por_familia_y_usa_la_cabecera(
    servidor: Servidor,
) -> None:
    servidor.status = 502
    servidor.cuerpo = b"<html>Bad gateway</html>"
    servidor.cabeceras = {"Content-Type": "text/html", "X-Solicitud-Id": "req_02XYZ"}

    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_pieza("pza_1", timeout=5)

    assert excinfo.value.code == "historia_viva_unavailable"
    assert excinfo.value.solicitud_id == "req_02XYZ"


@pytest.mark.parametrize(
    ("cuerpo", "tipo"),
    [(b"no es json", "application/json"), (b"[]", "application/json"), (b"{}", "text/html")],
)
def test_un_200_que_no_es_un_objeto_json_es_respuesta_invalida(
    servidor: Servidor, cuerpo: bytes, tipo: str
) -> None:
    servidor.cuerpo = cuerpo
    servidor.cabeceras = {"Content-Type": tipo}

    with pytest.raises(HistoriaVivaError) as excinfo:
        transporte(servidor).get_fragmentos(ConsultaFragmentos(texto="abc"), timeout=5)

    assert excinfo.value.code == "historia_viva_response_invalid"


def test_sin_servidor_es_indisponibilidad() -> None:
    servidor = Servidor()
    url = servidor.url
    servidor.cerrar()

    with pytest.raises(HistoriaVivaError) as excinfo:
        TransporteHistoriaVivaHttp(url, lambda: TOKEN).get_pieza("pza_1", timeout=2)

    assert excinfo.value.code == "historia_viva_unavailable"


# --- Configuración y token en la variable de entorno -------------------------------


def test_sin_claves_historia_viva_no_esta_configurada() -> None:
    assert cargar_configuracion_historia_viva({"OTRA": "x"}) is None


def test_la_configuracion_arma_un_cliente_que_manda_el_token_de_la_variable(
    servidor: Servidor,
) -> None:
    config = cargar_configuracion_historia_viva(
        {"AGENTE1_HV_BASE_URL": servidor.url, "AGENTE1_HV_TOKEN": f" {TOKEN}\n"}
    )

    cliente = construir_cliente_historia_viva(config)
    cliente.buscar_fragmentos(ConsultaFragmentos(texto="abc"))

    assert servidor.recibidos[0]["cabeceras"]["Authorization"] == f"Bearer {TOKEN}"


def test_el_token_no_aparece_al_imprimir_la_configuracion() -> None:
    config = cargar_configuracion_historia_viva(
        {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN": TOKEN}
    )

    assert TOKEN not in repr(config)


@pytest.mark.parametrize(
    ("env", "codigo"),
    [
        ({"AGENTE1_HV_BASE_URL": "http://hv.local"}, "historia_viva_config_incomplete"),
        ({"AGENTE1_HV_TOKEN": TOKEN}, "historia_viva_config_incomplete"),
        (
            {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN": "   "},
            "historia_viva_config_incomplete",
        ),
        (
            {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN_ARCHIVO": "/tmp/t"},
            "historia_viva_config_unknown_key",
        ),
        (
            {"AGENTE1_HV_BASE_URL": "ftp://hv.local", "AGENTE1_HV_TOKEN": TOKEN},
            "historia_viva_config_base_url",
        ),
        (
            {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN": "hv con espacio"},
            "historia_viva_config_token_invalid",
        ),
        (
            {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN": "hv_ñ"},
            "historia_viva_config_token_invalid",
        ),
        (
            {"AGENTE1_HV_BASE_URL": "http://hv.local", "AGENTE1_HV_TOKEN": "a" * 4097},
            "historia_viva_config_token_invalid",
        ),
    ],
)
def test_una_configuracion_rota_se_rechaza_con_codigo(env: dict, codigo: str) -> None:
    with pytest.raises(ConfiguracionHistoriaVivaError) as excinfo:
        cargar_configuracion_historia_viva(env)

    assert excinfo.value.code == codigo
    assert TOKEN not in str(excinfo.value)
