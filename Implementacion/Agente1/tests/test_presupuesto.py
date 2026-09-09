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
    MEDICION_DOCUMENTO_MAXIMO_V3,
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


def test_la_relacion_de_tokens_no_supera_ningun_extremo_medido():
    """La constante tiene que ser una cota, no un promedio ni una estimación.

    Se verifica contra la medición versionada y no contra sí misma: si alguien
    la sube por encima de cualquier estilo observado, el presupuesto derivado
    baja y deja de cubrir el caso que la medición ya vio. Evidencia:
    `evidencias/medicion-presupuesto-decodificacion-2026-09-08.md`.
    """

    peor_medido = min(
        caracteres / tokens
        for caracteres, tokens in MEDICION_DOCUMENTO_MAXIMO_V3.values()
    )

    assert CHARS_POR_TOKEN_MENOS_FAVORABLE <= peor_medido


def test_la_medicion_versionada_describe_el_documento_maximo_del_contrato():
    """Los caracteres medidos tienen que ser los del contrato vigente.

    Si el contrato cambia de tamaño, la medición queda vieja y el presupuesto
    derivado se apoya en un documento que ya no existe.
    """

    caracteres = len(documento_maximo(CONTRATO_SALIDA_ESTRUCTURADA_V3))

    assert {medido for medido, _ in MEDICION_DOCUMENTO_MAXIMO_V3.values()} == {
        caracteres
    }


def test_un_arreglo_de_texto_acotado_por_maxitems_si_se_puede_dimensionar():
    """El contrato del fallback de interpretación (#26) acota su arreglo con
    `maxItems` y `items.maxLength` en lugar de con un enum, porque los términos
    de búsqueda son texto libre y no un catálogo cerrado. Eso sigue siendo una
    salida acotada, así que tiene que poder dimensionarse."""
    schema = {
        "required": ["terminos"],
        "properties": {
            "terminos": {
                "type": "array",
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string", "maxLength": 5},
            }
        },
    }

    documento = json.loads(documento_maximo(schema))

    assert len(documento["terminos"]) == 3
    assert all(len(termino) == 5 for termino in documento["terminos"])
    assert len(set(documento["terminos"])) == 3, "uniqueItems exige valores distintos"


def test_un_arreglo_de_texto_sin_maxitems_no_se_puede_dimensionar():
    schema = {
        "required": ["terminos"],
        "properties": {
            "terminos": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "maxLength": 5},
            }
        },
    }

    with pytest.raises(ContratoNoDimensionable):
        documento_maximo(schema)


def test_un_arreglo_largo_de_texto_respeta_el_maxlength_de_cada_item():
    """El relleno que distingue un elemento de otro no puede hacerle exceder
    su propio `maxLength`: un documento más grande que el contrato
    sobredimensiona el presupuesto, que es el error de medición de
    `DEF-A1-013` al revés. Se prueba en el borde exacto —tantos elementos
    como valores distintos admite el largo— porque es donde un relleno
    ingenuo empieza a desbordar."""
    schema = {
        "required": ["terminos"],
        "properties": {
            "terminos": {
                "type": "array",
                "maxItems": 100,
                "uniqueItems": True,
                "items": {"type": "string", "maxLength": 2},
            }
        },
    }

    documento = json.loads(documento_maximo(schema))

    assert len(documento["terminos"]) == 100
    assert all(len(termino) == 2 for termino in documento["terminos"])
    assert len(set(documento["terminos"])) == 100, "uniqueItems exige valores distintos"


def test_un_arreglo_que_no_puede_tener_items_unicos_no_se_puede_dimensionar():
    """`uniqueItems` con más elementos que combinaciones posibles es un
    contrato imposible de satisfacer, no un contrato grande: tiene que
    interrumpir el cálculo en vez de devolver un número inventado."""
    schema = {
        "required": ["terminos"],
        "properties": {
            "terminos": {
                "type": "array",
                "maxItems": 200,
                "uniqueItems": True,
                "items": {"type": "string", "maxLength": 1},
            }
        },
    }

    with pytest.raises(ContratoNoDimensionable):
        documento_maximo(schema)


def test_un_enum_mas_grande_que_maxitems_no_sobredimensiona():
    """Las dos formas de acotar un arreglo tienen que decir lo mismo: si el
    contrato admite menos items que valores tiene el enum, el documento máximo
    no puede usar el catálogo entero."""
    schema = {
        "required": ["etiquetas"],
        "properties": {
            "etiquetas": {
                "type": "array",
                "maxItems": 2,
                "uniqueItems": True,
                "items": {"type": "string", "enum": ["#a", "#b", "#c", "#d"]},
            }
        },
    }

    documento = json.loads(documento_maximo(schema))

    assert documento["etiquetas"] == ["#a", "#b"]


def test_un_enum_no_textual_no_se_puede_dimensionar():
    schema = {
        "required": ["numeros"],
        "properties": {
            "numeros": {
                "type": "array",
                "uniqueItems": True,
                "items": {"enum": [1, 2, 3]},
            }
        },
    }

    with pytest.raises(ContratoNoDimensionable):
        documento_maximo(schema)
