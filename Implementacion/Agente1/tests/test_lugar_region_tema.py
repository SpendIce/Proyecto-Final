"""DEF-A1-026: una región amplia después de «en» es tema, no sede.

En la validación final de #51 (20/10, gemma4:e4b, FIE-DIF-06) los cuatro posts
se rechazaron por `unauthorized_place` porque decían «la soberanía en la
Patagonia y la Antártida», que es el tema de la actividad.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.posts import (
    CONTRATO_CREATIVO_V3,
    menciona_lugar_propio,
    procesar_post_estructurado,
)

CORPUS = Path(__file__).parents[1] / "data" / "corpus-fie-informa-difusiones.csv"


@pytest.mark.parametrize(
    "texto",
    [
        "los desafíos logísticos para asegurar la soberanía en la Patagonia y la Antártida",
        "el desarrollo de capacidades en Argentina",
        "la presencia científica en la Antártida",
        "la historia del conflicto en Malvinas",
    ],
)
def test_region_tema_no_es_lugar(texto: str) -> None:
    assert not menciona_lugar_propio(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "nos encontramos en el Hall de Banderas",
        "una charla en Córdoba",
        "desde el Centro Educativo de las Fuerzas Armadas",
        "la soberanía en la Patagonia y el encuentro en Palermo",
    ],
)
def test_sede_o_ciudad_sigue_siendo_lugar(texto: str) -> None:
    assert menciona_lugar_propio(texto)


@pytest.mark.parametrize("canal", ["instagram", "linkedin"])
def test_post_de_fie_dif_06_con_la_region_como_tema_pasa(canal: str, tmp_path: Path) -> None:
    creatividad = {
        "gancho": "¿Cómo se articulan la energía y la logística en el desarrollo del país?",
        "prosa": (
            "Se presenta un ciclo de encuentros sobre la transición hacia fuentes "
            "renovables y los desafíos logísticos para asegurar la soberanía en la "
            "Patagonia y la Antártida."
        ),
        "cta": "Encontrá más detalles sobre esta serie de charlas en el enlace.",
        "hashtags": ["#FIE"],
    }

    resultado = procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(CORPUS),
        id_solicitud="FIE-DIF-06",
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(json.dumps(creatividad, ensure_ascii=False)),
        contrato=CONTRATO_CREATIVO_V3,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION", resultado.log_path.read_text(encoding="utf-8")
