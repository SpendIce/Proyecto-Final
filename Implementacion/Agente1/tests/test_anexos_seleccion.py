"""Selección de lo que se declara en los anexos del laboratorio.

Blinda la decisión de recorte: que ninguno de los nombres elegidos quede sin fila
en el perfil (un nombre mal escrito recortaría de menos en silencio), que no se
caiga ningún componente, que se respete el tope, y que estén los dos ítems que el
laboratorio siembra en su propia plantilla como ejemplo.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
REPO = ROOT.parent.parent
PERFIL_CALIDAD = (
    REPO / "Documentos" / "Laboratorio" / "Perfil-Calidad-Sistema-Demostracion-v1.md"
)
PERFIL_SEGURIDAD = (
    REPO / "Documentos" / "Laboratorio" / "Perfil-Seguridad-Sistema-Demostracion-v1.md"
)


def _cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ROOT / "scripts" / f"{nombre}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def seleccion():
    return _cargar("anexos_seleccion")


@pytest.fixture(scope="module")
def filas():
    calidad = _cargar("anexo2_calidad")
    seguridad = _cargar("anexo3_seguridad")
    return {
        "calidad": calidad.parsear_fuente(PERFIL_CALIDAD.read_text(encoding="utf-8")),
        "seguridad": seguridad.parsear_fuente(
            PERFIL_SEGURIDAD.read_text(encoding="utf-8")
        ),
    }


@pytest.mark.usefixtures("requiere_repo_documentos")
def test_la_seleccion_resuelve_contra_los_perfiles_reales(seleccion, filas):
    """Un nombre mal escrito tiene que fallar, no recortar de menos en silencio."""

    calidad = seleccion.seleccionar_calidad(filas["calidad"])
    seguridad = seleccion.seleccionar_seguridad(filas["seguridad"])

    esperado_calidad = sum(len(v) for v in seleccion.SELECCION_CALIDAD.values())
    esperado_seguridad = sum(len(v) for v in seleccion.SELECCION_SEGURIDAD.values())
    assert len(calidad) == esperado_calidad
    assert len(seguridad) == esperado_seguridad


@pytest.mark.usefixtures("requiere_repo_documentos")
def test_no_se_cae_ningun_componente(seleccion, filas):
    """Cada componente que el perfil declara tiene que aparecer en el anexo."""

    for clave, seleccionar, atributo, mapa in (
        (
            "calidad",
            seleccion.seleccionar_calidad,
            "atributo",
            seleccion.SELECCION_CALIDAD,
        ),
        (
            "seguridad",
            seleccion.seleccionar_seguridad,
            "item",
            seleccion.SELECCION_SEGURIDAD,
        ),
    ):
        componentes_fuente = {f.estrato for f in filas[clave]}
        seleccionadas = seleccionar(filas[clave])
        assert {f.estrato for f in seleccionadas} == componentes_fuente

        # El orden no lo fija esta lista sino el perfil (el del estándar en
        # calidad y el de los factores en seguridad): acá se compara el conjunto.
        for componente, declarados in mapa.items():
            en_anexo = {
                getattr(f, atributo)
                for f in seleccionadas
                if f.estrato == componente
            }
            assert en_anexo == set(declarados), componente


def test_se_respeta_el_tope_por_componente(seleccion):
    for mapa in (seleccion.SELECCION_CALIDAD, seleccion.SELECCION_SEGURIDAD):
        for componente, declarados in mapa.items():
            assert 1 <= len(declarados) <= seleccion.TOPE_POR_COMPONENTE, componente


def test_estan_los_dos_items_que_la_plantilla_siembra_como_ejemplo(seleccion):
    """La plantilla oficial del Anexo 3 trae «almacenamiento seguro de contraseñas»
    y «conexión por TLS» como filas de ejemplo: son las que el laboratorio mira.
    """

    declarados = {
        item for declarados in seleccion.SELECCION_SEGURIDAD.values() for item in declarados
    }
    assert any("contrase" in item.lower() for item in declarados)
    assert any("TLS" in item for item in declarados)
