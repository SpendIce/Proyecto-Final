"""Los documentos del corte de versión (#93).

El tag, el `CHANGELOG.md` y el procedimiento tienen que existir y decir lo
importante: el changelog lleva la primera versión y la sección *Configuración*;
el procedimiento deja explícito que el manifest versionado queda viejo entre
versiones y que el corte lo regenera.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_changelog_tiene_primera_version_y_seccion_configuracion() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## [0.1.0]" in changelog
    assert "## Configuración" in changelog


def test_el_procedimiento_dice_que_el_manifest_queda_viejo() -> None:
    procedimiento = (ROOT / "PROCEDIMIENTO-CORTE-DE-VERSION.md").read_text(
        encoding="utf-8"
    )

    assert "manifest-version.json" in procedimiento
    assert "agente1-v" in procedimiento
    # El paso de regeneración, explícito: el manifest viejo es un agente que no
    # arranca en modo operación, y eso es por diseño.
    assert "manifest_version.py" in procedimiento


@pytest.mark.parametrize(
    "archivo", ["CHANGELOG.md", "PROCEDIMIENTO-CORTE-DE-VERSION.md"]
)
def test_los_documentos_del_corte_estan_versionados(archivo: str) -> None:
    assert (ROOT / archivo).is_file()
