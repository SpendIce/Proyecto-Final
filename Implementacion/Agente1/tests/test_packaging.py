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


def test_recursos_hu011_v2_estructurados_son_empaquetables():
    import agente1

    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "post_creative_output_v2.schema.json")
        .read_text(encoding="utf-8")
    )

    assert contrato["x-contract-version"] == "post_creative_output_v2"
    assert contrato["x-status"] == "PROVISIONAL_NO_INSTITUCIONAL"
    assert contrato["additionalProperties"] is False
    assert contrato["required"] == ["gancho", "prosa", "cta", "hashtags"]
    hashtag_items = contrato["properties"]["hashtags"]["items"]
    assert "pattern" not in hashtag_items
    assert hashtag_items["enum"] == contrato["x-provisional-safety-hashtags"]
    assert callable(agente1.procesar_post_estructurado)
    for canal in ("instagram", "linkedin"):
        prompt = (
            files("agente1")
            .joinpath("prompts", f"post_{canal}_structured_v2.txt")
            .read_text(encoding="utf-8")
        )
        assert f"PROMPT_VERSION: post_{canal}_structured_v2" in prompt
        assert "CONTRACT_VERSION: post_creative_output_v2" in prompt


def test_recursos_y_api_primaria_hu012_son_empaquetables():
    import agente1

    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "confirmacion_inscripcion_v1.schema.json")
        .read_text(encoding="utf-8")
    )
    plantilla = (
        files("agente1")
        .joinpath("prompts", "confirmacion_inscripcion_provisional_v1.txt")
        .read_text(encoding="utf-8")
    )

    assert contrato["x-contract-version"] == "confirmacion_inscripcion_v1"
    assert contrato["x-status"] == "PROVISIONAL_NO_INSTITUCIONAL"
    assert "TEMPLATE_VERSION: confirmacion_inscripcion_provisional_v1" in plantilla
    for nombre in (
        "AprobacionHumana",
        "DestinoConfirmacionesFake",
        "RegistroConfirmacionesMemoria",
        "ResultadoConfirmacion",
        "SolicitudConfirmacion",
        "procesar_confirmacion",
    ):
        assert nombre in agente1.__all__
        assert getattr(agente1, nombre) is not None


def test_migraciones_del_spike_son_artefactos_de_repo_no_package_data():
    """Las migraciones se aplican con un cliente SQL, no se importan del wheel."""
    configuracion = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    recursos = configuracion["tool"]["setuptools"]["package-data"]["agente1"]
    migraciones = ROOT / "migrations"

    assert all("migration" not in patron for patron in recursos)
    for version in ("0001_persistencia_agente1", "0002_integridad_referencial_borradores"):
        assert (migraciones / f"{version}.up.sql").is_file()
        assert (migraciones / f"{version}.down.sql").is_file()


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
