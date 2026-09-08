"""Regresión de `DEF-A1-013`: el presupuesto de decodificación se dimensiona
contra el contrato, y una configuración insuficiente falla acá antes de que
alguien la acepte como baseline."""

import json

import pytest

from agente1.ollama import (
    DEFAULT_OLLAMA_NUM_PREDICT,
    MAX_OLLAMA_NUM_PREDICT,
)
from agente1.posts import (
    CONTRATO_SALIDA_ESTRUCTURADA,
    CONTRATO_SALIDA_ESTRUCTURADA_V3,
)
from agente1.presupuesto import (
    CHARS_POR_TOKEN_MENOS_FAVORABLE,
    ContratoNoDimensionable,
    documento_maximo,
    presupuesto_minimo_num_predict,
)


CONTRATOS = {
    "v2": CONTRATO_SALIDA_ESTRUCTURADA,
    "v3": CONTRATO_SALIDA_ESTRUCTURADA_V3,
}


@pytest.mark.parametrize("nombre", sorted(CONTRATOS))
def test_documento_maximo_respeta_los_limites_del_contrato(nombre):
    contrato = CONTRATOS[nombre]
    documento = json.loads(documento_maximo(contrato))

    assert set(documento) == set(contrato["required"])
    for campo in ("gancho", "prosa", "cta"):
        assert len(documento[campo]) == contrato["properties"][campo]["maxLength"]
    # Todos los hashtags del enum, que es la cantidad máxima con uniqueItems.
    assert documento["hashtags"] == contrato["properties"]["hashtags"]["items"]["enum"]


@pytest.mark.parametrize("nombre", sorted(CONTRATOS))
def test_el_presupuesto_por_defecto_cubre_el_documento_maximo(nombre):
    """Es la regresión que le faltaba a `DEF-A1-013`.

    Si una versión futura del contrato sube un `maxLength`, el requerido sube
    solo y este test falla antes de que una corrida trunque en silencio.
    """

    requerido = presupuesto_minimo_num_predict(CONTRATOS[nombre])

    assert DEFAULT_OLLAMA_NUM_PREDICT >= requerido, (
        f"el presupuesto por defecto ({DEFAULT_OLLAMA_NUM_PREDICT}) no alcanza "
        f"para el documento máximo del contrato {nombre} ({requerido} tokens)"
    )
    # El techo configurable también tiene que poder cubrirlo: si no, ninguna
    # configuración válida del adapter sirve para el contrato vigente.
    assert MAX_OLLAMA_NUM_PREDICT >= requerido


@pytest.mark.parametrize("historico", [112, 300])
def test_los_presupuestos_historicos_quedan_por_debajo_del_requerido(historico):
    """Sin esta comprobación la regresión anterior no prueba nada.

    112 es el valor que enmascaró las fallas de contenido del benchmark del
    2026-08-26; 300 fue la corrección parcial que cubría prosa corriente pero
    no el documento máximo del contrato.
    """

    requerido = presupuesto_minimo_num_predict(CONTRATO_SALIDA_ESTRUCTURADA_V3)

    assert historico < requerido


def test_un_contrato_mas_largo_exige_mas_presupuesto():
    contrato = json.loads(json.dumps(CONTRATO_SALIDA_ESTRUCTURADA_V3))
    contrato["properties"]["prosa"]["maxLength"] = 5_000

    assert presupuesto_minimo_num_predict(contrato) > MAX_OLLAMA_NUM_PREDICT


def test_un_contrato_sin_limite_no_se_puede_dimensionar():
    contrato = json.loads(json.dumps(CONTRATO_SALIDA_ESTRUCTURADA_V3))
    del contrato["properties"]["prosa"]["maxLength"]

    with pytest.raises(ContratoNoDimensionable):
        presupuesto_minimo_num_predict(contrato)


def test_un_arreglo_sin_enum_no_se_puede_dimensionar():
    contrato = json.loads(json.dumps(CONTRATO_SALIDA_ESTRUCTURADA_V3))
    contrato["properties"]["hashtags"]["items"] = {"type": "string"}

    with pytest.raises(ContratoNoDimensionable):
        presupuesto_minimo_num_predict(contrato)


def test_la_relacion_de_tokens_documenta_el_extremo_malo_medido():
    """El número viene de una medición, no de una estimación.

    Si alguien lo sube sin volver a medir, el presupuesto derivado baja y la
    cota deja de ser una cota. Ver `evidencias/medicion-presupuesto-decodificacion-2026-09-08.md`.
    """

    assert CHARS_POR_TOKEN_MENOS_FAVORABLE == 1.91
