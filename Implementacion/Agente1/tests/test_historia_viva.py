"""Seam de consulta a Historia Viva: un puerto, precisión de fecha como control,
efeméride compuesta del lado de A1, y aportes idempotentes que nacen pendientes.

Todo corre sin red y sin credenciales: el fake es la única implementación del
puerto que existe hoy."""

from datetime import date
import inspect

import pytest

from agente1.historia_viva import (
    ESTADO_APORTE,
    LIMITE_FRAGMENTOS_MAX,
    Aporte,
    ConsultaFragmentos,
    Fragmento,
    HistoriaViva,
    HistoriaVivaError,
    HistoriaVivaFake,
    Pieza,
    RangoHistorico,
    RecepcionAporte,
    componer_material_efemeride,
)


def rango(desde: date, hasta: date, precision: str = "dia") -> RangoHistorico:
    return RangoHistorico(desde=desde, hasta=hasta, precision=precision)


def fragmento(
    *,
    fragmento_id: str = "frg-001",
    pieza_id: str = "pie-001",
    texto: str = "La Facultad abrió sus puertas con veinte cursantes.",
    rango_: RangoHistorico | None = None,
    tipo: str = "acta",
    ubicacion: str | None = "página 3",
) -> Fragmento:
    return Fragmento(
        fragmento_id=fragmento_id,
        pieza_id=pieza_id,
        texto=texto,
        rango=rango_ or rango(date(1926, 8, 7), date(1926, 8, 7)),
        tipo=tipo,
        resumen_pieza="Acta fundacional sintética",
        url_original="https://ejemplo.invalid/piezas/1",
        validada_el=date(2026, 1, 15),
        ubicacion=ubicacion,
    )


# --- El puerto ---------------------------------------------------------------


def test_el_puerto_solo_expone_buscar_ampliar_y_aportar():
    """Un único puerto de alto nivel, con tres operaciones y ninguna más."""

    operaciones = {
        nombre
        for nombre, _ in inspect.getmembers(HistoriaViva, inspect.isfunction)
        if not nombre.startswith("_")
    }

    assert operaciones == {"buscar_fragmentos", "obtener_pieza", "registrar_aporte"}


def test_el_puerto_no_admite_que_historia_viva_inicie_la_interaccion():
    """A1 siempre inicia: no hay callbacks, suscripciones ni cola entrante.

    Que la capacidad no exista es el control. Si alguna vez aparece un método
    de recepción, esta prueba lo tiene que hacer visible.
    """

    superficie = " ".join(
        nombre for nombre, _ in inspect.getmembers(HistoriaViva)
    ).casefold()

    for entrante in ("suscrib", "callback", "webhook", "recibir", "notificar", "push"):
        assert entrante not in superficie


# --- Precisión de fecha ------------------------------------------------------


@pytest.mark.parametrize(
    ("desde", "hasta", "precision", "esperado"),
    [
        (date(1926, 8, 7), date(1926, 8, 7), "dia", "7 de agosto de 1926"),
        (date(1926, 8, 1), date(1926, 8, 31), "mes", "agosto de 1926"),
        (date(1926, 1, 1), date(1926, 12, 31), "anio", "1926"),
        (date(1920, 1, 1), date(1929, 12, 31), "decada", "la década de 1920"),
        (date(1926, 1, 1), date(1928, 12, 31), "anio", "entre 1926 y 1928"),
    ],
)
def test_la_expresion_temporal_dice_solo_lo_que_la_precision_sostiene(
    desde, hasta, precision, esperado
):
    assert rango(desde, hasta, precision).expresion_temporal() == esperado


@pytest.mark.parametrize("precision", ["mes", "anio", "decada"])
def test_una_precision_gruesa_nunca_produce_una_fecha_exacta(precision):
    """El control que pide `respuesta-nacho.md`: no presentar como fecha exacta
    una pieza cuya precisión es de mes, año o década."""

    unico_dia = rango(date(1926, 8, 7), date(1926, 8, 7), precision)

    assert unico_dia.es_fecha_exacta is False
    assert "7 de agosto" not in unico_dia.expresion_temporal()


def test_un_rango_sin_precision_conocida_se_rechaza():
    with pytest.raises(ValueError, match="precision"):
        rango(date(1926, 8, 7), date(1926, 8, 7), "aproximada")


def test_un_rango_invertido_se_rechaza():
    with pytest.raises(ValueError, match="invertido"):
        rango(date(1930, 1, 1), date(1926, 1, 1))


def test_la_cita_identifica_el_pasaje_y_no_solo_el_documento():
    assert fragmento().cita() == "pie-001, página 3 (7 de agosto de 1926)"
    assert fragmento(ubicacion=None).cita() == "pie-001 (7 de agosto de 1926)"


# --- Efeméride compuesta del lado de A1 --------------------------------------


def test_la_efemeride_se_compone_desde_una_busqueda_temporal():
    cliente = HistoriaVivaFake(fragmentos=(fragmento(),))

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
    # La consulta que sale es por período, sin pedir una efeméride ni un tipo:
    # inventar un tipo de pieza sería decidir por la fuente.
    (consulta,) = cliente.consultas
    assert (consulta.desde, consulta.hasta) == (date(1926, 8, 1), date(1926, 8, 31))
    assert consulta.texto is None
    assert consulta.tipo is None


def test_material_vacio_no_habilita_ninguna_afirmacion_historica():
    """Sin fragmentos no hay hueco que rellenar: hay ausencia de material."""

    material = componer_material_efemeride(
        HistoriaVivaFake(), desde=date(1900, 1, 1), hasta=date(1900, 12, 31)
    )

    assert material.hay_material is False
    assert material.afirmaciones() == ()
    assert material.piezas_fuente() == ()


def test_historia_viva_caida_no_se_disimula_con_una_efemeride_sin_sustento():
    cliente = HistoriaVivaFake(
        falla_en={"buscar_fragmentos": "historia_viva_unavailable"}
    )

    with pytest.raises(HistoriaVivaError) as excinfo:
        componer_material_efemeride(
            cliente, desde=date(1926, 8, 1), hasta=date(1926, 8, 31)
        )

    assert excinfo.value.code == "historia_viva_unavailable"


def test_un_periodo_sin_coincidencias_devuelve_vacio_y_no_es_un_error():
    cliente = HistoriaVivaFake(fragmentos=(fragmento(),))

    material = componer_material_efemeride(
        cliente, desde=date(1950, 1, 1), hasta=date(1950, 12, 31)
    )

    assert material.hay_material is False


def test_las_piezas_fuente_no_se_repiten_y_conservan_el_orden():
    cliente = HistoriaVivaFake(
        fragmentos=(
            fragmento(fragmento_id="frg-001", pieza_id="pie-002"),
            fragmento(fragmento_id="frg-002", pieza_id="pie-001"),
            fragmento(fragmento_id="frg-003", pieza_id="pie-002"),
        )
    )

    material = componer_material_efemeride(
        cliente, desde=date(1926, 1, 1), hasta=date(1926, 12, 31)
    )

    assert material.piezas_fuente() == ("pie-002", "pie-001")


# --- Consulta ----------------------------------------------------------------


def test_la_consulta_acota_el_tope_de_resultados():
    with pytest.raises(ValueError, match="limite"):
        ConsultaFragmentos(texto="fundación", limite=LIMITE_FRAGMENTOS_MAX + 1)


def test_una_consulta_sin_texto_ni_periodo_se_rechaza():
    with pytest.raises(ValueError, match="texto o período"):
        ConsultaFragmentos()


def test_la_busqueda_respeta_el_limite_pedido():
    cliente = HistoriaVivaFake(
        fragmentos=tuple(
            fragmento(fragmento_id=f"frg-{indice:03d}") for indice in range(5)
        )
    )

    encontrados = cliente.buscar_fragmentos(
        ConsultaFragmentos(desde=date(1926, 1, 1), hasta=date(1926, 12, 31), limite=2)
    )

    assert len(encontrados) == 2


# --- Ampliar una recuperación corta ------------------------------------------


def test_obtener_pieza_devuelve_la_pieza_completa():
    pieza = Pieza(
        pieza_id="pie-001",
        titulo="Acta fundacional sintética",
        resumen="Resumen sintético",
        rango=rango(date(1926, 8, 7), date(1926, 8, 7)),
        tipo="acta",
        url_original="https://ejemplo.invalid/piezas/1",
        validada_el=date(2026, 1, 15),
        fragmentos=(fragmento(),),
    )
    cliente = HistoriaVivaFake(piezas=(pieza,))

    assert cliente.obtener_pieza("pie-001") is pieza


def test_una_pieza_inexistente_o_no_validada_no_se_distingue():
    """El contrato acordado responde 404 en los dos casos, sin revelar cuál."""

    assert HistoriaVivaFake().obtener_pieza("pie-999") is None


# --- Aportes -----------------------------------------------------------------


def aporte(clave: str = "apo-key-001") -> Aporte:
    return Aporte(
        clave_idempotencia=clave,
        tipo_contenido="gacetilla",
        canal="ninguno",
        titulo="Borrador sintético de efeméride",
        cuerpo="Cuerpo sintético redactado por A1.",
        piezas_fuente=("pie-001",),
    )


def test_un_aporte_nace_pendiente_de_validacion():
    recepcion = HistoriaVivaFake().registrar_aporte(aporte())

    assert recepcion.estado == ESTADO_APORTE
    assert recepcion.duplicado is False


def test_no_existe_forma_de_declarar_un_aporte_validado_o_publicado():
    with pytest.raises(ValueError, match="pendiente de validación"):
        RecepcionAporte(aporte_id="apo-0001", estado="PUBLICADO")


def test_reenviar_el_mismo_aporte_no_lo_duplica():
    cliente = HistoriaVivaFake()

    primera = cliente.registrar_aporte(aporte())
    segunda = cliente.registrar_aporte(aporte())

    assert segunda.aporte_id == primera.aporte_id
    assert segunda.duplicado is True


def test_dos_aportes_distintos_reciben_identificadores_distintos():
    cliente = HistoriaVivaFake()

    primera = cliente.registrar_aporte(aporte("apo-key-001"))
    segunda = cliente.registrar_aporte(aporte("apo-key-002"))

    assert primera.aporte_id != segunda.aporte_id


def test_un_aporte_sin_procedencia_se_rechaza():
    with pytest.raises(ValueError, match="piezas fuente"):
        Aporte(
            clave_idempotencia="apo-key-003",
            tipo_contenido="gacetilla",
            canal="ninguno",
            titulo="Título",
            cuerpo="Cuerpo",
            piezas_fuente=(),
        )


def test_un_aporte_sin_clave_de_idempotencia_valida_se_rechaza():
    with pytest.raises(ValueError, match="idempotencia"):
        Aporte(
            clave_idempotencia="../escape",
            tipo_contenido="gacetilla",
            canal="ninguno",
            titulo="Título",
            cuerpo="Cuerpo",
            piezas_fuente=("pie-001",),
        )


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("tipo_contenido", "efemeride"), ("canal", "tiktok")],
)
def test_el_aporte_solo_admite_tipos_y_canales_conocidos(campo, valor):
    campos = {
        "clave_idempotencia": "apo-key-004",
        "tipo_contenido": "gacetilla",
        "canal": "ninguno",
        "titulo": "Título",
        "cuerpo": "Cuerpo",
        "piezas_fuente": ("pie-001",),
        campo: valor,
    }

    with pytest.raises(ValueError):
        Aporte(**campos)


# --- Fallas ------------------------------------------------------------------


@pytest.mark.parametrize(
    "operacion", ["buscar_fragmentos", "obtener_pieza", "registrar_aporte"]
)
def test_cada_operacion_puede_fallar_por_separado_sin_red(operacion):
    cliente = HistoriaVivaFake(
        fragmentos=(fragmento(),), falla_en={operacion: "historia_viva_rate_limited"}
    )
    llamadas = {
        "buscar_fragmentos": lambda: cliente.buscar_fragmentos(
            ConsultaFragmentos(desde=date(1926, 1, 1), hasta=date(1926, 12, 31))
        ),
        "obtener_pieza": lambda: cliente.obtener_pieza("pie-001"),
        "registrar_aporte": lambda: cliente.registrar_aporte(aporte()),
    }

    with pytest.raises(HistoriaVivaError) as excinfo:
        llamadas[operacion]()

    assert excinfo.value.code == "historia_viva_rate_limited"


def test_un_codigo_de_error_desconocido_se_colapsa_a_uno_conocido():
    """La auditoría sólo admite vocabulario cerrado: nada de texto remoto."""

    error = HistoriaVivaError("detalle-remoto-con-secreto@example.invalid")

    assert error.code == "historia_viva_unavailable"
    assert "example.invalid" not in str(error)


def test_el_fake_no_necesita_red_ni_credenciales():
    """El constructor no admite host, token ni nada que implique transporte."""

    parametros = set(inspect.signature(HistoriaVivaFake.__init__).parameters) - {"self"}

    assert parametros == {"fragmentos", "piezas", "falla_en"}
