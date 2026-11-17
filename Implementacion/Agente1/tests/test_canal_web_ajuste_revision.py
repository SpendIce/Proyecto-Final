"""Revisión del ajuste generativo: asunto único canónico y timeout tipado.

Dos acotaciones sobre la revisión cruzada del diff de ajuste:

- `_fijar_asunto` sólo miraba la primera línea no vacía: si el modelo
  bajaba el `Asunto:` tras un encabezado, lo duplicaba o le cambiaba las
  mayúsculas, el Doc quedaba con dos líneas de asunto —una de la base y
  otra reescrita por el modelo— y el gate no lo veía porque corre antes
  de recomponer. Ahora se descartan todas las líneas de asunto del
  modelo, se antepone la de la base y la pieza recompuesta vuelve a pasar
  el gate: si un hecho sólo vivía en la línea descartada, la salida no se
  rescata.
- El timeout real del adapter de Ollama llegaba como `RuntimeError`
  genérico y se registraba `generador_error`. `OllamaTimeoutError` es un
  subtipo de `RuntimeError` —los callers que capturan el genérico no
  cambian— y `ajustar` lo registra como `timeout_generador`.
"""

from __future__ import annotations

import pytest

from agente1.destinos import BORRADOR_MARKER
from agente1.gacetillas import renderizar
from agente1.ollama import OllamaGenerator
from agente1.web.ajuste import ajustar, normalizar_pieza_ajustada

CAMPOS = {
    "titulo": "Jornada sintética de extensión",
    "cuerpo": "La jornada reunió a estudiantes y docentes en la facultad.",
}
TEXTO_VALIDO = BORRADOR_MARKER + renderizar("cronica_de_evento", CAMPOS) + "\n"

CAMPOS_DIFUSION = {
    "titulo": "Curso sintético de extensión",
    "bajada": "La Secretaría de Extensión Universitaria abre la inscripción.",
    "cuerpo": "La actividad se dicta en la sede de la facultad.",
    "fecha_inicio": "2026-11-20",
    "contacto": "extension@example.invalid",
}
TEXTO_DIFUSION = (
    BORRADOR_MARKER + renderizar("difusion_de_actividad", CAMPOS_DIFUSION) + "\n"
)

FIRMANTE_ULTIMA_LINEA = "www.fie.undef.edu.ar"


def _lineas_asunto(texto: str) -> list[str]:
    return [
        linea
        for linea in texto.splitlines()
        if linea.strip().casefold().startswith("asunto:")
    ]


def test_un_solo_asunto_canonico_si_el_modelo_lo_baja_de_linea() -> None:
    """El caso reproducido en la revisión: el modelo antepone un encabezado
    propio y deja el `Asunto:` en la tercera línea. Antes quedaban dos
    asuntos —el canónico antepuesto y el del modelo intacto—."""
    salida = (
        BORRADOR_MARKER
        + "Jornada de extensión\n\n"
        + "Asunto: Jornada sintética de extensión — reescrito por el modelo\n\n"
        + "La jornada reunió a todos.\n"
    )

    texto, errores = normalizar_pieza_ajustada(
        salida,
        tipo="cronica_de_evento",
        campos=CAMPOS,
        texto_base=TEXTO_VALIDO,
    )

    assert errores == []
    assert _lineas_asunto(texto) == ["Asunto: Jornada sintética de extensión"]
    # El asunto canónico es el primer contenido tras la marca; el
    # encabezado del modelo queda como prosa, el pie institucional intacto.
    cuerpo = texto[len(BORRADOR_MARKER):]
    assert cuerpo.startswith("Asunto: Jornada sintética de extensión\n\n")
    assert "Jornada de extensión" in cuerpo
    assert "reescrito por el modelo" not in texto
    assert texto.rstrip().endswith(FIRMANTE_ULTIMA_LINEA)


@pytest.mark.parametrize(
    "linea_extra",
    [
        "Asunto: Jornada sintética de extensión",
        "asunto: Jornada sintética de extensión",
        "ASUNTO : Jornada sintética de extensión",
        "Asunto: Otro título inventado",
    ],
)
def test_asunto_repetido_o_recapitalizado_queda_en_uno(
    linea_extra: str,
) -> None:
    """Duplicado literal, en minúscula, con otro espaciado o con otro
    contenido: cualquier línea de asunto del modelo se descarta."""
    salida = (
        BORRADOR_MARKER
        + "Asunto: Jornada sintética de extensión\n\n"
        + "La jornada reunió a todos.\n\n"
        + linea_extra
        + "\n"
    )

    texto, errores = normalizar_pieza_ajustada(
        salida,
        tipo="cronica_de_evento",
        campos=CAMPOS,
        texto_base=TEXTO_VALIDO,
    )

    assert errores == []
    assert _lineas_asunto(texto) == ["Asunto: Jornada sintética de extensión"]
    assert "Otro título inventado" not in texto


def test_el_asunto_corregido_por_la_persona_es_el_que_se_repone() -> None:
    """La base es la revisión vigente con la corrección humana importada:
    el asunto que se fija es ese, no el del pedido ni el que escriba el
    modelo, y el pie queda igual."""
    base_corregida = TEXTO_VALIDO.replace(
        "Asunto: Jornada sintética de extensión",
        "Asunto: Jornada de extensión universitaria",
    )
    salida = (
        BORRADOR_MARKER
        + "Asunto: Título inventado por el modelo\n\n"
        + "La jornada reunió a todos.\n"
    )

    texto, errores = normalizar_pieza_ajustada(
        salida,
        tipo="cronica_de_evento",
        campos=CAMPOS,
        texto_base=base_corregida,
    )

    assert errores == []
    cuerpo = texto[len(BORRADOR_MARKER):]
    assert cuerpo.startswith(
        "Asunto: Jornada de extensión universitaria\n\n"
    )
    assert "Título inventado" not in texto
    assert texto.rstrip().endswith(FIRMANTE_ULTIMA_LINEA)


def test_un_hecho_solo_en_la_linea_descartada_no_se_rescata() -> None:
    """Control negativo: el `contacto` es un hecho que el gate exige. Si la
    única línea que lo traía es la de asunto que se descarta, la salida
    era inválida desde el inicio — recomponer no puede inventarlo— y el
    ajuste cierra en error, no en una pieza que perdió el dato."""
    salida = (
        BORRADOR_MARKER
        + "Asunto: Curso sintético de extensión — extension@example.invalid\n\n"
        + "La Secretaría de Extensión Universitaria abre la inscripción.\n\n"
        + "La actividad se dicta en la sede de la facultad.\n\n"
        + "📅 viernes 20 de noviembre de 2026\n"
    )

    texto, errores = normalizar_pieza_ajustada(
        salida,
        tipo="difusion_de_actividad",
        campos=CAMPOS_DIFUSION,
        texto_base=TEXTO_DIFUSION,
    )

    assert texto == ""
    assert "hecho_perdido" in errores


def test_el_hecho_en_la_linea_de_asunto_y_en_el_cuerpo_se_conserva() -> None:
    """El mismo dato dentro del asunto del modelo pero también en el
    cuerpo: se descarta la línea, el hecho sigue presente y el gate post-
    recomposición lo confirma."""
    salida = (
        BORRADOR_MARKER
        + "Asunto: Curso sintético de extensión — extension@example.invalid\n\n"
        + "La Secretaría de Extensión Universitaria abre la inscripción.\n\n"
        + "La actividad se dicta en la sede de la facultad.\n\n"
        + "📅 viernes 20 de noviembre de 2026\n\n"
        + "Consultas: extension@example.invalid\n"
    )

    texto, errores = normalizar_pieza_ajustada(
        salida,
        tipo="difusion_de_actividad",
        campos=CAMPOS_DIFUSION,
        texto_base=TEXTO_DIFUSION,
    )

    assert errores == []
    assert _lineas_asunto(texto) == ["Asunto: Curso sintético de extensión"]
    assert "extension@example.invalid" in texto


class _ConexionQueAgotaDeadline:
    """Transporte falso: el socket agota el deadline durante el request,
    como le pasa al adapter real cuando el modelo no responde a tiempo."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def request(self, *args, **kwargs) -> None:
        raise TimeoutError

    def getresponse(self):  # pragma: no cover - el request ya falló
        raise AssertionError("el request ya agotó el deadline")

    def close(self) -> None:
        pass


def test_el_timeout_del_adapter_llega_a_ajustar_como_timeout_generador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La excepción viaja de punta a punta: el `TimeoutError` del
    transporte sale del adapter como `OllamaTimeoutError` y `ajustar` lo
    registra `timeout_generador`, en un solo intento."""
    monkeypatch.setattr(
        "agente1.ollama.HTTPConnection", _ConexionQueAgotaDeadline
    )
    generator = OllamaGenerator(
        modelo="gemma4:e4b", base_url="http://127.0.0.1:1", timeout_s=5
    )

    salida = ajustar(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=generator,
    )

    assert salida.texto == ""
    assert salida.errores == ["timeout_generador"]
    assert salida.intentos == 1
    assert [fallo.codigos for fallo in salida.fallos] == [
        ("timeout_generador",)
    ]
    assert salida.fallos[0].duracion_ms >= 0
