"""HU-013 (#20, #22, #23): de una solicitud en lenguaje natural a un borrador.

Este módulo es el seam nuevo: `interpretar_solicitud` recibe la prosa de una
persona de la SEU junto con la identidad que afirma el canal, la clasifica a
una **intención** de un catálogo cerrado y, cuando corresponde, despacha al
pipeline de gacetilla (HU-010) o al de post (HU-011) que ya existen. Nunca
propaga excepciones de la fuente, del generador ni del destino: cada camino
—éxito o falla— termina en un `ResultadoInterpretacion` y en una línea de
auditoría.

Alcance de estos incrementos: la persona nombra la intención y, o bien un
identificador de actividad reconocible en la prosa (#20), o bien datos
suficientes para resolver la actividad por **búsqueda difusa
determinística** sobre el índice que arma `fuente.enumerar()` (#23, requiere
#19), normalizando título, fecha y organización. De la búsqueda difusa se
acepta directamente el caso de **coincidencia única y clara**; cuando eso no
alcanza —ninguna coincidencia por encima del umbral, o varias cercanas entre
sí— el agente no adivina ni rechaza de una: junta hasta
`MAX_CANDIDATAS_REPREGUNTA` actividades candidatas y **repregunta** (#25), en
lugar de generar sobre una elección propia. Para `generar_post` (#22) la
prosa además nombra el canal (Instagram o LinkedIn).

**Estado entre turnos (#25).** Una repregunta crea una `InteraccionPendiente`
que el núcleo guarda a través del puerto `RegistroPendientes`, si el llamador
provee uno. Esa pendiente conserva únicamente orden, identificador, título y
fecha de cada candidata, la intención ya clasificada y el instante de
vencimiento — nunca la prosa del pedido que la originó. El mensaje
siguiente de la misma persona (`solicitante.identificador`) puede resolverla
por número de orden ("el segundo") o por un rasgo distintivo de una
candidata (su título parcial, o el día de la semana de su fecha, como "el
del martes"): en ambos casos es una búsqueda determinística sobre ese
conjunto chico y cerrado que el propio agente produjo, nunca interpretación
sobre contenido externo. Un pedido nuevo y completo (identificador explícito,
o coincidencia única y clara) descarta la pendiente en lugar de dejarse
capturar por ella. La pendiente vence sola —quince minutos, con el reloj
inyectado— y perder el estado nunca rompe nada: la persona vuelve a
preguntar. Hay como mucho una interacción pendiente por persona: la más
reciente reemplaza a cualquier anterior.

Deliberadamente **no** entran acá:

- el canal de interacción como adapter (#24) — no confundir con el canal de
  la red social que resuelve `_resolver_canal`, que es un dato del dominio de
  `generar_post`, no el transporte de la interacción;
- el fallback con modelo ante lo ambiguo (#26) — la resolución de actividad
  sigue siendo íntegramente de código, nunca del modelo, aun así; #26 se
  engancha exactamente donde este incremento deja de intentar resolver: sin
  identificador explícito, sin coincidencia única y clara, y sin una
  referencia válida a una interacción pendiente.

Decisiones que no se ven en el código:

- **La prosa nunca llega a un prompt.** Lo único que sale de `texto` hacia los
  pipelines de gacetilla y de post es el identificador de actividad —extraído
  o resuelto— y, para `generar_post`, el nombre del canal ya resuelto: ambos
  pasan por sus propios contratos (`id_solicitud`, `canal`). El texto libre se
  usa únicamente para clasificar y para buscar localmente, en este proceso,
  contra un vocabulario cerrado y contra un índice estructurado — nunca como
  instrucción hacia el generador.
- **La resolución de actividad es código, no el modelo.** `fuente.enumerar()`
  entrega filas estructuradas; la comparación es un puntaje determinístico
  sobre texto normalizado (ver `_resolver_actividad_por_similitud`). El
  contenido de la planilla no entra a ningún prompt: en el peor caso, el
  código elige mal una actividad, lo que es visible de inmediato en el
  `resumen` de la respuesta y queda bloqueado igual por el gate de hechos y
  por la validación humana. Ver ADR 0001.
- **La clasificación es determinística y el catálogo es cerrado.** Un texto
  que no activa ninguna palabra clave del catálogo se clasifica
  `fuera_de_alcance`; no se aproxima a la intención más parecida. Ver
  ADR 0001.
- **El canal de `generar_post` se resuelve con código determinístico, nunca
  con el modelo.** `_resolver_canal` reconoce la mención literal de
  "Instagram" o "LinkedIn" en la prosa. Un pedido que no menciona ninguno de
  los dos, o que menciona los dos a la vez, no tiene un canal resuelto sin
  ambigüedad: en ambos casos el resultado es el mismo, explícito y sin
  inventar un default — `INCOMPLETA` con `canal_no_encontrado`, el mismo
  tratamiento que ya recibe un identificador de actividad ausente. No hay
  heurística de "canal más probable": o se reconoce exactamente uno, o se
  pide el dato.
- **La identidad se exige y se registra, nunca se verifica.** El canal afirma
  quién pide y con qué rol; el núcleo decide con ese dato pero no tiene forma
  de comprobarlo. Ver ADR 0002. Cada línea de auditoría lleva
  `identidad_verificada: false` en este incremento, para que nadie la lea
  como si acreditara control de acceso.
- **El registro nunca lleva prosa.** Sólo el derivado estructurado:
  correlación, intención, identificador de actividad, si intervino el modelo
  (siempre `False` en este incremento, que no implementa el fallback de
  #26), resultado, códigos y hashes. Esto vale igual para una repregunta: el
  código de resultado (`repregunta_generada`) es la única marca que deja, sin
  volcar las candidatas al log.
- **La respuesta nunca lleva el texto completo del borrador.** Éxito devuelve
  un puntero (`borrador_path` / `referencia_borrador`) más un resumen corto
  armado a partir de datos ya institucionales (título, fecha), nunca el
  cuerpo generado. Una repregunta devuelve, en el mismo espíritu, sólo
  `candidatas` (datos ya institucionales del índice) y un `resumen` que las
  enumera, nunca la prosa del pedido.
- **La interacción pendiente conserva sólo lo que el propio agente produjo.**
  `InteraccionPendiente` no tiene un campo de texto ni de prosa: sus
  candidatas son las mismas que ya se devolvieron en la repregunta. Resolver
  "el segundo" o "el del martes" es, por construcción, una búsqueda sobre ese
  conjunto cerrado — nunca una segunda pasada de interpretación sobre
  contenido externo.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from importlib.resources import files
from pathlib import Path
from typing import Callable, Protocol

from .destinos import DestinoBorradores, ReferenciaBorrador
from .fuentes import FuenteSolicitudes
from .posts import procesar_post_estructurado
from .presupuesto import presupuesto_minimo_num_predict
from .procesamiento import Generator, procesar_solicitud


HU = "HU-013"
CONTRACT_VERSION = "intenciones_v1"

CATALOGO_INTENCIONES = json.loads(
    files("agente1")
    .joinpath("contracts", "intenciones_v1.schema.json")
    .read_text(encoding="utf-8")
)
INTENCIONES = tuple(CATALOGO_INTENCIONES["intenciones"])
INTENCIONES_POR_ID: dict[str, dict[str, object]] = {
    str(item["id"]): item for item in INTENCIONES
}
IDS_INTENCIONES = frozenset(INTENCIONES_POR_ID)
INTENCION_FUERA_DE_ALCANCE = "fuera_de_alcance"
ROLES_HABILITADOS = frozenset(
    str(rol) for rol in CATALOGO_INTENCIONES["roles_habilitados_provisionales"]
)
# Fuente de verdad, del lado del código, de qué intención sabe producir
# realmente un borrador en este seam. Deliberadamente no se deriva de
# `pipeline_integrado` del catálogo: ese campo es una declaración del
# artefacto JSON, y basar el despacho en una declaración autoreportada
# permitiría que alguien la marque `true` sin escribir el despacho. Acá se
# fuerza la correspondencia inversa: el catálogo declara `pipeline_integrado`
# para documentar la intención, pero quien decide en tiempo de ejecución —y
# quien exige que exista un caso de prueba, ver `test_interpretacion.py`— es
# este conjunto.
INTENCIONES_CON_DESPACHO = frozenset({"generar_gacetilla", "generar_post"})


# --- Fallback con modelo local (#26) ----------------------------------------
# El modelo interviene sólo cuando el camino determinístico no resolvió, y su
# única salida admitida es una intención del catálogo más términos de búsqueda
# estructurados. `interpretacion_fallback_v1` es el contrato de esa salida; su
# enum tiene que ser el mismo catálogo que `intenciones_v1`, y hay una prueba
# que falla si dejan de coincidir. Ver ADR 0001.
CONTRATO_FALLBACK = json.loads(
    files("agente1")
    .joinpath("contracts", "interpretacion_fallback_v1.schema.json")
    .read_text(encoding="utf-8")
)
CONTRATO_FALLBACK_VERSION = str(CONTRATO_FALLBACK["x-contract-version"])
PROMPT_FALLBACK = (
    files("agente1")
    .joinpath("prompts", "interpretacion_fallback_v1.txt")
    .read_text(encoding="utf-8")
)
MAX_TERMINOS_FALLBACK = int(
    CONTRATO_FALLBACK["properties"]["terminos_busqueda"]["maxItems"]
)
MAX_LARGO_TERMINO_FALLBACK = int(
    CONTRATO_FALLBACK["properties"]["terminos_busqueda"]["items"]["maxLength"]
)
# El presupuesto se deriva del contrato con la misma maquinaria que usa el
# pipeline de gacetilla (`presupuesto.py`), no se fija a mano: si una versión
# futura del contrato admite más términos o términos más largos, este número
# sube solo y la regresión avisa antes de que alguien acepte un presupuesto que
# ya no alcanza. Es la lección de DEF-A1-013.
NUM_PREDICT_FALLBACK = presupuesto_minimo_num_predict(CONTRATO_FALLBACK)

# Identificador "explícito": palabras alfabéticas cortas, un guion y dígitos,
# como los que ya produce el dataset sintético (`SYN-001`). Es una forma
# reconocible en prosa suelta sin necesitar que la persona la etiquete ("el
# identificador es..."). No es resolución difusa: sólo reconoce un patrón
# sintáctico, nunca compara contra el contenido de la planilla. Todo lo que
# este patrón acepta es, por construcción, un subconjunto de lo que acepta el
# contrato de `id_solicitud` de HU-010/HU-011 (alfanumérico, guion y guion
# bajo): la validación de forma final la vuelve a hacer `procesar_solicitud`,
# así que acá no hace falta repetirla.
PATRON_IDENTIFICADOR_EXPLICITO = re.compile(r"\b[A-Za-z]{2,10}-[0-9]{1,6}\b")


def _normalizar(texto: str) -> str:
    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )
    return sin_acentos.casefold()


# --- Clasificación determinística ------------------------------------------
# Cada patrón reconoce una familia de palabras del dominio, sobre el texto ya
# normalizado (sin acentos, sin mayúsculas). No pretenden tolerar errores de
# tipeo: eso queda para la resolución de actividad (#23), no para reconocer
# qué tipo de pieza se pide.
PATRON_AJUSTAR = re.compile(
    r"\b(?:ajust\w*|correg\w*|corrig\w*|modific\w*|cambi\w*)\b[\s\S]*\bborrador\w*\b"
    r"|\bborrador\w*\b[\s\S]*\b(?:ajust\w*|correg\w*|corrig\w*|modific\w*|cambi\w*)\b"
)
PATRON_GACETILLA = re.compile(r"\bgacetill\w*\b")
PATRON_POST = re.compile(r"\b(?:post\w*|instagram\w*|linkedin\w*)\b")
PATRON_NEWSLETTER = re.compile(r"\b(?:newsletter\w*|boletin\w*)\b")
PATRON_MAIL = re.compile(r"\b(?:mail\w*|correo\w*|email\w*)\b")


def _clasificar_intencion(texto: str) -> str:
    """Determina la intención a partir de palabras clave del dominio.

    Nunca levanta: cualquier texto que no dispare ninguna regla termina en
    `fuera_de_alcance`. El orden de los `if` es la política de desempate
    cuando el texto activa más de un patrón; `ajustar_borrador` va primero
    porque combina dos palabras y es la más específica.
    """

    normalizado = _normalizar(texto)
    if PATRON_AJUSTAR.search(normalizado):
        return "ajustar_borrador"
    if PATRON_GACETILLA.search(normalizado):
        return "generar_gacetilla"
    if PATRON_POST.search(normalizado):
        return "generar_post"
    if PATRON_NEWSLETTER.search(normalizado):
        return "generar_newsletter"
    if PATRON_MAIL.search(normalizado):
        return "generar_mail"
    return INTENCION_FUERA_DE_ALCANCE


def _extraer_identificador_explicito(texto: str) -> str | None:
    """Primer token con forma de identificador de actividad, si hay uno.

    No consulta la fuente ni compara contra su contenido: es un
    reconocimiento sintáctico sobre la prosa. La validación de que la
    actividad exista queda, como siempre, del lado de `FuenteSolicitudes`.
    """

    coincidencia = PATRON_IDENTIFICADOR_EXPLICITO.search(texto)
    return coincidencia.group(0) if coincidencia is not None else None


# Canal de red social para `generar_post` (#22). Reconoce la mención literal
# de cada red sobre el texto ya normalizado (sin acentos, sin mayúsculas),
# igual que `_clasificar_intencion`: código determinístico, nunca el modelo.
# No es resolución difusa ni sinónimos: sólo el nombre de la red.
PATRON_CANAL_INSTAGRAM = re.compile(r"\binstagram\w*\b")
PATRON_CANAL_LINKEDIN = re.compile(r"\blinkedin\w*\b")


def _resolver_canal(texto: str) -> str | None:
    """Resuelve el canal de `generar_post` a partir de la prosa, o `None`.

    `None` significa "no hay un canal resuelto sin ambigüedad": cubre tanto el
    pedido que no menciona ninguna red como el que menciona las dos a la vez.
    Deliberadamente no hay un canal por defecto ni una preferencia entre
    ambos: el llamador trata `None` como dato faltante, igual que un
    identificador de actividad que no aparece en el texto.
    """

    normalizado = _normalizar(texto)
    es_instagram = PATRON_CANAL_INSTAGRAM.search(normalizado) is not None
    es_linkedin = PATRON_CANAL_LINKEDIN.search(normalizado) is not None
    if es_instagram and not es_linkedin:
        return "instagram"
    if es_linkedin and not es_instagram:
        return "linkedin"
    return None


# --- Resolución difusa de actividad (#23) ------------------------------------
# Cuando la prosa no trae un identificador explícito, se intenta resolver la
# actividad por similitud contra el índice que arma `fuente.enumerar()` (#19).
# Todo lo que sigue es código determinístico sobre texto ya normalizado: nada
# de esto arma un prompt ni consulta un modelo. Ver ADR 0001 y el docstring
# del módulo.
#
# El puntaje de una actividad es un promedio ponderado de tres "coberturas"
# de tokens (título, fecha, organización): para cada palabra de contenido del
# campo, se busca su mejor coincidencia entre las palabras de la consulta con
# `difflib.SequenceMatcher.ratio()` —determinístico, sin semillas de hash de
# por medio— y se promedia. Comparar por palabra en vez de por cadena
# completa es lo que permite tolerar relleno de la prosa ("quiero", "por
# favor") sin que ese relleno diluya el puntaje: una palabra de relleno de la
# consulta simplemente no aporta a la cobertura de ninguna palabra del campo,
# no resta.
#
# El umbral, el margen y los pesos no salen de una fórmula: se calibraron a
# mano contra el dataset sintético (`data/actividades_sinteticas.csv`) y el
# corpus versionado de frases realistas (`data/frases_resolucion_actividad.csv`),
# de modo que toda frase del corpus resuelva a su actividad esperada y que
# "el taller del martes" —ninguna actividad del dataset cae un martes—
# siga sin resolver. El título pesa más que la fecha y la organización
# porque es, en la prosa real, el dato que más se nombra; fecha y
# organización actúan sobre todo como desempate cuando dos títulos son
# parecidos (ver `test_frase_del_corpus_resuelve_a_la_actividad_esperada` y
# `test_pedido_con_coincidencia_cercana_pero_no_identica_no_genera_borrador`
# en `test_interpretacion.py`). Cambiar cualquiera de estos números exige
# volver a correr esas pruebas.
UMBRAL_COINCIDENCIA_CLARA = 0.55
MARGEN_DESAMBIGUACION = 0.10
_PESO_TITULO = 0.60
_PESO_FECHA = 0.25
_PESO_ORGANIZA = 0.15

_PATRON_TOKEN = re.compile(r"[a-z0-9]+")
# Palabras puramente gramaticales del español: artículos, preposiciones y
# pronombres cortos que aparecen tanto en la prosa como, a veces, en la
# escritura en letras de una fecha ("5 de agosto"). Sin filtrarlas, un "de"
# de la consulta coincidiría por igual contra el "de" de cualquier fecha o
# título, inflando el puntaje de todas las actividades por parejo y anulando
# la capacidad de discriminar entre ellas.
_STOPWORDS_ES = frozenset(
    {
        "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas",
        "y", "o", "en", "con", "por", "para", "al", "que", "su", "sus",
        "lo", "le", "les", "es", "son", "esa", "ese", "esta", "este",
    }
)
_MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
    12: "diciembre",
}


def _tokenizar(texto_normalizado: str) -> tuple[str, ...]:
    """Palabras de contenido de un texto ya pasado por `_normalizar`.

    Descarta palabras puramente gramaticales y palabras cortas que no son
    números: son las que menos aportan a distinguir una actividad de otra.
    """

    tokens = _PATRON_TOKEN.findall(texto_normalizado)
    return tuple(
        token
        for token in tokens
        if token not in _STOPWORDS_ES and (len(token) >= 3 or token.isdigit())
    )


def _variantes_fecha_tokenizadas(fecha: str) -> tuple[str, ...]:
    """Tokens de contenido de una fecha, en las formas en que se la nombra.

    Una fecha ISO ("2026-08-05") casi nunca aparece así en prosa suelta; se
    la nombra con el día y el mes en letras ("5 de agosto"). Se agregan
    ambas representaciones al índice para que la fecha pueda aportar a la
    resolución tanto si la prosa la cita en formato ISO como en letras.
    """

    fecha = fecha.strip() if isinstance(fecha, str) else ""
    if not fecha:
        return ()
    tokens: set[str] = set(_tokenizar(_normalizar(fecha)))
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return tuple(sorted(tokens))
    nombre_mes = _MESES_ES[fecha_dt.month]
    tokens.update(
        _tokenizar(
            _normalizar(f"{fecha_dt.day} de {nombre_mes} de {fecha_dt.year}")
        )
    )
    return tuple(sorted(tokens))


def _cobertura_tokens(
    tokens_campo: tuple[str, ...], tokens_consulta: tuple[str, ...]
) -> float:
    """Fracción de `tokens_campo` reconocible entre `tokens_consulta`.

    Para cada palabra del campo (título, fecha u organización), se toma su
    mejor `ratio()` contra cualquier palabra de la consulta —tolera errores
    de tipeo de a una palabra— y se promedia. Un campo vacío no aporta nada
    (cobertura 0), nunca indeterminado.
    """

    if not tokens_campo:
        return 0.0
    if not tokens_consulta:
        return 0.0
    total = 0.0
    for token_campo in tokens_campo:
        mejor = max(
            SequenceMatcher(None, token_campo, token_consulta, autojunk=False).ratio()
            for token_consulta in tokens_consulta
        )
        total += mejor
    return total / len(tokens_campo)


def _puntuar_actividad(tokens_consulta: tuple[str, ...], fila: dict[str, str]) -> float:
    titulo = str(fila.get("titulo", "") or "")
    organiza = str(fila.get("organiza", "") or "")
    fecha = str(fila.get("fecha", "") or "")

    cobertura_titulo = _cobertura_tokens(_tokenizar(_normalizar(titulo)), tokens_consulta)
    cobertura_organiza = _cobertura_tokens(_tokenizar(_normalizar(organiza)), tokens_consulta)
    cobertura_fecha = _cobertura_tokens(_variantes_fecha_tokenizadas(fecha), tokens_consulta)

    return (
        _PESO_TITULO * cobertura_titulo
        + _PESO_FECHA * cobertura_fecha
        + _PESO_ORGANIZA * cobertura_organiza
    )


def _resolver_actividad_por_similitud(texto: str, fuente: FuenteSolicitudes) -> str | None:
    """Resuelve a lo sumo un `id_solicitud`, sólo ante coincidencia única y clara.

    Nunca propaga: cualquier falla al enumerar la fuente, o cualquier fila
    con forma inesperada, se trata como "no se encontró actividad", igual
    que cero coincidencias. Ninguna coincidencia y varias coincidencias
    cercanas entre sí se tratan igual en este incremento (#23): sólo se
    acepta la actividad ganadora cuando supera el umbral mínimo *y* saca una
    ventaja clara sobre la segunda mejor — un empate exacto en el puntaje
    más alto queda, por construcción, siempre por debajo de ese margen, así
    que nunca se acepta como ganador.

    El orden de `candidatos` se desempata por `id_solicitud` (orden
    alfabético) ante puntajes iguales. Esto no es lo que hace reproducible
    al resultado devuelto: eso ya lo garantiza que el puntaje sea una
    función pura del texto normalizado, sin estructuras de orden no
    determinístico de por medio. El desempate por id es más bien higiene
    defensiva: mantiene el orden de la lista interna de candidatos
    independiente del orden en que la fuente haya enumerado las filas, en
    vez de heredarlo por la estabilidad incidental de `sort()`.
    """

    try:
        actividades = fuente.enumerar()
    except Exception:
        return None
    if not isinstance(actividades, list):
        return None

    tokens_consulta = _tokenizar(_normalizar(texto))
    if not tokens_consulta:
        return None

    candidatos: list[tuple[float, str]] = []
    for fila in actividades:
        if not isinstance(fila, dict):
            continue
        id_solicitud = fila.get("id_solicitud")
        if not isinstance(id_solicitud, str) or not id_solicitud:
            continue
        try:
            puntaje = _puntuar_actividad(tokens_consulta, fila)
        except Exception:
            continue
        candidatos.append((puntaje, id_solicitud))

    if not candidatos:
        return None
    candidatos.sort(key=lambda candidato: (-candidato[0], candidato[1]))

    mejor_puntaje, mejor_id = candidatos[0]
    if mejor_puntaje < UMBRAL_COINCIDENCIA_CLARA:
        return None
    if len(candidatos) > 1:
        segundo_puntaje, _ = candidatos[1]
        if mejor_puntaje - segundo_puntaje < MARGEN_DESAMBIGUACION:
            return None
    return mejor_id


# --- Repregunta con candidatas y resolución de la pendiente (#25) -----------
# Cuando `_resolver_actividad_por_similitud` no alcanza una coincidencia
# única y clara, se junta un puñado de candidatas para que la persona elija
# en el turno siguiente, en lugar de adivinar o rechazar de una. Todo lo que
# sigue reutiliza el mismo puntaje determinístico (`_puntuar_actividad`) y
# los mismos tokenizadores que la resolución directa: no hay una segunda
# fuente de verdad sobre qué tan parecida es una actividad a la consulta.
MAX_CANDIDATAS_REPREGUNTA = 5

# Referencia a una candidata por número de orden. Cubre la palabra ordinal en
# sus dos géneros y su forma apocopada ("primer"); el dígito ("1", "2", ...)
# se reconoce aparte, en `_referencia_por_digito`, y con prioridad menor: un
# dígito suelto puede venir de una fecha ("el del 5 de agosto") y confundirse
# con un número de orden, así que sólo se usa como último recurso, después de
# intentar la palabra ordinal y el rasgo distintivo.
_ORDEN_POR_PALABRA_ES: dict[str, int] = {
    "primero": 1, "primera": 1, "primer": 1,
    "segundo": 2, "segunda": 2,
    "tercero": 3, "tercera": 3, "tercer": 3,
    "cuarto": 4, "cuarta": 4,
    "quinto": 5, "quinta": 5,
}

# Días de la semana en español, indexados como `datetime.weekday()` (0 =
# lunes). Es la única forma en que una fecha ISO ("2026-08-05") se vuelve un
# rasgo nombrable en prosa suelta ("el del martes"): ninguna otra parte del
# módulo necesita el día de la semana, porque la resolución directa (#23) se
# calibró sin él — ver `UMBRAL_COINCIDENCIA_CLARA` más arriba.
_DIAS_SEMANA_ES = (
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
)


def _generar_candidatas(
    texto: str, fuente: FuenteSolicitudes
) -> tuple["CandidataActividad", ...]:
    """Hasta `MAX_CANDIDATAS_REPREGUNTA` actividades para una repregunta.

    Nunca propaga: cualquier falla al enumerar la fuente, o cualquier fila
    con forma inesperada, se trata como "no hay candidatas". Una actividad
    con puntaje exactamente `0.0` (ningún token en común con la consulta) se
    descarta: no tiene sentido ofrecerla como opción. Por lo demás, no hay un
    umbral de confianza como en la resolución directa —a propósito: llegar
    hasta acá ya significa que ninguna actividad se pudo aceptar sola, y el
    punto de la repregunta es dejar elegir a la persona en vez de que el
    código seleccione con un puntaje que no llegó a convencerlo.
    """

    try:
        actividades = fuente.enumerar()
    except Exception:
        return ()
    if not isinstance(actividades, list):
        return ()

    tokens_consulta = _tokenizar(_normalizar(texto))
    if not tokens_consulta:
        return ()

    puntuadas: list[tuple[float, str, str, str]] = []
    for fila in actividades:
        if not isinstance(fila, dict):
            continue
        id_solicitud = fila.get("id_solicitud")
        if not isinstance(id_solicitud, str) or not id_solicitud:
            continue
        try:
            puntaje = _puntuar_actividad(tokens_consulta, fila)
        except Exception:
            continue
        if puntaje <= 0.0:
            continue
        titulo = str(fila.get("titulo", "") or "")
        fecha = str(fila.get("fecha", "") or "")
        puntuadas.append((puntaje, id_solicitud, titulo, fecha))

    if not puntuadas:
        return ()
    puntuadas.sort(key=lambda item: (-item[0], item[1]))
    return tuple(
        CandidataActividad(
            orden=orden, id_actividad=id_solicitud, titulo=titulo, fecha=fecha
        )
        for orden, (_, id_solicitud, titulo, fecha) in enumerate(
            puntuadas[:MAX_CANDIDATAS_REPREGUNTA], start=1
        )
    )


def _dia_semana_token(fecha: str) -> str | None:
    """Nombre del día de la semana de una fecha ISO, o `None` si no aplica."""

    fecha = fecha.strip() if isinstance(fecha, str) else ""
    if not fecha:
        return None
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return None
    return _DIAS_SEMANA_ES[fecha_dt.weekday()]


def _tokens_distintivos(candidata: "CandidataActividad") -> frozenset[str]:
    """Tokens con los que se puede nombrar esta candidata en prosa suelta.

    Título y fecha —incluido el día de la semana— son exactamente los datos
    que la candidata conserva (ver `CandidataActividad`): esta función no
    vuelve a tocar la fuente ni ningún otro campo de la actividad.
    """

    tokens = set(_tokenizar(_normalizar(candidata.titulo)))
    tokens.update(_variantes_fecha_tokenizadas(candidata.fecha))
    dia = _dia_semana_token(candidata.fecha)
    if dia is not None:
        tokens.add(dia)
    return frozenset(tokens)


def _referencia_por_orden(
    tokens_mensaje: frozenset[str], candidatas: tuple["CandidataActividad", ...]
) -> "CandidataActividad | None":
    """Resuelve por palabra ordinal ("el segundo"). Nunca por dígito suelto."""

    ordenes_mencionados = {
        _ORDEN_POR_PALABRA_ES[token]
        for token in tokens_mensaje
        if token in _ORDEN_POR_PALABRA_ES
    }
    if len(ordenes_mencionados) != 1:
        return None
    (orden,) = ordenes_mencionados
    for candidata in candidatas:
        if candidata.orden == orden:
            return candidata
    return None


def _referencia_por_rasgo(
    tokens_mensaje: frozenset[str], candidatas: tuple["CandidataActividad", ...]
) -> "CandidataActividad | None":
    """Resuelve por un rasgo distintivo (título parcial, fecha, día de la
    semana) que sólo aparezca en una de las candidatas.

    Intersección de tokens, no puntaje: el universo de candidatas es chico y
    cerrado, así que alcanza con que el mensaje mencione algo que distinga a
    una sola de ellas. Si el rasgo aparece en más de una candidata —dos
    títulos parecidos entre sí, por ejemplo— no hay forma de saber cuál
    quiso decir la persona, y no se elige ninguna.
    """

    coincidencias = [
        candidata
        for candidata in candidatas
        if _tokens_distintivos(candidata) & tokens_mensaje
    ]
    if len(coincidencias) == 1:
        return coincidencias[0]
    return None


def _referencia_por_digito(
    tokens_mensaje: frozenset[str], candidatas: tuple["CandidataActividad", ...]
) -> "CandidataActividad | None":
    """Último recurso: un dígito suelto ("2") como número de orden.

    Se intenta después de la palabra ordinal y del rasgo distintivo porque un
    dígito puede venir de una fecha mencionada en el mensaje y no de una
    referencia al orden.
    """

    ordenes_validos = {candidata.orden for candidata in candidatas}
    digitos_mencionados = {
        int(token)
        for token in tokens_mensaje
        if token.isdigit() and int(token) in ordenes_validos
    }
    if len(digitos_mencionados) != 1:
        return None
    (orden,) = digitos_mencionados
    for candidata in candidatas:
        if candidata.orden == orden:
            return candidata
    return None


def _resolver_referencia_pendiente(
    texto: str, candidatas: tuple["CandidataActividad", ...]
) -> "CandidataActividad | None":
    """Resuelve el mensaje siguiente contra las candidatas de una pendiente.

    Búsqueda determinística sobre un conjunto chico y cerrado que el propio
    agente produjo — nunca interpretación sobre contenido externo. Orden de
    intento: palabra ordinal, rasgo distintivo, dígito suelto; el primero que
    resuelva sin ambigüedad gana.
    """

    tokens_mensaje = frozenset(_tokenizar(_normalizar(texto)))
    if not tokens_mensaje:
        return None
    referencia = _referencia_por_orden(tokens_mensaje, candidatas)
    if referencia is not None:
        return referencia
    referencia = _referencia_por_rasgo(tokens_mensaje, candidatas)
    if referencia is not None:
        return referencia
    return _referencia_por_digito(tokens_mensaje, candidatas)


def _resumen_repregunta(candidatas: tuple["CandidataActividad", ...]) -> str:
    """Texto corto que enumera las candidatas, armado sólo con sus datos.

    Análogo a `_resumen_desde_fuente`: nunca prosa del pedido, sólo datos ya
    institucionales (título, fecha) que las propias candidatas conservan.
    """

    lineas = [
        f"{candidata.orden}) {candidata.titulo}"
        + (f" ({candidata.fecha})" if candidata.fecha else "")
        for candidata in candidatas
    ]
    return (
        "Encontré más de una actividad posible. Respondé con su número de "
        "orden o un dato que la distinga (por ejemplo, la fecha):\n"
        + "\n".join(lineas)
    )


@dataclass(frozen=True)
class TerminosInterpretados:
    """Lo único que se acepta de vuelta del modelo, ya validado (#26).

    `intencion` pertenece al catálogo cerrado y `terminos` son palabras
    sueltas acotadas por el contrato. No hay ningún otro campo: el modelo no
    devuelve texto redactado, ni identificadores de actividad, ni decisiones.
    """

    intencion: str
    terminos: tuple[str, ...]


def _validar_salida_fallback(salida: str) -> TerminosInterpretados | None:
    """Valida la salida del modelo contra `interpretacion_fallback_v1`.

    Devuelve `None` ante cualquier desvío —JSON inválido, claves faltantes o
    de más, tipos equivocados, término demasiado largo, o una intención que no
    está en el catálogo— sin distinguir entre ellos: el llamador sólo necesita
    saber si hay una salida usable. Una salida manipulada no puede producir
    una intención inexistente porque la pertenencia al catálogo se comprueba
    acá y no en el prompt. Ver ADR 0001.
    """

    try:
        documento = json.loads(salida)
    except (TypeError, ValueError):
        return None
    if not isinstance(documento, dict):
        return None
    if set(documento) != set(CONTRATO_FALLBACK["required"]):
        return None
    intencion = documento["intencion"]
    if not isinstance(intencion, str) or intencion not in IDS_INTENCIONES:
        return None
    terminos = documento["terminos_busqueda"]
    if not isinstance(terminos, list) or len(terminos) > MAX_TERMINOS_FALLBACK:
        return None
    for termino in terminos:
        if (
            not isinstance(termino, str)
            or not termino.strip()
            or len(termino) > MAX_LARGO_TERMINO_FALLBACK
        ):
            return None
    return TerminosInterpretados(
        intencion=intencion, terminos=tuple(str(termino) for termino in terminos)
    )


def _interpretar_con_modelo(
    texto: str, interprete: Generator | None
) -> TerminosInterpretados | None:
    """Intenta el fallback. Nunca propaga y nunca ve la planilla.

    El prompt lleva el catálogo cerrado y la prosa de la persona delimitada y
    declarada como dato no confiable —nunca como instrucción—, y nada más: el
    contenido de la fuente no entra acá, así que una fila maliciosa no puede
    alterar el comportamiento del modelo. Si el intérprete no está
    configurado, la capa sigue funcionando con menor cobertura.
    """

    if interprete is None:
        return None
    # `replace` y no `format`: la plantilla contiene un ejemplo JSON literal
    # con llaves, que `format` interpretaría como marcadores. Misma razón por
    # la que los prompts de posts usan `replace` (ver `posts.py`).
    prompt = (
        PROMPT_FALLBACK.replace(
            "{intenciones}",
            "\n".join(f"- {identificador}" for identificador in sorted(IDS_INTENCIONES)),
        )
        .replace("{max_terminos}", str(MAX_TERMINOS_FALLBACK))
        .replace("{max_largo_termino}", str(MAX_LARGO_TERMINO_FALLBACK))
        .replace("{pedido}", texto)
    )
    try:
        salida = interprete.generar(prompt)
    except Exception:
        return None
    if not isinstance(salida, str):
        return None
    return _validar_salida_fallback(salida)


@dataclass(frozen=True)
class CandidataActividad:
    """Una actividad candidata ofrecida en una repregunta.

    Conserva únicamente lo que el propio agente calculó a partir del índice
    de `fuente.enumerar()` —nunca la prosa del pedido—: `orden` es la
    posición (1-based) en la lista mostrada, la que la persona puede nombrar
    ("el segundo"); `id_actividad`, `titulo` y `fecha` son los mismos datos
    institucionales que ya usa `_resumen_desde_fuente`.
    """

    orden: int
    id_actividad: str
    titulo: str
    fecha: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.orden, int)
            or isinstance(self.orden, bool)
            or self.orden < 1
        ):
            raise ValueError("orden de candidata inválido")
        if not isinstance(self.id_actividad, str) or not self.id_actividad.strip():
            raise ValueError("candidata sin identificador de actividad")
        if not isinstance(self.titulo, str):
            raise ValueError("candidata sin título")
        if not isinstance(self.fecha, str):
            raise ValueError("candidata sin fecha")


@dataclass(frozen=True)
class InteraccionPendiente:
    """Estado entre turnos: qué preguntó el agente y qué espera de la respuesta.

    Conserva únicamente candidatas (ver `CandidataActividad`), la intención
    ya clasificada y el instante de vencimiento — nunca la prosa del pedido
    original. Es, por diseño, todo lo que el mecanismo de repregunta necesita
    para resolver el turno siguiente sin volver a interpretar texto externo.
    """

    intencion: str
    candidatas: tuple[CandidataActividad, ...]
    vencimiento: datetime

    def __post_init__(self) -> None:
        if self.intencion not in INTENCIONES_CON_DESPACHO:
            raise ValueError(
                "una interacción pendiente sólo puede existir para una "
                "intención con despacho"
            )
        if not self.candidatas:
            raise ValueError("interacción pendiente sin candidatas")
        ordenes = [candidata.orden for candidata in self.candidatas]
        if len(ordenes) != len(set(ordenes)):
            raise ValueError("candidatas de la pendiente con orden duplicado")
        if self.vencimiento.tzinfo is None:
            raise ValueError("vencimiento de la pendiente sin zona horaria")


# Vencimiento fijo de la interacción pendiente (spec #25). No se calibra como
# los umbrales de resolución difusa: es un requisito de producto (quince
# minutos), no un parámetro ajustado contra un corpus.
VENCIMIENTO_PENDIENTE = timedelta(minutes=15)


class RegistroPendientes(Protocol):
    """Puerto del estado entre turnos: una interacción pendiente por persona.

    Tres operaciones y ninguna más — en particular no hay forma de listar
    todas las pendientes ni de recorrerlas: cada una vive bajo la identidad
    de quien la originó. Deliberadamente **no** hay una implementación
    productiva de este puerto: la spec (#25) es explícita en que este
    registro no necesita durabilidad porque no hay nada irreversible que
    proteger — perder una pendiente sólo hace que la persona vuelva a
    preguntar. La única implementación que se entrega es
    `RegistroPendientesMemoria`, un fake en memoria.
    """

    def obtener(self, identificador_solicitante: str) -> InteraccionPendiente | None: ...

    def guardar(
        self, identificador_solicitante: str, pendiente: InteraccionPendiente
    ) -> None: ...

    def descartar(self, identificador_solicitante: str) -> None: ...


class RegistroPendientesMemoria:
    """Único adapter de `RegistroPendientes`: en memoria, sin durabilidad.

    Mismo patrón que `HistoriaVivaFake` en `historia_viva.py`: sirve para
    ejercitar el seam completo en pruebas, sin disco ni credenciales. Una
    instancia nueva no ve el estado de ninguna otra — no hay nada compartido
    a nivel de clase — porque no existe ningún requisito de que el estado
    sobreviva más allá del proceso que lo creó.
    """

    def __init__(self) -> None:
        self._pendientes: dict[str, InteraccionPendiente] = {}

    def obtener(self, identificador_solicitante: str) -> InteraccionPendiente | None:
        return self._pendientes.get(identificador_solicitante)

    def guardar(
        self, identificador_solicitante: str, pendiente: InteraccionPendiente
    ) -> None:
        # Una sola interacción pendiente por persona: guardar reemplaza
        # cualquier pendiente anterior de la misma identidad, nunca acumula.
        self._pendientes[identificador_solicitante] = pendiente

    def descartar(self, identificador_solicitante: str) -> None:
        self._pendientes.pop(identificador_solicitante, None)


def _obtener_pendiente_vigente(
    registro_pendientes: RegistroPendientes | None,
    identificador_solicitante: str,
    ahora: datetime,
) -> InteraccionPendiente | None:
    """Pendiente no vencida de esta persona, o `None`.

    Nunca propaga: un puerto que rompe al leer se trata como "no hay
    pendiente", igual que si nunca hubiera existido. Una pendiente vencida se
    descarta de una vez —higiene del fake, no un requisito de la spec— en
    lugar de quedar viva para que la próxima lectura la vuelva a encontrar y
    la vuelva a evaluar como vencida.
    """

    if registro_pendientes is None:
        return None
    try:
        pendiente = registro_pendientes.obtener(identificador_solicitante)
    except Exception:
        return None
    if not isinstance(pendiente, InteraccionPendiente):
        return None
    if ahora >= pendiente.vencimiento:
        _descartar_pendiente(registro_pendientes, identificador_solicitante)
        return None
    return pendiente


def _guardar_pendiente(
    registro_pendientes: RegistroPendientes | None,
    identificador_solicitante: str,
    pendiente: InteraccionPendiente,
) -> None:
    """Nunca propaga: sin puerto, o si el puerto rompe, no hay estado que
    guardar y el llamador sigue funcionando con menor cobertura entre turnos,
    igual que el resto del módulo degrada sin romper disponibilidad."""

    if registro_pendientes is None:
        return
    try:
        registro_pendientes.guardar(identificador_solicitante, pendiente)
    except Exception:
        pass


def _descartar_pendiente(
    registro_pendientes: RegistroPendientes | None, identificador_solicitante: str
) -> None:
    if registro_pendientes is None:
        return
    try:
        registro_pendientes.descartar(identificador_solicitante)
    except Exception:
        pass


@dataclass(frozen=True)
class IdentidadSolicitante:
    """Quién pide y con qué rol, tal como lo afirma el canal.

    Ver ADR 0002: el núcleo exige este dato y decide con él, pero no lo
    verifica. `identificador` es lo que el canal usó para reconocer a la
    persona (una cuenta, una casilla); nunca se persiste tal cual, sólo su
    hash.
    """

    identificador: str
    rol: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.identificador, str)
            or not isinstance(self.rol, str)
            or not self.identificador.strip()
            or not self.rol.strip()
            or "\r" in self.identificador
            or "\n" in self.identificador
            or "\r" in self.rol
            or "\n" in self.rol
        ):
            raise ValueError("identidad de solicitante inválida")


ESTADOS_RESULTADO = frozenset(
    {
        "PENDIENTE_VALIDACION",
        "PENDIENTE_DESAMBIGUACION",
        "INCOMPLETA",
        "INVALIDA",
        "FALLIDA",
        "RECHAZADA",
    }
)


@dataclass(frozen=True)
class ResultadoInterpretacion:
    """Salida del seam. Nunca lleva la prosa ni el texto completo del borrador.

    `resumen` se completa en éxito (`PENDIENTE_VALIDACION`), a partir de
    datos ya institucionales (título, fecha) leídos de la fuente, y también
    en una repregunta (`PENDIENTE_DESAMBIGUACION`), donde enumera las
    `candidatas` — jamás del cuerpo generado ni de la prosa del pedido.
    `candidatas` sólo se completa en `PENDIENTE_DESAMBIGUACION`.
    """

    estado: str
    intencion: str | None
    correlation_id: str
    log_path: Path
    borrador_path: Path | None = None
    referencia_borrador: ReferenciaBorrador | None = None
    resumen: str | None = None
    error: str | None = None
    candidatas: "tuple[CandidataActividad, ...]" = ()


def interpretar_solicitud(
    *,
    texto: str,
    solicitante: IdentidadSolicitante,
    fuente: FuenteSolicitudes,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
    registro_pendientes: RegistroPendientes | None = None,
    reloj: Callable[[], datetime] | None = None,
    interprete: Generator | None = None,
) -> ResultadoInterpretacion:
    """Entra un mensaje, sale un resultado. Nunca propaga excepciones.

    Orden de los controles: primero la forma de la identidad (tipos),
    después la autorización por rol —un pedido de alguien sin rol habilitado
    no debe ni clasificarse—, después la clasificación determinística, y
    recién ahí el despacho al pipeline que corresponda.

    `registro_pendientes` y `reloj` son opcionales: sin `registro_pendientes`
    el seam sigue respondiendo una repregunta cuando hace falta, sólo que no
    hay dónde recordarla para el turno siguiente — degrada en cobertura entre
    turnos, no en disponibilidad, igual que el resto del módulo degrada sin
    el modelo. `reloj` por defecto es `datetime.now(timezone.utc)`; las
    pruebas lo inyectan para no depender de esperas reales (#25).

    `interprete` es el modelo local del fallback (#26). También es opcional y
    por la misma razón: sin él, un pedido que el camino determinístico no
    resuelve termina en repregunta igual que antes, con menor cobertura y sin
    perder disponibilidad. Es un `Generator` distinto del que redacta los
    borradores porque hace otra cosa —extrae términos, no redacta— y porque
    así ninguna prueba determinística depende de que exista.
    """

    correlation_id = str(uuid.uuid4())
    log_path = directorio_salida / "logs" / "interpretaciones-hu013.jsonl"
    texto_seguro = texto if isinstance(texto, str) else ""
    ahora_fn = reloj if reloj is not None else (lambda: datetime.now(timezone.utc))

    if not isinstance(solicitante, IdentidadSolicitante):
        return _finalizar(
            log_path=log_path,
            correlation_id=correlation_id,
            texto=texto_seguro,
            solicitante=None,
            intencion=None,
            id_actividad=None,
            estado="INVALIDA",
            resultado="identidad_invalida",
            error="Identidad de solicitante inválida",
        )
    if not isinstance(texto, str) or not texto.strip():
        return _finalizar(
            log_path=log_path,
            correlation_id=correlation_id,
            texto=texto_seguro,
            solicitante=solicitante,
            intencion=None,
            id_actividad=None,
            estado="INVALIDA",
            resultado="mensaje_invalido",
            error="El mensaje está vacío o no es texto",
        )
    if solicitante.rol not in ROLES_HABILITADOS:
        return _finalizar(
            log_path=log_path,
            correlation_id=correlation_id,
            texto=texto_seguro,
            solicitante=solicitante,
            intencion=None,
            id_actividad=None,
            estado="RECHAZADA",
            resultado="rol_no_habilitado",
            error="El rol de quien pide no está habilitado para interactuar con el agente",
        )

    # #25: antes de clasificar, se mira si esta persona tiene una interacción
    # pendiente vigente y si este mensaje la resuelve por referencia (número
    # de orden o rasgo distintivo). El resultado de esa consulta se usa más
    # abajo en dos lugares posibles: como intención de respaldo cuando el
    # mensaje no clasifica solo (por ejemplo, "el segundo" no menciona
    # "gacetilla"), y como fuente del identificador cuando la resolución
    # directa de este mismo mensaje no alcanza una coincidencia única y
    # clara. Nunca se usa cuando la resolución directa ya tiene éxito: un
    # pedido nuevo y completo descarta la pendiente en lugar de dejarse
    # capturar por ella (ver más abajo).
    pendiente_vigente = _obtener_pendiente_vigente(
        registro_pendientes, solicitante.identificador, ahora_fn()
    )
    referencia = (
        _resolver_referencia_pendiente(texto, pendiente_vigente.candidatas)
        if pendiente_vigente is not None
        else None
    )

    intencion = _clasificar_intencion(texto)

    modelo_utilizado = False

    if intencion in INTENCIONES_CON_DESPACHO:
        intencion_efectiva = intencion
        id_actividad = _extraer_identificador_explicito(texto)
        if id_actividad is None:
            # #23: sin identificador explícito, se intenta resolver la
            # actividad por similitud contra el índice de
            # `fuente.enumerar()`. Sólo se acepta coincidencia única y clara.
            id_actividad = _resolver_actividad_por_similitud(texto, fuente)

        if id_actividad is not None:
            # Pedido nuevo y completo: se resolvió solo, así que no se deja
            # capturar por una pendiente previa y la descarta si existía.
            _descartar_pendiente(registro_pendientes, solicitante.identificador)
        elif referencia is not None:
            # El mensaje no resuelve solo, pero sí nombra —por orden o por
            # rasgo— una de las candidatas que el propio agente ofreció.
            # Consumida: la pendiente no sobrevive a su propia resolución.
            id_actividad = referencia.id_actividad
            _descartar_pendiente(registro_pendientes, solicitante.identificador)
        else:
            # #26: antes de repreguntar se intenta el modelo. Su salida
            # validada aporta términos de búsqueda que alimentan la **misma**
            # resolución determinística de #23 — el modelo nunca elige la
            # actividad, sólo reformula la consulta— y puede corregir la
            # intención, siempre dentro del catálogo cerrado.
            interpretado = _interpretar_con_modelo(texto, interprete)
            if interpretado is not None:
                if interpretado.intencion in INTENCIONES_CON_DESPACHO:
                    intencion_efectiva = interpretado.intencion
                if interpretado.terminos:
                    # Los términos se **suman** a la prosa original en lugar
                    # de reemplazarla. No es un detalle: la cobertura de
                    # `_puntuar_actividad` es monótona en la cantidad de
                    # tokens de la consulta, así que una consulta armada sólo
                    # con los términos del modelo nunca podría puntuar más
                    # alto que la prosa completa, y el fallback no agregaría
                    # cobertura alguna. Sumándolos, el modelo sólo puede
                    # aportar señal —una forma normalizada de lo que la
                    # persona escribió mal— y nunca quitar la que ya había.
                    id_actividad = _resolver_actividad_por_similitud(
                        texto + " " + " ".join(interpretado.terminos), fuente
                    )
                if id_actividad is not None:
                    modelo_utilizado = True
                    _descartar_pendiente(
                        registro_pendientes, solicitante.identificador
                    )

        if id_actividad is None and referencia is None:
            # Ni resolución directa, ni referencia a una pendiente, ni ayuda
            # del modelo: se junta un conjunto de candidatas y se repregunta
            # (#25) en lugar de aceptar una elección propia. Si ni siquiera
            # hay candidatas que ofrecer, se mantiene el desenlace de #23:
            # "no se encontró identificador", sin crear estado nuevo.
            candidatas = _generar_candidatas(texto, fuente)
            if not candidatas:
                return _finalizar(
                    log_path=log_path,
                    correlation_id=correlation_id,
                    texto=texto_seguro,
                    solicitante=solicitante,
                    intencion=intencion,
                    id_actividad=None,
                    estado="INCOMPLETA",
                    resultado="identificador_no_encontrado",
                    error=(
                        "No se reconoció ni un identificador explícito ni "
                        "una actividad única y clara en el pedido"
                    ),
                )
            _guardar_pendiente(
                registro_pendientes,
                solicitante.identificador,
                InteraccionPendiente(
                    intencion=intencion,
                    candidatas=candidatas,
                    vencimiento=ahora_fn() + VENCIMIENTO_PENDIENTE,
                ),
            )
            return _finalizar(
                log_path=log_path,
                correlation_id=correlation_id,
                texto=texto_seguro,
                solicitante=solicitante,
                intencion=intencion,
                id_actividad=None,
                estado="PENDIENTE_DESAMBIGUACION",
                resultado="repregunta_generada",
                error=None,
                resumen=_resumen_repregunta(candidatas),
                candidatas=candidatas,
            )
    elif referencia is not None:
        # El mensaje no clasifica solo a una intención con despacho (un "el
        # segundo" suelto no menciona "gacetilla" ni "post"), pero sí
        # resuelve contra una pendiente vigente: se continúa con la
        # intención que esa pendiente ya tenía clasificada, nunca con
        # `fuera_de_alcance`.
        intencion_efectiva = pendiente_vigente.intencion
        id_actividad = referencia.id_actividad
        _descartar_pendiente(registro_pendientes, solicitante.identificador)
    else:
        # Sin pendiente que resolver: mismo rechazo que sin esta historia.
        # Único punto de decisión sobre "esta intención produce un borrador
        # o se rechaza": cubre en la misma rama `fuera_de_alcance` (nunca se
        # aproxima a la más parecida), `ajustar_borrador` (reconocida, fuera
        # de alcance de esta iteración) y las intenciones sin pipeline
        # construido (`generar_newsletter`, `generar_mail`).
        # `INTENCIONES_CON_DESPACHO` es la única fuente de verdad de qué
        # intención despacha de verdad: ni el catálogo por sí solo ni una
        # intención declarada `ACTIVA` alcanzan para producir un borrador si
        # no está también acá.
        entrada_catalogo = INTENCIONES_POR_ID[intencion]
        return _finalizar(
            log_path=log_path,
            correlation_id=correlation_id,
            texto=texto_seguro,
            solicitante=solicitante,
            intencion=intencion,
            id_actividad=None,
            estado="RECHAZADA",
            resultado=str(entrada_catalogo["codigo_rechazo"]),
            error="La solicitud no corresponde a una intención con despacho disponible en este seam",
        )

    # A partir de acá, `intencion_efectiva` e `id_actividad` están resueltos
    # —directamente, o por una referencia a una interacción pendiente— y el
    # despacho es idéntico al de #22/#23. `generar_gacetilla` y
    # `generar_post` comparten la misma forma de despacho (pipeline ->
    # resumen a partir de la fuente) pero difieren en un dato de entrada: el
    # post necesita además el canal, resuelto acá mismo con código
    # determinístico (`_resolver_canal`), nunca por el modelo — y siempre a
    # partir del mensaje de este turno, nunca de uno anterior: el canal no
    # es parte de lo que conserva una interacción pendiente.
    if intencion_efectiva == "generar_post":
        canal = _resolver_canal(texto)
        if canal is None:
            return _finalizar(
                log_path=log_path,
                correlation_id=correlation_id,
                texto=texto_seguro,
                solicitante=solicitante,
                intencion=intencion_efectiva,
                id_actividad=id_actividad,
                estado="INCOMPLETA",
                resultado="canal_no_encontrado",
                error=(
                    "No se reconoció un canal (Instagram o LinkedIn) "
                    "explícito en el pedido"
                ),
            )
        resultado_proceso = procesar_post_estructurado(
            fuente=fuente,
            id_solicitud=id_actividad,
            canal=canal,
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino,
        )
        resumen = None
        if resultado_proceso.estado == "PENDIENTE_VALIDACION":
            resumen = _resumen_post_desde_fuente(fuente, id_actividad, canal)
    else:
        resultado_proceso = procesar_solicitud(
            fuente=fuente,
            id_solicitud=id_actividad,
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino,
        )
        resumen = None
        if resultado_proceso.estado == "PENDIENTE_VALIDACION":
            resumen = _resumen_desde_fuente(fuente, id_actividad)

    return _finalizar(
        log_path=log_path,
        correlation_id=correlation_id,
        texto=texto_seguro,
        solicitante=solicitante,
        intencion=intencion_efectiva,
        id_actividad=id_actividad,
        modelo_utilizado=modelo_utilizado,
        estado=resultado_proceso.estado,
        resultado=_RESULTADOS_POR_ESTADO.get(resultado_proceso.estado, "estado_no_reconocido"),
        error=resultado_proceso.error,
        borrador_path=resultado_proceso.borrador_path,
        referencia_borrador=resultado_proceso.referencia_borrador,
        resumen=resumen,
        pipeline_correlation_id=resultado_proceso.correlation_id,
    )


_RESULTADOS_POR_ESTADO = {
    "PENDIENTE_VALIDACION": "borrador_generado",
    "INCOMPLETA": "datos_incompletos",
    "INVALIDA": "solicitud_invalida",
    "FALLIDA": "pipeline_failure",
}


def _resumen_desde_fuente(fuente: FuenteSolicitudes, id_actividad: str) -> str | None:
    """Arma un resumen corto a partir de datos ya institucionales.

    Nunca lee el borrador generado: sólo vuelve a consultar la fuente
    (solo lectura) para nombrar la actividad. Si esa segunda lectura falla,
    el resumen queda en `None`: el borrador ya existe igual, esto sólo hace
    más cómoda la respuesta.
    """

    try:
        fila = fuente.obtener(id_actividad)
    except Exception:
        return None
    if not isinstance(fila, dict):
        return None
    titulo = fila.get("titulo", "")
    fecha = fila.get("fecha", "")
    if not isinstance(titulo, str) or not titulo.strip():
        return None
    if isinstance(fecha, str) and fecha.strip():
        return f"Gacetilla para '{titulo.strip()}' ({fecha.strip()})."
    return f"Gacetilla para '{titulo.strip()}'."


def _resumen_post_desde_fuente(
    fuente: FuenteSolicitudes, id_actividad: str, canal: str
) -> str | None:
    """Resumen corto del post generado, análogo a `_resumen_desde_fuente`.

    Nunca lee el borrador generado: sólo vuelve a consultar la fuente
    (solo lectura) para nombrar la actividad, e incluye el canal ya resuelto
    para que la respuesta sea inequívoca sobre qué pieza se generó.
    """

    try:
        fila = fuente.obtener(id_actividad)
    except Exception:
        return None
    if not isinstance(fila, dict):
        return None
    titulo = fila.get("titulo", "")
    if not isinstance(titulo, str) or not titulo.strip():
        return None
    return f"Post de {canal} para '{titulo.strip()}'."


def _finalizar(
    *,
    log_path: Path,
    correlation_id: str,
    texto: str,
    solicitante: IdentidadSolicitante | None,
    intencion: str | None,
    id_actividad: str | None,
    estado: str,
    resultado: str,
    error: str | None,
    borrador_path: Path | None = None,
    referencia_borrador: ReferenciaBorrador | None = None,
    resumen: str | None = None,
    pipeline_correlation_id: str | None = None,
    candidatas: "tuple[CandidataActividad, ...]" = (),
    modelo_utilizado: bool = False,
) -> ResultadoInterpretacion:
    if estado not in ESTADOS_RESULTADO:
        estado = "FALLIDA"
    registro: dict[str, object] = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "correlation_id": correlation_id,
        "pipeline_correlation_id": pipeline_correlation_id,
        "intencion": intencion,
        "id_actividad": id_actividad,
        "modelo_utilizado": modelo_utilizado,
        "solicitante_rol": solicitante.rol if solicitante is not None else None,
        "solicitante_hash": (
            _hash(solicitante.identificador) if solicitante is not None else None
        ),
        "identidad_verificada": False,
        "estado": estado,
        "resultado": resultado,
        "error": error,
        "mensaje_hash": _hash(texto),
        "output_hash": (
            _hash(referencia_borrador.referencia) if referencia_borrador is not None else None
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _registrar(log_path, registro)
    return ResultadoInterpretacion(
        estado=estado,
        intencion=intencion,
        correlation_id=correlation_id,
        log_path=log_path,
        borrador_path=borrador_path,
        referencia_borrador=referencia_borrador,
        resumen=resumen,
        error=error,
        candidatas=candidatas,
    )


def _registrar(path: Path, registro: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()
