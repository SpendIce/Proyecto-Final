"""La política de redes debe ser verificable, no declarativa.

`DEF-A1-007` registra que la SEU todavía no comunicó criterios de tono,
longitud, hashtags, CTA ni reel. Mientras tanto el sistema opera con reglas
provisionales del equipo técnico. Este módulo verifica dos cosas distintas:

1. que toda regla declarada `ACTIVA` en el artefacto de política produzca
   efectivamente su código de validación en el gate de HU-011; y
2. que ninguna regla pendiente de criterio institucional quede presentada como
   cumplida, ni con un código de gate ni sin referencia al pedido a la SEU.

Un control mecánico verde no acredita adecuación editorial: eso permanece en
`RED-TON-03` como `NO_MECANIZABLE`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.politica_redes import (
    APLICACIONES,
    CANALES_NO_SOPORTADOS,
    CANALES_SOPORTADOS,
    HASHTAGS_AUTORIZADOS_PROVISIONALES,
    POLICY_STATUS,
    POLITICA_REDES,
    POLITICAS_DEFAULT,
    REGLAS,
    PoliticaPost,
    contar_emojis,
    errores_de_estilo,
    regla,
    reglas_por_aplicacion,
)
from agente1.posts import CONTRATO_CREATIVO_V3, procesar_post_estructurado


ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

CREATIVIDAD_CONFORME = {
    "gancho": "¿Buscás un espacio para compartir lo que sabés?",
    "prosa": (
        "Te invitamos a sumarte a una propuesta abierta, pensada para que "
        "puedas intercambiar experiencias y aprender junto a otras personas."
    ),
    "cta": "Sumate y participá de la propuesta.",
    "hashtags": ["#Aprender", "#Comunidad"],
}


def _procesar(
    tmp_path: Path,
    *,
    canal: str = "instagram",
    creatividad: dict[str, object] | None = None,
    politica: PoliticaPost | None = None,
):
    payload = dict(CREATIVIDAD_CONFORME)
    payload.update(creatividad or {})
    return procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-001",
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(json.dumps(payload, ensure_ascii=False)),
        politica=politica,
        contrato=CONTRATO_CREATIVO_V3,
    )


def _errores(resultado) -> list[str]:
    registro = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    return registro["validation_errors"]


# Caso negativo mínimo por regla ACTIVA: canal, creatividad y política que deben
# hacer visible el código declarado en el artefacto.
CASOS_NEGATIVOS: dict[str, dict[str, object]] = {
    "RED-EXT-01": {"politica": {"max_chars": 120}},
    "RED-EXT-02": {"creatividad": {"gancho": "Muy corto"}},
    "RED-HTG-01": {"creatividad": {"hashtags": []}},
    "RED-HTG-02": {"creatividad": {"hashtags": ["#EtiquetaInventada"]}},
    "RED-HTG-03": {"creatividad": {"hashtags": ["#Aprender", "#aprender"]}},
    "RED-HTG-04": {"creatividad": {"hashtags": ["Aprender"]}},
    "RED-REG-01": {"creatividad": {"cta": "Únete a esta propuesta abierta."}},
    "RED-TON-01": {
        "creatividad": {
            "prosa": (
                "Una propuesta imperdible para quienes quieran acercarse a "
                "compartir lo que saben con otras personas."
            )
        }
    },
    "RED-TON-02": {
        "canal": "linkedin",
        "creatividad": {"cta": "Sumate a la propuesta institucional!"},
    },
    "RED-EMO-01": {
        "canal": "linkedin",
        "creatividad": {"cta": "Sumate a la propuesta institucional 🎓"},
    },
    "RED-CTA-01": {"creatividad": {"cta": "Reservá tu lugar en la propuesta."}},
    "RED-CTA-02": {
        "creatividad": {
            "prosa": (
                "Se trata de una propuesta ya aprobada, pensada para "
                "acompañar a quienes quieran participar de la experiencia."
            )
        }
    },
    "RED-ALC-01": {"canal": "tiktok"},
    "RED-ALC-02": {"canal": "reel"},
}


def test_artefacto_de_politica_es_estructuralmente_coherente() -> None:
    identificadores = [item["id"] for item in REGLAS]
    canales_conocidos = set(CANALES_SOPORTADOS) | set(CANALES_NO_SOPORTADOS)

    assert POLITICA_REDES["x-status"] == POLICY_STATUS
    assert len(identificadores) == len(set(identificadores))
    for item in REGLAS:
        assert item["aplicacion"] in APLICACIONES
        assert item["enunciado"].strip()
        assert set(item["canales"]) <= canales_conocidos
        assert item["punto_nota_seu"]


def test_regla_activa_declara_codigo_y_regla_pendiente_no_lo_simula() -> None:
    for item in reglas_por_aplicacion("ACTIVA"):
        assert item["codigo_gate"], item["id"]
    for aplicacion in ("NO_APLICADA_PENDIENTE_SEU", "NO_MECANIZABLE"):
        for item in reglas_por_aplicacion(aplicacion):
            assert item["codigo_gate"] is None, item["id"]
            assert item["origen_valor"] == "SIN_DEFINICION_INSTITUCIONAL", item["id"]


def test_toda_regla_activa_tiene_caso_negativo_de_regresion() -> None:
    """Sin este control, agregar una regla al artefacto la daría por cumplida."""
    activas = {item["id"] for item in reglas_por_aplicacion("ACTIVA")}

    assert activas == set(CASOS_NEGATIVOS)


@pytest.mark.parametrize("identificador", sorted(CASOS_NEGATIVOS))
def test_cada_regla_activa_se_observa_en_el_gate(
    identificador: str, tmp_path: Path
) -> None:
    caso = CASOS_NEGATIVOS[identificador]
    canal = str(caso.get("canal", "instagram"))
    politica_base = POLITICAS_DEFAULT.get(canal)
    ajuste = caso.get("politica")
    politica = (
        replace(politica_base, **ajuste)
        if ajuste and politica_base is not None
        else None
    )

    resultado = _procesar(
        tmp_path,
        canal=canal,
        creatividad=caso.get("creatividad"),
        politica=politica,
    )

    assert resultado.borrador_path is None
    assert regla(identificador)["codigo_gate"] in _errores(resultado)


def test_creatividad_conforme_sigue_produciendo_borrador(tmp_path: Path) -> None:
    """Las reglas nuevas no pueden bloquear el camino conforme."""
    for canal in CANALES_SOPORTADOS:
        resultado = _procesar(tmp_path / canal, canal=canal)

        assert resultado.estado == "PENDIENTE_VALIDACION"
        assert resultado.borrador_path is not None


def test_politicas_por_canal_derivan_del_artefacto() -> None:
    for canal, politica in POLITICAS_DEFAULT.items():
        declarado = POLITICA_REDES["canales"][canal]

        assert politica.version == declarado["policy_version"]
        assert politica.max_chars == declarado["max_chars"]
        assert politica.min_hashtags == declarado["min_hashtags"]
        assert politica.max_hashtags == declarado["max_hashtags"]
        assert politica.max_emojis == declarado["max_emojis"]
        assert politica.max_exclamaciones == declarado["max_exclamaciones"]


def test_allowlist_de_hashtags_coincide_con_el_contrato_creativo() -> None:
    """La política es la fuente; el contrato no puede divergir en silencio."""
    assert (
        tuple(CONTRATO_CREATIVO_V3.schema["x-provisional-safety-hashtags"])
        == HASHTAGS_AUTORIZADOS_PROVISIONALES
    )
    assert CONTRATO_CREATIVO_V3.hashtags_seguros == frozenset(
        HASHTAGS_AUTORIZADOS_PROVISIONALES
    )


def test_reel_esta_declarado_fuera_de_alcance_y_no_es_canal_soportado() -> None:
    assert "reel" not in CANALES_SOPORTADOS
    assert CANALES_NO_SOPORTADOS["reel"]["estado"] == "FUERA_DE_ALCANCE_MVP"


@pytest.mark.parametrize(
    "texto",
    [
        "¿Qué proponemos? Un espacio abierto —y compartido— para aprender…",
        "Aprender, compartir y volver a empezar: así de simple.",
    ],
)
def test_signos_del_espanol_no_se_cuentan_como_emoji(texto: str) -> None:
    assert contar_emojis(texto) == 0
    assert errores_de_estilo(texto, POLITICAS_DEFAULT["linkedin"]) == []


@pytest.mark.parametrize(
    "texto",
    ["Una PROMOCIÓN para la comunidad", "Una promocion para la comunidad"],
)
def test_lexico_promocional_se_detecta_sin_depender_de_tildes_ni_mayusculas(
    texto: str,
) -> None:
    assert "unauthorized_promotional_language" in errores_de_estilo(
        texto, POLITICAS_DEFAULT["linkedin"]
    )


def test_politica_construida_a_mano_no_aplica_reglas_que_no_declara() -> None:
    """`None` significa regla no aplicada, no límite infinito institucional."""
    politica = PoliticaPost(
        version="post_policy_test_v1",
        status=POLICY_STATUS,
        max_chars=1000,
        min_hashtags=1,
        max_hashtags=10,
    )

    assert errores_de_estilo("¡Una oferta imperdible! 🎉", politica) == []


@pytest.mark.parametrize("canal", sorted(CANALES_SOPORTADOS))
def test_prompt_v3_no_deja_placeholders_sin_resolver(canal: str, tmp_path: Path) -> None:
    """El prompt debe llevar los límites de la política, no su marcador."""
    prompts: list[str] = []

    class GeneradorQueCapturaPrompt:
        modelo = "fake-captura-prompt"
        num_predict = None

        def generar(self, prompt: str) -> str:
            prompts.append(prompt)
            return json.dumps(CREATIVIDAD_CONFORME, ensure_ascii=False)

    procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-001",
        canal=canal,
        directorio_salida=tmp_path,
        generator=GeneradorQueCapturaPrompt(),
        contrato=CONTRATO_CREATIVO_V3,
    )

    prompt = prompts[0]
    politica = POLITICAS_DEFAULT[canal]
    for marcador in ("{max_chars}", "{max_emojis}", "{max_exclamaciones}", "{datos_fuente}"):
        assert marcador not in prompt
    assert f"emojis: {politica.max_emojis}" in prompt
    assert f"exclamación: {politica.max_exclamaciones}" in prompt
