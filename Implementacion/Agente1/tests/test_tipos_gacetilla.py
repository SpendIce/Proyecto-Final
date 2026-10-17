"""Regresion del contrato de tipos de gacetilla (issue #120).

El contrato es la interfaz congelada entre la decision #120 y su trabajo: la
forma declarada y el modo de produccion de cada tipo, y si el tipo necesita una
actividad de la fuente institucional. Si alguien agrega, saca o cambia un tipo,
esta regresion falla y obliga a decidirlo en el contrato, no en el codigo.
"""

import json
from pathlib import Path

CONTRATO = Path(__file__).resolve().parents[1] / "src" / "agente1" / "contracts" / "tipos_gacetilla_v1.json"

# Los siete tipos del corpus y su modo, tal como los decidio la decision #120 y
# su adendo del 17/10. Es la expectativa congelada: cambiarla es cambiar la
# decision, no el test.
ESPERADO = [
    ("difusion_de_actividad", "genera", True),
    ("cronica_de_evento", "extrae_y_confirma", False),
    ("aviso_de_otra_area", "extrae_y_confirma", False),
    ("convocatoria_interna", "extrae_y_confirma", False),
    ("saludo_o_efemeride", "genera", False),
    ("fallecimiento", "extrae_y_confirma", False),
    ("newsletter", "extrae_y_confirma", False),
]


def _contrato() -> dict:
    return json.loads(CONTRATO.read_text(encoding="utf-8"))


def test_el_contrato_declara_los_siete_tipos_del_corpus():
    tipos = _contrato()["tipos"]
    assert [t["id"] for t in tipos] == [e[0] for e in ESPERADO]


def test_cada_tipo_declara_su_modo_y_si_necesita_actividad():
    tipos = _contrato()["tipos"]
    observado = [(t["id"], t["modo"], t["requiere_actividad"]) for t in tipos]
    assert observado == ESPERADO


def test_todo_modo_esta_declarado_en_el_contrato():
    contrato = _contrato()
    declarados = set(contrato["modos"])
    for tipo in contrato["tipos"]:
        assert tipo["modo"] in declarados, tipo["id"]


def test_solo_difusion_necesita_una_actividad_de_la_fuente():
    tipos = _contrato()["tipos"]
    con_actividad = [t["id"] for t in tipos if t["requiere_actividad"]]
    assert con_actividad == ["difusion_de_actividad"]


def test_solo_los_tipos_que_generan_pueden_exigir_prompt():
    """Un tipo que extrae y confirma no llama al modelo: no tiene prompt."""

    tipos = _contrato()["tipos"]
    que_generan = [t["id"] for t in tipos if t["modo"] == "genera"]
    assert que_generan == ["difusion_de_actividad", "saludo_o_efemeride"]


def test_la_cronica_declara_generar_desde_historia_viva_como_destino():
    tipos = {t["id"]: t for t in _contrato()["tipos"]}
    assert "destino_declarado" in tipos["cronica_de_evento"]


def test_el_contrato_cita_su_decision_y_su_adr():
    contrato = _contrato()
    assert contrato["x-contract-version"] == "tipos_gacetilla_v1"
    assert contrato["x-decision"] == "#120"
    assert contrato["x-adr"].endswith("0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md")
