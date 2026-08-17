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


def test_recursos_hu011_versionados_son_empaquetables_y_provisionales():
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "post_input_v1.schema.json")
        .read_text(encoding="utf-8")
    )

    assert contrato["x-contract-version"] == "post_input_v1"
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
    for canal in ("instagram", "linkedin"):
        prompt = (
            files("agente1")
            .joinpath("prompts", f"post_{canal}_v1.txt")
            .read_text(encoding="utf-8")
        )
        assert f"PROMPT_VERSION: post_{canal}_v1" in prompt
        assert "POLICY_STATUS: PROVISIONAL_NO_INSTITUCIONAL" in prompt


def test_schema_candidato_a2_a5_esta_declarado_como_recurso_importable():
    configuracion = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    recursos = configuracion["tool"]["setuptools"]["package-data"]["agente1"]

    assert "contracts/insumos/*.json" in recursos
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "insumos", "agente1_insumo_candidate_v1.schema.json")
        .read_text(encoding="utf-8")
    )
    assert contrato["properties"]["schema"]["const"] == "agente1.insumo.v1"


def test_dataset_versionado_tiene_cinco_casos_y_dos_invalidos():
    with (ROOT / "data" / "actividades_sinteticas.csv").open(
        encoding="utf-8", newline=""
    ) as archivo:
        filas = list(csv.DictReader(archivo))

    assert len(filas) == 5
    assert sum(not fila["contacto"] or not fila["fecha"] for fila in filas) >= 2
    assert any(not fila["lugar"] for fila in filas)
