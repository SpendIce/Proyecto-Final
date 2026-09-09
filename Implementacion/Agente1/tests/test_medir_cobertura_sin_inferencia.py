"""La medición de cobertura sin inferencia (HU-013/#26) existe, corre sin
invocar ningún modelo, y distingue el corpus calibrado del que no lo está.

Se carga el script por ruta, como `test_workspace_e2e_script.py`, para no
agregar `scripts/` al path de importación de toda la suite."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "medir_cobertura_sin_inferencia.py"
DATASET = ROOT / "data" / "actividades_sinteticas.csv"
CORPUS_CALIBRADO = ROOT / "data" / "frases_resolucion_actividad.csv"
CORPUS_AMBIGUAS = ROOT / "data" / "frases_ambiguas_fallback.csv"


NOMBRE_MODULO = "medir_cobertura_script_test"


def _cargar_script():
    # El módulo se registra en `sys.modules` antes de ejecutarlo porque el
    # script define un dataclass y usa anotaciones diferidas: `dataclasses`
    # resuelve los tipos buscando el módulo por su nombre, y si no está
    # registrado falla al construir la clase. Es la diferencia con
    # `test_workspace_e2e_script.py`, cuyo script no define dataclasses.
    spec = importlib.util.spec_from_file_location(NOMBRE_MODULO, SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[NOMBRE_MODULO] = modulo
    try:
        spec.loader.exec_module(modulo)
    except Exception:
        del sys.modules[NOMBRE_MODULO]
        raise
    return modulo


def test_la_medicion_esta_disponible_y_clasifica_cada_frase():
    modulo = _cargar_script()
    medicion = modulo.medir(CORPUS_CALIBRADO, DATASET)

    assert medicion.total == len(medicion.detalle)
    assert medicion.total > 0
    assert 0.0 <= medicion.porcentaje_sin_inferencia <= 100.0
    assert all(caso["via"] in modulo.VIAS for caso in medicion.detalle)


def test_el_corpus_calibrado_resuelve_entero_sin_inferencia():
    """El corpus de #23 se calibró para eso, así que este número tiene que
    seguir en 100 %: si baja, una constante de resolución se movió."""
    medicion = _cargar_script().medir(CORPUS_CALIBRADO, DATASET)

    assert medicion.porcentaje_sin_inferencia == 100.0
    assert medicion.porcentaje_correctas == 100.0


def test_el_corpus_no_calibrado_deja_trabajo_al_fallback():
    """La contracara honesta del test anterior, y la razón por la que el
    fallback existe. `frases_ambiguas_fallback.csv` reúne frases que no se
    eligieron para pasar: piden la actividad por un rasgo parcial, por una
    fecha en otro formato o por quién la organiza.

    El umbral no es "menos de 100 %" sino una mayoría sin resolver: un corpus
    que resolviera al 99 % dejaría de decir algo sobre el trabajo pendiente, y
    eso habría que revisarlo, no celebrarlo.
    """
    medicion = _cargar_script().medir(CORPUS_AMBIGUAS, DATASET)

    assert medicion.total >= 8
    assert medicion.porcentaje_sin_inferencia < 50.0


def test_toda_frase_resuelta_del_corpus_ambiguo_llega_a_la_actividad_esperada():
    """La columna `id_esperado` del corpus tiene que significar algo: una
    frase que el camino determinístico resuelve **mal** es un defecto, no una
    frase pendiente de fallback."""
    medicion = _cargar_script().medir(CORPUS_AMBIGUAS, DATASET)
    modulo = _cargar_script()

    resueltas = [
        caso for caso in medicion.detalle if caso["via"] != modulo.VIA_SIN_RESOLVER
    ]
    assert resueltas, "si nada resuelve, el corpus no ejercita la resolución"
    for caso in resueltas:
        assert caso["resuelto"] == caso["esperado"], caso["frase"]


def test_todo_id_esperado_del_corpus_existe_en_el_dataset():
    """Sin esto, la columna `id_esperado` sólo se verifica en las filas que el
    camino determinístico resuelve —hoy 1 de 8— y las otras siete podrían
    apuntar a actividades inexistentes sin que nada avise. El corpus es la
    referencia contra la que se mide el fallback: si sus expectativas son
    falsas, la medición no significa nada.
    """
    import csv

    with DATASET.open(encoding="utf-8", newline="") as archivo:
        ids_dataset = {fila["id_solicitud"] for fila in csv.DictReader(archivo)}

    for corpus in (CORPUS_CALIBRADO, CORPUS_AMBIGUAS):
        with corpus.open(encoding="utf-8", newline="") as archivo:
            filas = list(csv.DictReader(archivo))
        assert filas, f"{corpus.name} está vacío"
        for fila in filas:
            assert fila["id_esperado"] in ids_dataset, (
                f"{corpus.name} espera {fila['id_esperado']}, "
                f"que no existe en el dataset: {fila['frase']}"
            )
