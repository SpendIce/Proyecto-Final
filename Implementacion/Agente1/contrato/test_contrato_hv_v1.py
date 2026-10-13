"""Prueba de contrato del cliente de A1 contra `/v1` de Historia Viva (#12, #17).

Corre el cliente real (`ClienteHistoriaViva` sobre `TransporteHistoriaVivaHttp`)
contra el mock Prism del paquete `contratojuan`, que levanta
`node ejecutar-contrato.mjs` y exporta `HV_BASE_URL` y `HV_TOKEN`. Cada caso
elige su escenario con `Prefer: code=<status>, example=<nombre>` y afirma qué
hace el cliente con la respuesta, no sólo el status.

Fuera de la suite normal (`testpaths = tests`): sin `HV_BASE_URL` se saltea
entera. Los casos pendientes de C48 llevan la marca `c48` y se pueden
saltear con `-m "not c48"`. A1 no consume `GET /v1/efemerides` ni
`GET /v1/relatos` (compone su propia efeméride, ADR 0008), así que no se cubren.
"""

from __future__ import annotations

import os
from datetime import date

import pytest

from agente1.historia_viva import (
    ESTADO_APORTE,
    Aporte,
    ConsultaFragmentos,
    HistoriaVivaError,
    componer_material_efemeride,
)
from agente1.historia_viva_cliente import ClienteHistoriaViva, PoliticaCliente
from agente1.historia_viva_http import TransporteHistoriaVivaHttp

BASE_URL = os.environ.get("HV_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="HV_BASE_URL no definida")

PIEZA = "pza_5b2e9c40-7a13-4d88-9f06-1c3a8e4d2b77"
# El mock devuelve siempre esta clave en el acuse; el cliente exige que el
# acuse sea el de la clave enviada, así que el caso manda la misma.
CLAVE = "3f1c9a12-7f0b-4a2e-9a7d-0c5b6e2f1d44"


class RelojFake:
    def __init__(self) -> None:
        self.esperas: list[float] = []

    def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)


class Contador:
    """Envuelve el transporte HTTP real para contar los pedidos que salen."""

    def __init__(self, transporte: TransporteHistoriaVivaHttp) -> None:
        self._transporte = transporte
        self.pedidos = 0

    def get_fragmentos(self, consulta, *, timeout):
        self.pedidos += 1
        return self._transporte.get_fragmentos(consulta, timeout=timeout)

    def get_pieza(self, pieza_id, *, timeout):
        self.pedidos += 1
        return self._transporte.get_pieza(pieza_id, timeout=timeout)

    def post_aporte(self, aporte, *, timeout):
        self.pedidos += 1
        return self._transporte.post_aporte(aporte, timeout=timeout)


def armar(status: int, ejemplo: str, **politica: object):
    tokens_leidos: list[str] = []

    def token() -> str:
        valor = os.environ["HV_TOKEN"]
        tokens_leidos.append(valor)
        return valor

    transporte = Contador(
        TransporteHistoriaVivaHttp(
            BASE_URL,
            token,
            cabeceras_extra={"Prefer": f"code={status}, example={ejemplo}"},
        )
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(**politica), reloj=reloj
    )
    return cliente, transporte, reloj, tokens_leidos


def consulta() -> ConsultaFragmentos:
    return ConsultaFragmentos(texto="convenio", limite=10)


def aporte() -> Aporte:
    return Aporte(
        clave_idempotencia=CLAVE,
        tipo_contenido="gacetilla",
        canal="ninguno",
        titulo="La FIE celebra diez años de cooperación con la UTN",
        cuerpo="La Facultad de Ingeniería del Ejército conmemora una década del convenio marco con la UTN.",
        piezas_fuente=(PIEZA,),
        fragmentos_fuente=("frg_e41d0c7a-2f95-5b3e-a8c1-96d7f0b3c254",),
    )


def fallar(operacion, cliente) -> HistoriaVivaError:
    with pytest.raises(HistoriaVivaError) as excinfo:
        operacion(cliente)
    return excinfo.value


# --- GET /v1/fragmentos -----------------------------------------------------------


def test_fragmentos_conResultados_cita_pagina_seccion_y_precision() -> None:
    cliente, transporte, _, tokens = armar(200, "conResultados")

    convenio, acta, foto = cliente.buscar_fragmentos(consulta())

    assert convenio.fragmento_id == "frg_e41d0c7a-2f95-5b3e-a8c1-96d7f0b3c254"
    assert convenio.cita() == (
        f"{PIEZA}, p. 1, Cláusula primera — Objeto (11 de abril de 2016)"
    )
    assert convenio.validada_el == date(2026, 11, 10)
    assert acta.rango.expresion_temporal() == "septiembre de 2018"
    assert acta.ubicacion == "p. 4"
    assert foto.rango.expresion_temporal() == "1972"
    assert foto.ubicacion is None
    # `url_original` se conserva como referencia para una persona; no se sigue.
    assert convenio.url_original.startswith("http://localhost:8000/validar.html?pieza=")
    assert transporte.pedidos == 1
    assert len(tokens) == 1


def test_fragmentos_precisionDecada_no_es_fecha_exacta() -> None:
    cliente, *_ = armar(200, "precisionDecada")

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.tipo == "plano"
    assert fragmento.rango.es_fecha_exacta is False
    assert fragmento.rango.expresion_temporal() == "la década de 1960"


def test_fragmentos_precisionRango_se_redacta_entre_x_y_y() -> None:
    cliente, *_ = armar(200, "precisionRango")

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.rango.precision == "rango"
    assert fragmento.rango.es_fecha_exacta is False
    assert fragmento.rango.expresion_temporal() == "entre 2015 y 2019"
    assert fragmento.cita().endswith("(entre 2015 y 2019)")


def test_fragmentos_planillaConSeccion_usa_la_hoja_como_ubicacion() -> None:
    cliente, *_ = armar(200, "planillaConSeccion")

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.tipo == "planilla"
    assert fragmento.ubicacion == "Hoja «Ingresantes 2010»"


def test_fragmentos_videoDescrito_usa_la_marca_de_tiempo_como_ubicacion() -> None:
    cliente, *_ = armar(200, "videoDescrito")

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.tipo == "video"
    assert fragmento.ubicacion == "00:12:30"


def test_fragmentos_sinResultados_no_da_material_para_afirmar() -> None:
    cliente, *_ = armar(200, "sinResultados")

    material = componer_material_efemeride(
        cliente, desde=date(2026, 11, 18), hasta=date(2026, 11, 18)
    )

    assert material.hay_material is False
    assert material.afirmaciones() == ()


@pytest.mark.parametrize(
    ("status", "ejemplo"),
    [(400, "sinCriterio"), (400, "parametroDesconocido"), (404, "rutaInexistente")],
)
def test_fragmentos_4xx_es_definitivo(status: int, ejemplo: str) -> None:
    cliente, transporte, reloj, _ = armar(status, ejemplo)

    error = fallar(lambda c: c.buscar_fragmentos(consulta()), cliente)

    assert error.code == "historia_viva_request_invalid"
    assert error.solicitud_id is not None and error.solicitud_id.startswith("req_")
    assert transporte.pedidos == 1
    assert reloj.esperas == []


# --- GET /v1/piezas/{pieza_id} ----------------------------------------------------


def test_piezas_convenio_devuelve_la_pieza_completa() -> None:
    cliente, *_ = armar(200, "convenio")

    pieza = cliente.obtener_pieza(PIEZA)

    assert pieza is not None
    assert pieza.tipo == "convenio"
    assert "En la ciudad de Buenos Aires" in pieza.texto
    assert pieza.rango.expresion_temporal() == "11 de abril de 2016"
    assert [f.ubicacion for f in pieza.fragmentos] == [
        "p. 1, Cláusula primera — Objeto",
        "p. 1, Cláusula segunda — Vigencia",
        "p. 2, Firmas",
    ]


def test_piezas_videoAnalizadoPorPersona_acepta_el_tipo_nuevo() -> None:
    cliente, *_ = armar(200, "videoAnalizadoPorPersona")

    pieza = cliente.obtener_pieza("pza_a41f3b7c-6d28-4e90-b5a1-3c7e9f1d2b48")

    assert pieza is not None
    assert pieza.tipo == "video"
    assert pieza.fragmentos[0].ubicacion == "00:12:30"


def test_piezas_noDisponible_es_ausencia_no_error() -> None:
    cliente, transporte, reloj, _ = armar(404, "noDisponible")

    assert cliente.obtener_pieza(PIEZA) is None
    assert transporte.pedidos == 1
    assert reloj.esperas == []


def test_piezas_idMalFormado_es_definitivo() -> None:
    cliente, transporte, reloj, _ = armar(400, "idMalFormado")

    error = fallar(lambda c: c.obtener_pieza(PIEZA), cliente)

    assert error.code == "historia_viva_request_invalid"
    assert transporte.pedidos == 1
    assert reloj.esperas == []


# --- POST /v1/aportes -------------------------------------------------------------


def test_aportes_creado_queda_pendiente() -> None:
    cliente, *_ = armar(201, "creado")

    recepcion = cliente.registrar_aporte(aporte())

    assert recepcion.aporte_id == "apt_2c71b9e0-4f3a-4a58-b1d6-e08c5a97f312"
    assert recepcion.pieza_id == "pza_8d0a6c15-93e2-4b7f-a4d0-5e1f7c2b8a39"
    assert recepcion.estado == ESTADO_APORTE
    assert recepcion.duplicado is False


def test_aportes_repetido_devuelve_el_acuse_original() -> None:
    cliente, *_ = armar(200, "repetido")

    recepcion = cliente.registrar_aporte(aporte())

    assert recepcion.aporte_id == "apt_2c71b9e0-4f3a-4a58-b1d6-e08c5a97f312"
    assert recepcion.duplicado is True


@pytest.mark.parametrize(
    ("status", "ejemplo"),
    [
        (400, "claveReutilizada"),
        (400, "claveAusente"),
        (400, "cuerpoGrande"),
        (400, "fuenteInexistente"),
        (404, "rutaInexistente"),
    ],
)
def test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado(
    status: int, ejemplo: str
) -> None:
    cliente, transporte, reloj, _ = armar(
        status, ejemplo, reintentar_aportes=True
    )

    error = fallar(lambda c: c.registrar_aporte(aporte()), cliente)

    assert error.code == "historia_viva_request_invalid"
    assert transporte.pedidos == 1
    assert reloj.esperas == []


# --- Comunes a las tres rutas -----------------------------------------------------

OPERACIONES = {
    "fragmentos": (lambda c: c.buscar_fragmentos(consulta()), {}),
    "piezas": (lambda c: c.obtener_pieza(PIEZA), {}),
    "aportes": (lambda c: c.registrar_aporte(aporte()), {"reintentar_aportes": True}),
}


@pytest.mark.parametrize("ruta", OPERACIONES)
@pytest.mark.parametrize(
    ("status", "ejemplo", "codigo"),
    [
        (401, "tokenInvalido", "historia_viva_unauthorized"),
        (403, "sinAlcance", "historia_viva_forbidden"),
    ],
)
def test_comun_4xx_de_credencial_es_definitivo(
    ruta: str, status: int, ejemplo: str, codigo: str
) -> None:
    operacion, politica = OPERACIONES[ruta]
    cliente, transporte, reloj, _ = armar(status, ejemplo, **politica)

    error = fallar(operacion, cliente)

    assert error.code == codigo
    assert transporte.pedidos == 1
    assert reloj.esperas == []


@pytest.mark.parametrize("ruta", OPERACIONES)
def test_comun_limite_espera_retry_after_y_no_reintenta_en_rafaga(ruta: str) -> None:
    operacion, politica = OPERACIONES[ruta]
    cliente, transporte, reloj, _ = armar(429, "limite", reintentos=2, **politica)

    error = fallar(operacion, cliente)

    assert error.code == "historia_viva_rate_limited"
    assert error.reintentar_en == 30
    assert reloj.esperas == [30, 30]
    assert transporte.pedidos == 3


@pytest.mark.parametrize("ruta", OPERACIONES)
@pytest.mark.parametrize("ejemplo", ["pausado", "motorCaido"])
def test_comun_503_con_retry_after_largo_no_bloquea_el_flujo(
    ruta: str, ejemplo: str
) -> None:
    """El mock manda `Retry-After: 300`: más que `espera_maxima_segundos`. El
    cliente no espera cinco minutos ni reintenta antes de tiempo: falla."""

    operacion, politica = OPERACIONES[ruta]
    cliente, transporte, reloj, _ = armar(503, ejemplo, **politica)

    error = fallar(operacion, cliente)

    assert error.code == "historia_viva_unavailable"
    assert error.reintentar_en == 300
    assert reloj.esperas == []
    assert transporte.pedidos == 1


def test_comun_503_con_retry_after_corto_se_reintenta_esperando() -> None:
    """Con la API real, motor o base caídos mandan `Retry-After: 30`; acá se
    simula subiendo el tope de la política por encima de los 300 del mock."""

    cliente, transporte, reloj, _ = armar(
        503, "motorCaido", reintentos=1, espera_maxima_segundos=300
    )

    fallar(lambda c: c.buscar_fragmentos(consulta()), cliente)

    assert reloj.esperas == [300]
    assert transporte.pedidos == 2


def test_comun_el_token_se_lee_en_cada_pedido() -> None:
    """Rotar el token no exige reiniciar: el transporte lo pide en cada envío."""

    cliente, _, _, tokens = armar(200, "sinResultados")

    cliente.buscar_fragmentos(consulta())
    cliente.buscar_fragmentos(consulta())

    assert len(tokens) == 2


# --- Pendientes de C48 ------------------------------------------------------------


@pytest.mark.c48
def test_c48_aporteValidado_vuelve_como_cualquier_pieza() -> None:
    cliente, *_ = armar(200, "aporteValidado")

    pieza = cliente.obtener_pieza("pza_8d0a6c15-93e2-4b7f-a4d0-5e1f7c2b8a39")

    assert pieza is not None
    assert pieza.tipo == "nota"
    assert pieza.fragmentos[0].ubicacion is None


@pytest.mark.c48
def test_c48_aporteRechazado_es_definitivo_y_no_reusa_la_clave() -> None:
    cliente, transporte, reloj, _ = armar(
        422, "aporteRechazado", reintentar_aportes=True
    )

    error = fallar(lambda c: c.registrar_aporte(aporte()), cliente)

    assert error.code == "historia_viva_aporte_rechazado"
    assert transporte.pedidos == 1
    assert reloj.esperas == []
