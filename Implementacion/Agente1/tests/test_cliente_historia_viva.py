"""Cliente pull hacia Historia Viva: valida respuestas crudas contra el
contrato candidato, reintenta sólo lo idempotente y nunca inventa el dato que
faltó.

Todo corre sin red: el `TransporteHistoriaVivaFake` entrega cuerpos crudos
como los parsearía un adapter HTTP que todavía no existe (issue #17)."""

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
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    PERDER_RESPUESTA,
    SCHEMA_APORTE,
    SCHEMA_FRAGMENTOS,
    SCHEMA_PIEZA,
    ClienteHistoriaViva,
    PoliticaCliente,
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
        "fragmento_id": "frg-001",
        "pieza_id": "pie-001",
        "texto": "La Facultad abrió sus puertas con veinte cursantes.",
        "rango": {
            "desde": "1926-08-07",
            "hasta": "1926-08-07",
            "precision_fecha": "dia",
        },
        "tipo": "acta",
        "resumen_pieza": "Acta fundacional sintética",
        "url_original": "https://ejemplo.invalid/piezas/1",
        "validada_el": "2026-01-15",
        "ubicacion": "página 3",
    }
    crudo.update(cambios)
    return crudo


def respuesta_fragmentos(*fragmentos: dict) -> dict:
    return {"schema": SCHEMA_FRAGMENTOS, "fragmentos": list(fragmentos)}


def respuesta_pieza(**cambios: object) -> dict:
    pieza = {
        "pieza_id": "pie-001",
        "titulo": "Acta fundacional sintética",
        "resumen": "Resumen sintético",
        "rango": {
            "desde": "1926-08-07",
            "hasta": "1926-08-07",
            "precision_fecha": "dia",
        },
        "tipo": "acta",
        "url_original": "https://ejemplo.invalid/piezas/1",
        "validada_el": "2026-01-15",
        "fragmentos": [fragmento_crudo()],
    }
    pieza.update(cambios)
    return {"schema": SCHEMA_PIEZA, "pieza": pieza}


def respuesta_aporte(**cambios: object) -> dict:
    crudo = {
        "schema": SCHEMA_APORTE,
        "aporte_id": "apo-0001",
        "estado": ESTADO_APORTE,
        "duplicado": False,
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
        "piezas_fuente": ("pie-001",),
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

    assert fragmento.fragmento_id == "frg-001"
    assert fragmento.pieza_id == "pie-001"
    assert fragmento.rango.precision == "dia"
    assert fragmento.ubicacion == "página 3"
    assert fragmento.cita() == "pie-001, página 3 (7 de agosto de 1926)"


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
            "pie-001, página 3 (7 de agosto de 1926)",
        ),
    )
    assert material.piezas_fuente() == ("pie-001",)


def test_una_consulta_sin_resultados_produce_una_lista_vacia() -> None:
    """El vacío es `200` con lista vacía, no una afirmación ni un error."""

    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    assert cliente.buscar_fragmentos(consulta()) == ()


def test_una_pieza_valida_se_amplia_completa() -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_pieza": respuesta_pieza()}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    pieza = cliente.obtener_pieza("pie-001")

    assert pieza is not None
    assert pieza.pieza_id == "pie-001"
    assert len(pieza.fragmentos) == 1


def test_una_pieza_inexistente_o_no_validada_devuelve_ausencia() -> None:
    """El contrato responde 404 indistinguible; el transporte lo entrega `None`."""

    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    assert cliente.obtener_pieza("pie-999") is None


def test_un_aporte_valido_queda_pendiente_de_validacion() -> None:
    cliente = ClienteHistoriaViva(TransporteHistoriaVivaFake(), reloj=RelojFake())

    recepcion = cliente.registrar_aporte(aporte())

    assert recepcion.aporte_id == "apo-0001"
    assert recepcion.estado == ESTADO_APORTE
    assert recepcion.duplicado is False


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
        pytest.param(lambda c: c.pop("rango"), id="sin_rango"),
        pytest.param(
            lambda c: c["rango"].update(precision_fecha="aproximada"),
            id="precision_desconocida",
        ),
        pytest.param(
            lambda c: c["rango"].update(desde="1926-08-09"),
            id="rango_invertido",
        ),
        pytest.param(
            lambda c: c["rango"].pop("precision_fecha"),
            id="precision_ausente",
        ),
        pytest.param(
            lambda c: c.update(fragmento_id="../escape"),
            id="fragmento_id_invalido",
        ),
        pytest.param(lambda c: c.update(texto="   "), id="texto_vacio"),
        pytest.param(lambda c: c.update(campo_sorpresa=1), id="campo_extra"),
        pytest.param(
            lambda c: c.update(validada_el="hace un mes"),
            id="fecha_no_iso",
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
        pytest.param({"schema": SCHEMA_FRAGMENTOS}, id="sin_lista"),
        pytest.param(
            {"schema": "historia_viva.fragmentos.v99", "fragmentos": []},
            id="version_desconocida",
        ),
        pytest.param(
            {"schema": SCHEMA_FRAGMENTOS, "fragmentos": [], "extra": True},
            id="campo_extra_en_respuesta",
        ),
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
                fragmento_crudo(fragmento_id="frg-001"),
                fragmento_crudo(fragmento_id="frg-002"),
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.buscar_fragmentos(consulta(limite=1))

    assert excinfo.value.code == "historia_viva_response_invalid"


def test_una_pieza_que_no_es_la_pedida_se_rechaza() -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"get_pieza": respuesta_pieza(pieza_id="pie-777")}
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    with pytest.raises(HistoriaVivaError) as excinfo:
        cliente.obtener_pieza("pie-001")

    assert excinfo.value.code == "historia_viva_response_invalid"


@pytest.mark.parametrize(
    "cambios",
    [
        pytest.param({"estado": "PUBLICADO"}, id="aporte_publicado"),
        pytest.param({"estado": "VALIDADO"}, id="aporte_validado"),
        pytest.param({"duplicado": "si"}, id="duplicado_no_booleano"),
        pytest.param({"aporte_id": "../escape"}, id="aporte_id_invalido"),
        pytest.param({"schema": "historia_viva.aporte.v2"}, id="schema_otro"),
    ],
)
def test_una_recepcion_fuera_de_contrato_se_rechaza(cambios) -> None:
    transporte = TransporteHistoriaVivaFake(
        respuestas={"post_aporte": respuesta_aporte(**cambios)}
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
                    rango={
                        "desde": "1926-08-01",
                        "hasta": "1926-08-31",
                        "precision_fecha": precision,
                    }
                )
            )
        }
    )
    cliente = ClienteHistoriaViva(transporte, reloj=RelojFake())

    (fragmento,) = cliente.buscar_fragmentos(consulta())

    assert fragmento.rango.es_fecha_exacta is False
    assert fragmento.rango.expresion_temporal() == expresion_esperada
    assert "7 de agosto" not in fragmento.cita()


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

    assert recepcion.aporte_id == "apo-0001"
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
    cliente.obtener_pieza("pie-001")
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

    assert fragmento.fragmento_id == "frg-001"
    assert len(transporte.llamadas) == 2
    assert reloj.esperas == [0.25]


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
        cliente.obtener_pieza("pie-001")

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
    ],
)
def test_la_politica_rechaza_valores_sin_sentido(campos) -> None:
    with pytest.raises(ValueError):
        PoliticaCliente(**campos)


# --- Coherencia con el schema versionado ----------------------------------------


def test_el_schema_json_es_parseable_y_coincide_con_el_runtime() -> None:
    schema_path = (
        Path(__file__).parents[1]
        / "src"
        / "agente1"
        / "contracts"
        / "historia_viva_cliente_candidate_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    defs = schema["$defs"]

    assert schema["x-contract-version"] == CONTRACT_VERSION
    assert schema["x-status"] == CONTRACT_STATUS
    assert schema["x-status"] == "CANDIDATO_NO_INSTITUCIONAL"
    assert defs["respuesta_fragmentos"]["properties"]["schema"]["const"] == (
        SCHEMA_FRAGMENTOS
    )
    assert defs["respuesta_pieza"]["properties"]["schema"]["const"] == SCHEMA_PIEZA
    assert defs["respuesta_aporte"]["properties"]["schema"]["const"] == SCHEMA_APORTE
    assert defs["rango_historico"]["properties"]["precision_fecha"]["enum"] == list(
        PRECISIONES_FECHA
    )
    assert defs["respuesta_aporte"]["properties"]["estado"]["const"] == ESTADO_APORTE
    assert set(
        defs["solicitud_aporte"]["properties"]["tipo_contenido"]["enum"]
    ) == set(TIPOS_CONTENIDO_APORTE)
    assert set(defs["solicitud_aporte"]["properties"]["canal"]["enum"]) == set(
        CANALES_APORTE
    )
    # El contrato que se valida es candidato: la deuda con #17 queda declarada.
    assert schema["x-issue"] == 17
