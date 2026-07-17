import importlib
from importlib.resources import files
from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]


def test_configuracion_de_packaging_declara_backend_importable_y_prompt():
    configuracion = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    backend = configuracion["build-system"]["build-backend"]

    importlib.import_module(backend)
    assert configuracion["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert "PROMPT_VERSION: gacetilla_v1" in (
        files("agente1")
        .joinpath("prompts", "gacetilla_v1.txt")
        .read_text(encoding="utf-8")
    )
