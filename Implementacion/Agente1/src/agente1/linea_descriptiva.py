"""HU-014/#74 — Línea descriptiva por actividad en el certificado.

El certificado mantiene la plantilla fija de la SEU y suma **una línea
descriptiva por actividad** que redacta el modelo. Título, carga horaria y
modalidad son variables del registro de la actividad que renderiza la
plantilla, nunca texto del modelo: por eso el prompt sólo recibe los campos
que describen el contenido (título, descripción, público) y los gates
rechazan cualquier hecho que la línea intente afirmar.

La línea se aprueba **una vez por actividad** por el Form de decisiones,
con el mismo circuito que la plantilla: `apruebo_semantica` del RGC y
`apruebo_utilitaria` del Coordinador de Extensión. La decisión queda atada
al hash del texto de la línea y al `id_actividad`, así que reaprobar no es
una decisión sobre el certificado sino sobre el texto exacto.

**Clave de decisión (contrato con #75, documentado también en el README).**
El objeto del Form es

    linea_descriptiva-<id_actividad>-<sha256 de la línea normalizada>

La notación del ticket (`linea_descriptiva:<id>:<hash>`) no entra en
`ID_RE`, que no admite `:`; la forma elegida codifica los mismos tres
elementos con el alfabeto del identificador. La normalización previa al
hash es `normalizar_linea` (NFC, espacios colapsados, strip), de modo que
una diferencia de whitespace no cambie el objeto. Todo consumidor deriva el
objeto con `objeto_id_linea_descriptiva`, nunca a mano.

Las precondiciones que este módulo deja verificables para el circuito de
emisión (`certificados.py` las exige cuando la solicitud trae línea):

- `linea_descriptiva_aprobada`: las dos decisiones registradas sobre el
  objeto, cada una con el rol del padrón que le corresponde.
- `lote_cierre_aprobado`: la `apruebo_lote` utilitaria registrada sobre el
  objeto del lote de cierre. La lista de participantes y su emisión son
  alcance de #75; acá sólo se verifica la decisión.

Gates deterministas (`validar_linea_descriptiva`): una sola línea,
extensión acotada, sin cifras ni fechas escritas por el modelo (dígitos,
fechas numéricas, meses y días), sin duraciones en letras (`horas`, `hs`),
sin modalidad, lugares, organizadores, importes, correos ni URLs, sin
actos institucionales ni eco de instrucciones, y sin repetir las palabras
distintivas del título. La coincidencia semántica del contenido con la
actividad la juzga la aprobación humana, no el gate: lo mecánico garantiza
que la línea no puede afirmar hechos, porque los hechos los pone la
plantilla desde el registro.
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
from typing import Mapping, Protocol

from .confirmaciones import (
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
)
from .decisiones_form import (
    DECISION_APRUEBO_LOTE,
    DECISION_APRUEBO_SEMANTICA,
    DECISION_APRUEBO_UTILITARIA,
    RESULTADO_REGISTRADA,
    TIPO_LINEA_DESCRIPTIVA,
    TIPO_LOTE,
    EnlacesDecisiones,
    RegistroDecisiones,
)
from .posts import (
    PATRON_ACCION_NO_AUTORIZADA,
    PATRON_ATRIBUCION_FACTUAL,
    PATRON_EMAIL,
    PATRON_FECHA,
    PATRON_HECHO_CREATIVO,
    PATRON_IMPORTE,
    PATRON_INYECCION,
    PATRON_LUGAR_ETIQUETADO,
    PATRON_LUGAR_PROPIO,
    PATRON_REFERENCIA_LUGAR,
    PATRON_TUTEO,
    PATRON_URL,
    _contiene_fragmento_significativo,
)
from .presupuesto import (
    MENSAJE_PRESUPUESTO_AGOTADO,
    RESULTADO_PRESUPUESTO_AGOTADO,
    PresupuestoAgotadoError,
)
from .registro_auditoria import escribir_registro

HU = "HU-014"
CONTRACT_VERSION = "linea_descriptiva_v1"
PROMPT_VERSION = "linea_descriptiva_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"

# Extensión de la línea: límites técnicos provisionales, en el espíritu de
# los topes de prosa de la gacetilla (DEF-A1-007). Una línea de certificado
# es una sola oración descriptiva; 200 caracteres ya es generoso para ese
# formato y 20 filtra salidas degeneradas. La calidad la juzga la SEU.
MIN_LINEA_CHARS = 20
MAX_LINEA_CHARS = 200

# El objeto del Form entra en `ID_RE` (128 chars): 18 del prefijo, 1 del
# guion antes del hash y 64 de sha256 dejan 45 para el identificador de la
# actividad. Un id más largo se rechaza en la frontera, antes de que el
# registro lo haga con un error menos claro.
ID_ACTIVIDAD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,44}\Z")
_OBJETO_PREFIX = "linea_descriptiva-"

# Campos de la fila que entran al prompt. Fecha, carga, modalidad,
# organización, contacto y enlaces quedan afuera a propósito: el modelo no
# puede copiar un hecho que nunca vio. Son exactamente los campos que
# describen el contenido de la actividad.
CAMPOS_PROMPT = ("titulo", "descripcion", "publico")
CAMPOS_REQUERIDOS = ("id_actividad", "titulo", "descripcion")

# Fechas escritas en letras: meses y días de semana. Las fechas numéricas
# las cubre PATRON_FECHA (posts); los dígitos, la regla general.
PATRON_FECHA_LETRAS = re.compile(
    r"\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"octubre|noviembre|diciembre|lunes|martes|mi[eé]rcoles|jueves|"
    r"viernes|s[aá]bado|domingo)\b",
    flags=re.IGNORECASE,
)
# Carga horaria redactada en letras ("cuarenta horas", "6 hs"): los dígitos
# ya están prohibidos, pero una duración puede escribirse sin cifras.
PATRON_DURACION = re.compile(r"\b(?:horas?|hs)\b", flags=re.IGNORECASE)
# Complemento de PATRON_HECHO_CREATIVO para variantes de modalidad que su
# catálogo no lista ("híbrida", "a distancia").
PATRON_MODALIDAD_COMPLEMENTO = re.compile(
    r"\b(?:h[ií]brid[oa]s?|a\s+distancia)\b", flags=re.IGNORECASE
)


class LineaDescriptivaError(RuntimeError):
    """Fallo de contrato del módulo. `code` queda en la auditoría."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Generator(Protocol):
    """Puerto del generador de texto, el mismo contrato que HU-010/HU-011."""

    modelo: str
    num_predict: int | None

    def generar(self, prompt: str) -> str: ...


def normalizar_linea(linea: str) -> str:
    """Forma canónica de la línea: NFC, espacios colapsados, strip.

    Es la base del hash que va al objeto de decisión: dos textos iguales
    salvo whitespace comparten objeto, como debe ser.
    """

    return " ".join(
        unicodedata.normalize("NFC", linea).split()
    )


def hash_linea_descriptiva(linea: str) -> str:
    return hashlib.sha256(
        normalizar_linea(linea).encode("utf-8")
    ).hexdigest()


def objeto_id_linea_descriptiva(id_actividad: str, linea: str) -> str:
    """Objeto del Form de decisiones para esta línea de esta actividad.

    `linea_descriptiva-<id_actividad>-<sha256>`: ajuste documentado de la
    notación del ticket (los `:` no entran en `ID_RE`). Derivarlo siempre
    por acá es lo que permite que cualquier consumidor —este módulo,
    `certificados.py`, la emisión de #75— hable del mismo objeto.
    """

    if (
        not isinstance(id_actividad, str)
        or ID_ACTIVIDAD_RE.fullmatch(id_actividad) is None
        or not isinstance(linea, str)
    ):
        raise LineaDescriptivaError("linea_objeto_invalid")
    return f"{_OBJETO_PREFIX}{id_actividad}-{hash_linea_descriptiva(linea)}"


def validar_linea_descriptiva(
    linea: object, *, titulo_actividad: str | None = None
) -> tuple[str, ...]:
    """Gates deterministas sobre el texto. Devuelve códigos, nunca prosa.

    `titulo_actividad` es opcional: quien lo tiene (la generación con la
    fila; el certificado con su campo `actividad`) exige además que la
    línea no repita las palabras distintivas del título, igual que el gate
    creativo de HU-011.
    """

    if not isinstance(linea, str):
        return ("linea_tipo_invalido",)
    errores: list[str] = []
    if any(
        unicodedata.category(caracter).startswith("C") for caracter in linea
    ):
        errores.append("linea_caracteres_invalidos")
    # "Una sola línea" se evalúa sobre las líneas con contenido: un salto
    # final no descalifica, dos líneas de texto sí.
    if sum(1 for tramo in linea.splitlines() if tramo.strip()) > 1:
        errores.append("linea_multiple")
    normalizada = normalizar_linea(linea)
    if not normalizada:
        errores.append("linea_vacia")
    else:
        if len(normalizada) > MAX_LINEA_CHARS:
            errores.append("linea_excedida")
        if len(normalizada) < MIN_LINEA_CHARS:
            errores.append("linea_corta")
    # Cualquier dígito se rechaza sin más análisis, igual que en HU-011:
    # separar una cifra inocente de una inventada exige entender el texto,
    # y todos los números legítimos del certificado los pone la plantilla.
    if re.search(r"\d", normalizada):
        errores.append("unauthorized_number")
    if PATRON_FECHA.search(normalizada) or PATRON_FECHA_LETRAS.search(
        normalizada
    ):
        errores.append("unauthorized_date")
    if PATRON_DURACION.search(normalizada):
        errores.append("unauthorized_duration")
    if PATRON_EMAIL.search(normalizada):
        errores.append("unauthorized_email")
    if PATRON_URL.search(normalizada):
        errores.append("unauthorized_url")
    if PATRON_IMPORTE.search(normalizada):
        errores.append("unauthorized_amount")
    if (
        PATRON_LUGAR_ETIQUETADO.search(normalizada)
        or PATRON_LUGAR_PROPIO.search(normalizada)
        or PATRON_REFERENCIA_LUGAR.search(normalizada)
    ):
        errores.append("unauthorized_place")
    if PATRON_ACCION_NO_AUTORIZADA.search(normalizada):
        errores.append("unauthorized_action_claim")
    if PATRON_TUTEO.search(normalizada):
        errores.append("non_rioplatense_register")
    if (
        PATRON_HECHO_CREATIVO.search(normalizada)
        or PATRON_MODALIDAD_COMPLEMENTO.search(normalizada)
        or PATRON_ATRIBUCION_FACTUAL.search(normalizada)
    ):
        errores.append("unauthorized_fact_claim")
    if PATRON_INYECCION.search(normalizada):
        errores.append("prompt_injection_echo")
    if titulo_actividad and _contiene_fragmento_significativo(
        normalizada, titulo_actividad
    ):
        # El título lo renderiza la plantilla: una línea que repite sus
        # palabras distintivas está duplicando un hecho, no describiendo.
        errores.append("source_fact_in_creative_field")
    return tuple(dict.fromkeys(errores))


@dataclass(frozen=True)
class ResultadoLinea:
    """Salida del pipeline de la línea descriptiva.

    `PENDIENTE_VALIDACION` es el único estado con línea: generada y con
    gates superados, a la espera de las dos decisiones del Form.
    """

    estado: str
    correlation_id: str
    log_path: Path
    objeto_id: str | None = None
    linea: str | None = None
    error: str | None = None
    validation_errors: tuple[str, ...] = ()


def construir_prompt_linea(fila: Mapping[str, str]) -> str:
    """Prompt con la plantilla versionada y el subconjunto de la fila.

    El modelo sólo ve `CAMPOS_PROMPT`: describir sin hechos es posible con
    título, descripción y público; el resto del registro no entra.
    """

    plantilla = (
        files("agente1")
        .joinpath("prompts", "linea_descriptiva_v1.txt")
        .read_text(encoding="utf-8")
    )
    datos = json.dumps(
        {
            campo: fila[campo]
            for campo in CAMPOS_PROMPT
            if fila.get(campo, "").strip()
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return plantilla.replace("{datos_fuente}", datos)


def generar_linea_descriptiva(
    *,
    fila: Mapping[str, str],
    directorio_salida: Path,
    generator: Generator,
) -> ResultadoLinea:
    """Genera la línea de una actividad con gates fail-closed.

    Misma doctrina que `procesar_solicitud`: nada llega a validación sin
    pasar la frontera anterior (fila completa, generación, contrato de
    salida). Cada ejecución deja una línea JSONL en
    `logs/lineas-descriptivas.jsonl` con hashes, nunca el texto.
    """

    correlation_id = str(uuid.uuid4())
    log_path = (
        Path(directorio_salida) / "logs" / "lineas-descriptivas.jsonl"
    )
    modelo = getattr(generator, "modelo", None)
    num_predict = getattr(generator, "num_predict", None)

    def cerrar(
        *,
        estado: str,
        resultado: str,
        error: str | None,
        objeto_id: str | None = None,
        linea: str | None = None,
        validation_errors: tuple[str, ...] = (),
    ) -> ResultadoLinea:
        entrada = json.dumps(
            fila if isinstance(fila, Mapping) else repr(fila),
            ensure_ascii=False,
            sort_keys=True,
            default=lambda valor: f"<invalid:{type(valor).__name__}>",
        )
        registro: dict[str, object] = {
            "hu": HU,
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "policy_status": POLICY_STATUS,
            "correlation_id": correlation_id,
            "id_actividad": fila.get("id_actividad")
            if isinstance(fila, Mapping)
            else None,
            "modelo": modelo,
            "num_predict": num_predict,
            "estado": estado,
            "resultado": resultado,
            "error": error,
            "input_hash": _hash(entrada),
            "output_hash": hash_linea_descriptiva(linea)
            if linea is not None
            else None,
            "linea_objeto_id": objeto_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if validation_errors:
            registro["validation_errors"] = list(validation_errors)
        escribir_registro(log_path, registro)
        return ResultadoLinea(
            estado=estado,
            correlation_id=correlation_id,
            log_path=log_path,
            objeto_id=objeto_id,
            linea=linea,
            error=error,
            validation_errors=validation_errors,
        )

    if not isinstance(fila, Mapping):
        return cerrar(
            estado="INVALIDA",
            resultado="source_request_invalid",
            error="fila_invalida",
        )
    id_actividad = fila.get("id_actividad", "")
    if (
        not isinstance(id_actividad, str)
        or ID_ACTIVIDAD_RE.fullmatch(id_actividad) is None
    ):
        return cerrar(
            estado="INVALIDA",
            resultado="source_request_invalid",
            error="actividad_id_invalid",
        )
    faltantes = [
        campo
        for campo in CAMPOS_REQUERIDOS
        if not str(fila.get(campo, "") or "").strip()
    ]
    if faltantes:
        return cerrar(
            estado="INCOMPLETA",
            resultado="datos_incompletos",
            error=f"Campos obligatorios faltantes: {', '.join(faltantes)}",
        )

    try:
        contenido = generator.generar(construir_prompt_linea(fila))
    except PresupuestoAgotadoError:
        return cerrar(
            estado="FALLIDA",
            resultado=RESULTADO_PRESUPUESTO_AGOTADO,
            error=MENSAJE_PRESUPUESTO_AGOTADO,
        )
    except Exception:
        return cerrar(
            estado="FALLIDA",
            resultado="error_generacion",
            error="Falló la generación de la línea",
        )

    errores = validar_linea_descriptiva(
        contenido, titulo_actividad=str(fila.get("titulo", ""))
    )
    if errores:
        return cerrar(
            estado="FALLIDA",
            resultado="salida_no_conforme",
            error="La línea generada no cumple el contrato mínimo",
            validation_errors=errores,
        )

    linea = normalizar_linea(contenido)
    return cerrar(
        estado="PENDIENTE_VALIDACION",
        resultado="linea_generada",
        error=None,
        objeto_id=objeto_id_linea_descriptiva(id_actividad, linea),
        linea=linea,
    )


def declarar_linea_pendiente(
    enlaces: EnlacesDecisiones, *, id_actividad: str, linea: str
) -> dict[str, object]:
    """Abre la línea a decisión y devuelve objeto y links del par de roles.

    Es el punto único de los emisores, igual que `declarar_y_enlaces` para
    plantillas y lotes: sin esta declaración la respuesta del Form se
    rechaza como `objeto_inexistente`.
    """

    objeto_id = objeto_id_linea_descriptiva(id_actividad, linea)
    enlaces_decision = enlaces.declarar_y_enlaces(
        tipo=TIPO_LINEA_DESCRIPTIVA,
        objeto_id=objeto_id,
        detalle={"id_actividad": id_actividad, "hu": "hu_014"},
    )
    return {"objeto_id": objeto_id, "enlaces": enlaces_decision}


def linea_descriptiva_aprobada(
    registro: RegistroDecisiones, *, id_actividad: str, linea: str
) -> bool:
    """¿La línea exacta de esta actividad tiene las dos aprobaciones?

    Verdadero sólo si en la auditoría figuran `apruebo_semantica` con rol
    del RGC **y** `apruebo_utilitaria` con rol del Coordinador sobre el
    objeto de esta línea. La aprobación parcial no habilita nada, y una
    decisión sobre otro texto —otro hash— no vale para esta línea: es el
    vínculo entre el contenido aprobado y el contenido emitido.
    """

    if not isinstance(registro, RegistroDecisiones):
        return False
    try:
        objeto_id = objeto_id_linea_descriptiva(id_actividad, linea)
    except LineaDescriptivaError:
        return False
    roles_por_decision = {
        str(linea_registro.get("decision")): str(
            linea_registro.get("rol")
        )
        for linea_registro in registro.procesadas()
        if linea_registro.get("tipo") == TIPO_LINEA_DESCRIPTIVA
        and linea_registro.get("objeto_id") == objeto_id
        and linea_registro.get("resultado") == RESULTADO_REGISTRADA
    }
    return (
        roles_por_decision.get(DECISION_APRUEBO_SEMANTICA)
        == ROL_APROBACION_SEMANTICA
        and roles_por_decision.get(DECISION_APRUEBO_UTILITARIA)
        == ROL_APROBACION_UTILITARIA
    )


def lote_cierre_aprobado(
    registro: RegistroDecisiones, *, objeto_lote: str
) -> bool:
    """¿El lote de cierre tiene la `apruebo_lote` utilitaria registrada?

    El objeto del lote lo define quien emite la lista de cierre (#75); la
    precondición verificable es la misma para cualquiera de sus formas:
    decisión registrada por el rol utilitario del padrón.
    """

    if not isinstance(registro, RegistroDecisiones) or not isinstance(
        objeto_lote, str
    ):
        return False
    return any(
        linea_registro.get("tipo") == TIPO_LOTE
        and linea_registro.get("objeto_id") == objeto_lote
        and linea_registro.get("decision") == DECISION_APRUEBO_LOTE
        and linea_registro.get("resultado") == RESULTADO_REGISTRADA
        and linea_registro.get("rol") == ROL_APROBACION_UTILITARIA
        for linea_registro in registro.procesadas()
    )


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


__all__ = [
    "CAMPOS_PROMPT",
    "CAMPOS_REQUERIDOS",
    "CONTRACT_VERSION",
    "ID_ACTIVIDAD_RE",
    "LineaDescriptivaError",
    "MAX_LINEA_CHARS",
    "MIN_LINEA_CHARS",
    "PROMPT_VERSION",
    "ResultadoLinea",
    "construir_prompt_linea",
    "declarar_linea_pendiente",
    "generar_linea_descriptiva",
    "hash_linea_descriptiva",
    "linea_descriptiva_aprobada",
    "lote_cierre_aprobado",
    "normalizar_linea",
    "objeto_id_linea_descriptiva",
    "validar_linea_descriptiva",
]
