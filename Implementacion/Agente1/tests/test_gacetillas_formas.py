"""Conformidad de forma de los siete tipos de gacetilla (#121).

Cada tipo declara su forma (`contracts/formas/<tipo>_v1.json`) y su contrato de
entrada (`contracts/entradas/<tipo>_v1.json`). Este modulo verifica que los
siete renderizan su pieza desde un caso del corpus con el renderer unico, que
el gate tiene nucleo comun mas reglas por tipo, que solo los tipos que generan
tienen prompt y que los que extraen y confirman no llaman al modelo.

Los goldens de `golden/formas/` son la pieza esperada de cada tipo: se comparan
byte a byte contra el renderer. El caso es sintetico y con forma del corpus;
algunos datos son claramente ficticios (`example.invalid`), asi que el golden
no reproduce datos personales del corpus real.
"""

from __future__ import annotations

import csv
import inspect
import json
import re
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.gacetillas import (
    TIPO_DIFUSION,
    TipoGeneraError,
    TipoNoGeneraError,
    campos_obligatorios,
    campos_que_no_aplican,
    cargar_entrada,
    cargar_forma,
    confirmar_pieza,
    generar_pieza,
    modo_de,
    renderizar,
    tipos,
    validar_pieza,
)
from agente1.procesamiento import PATRON_BORRADOR, _renderizar_mail

ROOT = Path(__file__).parents[1]
GOLDEN = ROOT / "golden" / "formas"
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

SALUDO = (
    "En el Día del Ingeniero saludamos a toda la comunidad de la facultad y "
    "reconocemos el trabajo de quienes ejercen la profesión con compromiso y "
    "vocación de servicio."
)

CASOS: dict[str, dict[str, str]] = {
    "cronica_de_evento": {
        "titulo": "Visita de la comisión de extensión al laboratorio de electrónica",
        "cuerpo": (
            "La comisión de extensión recorrió el laboratorio de electrónica "
            "junto a docentes y estudiantes. Durante la visita se presentaron "
            "los proyectos en curso y se acordaron las próximas actividades "
            "conjuntas."
        ),
    },
    "aviso_de_otra_area": {
        "titulo": "Estacionamiento de motos",
        "publico": "educativa",
        "hecho": "el estacionamiento para motos no estará habilitado",
        "fecha": "2026-11-02",
        "condicion": "hasta nuevo aviso",
        "area_emisora": "Secretaría Académica",
    },
    "convocatoria_interna": {
        "titulo": "Convocatoria interna de tutores",
        "destinatarios": "docentes de la casa",
        "convocatoria": "la convocatoria interna de tutores para el segundo semestre",
        "requisitos": "tener dos años de antigüedad y disponibilidad horaria",
        "fecha_limite": "2026-11-15",
        "area_emisora": "Secretaría Académica",
        "contacto": "doe@fie.undef.edu.ar",
    },
    "fallecimiento": {
        "titulo": "Informar fallecimiento",
        "nombre": "María Ejemplo",
        "rol": "docente de la casa",
        "dia": "viernes 23 de octubre",
        "hora": "11:00",
        "lugar": "Capilla del Instituto",
    },
    "newsletter": {
        "titulo": "Boletín del Observatorio",
        "enlace_adjunto": "https://example.invalid/boletin",
        "area_emisora": "Secretaría de Extensión Universitaria",
    },
    "saludo_o_efemeride": {"titulo": "Día del Ingeniero"},
}


def _fila_syn_001() -> dict[str, str]:
    with DATASET.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["id_actividad"] == "SYN-001":
                return fila
    raise AssertionError("falta SYN-001 en el dataset sintético")


def _prosa_difusion() -> dict[str, str]:
    ficha = (ROOT / "golden" / "SYN-001.ficha.md").read_text(encoding="utf-8")
    match = PATRON_BORRADOR.fullmatch(ficha.strip())
    assert match is not None
    return {"bajada": match.group("bajada").strip(), "cuerpo": match.group("cuerpo").strip()}


def _campos(tipo: str) -> dict[str, str]:
    if tipo == TIPO_DIFUSION:
        return _fila_syn_001()
    return dict(CASOS[tipo])


def _pieza(tipo: str) -> str:
    if tipo == TIPO_DIFUSION:
        return renderizar(tipo, _campos(tipo), _prosa_difusion())
    if modo_de(tipo) == "genera":
        pieza, errores = generar_pieza(tipo, _campos(tipo), FakeGenerator(SALUDO))
        assert errores == [], errores
        return pieza
    pieza, errores = confirmar_pieza(tipo, _campos(tipo))
    assert errores == [], errores
    return pieza


class GeneratorQueNoDebeInvocarse:
    modelo = "fake-no-invocar"

    def generar(self, prompt: str) -> str:
        raise AssertionError("un tipo que extrae y confirma no debe llamar al modelo")


# --- Contratos por tipo ---------------------------------------------------


def test_los_siete_tipos_declaran_forma_versionada_y_contrato_de_entrada():
    assert tipos() == (
        "difusion_de_actividad",
        "cronica_de_evento",
        "aviso_de_otra_area",
        "convocatoria_interna",
        "saludo_o_efemeride",
        "fallecimiento",
        "newsletter",
    )
    for tipo in tipos():
        forma = cargar_forma(tipo)
        entrada = cargar_entrada(tipo)

        assert forma["schema_version"] == f"forma_gacetilla_{tipo}_v1"
        assert forma["tipo"] == tipo
        assert forma["modo"] == modo_de(tipo)
        for parte in ("encabezado", "pie", "firmante", "formulas", "etiquetas"):
            assert parte in forma, f"{tipo} no declara {parte}"
        assert forma["firmante"].strip()
        assert forma["encabezado"]["asunto"] == "Asunto: {titulo}"

        assert entrada["x-tipo"] == tipo
        assert entrada["x-modo"] == modo_de(tipo)
        assert entrada["x-contract-version"].startswith("gacetilla_entrada_")
        assert campos_obligatorios(tipo), f"{tipo} no declara required"
        assert campos_que_no_aplican(tipo), f"{tipo} no declara campos que no aplican"
        assert set(campos_obligatorios(tipo)).isdisjoint(campos_que_no_aplican(tipo))


def test_los_campos_de_actividad_no_aplican_a_los_tipos_que_no_son_difusion():
    de_actividad = {"modalidad", "duracion_horas", "enlace_inscripcion", "fecha_inicio"}
    for tipo in tipos():
        if tipo == TIPO_DIFUSION:
            continue
        assert de_actividad <= set(campos_que_no_aplican(tipo)), tipo


def test_las_formulas_solo_referencian_campos_declarados_o_auxiliares():
    reservados = {"dia", "mes", "valor", "fecha_larga"}
    for tipo in tipos():
        forma = cargar_forma(tipo)
        plantillas = [str(forma["pie"]), *map(str, forma["formulas"].values())]
        plantillas += [str(valor) for valor in forma["encabezado"].values()]
        referencias: set[str] = set()
        for plantilla in plantillas:
            referencias.update(re.findall(r"\{([a-z_]+)\}", plantilla))
        declarados = set(campos_obligatorios(tipo)) | set(campos_que_no_aplican(tipo))
        # Un campo opcional del contrato tambien puede aparecer en una formula.
        opcionales = set(forma.get("fechas", ()))
        assert referencias <= declarados | reservados | opcionales, tipo


def test_las_intenciones_declaran_el_mismo_enum_de_tipos_que_el_contrato_congelado():
    catalogo = json.loads(
        (ROOT / "src" / "agente1" / "contracts" / "intenciones_v4.schema.json").read_text(
            encoding="utf-8"
        )
    )
    gacetilla = next(item for item in catalogo["intenciones"] if item["id"] == "generar_gacetilla")
    parametro = next(p for p in gacetilla["parametros"] if p["nombre"] == "tipo_gacetilla")

    assert parametro["enum"] == list(tipos())
    assert {item["id"] for item in catalogo["intenciones"]}.isdisjoint(
        {"generar_newsletter", "generar_mail"}
    )


# --- Conformidad de forma contra el corpus --------------------------------


@pytest.mark.parametrize("tipo", tipos())
def test_cada_tipo_renderiza_su_pieza_del_corpus_y_pasa_el_gate(tipo):
    pieza = _pieza(tipo)
    esperada = (GOLDEN / f"{tipo}.md").read_text(encoding="utf-8").rstrip("\n")

    assert pieza == esperada
    assert validar_pieza(tipo, pieza, _campos(tipo)) == []


def test_la_difusion_no_repite_la_frase_fija_de_invitacion_y_sigue_siendo_fie_informa():
    pieza = _pieza(TIPO_DIFUSION)
    forma = cargar_forma(TIPO_DIFUSION)

    assert "La Facultad de Ingeniería del Ejército invita a" not in pieza
    assert pieza.startswith("Asunto: ")
    assert f"Consultas: {_campos(TIPO_DIFUSION)['contacto']}" in pieza
    assert forma["pie"] in pieza
    assert forma["firmante"] in pieza


# --- Modo de produccion ----------------------------------------------------


@pytest.mark.parametrize(
    "tipo",
    [
        "cronica_de_evento",
        "aviso_de_otra_area",
        "convocatoria_interna",
        "fallecimiento",
        "newsletter",
    ],
)
def test_los_cinco_tipos_que_extraen_no_llaman_al_modelo_ni_necesitan_prompt(tipo):
    forma = cargar_forma(tipo)

    assert forma["modo"] == "extrae_y_confirma"
    assert forma["salida_modelo"] is None
    with pytest.raises(TipoNoGeneraError):
        generar_pieza(tipo, _campos(tipo), GeneratorQueNoDebeInvocarse())
    # El contrato de entrada lo declara y el fallback de interpretación no
    # interviene: los datos los carga quien pide.
    assert cargar_entrada(tipo)["x-interpretacion_fallback"] is False


@pytest.mark.parametrize("tipo", ["difusion_de_actividad", "saludo_o_efemeride"])
def test_los_dos_tipos_que_generan_tienen_prompt_versionado(tipo):
    forma = cargar_forma(tipo)
    prompt_version = forma["salida_modelo"]["prompt_version"]
    plantilla = (
        ROOT / "src" / "agente1" / "prompts" / f"{prompt_version}.txt"
    ).read_text(encoding="utf-8")

    assert plantilla.splitlines()[0] == f"PROMPT_VERSION: {prompt_version}"
    assert forma["modo"] == "genera"


def test_el_saludo_se_genera_con_su_prompt_corto_y_el_gate_lo_controla():
    with pytest.raises(TipoGeneraError):
        confirmar_pieza("saludo_o_efemeride", {"titulo": "Día del Ingeniero"})

    pieza, errores = generar_pieza(
        "saludo_o_efemeride",
        {"titulo": "Día del Ingeniero"},
        FakeGenerator(SALUDO),
    )
    assert errores == []
    assert SALUDO in pieza

    _, errores_largo = generar_pieza(
        "saludo_o_efemeride",
        {"titulo": "Día del Ingeniero"},
        FakeGenerator(" ".join(["palabra"] * 61) + "."),
    )
    assert errores_largo == ["prosa_muy_larga"]

    _, errores_datos = generar_pieza(
        "saludo_o_efemeride",
        {"titulo": "Día del Ingeniero"},
        FakeGenerator("Saludamos a la comunidad el 11 de junio."),
    )
    assert errores_datos == ["prosa_con_datos"]


def test_confirmar_pieza_falla_cerrado_si_falta_un_dato_confirmado():
    campos = dict(CASOS["fallecimiento"])
    campos.pop("nombre")

    pieza, errores = confirmar_pieza("fallecimiento", campos)

    assert pieza == ""
    assert errores == ["campos_obligatorios_ausentes"]


# --- Gate: nucleo comun mas reglas por tipo --------------------------------


def test_el_aviso_no_puede_afirmar_una_invitacion():
    pieza = _pieza("aviso_de_otra_area")
    pieza_invalida = pieza.replace(
        "Muchas gracias",
        "La Facultad de Ingeniería del Ejército invita a participar.\n\nMuchas gracias",
    )

    assert validar_pieza("aviso_de_otra_area", pieza_invalida, _campos("aviso_de_otra_area")) == [
        "aviso_afirma_invitacion"
    ]


def test_el_fallecimiento_no_puede_inventar_un_nombre():
    pieza = _pieza("fallecimiento")
    pieza_invalida = pieza.replace("María Ejemplo", "Otra Persona")

    assert validar_pieza("fallecimiento", pieza_invalida, _campos("fallecimiento")) == [
        "hecho_perdido",
        "fallecimiento_sin_nombre_confirmado",
    ]


def test_el_comunicado_no_puede_inventar_un_area_emisora():
    pieza = _pieza("newsletter")
    pieza_invalida = pieza.replace(
        "Secretaría de Extensión Universitaria", "Área Inventada"
    )

    assert validar_pieza("newsletter", pieza_invalida, _campos("newsletter")) == [
        "hecho_perdido",
        "emisor_area_no_confirmada",
    ]


def test_el_gate_compara_contra_lo_confirmado_y_no_contra_texto_generado():
    pieza = _pieza("cronica_de_evento")
    otros_campos = {
        "titulo": CASOS["cronica_de_evento"]["titulo"],
        "cuerpo": "Un texto distinto que nadie confirmó.",
    }

    assert validar_pieza("cronica_de_evento", pieza, otros_campos) == ["hecho_perdido"]


def test_el_aviso_sin_fecha_se_renderiza_sin_inventar_una_fecha():
    campos = dict(CASOS["aviso_de_otra_area"])
    campos.pop("fecha")

    pieza, errores = confirmar_pieza("aviso_de_otra_area", campos)

    assert errores == []
    assert "a partir del" not in pieza
    assert "hasta nuevo aviso" in pieza


def test_el_gate_rechaza_marcadores_sin_resolver_y_proceso_interno():
    pieza = _pieza("cronica_de_evento")

    assert validar_pieza(
        "cronica_de_evento", pieza.replace("NOTICIAS FIE", "<título>"), _campos("cronica_de_evento")
    ) == ["marcador_sin_resolver"]
    assert validar_pieza(
        "cronica_de_evento", pieza + "\nPendiente de validación.", _campos("cronica_de_evento")
    ) == ["proceso_interno"]


# --- El renderer es uno solo ----------------------------------------------


def test_el_renderer_de_difusion_no_tiene_frases_institucionales_literales():
    fuente = inspect.getsource(_renderizar_mail)

    for frase in (
        "Facultad de Ingeniería del Ejército",
        "Departamento de Cursos Complementarios",
        "Secretaría de Extensión Universitaria",
        "invita a",
        "Consultas:",
        "Fie informa",
    ):
        assert frase not in fuente, f"el renderer todavía hardcodea: {frase}"
