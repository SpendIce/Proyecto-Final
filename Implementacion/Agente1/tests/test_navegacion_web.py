"""Flecha «Volver» de la cabecera: a qué pantalla lleva cada ruta.

Volver lleva a la pantalla madre, no al historial del navegador: después
de un POST con redirección, `history.back()` puede devolver al formulario
recién enviado o sacar a la persona de la web si entró por un enlace.
"""

from __future__ import annotations

import pytest

from agente1.web.navegacion import destino_volver


@pytest.mark.parametrize(
    ("ruta", "esperado"),
    [
        ("/solicitudes/sol-1", ("/bandeja", "Volver a la bandeja")),
        ("/solicitudes/sol-1/correo", ("/solicitudes/sol-1", "Volver a la pieza")),
        ("/nuevo-pedido", ("/bandeja", "Volver a la bandeja")),
        ("/certificados/pedir", ("/bandeja#certificados", "Volver a la bandeja")),
        ("/certificados/lote-1", ("/bandeja#certificados", "Volver a la bandeja")),
        (
            "/certificados/lote-1/emision",
            ("/certificados/lote-1", "Volver al lote"),
        ),
        ("/sin-permiso", ("/bandeja", "Volver a la bandeja")),
    ],
)
def test_cada_pantalla_vuelve_a_su_madre(
    ruta: str, esperado: tuple[str, str]
) -> None:
    assert destino_volver(ruta) == esperado


@pytest.mark.parametrize("ruta", ["/", "/bandeja", "/ingresar", ""])
def test_el_inicio_y_el_ingreso_no_tienen_volver(ruta: str) -> None:
    assert destino_volver(ruta) is None


def test_la_barra_final_no_cambia_el_destino() -> None:
    assert destino_volver("/certificados/lote-1/emision/") == (
        "/certificados/lote-1",
        "Volver al lote",
    )
