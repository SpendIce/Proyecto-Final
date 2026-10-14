"""Set de evaluación de gacetillas contra el corpus FIE INFORMA (issue #111).

El set vive en `data/corpus-fie-informa-difusiones.csv` con el encabezado
exacto de `COLUMNAS_ACTIVIDADES_V2`, de modo que cada caso corre por el mismo
pipeline HU-010 que `actividades_sinteticas.csv`. Estos chequeos NO reinventan
un validador: ejercitan el gate existente (`procesar_fila_csv` y sus
validaciones) y agregan las regresiones del set —procedencia por campo, slots
por tipo, manifest congelado por hash y la regresión nueva de que la salida no
reproduce las erratas del corpus, que necesita #105—.

Los chequeos son de contrato, no de calidad: no puntúan parecido a un FIE
INFORMA. Eso lo hace la rúbrica humana, sujeta a la aprobación de Juani.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import pytest

from agente1 import FakeGenerator, procesar_fila_csv
from agente1.destinos import BORRADOR_MARKER
from agente1.fuentes import COLUMNAS_ACTIVIDADES_V2, CsvFuenteSolicitudes
from agente1.posts import PATRON_TUTEO
from agente1.procesamiento import (
    _FIRMA_INSTITUCIONAL,
    _PIE_DIFUSION,
    CONTRATO_ENTRADA,
    MAX_BORRADOR_CHARS,
    PATRON_PROSA_SIN_DATOS,
    PREFIJO_BORRADOR_DOC,
    _nombre_doc,
    _validar_render_mail,
    _validar_salida,
)

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "corpus-fie-informa-difusiones.csv"
PROCEDENCIA = ROOT / "data" / "corpus-fie-informa-difusiones.procedencia.csv"
MANIFEST = (
    ROOT / "evidencias" / "manifest-set-evaluacion-gacetillas-fie-informa-2026-10-14.json"
)
DOCUMENTO = (
    ROOT / "evidencias" / "set-evaluacion-gacetillas-fie-informa-2026-10-14.md"
)

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _leer_filas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


FILAS = _leer_filas(DATASET)
IDS = [fila["id_actividad"] for fila in FILAS]
CAMPOS_REQUIRED = tuple(CONTRATO_ENTRADA["required"])
ORIGENES = frozenset({"flyer", "provisional", "no_informado", "sintetico"})

# Campos declarados provisionales: los que el flyer no trae y hay que completar
# para cubrir el `required` del contrato o para fijar un hecho del correo.
# `publico` falta en los 8 flyers; la `modalidad` se infiere del lugar en 5
# casos; el `contacto` de área se declara en los 3 que no lo informan.
PROVISIONALES_ESPERADOS = (
    {(caso, "publico") for caso in IDS if caso != "FIE-DIF-07"}
    | {(caso, "modalidad") for caso in ("FIE-DIF-03", "FIE-DIF-04", "FIE-DIF-05", "FIE-DIF-06", "FIE-DIF-08")}
    | {(caso, "contacto") for caso in ("FIE-DIF-04", "FIE-DIF-05", "FIE-DIF-06")}
)

# Erratas del corpus (Documentos/PoC/Corpus-FIE-Informa-Historico-2026-10-13.md
# §5) que el agente no debe perpetuar: el corpus es referencia de formato, no de
# ortografía. Regresión nueva que necesita #105.
ERRATAS_CORPUS = ("visitaros", "FRACIA", "NOTIFICAS", "elpe", "Secretaria", "activiad")

# Vocabulario de proceso interno (DEF-A1-017): no puede aparecer en la prosa de
# lectura pública. El marcador `BORRADOR — NO PUBLICAR` se descuenta porque es
# metadato del artefacto, no prosa del correo.
TERMINOS_PROCESO_INTERNO = ("revisión", "validación", "aprobación", "borrador", "pendiente")

TIPOS_FIE_INFORMA = (
    "difusion de actividad",
    "cronica",
    "aviso/comunicado",
    "saludo/efemeride",
    "convocatoria interna",
    "fallecimiento",
)


def _ficha_conforme(fila: dict[str, str]) -> str:
    """Arma la ficha que el pipeline valida, con los hechos de la fila.

    Reemplaza la salida del modelo con un texto determinista de forma: la prosa
    es neutra y sin datos (así pasa `PATRON_PROSA_SIN_DATOS`), y los hechos
    —título, fecha, organiza, lugar, contacto— se copian de la fila para que el
    gate los acepte. No se usa para puntuar calidad.
    """

    lineas = [
        "## TÍTULO",
        fila["titulo"],
        "",
        "## DATOS DE LA ACTIVIDAD",
        f"Fecha: {fila['fecha_inicio']}",
        f"Organiza: {fila['organiza']}",
    ]
    if fila["lugar"].strip():
        lineas.append(f"Lugar: {fila['lugar']}")
    lineas += [
        "",
        "## CONTACTO",
        fila["contacto"],
        "",
        "## BAJADA",
        "Una propuesta institucional para acercar la actividad a la comunidad.",
        "",
        "## CUERPO",
        "La facultad acompaña la actividad con información institucional y un "
        "espacio de consulta para el público asistente.",
    ]
    return "\n".join(lineas)


def _correr_caso(fila: dict[str, str], tmp_path: Path) -> tuple[str, str]:
    """Corre un caso por el pipeline HU-010 y devuelve `(estado, correo)`."""

    resultado = procesar_fila_csv(
        csv_path=DATASET,
        id_solicitud=fila["id_actividad"],
        directorio_salida=tmp_path / fila["id_actividad"],
        generator=FakeGenerator(_ficha_conforme(fila)),
    )
    assert resultado.borrador_path is not None, resultado.error
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert borrador.startswith(BORRADOR_MARKER)
    correo = borrador[len(BORRADOR_MARKER):].rstrip("\n")
    return resultado.estado, correo


def test_el_csv_tiene_el_encabezado_exacto_del_contrato_v2():
    with DATASET.open(encoding="utf-8", newline="") as archivo:
        encabezados = next(csv.reader(archivo))

    assert tuple(encabezados) == COLUMNAS_ACTIVIDADES_V2
    assert len(encabezados) == 15


def test_todos_los_casos_traen_los_required_completos_y_ids_unicos():
    filas = CsvFuenteSolicitudes(DATASET).enumerar()

    assert len(filas) == 8
    assert len({fila["id_actividad"] for fila in filas}) == 8
    for fila in filas:
        for campo in CAMPOS_REQUIRED:
            assert fila[campo].strip(), f"{fila['id_actividad']} sin {campo}"


@pytest.mark.parametrize("fila", FILAS, ids=IDS)
def test_cada_caso_corre_por_el_pipeline_y_no_pierde_hechos(fila, tmp_path):
    estado, correo = _correr_caso(fila, tmp_path)

    assert estado == "PENDIENTE_VALIDACION"
    # `renderer_fact_missing` = 0: ningún dato de la fila se perdió ni se alteró
    # entre la ficha validada y el correo guardado.
    assert _validar_render_mail(correo, fila) == []
    assert len(correo) <= MAX_BORRADOR_CHARS


@pytest.mark.parametrize("fila", FILAS, ids=IDS)
def test_la_ficha_conforme_pasa_el_gate_sin_errores(fila):
    assert _validar_salida(_ficha_conforme(fila), fila) == []


@pytest.mark.parametrize("fila", FILAS, ids=IDS)
def test_el_correo_no_usa_tuteo_ni_meta_lenguaje_de_proceso(fila, tmp_path):
    _, correo = _correr_caso(fila, tmp_path)
    plano = correo.lower()

    assert PATRON_TUTEO.search(correo) is None
    for termino in TERMINOS_PROCESO_INTERNO:
        assert termino not in plano, f"meta-lenguaje de proceso: {termino}"


@pytest.mark.parametrize("fila", FILAS, ids=IDS)
def test_la_prosa_de_la_ficha_no_lleva_datos_concretos(fila):
    ficha = _ficha_conforme(fila)
    bajada = ficha.split("## BAJADA")[1].split("## CUERPO")[0]
    cuerpo = ficha.split("## CUERPO")[1]

    assert PATRON_PROSA_SIN_DATOS.search(bajada) is None
    assert PATRON_PROSA_SIN_DATOS.search(cuerpo) is None


@pytest.mark.parametrize("fila", FILAS, ids=IDS)
def test_el_correo_lleva_pie_fijo_firma_y_consultas_igual_al_contacto(fila, tmp_path):
    _, correo = _correr_caso(fila, tmp_path)

    assert f"Consultas: {fila['contacto']}" in correo
    assert _PIE_DIFUSION in correo
    assert _FIRMA_INSTITUCIONAL in correo


def test_el_nombre_del_doc_sigue_la_convencion_del_corpus():
    generado_en = date(2026, 10, 14)
    for fila in FILAS:
        nombre = _nombre_doc(fila, generado_en)

        assert nombre.startswith(PREFIJO_BORRADOR_DOC)
        assert nombre == f"BORRADOR — Fie informa 14-10 {fila['titulo']}"


def test_el_set_no_reproduce_erratas_del_corpus(tmp_path):
    texto_dataset = DATASET.read_text(encoding="utf-8")

    for errata in ERRATAS_CORPUS:
        assert errata not in texto_dataset, f"errata transcrita al set: {errata}"
    for fila in FILAS:
        _, correo = _correr_caso(fila, tmp_path / fila["id_actividad"])
        for errata in ERRATAS_CORPUS:
            assert errata not in correo, f"la salida reproduce la errata: {errata}"


def test_la_procedencia_esta_declarada_por_campo_y_marca_los_provisionales():
    filas = _leer_filas(PROCEDENCIA)

    assert {fila["id_actividad"] for fila in filas} == set(IDS)
    assert len(filas) == len(IDS) * len(COLUMNAS_ACTIVIDADES_V2)
    por_caso: dict[str, set[str]] = {}
    for fila in filas:
        assert fila["origen"] in ORIGENES
        por_caso.setdefault(fila["id_actividad"], set()).add(fila["campo"])
        if fila["origen"] == "no_informado":
            assert fila["campo"] not in CAMPOS_REQUIRED
    for caso, campos in por_caso.items():
        assert campos == set(COLUMNAS_ACTIVIDADES_V2), caso
    provisionales = {
        (fila["id_actividad"], fila["campo"])
        for fila in filas
        if fila["origen"] == "provisional"
    }
    assert provisionales == PROVISIONALES_ESPERADOS


def test_el_manifest_esta_congelado_por_hash_y_no_copia_contenido():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    serializado = json.dumps(manifest, ensure_ascii=False)

    assert manifest["schema_version"] == "set_evaluacion_fie_informa_v1"
    assert manifest["artefactos"]["dataset_sha256"] == _sha256(DATASET)
    assert manifest["artefactos"]["procedencia_sha256"] == _sha256(PROCEDENCIA)
    assert manifest["artefactos"]["documento_sha256"] == _sha256(DOCUMENTO)
    assert manifest["corpus"]["zip_sha256"] == (
        "aa8c64fa1ef79dbfa8e91be484b85a2cfebd18d5979b5cb4b4c63471a80fac46"
    )
    assert manifest["corpus"]["piezas_incluidas"]
    for pieza in manifest["corpus"]["piezas_incluidas"]:
        assert re.fullmatch(r"[0-9a-f]{64}", pieza["sha256"])
    # El manifest cita el hash de los originales, no copia su contenido ni
    # datos de contacto/enlaces (repo público).
    assert "@" not in serializado
    assert "http" not in serializado


def test_los_slots_por_tipo_estan_documentados_sin_casos_de_tipos_sin_pipeline():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    slots = manifest["slots_por_tipo"]

    assert tuple(slots) == TIPOS_FIE_INFORMA
    assert slots["difusion de actividad"]["casos"] > 0
    for tipo, slot in slots.items():
        if tipo != "difusion de actividad":
            assert slot["casos"] == 0
            assert slot["motivo"]
            assert slot["pipeline_existe"] is False


def test_el_documento_del_set_declara_los_bloques_obligatorios():
    texto = DOCUMENTO.read_text(encoding="utf-8")

    for bloque in (
        "Criterio de inclusión",
        "Piezas dudosas excluidas",
        "Procedencia por campo",
        "Slots por tipo",
        "Campos provisionales",
        "Rúbrica humana",
        "Chequeos automáticos",
        "aprobación de Juani",
    ):
        assert bloque in texto, f"falta el bloque: {bloque}"
    for dimension in (
        "parecido a un FIE INFORMA",
        "fidelidad de sentido",
        "claridad y uso",
    ):
        assert dimension in texto
