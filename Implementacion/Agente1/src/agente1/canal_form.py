"""HU-013 (#71): adapter del canal de interacción sobre Google Form + Sheet.

Es el canal de interacción provisional del sistema de demostración (decisión
#52, ADR 0005): un Google Form de pedidos en D2, restringido al dominio de la
FIE y con «recopilar correos verificados» activado, de **campo único** —el
pedido en lenguaje natural—. El Form lo crea una persona; el agente no
necesita scope de Forms ni escribe nunca la hoja de respuestas: sólo la lee
con `GoogleSheetsLectorValores`, el mismo `values.get` de los adapters de
Sheets (allowlist fijada al construir, deadline absoluto, tope de
respuesta). La regla «escribir es siempre crear nuevo» del adapter de
Workspace no cambia: lo único que este canal produce en Google es el
borrador nuevo en Drive —como hoy, por `procesar_solicitud`— más el correo
de aviso por `gmail.send` cercado por la lista de direcciones de prueba de
#40.

Forma de la hoja de respuestas que este adapter lee, la que Google Forms
produce para un formulario de correo verificado y una sola pregunta abierta:

``Marca temporal | Dirección de correo electrónico | <pedido>``

Desde #122 la forma la declara un contrato versionado
(`contracts/canal_form_respuestas_v{1,2}.json`): la v1 es la de siempre y
sigue siendo el default; la v2 suma la primera pregunta de **tipo de
gacetilla** (lista cerrada tomada del contrato de tipos), la **actividad
condicional** —sólo los tipos que la llevan; el ítem «No es una actividad /
no figura» no registra nada— y el **área emisora** por un padrón cerrado
(`contracts/areas_emisoras_v1.json`), porque de ese padrón sale la firma del
área que imprime la pieza. Una fila estructurada que no cumple las listas
cerradas no va al núcleo —nada puede rechazarla por dónde y «la clase más
parecida» está prohibida—: el chequeo es del canal, no contiene prosa libre,
y su desenlace es acotado (mensaje fijo + registro del atendido, sin
generación). El núcleo no cambia; el texto que el armador deriva de la fila
usa el mismo vocabulario determinístico de la repregunta
(`gacetilla actividad <id>`), así que el pedido estructurado entra por el
mismo clasificador de siempre.

El adapter la lee por **posición de columna**, no por encabezado —los
enunciados de las preguntas son texto libre y no sirven de contrato—. Una
fila cuya segunda columna no es un correo válido se omite (cubre el
encabezado y cualquier resto de edición): no hay a quién responderle, igual
que una fila incompleta de `canal_planilla.py`. Una fila sin marca temporal
tampoco puede convertirse en pedido porque no hay con qué formarle un id
estable.

Identidad y rol (ADR 0005):

- **La identidad es el correo verificado de la respuesta.** Google lo
  autentica al exigir el inicio de sesión del dominio; este adapter confía
  en esa propiedad del formulario y no la vuelve a comprobar —no puede—,
  igual que el canal de planilla confiaba en la fila escrita a mano.
- **El rol sale del padrón**, un archivo fuera del repo que mantiene la SEU
  (provisionalmente el autor): `PadronRoles` mapea correo → rol. Una
  identidad que no está en el padrón recibe el rol centinela
  `ROL_NO_EN_PADRON`, que no pertenece a `ROLES_HABILITADOS`: el núcleo la
  rechaza con `rol_no_habilitado` y la registra como cualquier rechazo —el
  pedido se rechaza y se registra, como pide el criterio.
- El registro del canal (`atendidos-canal-form.jsonl`) declara
  `identidad_canal: correo_verificado_form` y `rol_origen: padron |
  fuera_de_padron` por pedido, para que la evidencia distinga «identidad
  verificada por el canal» de «rol autorizado por el padrón». La línea de
  auditoría del núcleo sigue diciendo `identidad_verificada: false`: ese
  campo significa «verificada por el agente», y el agente no verifica
  nada —la verificación es del canal, no del núcleo (ADR 0005: «el núcleo
  no cambia»).

«Pendiente» no se calcula contra la Sheet —que no se puede escribir— sino
contra el registro local de atendidos: `responder` agrega una línea por
pedido y `leer_pendientes` omite los que ya figuran. El registro **nunca
lleva prosa ni correo en claro**: id del pedido (ya un hash), hash del
correo, rol, estado, resultado del aviso y correlación. Si el proceso muere
entre la generación del borrador y el registro del atendido, la corrida
siguiente vuelve a atender el pedido: el duplicado queda visible como dos
borradores y lo reconcilia una persona —la misma política `manual_only`
del runner E2E, nada de takeover automático.

El correo de aviso (D12 de #38): todo cuerpo empieza con
`MARCADOR_BORRADOR` («BORRADOR — NO ENVIAR»), porque el destino
`GmailDestinoConfirmaciones` lo exige mientras rija la lista de prueba. El
destinatario es el correo verificado del pedido —que en D2 tiene que estar
además en la lista de direcciones permitidas; si no está, la entrega se
rechaza antes de la red y queda `aviso: rechazada` en el registro, sin
reintento ni re-despacho del pedido.

Repregunta sin prosa: cuando el núcleo devuelve `PENDIENTE_DESAMBIGUACION`,
el aviso trae **un link prellenado por candidata** —`viewform?usp=pp_url&
entry.<id>=<texto>`— cuyo valor es una plantilla determinística
`gacetilla|post actividad <id_actividad> (pedido <ref>)`: identificadores
institucionales, nunca la prosa del pedido. Al enviar el formulario con ese
valor, la nueva respuesta trae un identificador explícito que el núcleo
reconoce con `PATRON_IDENTIFICADOR_EXPLICITO` y resuelve directo —funciona
aunque la interacción pendiente de quince minutos ya haya vencido, porque
la resolución no depende del estado entre turnos. La `ref` del pedido
(hash truncado) queda en la respuesta sólo para trazabilidad humana. En un
post, si el canal no quedó resuelto, el pedido vuelve `INCOMPLETA` con
`canal_no_encontrado` y el aviso siguiente explica qué falta —la persona
puede completar el campo antes de enviar.

Propuesta de intención (#27): cuando el núcleo devuelve
`PENDIENTE_CONFIRMACION` (el pedido no se reconoció y el modelo propuso una
intención permitida con la actividad resuelta por código), el aviso no lleva
links de decisión ni de borrador: lleva el resumen institucional y **un**
enlace al mismo Form, prellenado por código con la palabra clave de la
intención permitida y el identificador de la actividad. Abrir el enlace no
ejecuta nada; revisar y enviar el formulario constituye un pedido nuevo, que
el núcleo vuelve a clasificar, resolver y autorizar por rol. Si la propuesta
es de un post, el canal de la red no se puede prellenar (nombrarlo ya haría
reconocer el pedido por el camino determinístico), así que el aviso pide
agregarlo antes de enviar. La propuesta no despacha ningún pipeline generador
y el aviso no copia prosa del usuario ni del modelo.

La prosa del pedido sigue siendo entrada no confiable (ADR 0001): este
adapter la transporta al núcleo y nunca la persiste —no figura en el
registro de atendidos, ni en los avisos, ni en los links— y nunca entra a
un prompt.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from .canal import PedidoCanal
from .confirmaciones import (
    MARCADOR_BORRADOR,
    DestinoConfirmaciones,
    EntregaRechazadaError,
    email_valido,
)
from .destinos import ReferenciaBorrador
from .gacetillas import (
    campos_obligatorios,
    campos_que_no_aplican,
    modo_de,
    requiere_actividad,
)
from .gacetillas import (
    tipos as tipos_de_gacetilla,
)
from .google_workspace import (
    ID_RE,
    MAX_WORKSPACE_TIMEOUT_S,
    AccessTokenProvider,
    GoogleSheetsLectorValores,
    TransporteHttp,
)
from .interpretacion import (
    PATRON_IDENTIFICADOR_EXPLICITO,
    CandidataActividad,
    IdentidadSolicitante,
    PropuestaIntencion,
    ResultadoInterpretacion,
)
from .registro_auditoria import escribir_registro
from .workspace_config import _A1_RE, ConfiguracionWorkspaceError

if TYPE_CHECKING:
    # `decisiones_form` ya importa este módulo (reusa `PadronRoles`): el
    # import real sería circular. El colaborador se verifica por duck typing
    # en `__init__`, así que la anotación alcanza con TYPE_CHECKING.
    from .decisiones_form import EnlacesDecisiones


# Rol centinela con el que entra al núcleo una identidad que no figura en el
# padrón. No pertenece a `ROLES_HABILITADOS` —nunca puede pertenecer, porque
# el catálogo lo define la institución y este valor lo define el código— así
# que el pedido se rechaza con `rol_no_habilitado` y queda registrado igual
# que cualquier rechazo. El registro del canal lo distingue de un rol real
# no habilitado con `rol_origen: fuera_de_padron`.
ROL_NO_EN_PADRON = "no_en_padron"

# Posiciones de columna del contrato v1 (una sola pregunta abierta). Se
# leen por posición, no por encabezado: los enunciados son texto libre y no
# sirven de contrato. El contrato v2 (#122) suma tipo, actividad y área
# emisora; sus posiciones viven en el archivo versionado y este módulo las
# carga de ahí, no acá.
COL_MARCA_TEMPORAL = 0
COL_CORREO = 1
COL_TEXTO = 2

# Versión del contrato de la hoja de respuestas (#122). La que usa el canal
# se declara por variable de entorno; sin la variable queda v1, la forma de
# siempre, porque cambiar de hoja es una decisión del operador y no un
# default silencioso. Un valor desconocido invalida la configuración.
CONTRATO_HOJA_V1 = "canal_form_respuestas_v1"
CONTRATO_HOJA_V2 = "canal_form_respuestas_v2"
CONTRATOS_HOJA = (CONTRATO_HOJA_V1, CONTRATO_HOJA_V2)

# Último ítem de la lista condicional de actividades (contrato v2): no da
# de alta ninguna actividad. Elegida con un tipo que la necesita, el
# desenlace es fail-closed: la planilla institucional manda y cargarla no es
# tarea de este agente.
ETIQUETA_SIN_ACTIVIDAD = "No es una actividad / no figura"

# Origen declarado de los hechos de la pieza en el registro de atendidos
# (#122): con el tipo declarado y la actividad resuelta por el núcleo, los
# hechos vienen de la fuente institucional de actividades; cuando el
# desenlace es acotado del canal, nada se generó y no hay hechos de pieza
# que declarar. Un insumo de agente (ADR 0008) declara el suyo en la línea
# de auditoría del pipeline.
ORIGEN_HECHOS_FUENTE_INSTITUCIONAL = "fuente_institucional"

# Configuración por entorno. Mismo patrón que `workspace_config.py` y que la
# lista de Gmail: valores fuera del repo, validados de una sola vez, rechazo
# de claves desconocidas con el prefijo propio.
FORM_PEDIDOS_PREFIX = "AGENTE1_FORM_PEDIDOS_"
PADRON_PREFIX = "AGENTE1_PADRON_"
ENV_SHEET_ID = "AGENTE1_FORM_PEDIDOS_SHEET_ID"
ENV_RANGO_A1 = "AGENTE1_FORM_PEDIDOS_RANGO_A1"
ENV_FORM_ID = "AGENTE1_FORM_PEDIDOS_FORM_ID"
ENV_ENTRY_ID = "AGENTE1_FORM_PEDIDOS_ENTRY_ID"
ENV_TIMEOUT_S = "AGENTE1_FORM_PEDIDOS_TIMEOUT_S"
ENV_HOJA_CONTRATO = "AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO"
PADRON_ROLES_ENV = "AGENTE1_PADRON_ROLES_PATH"
_FORM_REQUIRED_KEYS = frozenset(
    {ENV_SHEET_ID, ENV_RANGO_A1, ENV_FORM_ID, ENV_ENTRY_ID, ENV_TIMEOUT_S}
)
_FORM_ALLOWED_KEYS = (
    _FORM_REQUIRED_KEYS | {PADRON_ROLES_ENV, ENV_HOJA_CONTRATO}
)

# Estado local entre corridas: un JSONL por pedido atendido, sin prosa ni
# correo en claro. Es la única marca de «respondido» que existe, porque la
# Sheet de respuestas no se puede escribir.
ATENDIDOS_NOMBRE = "atendidos-canal-form.jsonl"
REGISTRO_ATENDIDOS_VERSION = "canal_form_atendidos_v1"

ENTRY_ID_RE = re.compile(r"entry\.[0-9]{1,12}\Z")
_ROL_PADRON_RE = re.compile(r"[A-Za-z0-9_]{1,64}\Z")
_HASH_ID_RE = re.compile(r"[0-9a-f]{64}\Z")
MAX_FILAS_PADRON = 500
# La referencia del pedido que viaja en links y asuntos es el hash truncado:
# alcanza para correlacionar a ojo sin arrastrar 64 caracteres a un campo
# que una persona tiene que leer.
REF_PEDIDO_CORTA = 12

# Palabra que la plantilla prellenada usa para que el núcleo reclasifique la
# intención por el camino determinístico. Son las mismas palabras clave que
# ya reconoce `_clasificar_intencion`, no un vocabulario nuevo del canal.
_KEYWORD_POR_INTENCION = {
    "generar_gacetilla": "gacetilla",
    "generar_post": "post",
    "emitir_certificados": "certificados",
    "generar_plantilla_actividad": "plantilla",
}

# Etiqueta fija por decisión del catálogo #72, para el aviso del pedido de
# plantilla. El link lo mintea `EnlacesDecisiones`; acá sólo se nombra qué
# aprobación registra cada uno.
_ETIQUETA_DECISION = {
    "apruebo_semantica": "Apruebo la revisión semántica de la plantilla",
    "apruebo_utilitaria": "Apruebo la plantilla (decisión utilitaria)",
    "apruebo_lote": "Habilito el lote de envíos de la actividad",
}

_FRASES_ASUNTO = {
    "PENDIENTE_VALIDACION": "tu borrador está listo",
    "PENDIENTE_DESAMBIGUACION": "elegí la actividad",
    "PENDIENTE_CONFIRMACION": "confirmá el pedido",
    "PENDIENTE_APROBACION": "espera la aprobación del lote",
    "EMITIDA": "certificados emitidos",
    "EMITIDA_PARCIAL": "certificados emitidos con entregas fallidas",
    "INCOMPLETA": "faltan datos",
    "INVALIDA": "pedido inválido",
    "FALLIDA": "el pedido falló",
    "RECHAZADA": "pedido rechazado",
}
# El cuerpo conjuga distinto que el asunto ("Tu pedido ... fue rechazado" vs.
# "Pedido: rechazado"), así que tiene su propio mapa de frases.
_FRASES_CUERPO = {
    "PENDIENTE_APROBACION": (
        "quedó pendiente de la aprobación del lote de cierre"
    ),
    "EMITIDA": "emitió los certificados del lote de cierre",
    "EMITIDA_PARCIAL": "emitió certificados con entregas fallidas",
    "INCOMPLETA": "no se pudo completar: faltan datos",
    "INVALIDA": "no es un pedido válido",
    "FALLIDA": "falló por un error",
    "RECHAZADA": "fue rechazado",
}
# Tipos de `ReferenciaBorrador` que apuntan a un documento de Google: sólo
# para ellos existe un link abrible que poner en el aviso.
_TIPOS_REFERENCIA_DOCS = frozenset({"google_docs", "google_drive_template"})


class CanalFormError(RuntimeError):
    """Falla del adapter del canal de pedidos, con código auditable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@lru_cache(maxsize=4)
def _contrato_hoja(version: str) -> dict[str, object]:
    """El contrato versionado de la hoja de respuestas, leído del repo.

    Sólo admite las versiones declaradas: un nombre que no está no se lee
    del disco ni se confunde con una versión nueva. Las posiciones de
    columna validadas acá son la única fuente que el adapter consulta: el
    archivo y el código no pueden divergir sin que el canal empiece a leer
    columnas corridas.
    """

    if version not in CONTRATOS_HOJA:
        raise CanalFormError("canal_form_hoja_contrato_desconocido")
    try:
        texto = (
            files("agente1")
            .joinpath("contracts", f"{version}.json")
            .read_text(encoding="utf-8")
        )
        contrato = json.loads(texto)
        columnas = contrato["columnas"]
        if not isinstance(columnas, dict) or any(
            not isinstance(pos, int) or pos < 0 for pos in columnas.values()
        ):
            raise ValueError("posiciones de columna no enteras")
        if "marca_temporal" not in columnas or "correo" not in columnas:
            raise ValueError("columnas obligatorias ausentes")
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        raise CanalFormError("canal_form_hoja_contrato_invalido") from None
    return columnas


@lru_cache(maxsize=1)
def _padron_areas() -> dict[str, dict[str, str]]:
    """El padrón cerrado de áreas emisoras, leído del contrato versionado.

    Igual doctrina que el padrón de roles (ADR 0005): lista cerrada, sólo
    lectura, nadie entra por haberla escrito mal. La firma institucional
    que la pieza imprime en su pie sale de acá: el id viaja declarado en la
    solicitud y el nombre que se imprime es el del padrón, nunca el texto
    libre de la hoja de respuestas.
    """

    try:
        texto = (
            files("agente1")
            .joinpath("contracts", "areas_emisoras_v1.json")
            .read_text(encoding="utf-8")
        )
        contrato = json.loads(texto)
        areas = contrato["areas"]
        if not isinstance(areas, list) or not areas:
            raise ValueError("areas ausentes")
        areas_resueltas: dict[str, dict[str, str]] = {}
        for area in areas:
            id_area = str(area["id"]).strip()
            nombre = str(area["nombre"]).strip()
            if (
                not id_area
                or not nombre
                or "\n" in id_area
                or id_area in areas_resueltas
            ):
                raise ValueError("area inválida o repetida")
            areas_resueltas[id_area] = {"nombre": nombre}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise CanalFormError("canal_form_areas_padron_invalido") from None
    return areas_resueltas


def firma_de_area(id_area: str) -> str | None:
    """Firma institucional de área de la pieza, o `None` fuera del padrón.

    Es el wirado del mapeo área → firma (#122) sobre el único hueco que las
    formas declaradas dejan al dato: el placeholder `{area_emisora}` de su
    pie. El bloque `firmante` de la forma es el membrete institucional y
    queda fijo por tipo; la firma del área vive en este padrón, para que un
    aviso de otra área nunca vuelva a firmarse con el área equivocada.
    """

    if not isinstance(id_area, str):
        return None
    area = _padron_areas().get(id_area.strip())
    return area["nombre"] if area is not None else None


def _normalizar_etiqueta(valor: str) -> str:
    """Colapsa espacios y minúsculas para comparar etiquetas fijas."""

    return " ".join(valor.split()).casefold()


def es_opcion_sin_actividad(valor: str) -> bool:
    """¿La celda de actividad es el ítem «no es una actividad / no figura»?"""

    return _normalizar_etiqueta(valor) == _normalizar_etiqueta(
        ETIQUETA_SIN_ACTIVIDAD
    )


def es_id_actividad(valor: str) -> bool:
    """¿La celda de actividad es un identificador explícito de la planilla?

    Usa el mismo patrón que el núcleo reconoce en la prosa: el desplegable
    se carga con identificadores de la planilla y una celda con otra forma
    no puede resolverse determinísticamente. Dejarla pasar saldría a los
    tajes: el núcleo podría resolverla por similitud contra una actividad
    única y clara que no es la que la persona quiso decir.
    """

    if not isinstance(valor, str):
        return False
    return PATRON_IDENTIFICADOR_EXPLICITO.fullmatch(valor.strip()) is not None


class PadronRoles:
    """Correo verificado → rol autorizado (ADR 0005), cargado fuera del repo.

    El padrón lo mantiene la SEU —provisionalmente el autor del PPS— y el
    agente sólo lo lee: no hay operación de escritura. Las direcciones se
    normalizan a minúsculas sin espacios, igual que la lista de Gmail, así
    una variante de mayúsculas no esquiva ni falsifica la entrada. En las
    pruebas se inyecta el mapeo directo; en producción se carga por
    `cargar_padron_roles_csv` o `desde_entorno`.
    """

    def __init__(self, correos_roles: Mapping[str, str]) -> None:
        if not isinstance(correos_roles, Mapping):
            raise ConfiguracionWorkspaceError("padron_roles_invalid")
        normalizados: dict[str, str] = {}
        try:
            items = list(correos_roles.items())
        except Exception:
            raise ConfiguracionWorkspaceError("padron_roles_invalid") from None
        for correo, rol in items:
            correo_n = correo.strip().lower() if isinstance(correo, str) else ""
            rol_n = rol.strip() if isinstance(rol, str) else ""
            if not email_valido(correo_n) or _ROL_PADRON_RE.fullmatch(rol_n) is None:
                raise ConfiguracionWorkspaceError("padron_roles_invalid")
            normalizados[correo_n] = rol_n
        if not normalizados or len(normalizados) > MAX_FILAS_PADRON:
            raise ConfiguracionWorkspaceError("padron_roles_invalid")
        self._roles = normalizados

    def rol_para(self, correo: str) -> str | None:
        """Rol autorizado de este correo, o `None` si no está en el padrón."""

        if not isinstance(correo, str):
            return None
        return self._roles.get(correo.strip().lower())

    @classmethod
    def desde_entorno(
        cls, environ: Mapping[str, str] | None = None
    ) -> "PadronRoles":
        """Carga el padrón desde `AGENTE1_PADRON_ROLES_PATH` (fuera del repo)."""

        env = os.environ if environ is None else environ
        crudo = env.get(PADRON_ROLES_ENV)
        if crudo is None or not crudo.strip():
            raise ConfiguracionWorkspaceError("padron_roles_missing")
        return cargar_padron_roles_csv(Path(crudo.strip()).expanduser())

    def __repr__(self) -> str:
        # Las direcciones no se imprimen: un repr con correos terminaría en
        # logs. Mismo criterio que `GmailDestinoConfirmaciones`.
        return f"PadronRoles({len(self._roles)} correos)"


def cargar_padron_roles_csv(path: Path) -> PadronRoles:
    """Lee el padrón desde un CSV `correo,rol`. Falla por código, sin datos.

    La ruta vive fuera del repo y no se valida como identificador remoto:
    es un archivo local de configuración, como el env file. Un archivo
    ausente o ilegible, una fila inválida o un correo duplicado impiden que
    el padrón exista — un padrón a medias nunca habilita a medias.
    """

    try:
        with path.open(encoding="utf-8", newline="") as archivo:
            reader = csv.DictReader(archivo)
            encabezados = reader.fieldnames or []
            if (
                set(encabezados) != {"correo", "rol"}
                or len(encabezados) != len(set(encabezados))
            ):
                raise ConfiguracionWorkspaceError("padron_roles_invalid")
            filas: dict[str, str] = {}
            for fila in reader:
                if None in fila:
                    # Más columnas de las declaradas: fila desalineada.
                    raise ConfiguracionWorkspaceError("padron_roles_invalid")
                correo = (fila.get("correo") or "").strip().lower()
                rol = (fila.get("rol") or "").strip()
                if correo in filas:
                    raise ConfiguracionWorkspaceError("padron_roles_invalid")
                filas[correo] = rol
            if len(filas) > MAX_FILAS_PADRON:
                raise ConfiguracionWorkspaceError("padron_roles_invalid")
    except ConfiguracionWorkspaceError:
        raise
    except OSError:
        # El archivo no existe o no se puede leer: mismo código que la
        # variable ausente, porque para el agente es el mismo bloqueante.
        raise ConfiguracionWorkspaceError("padron_roles_missing") from None
    except (UnicodeDecodeError, csv.Error):
        raise ConfiguracionWorkspaceError("padron_roles_invalid") from None
    return PadronRoles(filas)


class LectorValoresCsv:
    """Lector de valores sobre un CSV local; mismo contrato que el de Sheets.

    Sirve para corridas offline del canal —un ensayo sin red con un CSV que
    imita la hoja de respuestas, ver `scripts/atender_canal_form.py`— y para
    pruebas del parseo de filas sin transporte. Devuelve filas como listas,
    incluida la de encabezados, que el adapter omite por no ser un correo
    válido — igual que la hoja real.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def leer_valores(self) -> list[object]:
        with self._path.open(encoding="utf-8", newline="") as archivo:
            return [list(fila) for fila in csv.reader(archivo)]


@dataclass(frozen=True, repr=False)
class ConfiguracionCanalForm:
    """Configuración del canal de pedidos por Form, validada de una sola vez.

    `padron_path` es una ruta local fuera del repo: se conserva como `Path`
    porque el padrón lo lee `PadronRoles.desde_entorno` por separado —la
    config declara dónde está, no lo lee. `contrato_hoja` declara qué forma
    de hoja de respuestas hay en producción (#122): v1 por defecto, la forma
    de una sola pregunta abierta.
    """

    sheet_id: str
    rango_a1: str
    form_id: str
    entry_id: str
    timeout_s: float
    padron_path: Path
    contrato_hoja: str = CONTRATO_HOJA_V1

    def resumen_seguro(self) -> dict[str, object]:
        """Vista publicable: hashes de los identificadores, nunca los valores."""

        return {
            "sheet_ref_hash": _hash(self.sheet_id),
            "range_hash": _hash(self.rango_a1),
            "form_ref_hash": _hash(self.form_id),
            "entry_id": self.entry_id,
            "padron_path_hash": _hash(str(self.padron_path)),
            "timeout_s": self.timeout_s,
            "contrato_hoja": self.contrato_hoja,
        }


def cargar_configuracion_canal_form(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionCanalForm:
    """Lee y valida `AGENTE1_FORM_PEDIDOS_*` + `AGENTE1_PADRON_ROLES_PATH`.

    Mismo contrato que `cargar_configuracion_workspace`: claves desconocidas
    con los prefijos propios se rechazan, un entorno incompleto falla, los
    errores son códigos sin datos adentro y el resultado expone sólo hashes
    por `resumen_seguro()`.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave
        for clave in env
        if (
            clave.startswith(FORM_PEDIDOS_PREFIX)
            or clave.startswith(PADRON_PREFIX)
        )
        and clave not in _FORM_ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionWorkspaceError("canal_form_config_unknown_key")
    if any(clave not in env for clave in _FORM_REQUIRED_KEYS | {PADRON_ROLES_ENV}):
        raise ConfiguracionWorkspaceError("canal_form_config_incomplete")

    try:
        sheet_id = env[ENV_SHEET_ID]
        rango_a1 = env[ENV_RANGO_A1]
        form_id = env[ENV_FORM_ID]
        entry_id = env[ENV_ENTRY_ID]
        timeout_s = float(env[ENV_TIMEOUT_S])
        padron_path = Path(env[PADRON_ROLES_ENV].strip()).expanduser()
        contrato_hoja = env.get(ENV_HOJA_CONTRATO, "").strip() or CONTRATO_HOJA_V1
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ConfiguracionWorkspaceError("canal_form_config_invalid") from None

    padron_crudo = env[PADRON_ROLES_ENV].strip()
    if (
        ID_RE.fullmatch(sheet_id) is None
        or _A1_RE.fullmatch(rango_a1) is None
        or ID_RE.fullmatch(form_id) is None
        or ENTRY_ID_RE.fullmatch(entry_id) is None
        or not math.isfinite(timeout_s)
        or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        or not padron_crudo
        or any(ord(caracter) < 32 for caracter in padron_crudo)
        or contrato_hoja not in CONTRATOS_HOJA
    ):
        raise ConfiguracionWorkspaceError("canal_form_config_invalid")

    return ConfiguracionCanalForm(
        sheet_id=sheet_id,
        rango_a1=rango_a1,
        form_id=form_id,
        entry_id=entry_id,
        timeout_s=timeout_s,
        padron_path=padron_path,
        contrato_hoja=contrato_hoja,
    )


def crear_lector_respuestas(
    *,
    config: ConfiguracionCanalForm,
    token_provider: AccessTokenProvider,
    transport: TransporteHttp | None = None,
) -> GoogleSheetsLectorValores:
    """Lector de la Sheet de respuestas del Form, con la allowlist de la config."""

    if not isinstance(config, ConfiguracionCanalForm):
        raise ValueError("configuración del canal de pedidos inválida")
    return GoogleSheetsLectorValores(
        spreadsheet_id=config.sheet_id,
        rango_a1=config.rango_a1,
        token_provider=token_provider,
        transport=transport,
        timeout_s=config.timeout_s,
    )


@dataclass(frozen=True, repr=False)
class BloqueoCanalV2:
    """Desenlace acotado de una fila estructurada que el canal rechaza.

    Las columnas estructuradas del contrato v2 se validan contra listas
    cerradas versionadas (tipos de gacetilla, padrón de áreas) y contra la
    condición de la actividad. Una fila que no cumple no va al núcleo: el
    núcleo no puede rechazar un tipo no declarado ni deshabilitar por dónde,
    y dejar pasar la fila para que otra cosa la interprete sería aidosla a
    la clase más parecida — justo lo que la lista cerrada prohíbe (#122,
    ADR 0012). El desenlace es fail-closed: aviso con mensaje fijo, registro
    del atendido sin generación; nunca da de alta una actividad.
    """

    id_pedido: str
    correo: str
    rol: str
    codigo: str
    mensaje: str
    tipo: str | None = None

    def __repr__(self) -> str:
        # Igual que el padrón: nada legible del pedido ni del correo en un
        # repr que puede terminar en logs.
        return f"BloqueoCanalV2({self.codigo})"


# Mensajes fijos por código de bloqueo. Es lo único que viaja al correo:
# texto institucional, nunca datos del pedido y nunca la prosa del campo
# libre. El tono ya es el de los avisos del canal: qué pasó, qué no se
# generó, qué tiene que hacer la persona con un canal institucional.
MENSAJES_BLOQUEO = {
    "tipo_no_declarado": (
        "El campo de tipo no corresponde a la lista cerrada de tipos de "
        "gacetilla, así que nada se generó. Los tipos válidos son los del "
        "desplegable del formulario, exactamente los del catálogo del repo."
    ),
    "tipo_sin_despacho": (
        "El tipo declarado todavía no despacha en este canal, así que nada "
        "se generó. Los datos que ese tipo exige los carga quien pide y el "
        "canal todavía no tiene las columnas para pedirlos; el circuito de "
        "pedidos sigue abierto por Form para lo que el núcleo reconoce."
    ),
    "actividad_requerida": (
        "El tipo declarado lleva actividad y el campo quedó vacío, así que "
        "nada se generó. La actividad tiene que estar cargada en la planilla "
        "institucional: cargarla no es tarea de este agente."
    ),
    "actividad_no_figura": (
        "«No es una actividad / no figura» no da de alta ninguna actividad "
        "y nada se generó. Para una difusión, la actividad tiene que estar "
        "cargada en la planilla institucional: cargarla no es tarea de este "
        "agente."
    ),
    "actividad_no_aplica": (
        "El tipo declarado no lleva actividad y el campo quedó elegido, así "
        "que nada se generó. Si el pedido es sobre una actividad, elegí "
        "difusión de actividad como tipo."
    ),
    "actividad_no_identificada": (
        "La actividad elegida no tiene la forma de un identificador de la "
        "planilla institucional, así que nada se generó y no se buscó entre "
        "otras actividades: la planilla manda y cargarla no es tarea de este "
        "agente."
    ),
    "area_requerida": (
        "El tipo declarado exige área emisora y el campo quedó vacío, así "
        "que nada se generó. Las áreas válidas son las del desplegable."
    ),
    "area_fuera_de_padron": (
        "El área emisora declarada no está en el padrón cerrado del repo, "
        "así que nada se generó. Las áreas válidas son las del desplegable."
    ),
    "area_no_aplica": (
        "El tipo declarado lleva el pie institucional de su forma declarada "
        "y no declara área emisora, así que nada se generó. Si el hecho lo "
        "emite otra área, el tipo correspondiente es aviso de otra área."
    ),
}


class CanalFormPedidos:
    """Adapter `CanalInteraccion`: Sheet de respuestas → núcleo → aviso Gmail.

    `lector` es cualquier objeto con `leer_valores()` —en producción un
    `GoogleSheetsLectorValores` sobre la Sheet del Form, en offline un
    `LectorValoresCsv`—. `avisos` implementa el puerto
    `DestinoConfirmaciones` (`GmailDestinoConfirmaciones` en producción, el
    fake en pruebas): el adapter no construye el correo, lo delega.
    `directorio_estado` aloja `atendidos-canal-form.jsonl`, la única marca
    de «respondido» que existe — la Sheet es de sólo lectura.

    `decisiones` es el puente opcional al segundo Form («Registro de
    decisiones», #72): cuando está, el aviso de borrador listo declara el
    pedido como objeto pendiente de decisión y adjunta los links prellenados
    «lo publiqué / lo descarté». Sin `decisiones` el correo va igual, sólo
    que sin links de decisión.
    """

    def __init__(
        self,
        *,
        lector: object,
        padron: PadronRoles,
        avisos: DestinoConfirmaciones,
        directorio_estado: Path,
        form_id: str,
        entry_id: str,
        decisiones: EnlacesDecisiones | None = None,
        contrato_hoja: str = CONTRATO_HOJA_V1,
    ) -> None:
        if (
            not callable(getattr(lector, "leer_valores", None))
            or not isinstance(padron, PadronRoles)
            or not callable(getattr(avisos, "entregar", None))
            or not isinstance(directorio_estado, Path)
            or not isinstance(form_id, str)
            or ID_RE.fullmatch(form_id) is None
            or not isinstance(entry_id, str)
            or ENTRY_ID_RE.fullmatch(entry_id) is None
            or contrato_hoja not in CONTRATOS_HOJA
            or (
                decisiones is not None
                and not all(
                    callable(getattr(decisiones, metodo, None))
                    for metodo in ("enlaces_publicacion", "declarar_y_enlaces")
                )
            )
        ):
            raise ValueError("configuración del canal de pedidos inválida")
        self._lector = lector
        self._padron = padron
        self._avisos = avisos
        self._directorio_estado = directorio_estado
        self._atendidos_path = directorio_estado / ATENDIDOS_NOMBRE
        self._form_id = form_id
        self._entry_id = entry_id
        self._decisiones = decisiones
        self._contrato_hoja = contrato_hoja
        # Las posiciones son las del contrato cargado: en v1, marca, correo
        # y pedido; en v2, tipo, actividad y área emisora entre el correo y
        # el pedido. Se consultan por nombre y nadie las repite a mano acá.
        self._columnas_hoja: dict[str, int] = _contrato_hoja(contrato_hoja)

    def leer_pendientes(self) -> tuple[PedidoCanal, ...]:
        """Pedidos nuevos de la hoja, en orden de llegada.

        La lectura de la Sheet sí puede propagar `FuenteSolicitudesError`:
        sin poder leer no hay forma honesta de decir cuántos pendientes hay,
        y correr el bucle con la lista vacía simularía «sin pedidos» — el
        mismo criterio con el que una fuente rota falla la corrida en lugar
        de devolver una actividad vacía. El registro de atendidos ilegible
        falla igual (`canal_form_registry_invalid`): ante la duda sobre qué
        ya se atendió, se frena antes que arriesgar un borrador duplicado.

        #122: las filas estructuradas del contrato v2 que no cumplen la
        lista cerrada de tipos, la condición de la actividad o el padrón de
        áreas no van al núcleo — nada lo puede rechazar por dónde, y la
        clase más parecida está prohibida —. Acá mismo reciben su desenlace
        acotado (aviso con mensaje fijo y registro del atendido): la fila
        queda marcada como atendida para que no vuelva, y el pedido que sale
        hacia el bucle es sólo el que el núcleo puede procesar. Es lectura y
        respuesta en la misma pasada; el bucle no se entera de los bloqeos,
        que no son resultados de interpretación sino del contrato de la hoja.
        """

        values = self._lector.leer_valores()
        atendidos = self._ids_atendidos()
        pendientes: list[PedidoCanal] = []
        vistos: set[str] = set()
        for fila in values:
            resultado = self._procesar_fila(
                fila, atendidos=atendidos, vistos=vistos, pendientes=pendientes
            )
            # `_procesar_fila` marca tanto los bloqueos atendidos como los
            # pedidos listos en el mismo set, para que una hoja con dos filas
            # iguales no despache ni avise dos veces.
            if resultado is not None:
                vistos.add(resultado)
        return tuple(pendientes)

    def _procesar_fila(
        self,
        fila: object,
        *,
        atendidos: set[str],
        vistos: set[str],
        pendientes: list[PedidoCanal],
    ) -> str | None:
        """Una fila hacia su desenlace. Devuelve el id de pedido tratado.

        En v1 reproduce la lectura de siempre: fila reconocible → pedido.
        En v2 valida las columnas estructuradas; un bloqueo se resuelve acá
        mismo (aviso y registro) y devuelve su id para la deduplicación.
        """

        if self._contrato_hoja == CONTRATO_HOJA_V1:
            pedido = self._pedido_desde_fila_v1(fila)
            if pedido is None:
                return None
            id_pedido = pedido.id_pedido
        else:
            pedido, bloqueo = self._pedido_estructurado(fila)
            if bloqueo is not None:
                id_pedido = bloqueo.id_pedido
                if id_pedido in atendidos or id_pedido in vistos:
                    return id_pedido
                self._resolver_bloqueo(bloqueo)
                atendidos.add(id_pedido)
                return id_pedido
            if pedido is None:
                return None
            id_pedido = pedido.id_pedido
        if id_pedido in atendidos or id_pedido in vistos:
            return id_pedido
        atendidos.add(id_pedido)
        pendientes.append(pedido)
        return id_pedido

    def responder(self, pedido: PedidoCanal, resultado: ResultadoInterpretacion) -> None:
        """Avisa por correo y registra el atendido. Nunca re-despacha.

        El correo es la única vía de respuesta que tiene la persona —la hoja
        no se escribe— así que se intenta para todo resultado, éxito o
        rechazo. Si la entrega falla (rechazo de la lista de prueba, caída
        del medio) se registra el desenlace igual: el pedido ya se procesó
        y repetirlo generaría un segundo borrador, que en comunicación
        institucional es peor que un aviso perdido.
        """

        # Con el puente de decisiones conectado, el correo de borrador listo
        # declara los objetos que quedaron abiertos a decisión y adjunta los
        # links del Form de decisiones (#72). La declaración queda aunque el
        # aviso no llegue: el objeto sí quedó abierto a decisión, y ese
        # estado es el que la auditoría de decisiones va a exigir después.
        # Un pipeline que nombra sus objetos en `objetos_decision` —hoy la
        # plantilla y el lote de `generar_plantilla_actividad`, #73— declara
        # ésos; los demás siguen declarando el pedido como `publicacion`.
        decisiones_objeto: str | None = None
        decisiones_objetos: tuple[str, ...] = ()
        enlaces_decision: Mapping[str, str] | None = None
        enlaces_objetos: tuple[tuple[str, str, dict[str, str]], ...] = ()
        if (
            self._decisiones is not None
            and resultado.estado == "PENDIENTE_VALIDACION"
        ):
            if resultado.objetos_decision:
                enlaces_objetos = tuple(
                    self._declarar_objeto_decision(objeto)
                    for objeto in resultado.objetos_decision
                )
                decisiones_objetos = tuple(
                    f"{objeto['tipo']}:{objeto['objeto_id']}"
                    for objeto in resultado.objetos_decision
                )
            else:
                enlaces_decision = self._decisiones.enlaces_publicacion(
                    objeto_id=pedido.id_pedido,
                    pieza=_KEYWORD_POR_INTENCION.get(resultado.intencion or ""),
                    correlation_id=resultado.correlation_id,
                )
                decisiones_objeto = pedido.id_pedido
        # #122: una fila estructurada del contrato v2 declara en su registro
        # qué campos estructurados trajo el canal y de dónde vienen los
        # hechos de la pieza. Los valores son vocabulario cerrado (tipo,
        # identificador de la planilla), nunca prosa. En v1 no hay nada que
        # declarar y el registro queda como siempre.
        estructura = dict(pedido.estructura) if pedido.estructura else {}
        declarado = {k: v for k, v in estructura.items() if v} or None
        asunto = _asunto_aviso(pedido=pedido, resultado=resultado)
        cuerpo = self._cuerpo_aviso(
            pedido=pedido,
            resultado=resultado,
            enlaces_decision=enlaces_decision,
            enlaces_objetos=enlaces_objetos,
        )
        aviso, aviso_codigo = self._enviar_aviso(pedido, resultado, asunto, cuerpo)
        self._registrar_atendido(
            pedido,
            resultado,
            aviso=aviso,
            aviso_codigo=aviso_codigo,
            decisiones_objeto=decisiones_objeto,
            decisiones_objetos=decisiones_objetos,
            contrato_hoja=(
                self._contrato_hoja if self._contrato_hoja != CONTRATO_HOJA_V1 else None
            ),
            declarado=declarado,
            origen_hechos=(
                ORIGEN_HECHOS_FUENTE_INSTITUCIONAL if declarado else None
            ),
        )

    def _declarar_objeto_decision(
        self, objeto: Mapping[str, object]
    ) -> tuple[str, str, dict[str, str]]:
        """Declara un objeto del núcleo y mintea sus links (#72).

        El núcleo ya produjo `tipo` y `objeto_id` conformes al catálogo; el
        `declarar_y_enlaces` valida de nuevo — un objeto que no pase el
        catálogo levanta `DecisionesFormError` y corta la respuesta, porque
        un aviso con links rotos es peor que un aviso que no salió.
        """

        tipo = str(objeto["tipo"])
        objeto_id = str(objeto["objeto_id"])
        detalle = objeto.get("detalle")
        enlaces = self._decisiones.declarar_y_enlaces(
            tipo=tipo,
            objeto_id=objeto_id,
            detalle=(
                {str(k): str(v) for k, v in detalle.items()}
                if isinstance(detalle, Mapping)
                else None
            ),
        )
        return tipo, objeto_id, enlaces

    # --- Lectura de la hoja -------------------------------------------------

    def _pedido_desde_fila_v1(self, fila: object) -> PedidoCanal | None:
        """Una fila de la hoja v1 como pedido, o `None` si no es reconocible.

        Reconocible exige marca temporal y correo válido: la marca es parte
        del `id_pedido` —sin ella dos respuestas del mismo correo serían el
        mismo pedido— y el correo es la identidad y el destino del aviso.
        El texto puede venir vacío: eso ya es un pedido y lo rechaza el
        núcleo (`mensaje_invalido`), no el adapter.
        """

        if not isinstance(fila, list):
            return None
        marca = _celda(fila, COL_MARCA_TEMPORAL)
        correo = _celda(fila, COL_CORREO).lower()
        texto = _celda(fila, COL_TEXTO)
        if not marca or not email_valido(correo):
            return None
        rol = self._padron.rol_para(correo) or ROL_NO_EN_PADRON
        return PedidoCanal(
            id_pedido=_id_pedido(marca, correo, texto),
            solicitante=IdentidadSolicitante(identificador=correo, rol=rol),
            texto=texto,
        )

    def _pedido_estructurado(
        self, fila: object
    ) -> tuple[PedidoCanal | None, BloqueoCanalV2 | None]:
        """Una fila del contrato v2 hacia pedido despachable o bloqueo.

        El tipo es la primera pregunta y manda: entra validado contra la
        lista cerrada de `tipos_gacetilla_v1` (leída del contrato, nunca
        copiada). La actividad es condicional: sólo la llevan los tipos que
        el contrato declara con actividad, y el ítem «no es una actividad /
        no figura» no la registra nunca — la planilla institucional es la
        única fuente. El área emisora sale del padrón cerrado del repo, y la
        firma de la pieza es la del padrón, no el texto de la hoja.

        La marca y el correo cumplen lo mismo que en v1: identifican al
        solicitante y firman el `id_pedido`. El id de una fila estructurada
        hashhea también las columnas estructuradas, así que dos envíos
        iguales del mismo correo no se despachan dos veces y una edición de
        la respuesta vuelve a atenderse.
        """

        if not isinstance(fila, list):
            return None, None
        marca = _celda(fila, COL_MARCA_TEMPORAL)
        correo = _celda(fila, COL_CORREO).lower()
        if not marca or not email_valido(correo):
            return None, None
        tipo_crudo = _celda(fila, self._columnas_hoja["tipo_gacetilla"])
        actividad_cruda = _celda(fila, self._columnas_hoja["actividad"])
        area_cruda = _celda(fila, self._columnas_hoja["area_emisora"])
        texto = _celda(fila, self._columnas_hoja["pedido"])
        rol = self._padron.rol_para(correo) or ROL_NO_EN_PADRON
        id_pedido = _id_pedido(
            marca, correo, tipo_crudo, actividad_cruda, area_cruda, texto
        )

        tipo = tipo_crudo if tipo_crudo in tipos_de_gacetilla() else None
        if tipo is None:
            # El valor declarado no entra al registro: no pasó la lista
            # cerrada y sería prosa en claro. Sólo queda el código.
            return None, self._bloqueo(id_pedido, correo, rol, "tipo_no_declarado")

        # La actividad es un campo condicional del Form: la llevan sólo los
        # tipos que su contrato declara. Las reglas salen de los contratos
        # de entrada, no de listas copiadas a mano.
        sin_actividad = es_opcion_sin_actividad(actividad_cruda)
        if requiere_actividad(tipo):
            if sin_actividad:
                return None, self._bloqueo(
                    id_pedido, correo, rol, "actividad_no_figura", tipo=tipo
                )
            if not actividad_cruda:
                return None, self._bloqueo(
                    id_pedido, correo, rol, "actividad_requerida", tipo=tipo
                )
            if not es_id_actividad(actividad_cruda):
                # La celda no tiene forma de identificador: no queda en
                # el registro, sería texto libre.
                return None, self._bloqueo(
                    id_pedido,
                    correo,
                    rol,
                    "actividad_no_identificada",
                    tipo=tipo,
                )
        elif actividad_cruda and not sin_actividad:
            return None, self._bloqueo(
                id_pedido, correo, rol, "actividad_no_aplica", tipo=tipo
            )

        # Área emisora por padrón cerrado: obligatoria según el contrato de
        # entrada del tipo, prohibida donde el tipo declara que no aplica.
        area_req = "area_emisora" in campos_obligatorios(tipo)
        area_no_aplica = "area_emisora" in campos_que_no_aplican(tipo)
        if area_cruda:
            if area_no_aplica:
                return None, self._bloqueo(
                    id_pedido, correo, rol, "area_no_aplica", tipo=tipo
                )
            firma = firma_de_area(area_cruda)
            if firma is None:
                # El valor declarado tampoco entra al registro: no pasó el
                # padrón cerrado.
                return None, self._bloqueo(
                    id_pedido, correo, rol, "area_fuera_de_padron", tipo=tipo
                )
        elif area_req:
            return None, self._bloqueo(
                id_pedido, correo, rol, "area_requerida", tipo=tipo
            )

        # El núcleo hoy sólo despacha gacetillas de actividad por el camino
        # determinístico de #115: el texto armado acá lleva la palabra clave
        # y el identificador explícito con el mismo vocabulario que ya usa
        # la repregunta, así que el pedido estructurado entra por el mismo
        # clasificador y no hay segunda interpretación de la prosa. Los seis
        # tipos restantes confirman datos que el canal todavía no pide
        # (#121): el bloqueo `tipo_sin_despacho` lo deja visible sin
        # aproximar la pieza a la clase más parecida.
        if modo_de(tipo) == "genera" and requiere_actividad(tipo):
            return (
                PedidoCanal(
                    id_pedido=id_pedido,
                    solicitante=IdentidadSolicitante(
                        identificador=correo, rol=rol
                    ),
                    texto=f"gacetilla actividad {actividad_cruda}",
                    estructura={
                        "tipo": tipo,
                        "actividad": actividad_cruda,
                    },
                ),
                None,
            )
        return None, self._bloqueo(
            id_pedido, correo, rol, "tipo_sin_despacho", tipo=tipo
        )

    def _bloqueo(
        self,
        id_pedido: str,
        correo: str,
        rol: str,
        codigo: str,
        *,
        tipo: str | None = None,
    ) -> BloqueoCanalV2:
        return BloqueoCanalV2(
            id_pedido=id_pedido,
            correo=correo,
            rol=rol,
            codigo=codigo,
            mensaje=MENSAJES_BLOQUEO[codigo],
            tipo=tipo,
        )

    def _resolver_bloqueo(self, bloqueo: BloqueoCanalV2) -> None:
        """Aviso y registro de un bloqueo: desenlace acotado, sin generación.

        El núcleo no interviene; el pedido queda atendido con su código y con
        el origen de los hechos declarado por el canal. La prosa del campo
        libre no viaja: ni al registro —que no lleva prosa— ni al correo,
        que sólo lleva el mensaje fijo del código.
        """

        pedido = PedidoCanal(
            id_pedido=bloqueo.id_pedido,
            solicitante=IdentidadSolicitante(
                identificador=bloqueo.correo, rol=bloqueo.rol
            ),
            texto="",
        )
        resultado = ResultadoInterpretacion(
            estado="INVALIDA",
            intencion=None,
            correlation_id=str(uuid.uuid4()),
            log_path=self._atendidos_path,
            error=bloqueo.mensaje,
        )
        asunto = _asunto_aviso(pedido=pedido, resultado=resultado)
        cuerpo = self._cuerpo_aviso(pedido=pedido, resultado=resultado)
        aviso, aviso_codigo = self._enviar_aviso(pedido, resultado, asunto, cuerpo)
        self._registrar_atendido(
            pedido,
            resultado,
            aviso=aviso,
            aviso_codigo=aviso_codigo,
            contrato_hoja=self._contrato_hoja,
            declarado={
                "tipo": bloqueo.tipo,
            },
            origen_hechos="solicitud",
            codigo_bloqueo=bloqueo.codigo,
        )

    def _ids_atendidos(self) -> set[str]:
        if not self._atendidos_path.exists():
            return set()
        ids: set[str] = set()
        try:
            lineas = self._atendidos_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            raise CanalFormError("canal_form_registry_unavailable") from None
        for linea in lineas:
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                raise CanalFormError("canal_form_registry_invalid") from None
            # El archivo es interno, pero una línea deformada no puede
            # tratarse como «no existe»: quizás el pedido sí se atendió y
            # releerlo duplicaría un borrador. Fail closed.
            if (
                not isinstance(registro, dict)
                or registro.get("version") != REGISTRO_ATENDIDOS_VERSION
                or not isinstance(registro.get("id_pedido"), str)
                or _HASH_ID_RE.fullmatch(registro["id_pedido"]) is None
            ):
                raise CanalFormError("canal_form_registry_invalid")
            ids.add(registro["id_pedido"])
        return ids

    # --- Respuesta ----------------------------------------------------------

    def _enviar_aviso(
        self,
        pedido: PedidoCanal,
        resultado: ResultadoInterpretacion,
        asunto: str,
        cuerpo: str,
    ) -> tuple[str, str | None]:
        """Un intento de `gmail.send`; el desenlace vuelve para el registro.

        `EntregaRechazadaError` es una prohibición de política —destinatario
        fuera de la lista de prueba, cuerpo sin marca—: se registra como
        `rechazada` con su código, sin reintento. Cualquier otra excepción
        del destino (caída del medio, auth) es `fallida`. Nunca propaga:
        responder no puede romper el bucle de atención.
        """

        try:
            self._avisos.entregar(
                idempotency_key=_hash(
                    f"canal-form-aviso|{pedido.id_pedido}|{resultado.correlation_id}"
                ),
                destinatario=pedido.solicitante.identificador,
                asunto=asunto,
                cuerpo=cuerpo,
            )
        except EntregaRechazadaError as exc:
            return "rechazada", exc.code
        except Exception as exc:
            return "fallida", getattr(exc, "code", None)
        return "enviada", None

    def _cuerpo_aviso(
        self,
        *,
        pedido: PedidoCanal,
        resultado: ResultadoInterpretacion,
        enlaces_decision: Mapping[str, str] | None = None,
        enlaces_objetos: tuple[tuple[str, str, dict[str, str]], ...] = (),
    ) -> str:
        """Texto del aviso: sólo datos institucionales y links, nunca prosa.

        Todo cuerpo empieza con `MARCADOR_BORRADOR` porque el destino Gmail
        lo exige mientras rija la lista de prueba (D12). Lo que sigue sale
        del `ResultadoInterpretacion` —resumen con datos de la fuente, error
        con mensajes fijos, candidatas del índice—, nunca del texto del
        pedido ni del cuerpo del borrador. `enlaces_decision` son los links
        prellenados del Form de decisiones (#72): etiqueta fija más URL, la
        pieza publicada o descartada la decide una persona, no el agente.
        """

        ref = _ref_pedido(pedido.id_pedido)
        lineas: list[str] = []
        if resultado.estado == "PENDIENTE_VALIDACION":
            lineas.append(
                f"Tu pedido (ref. {ref}) quedó listo. El borrador espera "
                "validación humana: el Agente 1 no publica ni envía nada."
            )
            if resultado.resumen:
                lineas.append(_una_linea(resultado.resumen))
            url = _url_documento(resultado.referencia_borrador)
            if url is not None:
                lineas.extend(("", f"Borrador: {url}"))
            if enlaces_decision is not None:
                lineas.extend(
                    (
                        "",
                        "La difusión la hace una persona. Cuando definas "
                        "qué pasa con el borrador, registrá la decisión "
                        "con tu correo verificado:",
                        f"Lo publiqué: {enlaces_decision['publique']}",
                        f"Lo descarté: {enlaces_decision['descarte']}",
                    )
                )
            if enlaces_objetos:
                # #73: la plantilla exige la doble aprobación y el lote la
                # suya; el aviso enumera cada objeto con sus links del Form
                # de decisiones. Nada se envía sin las tres registradas.
                lineas.extend(
                    (
                        "",
                        "La plantilla y el envío necesitan decisiones "
                        "registradas en el Form de decisiones. Registrá "
                        "cada aprobación con tu correo verificado:",
                    )
                )
                for tipo, objeto_id, enlaces in enlaces_objetos:
                    lineas.append(f"{tipo}: {objeto_id}")
                    for decision in sorted(enlaces):
                        etiqueta = _ETIQUETA_DECISION.get(decision, decision)
                        lineas.append(f"  {etiqueta}: {enlaces[decision]}")
        elif resultado.estado == "PENDIENTE_CONFIRMACION":
            # #27: el pedido no se reconoció, el modelo propuso una intención
            # permitida y la actividad se resolvió por código. No hay borrador
            # ni nada que decidir: sólo un pedido nuevo que la persona revisa y
            # envía. El aviso lleva texto fijo más el resumen institucional y
            # el enlace prellenado con identificadores; ni la prosa del pedido
            # ni la salida del modelo viajan acá.
            lineas.append(
                f"Tu pedido (ref. {ref}) no se reconoció como una pieza del "
                "catálogo, así que no se generó nada."
            )
            if resultado.resumen:
                lineas.append(_una_linea(resultado.resumen))
            enlace = self._enlace_propuesta(pedido, resultado.propuesta)
            lineas.extend(
                (
                    "",
                    "Si es correcto, revisá el formulario y envialo: ese "
                    "envío es un pedido nuevo y recién ahí se genera.",
                )
            )
            if enlace is not None:
                lineas.append(
                    "Abrir el enlace no confirma nada. Podés editarlo antes "
                    "de enviarlo:"
                )
                lineas.append(enlace)
            if resultado.intencion == "generar_post":
                # El canal del post no se puede prellenar: nombrar la red en
                # el pedido ya lo haría reconocer por el camino determinístico,
                # así que una propuesta de post nunca lo trae. Se pide acá, con
                # el mismo circuito de aclaración que ya usa la repregunta.
                lineas.append(
                    "Si es un post, agregá «instagram» o «linkedin» en el "
                    "campo antes de enviar: sin la red no se genera."
                )
        elif resultado.estado == "PENDIENTE_DESAMBIGUACION":
            lineas.append(
                f"Tu pedido (ref. {ref}) necesita que elijas la actividad."
            )
            if resultado.resumen:
                lineas.extend(("", resultado.resumen))
            # Pares (candidata, enlace): si una candidata no tiene link
            # honesto que ofrecer se salta ella sola, sin desalinear a las
            # demás con el enlace que no les corresponde.
            enlaces = [
                (candidata, enlace)
                for candidata in resultado.candidatas
                if (
                    enlace := self._enlace_repregunta(
                        pedido, candidata, resultado.intencion
                    )
                )
                is not None
            ]
            if enlaces:
                lineas.extend(
                    (
                        "",
                        "Entrá al link de la actividad correcta y enviá el "
                        "formulario tal como viene (podés editarlo antes):",
                    )
                )
                for candidata, enlace in enlaces:
                    lineas.append(f"{candidata.orden}) {_etiqueta_candidata(candidata)}")
                    lineas.append(f"   {enlace}")
            if resultado.intencion == "generar_post":
                lineas.extend(
                    (
                        "",
                        "Si el post no es para la red que querías, agregá "
                        "«instagram» o «linkedin» en el campo antes de enviar.",
                    )
                )
        else:
            lineas.append(
                f"Tu pedido (ref. {ref}) "
                f"{_FRASES_CUERPO.get(resultado.estado, 'se procesó')}."
            )
            if resultado.error:
                lineas.append(_una_linea(resultado.error))
            if resultado.resumen:
                lineas.append(_una_linea(resultado.resumen))
        return f"{MARCADOR_BORRADOR}\n\n" + "\n".join(lineas) + "\n"

    def _enlace_propuesta(
        self, pedido: PedidoCanal, propuesta: PropuestaIntencion | None
    ) -> str | None:
        """Link prellenado de la propuesta (#27): ids, nunca prosa.

        Arma **por código** el texto del pedido nuevo: la palabra clave de la
        intención permitida y el identificador de la actividad resuelta, con
        la referencia corta del pedido original como trazabilidad. El núcleo
        vuelve a clasificar, resolver la actividad y autorizar por rol ese
        texto cuando la persona lo envíe: el enlace no es una autorización ni
        una confirmación. `None` si el resultado no trae propuesta o si la
        intención no tiene palabra clave.
        """

        if not isinstance(propuesta, PropuestaIntencion):
            return None
        keyword = _KEYWORD_POR_INTENCION.get(propuesta.intencion)
        if keyword is None:
            return None
        valor = (
            f"{keyword} actividad {propuesta.id_actividad} "
            f"(pedido {_ref_pedido(pedido.id_pedido)})"
        )
        return self._url_prellenada(valor)

    def _enlace_repregunta(
        self,
        pedido: PedidoCanal,
        candidata: CandidataActividad,
        intencion: str | None,
    ) -> str | None:
        """Link prellenado de una candidata: ids, nunca prosa.

        El valor precargado es una plantilla determinística
        `<keyword> actividad <id_actividad> (pedido <ref>)`: la palabra clave
        reclasifica la intención por el camino determinístico y el
        identificador explícito de la actividad resuelve directo, con o sin
        interacción pendiente vigente. `None` para una intención sin
        keyword —no hay link honesto que ofrecer.
        """

        keyword = _KEYWORD_POR_INTENCION.get(intencion or "")
        if keyword is None:
            return None
        valor = (
            f"{keyword} actividad {candidata.id_actividad} "
            f"(pedido {_ref_pedido(pedido.id_pedido)})"
        )
        return self._url_prellenada(valor)

    def _url_prellenada(self, valor: str) -> str:
        """URL del Form de pedidos con un valor precargado en su único campo."""

        return (
            f"https://docs.google.com/forms/d/e/{self._form_id}/viewform"
            f"?usp=pp_url&{self._entry_id}={quote(valor, safe='')}"
        )

    def _registrar_atendido(
        self,
        pedido: PedidoCanal,
        resultado: ResultadoInterpretacion,
        *,
        aviso: str,
        aviso_codigo: str | None,
        decisiones_objeto: str | None = None,
        decisiones_objetos: tuple[str, ...] = (),
        contrato_hoja: str | None = None,
        declarado: dict[str, str | None] | None = None,
        origen_hechos: str | None = None,
        codigo_bloqueo: str | None = None,
    ) -> None:
        """Agrega el pedido al registro de atendidos. Sin prosa ni correo.

        Es la única escritura del adapter: un JSONL local append-only. Una
        falla acá sí propaga —si no queda constancia del atendido, la
        próxima lectura volvería a despachar el pedido y duplicaría el
        borrador. `decisiones_objeto` es el id bajo el que el pedido quedó
        declarado como objeto de decisión de publicación (#72), cuando el
        aviso llevó los links del segundo Form; `decisiones_objetos`
        enumera los pares `tipo:objeto_id` que el pipeline dejó abiertos
        (#73: plantilla y lote).

        #122: para las filas del contrato v2, `contrato_hoja` declara la
        forma leída, `declarado` enumera los campos estructurados que trajo
        la fila (vocabulario cerrado: tipo, identificador de actividad) y
        `origen_hechos` declara de dónde vienen los hechos de la pieza: la
        fuente institucional de actividades por el despacho del núcleo, la
        declaración de la solicitud en un bloqueo. Filas de la forma v1 no
        registran esas claves y el archivo queda como antes.
        """

        self._directorio_estado.mkdir(parents=True, exist_ok=True)
        registro: dict[str, object] = {
            "version": REGISTRO_ATENDIDOS_VERSION,
            "id_pedido": pedido.id_pedido,
            "solicitante_hash": _hash(pedido.solicitante.identificador),
            "rol": pedido.solicitante.rol,
            "identidad_canal": "correo_verificado_form",
            "rol_origen": (
                "fuera_de_padron"
                if pedido.solicitante.rol == ROL_NO_EN_PADRON
                else "padron"
            ),
            "estado": resultado.estado,
            "intencion": resultado.intencion,
            "aviso": aviso,
            "aviso_codigo": aviso_codigo,
            "decisiones_objeto": decisiones_objeto,
            "decisiones_objetos": list(decisiones_objetos),
            "correlation_id": resultado.correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if contrato_hoja is not None:
            registro["contrato_hoja"] = contrato_hoja
        if declarado:
            registro["declarado"] = {
                campo: valor for campo, valor in declarado.items() if valor
            }
        if origen_hechos is not None:
            registro["origen_hechos"] = origen_hechos
        if codigo_bloqueo is not None:
            # Sólo en los desenlaces acotados del canal: el código de
            # bloqueo que explican el aviso y la auditoría.
            registro["resultado"] = codigo_bloqueo
        escribir_registro(self._atendidos_path, registro)


def _celda(fila: list[object], indice: int) -> str:
    """Celda como texto recortado; ausente o no-texto es cadena vacía."""

    if indice >= len(fila):
        return ""
    valor = fila[indice]
    return valor.strip() if isinstance(valor, str) else ""


def _id_pedido(*partes: str) -> str:
    """Id estable por respuesta: hash de las partes de la fila.

    La misma fila produce el mismo id entre lecturas —es lo que hace
    verificable «ya se atendió»— y nada queda legible en el hash: ni el
    correo ni la prosa. El texto entra al hash para que dos respuestas
    distintas del mismo correo dentro del mismo segundo no colapsen en un
    solo pedido —un `id` que las fundiera las dejaría una sin atender y en
    silencio, que es peor que un borrador duplicado. En la forma v2 (#122)
    las columnas estructuradas son partes del id por la misma razón: un
    envío con otra área o otra actividad es otro pedido. Si una persona
    edita la respuesta en la hoja, el id cambia y el pedido vuelve a
    atenderse: es la única forma honesta de «reintentar» una respuesta ya
    marcada.
    """

    return _hash("|".join(partes))


def _ref_pedido(id_pedido: str) -> str:
    return id_pedido[:REF_PEDIDO_CORTA]


def _una_linea(texto: str, *, maximo: int = 300) -> str:
    """Colapsa whitespace para insertar un dato en el cuerpo del aviso.

    Un título o resumen con saltos de línea inyectaría líneas al correo; se
    aplana y se acota — es presentación, no recorte del dato en el sistema.
    """

    aplanado = " ".join(str(texto).split())
    return aplanado[:maximo]


def _etiqueta_candidata(candidata: CandidataActividad) -> str:
    titulo = _una_linea(candidata.titulo, maximo=120)
    fecha = _una_linea(candidata.fecha_inicio, maximo=40)
    return f"{titulo} ({fecha})" if fecha else titulo


def _url_documento(referencia: ReferenciaBorrador | None) -> str | None:
    """Link abrible al borrador, sólo para referencias de Google Docs."""

    if referencia is None or referencia.tipo not in _TIPOS_REFERENCIA_DOCS:
        return None
    return f"https://docs.google.com/document/d/{referencia.referencia}/edit"


def _asunto_aviso(*, pedido: PedidoCanal, resultado: ResultadoInterpretacion) -> str:
    """Asunto fijo por estado con la referencia corta del pedido."""

    frase = _FRASES_ASUNTO.get(resultado.estado, "resultado de tu pedido")
    return f"[Agente 1] Pedido {_ref_pedido(pedido.id_pedido)}: {frase}"


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()
