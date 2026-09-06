"""Contrato creativo v3: el modelo redacta en lugar de seleccionar.

v2 restringía gancho, prosa y CTA a un catálogo cerrado de dos opciones por
canal. La corrida live del 2026-08-17 mostró que eso colapsaba a una única
combinación por canal (`DEF-A1-011`). v3 libera la redacción sin tocar el gate
de hechos: los hechos institucionales los sigue agregando el renderer
determinista.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.posts import (
    CONTRATO_CREATIVO_V2,
    CONTRATO_CREATIVO_V3,
    PATRON_REFERENCIA_LUGAR,
    procesar_post_estructurado,
)


ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

CREATIVIDAD_LIBRE = {
    "gancho": "¿Buscás un espacio para compartir lo que sabés?",
    "prosa": (
        "Te invitamos a sumarte a una propuesta abierta, pensada para que "
        "puedas intercambiar experiencias y aprender junto a otras personas."
    ),
    "cta": "Sumate y participá de la propuesta.",
    "hashtags": ["#Aprender", "#Comunidad"],
}


def _generar(creatividad: dict[str, object], contrato, tmp_path: Path):
    return procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-001",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(
            json.dumps(creatividad, ensure_ascii=False, sort_keys=True)
        ),
        contrato=contrato,
    )


def test_v3_no_declara_catalogo_cerrado() -> None:
    assert CONTRATO_CREATIVO_V3.catalogo_por_canal is None
    assert CONTRATO_CREATIVO_V3.catalogo_version is None
    assert CONTRATO_CREATIVO_V2.catalogo_por_canal is not None


def test_v3_acepta_redaccion_original_fuera_de_todo_catalogo(tmp_path: Path) -> None:
    resultado = _generar(CREATIVIDAD_LIBRE, CONTRATO_CREATIVO_V3, tmp_path)

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "BORRADOR — NO PUBLICAR" in borrador
    assert CREATIVIDAD_LIBRE["gancho"] in borrador


def test_v2_sigue_rechazando_texto_fuera_del_catalogo(tmp_path: Path) -> None:
    """La liberación de v3 no debe haber aflojado v2."""
    resultado = _generar(CREATIVIDAD_LIBRE, CONTRATO_CREATIVO_V2, tmp_path)

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert "creative_slot_not_in_catalog" in registro["validation_errors"]


def test_v3_conserva_el_gate_de_hechos(tmp_path: Path) -> None:
    """Liberar la redacción no puede habilitar invención de hechos."""
    creatividad = dict(CREATIVIDAD_LIBRE)
    creatividad["prosa"] = "Nos encontramos el 5 de agosto a las 18:00 horas."

    resultado = _generar(creatividad, CONTRATO_CREATIVO_V3, tmp_path)

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert "unauthorized_number" in registro["validation_errors"]


@pytest.mark.parametrize(
    ("campo", "valor", "error"),
    [
        ("prosa", "Un seminario remoto para seguir aprendiendo junto a otras personas.", "unauthorized_fact_claim"),
        ("cta", "Inscribite ahora y asegurá tu lugar en esta propuesta.", "unauthorized_call_to_action"),
        ("cta", "Inscríbete y conocé nuevas propuestas para participar.", "non_rioplatense_register"),
        ("prosa", "Este taller propone un espacio abierto para compartir experiencias.", "source_fact_in_creative_field"),
    ],
)
def test_v3_rechaza_riesgos_linguisticos_y_fragmentos_de_hechos(
    campo: str, valor: str, error: str, tmp_path: Path
) -> None:
    """Regresiones de DEF-A1-012; no sustituyen la validación editorial SEU."""
    creatividad = dict(CREATIVIDAD_LIBRE)
    creatividad[campo] = valor

    resultado = _generar(creatividad, CONTRATO_CREATIVO_V3, tmp_path)

    assert resultado.estado == "FALLIDA"
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert error in registro["validation_errors"]


def test_v3_rechaza_texto_por_debajo_del_minimo(tmp_path: Path) -> None:
    creatividad = dict(CREATIVIDAD_LIBRE)
    creatividad["gancho"] = "Hola."

    resultado = _generar(creatividad, CONTRATO_CREATIVO_V3, tmp_path)

    assert resultado.estado == "FALLIDA"
    registro = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert "creative_field_invalid" in registro["validation_errors"]


def test_v3_audita_su_propia_version_de_contrato_y_prompt(tmp_path: Path) -> None:
    resultado = _generar(CREATIVIDAD_LIBRE, CONTRATO_CREATIVO_V3, tmp_path)
    registro = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )

    assert registro["output_contract_version"] == "post_creative_output_v3"
    assert registro["prompt_version"] == "post_instagram_structured_v3"
    assert registro["creative_catalog_version"] is None


@pytest.mark.parametrize(
    "texto",
    [
        "Nos vemos en el aula",
        "La actividad se hace desde la sede central",
        "Encuentro en el campus",
        "Charla en la biblioteca",
        "hacia el auditorio principal",
    ],
)
def test_patron_lugar_detecta_lugares_genericos(texto: str) -> None:
    assert PATRON_REFERENCIA_LUGAR.search(texto) is not None


@pytest.mark.parametrize(
    "texto",
    [
        "sumergirte en un mundo de conocimiento",
        "En esta actividad nos encontramos",
        "una propuesta pensada en comunidad",
        "trabajamos en conjunto",
        "en esta jornada de aprendizaje",
    ],
)
def test_patron_lugar_no_marca_sintagmas_que_no_son_lugares(texto: str) -> None:
    """El patrón anterior usaba `\\S+` y marcaba cualquier "en X" del español."""
    assert PATRON_REFERENCIA_LUGAR.search(texto) is None
