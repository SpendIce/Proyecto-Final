"""El gate de registro no confunde la tercera persona con el imperativo (#51).

«explora», «comparte» o «participa» son a la vez imperativo con tuteo y
tercera persona del indicativo. Sólo cuentan como tuteo al comienzo de una
oración o cláusula; en el cribado del 20/10 «esta actividad explora la
integración industrial» tumbaba un post de LinkedIn correcto.
"""

from __future__ import annotations

import pytest

from agente1.linea_descriptiva import validar_linea_descriptiva
from agente1.posts import PATRON_TUTEO


@pytest.mark.parametrize(
    "texto",
    [
        "esta actividad explora la integración industrial",
        "la jornada comparte experiencias del sector",
        "el curso aprende de casos reales y conoce su contexto",
        "sumate y enterate de las propuestas",
    ],
)
def test_tercera_persona_y_voseo_no_son_tuteo(texto: str) -> None:
    assert PATRON_TUTEO.search(texto) is None


@pytest.mark.parametrize(
    "texto",
    [
        "Explora nuestras propuestas de formación",
        "Te esperamos. Participa de la charla",
        "¿Querés saber más? Descubre el programa",
        "Es una propuesta abierta, conoce a los referentes",
        "Inscríbete en el enlace",
        "si puedes, vení",
    ],
)
def test_imperativo_y_segunda_persona_con_tuteo_siguen_rechazandose(texto: str) -> None:
    assert PATRON_TUTEO.search(texto) is not None


def test_linea_descriptiva_en_tercera_persona_pasa_el_gate_de_registro() -> None:
    errores = validar_linea_descriptiva(
        "Formación que explora la gestión de infraestructuras en entornos polares."
    )
    assert "non_rioplatense_register" not in errores
