"""Destino de la flecha «Volver» de la cabecera.

Volver lleva a la pantalla madre de cada ruta, no al historial del
navegador: tras un POST con redirección `history.back()` puede devolver
al formulario recién enviado, y si la persona entró por un enlace la saca
de la web. La bandeja es el inicio y el ingreso no tiene madre, así que
ninguna de las dos muestra la flecha.
"""

from __future__ import annotations

_BANDEJA = ("/bandeja", "Volver a la bandeja")
_BANDEJA_CERTIFICADOS = ("/bandeja#certificados", "Volver a la bandeja")
_SIN_VOLVER = frozenset({"", "bandeja", "ingresar"})


def destino_volver(ruta: str) -> tuple[str, str] | None:
    """`(href, etiqueta)` de la flecha para `ruta`, o `None` si no va."""
    partes = [p for p in ruta.strip("/").split("/") if p]
    if not partes or partes[0] in _SIN_VOLVER:
        return None
    if partes[0] == "solicitudes" and len(partes) >= 3:
        return (f"/solicitudes/{partes[1]}", "Volver a la pieza")
    if partes[0] == "certificados":
        if len(partes) >= 3 and partes[1] != "pedir":
            return (f"/certificados/{partes[1]}", "Volver al lote")
        return _BANDEJA_CERTIFICADOS
    return _BANDEJA
