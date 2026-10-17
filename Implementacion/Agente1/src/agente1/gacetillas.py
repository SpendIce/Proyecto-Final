"""Gacetillas por tipo: forma declarada, modo de produccion y gate (#121).

El Agente 1 prepara **gacetillas** para el canal FIE Informa, y el canal lleva
siete clases de pieza (ADR 0012): difusion de actividad, cronica de evento,
aviso de otra area, convocatoria interna, saludo o efemeride, fallecimiento y
newsletter. Cada tipo declara:

- su **forma declarada** (`contracts/formas/<tipo>_v1.json`): las partes
  institucionales fijas (encabezado, pie, firmante, formulas y etiquetas) y el
  plan de armado de la pieza. El agente la copia; el modelo nunca la escribe.
- su **modo de produccion**, declarado en `tipos_gacetilla_v1.json`: *genera*
  (el modelo escribe la prosa) o *extrae y confirma* (los datos los carga quien
  pide y el agente solo los formatea).
- su **contrato de entrada** (`contracts/entradas/<tipo>_v1.json`): los campos
  obligatorios y los que no aplican a esa clase.

El **renderer es uno solo** (`renderizar`) y lo comparten los siete tipos: no
hay un renderer por tipo. Difusion de actividad es la primera forma declarada y
las otras seis se suman a la misma maquinaria. `_renderizar_mail` de
`procesamiento` delega aca: el marco sale de la forma declarada y no queda
ninguna frase institucional literal en el codigo.

El **gate tambien es uno** (`validar_pieza`): nucleo comun para todos los tipos
mas reglas propias de cada uno. En un tipo que extrae y confirma, el gate
compara la pieza contra **lo confirmado** y no contra texto generado, y por eso
`interpretacion_fallback` no interviene: no hay prosa que extraer.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Protocol

TIPO_DIFUSION = "difusion_de_actividad"

# Largo maximo de la pieza renderizada. Es el mismo tope mecanico que ya usaba
# el pipeline de HU-010: una gacetilla de FIE Informa es un parrafo corto.
MAX_BORRADOR_CHARS = 5000

# Vocabulario de proceso interno (DEF-A1-017): no puede aparecer en la pieza de
# lectura publica. Se busca en el texto normalizado, sin acentos ni mayusculas.
TERMINOS_PROCESO_INTERNO = (
    "revision",
    "validacion",
    "aprobacion",
    "borrador",
    "pendiente",
)

# Verbos y sustantivos de invitacion. Un aviso de otra area informa un hecho:
# afirmar una invitacion es una regla propia del tipo y la hace falsa.
TOKENS_INVITACION = ("invita", "invitamos", "participar", "anotate", "sumate")

# Marcadores de plantilla sin resolver: un hueco que quedo del esqueleto. Las
# formas del corpus usan dos notaciones: `{campo}` en las formulas y
# `<descripcion>` en los esqueletos.
PATRON_MARCADOR = re.compile(r"[{}]|<[^<>\n]+>")

# Placeholders que no son campos de la pieza sino auxiliares del renderer: no
# se cuentan como hechos que tengan que aparecer.
_PLACEHOLDERS_RESERVADOS = frozenset({"dia", "mes", "valor", "fecha_larga"})
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")

_MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
_DIAS_ES = (
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
)


class TipoGacetillaError(ValueError):
    """El tipo pedido no esta declarado en el contrato cerrado."""


class TipoNoGeneraError(ValueError):
    """Se pidio generar prosa para un tipo cuyo modo es extrae y confirma."""


class TipoGeneraError(ValueError):
    """Se pidio confirmar un tipo cuyo modo es genera (su prosa la escribe el modelo)."""


class Generator(Protocol):
    """Puerto minimo del generador, compatible con el de `procesamiento`."""

    def generar(self, prompt: str) -> str: ...


def _leer_json(*ruta: str) -> dict:
    return json.loads(
        files("agente1").joinpath(*ruta).read_text(encoding="utf-8")
    )


@lru_cache(maxsize=1)
def _contrato_tipos() -> dict:
    return _leer_json("contracts", "tipos_gacetilla_v1.json")


def tipos() -> tuple[str, ...]:
    """Los identificadores de los siete tipos del corpus, en orden declarado."""

    return tuple(str(tipo["id"]) for tipo in _contrato_tipos()["tipos"])


def _entrada_tipo(tipo: str) -> dict:
    for entrada in _contrato_tipos()["tipos"]:
        if entrada["id"] == tipo:
            return entrada
    raise TipoGacetillaError(f"tipo de gacetilla no declarado: {tipo!r}")


def modo_de(tipo: str) -> str:
    """Modo de produccion declarado por el tipo: `genera` o `extrae_y_confirma`."""

    return str(_entrada_tipo(tipo)["modo"])


def requiere_actividad(tipo: str) -> bool:
    return bool(_entrada_tipo(tipo)["requiere_actividad"])


@lru_cache(maxsize=16)
def cargar_forma(tipo: str) -> dict:
    """La forma declarada del tipo, desde su archivo versionado."""

    _entrada_tipo(tipo)  # valida que el tipo exista
    return _leer_json("contracts", "formas", f"{tipo}_v1.json")


@lru_cache(maxsize=16)
def cargar_entrada(tipo: str) -> dict:
    """El contrato de entrada del tipo: `required` y campos que no aplican."""

    _entrada_tipo(tipo)
    return _leer_json("contracts", "entradas", f"{tipo}_v1.json")


def campos_obligatorios(tipo: str) -> tuple[str, ...]:
    return tuple(str(campo) for campo in cargar_entrada(tipo)["required"])


def campos_que_no_aplican(tipo: str) -> tuple[str, ...]:
    return tuple(str(campo) for campo in cargar_entrada(tipo).get("no_aplican", []))


def version_de_forma(tipo: str) -> str:
    return str(cargar_forma(tipo)["schema_version"])


# --- Renderer unico ---------------------------------------------------------


def fecha_larga(iso: str) -> str | None:
    """«2026-08-05» -> «miércoles 5 de agosto de 2026», el formato del corpus.

    Misma fecha, otra escritura: no agrega ningun dato. Una fecha no-ISO no se
    inventa: devuelve `None` y el renderer cae al literal del campo.
    """

    try:
        fecha_dt = datetime.strptime(str(iso).strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None
    return (
        f"{_DIAS_ES[fecha_dt.weekday()]} {fecha_dt.day} de "
        f"{_MESES_ES[fecha_dt.month - 1]} de {fecha_dt.year}"
    )


def normalizar_texto(valor: str) -> str:
    """Forma comparable de un texto: sin acentos, sin caso y sin espacios de mas."""

    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_acentos.casefold().split())


def _texto(valores: Mapping[str, str], campo: str) -> str:
    valor = valores.get(campo, "")
    return valor.strip() if isinstance(valor, str) else ""


def _formatear_campo(forma: Mapping[str, object], campo: str, valor: str) -> str:
    """Aplica la formula del campo, si el tipo declara una para el.

    Dos auxiliares disponibles en las formulas: `{valor}` (el valor tal cual) y
    `{fecha_larga}` (la fecha en formato del corpus). Un campo sin formula se
    imprime literal.
    """

    formulas = forma.get("formulas", {})
    plantilla = formulas.get(campo) if isinstance(formulas, Mapping) else None
    if not isinstance(plantilla, str):
        return valor
    return plantilla.format(valor=valor, fecha_larga=fecha_larga(valor) or valor)


def _formatear_plantilla(
    forma: Mapping[str, object], plantilla: str, valores: Mapping[str, str]
) -> str:
    """Expande una formula de la forma, con las fechas en formato del corpus.

    Los campos declarados en `fechas` se imprimen en formato largo; el resto
    sale literal. Es la unica traduccion de datos que hace el renderer y no
    agrega informacion.
    """

    datos = dict(valores)
    fechas = forma.get("fechas", ())
    for campo in fechas if isinstance(fechas, (list, tuple)) else ():
        valor = datos.get(str(campo), "")
        formateada = fecha_larga(valor) if valor else None
        if formateada:
            datos[str(campo)] = formateada
    return plantilla.format(**datos)


def _aplicar_bloque(
    forma: Mapping[str, object], valores: Mapping[str, str], bloque: Mapping[str, object], lineas: list[str]
) -> None:
    clase = bloque.get("clase")
    if clase == "prosa":
        for campo in bloque.get("campos", ()):
            texto = _texto(valores, str(campo))
            if texto:
                lineas += [texto, ""]
    elif clase == "campos":
        grupo: list[str] = []
        etiquetas = forma.get("etiquetas", {})
        for campo in bloque.get("campos", ()):
            valor = _texto(valores, str(campo))
            if not valor:
                continue
            etiqueta = etiquetas.get(campo, "") if isinstance(etiquetas, Mapping) else ""
            grupo.append(f"{etiqueta}{_formatear_campo(forma, str(campo), valor)}")
        if grupo:
            lineas += grupo + [""]
    elif clase == "formula":
        formulas = forma.get("formulas", {})
        plantilla = formulas[str(bloque["id"])]
        lineas += [_formatear_plantilla(forma, plantilla, valores).strip(), ""]
    elif clase == "opcional":
        campo = str(bloque["campo"])
        formulas = forma.get("formulas", {})
        id_formula = str(bloque["formula"]) if _texto(valores, campo) else str(bloque["formula_alterna"])
        lineas += [
            _formatear_plantilla(forma, formulas[id_formula], valores).strip(),
            "",
        ]
    elif clase == "pie":
        _aplicar_pie(forma, valores, lineas)
    else:  # pragma: no cover - un bloque desconocido es un contrato mal editado
        raise TipoGacetillaError(f"bloque de forma desconocido: {clase!r}")


def _aplicar_pie(forma: Mapping[str, object], valores: Mapping[str, str], lineas: list[str]) -> None:
    pie = str(forma.get("pie", "")).format(**valores).strip()
    if pie:
        lineas += [pie, ""]
    firmante = str(forma.get("firmante", "")).format(**valores).strip()
    if firmante:
        lineas += ["--", firmante]


def renderizar(
    tipo: str,
    campos: Mapping[str, str],
    prosa: Mapping[str, str] | None = None,
) -> str:
    """Arma la pieza del tipo a partir de su forma declarada.

    Funcion pura y deterministica: el marco sale de la forma y los hechos de
    `campos`; `prosa` aporta la bajada y el cuerpo de los tipos que generan (o
    el texto confirmado, en los que extraen). Ningun texto institucional fijo
    vive en el codigo: sale de `contracts/formas/<tipo>_v1.json`.
    """

    forma = cargar_forma(tipo)
    valores: dict[str, str] = {
        str(campo): (valor.strip() if isinstance(valor, str) else "")
        for campo, valor in campos.items()
    }
    if prosa:
        valores.update(
            {str(campo): (valor or "").strip() for campo, valor in prosa.items()}
        )
    encabezado = forma["encabezado"]
    lineas = [encabezado["asunto"].format(**valores), ""]
    for bloque in forma["cuerpo"]:
        _aplicar_bloque(forma, valores, bloque, lineas)
    return "\n".join(lineas).rstrip("\n")


def nombre_doc(tipo: str, campos: Mapping[str, str], generado_en: date) -> str:
    """Nombre del Doc segun la convencion del corpus FIE Informa.

    «Fie informa D-M <titulo>» con la fecha de generacion y el titulo. La
    plantilla sale de la forma declarada; el prefijo de borrador lo agrega el
    llamador.
    """

    forma = cargar_forma(tipo)
    titulo = " ".join(str(campos.get("titulo", "")).split())
    return forma["encabezado"]["nombre_doc"].format(
        dia=generado_en.day, mes=generado_en.month, titulo=titulo
    )


# --- Gate: nucleo comun mas reglas por tipo ---------------------------------


def _campos_referenciados(forma: Mapping[str, object]) -> set[str]:
    """Campos que la forma imprime, directa o indirectamente.

    Recorre el plan de armado y junta los placeholders de las formulas, del
    encabezado y del pie. Descarta los auxiliares del renderer.
    """

    referencias: set[str] = set()

    def _sumar(plantilla: str) -> None:
        referencias.update(
            nombre
            for nombre in _PLACEHOLDER_RE.findall(plantilla)
            if nombre not in _PLACEHOLDERS_RESERVADOS
        )

    encabezado = forma.get("encabezado", {})
    if isinstance(encabezado, Mapping):
        for plantilla in encabezado.values():
            if isinstance(plantilla, str):
                _sumar(plantilla)
    formulas = forma.get("formulas", {})
    if isinstance(formulas, Mapping):
        for plantilla in formulas.values():
            if isinstance(plantilla, str):
                _sumar(plantilla)
    _sumar(str(forma.get("pie", "")))
    for bloque in forma.get("cuerpo", ()):
        clase = bloque.get("clase")
        if clase in {"prosa", "campos"}:
            referencias.update(str(campo) for campo in bloque.get("campos", ()))
        elif clase == "opcional":
            referencias.add(str(bloque["campo"]))
    return referencias


def _hecho_presente(valor: str, pieza_normalizada: str) -> bool:
    if normalizar_texto(valor) in pieza_normalizada:
        return True
    fecha = fecha_larga(valor)
    return fecha is not None and normalizar_texto(fecha) in pieza_normalizada


def _regla_aviso_no_invita(forma: Mapping[str, object], pieza: str, campos: Mapping[str, str]) -> list[str]:
    normalizado = normalizar_texto(pieza)
    if any(token in normalizado for token in TOKENS_INVITACION):
        return ["aviso_afirma_invitacion"]
    return []


def _regla_fallecimiento_nombre(forma: Mapping[str, object], pieza: str, campos: Mapping[str, str]) -> list[str]:
    nombre = _texto(campos, "nombre")
    if "fallecimiento" in normalizar_texto(pieza) and (
        not nombre or not _hecho_presente(nombre, normalizar_texto(pieza))
    ):
        return ["fallecimiento_sin_nombre_confirmado"]
    return []


def _regla_emisor_confirmado(forma: Mapping[str, object], pieza: str, campos: Mapping[str, str]) -> list[str]:
    area = _texto(campos, "area_emisora")
    if not area or not _hecho_presente(area, normalizar_texto(pieza)):
        return ["emisor_area_no_confirmada"]
    return []


# Reglas propias de cada tipo, ademas del nucleo comun. El apunte del ADR 0001
# y la decision #120 las enumeran: un aviso no puede afirmar una invitacion, un
# fallecimiento no puede inventar un nombre, un comunicado no puede inventar un
# area emisora. Se declaran aca, del lado del codigo, para que el catalogo no
# pueda habilitar un tipo sin su regla.
REGLAS_POR_TIPO: dict[str, tuple] = {
    "aviso_de_otra_area": (_regla_aviso_no_invita,),
    "fallecimiento": (_regla_fallecimiento_nombre,),
    "convocatoria_interna": (_regla_emisor_confirmado,),
    "newsletter": (_regla_emisor_confirmado,),
}


def validar_pieza(tipo: str, pieza: str, campos: Mapping[str, str]) -> list[str]:
    """Nucleo comun mas reglas por tipo.

    Nucleo comun para los siete tipos: largo, marca de plantilla sin resolver,
    sin proceso interno y cada hecho referenciado por la forma presente en la
    pieza. Reglas por tipo: las de `REGLAS_POR_TIPO`. Devuelve una lista de
    codigos —no un booleano— para que la auditoria diga que fallo.

    En un tipo que extrae y confirma, `campos` es lo confirmado; la comparacion
    es contra eso y nunca contra texto generado.
    """

    forma = cargar_forma(tipo)
    errores: list[str] = []
    if len(pieza) > MAX_BORRADOR_CHARS:
        return ["length_out_of_range"]
    if PATRON_MARCADOR.search(pieza):
        errores.append("marcador_sin_resolver")
    normalizado = normalizar_texto(pieza)
    if any(termino in normalizado for termino in TERMINOS_PROCESO_INTERNO):
        errores.append("proceso_interno")
    for campo in _campos_referenciados(forma):
        valor = _texto(campos, campo)
        if valor and not _hecho_presente(valor, normalizado):
            errores.append("hecho_perdido")
            break
    for regla in REGLAS_POR_TIPO.get(tipo, ()):
        errores += regla(forma, pieza, campos)
    return errores


# --- Produccion por modo ----------------------------------------------------


def construir_prompt(tipo: str, campos: Mapping[str, str]) -> str:
    """Arma el prompt del tipo que genera, a partir de su plantilla versionada."""

    forma = cargar_forma(tipo)
    salida = forma.get("salida_modelo") or {}
    prompt_version = str(salida["prompt_version"])
    plantilla = (
        files("agente1")
        .joinpath("prompts", f"{prompt_version}.txt")
        .read_text(encoding="utf-8")
    )
    datos_fuente = "\n".join(f"{campo}: {valor}" for campo, valor in campos.items())
    return plantilla.replace("{datos_fuente}", datos_fuente)


def _validar_prosa_directa(forma: Mapping[str, object], salida: str) -> list[str]:
    salida = salida.strip() if isinstance(salida, str) else ""
    if not salida:
        return ["prosa_vacia"]
    max_palabras = int((forma.get("salida_modelo") or {}).get("max_palabras", 0))
    if max_palabras and len(salida.split()) > max_palabras:
        return ["prosa_muy_larga"]
    if re.search(r"[.!?]$", salida) is None:
        return ["prosa_sin_puntuacion"]
    if re.search(r"\d|@|https?://|www\.|\$", salida):
        return ["prosa_con_datos"]
    normalizado = normalizar_texto(salida)
    if any(termino in normalizado for termino in TERMINOS_PROCESO_INTERNO):
        return ["prosa_con_proceso_interno"]
    return []


def generar_pieza(
    tipo: str, campos: Mapping[str, str], generator: Generator
) -> tuple[str, list[str]]:
    """Genera la pieza de un tipo cuyo modo es *genera* con salida de prosa directa.

    La forma declara la clase de salida (`salida_modelo.clase`). Los tipos con
    clase `ficha_actividad` (difusion) los orquesta `procesamiento`, que conoce
    su ficha; aca solo se produce la prosa directa (saludo o efemeride). Nunca
    se genera para un tipo que extrae y confirma: eso levanta `TipoNoGeneraError`.
    """

    forma = cargar_forma(tipo)
    if forma["modo"] != "genera":
        raise TipoNoGeneraError(tipo)
    clase = str((forma.get("salida_modelo") or {}).get("clase"))
    if clase != "prosa_directa":
        raise TipoGacetillaError(
            f"el tipo {tipo!r} no se genera por prosa directa sino por {clase!r}"
        )
    prompt = construir_prompt(tipo, campos)
    salida = generator.generar(prompt)
    errores = _validar_prosa_directa(forma, salida)
    if errores:
        return "", errores
    pieza = renderizar(tipo, campos, prosa={"cuerpo": salida.strip()})
    return pieza, validar_pieza(tipo, pieza, campos)


def confirmar_pieza(tipo: str, campos: Mapping[str, str]) -> tuple[str, list[str]]:
    """Formatea un tipo cuyo modo es *extrae y confirma*, sin llamar al modelo.

    Los datos los carga quien pide; el agente solo los formatea y el gate
    compara contra lo confirmado. `interpretacion_fallback` no interviene: no
    hay prosa que extraer del pedido en lenguaje natural.
    """

    if modo_de(tipo) != "extrae_y_confirma":
        raise TipoGeneraError(tipo)
    faltantes = [campo for campo in campos_obligatorios(tipo) if not _texto(campos, campo)]
    if faltantes:
        return "", ["campos_obligatorios_ausentes"]
    pieza = renderizar(tipo, campos)
    return pieza, validar_pieza(tipo, pieza, campos)
