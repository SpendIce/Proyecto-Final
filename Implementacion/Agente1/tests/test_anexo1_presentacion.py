"""Anexo 1 del laboratorio — presentación por estrato.

Cubre: el parseo de la tabla fuente compartida con el Anexo 2, la proyección
por estrato en el orden del inventario, la remisión de la seguridad al Anexo 3
sin duplicar la fila que ya viene en la fuente, y que la tabla real no pierda
ninguna fila ni ningún estrato.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
REPO = ROOT.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "anexo1_presentacion", ROOT / "scripts" / "anexo1_presentacion.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_modulo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_modulo)

INICIO = "<!-- TABLA-FUENTE:INICIO -->"
FIN = "<!-- TABLA-FUENTE:FIN -->"
ENCABEZADO = (
    "| Estrato | Característica | Atributo | Estado | Motivo | Evidencia versionada | "
    "Paso en vivo (< 2 min) |\n|---|---|---|---|---|---|---|"
)


def _fuente(rows: list[tuple[str, str, str, str, str]]) -> str:
    lineas = [INICIO, "", ENCABEZADO]
    for estrato, caracteristica, atributo, estado, motivo in rows:
        lineas.append(
            f"| {estrato} | {caracteristica} | {atributo} | {estado} | {motivo} | tests/x.py | paso |"
        )
    lineas.append(FIN)
    return "\n".join(lineas)


def _fuente_completa(estados: dict[str, str] | None = None) -> str:
    estados = estados or {}
    rows = [
        (
            estrato,
            "Característica X",
            f"Atributo {n}",
            estados.get(estrato, "A"),
            f"motivo {n}",
        )
        for n, estrato in enumerate(_modulo.ORDEN_ESTRATOS)
    ]
    return _fuente(rows)


def test_parsea_las_filas_de_la_tabla_fuente():
    filas = _modulo.parsear_fuente(_fuente_completa())
    assert len(filas) == len(_modulo.ORDEN_ESTRATOS)
    assert filas[0].estrato == "Canal"
    assert filas[0].estado == "A"
    assert filas[0].atributo == "Atributo 0"


def test_proyecta_en_el_orden_del_inventario():
    por_estrato = _modulo.proyectar_por_estrato(
        _modulo.parsear_fuente(_fuente_completa())
    )
    assert [estrato for estrato, _ in por_estrato] == _modulo.ORDEN_ESTRATOS


def test_remite_la_seguridad_al_anexo_3_en_todos_los_estratos():
    por_estrato = _modulo.proyectar_por_estrato(
        _modulo.parsear_fuente(_fuente_completa())
    )
    for estrato, rows in por_estrato:
        seguridad = [r for r in rows if r[0] == "Seguridad"]
        assert len(seguridad) == 1, estrato
        assert seguridad[0][2] == "Remite"
        assert "Anexo 3" in seguridad[0][3]


def test_no_duplica_una_fila_de_seguridad_ya_presente():
    rows = [
        (
            estrato,
            "Seguridad" if estrato == "Sistema" else "Característica X",
            "Seguridad (factor completo)" if estrato == "Sistema" else f"Atributo {n}",
            "Remite" if estrato == "Sistema" else "A",
            "ya declarada en la fuente",
        )
        for n, estrato in enumerate(_modulo.ORDEN_ESTRATOS)
    ]
    por_estrato = dict(_modulo.proyectar_por_estrato(_modulo.parsear_fuente(_fuente(rows))))
    sistema = [r for r in por_estrato["Sistema"] if r[0] == "Seguridad"]
    assert len(sistema) == 1
    assert sistema[0][3] == "ya declarada en la fuente"


def test_falla_si_falta_un_estrato():
    filas = _modulo.ORDEN_ESTRATOS[:-1]  # sin `Sistema`
    rows = [(estrato, "Característica X", "Atributo", "A", "motivo") for estrato in filas]
    with pytest.raises(ValueError, match="Sistema"):
        _modulo.proyectar_por_estrato(_modulo.parsear_fuente(_fuente(rows)))


@pytest.mark.usefixtures("requiere_repo_documentos")
def test_la_fuente_real_conserva_todas_las_filas_y_estratos():
    fuente = (
        REPO / "Documentos" / "Laboratorio" / "Perfil-Calidad-Sistema-Demostracion-v1.md"
    ).read_text(encoding="utf-8")
    filas = _modulo.parsear_fuente(fuente)
    por_estrato = _modulo.proyectar_por_estrato(filas)

    assert [estrato for estrato, _ in por_estrato] == _modulo.ORDEN_ESTRATOS
    declarados = sum(
        1 for _, rows in por_estrato for r in rows if r[3] != _modulo.MOTIVO_SEGURIDAD_REMITE
    )
    remisiones = sum(
        1 for _, rows in por_estrato for r in rows if r[3] == _modulo.MOTIVO_SEGURIDAD_REMITE
    )
    # Cada fila de la fuente aparece una vez; la remisión es la única fila que no
    # sale de la fuente, y sólo la agregan los estratos que no la traen ya.
    assert declarados == len(filas)
    assert remisiones == len(_modulo.ORDEN_ESTRATOS) - 1


def test_el_markdown_lleva_el_encabezado_de_la_plantilla_y_escapa_pipes():
    por_estrato = _modulo.proyectar_por_estrato(
        _modulo.parsear_fuente(_fuente_completa())
    )
    caracteristica, atributo, estado, _ = por_estrato[0][1][0]
    por_estrato[0][1][0] = (caracteristica, atributo, estado, "motivo con | pipe")
    markdown = _modulo.emitir_markdown(por_estrato)
    assert "# Evaluación del Proyecto: Presentación" in markdown
    assert "## Título del Proyecto" in markdown
    assert "## Lista de Control" in markdown
    assert "motivo con \\| pipe" in markdown
