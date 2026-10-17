"""Cliente pull hacia Historia Viva: valida respuestas crudas contra el
contrato `/v1`, reintenta sólo lo idempotente y nunca inventa el dato que
faltó.

Todo corre sin red: el `TransporteHistoriaVivaFake` entrega cuerpos crudos
como los entrega el adapter HTTP (`historia_viva_http.py`). La prueba contra
el mock de Historia Viva vive aparte, en `contrato/`."""

import json
from datetime import date
from pathlib import Path

import pytest

from agente1.historia_viva import (
    CANALES_APORTE,
    ESTADO_APORTE,
    PRECISIONES_FECHA,
    TIPOS_CONTENIDO_APORTE,
    Aporte,
    ConsultaFragmentos,
    HistoriaVivaError,
    componer_material_efemeride,
)
from agente1.historia_viva_cliente import (
    CAMPOS_APORTE_CREADO_V1,
    CAMPOS_FRAGMENTO_V1,
    CAMPOS_PIEZA_V1,
    CAMPOS_RESPUESTA_FRAGMENTOS_V1,
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    PERDER_RESPUESTA,
    ClienteHistoriaViva,
    PoliticaCliente,
    RespuestaAporte,
    TransporteHistoriaVivaFake,
)


class RelojFake:
    """La espera entre reintentos como dato registrado, no como tiempo real."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)


# --- Cuerpos crudos conformes -------------------------------------------------


def fragmento_crudo(**cambios: object) -> dict:
    crudo = {
        "fragmento_id": "frg_001",
        "pieza_id": "pza_001",
        "texto": "La Facultad abrió sus puertas con veinte cursantes.",
        "fecha_inicio": "1926-08-07",
        "fecha_fin": "1926-08-07",
        "precision_fecha": "dia",
        "tipo": "acta",
        "resumen_pieza": "Acta fundacional sintética",
        "url_original": "https://ejemplo.invalid/validar.html?pieza=001",
        "validada_el": "2026-01-15T10:00:00Z",
        "pagina": 3,
        "seccion": None,
    }
    crudo.update(cambios)
    return crudo


def respuesta_fragmentos(*fragmentos: dict) -> dict:
    return {"total": len(fragmentos), "limite": 10, "fragmentos": list(fragmentos)}


def respuesta_pieza(**cambios: object) -> dict:
    pieza = {
        "pieza_id": "pza_001",
        "tipo": "acta",
        "estado": "Validada",
        "resumen": "Resumen sintético",
        "texto": "Acta fundacional sintética, texto íntegro.",
        "fecha_inicio": "1926-08-07",
        "fecha_fin": "1926-08-07",
        "precision_fecha": "dia",
        "origen": "Archivo sintético",
        "lote_id": None,
        "lote_nombre": None,
        "url_original": "https://ejemplo.invalid/validar.html?pieza=001",
        "validada_por": "mgarcia",
        "validada_el": "2026-01-15T10:00:00Z",
        "modo_validacion": "individual",
        "fragmentos": [fragmento_crudo()],
    }
    pieza.update(cambios)
    return pieza


def respuesta_aporte(**cambios: object) -> dict:
    crudo = {
        "aporte_id": "apt_0001",
        "pieza_id": "pza_aporte-0001",
        "estado": "Pendiente",
        "recibido_el": "2026-11-03T14:07:55Z",
        "idempotency_key": "apo-key-001",
    }
    crudo.update(cambios)
    return crudo


def aporte(clave: str = "apo-key-001", **cambios: object) -> Aporte:
    campos = {
        "clave_idempotencia": clave,
        "tipo_contenido": "gacetilla",
        "canal": "ninguno",
        "titulo": "Borrador sintético de efeméride",
        "cuerpo": "Cuerpo sintético redactado por A1.",
        "piezas_fuente": ("pza_001",),
    }
    campos.update(cambios)
    return Aporte(**campos)


def consulta(**cambios: object) -> ConsultaFragmentos:
    campos: dict[str, object] = {
        "desde": date(1926, 1, 1),
        "hasta": date(1926, 12, 31),
    }
    campos.update(cambios)
    return ConsultaFragmentos(**campos)


# --- Respuestas válidas --------------------------------------------------------


def test_una_busqueda_valida_devuelve_fragmentos_del_dominio() -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_fragmentos": respuesta_fragmentos(fragmento_crudo())}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.fragmento_id == "frg_001"
    assert fragmento.pieza_id == "pza_001"
    assert fragmento.rango.precision == "dia"
    assert fragmento.validada_el == date(2026, 1, 15)
    assert fragmento.ubicacion == "p. 3"
    assert fragmento.cita() == "pza_001, p. 3 (7 de agosto de 1926)"


@pytest.mark.parametrize(
    ("pagina", "seccion", "ubicacion"),
    [
        pytest.param(4, "Cláusula primera", "p. 4, Cláusula primera", id="pagina_y_seccion"),
        pytest.param(None, "Hoja «Ingresantes 2010»", "Hoja «Ingresantes 2010»", id="planilla"),
        pytest.param(None, "00:12:30", "00:12:30", id="video"),
        pytest.param(None, None, None, id="sin_ubicacion"),
    ],
)
def test_la_ubicacion_sale_de_pagina_y_seccion(pagina, seccion, ubicacion) -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "get_fragmentos": respuesta_fragmentos(
                fragmento_crudo(pagina=pagina, seccion=seccion, tipo="planilla")
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.ubicacion == ubicacion
    assert fragmento.tipo == "planilla"


def test_el_cliente_implementa_el_puerto_y_compone_la_efemeride_en_a1() -> None:
    """La efeméride se compone del lado de A1: el cliente sólo entrega
    fragmentos citables, nunca una efeméride redactada por A2."""

    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_fragmentos": respuesta_fragmentos(fragmento_crudo())}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    material = componer_material_efemeride(
        cliente, desde=date(1926, 8, 1), hasta=date(1926, 8, 31), precision="mes"
    )

    assert material.hay_material
    assert material.afirmaciones() == (
        (
            "La Facultad abrió sus puertas con veinte cursantes.",
            "pza_001, p. 3 (7 de agosto de 1926)",
        ),
    )
    assert material.piezas_fuente() == ("pza_001",)


def test_una_consulta_sin_resultados_produce_una_lista_vacia() -> None:
    """El vacío es `200` con lista vacía, no una afirmación ni un error."""

    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    assert cliente.buscar_fragmentos(consulta()) == ()


def test_una_pieza_valida_se_amplia_completa() -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_pieza": respuesta_pieza()}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    pieza = cliente.obtener_pieza("pza_001")

    assert pieza is not None
    assert pieza.pieza_id == "pza_001"
    assert pieza.texto == "Acta fundacional sintética, texto íntegro."
    assert len(pieza.fragmentos) == 1


def test_una_pieza_inexistente_o_no_validada_devuelve_ausencia() -> None:
    """El contrato responde 404 indistinguible; el transporte lo entrega `None`."""

    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    assert cliente.obtener_pieza("pza_999") is None


def test_un_aporte_valido_queda_pendiente_de_validacion() -> None:
    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    recepcion = cliente.registrar_aporte(aporte())

    assert recepcion.aporte_id == "apt_fake-0001"
    assert recepcion.pieza_id == "pza_fake-aporte-0001"
    assert recepcion.estado == ESTADO_APORTE
    assert recepcion.duplicado is False


def test_el_aporte_no_admite_mail_como_tipo_de_contenido() -> None:
    """Un mail es el canal `correo`, no un tipo de contenido: la rc2 de `/v1`
    trae `comunicado` en su lugar y el gate del cliente frena al aporte."""

    with pytest.raises(ValueError):
        aporte(tipo_contenido="mail")


def test_nada_viaja_hasta_que_a1_inicia() -> None:
    """Pull significa que el transporte no se toca sin una llamada del puerto."""

    transporte = TransporteHistoriaVivaFake()
    ClienteHistoriaViva(transporte, reloj=RelojFake())

    assert transporte.llamadas == []


# --- Respuestas fuera de contrato ---------------------------------------------


@pytest.mark.parametrize(
    "mutacion",
    [
        pytest.param(lambda c: c.pop("fragmento_id"), id="sin_fragmento_id"),
        pytest.param(lambda c: c.pop("texto"), id="sin_texto"),
        pytest.param(lambda c: c.pop("fecha_inicio"), id="sin_fecha_inicio"),
        pytest.param(
            lambda c: c.update(precision_fecha="aproximada"),
            id="precision_desconocida",
        ),
        pytest.param(
            lambda c: c.update(fecha_inicio="1926-08-09"),
            id="rango_invertido",
        ),
        pytest.param(lambda c: c.pop("precision_fecha"), id="precision_ausente"),
        pytest.param(
            lambda c: c.update(fragmento_id="../escape"),
            id="fragmento_id_invalido",
        ),
        pytest.param(
            lambda c: c.update(fragmento_id="pza_001"), id="fragmento_id_sin_prefijo"
        ),
        pytest.param(lambda c: c.update(pieza_id="pie-001"), id="pieza_id_sin_prefijo"),
        pytest.param(lambda c: c.update(texto="   "), id="texto_vacio"),
        pytest.param(lambda c: c.update(campo_sorpresa=1), id="campo_extra"),
        pytest.param(lambda c: c.pop("seccion"), id="sin_seccion"),
        pytest.param(lambda c: c.update(pagina=0), id="pagina_cero"),
        pytest.param(lambda c: c.update(pagina="3"), id="pagina_texto"),
        pytest.param(
            lambda c: c.update(validada_el="hace un mes"),
            id="momento_no_rfc3339",
        ),
        pytest.param(
            lambda c: c.update(validada_el="2026-01-15"),
            id="momento_sin_hora",
        ),
        pytest.param(
            lambda c: c.update(url_original="javascript:alert(1)"),
            id="url_no_http",
        ),
    ],
)
def test_un_fragmento_fuera_de_contrato_se_rechaza_entero(mutacion) -> None:
    crudo = fragmento_crudo()
    mutacion(crudo)
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_fragmentos": respuesta_fragmentos(crudo)}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta())

    assert excinfo.value.code == "historia_viva_response_invalid"


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param([], id="lista_desnuda"),
        pytest.param("error de texto", id="texto_plano"),
        pytest.param({"total": 0, "limite": 10}, id="sin_lista"),
        pytest.param({"total": 0, "fragmentos": []}, id="sin_limite"),
        pytest.param(
            {"total": 0, "limite": 10, "fragmentos": [], "extra": True},
            id="campo_extra_en_respuesta",
        ),
        pytest.param(
            {"total": 0, "limite": 10, "fragmentos": [fragmento_crudo()]},
            id="total_menor_que_lo_recibido",
        ),
        pytest.param({"total": True, "limite": 10, "fragmentos": []}, id="total_booleano"),
    ],
)
def test_una_respuesta_de_busqueda_sin_la_forma_declarada_se_rechaza(
    cuerpo,
) -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_fragmentos": cuerpo}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta())

    assert excinfo.value.code == "historia_viva_response_invalid"


def test_mas_fragmentos_que_el_limite_pedido_es_fuera_de_contrato() -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "get_fragmentos": respuesta_fragmentos(
                fragmento_crudo(fragmento_id="frg_001"),
                fragmento_crudo(fragmento_id="frg_002"),
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta(limite=1))

    assert excinfo.value.code == "historia_viva_response_invalid"


@pytest.mark.parametrize(
    "cambios",
    [
        pytest.param({"pieza_id": "pza_777"}, id="otra_pieza"),
        pytest.param({"estado": "Pendiente"}, id="no_validada"),
        pytest.param({"modo_validacion": "automatica"}, id="modo_desconocido"),
        pytest.param({"lote_id": "../lote"}, id="lote_invalido"),
        pytest.param({"titulo": "Acta"}, id="campo_extra"),
        pytest.param({"texto": ""}, id="sin_texto"),
        pytest.param(
            {"fragmentos": [fragmento_crudo(pieza_id="pza_002")]},
            id="fragmento_de_otra_pieza",
        ),
    ],
)
def test_una_pieza_fuera_de_contrato_se_rechaza(cambios) -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_pieza": respuesta_pieza(**cambios)}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.obtener_pieza("pza_001")

    assert excinfo.value.code == "historia_viva_response_invalid"


@pytest.mark.parametrize(
    "cambios",
    [
        pytest.param({"estado": "Publicado"}, id="aporte_publicado"),
        pytest.param({"estado": "Validada"}, id="aporte_validado"),
        pytest.param({"aporte_id": "../escape"}, id="aporte_id_invalido"),
        pytest.param({"aporte_id": "apo-0001"}, id="aporte_id_sin_prefijo"),
        pytest.param({"idempotency_key": "otra-clave-001"}, id="acuse_de_otra_clave"),
        pytest.param({"recibido_el": "ayer"}, id="recibido_no_rfc3339"),
        pytest.param({"duplicado": False}, id="campo_extra"),
    ],
)
def test_una_recepcion_fuera_de_contrato_se_rechaza(cambios) -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "post_aporte": RespuestaAporte(
                cuerpo=respuesta_aporte(**cambios), repetido=False
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.registrar_aporte(aporte())

    assert excinfo.value.code == "historia_viva_response_invalid"


# --- Precisión de fecha --------------------------------------------------------


@pytest.mark.parametrize(
    ("precision", "expresion_esperada"),
    [
        ("mes", "agosto de 1926"),
        ("anio", "1926"),
        ("decada", "la década de 1920"),
        ("rango", "agosto de 1926"),
    ],
)
def test_una_precision_gruesa_no_se_presenta_como_fecha_exacta(
    precision: str, expresion_esperada: str
) -> None:
    """El rango llega con `desde`/`hasta` exactos pero la precisión declarada
    limita lo que se puede decir: el cliente no gana exactitud por conocer el
    `date` crudo."""

    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "get_fragmentos": respuesta_fragmentos(
                fragmento_crudo(
                    fecha_inicio="1926-08-01",
                    fecha_fin="1926-08-31",
                    precision_fecha=precision,
                )
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.rango.es_fecha_exacta is False
    assert fragmento.rango.expresion_temporal() == expresion_esperada
    assert "7 de agosto" not in fragmento.cita()


@pytest.mark.parametrize(
    ("desde", "hasta", "expresion"),
    [
        pytest.param("2015-01-01", "2019-12-31", "entre 2015 y 2019", id="anios"),
        pytest.param("2015-03-01", "2015-06-30", "entre marzo y junio de 2015", id="meses"),
        pytest.param("2015-03-03", "2015-03-09", "marzo de 2015", id="un_mes"),
        pytest.param("2015-03-03", "2015-03-03", "marzo de 2015", id="un_dia_no_es_exacto"),
    ],
)
def test_la_precision_rango_se_redacta_entre_x_y_y(desde, hasta, expresion) -> None:
    """`rango` (/v1 1.1) nunca es fecha exacta, aunque empiece y termine el
    mismo día: se engrosa, no se afina."""

    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "get_fragmentos": respuesta_fragmentos(
                fragmento_crudo(
                    fecha_inicio=desde, fecha_fin=hasta, precision_fecha="rango"
                )
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.rango.es_fecha_exacta is False
    assert fragmento.rango.expresion_temporal() == expresion


# --- Idempotencia de aportes ---------------------------------------------------


def test_la_misma_clave_no_duplica_el_aporte() -> None:
    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    primera = cliente.registrar_aporte(aporte())
    segunda = cliente.registrar_aporte(aporte())

    assert segunda.aporte_id == primera.aporte_id
    assert segunda.duplicado is True


def test_claves_distintas_producen_aportes_distintos() -> None:
    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    primera = cliente.registrar_aporte(aporte("apo-key-001"))
    segunda = cliente.registrar_aporte(aporte("apo-key-002"))

    assert primera.aporte_id != segunda.aporte_id
    assert segunda.duplicado is False


def test_la_misma_clave_con_otro_payload_es_conflicto() -> None:
    """La semántica propuesta en el paquete de cierre: reusar la clave con un
    cuerpo distinto no muta el primer aporte ni crea uno encubierto."""

    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())
    cliente.registrar_aporte(aporte())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.registrar_aporte(aporte(titulo="Otro título"))

    assert excinfo.value.code == "historia_viva_request_invalid"


def test_una_respuesta_perdida_no_crea_un_segundo_aporte() -> None:
    """El escenario que la clave existe para resolver: el primer POST persistió
    pero la respuesta se perdió; el reintento devuelve el mismo `aporte_id`."""

    transporte = TransporteHistoriaVivaFake(
        guiones={"post_aporte": (PERDER_RESPUESTA,)}
    )
    cliente = ClienteHistoriaViva(
        transporte,
        politica=PoliticaCliente(reintentos=1, reintentar_aportes=True),
        reloj=RelojFake(),
    )

    recepcion = cliente.registrar_aporte(aporte())

    assert recepcion.aporte_id == "apt_fake-0001"
    assert recepcion.duplicado is True
    assert [op for op, _ in transporte.llamadas] == [
        "post_aporte",
        "post_aporte",
    ]


# --- Timeout y reintentos -------------------------------------------------------


def test_el_timeout_declarado_llega_a_cada_llamada() -> None:
    transporte = TransporteHistoriaVivaFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(timeout_segundos=25.0)
    )

    cliente.buscar_fragmentos(consulta())
    cliente.obtener_pieza("pza_001")
    cliente.registrar_aporte(aporte())

    assert transporte.llamadas == [
        ("get_fragmentos", 25.0),
        ("get_pieza", 25.0),
        ("post_aporte", 25.0),
    ]


def test_una_falla_transitoria_se_reintenta_con_espera() -> None:
    transporte = TransporteHistoriaVivaFake(
        guiones={
            "get_fragmentos": (
                HistoriaVivaError("historia_viva_rate_limited"),
                respuesta_fragmentos(fragmento_crudo()),
            )
        }
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(espera_segundos=0.25), reloj=reloj
    )

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.fragmento_id == "frg_001"
    assert len(transporte.llamadas) == 2
    assert reloj.esperas == [0.25]


def test_el_reintento_espera_lo_que_pide_retry_after() -> None:
    """Un `429` con `Retry-After: 30` se espera entero, no en ráfaga."""

    transporte = TransporteHistoriaVivaFake(
        guiones={
            "get_fragmentos": (
                HistoriaVivaError("historia_viva_rate_limited", reintentar_en=30),
                respuesta_fragmentos(),
            )
        }
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(transporte, reloj=reloj)

    assert cliente.buscar_fragmentos(consulta()) == ()
    assert reloj.esperas == [30]


def test_un_retry_after_mayor_que_el_tope_no_se_espera() -> None:
    """El `503` del interruptor pide 300 s: el flujo falla en vez de bloquearse."""

    transporte = TransporteHistoriaVivaFake(
        guiones={
            "get_fragmentos": (
                HistoriaVivaError("historia_viva_unavailable", reintentar_en=300),
                respuesta_fragmentos(),
            )
        }
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(espera_maxima_segundos=30), reloj=reloj
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta())

    assert excinfo.value.code == "historia_viva_unavailable"
    assert len(transporte.llamadas) == 1
    assert reloj.esperas == []


def test_agotados_los_reintentos_la_falla_se_propaga() -> None:
    transporte = TransporteHistoriaVivaFake(
        guiones={
            "get_fragmentos": (
                HistoriaVivaError("historia_viva_unavailable"),
                HistoriaVivaError("historia_viva_unavailable"),
                HistoriaVivaError("historia_viva_unavailable"),
            )
        }
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte,
        politica=PoliticaCliente(reintentos=2, espera_segundos=0.5),
        reloj=reloj,
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta())

    assert excinfo.value.code == "historia_viva_unavailable"
    assert len(transporte.llamadas) == 3
    assert reloj.esperas == [0.5, 0.5]


@pytest.mark.parametrize(
    "codigo",
    [
        "historia_viva_unauthorized",
        "historia_viva_forbidden",
        "historia_viva_request_invalid",
        "historia_viva_response_invalid",
        "historia_viva_aporte_rechazado",
    ],
)
def test_una_falla_definitiva_no_se_reintenta(codigo: str) -> None:
    """Esperar no cambia un `401` ni una respuesta fuera de contrato."""

    transporte = TransporteHistoriaVivaFake(
        guiones={"get_pieza": (HistoriaVivaError(codigo),)}
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(reintentos=3), reloj=reloj
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.obtener_pieza("pza_001")

    assert excinfo.value.code == codigo
    assert len(transporte.llamadas) == 1
    assert reloj.esperas == []


def test_el_aporte_no_reintenta_por_default() -> None:
    """Mientras #17 no cierre la deduplicación por `Idempotency-Key`, un POST
    reintentado puede crear el segundo aporte que la clave existe para evitar."""

    transporte = TransporteHistoriaVivaFake(
        guiones={
            "post_aporte": (
                HistoriaVivaError("historia_viva_unavailable"),
                respuesta_aporte(),
            )
        }
    )
    reloj = RelojFake()
    cliente = ClienteHistoriaViva(
        transporte, politica=PoliticaCliente(reintentos=2), reloj=reloj
    )

    with pytest.raises(HistoriaVivaError):
        cliente.registrar_aporte(aporte())

    assert len(transporte.llamadas) == 1
    assert reloj.esperas == []


@pytest.mark.parametrize(
    "campos",
    [
        {"timeout_segundos": 0},
        {"reintentos": -1},
        {"espera_segundos": -0.1},
        {"espera_segundos": 5, "espera_maxima_segundos": 1},
    ],
)
def test_la_politica_rechaza_valores_sin_sentido(campos) -> None:
    with pytest.raises(ValueError):
        PoliticaCliente(**campos)


# --- Coherencia con el espejo del contrato --------------------------------------


def test_el_espejo_del_contrato_coincide_con_el_runtime() -> None:
    """`contracts/historia_viva_v1.schema.json` espeja las formas de
    `openapi-agentes.yaml` que A1 consume; el decodificador usa los mismos
    campos y enums."""

    schema_path = (
        Path(__file__).parents[1]
        / "src"
        / "agente1"
        / "contracts"
        / "historia_viva_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    defs = schema["$defs"]

    assert schema["x-contract-version"] == CONTRACT_VERSION
    assert schema["x-status"] == CONTRACT_STATUS
    assert set(defs["Fragmento"]["required"]) == CAMPOS_FRAGMENTO_V1
    assert set(defs["RespuestaFragmentos"]["required"]) == CAMPOS_RESPUESTA_FRAGMENTOS_V1
    assert set(defs["Pieza"]["required"]) == CAMPOS_PIEZA_V1
    assert set(defs["AporteCreado"]["required"]) == CAMPOS_APORTE_CREADO_V1
    for nombre in ("Fragmento", "RespuestaFragmentos", "Pieza", "AporteCreado"):
        assert defs[nombre]["additionalProperties"] is False
    assert defs["PrecisionFecha"]["enum"] == list(PRECISIONES_FECHA)
    # El aporte manda exactamente el vocabulario de la rc2 de `/v1`: `mail` no
    # es un tipo de contenido, el mail aparece como canal `correo` (#101, #117).
    assert set(defs["TipoContenido"]["enum"]) == TIPOS_CONTENIDO_APORTE
    assert set(defs["Canal"]["enum"]) - {None} == CANALES_APORTE - {"ninguno"}
