"""HU-013/#72 — Registro de decisiones humanas por un segundo Google Form.

El correo del agente que presenta un borrador —o el resumen de una plantilla
o de un lote— trae links prellenados a un Form propio, «Registro de
decisiones». La persona lo abre, Google adjunta su correo verificado (mismo
modelo que ADR 0005: el Form restringe al dominio y recolecta la dirección;
la identidad viene de Google y el rol del padrón externo) y envía. El agente
lee la hoja de respuestas, valida la respuesta contra el padrón y contra el
catálogo, y la registra en la auditoría. **No dispara ninguna acción**: la
difusión la hace la persona a mano; la decisión registrada es la evidencia
que el circuito exige (#52).

La hoja de respuestas se lee por posición de columna, igual que en el Form
de pedidos (los enunciados de las preguntas son texto libre y no sirven de
contrato):

    Marca temporal | Dirección de correo | Tipo | Objeto | Decisión

`Tipo` y `Decisión` forman un catálogo cerrado; `Objeto` es el identificador
de aquello sobre lo que se decide. Los tres viajan prellenados en el link:
la persona no los escribe ni los elige. El catálogo vigente:

- `publicacion` — decisión sobre el borrador de una pieza de difusión
  (HU-010 gacetilla, HU-011 post): `publique` o `descarte`. Es el registro
  de «lo publiqué / lo descarté». No habilita ni ejecuta nada en el agente.
- `plantilla` — aprobación de una versión de plantilla, una decisión por
  rol: `apruebo_semantica` (Responsable de Gestión del Conocimiento) o
  `apruebo_utilitaria` (Coordinador de Extensión). El objeto es el id de la
  versión.
- `lote` — aprobación de un lote (incluye la habilitación de envíos de una
  actividad): `apruebo_lote`, decisión utilitaria del Coordinador. El objeto
  es el id del lote.
- `linea_descriptiva` — aprobación de la línea descriptiva de una actividad
  para el certificado de HU-014 (#74), una decisión por rol igual que la
  plantilla: `apruebo_semantica` o `apruebo_utilitaria`. El objeto es
  `linea_descriptiva-<id_actividad>-<hash>` (los `:` de la notación del
  ticket no entran en `ID_RE`; la forma elegida la deriva
  `linea_descriptiva.objeto_id_linea_descriptiva` y está documentada en el
  README para que #75 la consuma igual).

El rol que cada decisión exige es parte del catálogo (`ROLES_POR_DECISION`)
y sigue el acta del 22/09: semántica al RGC, utilitaria al Coordinador. La
decisión de publicación es la validación humana de la difusión (#52) y la
puede registrar cualquiera de los dos roles designados: un rol operativo del
padrón (`coordinador_seu`, `auxiliar_seu`) que pida piezas no puede decidir
sobre ellas.

Un link alterado produce rechazo registrado, nunca una decisión aceptada:

- `tipo_desconocido`: el tipo no pertenece al catálogo.
- `decision_fuera_de_catalogo`: la decisión no vale para ese tipo.
- `objeto_invalido`: el objeto no tiene forma de identificador.
- `objeto_inexistente`: el objeto no fue declarado pendiente. El único modo
  de abrir un objeto a decisión es que el agente lo declare al emitir el
  correo que trae el link (`EnlacesDecisiones`): un id inventado no existe
  en `decisiones-pendientes.jsonl` y se rechaza.
- `fuera_de_padron`: el correo verificado no figura en el padrón de roles.
- `rol_no_corresponde`: el rol del padrón no es el que la decisión exige.

Estado local del adapter, dos JSONL append-only dentro de un directorio de
estado compartido con quien emite los correos:

- `decisiones-pendientes.jsonl` — objetos abiertos a decisión, una línea por
  `(tipo, objeto)` declarada. La escribe quien mintea el link.
- `decisiones-procesadas.jsonl` — cada respuesta procesada, registrada o
  rechazada, con identidad verificada (hash del correo), rol del padrón y
  fecha con zona horaria. Es la auditoría de decisiones.

Ninguno de los dos archivos guarda el correo en claro: `correo_hash`
permite correlacionar sin exponer la dirección, igual que
`atendidos-canal-form.jsonl`. Un registro corrupto se trata como
`decisiones_registry_invalid` y la corrida se interrumpe antes de procesar
nada nuevo: un registro de decisiones inconsistente no se resuelve
adivinando.

La respuesta ya procesada no se relee: el id de respuesta es el hash de la
fila completa (`marca|correo|tipo|objeto|decisión`), así que el mismo envío
releído se deduplica. Dos decisiones distintas sobre el mismo objeto —
«publiqué» y después «descarté»— son eventos distintos y quedan los dos:
el registro es append-only de eventos y la interpretación del conjunto (una
plantilla está aprobada cuando existen las dos decisiones, por ejemplo) la
hace el consumidor del registro, no este adapter.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .canal_form import (
    ENTRY_ID_RE,
    PADRON_PREFIX,
    PADRON_ROLES_ENV,
    ROL_NO_EN_PADRON,
    PadronRoles,
    cargar_padron_roles_csv,
)
from .confirmaciones import (
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    ROLES_APROBACION,
    email_valido,
)
from .google_workspace import (
    ID_RE,
    MAX_WORKSPACE_TIMEOUT_S,
    AccessTokenProvider,
    GoogleSheetsLectorValores,
    TransporteHttp,
)
from .registro_auditoria import escribir_registro
from .workspace_config import _A1_RE, ConfiguracionWorkspaceError

# ---------------------------------------------------------------------------
# Contrato de la hoja de respuestas del Form de decisiones
# ---------------------------------------------------------------------------

COL_MARCA_TEMPORAL = 0
COL_CORREO = 1
COL_TIPO = 2
COL_OBJETO = 3
COL_DECISION = 4

# Catálogo cerrado de decisiones. `Tipo` discrimina sobre qué se decide;
# `Decisión` es el valor que el link prellenado declara. Ningún otro par
# (tipo, decisión) es una decisión válida: si llega, vino de un link
# alterado o de una respuesta cargada a mano y se rechaza.
TIPO_PUBLICACION = "publicacion"
TIPO_PLANTILLA = "plantilla"
TIPO_LOTE = "lote"
TIPO_LINEA_DESCRIPTIVA = "linea_descriptiva"

DECISION_PUBLIQUE = "publique"
DECISION_DESCARTE = "descarte"
DECISION_APRUEBO_SEMANTICA = "apruebo_semantica"
DECISION_APRUEBO_UTILITARIA = "apruebo_utilitaria"
DECISION_APRUEBO_LOTE = "apruebo_lote"

DECISIONES_POR_TIPO: dict[str, frozenset[str]] = {
    TIPO_PUBLICACION: frozenset({DECISION_PUBLIQUE, DECISION_DESCARTE}),
    TIPO_PLANTILLA: frozenset(
        {DECISION_APRUEBO_SEMANTICA, DECISION_APRUEBO_UTILITARIA}
    ),
    TIPO_LOTE: frozenset({DECISION_APRUEBO_LOTE}),
    TIPO_LINEA_DESCRIPTIVA: frozenset(
        {DECISION_APRUEBO_SEMANTICA, DECISION_APRUEBO_UTILITARIA}
    ),
}
TIPOS_DECISION = frozenset(DECISIONES_POR_TIPO)

# Rol del padrón que cada (tipo, decisión) exige. La publicación es la
# validación de la difusión y la puede dejar cualquiera de los dos roles
# designados; las aprobaciones de plantilla son una por rol; el lote es
# decisión utilitaria del Coordinador (habilita envíos de la actividad); la
# línea descriptiva del certificado sigue el mismo circuito que la plantilla
# (una aprobación por rol, #74).
ROLES_POR_DECISION: dict[tuple[str, str], frozenset[str]] = {
    (TIPO_PUBLICACION, DECISION_PUBLIQUE): ROLES_APROBACION,
    (TIPO_PUBLICACION, DECISION_DESCARTE): ROLES_APROBACION,
    (TIPO_PLANTILLA, DECISION_APRUEBO_SEMANTICA): frozenset(
        {ROL_APROBACION_SEMANTICA}
    ),
    (TIPO_PLANTILLA, DECISION_APRUEBO_UTILITARIA): frozenset(
        {ROL_APROBACION_UTILITARIA}
    ),
    (TIPO_LOTE, DECISION_APRUEBO_LOTE): frozenset({ROL_APROBACION_UTILITARIA}),
    (TIPO_LINEA_DESCRIPTIVA, DECISION_APRUEBO_SEMANTICA): frozenset(
        {ROL_APROBACION_SEMANTICA}
    ),
    (TIPO_LINEA_DESCRIPTIVA, DECISION_APRUEBO_UTILITARIA): frozenset(
        {ROL_APROBACION_UTILITARIA}
    ),
}

# Resultados y códigos de rechazo del registro. `rechazada` lleva siempre
# uno de estos códigos para que la auditoría diga por qué no valió.
RESULTADO_REGISTRADA = "registrada"
RESULTADO_RECHAZADA = "rechazada"
RECHAZO_TIPO_DESCONOCIDO = "tipo_desconocido"
RECHAZO_DECISION_FUERA_DE_CATALOGO = "decision_fuera_de_catalogo"
RECHAZO_OBJETO_INVALIDO = "objeto_invalido"
RECHAZO_OBJETO_INEXISTENTE = "objeto_inexistente"
RECHAZO_FUERA_DE_PADRON = "fuera_de_padron"
RECHAZO_ROL_NO_CORRESPONDE = "rol_no_corresponde"

ROL_ORIGEN_PADRON = "padron"
ROL_ORIGEN_FUERA_DE_PADRON = "fuera_de_padron"
IDENTIDAD_CANAL = "correo_verificado_form"

# Archivos de estado, append-only (ver docstring del módulo).
PENDIENTES_NOMBRE = "decisiones-pendientes.jsonl"
PROCESADAS_NOMBRE = "decisiones-procesadas.jsonl"
VERSION_PENDIENTES = "decisiones_pendientes_v1"
VERSION_PROCESADAS = "decisiones_procesadas_v1"

_HASH_ID_RE = re.compile(r"[0-9a-f]{64}\Z")

_DETALLE_CLAVE_RE = re.compile(r"[a-z0-9_]{1,64}\Z")

# Configuración por entorno del segundo Form: mismo patrón que
# `AGENTE1_FORM_PEDIDOS_*`, con una entry por campo prellenado.
FORM_DECISIONES_PREFIX = "AGENTE1_FORM_DECISIONES_"
ENV_DECISIONES_SHEET_ID = "AGENTE1_FORM_DECISIONES_SHEET_ID"
ENV_DECISIONES_RANGO_A1 = "AGENTE1_FORM_DECISIONES_RANGO_A1"
ENV_DECISIONES_FORM_ID = "AGENTE1_FORM_DECISIONES_FORM_ID"
ENV_DECISIONES_ENTRY_TIPO = "AGENTE1_FORM_DECISIONES_ENTRY_TIPO"
ENV_DECISIONES_ENTRY_OBJETO = "AGENTE1_FORM_DECISIONES_ENTRY_OBJETO"
ENV_DECISIONES_ENTRY_DECISION = "AGENTE1_FORM_DECISIONES_ENTRY_DECISION"
ENV_DECISIONES_TIMEOUT_S = "AGENTE1_FORM_DECISIONES_TIMEOUT_S"
_DECISIONES_REQUIRED_KEYS = frozenset(
    {
        ENV_DECISIONES_SHEET_ID,
        ENV_DECISIONES_RANGO_A1,
        ENV_DECISIONES_FORM_ID,
        ENV_DECISIONES_ENTRY_TIPO,
        ENV_DECISIONES_ENTRY_OBJETO,
        ENV_DECISIONES_ENTRY_DECISION,
        ENV_DECISIONES_TIMEOUT_S,
    }
)
_DECISIONES_ALLOWED_KEYS = _DECISIONES_REQUIRED_KEYS | {PADRON_ROLES_ENV}


class DecisionesFormError(RuntimeError):
    """Fallo operativo del canal de decisiones. `code` queda en evidencia."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# Configuración por entorno
# ---------------------------------------------------------------------------


@dataclass(frozen=True, repr=False)
class ConfiguracionFormDecisiones:
    """Valores validados del Form de decisiones y su hoja de respuestas."""

    sheet_id: str
    rango_a1: str
    form_id: str
    entry_tipo: str
    entry_objeto: str
    entry_decision: str
    timeout_s: float

    def resumen_seguro(self) -> dict[str, object]:
        """Vista publicable: sólo hashes de los identificadores."""

        return {
            "spreadsheet_ref_hash": _hash(self.sheet_id),
            "range_hash": _hash(self.rango_a1),
            "form_ref_hash": _hash(self.form_id),
            "entry_tipo_hash": _hash(self.entry_tipo),
            "entry_objeto_hash": _hash(self.entry_objeto),
            "entry_decision_hash": _hash(self.entry_decision),
            "timeout_s": self.timeout_s,
        }


def cargar_configuracion_form_decisiones(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionFormDecisiones:
    """Lee y valida el entorno del Form de decisiones.

    Falla con códigos (`canal_form_decisiones_config_incomplete`, por
    ejemplo), nunca con el valor problemático adentro del mensaje. Las
    variables desconocidas con los prefijos del canal se rechazan: un
    identificador mal tipeado no debe caer en silencio a otro recurso.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave
        for clave in env
        if (
            clave.startswith(FORM_DECISIONES_PREFIX)
            or clave.startswith(PADRON_PREFIX)
        )
        and clave not in _DECISIONES_ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionWorkspaceError("canal_form_decisiones_config_unknown_key")
    if any(clave not in env for clave in _DECISIONES_REQUIRED_KEYS):
        raise ConfiguracionWorkspaceError("canal_form_decisiones_config_incomplete")

    try:
        sheet_id = env[ENV_DECISIONES_SHEET_ID]
        rango_a1 = env[ENV_DECISIONES_RANGO_A1]
        form_id = env[ENV_DECISIONES_FORM_ID]
        entry_tipo = env[ENV_DECISIONES_ENTRY_TIPO]
        entry_objeto = env[ENV_DECISIONES_ENTRY_OBJETO]
        entry_decision = env[ENV_DECISIONES_ENTRY_DECISION]
        timeout_s = float(env[ENV_DECISIONES_TIMEOUT_S])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ConfiguracionWorkspaceError(
            "canal_form_decisiones_config_invalid"
        ) from None

    if (
        ID_RE.fullmatch(sheet_id) is None
        or _A1_RE.fullmatch(rango_a1) is None
        or ID_RE.fullmatch(form_id) is None
        or ENTRY_ID_RE.fullmatch(entry_tipo) is None
        or ENTRY_ID_RE.fullmatch(entry_objeto) is None
        or ENTRY_ID_RE.fullmatch(entry_decision) is None
        or not math.isfinite(timeout_s)
        or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
    ):
        raise ConfiguracionWorkspaceError("canal_form_decisiones_config_invalid")

    return ConfiguracionFormDecisiones(
        sheet_id=sheet_id,
        rango_a1=rango_a1,
        form_id=form_id,
        entry_tipo=entry_tipo,
        entry_objeto=entry_objeto,
        entry_decision=entry_decision,
        timeout_s=timeout_s,
    )


def crear_lector_decisiones(
    *,
    config: ConfiguracionFormDecisiones,
    token_provider: AccessTokenProvider,
    transport: TransporteHttp | None = None,
) -> GoogleSheetsLectorValores:
    """Lector de la Sheet de respuestas del Form de decisiones."""

    if not isinstance(config, ConfiguracionFormDecisiones):
        raise ValueError("configuración del Form de decisiones inválida")
    return GoogleSheetsLectorValores(
        spreadsheet_id=config.sheet_id,
        rango_a1=config.rango_a1,
        token_provider=token_provider,
        transport=transport,
        timeout_s=config.timeout_s,
    )


# ---------------------------------------------------------------------------
# Registro de decisiones: pendientes declarados y respuestas procesadas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoDecision:
    """Una respuesta del Form ya validada, tal como queda en la auditoría.

    `tipo`, `objeto_id`, `decision` y `marca_temporal_form` van sanitizados
    a una línea acotada: en una respuesta rechazada pueden venir de un link
    alterado, así que el registro guarda evidencia útil y no prosa libre.
    `correo_hash` es la identidad verificada hasheada; el correo en claro no
    se persiste nunca.
    """

    id_respuesta: str
    correo_hash: str
    rol: str
    rol_origen: str
    tipo: str
    objeto_id: str
    decision: str
    resultado: str
    rechazo_codigo: str | None
    marca_temporal_form: str
    timestamp: str


@dataclass(frozen=True)
class _RespuestaDecision:
    """Fila cruda del Form, con el correo verificado todavía en claro.

    Vive sólo en memoria durante el procesamiento de la corrida; lo que se
    persiste es `ResultadoDecision`, que ya trae el hash.
    """

    id_respuesta: str
    correo: str
    marca_temporal: str
    tipo: str
    objeto: str
    decision: str


class RegistroDecisiones:
    """Estado del canal de decisiones en dos JSONL append-only.

    `decisiones-pendientes.jsonl` declara los objetos abiertos a decisión:
    lo escribe quien emite el correo con los links (el canal de pedidos para
    publicaciones; los emisores de plantillas y lotes para el resto).
    `decisiones-procesadas.jsonl` es la auditoría: una línea por respuesta
    ya procesada, registrada o rechazada.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = Path(directorio)
        self._path_pendientes = self._directorio / PENDIENTES_NOMBRE
        self._path_procesadas = self._directorio / PROCESADAS_NOMBRE

    def declarar_pendiente(
        self,
        *,
        tipo: str,
        objeto_id: str,
        detalle: Mapping[str, str] | None = None,
    ) -> None:
        """Abre `objeto_id` a decisiones de `tipo`. Idempotente.

        Es el anti-tamper: un link alterado con un id inventado no encuentra
        pendiente y se rechaza. Si la pareja `(tipo, objeto_id)` ya está
        declarada no se escribe una segunda línea: el detalle del primer
        emitido sigue siendo la evidencia.
        """

        if tipo not in TIPOS_DECISION:
            raise DecisionesFormError("decision_tipo_invalid")
        if ID_RE.fullmatch(objeto_id) is None:
            raise DecisionesFormError("decision_objeto_invalid")
        if self.es_pendiente(tipo=tipo, objeto_id=objeto_id):
            return
        self._directorio.mkdir(parents=True, exist_ok=True)
        linea = {
            "version": VERSION_PENDIENTES,
            "tipo": tipo,
            "objeto_id": objeto_id,
            "detalle": _sanear_detalle(detalle),
            "declarado_en": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self._path_pendientes.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(linea, ensure_ascii=False) + "\n")
        except OSError:
            raise DecisionesFormError(
                "decisiones_registry_unavailable"
            ) from None

    def es_pendiente(self, *, tipo: str, objeto_id: str) -> bool:
        return any(
            pendiente["tipo"] == tipo and pendiente["objeto_id"] == objeto_id
            for pendiente in self._leer_pendientes()
        )

    def pendientes(self) -> tuple[dict[str, object], ...]:
        return self._leer_pendientes()

    def registrar(self, resultado: ResultadoDecision) -> None:
        """Agrega la respuesta procesada a la auditoría."""

        self._directorio.mkdir(parents=True, exist_ok=True)
        linea = {
            "version": VERSION_PROCESADAS,
            "id_respuesta": resultado.id_respuesta,
            "correo_hash": resultado.correo_hash,
            "rol": resultado.rol,
            "rol_origen": resultado.rol_origen,
            "identidad_canal": IDENTIDAD_CANAL,
            "tipo": resultado.tipo,
            "objeto_id": resultado.objeto_id,
            "decision": resultado.decision,
            "resultado": resultado.resultado,
            "rechazo_codigo": resultado.rechazo_codigo,
            "marca_temporal_form": resultado.marca_temporal_form,
            "timestamp": resultado.timestamp,
        }
        try:
            escribir_registro(self._path_procesadas, linea)
        except OSError:
            raise DecisionesFormError(
                "decisiones_registry_unavailable"
            ) from None

    def ids_procesados(self) -> set[str]:
        """Ids de respuesta ya procesadas (registradas o rechazadas)."""

        return {linea["id_respuesta"] for linea in self._leer_procesadas()}

    def procesadas(self) -> tuple[dict[str, object], ...]:
        return self._leer_procesadas()

    def _leer_pendientes(self) -> tuple[dict[str, object], ...]:
        lineas = _leer_jsonl(self._path_pendientes)
        for linea in lineas:
            if (
                not isinstance(linea, dict)
                or linea.get("version") != VERSION_PENDIENTES
                or linea.get("tipo") not in TIPOS_DECISION
                or not isinstance(linea.get("objeto_id"), str)
                or ID_RE.fullmatch(linea["objeto_id"]) is None
            ):
                raise DecisionesFormError("decisiones_registry_invalid")
        return lineas

    def _leer_procesadas(self) -> tuple[dict[str, object], ...]:
        lineas = _leer_jsonl(self._path_procesadas)
        for linea in lineas:
            if (
                not isinstance(linea, dict)
                or linea.get("version") != VERSION_PROCESADAS
                or not isinstance(linea.get("id_respuesta"), str)
                or _HASH_ID_RE.fullmatch(linea["id_respuesta"]) is None
            ):
                raise DecisionesFormError("decisiones_registry_invalid")
        return lineas


def _leer_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    if not path.exists():
        return ()
    try:
        lineas = tuple(
            json.loads(texto)
            for texto in path.read_text(encoding="utf-8").splitlines()
            if texto.strip()
        )
    except (OSError, json.JSONDecodeError):
        raise DecisionesFormError("decisiones_registry_invalid") from None
    return lineas


def _sanear_detalle(
    detalle: Mapping[str, str] | None,
) -> dict[str, str] | None:
    """Acota el detalle de un pendiente a pares clave/valor cortos.

    El detalle es contexto institucional del emisor (la pieza, la
    correlación), no texto libre: claves snake_case acotadas y valores de
    una línea, así el registro nunca carga prosa.
    """

    if detalle is None:
        return None
    saneado: dict[str, str] = {}
    for clave, valor in detalle.items():
        if _DETALLE_CLAVE_RE.fullmatch(str(clave)) is None or not isinstance(
            valor, str
        ):
            raise DecisionesFormError("decision_detalle_invalid")
        saneado[str(clave)] = _una_linea(valor, maximo=200)
    return saneado or None


# ---------------------------------------------------------------------------
# Links prellenados del Form de decisiones
# ---------------------------------------------------------------------------


class EnlacesDecisiones:
    """Mintea los links del Form de decisiones y declara los pendientes.

    La misma instancia sirve a cualquier emisor: el canal de pedidos la usa
    para adjuntar «lo publiqué / lo descarté» al correo del borrador, y los
    correos de plantilla y de lote mintean con `enlaces_para` un link por
    decisión del tipo. `declarar_pendiente` es lo que abre el objeto: sin la
    declaración, el lector rechaza la decisión como `objeto_inexistente`.
    """

    def __init__(
        self,
        *,
        registro: RegistroDecisiones,
        form_id: str,
        entry_tipo: str,
        entry_objeto: str,
        entry_decision: str,
    ) -> None:
        if (
            not isinstance(registro, RegistroDecisiones)
            or ID_RE.fullmatch(form_id) is None
            or ENTRY_ID_RE.fullmatch(entry_tipo) is None
            or ENTRY_ID_RE.fullmatch(entry_objeto) is None
            or ENTRY_ID_RE.fullmatch(entry_decision) is None
        ):
            raise ValueError(
                "EnlacesDecisiones requiere registro e identificadores válidos"
            )
        self._registro = registro
        self._form_id = form_id
        self._entry_tipo = entry_tipo
        self._entry_objeto = entry_objeto
        self._entry_decision = entry_decision

    def enlace(self, *, tipo: str, objeto_id: str, decision: str) -> str:
        """Mintea un link prellenado. Los tres campos se validan al catálogo."""

        if (
            tipo not in DECISIONES_POR_TIPO
            or decision not in DECISIONES_POR_TIPO[tipo]
            or ID_RE.fullmatch(objeto_id) is None
        ):
            raise DecisionesFormError("decision_link_invalid")
        return (
            "https://docs.google.com/forms/d/e/"
            + quote(self._form_id, safe="")
            + "/viewform?usp=pp_url"
            + f"&{self._entry_tipo}={quote(tipo, safe='')}"
            + f"&{self._entry_objeto}={quote(objeto_id, safe='')}"
            + f"&{self._entry_decision}={quote(decision, safe='')}"
        )

    def enlaces_para(self, *, tipo: str, objeto_id: str) -> dict[str, str]:
        """Un link por decisión del catálogo del tipo.

        Para `plantilla` y `linea_descriptiva` devuelve el link semántico y
        el utilitario del mismo objeto; para `lote`, el único link de
        aprobación.
        """

        if tipo not in DECISIONES_POR_TIPO:
            raise DecisionesFormError("decision_tipo_invalid")
        return {
            decision: self.enlace(
                tipo=tipo, objeto_id=objeto_id, decision=decision
            )
            for decision in sorted(DECISIONES_POR_TIPO[tipo])
        }

    def declarar_pendiente(
        self,
        *,
        tipo: str,
        objeto_id: str,
        detalle: Mapping[str, str] | None = None,
    ) -> None:
        self._registro.declarar_pendiente(
            tipo=tipo, objeto_id=objeto_id, detalle=detalle
        )

    def declarar_y_enlaces(
        self,
        *,
        tipo: str,
        objeto_id: str,
        detalle: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Declara el objeto pendiente y devuelve los links del tipo.

        Es el punto único de los emisores: declarar y mintear en la misma
        llamada evita que un correo salga con links a un objeto que el
        registro todavía no conoce.
        """

        self.declarar_pendiente(tipo=tipo, objeto_id=objeto_id, detalle=detalle)
        return self.enlaces_para(tipo=tipo, objeto_id=objeto_id)

    def enlaces_publicacion(
        self,
        *,
        objeto_id: str,
        pieza: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        """Atajo del canal de pedidos: declara el borrador y mintea los links.

        `pieza` (`gacetilla`/`post`) y la correlación quedan en el detalle
        del pendiente como contexto de auditoría.
        """

        detalle: dict[str, str] = {}
        if pieza is not None:
            detalle["pieza"] = pieza
        if correlation_id is not None:
            detalle["correlation_id"] = correlation_id
        return self.declarar_y_enlaces(
            tipo=TIPO_PUBLICACION,
            objeto_id=objeto_id,
            detalle=detalle or None,
        )


# ---------------------------------------------------------------------------
# Canal: leer respuestas, validar, registrar
# ---------------------------------------------------------------------------


class CanalFormDecisiones:
    """Adapter del segundo Form: valida cada respuesta nueva y la audita.

    A diferencia del canal de pedidos no alimenta al núcleo ni responde con
    un correo: la respuesta a una decisión es el registro mismo. La pieza
    publicada o el envío habilitado los hace una persona, no el agente.
    """

    def __init__(
        self,
        *,
        lector: GoogleSheetsLectorValores,
        padron: PadronRoles,
        registro: RegistroDecisiones,
    ) -> None:
        if not isinstance(padron, PadronRoles):
            raise ValueError(
                "CanalFormDecisiones requiere un PadronRoles explícito"
            )
        if not isinstance(registro, RegistroDecisiones):
            raise ValueError(
                "CanalFormDecisiones requiere un RegistroDecisiones explícito"
            )
        self._lector = lector
        self._padron = padron
        self._registro = registro

    def atender(self) -> tuple[ResultadoDecision, ...]:
        """Procesa las respuestas nuevas de la hoja, una sola pasada.

        Devuelve el resultado de cada respuesta procesada, registrada o
        rechazada. Las filas sin correo verificado válido o sin marca
        temporal no son atribuibles a una identidad y se omiten, igual que
        en el canal de pedidos; las demás entran todas a la auditoría.
        """

        filas = self._lector.leer_valores()
        procesados = self._registro.ids_procesados()
        resultados: list[ResultadoDecision] = []
        for fila in filas:
            respuesta = _respuesta_desde_fila(fila)
            if respuesta is None or respuesta.id_respuesta in procesados:
                continue
            resultado = self._resolver(respuesta)
            # Si el registro falla la respuesta queda sin constancia:
            # propagar evita fingir que la auditoría la tomó.
            self._registro.registrar(resultado)
            procesados.add(respuesta.id_respuesta)
            resultados.append(resultado)
        return tuple(resultados)

    def _resolver(self, respuesta: _RespuestaDecision) -> ResultadoDecision:
        rol_padron = self._padron.rol_para(respuesta.correo)
        codigo = self._codigo_rechazo(respuesta, rol_padron)
        return ResultadoDecision(
            id_respuesta=respuesta.id_respuesta,
            correo_hash=_hash(respuesta.correo),
            rol=(
                rol_padron
                if rol_padron is not None
                else ROL_NO_EN_PADRON
            ),
            rol_origen=(
                ROL_ORIGEN_PADRON
                if rol_padron is not None
                else ROL_ORIGEN_FUERA_DE_PADRON
            ),
            tipo=_una_linea(respuesta.tipo, maximo=128),
            objeto_id=_una_linea(respuesta.objeto, maximo=128),
            decision=_una_linea(respuesta.decision, maximo=128),
            resultado=(
                RESULTADO_REGISTRADA
                if codigo is None
                else RESULTADO_RECHAZADA
            ),
            rechazo_codigo=codigo,
            marca_temporal_form=_una_linea(
                respuesta.marca_temporal, maximo=128
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _codigo_rechazo(
        self, respuesta: _RespuestaDecision, rol_padron: str | None
    ) -> str | None:
        """Primera razón de rechazo, o `None` si la decisión es registrable.

        El orden es estructural primero, identidad después: una respuesta
        que ni siquiera nombra un objeto declarado no necesita mirar el
        padrón para saber que no vale, y un link alterado se rechaza con el
        mismo código venga de quien venga.
        """

        if respuesta.tipo not in DECISIONES_POR_TIPO:
            return RECHAZO_TIPO_DESCONOCIDO
        if respuesta.decision not in DECISIONES_POR_TIPO[respuesta.tipo]:
            return RECHAZO_DECISION_FUERA_DE_CATALOGO
        if ID_RE.fullmatch(respuesta.objeto) is None:
            return RECHAZO_OBJETO_INVALIDO
        if not self._registro.es_pendiente(
            tipo=respuesta.tipo, objeto_id=respuesta.objeto
        ):
            return RECHAZO_OBJETO_INEXISTENTE
        if rol_padron is None:
            return RECHAZO_FUERA_DE_PADRON
        if (
            rol_padron
            not in ROLES_POR_DECISION[(respuesta.tipo, respuesta.decision)]
        ):
            return RECHAZO_ROL_NO_CORRESPONDE
        return None


def _respuesta_desde_fila(fila: list[object]) -> _RespuestaDecision | None:
    """Mapea una fila cruda a una respuesta atribuible, o `None`.

    Sin correo verificado válido la respuesta no tiene identidad y sin marca
    temporal no tiene id estable: se omite. Cubre la fila de encabezados y
    restos ajenos al Form.
    """

    marca = _celda(fila, COL_MARCA_TEMPORAL)
    correo = _celda(fila, COL_CORREO).lower()
    if not marca or not email_valido(correo):
        return None
    tipo = _celda(fila, COL_TIPO)
    objeto = _celda(fila, COL_OBJETO)
    decision = _celda(fila, COL_DECISION)
    return _RespuestaDecision(
        id_respuesta=_hash("|".join((marca, correo, tipo, objeto, decision))),
        correo=correo,
        marca_temporal=marca,
        tipo=tipo,
        objeto=objeto,
        decision=decision,
    )


def _celda(fila: list[object], indice: int) -> str:
    """Valor de la celda como string, o "" si no existe o es vacía."""

    if indice >= len(fila):
        return ""
    valor = fila[indice]
    if valor is None:
        return ""
    return str(valor).strip()


def _una_linea(texto: str, *, maximo: int = 300) -> str:
    """Colapsa whitespace (incluidos saltos) y acota el largo."""

    return " ".join(texto.split())[:maximo]


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


__all__ = [
    "COL_CORREO",
    "COL_DECISION",
    "COL_MARCA_TEMPORAL",
    "COL_OBJETO",
    "COL_TIPO",
    "CanalFormDecisiones",
    "ConfiguracionFormDecisiones",
    "DECISIONES_POR_TIPO",
    "DECISION_APRUEBO_LOTE",
    "DECISION_APRUEBO_SEMANTICA",
    "DECISION_APRUEBO_UTILITARIA",
    "DECISION_DESCARTE",
    "DECISION_PUBLIQUE",
    "DecisionesFormError",
    "EnlacesDecisiones",
    "FORM_DECISIONES_PREFIX",
    "IDENTIDAD_CANAL",
    "PENDIENTES_NOMBRE",
    "PROCESADAS_NOMBRE",
    "RECHAZO_DECISION_FUERA_DE_CATALOGO",
    "RECHAZO_FUERA_DE_PADRON",
    "RECHAZO_OBJETO_INEXISTENTE",
    "RECHAZO_OBJETO_INVALIDO",
    "RECHAZO_ROL_NO_CORRESPONDE",
    "RECHAZO_TIPO_DESCONOCIDO",
    "RESULTADO_REGISTRADA",
    "RESULTADO_RECHAZADA",
    "ROLES_POR_DECISION",
    "RegistroDecisiones",
    "ResultadoDecision",
    "TIPO_LINEA_DESCRIPTIVA",
    "TIPO_LOTE",
    "TIPO_PLANTILLA",
    "TIPO_PUBLICACION",
    "TIPOS_DECISION",
    "cargar_configuracion_form_decisiones",
    "cargar_padron_roles_csv",
    "crear_lector_decisiones",
]
