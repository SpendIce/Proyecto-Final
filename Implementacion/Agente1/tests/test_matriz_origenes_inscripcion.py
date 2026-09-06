"""HU-012: la matriz por origen debe seguir siendo fail-closed y coherente.

La SEU comunicó dónde se inscribe cada tipo de actividad, no cómo confirmar.
Estas pruebas impiden dos regresiones silenciosas: que un origen quede
habilitado para enviar sin que exista la definición institucional que lo
autorice, y que la matriz divergía del contrato `confirmacion_inscripcion_v2`.
"""

from __future__ import annotations

import json
from importlib.resources import files

import pytest

from agente1.origenes_inscripcion import (
    CAMPOS_REQUERIDOS_POR_CONTRATO,
    ESTADOS_PREINSCRIPCION_CANDIDATOS,
    MATRIZ,
    MOTIVOS_DE_BLOQUEO,
    ORIGENES,
    ORIGENES_DE_INSCRIPCION,
    PROCEDENCIAS,
    DecisionEnvio,
    OrigenDesconocidoError,
    campos_sin_confirmar,
    descripcion,
    evaluar_envio,
)


CONTRATO_V2 = json.loads(
    files("agente1")
    .joinpath("contracts", "confirmacion_inscripcion_v2.schema.json")
    .read_text(encoding="utf-8")
)


def test_matriz_declara_no_habilitar_envio() -> None:
    assert MATRIZ["x-habilita-envio"] is False
    assert MATRIZ["x-status"] == "CANDIDATO_PENDIENTE_CONFIRMACION_SEU"


@pytest.mark.parametrize("origen", sorted(ORIGENES))
def test_ningun_origen_autoriza_envio(origen: str) -> None:
    decision = evaluar_envio(origen)

    assert decision.autorizado is False
    assert decision.motivos
    assert set(decision.motivos) <= MOTIVOS_DE_BLOQUEO


@pytest.mark.parametrize("origen", sorted(ORIGENES))
def test_todo_origen_declara_bloqueo_por_aprobacion_y_datos_personales(
    origen: str,
) -> None:
    """Ninguna combinación puede quedar habilitada por omisión."""
    motivos = set(evaluar_envio(origen).motivos)

    assert "regla_de_aprobacion_no_definida" in motivos
    assert "politica_datos_personales_no_definida" in motivos


def test_combinacion_origen_tipo_no_confirmada_se_reporta() -> None:
    decision = evaluar_envio("GOOGLE_FORMS", tipo_actividad="DIPLOMATURA")

    assert "combinacion_origen_tipo_no_confirmada" in decision.motivos


def test_combinacion_comunicada_no_agrega_ese_motivo() -> None:
    decision = evaluar_envio("GOOGLE_FORMS", tipo_actividad="WEBINAR")

    assert "combinacion_origen_tipo_no_confirmada" not in decision.motivos
    assert decision.autorizado is False


def test_estado_de_preinscripcion_no_puede_usarse_como_habilitante() -> None:
    for estado in ESTADOS_PREINSCRIPCION_CANDIDATOS:
        decision = evaluar_envio("SIU_GUARANI", estado_preinscripcion=estado)

        assert "estado_preinscripcion_no_confirmado" in decision.motivos
        assert decision.autorizado is False


def test_origen_fuera_de_la_matriz_se_rechaza() -> None:
    with pytest.raises(OrigenDesconocidoError):
        evaluar_envio("SISTEMA_NO_RELEVADO")


def test_decision_autorizada_sin_motivos_es_la_unica_forma_valida() -> None:
    """Impide construir una decisión que diga «sí» arrastrando bloqueos."""
    with pytest.raises(ValueError):
        DecisionEnvio(
            origen="SIU_GUARANI",
            tipo_actividad=None,
            autorizado=True,
            motivos=("origen_sin_adapter",),
        )
    with pytest.raises(ValueError):
        DecisionEnvio(
            origen="SIU_GUARANI", tipo_actividad=None, autorizado=False, motivos=()
        )


def test_origenes_de_inscripcion_coinciden_con_el_contrato_v2() -> None:
    enum_contrato = tuple(CONTRATO_V2["properties"]["origen_inscripcion"]["enum"])

    assert ORIGENES_DE_INSCRIPCION == enum_contrato


def test_tipos_de_actividad_de_la_matriz_existen_en_el_contrato_v2() -> None:
    enum_tipos = set(CONTRATO_V2["properties"]["tipo_actividad"]["enum"])

    for item in ORIGENES.values():
        assert set(item["tipos_actividad"]) <= enum_tipos, item["origen"]


def test_campos_requeridos_de_la_matriz_coinciden_con_el_contrato_v2() -> None:
    assert CAMPOS_REQUERIDOS_POR_CONTRATO == tuple(CONTRATO_V2["required"])


@pytest.mark.parametrize("origen", sorted(ORIGENES))
def test_cada_origen_declara_procedencia_de_cada_campo(origen: str) -> None:
    item = descripcion(origen)

    assert set(item["campos_disponibles"].values()) <= PROCEDENCIAS
    assert item["procedencia_hecho"] in PROCEDENCIAS
    assert item["adapter"] == "NO_DEFINIDO"
    assert item["regla_envio"] == "PROHIBIDO"


@pytest.mark.parametrize("origen", sorted(ORIGENES))
def test_ningun_origen_tiene_hoy_campos_confirmados(origen: str) -> None:
    """Si algún campo pasara a CONFIRMADO_SEU, debe hacerse con evidencia."""
    faltantes = campos_sin_confirmar(origen)

    assert "id_inscripcion" in faltantes


def test_el_correo_no_se_declara_como_origen_de_inscripcion() -> None:
    item = descripcion("CORREO_CURSOS_COMPLEMENTARIOS")

    assert item["clase"] == "CANAL_POSTERIOR"
    assert "canal_no_es_origen_de_inscripcion" in item["motivos_de_bloqueo"]
    assert "CORREO_CURSOS_COMPLEMENTARIOS" not in ORIGENES_DE_INSCRIPCION


def test_el_pdf_con_enlace_de_pago_no_habilita_persistir_datos_de_pago() -> None:
    pdf = descripcion("CORREO_CURSOS_COMPLEMENTARIOS")["pdf_informativo"]
    propiedades = CONTRATO_V2["properties"]

    assert pdf["existe"] == "CONFIRMADO_SEU"
    assert "enlace de pago" in pdf["observacion"]
    assert not any("pago" in nombre for nombre in propiedades)
