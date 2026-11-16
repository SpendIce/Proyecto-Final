"""Audiencias institucionales y prellenado de correo, sin enviar nada.

Este modulo arma el paso que sigue a la aprobacion de un borrador de gacetilla:
una URL de composicion de Gmail con asunto, cuerpo y destinatarios en Cco. No
usa `gmail.send`, no pide el scope `gmail.compose`, no crea borradores por API
y no hace ninguna llamada de red. El envio lo hace la persona desde su cliente
de correo.

El catalogo de audiencias vive fuera del repo, en
`~/.config/agente1/audiencias-institucionales.json`. El repo trae el loader y
el esquema (`contracts/audiencias_institucionales_v1.schema.json`), no la
lista: ninguna direccion institucional se hardcodea en codigo, tests ni
documentacion versionada.

Todas las audiencias nacen `PENDIENTE_SEU`. El prellenado **no filtra** por
aprobacion: el humano ve la lista completa y decide. `audiencias_pendientes`
se devuelve solo para que la interfaz lo muestre.

El cuerpo prellenado sale de la revision aprobada (su texto y su hash), no de
un re-render: quien llama pasa el cuerpo de esa revision tal como quedo
aprobado. Si la URL supera `MAX_URL_COMPOSE`, el cuerpo no viaja en la URL y
se devuelve aparte para el portapapeles.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

from .confirmaciones import email_valido

# Version del esquema del catalogo externo. Un archivo con otra version no se
# interpreta: el loader es fail-closed y no adivina campos de una version
# desconocida.
VERSION_CATALOGO = "audiencias_institucionales_v1"

# Base de composicion de Gmail. `tf=1` abre el formulario clasico y `fs=1` lo
# muestra en pantalla completa. Los destinatarios van en `bcc` (Cco), nunca en
# `to`: un reply-all a una lista institucional no debe salir de este flujo.
BASE_COMPOSE = "https://mail.google.com/mail/?view=cm&fs=1&tf=1"

# Tope practico de la URL. Por encima de este largo el cuerpo se copia al
# portapapeles en vez de viajar en la URL; el umbral lo decide este modulo, no
# el navegador.
MAX_URL_COMPOSE = 1800

ESTADO_PENDIENTE_SEU = "PENDIENTE_SEU"
ESTADO_APROBADA = "APROBADA"

# Estados que el loader acepta. Hoy el catalogo real solo tiene audiencias
# `PENDIENTE_SEU`; `APROBADA` y `RECHAZADA` quedan declarados para que una
# decision institucional futura no obligue a tocar el loader.
ESTADOS_APROBACION = frozenset({ESTADO_PENDIENTE_SEU, "APROBADA", "RECHAZADA"})

ALCANCES_ESPERADOS = frozenset(
    {"segmentado", "masivo", "interno", "desconocido"}
)

CATEGORIAS = frozenset(
    {
        "alumnos",
        "institucional",
        "comunidad",
        "docentes",
        "graduados",
        "personal",
        "conduccion",
    }
)

ORIGENES_USO = frozenset({"DECISION_USUARIO", "SUPUESTO", "PENDIENTE_SEU"})

# Ids del catalogo: minusculas, digitos y guion bajo. El id es una clave
# estable de la interfaz y del mapeo, no una direccion.
ID_AUDIENCIA_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Mapeo propuesto entre tipo de gacetilla y audiencias. No es una aprobacion
# de la SEU: cada entrada nace `PENDIENTE_SEU` y el humano decide. La unica
# excepcion documentada es la decision del autor del PPS para `fieinforma` y
# `secretaria_academica`, que vive en el catalogo externo como `origen_uso`.
_MAPEO_AUDIENCIAS: dict[str, tuple[str, ...]] = {
    "difusion_de_actividad": ("fieinforma",),
    "cronica_de_evento": ("fieinforma",),
    "aviso_de_otra_area": ("fieinforma",),
    "convocatoria_interna": (
        "docentes_ingenieria",
        "docentes_tecnicatura",
        "personal_gestion",
    ),
    "saludo_o_efemeride": ("fieinforma",),
    "fallecimiento": ("comunidad",),
    "newsletter": ("graduados_civiles", "graduados_oim", "alumnos_posgrados"),
}

# Campos obligatorios de cada audiencia. `observacion` puede ser `null`, pero
# la clave tiene que estar: un campo ausente no se confunde con uno vacio.
_CAMPOS_AUDIENCIA = (
    "id",
    "nombre",
    "direccion",
    "categoria",
    "alcance_esperado",
    "usos_candidatos",
    "estado_aprobacion",
    "observacion",
)


class ErrorAudiencias(ValueError):
    """Error cerrado del catalogo o del prellenado.

    El mensaje es solo el codigo: nunca incluye direcciones, nombres ni el
    contenido del archivo. Los codigos son parte de la interfaz y no cambian
    sin una decision explicita.
    """

    def __init__(self, codigo: str):
        self.codigo = codigo
        super().__init__(codigo)


@dataclass(frozen=True)
class Audiencia:
    """Una audiencia del catalogo externo, ya validada."""

    id: str
    nombre: str
    direccion: str
    categoria: str
    alcance_esperado: str
    usos_candidatos: tuple[str, ...]
    estado_aprobacion: str
    observacion: str | None
    origen_uso: str = ESTADO_PENDIENTE_SEU


@dataclass(frozen=True)
class CatalogoAudiencias:
    """Catalogo externo validado, con acceso por id."""

    version: str
    fuente: Mapping[str, object]
    estado_general: str
    audiencias: tuple[Audiencia, ...]

    @property
    def por_id(self) -> dict[str, Audiencia]:
        return {audiencia.id: audiencia for audiencia in self.audiencias}


@dataclass(frozen=True)
class Prellenado:
    """Resultado listo para que la interfaz abra el cliente de correo.

    `url` es la URL de composicion. `cuerpo_portapapeles` es el cuerpo cuando
    no viaja en la URL (por largo o porque no se pidio incluirlo); si es
    `None`, el cuerpo ya esta en la URL o no habia cuerpo.
    `audiencias_pendientes` lista los ids que no estan aprobados, para que la
    interfaz lo muestre. No se usa para filtrar destinatarios.
    """

    url: str
    destinatarios: tuple[str, ...]
    cuerpo_portapapeles: str | None
    audiencias_pendientes: tuple[str, ...]


def cargar_audiencias(ruta: str | Path) -> CatalogoAudiencias:
    """Carga y valida el catalogo externo; un archivo invalido no produce catalogo.

    El loader es fail-closed: ids unicos, direcciones validas con `email_valido`,
    sin direcciones duplicadas, campos obligatorios presentes y estados dentro
    del conjunto cerrado. Los errores no repiten direcciones.
    """

    camino = Path(ruta).expanduser()
    try:
        texto = camino.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ErrorAudiencias("audiencias_no_disponible") from None
    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        raise ErrorAudiencias("audiencias_json_invalido") from None
    return _validar_catalogo(datos)


def audiencias_para(
    tipo_gacetilla: str,
    catalogo: CatalogoAudiencias,
    *,
    es_de_carrera: bool = False,
) -> tuple[str, ...]:
    """Devuelve los ids de audiencia que propone el mapeo para un tipo.

    `es_de_carrera` solo aplica a `difusion_de_actividad`: suma
    `secretaria_academica` cuando la actividad es de carrera. El mapeo no es
    una aprobacion: los ids devueltos siguen `PENDIENTE_SEU` en el catalogo.
    """

    if not isinstance(tipo_gacetilla, str) or tipo_gacetilla not in _MAPEO_AUDIENCIAS:
        raise ErrorAudiencias("audiencias_tipo_desconocido")

    ids = _MAPEO_AUDIENCIAS[tipo_gacetilla]
    if tipo_gacetilla == "difusion_de_actividad" and es_de_carrera:
        ids = (*ids, "secretaria_academica")

    por_id = catalogo.por_id
    if any(id_audiencia not in por_id for id_audiencia in ids):
        raise ErrorAudiencias("audiencias_catalogo_incompleto")
    return ids


def url_compose(
    destinatarios: Iterable[object],
    asunto: object,
    cuerpo: object | None = None,
) -> str:
    """Arma la URL de composicion de Gmail con los destinatarios en Cco.

    No envia, no crea borradores y no toca la red. Las direcciones se
    normalizan a minusculas y se colapsan los duplicados exactos. El cuerpo es
    opcional; cuando esta, viaja como `body` y usa `quote` (espacios como
    `%20`), no `quote_plus`.
    """

    direcciones = _normalizar_destinatarios(destinatarios)
    _validar_asunto(asunto)
    if cuerpo is not None and not isinstance(cuerpo, str):
        raise ErrorAudiencias("audiencias_cuerpo_invalido")

    parametros: list[tuple[str, str]] = [
        ("bcc", ",".join(direcciones)),
        ("su", asunto),
    ]
    if cuerpo is not None:
        parametros.append(("body", cuerpo))
    return f"{BASE_COMPOSE}&{urlencode(parametros, quote_via=quote)}"


def construir_prellenado(
    tipo: str,
    asunto: object,
    cuerpo: object | None,
    catalogo: CatalogoAudiencias,
    seleccion: Iterable[object] | None = None,
    *,
    es_de_carrera: bool = False,
    incluir_cuerpo: bool = True,
) -> Prellenado:
    """Construye el prellenado sin enviar ni filtrar por aprobacion.

    Si `seleccion` es `None`, los ids salen del mapeo del tipo. Si viene, el
    humano eligio: se validan contra el catalogo y se respeta el orden, sin
    mirar el estado de aprobacion. `incluir_cuerpo=False` deja el cuerpo
    directamente en `cuerpo_portapapeles`, aunque entre en la URL.

    El cuerpo debe ser el de la revision aprobada, no uno regenerado.
    """

    por_id = catalogo.por_id
    if seleccion is None:
        ids = audiencias_para(tipo, catalogo, es_de_carrera=es_de_carrera)
    else:
        ids = _normalizar_seleccion(seleccion, por_id)

    audiencias = tuple(por_id[id_audiencia] for id_audiencia in ids)
    direcciones = _normalizar_destinatarios(
        audiencia.direccion for audiencia in audiencias
    )
    pendientes = tuple(
        audiencia.id
        for audiencia in audiencias
        if audiencia.estado_aprobacion != ESTADO_APROBADA
    )

    if cuerpo is not None and not isinstance(cuerpo, str):
        raise ErrorAudiencias("audiencias_cuerpo_invalido")
    _validar_asunto(asunto)

    if incluir_cuerpo and cuerpo is not None:
        url = url_compose(direcciones, asunto, cuerpo)
        if len(url) <= MAX_URL_COMPOSE:
            return Prellenado(url, direcciones, None, pendientes)

    return Prellenado(
        url_compose(direcciones, asunto),
        direcciones,
        cuerpo,
        pendientes,
    )


def _validar_catalogo(datos: object) -> CatalogoAudiencias:
    if not isinstance(datos, dict):
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    if datos.get("version") != VERSION_CATALOGO:
        raise ErrorAudiencias("audiencias_version_invalida")

    fuente = datos.get("fuente")
    if not isinstance(fuente, dict):
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    total_grupos = fuente.get("total_grupos")
    dominio = fuente.get("dominio")
    if (
        isinstance(total_grupos, bool)
        or not isinstance(total_grupos, int)
        or total_grupos <= 0
        or not isinstance(dominio, str)
        or not dominio.strip()
    ):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    estado_general = datos.get("estado_general")
    if not isinstance(estado_general, str) or not estado_general.strip():
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    crudas = datos.get("audiencias")
    if not isinstance(crudas, list) or not crudas:
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    if total_grupos != len(crudas):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    audiencias: list[Audiencia] = []
    ids: set[str] = set()
    direcciones: set[str] = set()
    for cruda in crudas:
        audiencia = _validar_audiencia(cruda)
        if audiencia.id in ids or audiencia.direccion in direcciones:
            raise ErrorAudiencias("audiencias_catalogo_invalido")
        ids.add(audiencia.id)
        direcciones.add(audiencia.direccion)
        audiencias.append(audiencia)

    return CatalogoAudiencias(
        version=VERSION_CATALOGO,
        fuente=dict(fuente),
        estado_general=estado_general,
        audiencias=tuple(audiencias),
    )


def _validar_audiencia(cruda: object) -> Audiencia:
    if not isinstance(cruda, dict):
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    if any(campo not in cruda for campo in _CAMPOS_AUDIENCIA):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    id_audiencia = cruda["id"]
    if (
        not isinstance(id_audiencia, str)
        or ID_AUDIENCIA_RE.fullmatch(id_audiencia) is None
    ):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    nombre = cruda["nombre"]
    if not isinstance(nombre, str) or not nombre.strip():
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    direccion = cruda["direccion"]
    if not isinstance(direccion, str):
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    direccion = direccion.strip().lower()
    if not email_valido(direccion):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    categoria = cruda["categoria"]
    if not isinstance(categoria, str) or categoria not in CATEGORIAS:
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    alcance = cruda["alcance_esperado"]
    if not isinstance(alcance, str) or alcance not in ALCANCES_ESPERADOS:
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    usos = cruda["usos_candidatos"]
    if not isinstance(usos, list) or any(
        not isinstance(uso, str) or not uso.strip() for uso in usos
    ):
        raise ErrorAudiencias("audiencias_catalogo_invalido")
    if len(set(usos)) != len(usos):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    estado = cruda["estado_aprobacion"]
    if not isinstance(estado, str) or estado not in ESTADOS_APROBACION:
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    observacion = cruda["observacion"]
    if observacion is not None and not isinstance(observacion, str):
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    origen_uso = cruda.get("origen_uso", ESTADO_PENDIENTE_SEU)
    if not isinstance(origen_uso, str) or origen_uso not in ORIGENES_USO:
        raise ErrorAudiencias("audiencias_catalogo_invalido")

    return Audiencia(
        id=id_audiencia,
        nombre=nombre.strip(),
        direccion=direccion,
        categoria=categoria,
        alcance_esperado=alcance,
        usos_candidatos=tuple(usos),
        estado_aprobacion=estado,
        observacion=observacion,
        origen_uso=origen_uso,
    )


def _normalizar_destinatarios(direcciones: Iterable[object]) -> tuple[str, ...]:
    if isinstance(direcciones, (str, bytes)):
        raise ErrorAudiencias("audiencias_destinatarios_invalidos")

    normalizadas: list[str] = []
    vistas: set[str] = set()
    try:
        for direccion in direcciones:
            if not isinstance(direccion, str):
                raise ErrorAudiencias("audiencias_destinatarios_invalidos")
            normalizada = direccion.strip().lower()
            if not email_valido(normalizada):
                raise ErrorAudiencias("audiencias_destinatarios_invalidos")
            if normalizada in vistas:
                continue
            vistas.add(normalizada)
            normalizadas.append(normalizada)
    except TypeError:
        raise ErrorAudiencias("audiencias_destinatarios_invalidos") from None

    if not normalizadas:
        raise ErrorAudiencias("audiencias_destinatarios_invalidos")
    return tuple(normalizadas)


def _normalizar_seleccion(
    seleccion: Iterable[object], por_id: Mapping[str, Audiencia]
) -> tuple[str, ...]:
    if isinstance(seleccion, (str, bytes)):
        raise ErrorAudiencias("audiencias_seleccion_invalida")

    ids: list[str] = []
    vistas: set[str] = set()
    try:
        for id_audiencia in seleccion:
            if (
                not isinstance(id_audiencia, str)
                or id_audiencia not in por_id
            ):
                raise ErrorAudiencias("audiencias_seleccion_invalida")
            if id_audiencia in vistas:
                continue
            vistas.add(id_audiencia)
            ids.append(id_audiencia)
    except TypeError:
        raise ErrorAudiencias("audiencias_seleccion_invalida") from None

    if not ids:
        raise ErrorAudiencias("audiencias_seleccion_invalida")
    return tuple(ids)


def _validar_asunto(asunto: object) -> None:
    if (
        not isinstance(asunto, str)
        or "\r" in asunto
        or "\n" in asunto
    ):
        raise ErrorAudiencias("audiencias_asunto_invalido")
