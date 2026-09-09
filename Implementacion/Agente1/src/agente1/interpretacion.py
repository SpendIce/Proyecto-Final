"""HU-013 (#20, #22): de una solicitud en lenguaje natural a un borrador.

Este módulo es el seam nuevo: `interpretar_solicitud` recibe la prosa de una
persona de la SEU junto con la identidad que afirma el canal, la clasifica a
una **intención** de un catálogo cerrado y, cuando corresponde, despacha al
pipeline de gacetilla (HU-010) o al de post (HU-011) que ya existen. Nunca
propaga excepciones de la fuente, del generador ni del destino: cada camino
—éxito o falla— termina en un `ResultadoInterpretacion` y en una línea de
auditoría.

Alcance de estos incrementos: la persona nombra la intención y un
identificador de actividad reconocible en la prosa (#20); para
`generar_post` (#22) además nombra el canal (Instagram o LinkedIn) en la
misma prosa. Deliberadamente **no** entran acá:

- la búsqueda difusa de actividad por título (#23, requiere #19);
- la repregunta con candidatas y el estado entre turnos (#25);
- el canal de interacción como adapter (#24) — no confundir con el canal de
  la red social que resuelve `_resolver_canal`, que es un dato del dominio de
  `generar_post`, no el transporte de la interacción;
- el fallback con modelo ante lo ambiguo (#26).

Decisiones que no se ven en el código:

- **La prosa nunca llega a un prompt.** Lo único que sale de `texto` hacia los
  pipelines de gacetilla y de post es el identificador de actividad y, para
  `generar_post`, el nombre del canal ya resuelto — ambos ya pasan por sus
  propios contratos (`id_solicitud`, `canal`). El texto libre se usa
  únicamente para clasificar localmente, en este proceso, contra un
  vocabulario cerrado.
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
  #26), resultado, códigos y hashes.
- **La respuesta nunca lleva el texto completo del borrador.** Éxito devuelve
  un puntero (`borrador_path` / `referencia_borrador`) más un resumen corto
  armado a partir de datos ya institucionales (título, fecha), nunca el
  cuerpo generado.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from .destinos import DestinoBorradores, ReferenciaBorrador
from .fuentes import FuenteSolicitudes
from .posts import procesar_post_estructurado
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
    {"PENDIENTE_VALIDACION", "INCOMPLETA", "INVALIDA", "FALLIDA", "RECHAZADA"}
)


@dataclass(frozen=True)
class ResultadoInterpretacion:
    """Salida del seam. Nunca lleva la prosa ni el texto completo del borrador.

    `resumen` sólo se completa en éxito, a partir de datos ya
    institucionales (título, fecha) leídos de la fuente; jamás del cuerpo
    generado.
    """

    estado: str
    intencion: str | None
    correlation_id: str
    log_path: Path
    borrador_path: Path | None = None
    referencia_borrador: ReferenciaBorrador | None = None
    resumen: str | None = None
    error: str | None = None


def interpretar_solicitud(
    *,
    texto: str,
    solicitante: IdentidadSolicitante,
    fuente: FuenteSolicitudes,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
) -> ResultadoInterpretacion:
    """Entra un mensaje, sale un resultado. Nunca propaga excepciones.

    Orden de los controles: primero la forma de la identidad (tipos),
    después la autorización por rol —un pedido de alguien sin rol habilitado
    no debe ni clasificarse—, después la clasificación determinística, y
    recién ahí el despacho al pipeline que corresponda.
    """

    correlation_id = str(uuid.uuid4())
    log_path = directorio_salida / "logs" / "interpretaciones-hu013.jsonl"
    texto_seguro = texto if isinstance(texto, str) else ""

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

    intencion = _clasificar_intencion(texto)
    entrada_catalogo = INTENCIONES_POR_ID[intencion]

    # Único punto de decisión sobre "esta intención produce un borrador o se
    # rechaza": cubre en la misma rama `fuera_de_alcance` (nunca se aproxima a
    # la más parecida), `ajustar_borrador` (reconocida, fuera de alcance de
    # esta iteración) y las intenciones sin pipeline construido
    # (`generar_newsletter`, `generar_mail`). `INTENCIONES_CON_DESPACHO` es la
    # única fuente de verdad de qué intención despacha de verdad: ni el
    # catálogo por sí solo ni una intención declarada `ACTIVA` alcanzan para
    # producir un borrador si no está también acá. Agregar una intención al
    # catálogo sin sumarla a este conjunto (y sin escribir su despacho) la
    # deja rechazada con su `codigo_rechazo`, nunca aceptada a medias.
    if intencion not in INTENCIONES_CON_DESPACHO:
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

    id_actividad = _extraer_identificador_explicito(texto)
    if id_actividad is None:
        return _finalizar(
            log_path=log_path,
            correlation_id=correlation_id,
            texto=texto_seguro,
            solicitante=solicitante,
            intencion=intencion,
            id_actividad=None,
            estado="INCOMPLETA",
            resultado="identificador_no_encontrado",
            error="No se reconoció un identificador de actividad explícito en el pedido",
        )

    # `generar_gacetilla` y `generar_post` comparten la misma forma de
    # despacho (pipeline -> resumen a partir de la fuente) pero difieren en un
    # dato de entrada: el post necesita además el canal, resuelto acá mismo
    # con código determinístico (`_resolver_canal`), nunca por el modelo.
    if intencion == "generar_post":
        canal = _resolver_canal(texto)
        if canal is None:
            return _finalizar(
                log_path=log_path,
                correlation_id=correlation_id,
                texto=texto_seguro,
                solicitante=solicitante,
                intencion=intencion,
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
        intencion=intencion,
        id_actividad=id_actividad,
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
        "modelo_utilizado": False,
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
    )


def _registrar(path: Path, registro: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()
