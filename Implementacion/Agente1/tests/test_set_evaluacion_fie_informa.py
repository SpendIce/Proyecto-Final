"""Set de evaluación de gacetillas contra el corpus FIE INFORMA (issue #111).

El set vive en `data/corpus-fie-informa-difusiones.csv` con el encabezado
exacto de `COLUMNAS_ACTIVIDADES_V2`, de modo que cada caso de difusión corre
por el mismo pipeline HU-010 que `actividades_sinteticas.csv`. Estos chequeos
NO reinventan un validador: ejercitan el gate existente (`procesar_fila_csv`
y sus validaciones) y agregan las regresiones del set —procedencia por campo,
slots por tipo, manifest congelado por hash y la regresión nueva de que la
salida no reproduce las erratas del corpus, que necesita #105—.

Desde el adendo del 17/10 (#120 con #121) el set tiene dos ejes: el eje 1
(rúbrica humana 1 a 4) sólo sobre los tipos que generan, y el eje 2
(conformidad de forma, binario y automático) sobre los siete tipos del
contrato `tipos_gacetilla_v1`. Los chequeos de acá son de contrato, no de
calidad: no puntúan parecido a un FIE INFORMA; eso lo hace la rúbrica humana
aprobada por Juani el 16/10, cuyas corridas de medición todavía no corrieron.
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
CONTRATO_TIPOS = ROOT / "src" / "agente1" / "contracts" / "tipos_gacetilla_v1.json"
PROMPT_SALUDO = ROOT / "src" / "agente1" / "prompts" / "saludo_o_efemeride_v1.txt"

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _leer_filas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _tipos_del_contrato() -> list[dict]:
    contrato = json.loads(CONTRATO_TIPOS.read_text(encoding="utf-8"))
    return contrato["tipos"]


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


def test_los_slots_por_tipo_cubren_los_siete_tipos_del_contrato_con_los_dos_ejes():
    modos = {tipo["id"]: tipo["modo"] for tipo in _tipos_del_contrato()}
    manifest = _manifest()
    slots = manifest["slots_por_tipo"]

    assert tuple(slots) == tuple(modos)
    for tipo, slot in slots.items():
        assert slot["modo"] == modos[tipo], tipo
        assert (ROOT / slot["forma_declarada"]).is_file(), tipo
        assert (ROOT / slot["golden"]).is_file(), tipo
        assert slot["eje_2"]["casos"] >= 1, tipo
    # El eje 1 (rúbrica) sólo tiene casos en los tipos que generan.
    for tipo, slot in slots.items():
        if modos[tipo] == "genera":
            assert slot["eje_1"]["casos"] >= 1, tipo
        else:
            assert slot["eje_1"]["casos"] == 0, tipo


def test_el_manifest_declara_los_dos_ejes_y_sus_descargos_verbatim():
    manifest = _manifest()
    descargos = manifest["descargos"]
    ejes = [eje["id"] for eje in manifest["ejes"]]

    assert "no declara conformidad de calidad" in descargos["eje_2"]
    assert "aplica sólo al eje 1" in descargos["umbral"]
    assert ejes == [
        "eje_1_calidad_de_prosa_generada",
        "eje_2_conformidad_de_forma",
    ]


def test_el_eje_1_solo_cubre_tipos_que_generan_y_declara_su_fuente_de_fidelidad():
    modos = {tipo["id"]: tipo["modo"] for tipo in _tipos_del_contrato()}
    manifest = _manifest()
    eje1 = manifest["ejes"][0]
    casos = manifest["casos"]

    assert eje1["id"] == "eje_1_calidad_de_prosa_generada"
    for tipo in eje1["tipos"]:
        assert modos[tipo] == "genera", tipo
    for caso_id in eje1["casos"]:
        caso = casos[caso_id]
        assert "eje_1_calidad_de_prosa_generada" in caso["ejes"], caso_id
        if caso["tipo"] == "difusion_de_actividad":
            assert "la fila" in caso["fuente_de_fidelidad"], caso_id
        else:
            # En un saludo la fuente de fidelidad no es una fila del CSV:
            # son la ocasión y la fecha que declara la pieza.
            assert "ocasión" in caso["fuente_de_fidelidad"], caso_id
            assert "fecha" in caso["fuente_de_fidelidad"], caso_id


def test_el_saludo_se_sienta_en_los_dos_ejes_con_su_prompt_existente():
    manifest = _manifest()
    caso = manifest["casos"]["FIE-SAL-01"]

    assert caso["tipo"] == "saludo_o_efemeride"
    assert caso["ejes"] == [
        "eje_1_calidad_de_prosa_generada",
        "eje_2_conformidad_de_forma",
    ]
    assert caso["fuente_de_fidelidad"] == (
        "la ocasión y la fecha que declara la pieza (Día del Ingeniero)"
    )
    # El tipo se sienta en el eje 1 porque su prompt existe y está versionado.
    assert PROMPT_SALUDO.is_file()
    assert caso["prompt"] == "src/agente1/prompts/saludo_o_efemeride_v1.txt"


def test_los_siete_tipos_declaran_caso_de_forma_con_su_forma_y_su_golden():
    ids_tipo = {tipo["id"] for tipo in _tipos_del_contrato()}
    manifest = _manifest()
    eje2 = manifest["ejes"][1]
    entradas = {entrada["tipo"]: entrada for entrada in eje2["casos_por_tipo"]}

    # Los siete tipos, sin excepción, cada uno con un caso representativo.
    assert set(entradas) == ids_tipo
    for tipo, entrada in entradas.items():
        forma = ROOT / entrada["forma_declarada"]
        assert forma.is_file(), tipo
        assert json.loads(forma.read_text(encoding="utf-8"))["tipo"] == tipo
        assert (ROOT / entrada["golden"]).is_file(), tipo
        caso = manifest["casos"][entrada["caso"]]
        assert caso["tipo"] == tipo, entrada["caso"]
        assert "eje_2_conformidad_de_forma" in caso["ejes"], entrada["caso"]
        assert entrada["pieza"]


def test_misas_y_vacunacion_y_tutores_no_cargan_como_difusion():
    # El pedido original de Juani entra por su propio tipo, no por difusión:
    # la misa y la vacunación son avisos de otra área, la convocatoria de
    # tutores es convocatoria interna (#103 §3), y sólo declaran el eje 2.
    manifest = _manifest()
    casos = manifest["casos"]

    assert casos["FIE-AVI-01"]["tipo"] == "aviso_de_otra_area"
    assert "misa" in casos["FIE-AVI-01"]["pieza"].lower()
    assert casos["FIE-AVI-02"]["tipo"] == "aviso_de_otra_area"
    assert "vacunación" in casos["FIE-AVI-02"]["pieza"].lower()
    assert casos["FIE-CON-01"]["tipo"] == "convocatoria_interna"
    assert "tutores" in casos["FIE-CON-01"]["pieza"].lower()
    for caso_id in ("FIE-AVI-01", "FIE-AVI-02", "FIE-CON-01"):
        assert casos[caso_id]["ejes"] == ["eje_2_conformidad_de_forma"], caso_id
        assert casos[caso_id]["tipo"] != "difusion_de_actividad"


def test_el_balseiro_queda_pendiente_de_transcripcion_sin_inventar_datos():
    manifest = _manifest()
    caso = manifest["casos"]["FIE-DIF-09"]
    sin_fila = "FIE-DIF-09" not in IDS

    assert caso["tipo"] == "difusion_de_actividad"
    assert caso["estado"] == "PENDIENTE_SEU"
    assert caso["data_source"] == "PENDIENTE_SEU"
    assert caso["fuente_de_fidelidad"].startswith("PENDIENTE_SEU")
    assert caso["pipeline"] is False
    assert caso["ejes"] == ["eje_1_calidad_de_prosa_generada"]
    # La pieza está identificada, pero no hay fila en el CSV y ningún dato
    # institucional inventado (no hay fecha, horario, lugar ni organiza).
    assert "28-5" in caso["pieza"]
    assert "Balseiro" in caso["pieza"]
    assert sin_fila
    for campo in ("fecha_inicio", "hora", "lugar", "organiza"):
        assert campo not in caso


def test_la_rubrica_esta_aprobada_y_las_corridas_siguen_sin_ejecutarse():
    manifest = _manifest()

    assert manifest["human_review"] == "RUBRICA_APROBADA_JUANI_2026-10-16"
    assert manifest["institutional_quality_assessed"] is False
    # El manifest no lista la aprobación de la rúbrica entre lo que no acredita
    # (ya está aprobada), pero sí lo que sigue sin producirse: la medición.
    no_acredita = " ".join(manifest["no_acredita"])
    assert "aprobación de la rúbrica por Juani" not in no_acredita
    assert "las corridas no se ejecutaron" in no_acredita


def test_prode_y_recreativas_quedan_fuera_de_los_dos_ejes():
    modos_tipos = {tipo["id"] for tipo in _tipos_del_contrato()}
    manifest = _manifest()
    fuera = manifest["fuera_de_alcance"]

    assert "prode" in " ".join(fuera["piezas"]).lower()
    # Ningún caso del set declara un tipo fuera del catálogo cerrado.
    assert all(caso["tipo"] in modos_tipos for caso in manifest["casos"].values())


def test_el_documento_del_set_declara_los_bloques_obligatorios():
    texto = DOCUMENTO.read_text(encoding="utf-8")

    for bloque in (
        "Criterio de inclusión",
        "Piezas dudosas excluidas",
        "Procedencia por campo",
        "Slots por tipo",
        "Campos provisionales",
        "Los dos ejes",
        "El caso Balseiro (28-5): pendiente de transcripción",
        "PENDIENTE_SEU",
        "Rúbrica humana",
        "Chequeos automáticos",
        "aprobación de Juani",
    ):
        assert bloque in texto, f"falta el bloque: {bloque}"
    # El umbral del eje 1 y el descargo del eje 2, con todas las letras.
    assert "no declara conformidad de calidad" in texto
    assert "aplica sólo al eje 1" in texto
    for dimension in (
        "parecido a un FIE INFORMA",
        "fidelidad de sentido",
        "claridad y uso",
    ):
        assert dimension in texto
