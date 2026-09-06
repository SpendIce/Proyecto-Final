"""Política de redes de HU-011 expresada como reglas verificables.

El artefacto `politicas/politica_redes_provisional_v1.json` es la única fuente
de los parámetros por canal y del inventario de reglas. Cada regla declara si
está aplicada por el gate (`ACTIVA`), si espera criterio institucional
(`NO_APLICADA_PENDIENTE_SEU`) o si requiere juicio editorial humano
(`NO_MECANIZABLE`). `tests/test_politica_redes.py` verifica que toda regla
`ACTIVA` produzca efectivamente su código de validación y que ninguna regla no
aplicada se presente como cumplida.

Ningún valor de este módulo fue aprobado por la SEU: ver `DEF-A1-007`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib.resources import files


POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"

POLITICA_REDES = json.loads(
    files("agente1")
    .joinpath("politicas", "politica_redes_provisional_v1.json")
    .read_text(encoding="utf-8")
)

POLICY_VERSION = POLITICA_REDES["x-policy-version"]
APLICACIONES = frozenset(POLITICA_REDES["aplicaciones"])
DIMENSIONES = frozenset(
    str(regla["dimension"]) for regla in POLITICA_REDES["reglas"]
)
CANALES_SOPORTADOS = tuple(POLITICA_REDES["canales_soportados"])
CANALES_NO_SOPORTADOS = dict(POLITICA_REDES["canales_no_soportados"])
HASHTAGS_AUTORIZADOS_PROVISIONALES = tuple(
    POLITICA_REDES["hashtags_autorizados_provisionales"]
)
LEXICO_PROMOCIONAL_PROHIBIDO = tuple(POLITICA_REDES["lexico_promocional_prohibido"])
REGLAS = tuple(POLITICA_REDES["reglas"])


def regla(identificador: str) -> dict[str, object]:
    for candidata in REGLAS:
        if candidata["id"] == identificador:
            return candidata
    raise KeyError(identificador)


def reglas_por_aplicacion(aplicacion: str) -> tuple[dict[str, object], ...]:
    if aplicacion not in APLICACIONES:
        raise KeyError(aplicacion)
    return tuple(item for item in REGLAS if item["aplicacion"] == aplicacion)


# Bloques Unicode de pictogramas y símbolos usados como emoji. Se excluyen
# deliberadamente comillas latinas, rayas, puntos suspensivos y signos de
# apertura del español, que no son emoji y sí son parte del registro escrito.
PATRON_EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "☀-➿"
    "⬀-⯿"
    "™©®"
    "]"
)
# El selector de variación no cuenta como emoji propio: acompaña al anterior.
SELECTOR_VARIACION = "️"


def contar_emojis(texto: str) -> int:
    return len(PATRON_EMOJI.findall(texto.replace(SELECTOR_VARIACION, "")))


def contar_exclamaciones(texto: str) -> int:
    return texto.count("!")


def _sin_diacriticos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(
        caracter
        for caracter in descompuesto
        if not unicodedata.combining(caracter)
    )


def _patron_lexico(terminos: tuple[str, ...]) -> re.Pattern[str] | None:
    if not terminos:
        return None
    alternativas = "|".join(
        re.escape(_sin_diacriticos(termino)).replace(r"\ ", r"\s+")
        for termino in terminos
    )
    return re.compile(rf"(?<![\w]){alternativas}(?![\w])")


PATRON_LEXICO_PROMOCIONAL = _patron_lexico(LEXICO_PROMOCIONAL_PROHIBIDO)


@dataclass(frozen=True)
class PoliticaPost:
    """Parámetros por canal aplicados al gate de HU-011.

    `max_emojis` y `max_exclamaciones` en `None` significan "sin regla
    aplicada", no "sin límite institucional": las políticas construidas a mano
    en pruebas conservan así el comportamiento previo, mientras que las
    políticas derivadas del artefacto sí aplican la regla.
    """

    version: str
    status: str
    max_chars: int
    min_hashtags: int
    max_hashtags: int
    max_emojis: int | None = None
    max_exclamaciones: int | None = None
    lexico_promocional: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.version, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.version)
            or self.status != POLICY_STATUS
            or isinstance(self.max_chars, bool)
            or not isinstance(self.max_chars, int)
            or not 1 <= self.max_chars <= 10000
            or isinstance(self.min_hashtags, bool)
            or not isinstance(self.min_hashtags, int)
            or not 0 <= self.min_hashtags <= 100
            or isinstance(self.max_hashtags, bool)
            or not isinstance(self.max_hashtags, int)
            or not 1 <= self.max_hashtags <= 100
            or self.min_hashtags > self.max_hashtags
            or not _limite_opcional_valido(self.max_emojis)
            or not _limite_opcional_valido(self.max_exclamaciones)
            or not isinstance(self.lexico_promocional, tuple)
            or any(
                not isinstance(termino, str) or not termino.strip()
                for termino in self.lexico_promocional
            )
        ):
            raise ValueError("política de post inválida")


def _limite_opcional_valido(valor: int | None) -> bool:
    if valor is None:
        return True
    return not isinstance(valor, bool) and isinstance(valor, int) and 0 <= valor <= 100


def _politica_desde_artefacto(canal: str) -> PoliticaPost:
    parametros = POLITICA_REDES["canales"][canal]
    return PoliticaPost(
        version=str(parametros["policy_version"]),
        status=POLICY_STATUS,
        max_chars=int(parametros["max_chars"]),
        min_hashtags=int(parametros["min_hashtags"]),
        max_hashtags=int(parametros["max_hashtags"]),
        max_emojis=int(parametros["max_emojis"]),
        max_exclamaciones=int(parametros["max_exclamaciones"]),
        lexico_promocional=LEXICO_PROMOCIONAL_PROHIBIDO,
    )


POLITICAS_DEFAULT = {
    canal: _politica_desde_artefacto(canal) for canal in CANALES_SOPORTADOS
}
POLITICA_DEFAULT = POLITICAS_DEFAULT[CANALES_SOPORTADOS[0]]


def errores_de_estilo(texto: str, politica: PoliticaPost) -> list[str]:
    """Aplica las reglas de estilo parametrizadas por canal.

    Devuelve códigos de validación estables; no decide calidad editorial ni
    reemplaza la revisión humana registrada.
    """

    errores: list[str] = []
    if politica.max_emojis is not None and contar_emojis(texto) > politica.max_emojis:
        errores.append("unauthorized_emoji")
    if (
        politica.max_exclamaciones is not None
        and contar_exclamaciones(texto) > politica.max_exclamaciones
    ):
        errores.append("unauthorized_exclamation")
    patron = (
        PATRON_LEXICO_PROMOCIONAL
        if politica.lexico_promocional == LEXICO_PROMOCIONAL_PROHIBIDO
        else _patron_lexico(politica.lexico_promocional)
    )
    if patron is not None and patron.search(_sin_diacriticos(texto)):
        errores.append("unauthorized_promotional_language")
    return errores
