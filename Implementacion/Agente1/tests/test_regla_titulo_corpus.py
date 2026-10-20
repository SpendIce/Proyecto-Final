"""Regla de repetición del título con títulos reales del corpus FIE INFORMA (#139).

El cribado de modelos del 20/10 (#51) con actividades reales mostró que la
regla vieja —una sola palabra significativa del título rechazaba— tumbaba
salidas correctas que nombraban el tema («Formación en infraestructuras
antárticas…»). La regla nueva rechaza el título completo o un tramo literal
con tres o más palabras significativas, y deja pasar la mención del tema. Los
tres consumidores comparten la función: posts (HU-011), línea descriptiva
(HU-014) y plantilla de actividad (HU-012).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.linea_descriptiva import validar_linea_descriptiva
from agente1.plantillas_actividad import _validar_plantilla
from agente1.posts import (
    CONTRATO_CREATIVO_V3,
    _contiene_fragmento_significativo,
    procesar_post_estructurado,
)

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "data" / "corpus-fie-informa-difusiones.csv"


def _fila(id_actividad: str) -> dict[str, str]:
    with CORPUS.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["id_actividad"] == id_actividad:
                return fila
    raise AssertionError(f"{id_actividad} no está en el corpus")


# Salidas reales de qwen2.5:7b del cribado del 20/10 (líneas HU-014) y
# variantes que copian el título. (id, texto, ¿se rechaza?)
CASOS = [
    ("FIE-DIF-02", "Formación en inteligencia artificial para gestión documental sin costo.", False),
    ("FIE-DIF-02", "Inteligencia artificial aplicada a la gestión documental para equipos.", True),
    ("FIE-DIF-03", "Exploración y futuros retos tecnológicos y científicos en la conquista del espacio.", False),
    ("FIE-DIF-03", "Los desafíos de la conquista del espacio, explicados para todos.", True),
    ("FIE-DIF-07", "Formación en infraestructuras antárticas con clases virtuales y trabajo final.", False),
    ("FIE-DIF-07", "Una diplomatura universitaria en infraestructuras antárticas.", True),
    ("FIE-DIF-04", "Celebramos el Día de la Escarapela con la comunidad.", True),
]


@pytest.mark.parametrize(("id_actividad", "texto", "rechaza"), CASOS)
def test_fragmento_del_titulo_real(id_actividad: str, texto: str, rechaza: bool) -> None:
    assert _contiene_fragmento_significativo(texto, _fila(id_actividad)["titulo"]) is rechaza


@pytest.mark.parametrize(("id_actividad", "texto", "rechaza"), CASOS)
def test_linea_descriptiva_con_titulo_real(
    id_actividad: str, texto: str, rechaza: bool
) -> None:
    errores = validar_linea_descriptiva(
        texto, titulo_actividad=_fila(id_actividad)["titulo"]
    )
    assert ("source_fact_in_creative_field" in errores) is rechaza


PLANTILLA_BASE = (
    "Hola {{nombre_destinatario}},\n\n"
    "Te escribimos por tu preinscripción a {{actividad}}, que comienza el "
    "{{fecha_inicio}}.\n\n"
    "La propuesta acerca herramientas de la facultad a la comunidad, con "
    "encuentros guiados y espacios de consulta durante todo el recorrido.\n\n"
    "{frase}\n\n"
    "Contacto: {{contacto}}\n"
)


@pytest.mark.parametrize(
    ("frase", "rechaza"),
    [
        ("El recorrido se centra en las infraestructuras antárticas y su mantenimiento.", False),
        ("Es una diplomatura universitaria en infraestructuras antárticas.", True),
    ],
)
def test_plantilla_de_actividad_con_titulo_real(frase: str, rechaza: bool) -> None:
    contenido = PLANTILLA_BASE.replace("{frase}", frase)
    errores = _validar_plantilla(contenido, _fila("FIE-DIF-07"), None)
    assert ("source_fact_in_template" in errores) is rechaza


CREATIVIDAD = {
    "gancho": "¿Te interesa el trabajo en la Antártida?",
    "prosa": "",
    "cta": "Sumate y participá de la propuesta.",
    "hashtags": ["#FIE", "#UNDEF"],
}


def _post(prosa: str, tmp_path: Path):
    creatividad = dict(CREATIVIDAD, prosa=prosa)
    return procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(CORPUS),
        id_solicitud="FIE-DIF-07",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(json.dumps(creatividad, ensure_ascii=False)),
        contrato=CONTRATO_CREATIVO_V3,
    )


def _errores(resultado) -> list[str]:
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8").splitlines()[-1])
    return list(registro.get("validation_errors") or [])


def test_post_que_nombra_el_tema_no_se_rechaza_por_el_titulo(tmp_path: Path) -> None:
    resultado = _post(
        "Una propuesta para aprender sobre infraestructuras antárticas junto a otras personas.",
        tmp_path,
    )
    assert "source_fact_in_creative_field" not in _errores(resultado)


def test_post_que_copia_el_titulo_se_rechaza(tmp_path: Path) -> None:
    resultado = _post(
        "Llega la diplomatura universitaria en infraestructuras antárticas para la comunidad.",
        tmp_path,
    )
    assert resultado.estado == "FALLIDA"
    assert "source_fact_in_creative_field" in _errores(resultado)
