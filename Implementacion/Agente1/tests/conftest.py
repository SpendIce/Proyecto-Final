"""Precondiciones externas de la suite.

Algunas pruebas leen cosas que viven fuera del Agente 1: la historia de git
(los runners de matriz registran el commit) o los perfiles del laboratorio en
`Documentos/` del repo. Dentro de la imagen de prueba (#143) no están, así que
esas pruebas se saltean con el motivo a la vista, igual que el cotejo del
manifest cuando falta git. La suite completa, con el repo y git, corre en el
workflow `agente1-ci`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1] if len(ROOT.parents) > 1 else ROOT


@pytest.fixture(scope="session")
def requiere_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git no disponible (imagen de prueba)")
    proceso = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proceso.returncode != 0:
        pytest.skip("sin repositorio git (imagen de prueba)")


@pytest.fixture(scope="session")
def requiere_repo_documentos() -> None:
    if not (REPO / "Documentos" / "Laboratorio").is_dir():
        pytest.skip("sin Documentos/ del repo (imagen de prueba)")
