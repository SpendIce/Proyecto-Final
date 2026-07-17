import importlib
from importlib.resources import files
import csv
import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]


def test_configuracion_de_packaging_declara_backend_importable_y_prompt():
    configuracion = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    backend = configuracion["build-system"]["build-backend"]

    importlib.import_module(backend)
    assert configuracion["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert "PROMPT_VERSION: gacetilla_v2" in (
        files("agente1")
        .joinpath("prompts", "gacetilla_v2.txt")
        .read_text(encoding="utf-8")
    )


def test_contrato_versionado_es_explicito_y_provisional():
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "gacetilla_input_v1.schema.json")
        .read_text(encoding="utf-8")
    )

    assert contrato["x-contract-version"] == "gacetilla_input_v1"
    assert contrato["x-status"] == "PROVISIONAL_NO_INSTITUCIONAL"
    assert contrato["required"] == [
        "id_solicitud",
        "titulo",
        "descripcion",
        "fecha",
        "publico",
        "organiza",
        "contacto",
        "fuente",
    ]
    assert contrato["properties"]["lugar"]["x-required"] is False


def test_dataset_versionado_tiene_cinco_casos_y_dos_invalidos():
    with (ROOT / "data" / "actividades_sinteticas.csv").open(
        encoding="utf-8", newline=""
    ) as archivo:
        filas = list(csv.DictReader(archivo))

    assert len(filas) == 5
    assert sum(not fila["contacto"] or not fila["fecha"] for fila in filas) >= 2
    assert any(not fila["lugar"] for fila in filas)
