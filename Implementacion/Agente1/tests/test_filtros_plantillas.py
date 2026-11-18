"""Filtros Jinja del canal web para el lenguaje de la SEU (#194)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from agente1.web.app import (
    condicion_legible,
    fecha_legible,
    roles_legibles,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (date(2026, 11, 8), "08/11/2026"),
        (datetime(2026, 11, 8, 14, 5), "08/11/2026 14:05"),
        ("2026-11-08", "08/11/2026"),
        ("2026-11-08T14:05", "08/11/2026 14:05"),
        ("2026-11-08 14:05", "08/11/2026 14:05"),
        ("sin fecha", "sin fecha"),
        ("", ""),
        (None, ""),
    ],
)
def test_fecha_legible(valor: object, esperado: str) -> None:
    assert fecha_legible(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("coordinador_seu", "Coordinación SEU"),
        ("auxiliar_seu", "Auxiliar SEU"),
        ("APROBADOR_CONTENIDO", "Aprobación de contenido"),
        ("APROBADOR_PAGOS", "Aprobación de pagos"),
        (
            "APROBADOR_PAGOS · APROBADOR_CONTENIDO",
            "Aprobación de pagos · Aprobación de contenido",
        ),
        ("lector_seu", "lector_seu"),
        ("", ""),
        (None, ""),
    ],
)
def test_roles_legibles(valor: object, esperado: str) -> None:
    assert roles_legibles(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("aprobacion", "Aprobación"),
        ("asistencia", "Asistencia"),
        ("otra", "otra"),
        (None, ""),
    ],
)
def test_condicion_legible(valor: object, esperado: str) -> None:
    assert condicion_legible(valor) == esperado
