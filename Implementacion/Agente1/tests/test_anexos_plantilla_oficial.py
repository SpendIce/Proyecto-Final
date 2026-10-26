"""Entrega de los anexos del laboratorio sobre las plantillas oficiales.

La invariante que protege este archivo es la del reparto de columnas que fijó el
correo del laboratorio del 14/10 (issue #57): el equipo de proyecto completa los
ítems y **el laboratorio completa las últimas columnas**. Si el volcado escribiera
en las columnas del laboratorio, le estaría marcando la planilla al evaluador.

El archivo se saltea si `python-docx` no está disponible —los scripts lo tienen
como dependencia opcional— o si no están las plantillas oficiales de la cátedra.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
REPO = ROOT.parent.parent
PLANTILLAS = REPO / "Contenido" / "DocumentacionAnteproyecto" / "Revision-Laboratorio-2025"
PLANTILLA_1 = PLANTILLAS / "3.1 - Anexo 1 - Presentación 2025.docx"
PLANTILLA_2 = PLANTILLAS / "3.2 - Anexo 2 - Calidad 2025.docx"
PLANTILLA_3 = PLANTILLAS / "3.3 - Anexo 3 - Seguridad 2025.docx"

FUENTE_CALIDAD = REPO / "Documentos" / "Laboratorio" / "Perfil-Calidad-Sistema-Demostracion-v1.md"
FUENTE_SEGURIDAD = (
    REPO / "Documentos" / "Laboratorio" / "Perfil-Seguridad-Sistema-Demostracion-v1.md"
)


def _cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ROOT / "scripts" / f"{nombre}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def docx():  # noqa: ANN201
    return pytest.importorskip("docx", reason="python-docx es opcional")


@pytest.fixture(scope="module")
def plantillas():  # noqa: ANN201
    for plantilla in (PLANTILLA_1, PLANTILLA_2, PLANTILLA_3):
        if not plantilla.exists():
            pytest.skip(f"falta la plantilla oficial: {plantilla.name}")


def _celdas_del_laboratorio(tabla, desde: int, primera_del_autor: int) -> list[str]:
    """Devuelve el texto de las columnas que NO le tocan al equipo de proyecto."""

    return [
        celda.text.strip()
        for fila in list(tabla.rows)[desde:]
        for indice, celda in enumerate(fila.cells)
        if indice >= primera_del_autor and celda.text.strip()
    ]


def test_anexo3_deja_vacias_las_columnas_del_laboratorio(docx, plantillas, tmp_path):
    modulo = _cargar("anexo3_seguridad")
    filas = modulo.ordenar(
        modulo.parsear_fuente(FUENTE_SEGURIDAD.read_text(encoding="utf-8"))
    )
    destino = tmp_path / "Anexo3.docx"
    modulo.emitir_plantilla(filas, PLANTILLA_3, destino)

    tabla = docx.Document(str(destino)).tables[0]
    # Dos encabezados más el título combinado: se conservan.
    assert [c.text.strip() for c in tabla.rows[1].cells][:2] == ["Componente", "Ítem"]
    assert [c.text.strip() for c in tabla.rows[2].cells][2:5] == ["MB", "B", "M"]
    assert len(tabla.rows) - modulo.FILAS_ENCABEZADO_PLANTILLA == len(filas)
    assert _celdas_del_laboratorio(tabla, modulo.FILAS_ENCABEZADO_PLANTILLA, 2) == []
    # Las filas de ejemplo de la plantilla no viajan a la entrega.
    items = [fila.cells[1].text.strip() for fila in list(tabla.rows)[3:]]
    assert "Conexión por TLS" not in items


def test_anexo3_declara_el_almacenamiento_de_contrasenas_y_el_tls(docx, plantillas, tmp_path):
    """Los dos ítems que la plantilla siembra como ejemplo tienen fila propia."""

    modulo = _cargar("anexo3_seguridad")
    filas = modulo.ordenar(
        modulo.parsear_fuente(FUENTE_SEGURIDAD.read_text(encoding="utf-8"))
    )
    destino = tmp_path / "Anexo3.docx"
    modulo.emitir_plantilla(filas, PLANTILLA_3, destino)

    tabla = docx.Document(str(destino)).tables[0]
    items = [fila.cells[1].text.strip() for fila in list(tabla.rows)[3:]]
    assert "Almacenamiento de credenciales y contraseñas" in items
    assert any("TLS" in item for item in items)


def test_anexo2_deja_vacias_las_columnas_del_laboratorio(docx, plantillas, tmp_path):
    modulo = _cargar("anexo2_calidad")
    filas = modulo.proyectar(
        modulo.parsear_fuente(FUENTE_CALIDAD.read_text(encoding="utf-8"))
    )
    destino = tmp_path / "Anexo2.docx"
    modulo.emitir_plantilla(filas, PLANTILLA_2, destino)

    tabla = docx.Document(str(destino)).tables[0]
    assert tabla.rows[1].cells[0].text.strip() == "Factor de calidad"
    assert len(tabla.rows) - modulo.FILAS_ENCABEZADO_PLANTILLA == len(filas)
    assert _celdas_del_laboratorio(tabla, modulo.FILAS_ENCABEZADO_PLANTILLA, 2) == []


def test_anexo1_reemplaza_el_esqueleto_por_una_tabla_por_estrato(docx, plantillas, tmp_path):
    modulo = _cargar("anexo1_presentacion")
    por_estrato = modulo.proyectar_por_estrato(
        modulo.parsear_fuente(FUENTE_CALIDAD.read_text(encoding="utf-8"))
    )
    destino = tmp_path / "Anexo1.docx"
    modulo.emitir_plantilla(por_estrato, PLANTILLA_1, destino)

    doc = docx.Document(str(destino))
    assert len(doc.tables) == len(modulo.ORDEN_ESTRATOS)
    for tabla in doc.tables:
        assert [c.text.strip() for c in tabla.rows[1].cells] == [
            "Atributo",
            "Estado",
            "Motivo",
        ]
    # El .docx es un entregable de Word: no arrastra el marcado de Markdown.
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "**" not in texto and "`" not in texto


def _emitir_los_tres(tmp_path: Path) -> list[Path]:
    a1 = _cargar("anexo1_presentacion")
    a2 = _cargar("anexo2_calidad")
    a3 = _cargar("anexo3_seguridad")
    calidad = a2.parsear_fuente(FUENTE_CALIDAD.read_text(encoding="utf-8"))
    destinos = [tmp_path / "Anexo1.docx", tmp_path / "Anexo2.docx", tmp_path / "Anexo3.docx"]
    a1.emitir_plantilla(a1.proyectar_por_estrato(calidad), PLANTILLA_1, destinos[0])
    a2.emitir_plantilla(a2.proyectar(calidad), PLANTILLA_2, destinos[1])
    a3.emitir_plantilla(
        a3.ordenar(a3.parsear_fuente(FUENTE_SEGURIDAD.read_text(encoding="utf-8"))),
        PLANTILLA_3,
        destinos[2],
    )
    return destinos


def test_los_tres_anexos_declaran_el_ciclo_lectivo_vigente(docx, plantillas, tmp_path):
    """Las plantillas son las de 2025; la entrega no puede decir «Ciclo Lectivo 2025»."""

    ciclo = _cargar("plantilla_laboratorio").CICLO_LECTIVO
    for destino in _emitir_los_tres(tmp_path):
        encabezado = "\n".join(
            p.text for s in docx.Document(str(destino)).sections for p in s.header.paragraphs
        )
        assert f"Ciclo Lectivo {ciclo}" in encabezado, destino.name
        assert "Ciclo Lectivo 2025" not in encabezado, destino.name


def test_anexos_2_y_3_sin_texto_de_ejemplo_y_con_referencias(docx, plantillas, tmp_path):
    _, anexo2, anexo3 = _emitir_los_tres(tmp_path)
    for destino in (anexo2, anexo3):
        texto = "\n".join(p.text for p in docx.Document(str(destino)).paragraphs)
        assert "a modo de ejemplo" not in texto
        assert "El Equipo de Proyecto completará" not in texto
    assert "ISO/IEC 25010:2023" in "\n".join(
        p.text for p in docx.Document(str(anexo2)).paragraphs
    )
    assert "NIST Cybersecurity Framework" in "\n".join(
        p.text for p in docx.Document(str(anexo3)).paragraphs
    )


def test_falla_si_la_plantilla_tiene_otras_columnas(docx, tmp_path):
    """Una plantilla oficial distinta a la del 2025 tiene que fallar ruidosamente."""

    modulo = _cargar("plantilla_laboratorio")
    doc = docx.Document()
    tabla = doc.add_table(rows=1, cols=3)
    for indice, texto in enumerate(("Otra", "Plantilla", "Cualquiera")):
        tabla.rows[0].cells[indice].text = texto

    with pytest.raises(SystemExit):
        modulo.verificar_columnas(tabla, ["Componente", "Ítem"])
