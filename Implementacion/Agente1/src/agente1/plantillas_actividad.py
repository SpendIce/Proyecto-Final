"""Plantilla de correo por actividad para HU-012 (#73).

La SEU pide por el canal — «generá la plantilla de correos de la
actividad» — y el agente produce **una plantilla por actividad**: un
documento versionado con prosa descriptiva redactada por el modelo y con
todos los datos dinámicos viajando como variables ``{{...}}``. El circuito
tiene dos tramos, separados a propósito por la aprobación humana:

1. **Generación** (`procesar_plantilla_actividad`, despachada por la
   intención `generar_plantilla_actividad` de `interpretacion.py`). El
   modelo ve sólo el título, la descripción y el público de la actividad
   y devuelve **un párrafo de prosa descriptiva**, sin saludo, sin cierre
   y sin variables (#140). El código compone el cuerpo alrededor de esa
   prosa con las variables del catálogo
   `contracts/plantilla_actividad_v2.json` —destinatario, actividad,
   inicio, contacto y, con plan, cuotas, medios y bonificaciones—, el
   mismo patrón que la gacetilla (#107, #121). Hasta v1 el modelo recibía
   la plantilla base entera y escribía el cuerpo con las variables: con
   actividades reales copiaba el bloque `LÍMITES`, rompía u omitía
   variables y agregaba hechos sueltos (0/5 en los cuatro modelos medidos
   para #51). El gate descarta la salida entera ante cualquier
   incumplimiento: llaves, saludo o cierre en la prosa; dígito, fecha,
   importe, correo o enlace en el texto; hecho de la fuente copiado;
   inyección o registro fuera del rioplatense. El cuerpo compuesto vuelve
   a pasar el gate de variables del catálogo. El éxito es un
   borrador `PENDIENTE_VALIDACION`, con dos objetos abiertos a decisión
   en el Form (#72): la plantilla (aprobación semántica y utilitaria) y
   el lote de envíos de la actividad (aprobación utilitaria).
2. **Envío por lote** (`encolar_lote_actividad` / `correr_lote_actividad`).
   Sólo cuando el registro de decisiones tiene las tres respuestas
   `registrada` — las dos de la plantilla y la del lote — el render
   determinista arma el correo de cada destinatario reemplazando las
   variables por los valores de la fila y del plan de pago. El modelo no
   interviene en el render. Los ítems nacen en `ENVIO_ENCOLADO`, como los
   recordatorios de pago: la autorización es la aprobación del lote, no
   una doble aprobación por pieza. La entrega la hace `drenar_envios`
   contra el destino habilitado — el fake explícito en la demostración.

La identidad de la plantilla y del lote se deriva del documento aprobado:
`tpl-<actividad>-<hash>` y `lote-<actividad>-<hash>` del mismo `sha256`
del texto. Aprobar esos objetos es aprobar esa redacción exacta para esa
actividad: otra versión generada produce otros objetos, que reinician el
circuito. La clave del ítem por destinatario cubre actividad, inscripción
y hash del documento, así que repetir la corrida con la misma plantilla
es `DUPLICADA` y con otra plantilla es un lote nuevo que vuelve a pedir
aprobación.

Los recordatorios de pago no pasan por acá: siguen siendo deterministas,
diarios y por lote propio (#38). Lo mismo vale para los disparadores
automáticos: no existen en este módulo — son HU-015 y quedan fuera del
alcance de #73.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Sequence

if TYPE_CHECKING:
    # Sólo el tipo: `decisiones_form` importa `canal_form`, que importa
    # `interpretacion`, que importa este módulo — a nivel de módulo sería
    # un ciclo. Las constantes se importan dentro de `encolar_lote_actividad`.
    from .decisiones_form import RegistroDecisiones

from .confirmaciones import (
    ESTADO_ENVIO_ENCOLADO,
    MARCADOR_BORRADOR,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    ColaEnvios,
    DestinoConfirmaciones,
    ItemEnvio,
    RegistroConfirmaciones,
    ResultadoEnvioEncolado,
    _hash,
    _monto_texto,
    _seccion_cuerpo,
    drenar_envios,
    email_valido,
)
from .destinos import (
    BORRADOR_MARKER,
    ID_SOLICITUD_RE,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
    ReferenciaBorrador,
)
from .fuentes import FuenteSolicitudes, FuenteSolicitudesError
from .pagos import PlanPago
from .posts import (
    PATRON_ATRIBUCION_FACTUAL,
    PATRON_EMAIL,
    PATRON_FECHA,
    PATRON_IMPORTE,
    PATRON_NUMERO,
    PATRON_TUTEO,
    PATRON_URL,
    _contiene_fragmento_significativo,
    _contiene_hecho,
)
from .presupuesto import (
    MENSAJE_PRESUPUESTO_AGOTADO,
    RESULTADO_PRESUPUESTO_AGOTADO,
    PresupuestoAgotadoError,
)
from .procesamiento import (
    Generator,
    ResultadoProceso,
    _hash_json,
    _hash_texto,
    _normalizar_fila_fuente,
    _num_predict,
    _registrar,
    _validar_id_solicitud,
)

HU = "HU-012"
CONTRACT_VERSION = "plantilla_actividad_v2"
TEMPLATE_VERSION = "plantilla_actividad_generada_v2"
# La estructura del cuerpo sigue siendo la de la base provisional v1; desde
# #140 la compone `_componer_cuerpo` y el modelo ya no la ve.
BASE_TEMPLATE_VERSION = "plantilla_actividad_base_provisional_v1"
PROMPT_VERSION = "plantilla_actividad_generacion_v4"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
CIRCUITO = "plantilla_actividad"

CONTRATO = json.loads(
    files("agente1")
    .joinpath("contracts", f"{CONTRACT_VERSION}.json")
    .read_text(encoding="utf-8")
)
CAMPOS_FILA_OBLIGATORIOS = tuple(CONTRATO["campos_fila_obligatorios"])
VARIABLES_REQUERIDAS = frozenset(CONTRATO["variables_requeridas"])
VARIABLES_OPCIONALES_FILA = frozenset(CONTRATO["variables_opcionales_fila"])
VARIABLES_PLAN_REQUERIDAS = frozenset(CONTRATO["variables_plan_requeridas"])
VARIABLES_PLAN_OPCIONALES = frozenset(CONTRATO["variables_plan_opcionales"])
VARIABLES_CONOCIDAS = (
    VARIABLES_REQUERIDAS
    | VARIABLES_OPCIONALES_FILA
    | VARIABLES_PLAN_REQUERIDAS
    | VARIABLES_PLAN_OPCIONALES
)
MAX_PLANTILLA_CHARS = int(CONTRATO["max_plantilla_chars"])
MIN_PROSA_PALABRAS = int(CONTRATO["min_prosa_palabras"])
MAX_PLANTILLA_PALABRAS = int(CONTRATO["max_plantilla_palabras"])
MAX_PROSA_PALABRAS = int(CONTRATO["max_prosa_palabras"])
MAX_PROSA_CHARS = int(CONTRATO["max_prosa_chars"])

# La variable de fila se habilita sólo cuando la columna existe y trae
# dato: mapea cada nombre de variable a su columna de la planilla.
COLUMNA_POR_VARIABLE_FILA = {
    "descripcion": "descripcion",
    "fecha_fin": "fecha_fin",
    "fecha_limite_inscripcion": "fecha_limite_inscripcion",
    "hora": "hora",
    "modalidad": "modalidad",
    "duracion_horas": "duracion_horas",
    "lugar": "lugar",
    "organiza": "organiza",
    "publico": "publico",
    "enlace_inscripcion": "enlace_inscripcion",
}
VARIABLES_PLAN = VARIABLES_PLAN_REQUERIDAS | VARIABLES_PLAN_OPCIONALES

# Campos cuyo valor literal en la plantilla la invalida: son hechos que el
# render completa desde la fila (o del plan). `titulo` y `descripcion`
# además se controlan por fragmento, no sólo por frase completa.
CAMPOS_HECHOS_FILA = (
    "titulo",
    "descripcion",
    "organiza",
    "contacto",
    "modalidad",
    "lugar",
    "publico",
    "enlace_inscripcion",
    "fecha_inicio",
    "fecha_fin",
    "fecha_limite_inscripcion",
    "hora",
    "duracion_horas",
    "fuente",
)

_TEXTO_PROMPT = (
    files("agente1")
    .joinpath("prompts", f"{PROMPT_VERSION}.txt")
    .read_text(encoding="utf-8")
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_PLACEHOLDER_MALFORMADO_RE = re.compile(r"\{\{?[^{}\s]*\}?\}?")
_PALABRA_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

# Conceptos sin variable propia: afirmarlos es un hecho que el contrato no
# autoriza ni el render puede completar. `certificado` es HU-014, cupos y
# gratuidad/descuentos no son datos de la fuente ni del plan.
PATRON_HECHO_NO_AUTORIZADO = re.compile(
    r"\b(?:gratis|gratuit[oa]s?|cupos?|certificad[oa]s?|descuentos?)\b",
    flags=re.IGNORECASE,
)
# Eco de vocabulario de prompting. Distinto del de `posts.py`: acá no se
# banea `instrucciones` porque el correo de preinscripción habla
# legítimamente de instrucciones de pago — el dominio del documento es otro.
PATRON_INYECCION_PLANTILLA = re.compile(
    r"\b(?:ignor[aá]\w*|prompt|system|assistant|jailbreak)\b",
    flags=re.IGNORECASE,
)
# Datos personales etiquetados: el único dato del destinatario es
# {{nombre_destinatario}}; el resto no existe como variable.
PATRON_DATO_PERSONAL = re.compile(
    r"\b(?:dni|documento\s+(?:de\s+)?identidad|legajo|tel[eé]fono|"
    r"celular|domicilio|cuit|cuil)\b",
    flags=re.IGNORECASE,
)
# Marcas del marco del documento: el modelo entrega el cuerpo y el sistema
# le pone el encabezado de versión, la marca de borrador y la sección
# LÍMITES. Una salida que las repite o las inventa rompería el corte de
# `_seccion_cuerpo` — la parte que viaja al destinatario — o le metería al
# destinatario texto de control que no fue aprobado.
PATRON_MARCO_DOCUMENTO = re.compile(
    r"\b(?:L[ÍI]MITES|TEMPLATE_VERSION|POLICY_STATUS|ESTADO_INSTITUCIONAL|"
    r"PROMPT_VERSION|CONTRACT_VERSION|BASE_TEMPLATE|PLANTILLA_BASE|"
    r"DATOS_JSON|BORRADOR)\b"
)

# Saludo o cierre al principio de una línea de la prosa: el código ya pone
# «Hola {{nombre_destinatario}},» y el contacto; repetirlos duplicaría el
# saludo o metería una firma que nadie aprobó.
PATRON_SALUDO_O_CIERRE = re.compile(
    r"^\s*(?:hola|estimad[oa]s?|querid[oa]s?|saludos|atentamente|"
    r"cordialmente|un\s+saludo)\b",
    flags=re.IGNORECASE | re.MULTILINE,
)

_LINEA_PROVISIONAL = (
    "Este texto es una plantilla provisional y requiere validación "
    "humana antes de cualquier envío."
)


@dataclass(frozen=True)
class ResultadoPlantillaActividad(ResultadoProceso):
    """El `ResultadoProceso` del pipeline, más los objetos de decisión.

    `plantilla_id` y `lote_id` son los objetos que el canal declara en el
    registro de decisiones (#72) para que el correo lleve sus links; el
    `detalle` de cada uno lo arma el núcleo de interpretación. `documento`
    es el texto íntegro de la plantilla — no viaja al log ni al aviso,
    sirve para que el tramo de lote la renderice. `actividad` es el título
    de la fuente, para que el resumen del canal nombre la actividad sin
    releer la fuente.
    """

    plantilla_id: str | None = None
    lote_id: str | None = None
    documento: str | None = None
    actividad: str | None = None


@dataclass(frozen=True)
class DestinatarioActividad:
    """Un destinatario del lote de la actividad.

    No es la persona del padrón de roles: es quien figura como inscripto o
    preinscripto de la actividad (padrón de preinscriptos en la demo).
    """

    id_inscripcion: str
    nombre_destinatario: str
    email_destinatario: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.id_inscripcion, str)
            or ID_SOLICITUD_RE.fullmatch(self.id_inscripcion) is None
            or not isinstance(self.nombre_destinatario, str)
            or not self.nombre_destinatario.strip()
            or not email_valido(self.email_destinatario)
        ):
            raise ValueError("destinatario de actividad inválido")


@dataclass(frozen=True)
class ResultadoItemActividad:
    """Qué pasó con un destinatario al encolarlo en el lote."""

    idempotency_key: str
    estado: str


@dataclass(frozen=True)
class ResultadoLoteActividad:
    """Resultado de intentar encolar el lote de la actividad.

    `estado` es `ENVIO_ENCOLADO` cuando al menos un ítem quedó encolado,
    `DUPLICADA` cuando todos ya existían, `VACIO` si no había
    destinatarios, e `INVALIDA` con `error` cuando las decisiones del
    registro no habilitan el encolado.
    """

    estado: str
    plantilla_id: str
    lote_id: str
    log_path: Path
    correlation_id: str
    items: tuple[ResultadoItemActividad, ...]
    error: str | None = None


def id_plantilla(documento: str, actividad_id: str) -> str:
    """Id del objeto `plantilla` de esta versión, para el Form #72.

    Deriva del texto íntegro: aprobar este objeto es aprobar esa
    redacción exacta. `ID_RE`-seguro porque `actividad_id` ya pasó la
    misma allowlist.
    """

    return f"tpl-{actividad_id}-{_hash(documento)[:24]}"


def id_lote(documento: str, actividad_id: str) -> str:
    """Id del objeto `lote` de la actividad bajo esta plantilla."""

    return f"lote-{actividad_id}-{_hash(documento)[:24]}"


def clave_item_actividad(
    *, actividad_id: str, id_inscripcion: str, documento: str
) -> str:
    """Clave de idempotencia del correo de un destinatario del lote.

    Cubre actividad, inscripción y el hash del documento: una segunda
    corrida con la misma plantilla choca en `crear` como `DUPLICADA`, y
    una plantilla nueva produce claves nuevas porque el texto que la SEU
    aprobó es otro.
    """

    return _hash(
        json.dumps(
            [
                "correo_actividad",
                actividad_id,
                id_inscripcion,
                _hash(documento),
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def documento_desde_borrador(contenido_md: str) -> str:
    """El documento de plantilla desde un `.md` de `borradores/`.

    Le saca la marca `# BORRADOR — NO PUBLICAR` que el destino antepone;
    si no está, asume que ya es el documento — el gate de `encolar` lo
    vuelve a verificar por hash igual al que aprobó la decisión.
    """

    texto = contenido_md if isinstance(contenido_md, str) else ""
    if texto.startswith(BORRADOR_MARKER):
        return texto[len(BORRADOR_MARKER):]
    return texto


def procesar_plantilla_actividad(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
    planes_pago: Mapping[str, PlanPago] | None = None,
) -> ResultadoPlantillaActividad:
    """Genera la plantilla de correo de una actividad.

    Devuelve siempre un `ResultadoPlantillaActividad` y nunca propaga
    excepciones del generador, de la fuente ni del destino. El éxito es
    `PENDIENTE_VALIDACION` con el documento versionado y los ids de los
    objetos de decisión; los demás estados son los de siempre del seam
    (`INCOMPLETA`, `INVALIDA`, `FALLIDA`).

    `planes_pago` es el mapa actividad → `PlanPago` disponible en esta
    corrida. Cuando la actividad tiene plan, el contrato exige las
    variables de cuotas y medios de pago; cuando no, esas variables están
    prohibidas — una plantilla que promete un plan que no existe es un
    hecho inventado.
    """

    correlation_id = str(uuid.uuid4())
    inicio_fuente = time.perf_counter()
    try:
        _validar_id_solicitud(id_solicitud)
    except (TypeError, ValueError):
        return _resultado_fuente(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_request_invalid",
        )
    try:
        fila = fuente.obtener(id_solicitud)
    except FuenteSolicitudesError as error_fuente:
        return _resultado_fuente(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=error_fuente.code,
        )
    except Exception:
        return _resultado_fuente(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_unavailable",
        )
    fila, source_error_code = _normalizar_fila_fuente(fila, id_solicitud)
    if source_error_code is not None:
        return _resultado_fuente(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=source_error_code,
        )

    faltantes = [
        campo
        for campo in CAMPOS_FILA_OBLIGATORIOS
        if not fila.get(campo, "").strip()
    ]
    if faltantes:
        error = f"Campos obligatorios faltantes: {', '.join(faltantes)}"
        log_path = _log_generacion(directorio_salida)
        _registrar(
            log_path,
            _linea_log(
                correlation_id=correlation_id,
                id_solicitud=id_solicitud,
                generator=generator,
                latencia_s=0.0,
                estado="INCOMPLETA",
                resultado="datos_incompletos",
                error=error,
                input_hash=_hash_json(fila),
            ),
        )
        return ResultadoPlantillaActividad(
            estado="INCOMPLETA",
            borrador_path=None,
            log_path=log_path,
            correlation_id=correlation_id,
            error=error,
        )

    plan = planes_pago.get(id_solicitud) if planes_pago else None
    if plan is not None and not isinstance(plan, PlanPago):
        plan = None

    inicio = time.perf_counter()
    prompt = _construir_prompt(fila)
    try:
        contenido_generado = generator.generar(prompt)
    except PresupuestoAgotadoError:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio, 6),
            resultado=RESULTADO_PRESUPUESTO_AGOTADO,
            error=MENSAJE_PRESUPUESTO_AGOTADO,
        )
    except Exception:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio, 6),
            resultado="error_generacion",
            error="Falló la generación de la plantilla",
        )
    latencia_s = round(time.perf_counter() - inicio, 6)
    contenido = (
        contenido_generado.strip()
        if isinstance(contenido_generado, str)
        else ""
    )
    if not contenido:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_vacia",
            error="El generador devolvió contenido vacío",
        )
    cuerpo = _componer_cuerpo(contenido, plan)
    errores = sorted(
        set(_validar_prosa(contenido) + _validar_plantilla(cuerpo, fila, plan))
    )
    if errores:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_no_conforme",
            error="La salida generada no cumple el contrato de la plantilla",
            validation_errors=errores,
        )

    documento = _armar_documento(cuerpo, id_solicitud)
    borrador = f"{BORRADOR_MARKER}{documento}"
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    try:
        referencia_borrador = destino_efectivo.guardar(
            f"{id_solicitud}-plantilla", borrador
        )
        if not isinstance(referencia_borrador, ReferenciaBorrador):
            raise DestinoBorradoresError("destination_contract_invalid")
    except DestinoBorradoresError as error_destino:
        return _resultado_destino(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            destination_error_code=error_destino.code,
        )
    except Exception:
        return _resultado_destino(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            destination_error_code="destination_unavailable",
        )

    plantilla_id = id_plantilla(documento, id_solicitud)
    lote_id = id_lote(documento, id_solicitud)
    log_path = _log_generacion(directorio_salida)
    _registrar(
        log_path,
        _linea_log(
            correlation_id=correlation_id,
            id_solicitud=id_solicitud,
            generator=generator,
            latencia_s=latencia_s,
            estado="PENDIENTE_VALIDACION",
            resultado="borrador_generado",
            error=None,
            input_hash=_hash_json(fila),
            output_hash=_hash_texto(borrador),
            plantilla_id=plantilla_id,
            lote_id=lote_id,
            con_plan=plan is not None,
        ),
    )
    return ResultadoPlantillaActividad(
        estado="PENDIENTE_VALIDACION",
        borrador_path=referencia_borrador.path,
        log_path=log_path,
        correlation_id=correlation_id,
        referencia_borrador=referencia_borrador,
        plantilla_id=plantilla_id,
        lote_id=lote_id,
        documento=documento,
        actividad=fila["titulo"].strip(),
    )


def _construir_prompt(fila: dict[str, str]) -> str:
    """El prompt del tramo de redacción: sólo lo que la prosa necesita.

    Desde #140 el modelo no ve la plantilla base ni el catálogo de
    variables: escribe un párrafo y el código compone el resto. Tampoco ve
    la modalidad, el organizador, la duración ni el plan de pago: son
    hechos que el cuerpo o el render ponen desde la fila, y dárselos
    invitaba a escribirlos — el gate los rechazaría igual, pero la defensa
    es no exponerlos. El bloque de pago lo agrega `_componer_cuerpo`.
    Desde v3 (#51) tampoco ve el público: el correo va a quien ya se
    preinscribió, y con el público a la vista los modelos lo copiaban.
    """

    datos = {
        "titulo": fila.get("titulo", ""),
        "descripcion": fila.get("descripcion", ""),
    }
    return _TEXTO_PROMPT.replace(
        "{datos_fuente}", json.dumps(datos, ensure_ascii=False, indent=2)
    )


def _componer_cuerpo(prosa: str, plan: PlanPago | None) -> str:
    """El cuerpo de la plantilla con la prosa del modelo en su lugar.

    Reproduce la estructura de la base provisional v1: saludo, línea de
    preinscripción e inicio, prosa, bloque de pago cuando la actividad
    declara plan, y contacto. Las variables las pone el código, así que
    las requeridas aparecen siempre una vez y las de pago sólo con plan.
    """

    bloque_plan = (
        "El valor y las formas de pago de la actividad son:\n"
        "{{detalle_cuotas}}\n"
        "Medios de pago: {{medios_pago}}.\n"
        "{{bonificaciones}}\n\n"
        if plan is not None
        else ""
    )
    return (
        "Hola {{nombre_destinatario}},\n\n"
        "Te escribimos por tu preinscripción a {{actividad}}.\n"
        "Inicio: {{fecha_inicio}}.\n\n"
        f"{prosa.strip()}\n\n"
        f"{bloque_plan}"
        "Contacto: {{contacto}}\n"
    )


def _validar_prosa(prosa: str) -> list[str]:
    """Gate propio del párrafo del modelo, antes de componer el cuerpo.

    Los hechos, datos dinámicos y marcas del documento los controla
    `_validar_plantilla` sobre el cuerpo compuesto; acá va lo que sólo
    tiene sentido sobre la prosa suelta: que no traiga llaves (las
    variables son del código), ni saludo o cierre, y que su extensión sea
    la de un párrafo.
    """

    errores: list[str] = []
    if "{" in prosa or "}" in prosa:
        errores.append("template_variable_in_prose")
    if PATRON_SALUDO_O_CIERRE.search(prosa):
        errores.append("greeting_or_closing_in_prose")
    palabras = len(_PALABRA_RE.findall(_PLACEHOLDER_RE.sub(" ", prosa)))
    if palabras < MIN_PROSA_PALABRAS:
        errores.append("template_too_short")
    if palabras > MAX_PROSA_PALABRAS or len(prosa) > MAX_PROSA_CHARS:
        errores.append("output_too_long")
    return errores


def _variables_permitidas(
    fila: dict[str, str], plan: PlanPago | None
) -> frozenset[str]:
    """Variables con dato que las llene en esta actividad.

    Una variable permitida pero sin dato no es opcional: es un hueco que
    el render no podría completar, así que usarla se rechaza en la
    generación (`template_variable_without_data`) en lugar de explotar en
    el render de cada destinatario.
    """

    permitidas = set(VARIABLES_REQUERIDAS)
    for variable, columna in COLUMNA_POR_VARIABLE_FILA.items():
        if fila.get(columna, "").strip():
            permitidas.add(variable)
    if plan is not None:
        permitidas |= VARIABLES_PLAN
    return frozenset(permitidas)


def _validar_plantilla(
    contenido: str, fila: dict[str, str], plan: PlanPago | None
) -> list[str]:
    """Gate mecánico del cuerpo de la plantilla. Nunca se recorta.

    Desde #140 recibe el cuerpo que compuso `_componer_cuerpo` con la
    prosa del modelo adentro: los controles de variables verifican la
    composición, y los de texto, la prosa.

    Controles: variables (catálogo cerrado, requeridas presentes una
    vez, permitidas con dato, ninguna repetida ni mal formada), ningún
    dato dinámico escrito (números, fechas, importes, correos, URLs),
    ningún hecho de la fuente copiado al texto, ningún dato personal,
    registro rioplatense, sin eco de prompting y sin hechos que el
    contrato no autoriza (cupos, certificados, gratuidad, descuentos,
    atribución de organización).
    """

    errores: list[str] = []
    if len(contenido) > MAX_PLANTILLA_CHARS:
        errores.append("output_too_long")

    usadas = _PLACEHOLDER_RE.findall(contenido)
    # Un placeholder mal formado (vacío, con espacios extraños o llaves
    # sueltas) no es una variable: es texto que el render dejaría pasar.
    resto_sin_validos = _PLACEHOLDER_RE.sub(" ", contenido)
    for match in _PLACEHOLDER_MALFORMADO_RE.finditer(resto_sin_validos):
        if "{{" in match.group(0) or "}}" in match.group(0):
            errores.append("template_variable_malformed")
            break

    permitidas = _variables_permitidas(fila, plan)
    requeridas = VARIABLES_REQUERIDAS | (
        VARIABLES_PLAN_REQUERIDAS if plan is not None else frozenset()
    )
    for variable in usadas:
        if variable not in VARIABLES_CONOCIDAS:
            errores.append("template_variable_unknown")
        elif variable not in permitidas:
            errores.append("template_variable_without_data")
    for variable in requeridas - set(usadas):
        errores.append("template_variable_missing")
    for variable in set(usadas):
        if usadas.count(variable) > 1:
            errores.append("template_variable_duplicated")

    # El texto residual es la zona del modelo: sin los `{{...}}` no puede
    # quedar ni un dato dinámico ni un hecho de la fuente.
    residual = _PLACEHOLDER_RE.sub(" ", contenido)
    if PATRON_FECHA.search(residual):
        errores.append("unauthorized_date")
    if PATRON_NUMERO.search(residual):
        errores.append("unauthorized_number")
    if PATRON_IMPORTE.search(residual) or "$" in residual:
        errores.append("unauthorized_price")
    if PATRON_EMAIL.search(residual):
        errores.append("unauthorized_email")
    if PATRON_URL.search(residual) or "www." in residual:
        errores.append("unauthorized_url")
    if PATRON_DATO_PERSONAL.search(residual):
        errores.append("personal_data")
    if PATRON_MARCO_DOCUMENTO.search(contenido):
        errores.append("document_marker_in_output")
    if PATRON_TUTEO.search(residual):
        errores.append("non_rioplatense_register")
    if PATRON_INYECCION_PLANTILLA.search(residual):
        errores.append("prompt_injection_echo")
    if PATRON_HECHO_NO_AUTORIZADO.search(residual):
        errores.append("unauthorized_fact_claim")
    if PATRON_ATRIBUCION_FACTUAL.search(residual):
        errores.append("unauthorized_fact_claim")

    for campo in CAMPOS_HECHOS_FILA:
        valor = fila.get(campo, "")
        if valor.strip() and _contiene_hecho(residual, valor):
            errores.append("source_fact_in_template")
            break
    else:
        if _contiene_fragmento_significativo(
            residual, fila.get("titulo", "")
        ):
            errores.append("source_fact_in_template")
    if (
        plan is not None
        and plan.asunto_preinscripcion.strip()
        and _contiene_hecho(residual, plan.asunto_preinscripcion)
    ):
        errores.append("source_fact_in_template")

    palabras = len(_PALABRA_RE.findall(residual))
    if palabras < MIN_PROSA_PALABRAS:
        errores.append("template_too_short")
    if palabras > MAX_PLANTILLA_PALABRAS:
        errores.append("output_too_long")

    return sorted(set(errores))


def _armar_documento(contenido: str, actividad_id: str) -> str:
    """El documento versionado: el cuerpo compuesto entre marcos fijos.

    La línea provisional y el bloque `LÍMITES` son parte del documento
    aprobado: la sección central —la que `_seccion_cuerpo` extrae para el
    render— incluye el aviso de provisionalidad, como en las demás
    plantillas de HU-012.
    """

    return (
        f"TEMPLATE_VERSION: {TEMPLATE_VERSION}\n"
        f"POLICY_STATUS: {POLICY_STATUS}\n\n"
        f"{MARCADOR_BORRADOR}\n\n"
        f"{contenido.strip()}\n\n"
        f"{_LINEA_PROVISIONAL}\n\n"
        "LÍMITES:\n"
        f"- ACTIVIDAD: {actividad_id}\n"
        "- El render es determinista por destinatario; este contenido no "
        "se entrega a un LLM.\n"
        "- Los datos dinámicos — destinatario, montos, cuotas, fechas, "
        "horarios, enlaces y datos personales — viajan como variables "
        "{{...}} y los completa el sistema desde la actividad, el plan "
        "de pago y el padrón, nunca desde el texto del modelo.\n"
        "- La plantilla se habilita sólo con la aprobación semántica y la "
        "utilitaria de esta actividad registradas en el Form de "
        "decisiones (#72); los envíos exigen además la aprobación del "
        "lote. Ninguna de ellas habilita nada por sí sola.\n"
        "- Sólo el destino habilitado — el fake explícito o el Gmail con "
        "lista de direcciones de prueba — puede entregarla.\n"
        "- La plantilla institucional definitiva queda PENDIENTE_SEU.\n"
    )


# --- Tramo de lote -----------------------------------------------------------


def _decision_registrada(
    decisiones: RegistroDecisiones,
    *,
    tipo: str,
    objeto_id: str,
    decision: str,
    rol: str,
) -> bool:
    """¿Hay una respuesta registrada para este par (tipo, objeto)?

    La validez ya se ejerció al registrar — padrón de roles, objeto
    declarado, catálogo cerrado — así que alcanza con comprobar que la
    línea existe con `resultado: registrada` y el rol que la decisión
    exige. Releer el rol acá documenta la invariante en el consumidor:
    una línea rechazada por rol nunca habilita nada.
    """

    # Import perezoso: `decisiones_form` depende de `canal_form`, que
    # depende del núcleo de interpretación — un ciclo a nivel de módulo.
    from .decisiones_form import RESULTADO_REGISTRADA

    return any(
        linea.get("tipo") == tipo
        and linea.get("objeto_id") == objeto_id
        and linea.get("decision") == decision
        and linea.get("resultado") == RESULTADO_REGISTRADA
        and linea.get("rol") == rol
        for linea in decisiones.procesadas()
    )


def renderizar_pieza_actividad(
    *,
    documento: str,
    fila: dict[str, str],
    plan: PlanPago | None,
    destinatario: DestinatarioActividad,
) -> tuple[str, str]:
    """Asunto y cuerpo del correo de un destinatario. Sin modelo.

    Sustituye cada variable por su valor de la fila o del plan; una
    variable sin valor es un error de programación — el gate de
    generación la habría rechazado — y se levanta antes de entregar una
    llave suelta al destinatario. Los medios de pago del plan, incluidos
    links o datos bancarios cuando los declare, llegan sólo acá: la
    auditoría conserva hashes.

    El asunto es el `asunto_preinscripcion` del plan cuando hay plan —
    la llave con la que la respuesta del preinscripto se asocia a la
    actividad (§4.2 del diseño de control de pagos) — y sin plan el
    título con la marca de borrador, porque ya no hay asociación de
    respuestas que proteger.
    """

    for campo in CAMPOS_FILA_OBLIGATORIOS:
        if not isinstance(fila.get(campo), str) or not fila[campo].strip():
            raise ValueError(
                "fila de actividad sin los campos que el render exige"
            )
    valores: dict[str, str] = {
        "nombre_destinatario": destinatario.nombre_destinatario.strip(),
        "actividad": fila["titulo"].strip(),
        "fecha_inicio": fila["fecha_inicio"].strip(),
        "contacto": fila["contacto"].strip(),
    }
    for variable, columna in COLUMNA_POR_VARIABLE_FILA.items():
        if fila.get(columna, "").strip():
            valores[variable] = fila[columna].strip()
    if plan is not None:
        detalle = "\n".join(
            f"- Cuota {cuota.nro}: ${_monto_texto(cuota.monto)}"
            + (
                f", vencimiento {cuota.vencimiento.isoformat()}."
                if cuota.vencimiento is not None
                else "."
            )
            for cuota in plan.cuotas
        )
        bonificadas = ", ".join(
            categoria.strip() for categoria in plan.categorias_bonificadas
        )
        valores["detalle_cuotas"] = detalle or "A confirmar por la Secretaría de Extensión"
        valores["medios_pago"] = (
            ", ".join(medio.strip() for medio in plan.medios_pago)
            or "A confirmar por la Secretaría de Extensión"
        )
        # La variable lleva la frase completa: suelta en la plantilla rinde
        # igual con categorías declaradas o sin ninguna.
        valores["bonificaciones"] = (
            f"Bonifican a: {bonificadas}."
            if bonificadas
            else "Sin bonificaciones declaradas."
        )

    cuerpo = _seccion_cuerpo(documento)
    # La sustitución va por el nombre capturado, no por el literal
    # `{{nombre}}`: una variante con espacios (`{{ nombre }}`) que el gate
    # aceptó se completa igual, y lo que no tenga valor queda como llave
    # suelta para que el control siguiente la rechace.
    cuerpo = _PLACEHOLDER_RE.sub(
        lambda match: valores.get(match.group(1), match.group(0)), cuerpo
    )
    if _PLACEHOLDER_RE.search(cuerpo):
        raise ValueError("plantilla de actividad con placeholders sin renderizar")

    if plan is not None and plan.asunto_preinscripcion.strip():
        return plan.asunto_preinscripcion.strip(), cuerpo
    return f"[{MARCADOR_BORRADOR}] {fila['titulo'].strip()}", cuerpo


def encolar_lote_actividad(
    *,
    documento: str,
    fila: dict[str, str],
    plan: PlanPago | None,
    destinatarios: Sequence[DestinatarioActividad],
    decisiones: RegistroDecisiones,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    directorio_salida: Path,
) -> ResultadoLoteActividad:
    """Encola el correo de cada destinatario hacia la entrega simulada.

    Orden de los controles — primero la autorización, después el
    registro: la plantilla exige las dos decisiones `registrada` (la
    semántica del Responsable de Gestión del Conocimiento y la utilitaria
    del Coordinador de Extensión) sobre el `plantilla_id` de este
    documento, y el lote la `apruebo_lote` utilitaria sobre su `lote_id`.
    Sin las tres, nada se encola — ni siquiera para mirar.

    Recién ahí, por cada destinatario: render determinista, `crear` por
    clave (una segunda corrida choca como `DUPLICADA`), transición
    `PENDIENTE_VALIDACION` → `ENVIO_ENCOLADO` e `ItemEnvio` en la cola.
    La entrega no pasa por acá: la hace `drenar_envios` con su candado
    de destino habilitado, como cualquier envío de HU-012.
    """

    # Constantes del catálogo de decisiones (#72): import perezoso por el
    # ciclo `decisiones_form → canal_form → interpretacion → este módulo`.
    from .decisiones_form import (
        DECISION_APRUEBO_LOTE,
        DECISION_APRUEBO_SEMANTICA,
        DECISION_APRUEBO_UTILITARIA,
        TIPO_LOTE,
        TIPO_PLANTILLA,
    )
    from .decisiones_form import (
        RegistroDecisiones as _RegistroDecisiones,
    )

    correlation_id = str(uuid.uuid4())
    log_path = _log_lote(directorio_salida)
    actividad_id = fila.get("id_actividad", "")
    plantilla_id = id_plantilla(documento, actividad_id)
    lote_id = id_lote(documento, actividad_id)

    def rechazo_lote(estado: str, error: str) -> ResultadoLoteActividad:
        _auditar_lote(
            log_path,
            correlation_id=correlation_id,
            evento="autorizacion_lote",
            estado=estado,
            resultado=error,
            actividad_id=actividad_id,
            plantilla_id=plantilla_id,
            lote_id=lote_id,
            destinatarios=len(destinatarios),
        )
        return ResultadoLoteActividad(
            estado=estado,
            plantilla_id=plantilla_id,
            lote_id=lote_id,
            log_path=log_path,
            correlation_id=correlation_id,
            items=(),
            error=error,
        )

    if not isinstance(decisiones, _RegistroDecisiones):
        return rechazo_lote("INVALIDA", "decisiones_registry_missing")
    if not actividad_id:
        return rechazo_lote("INVALIDA", "activity_id_missing")
    semantica = _decision_registrada(
        decisiones,
        tipo=TIPO_PLANTILLA,
        objeto_id=plantilla_id,
        decision=DECISION_APRUEBO_SEMANTICA,
        rol=ROL_APROBACION_SEMANTICA,
    )
    utilitaria = _decision_registrada(
        decisiones,
        tipo=TIPO_PLANTILLA,
        objeto_id=plantilla_id,
        decision=DECISION_APRUEBO_UTILITARIA,
        rol=ROL_APROBACION_UTILITARIA,
    )
    if not (semantica and utilitaria):
        return rechazo_lote("INVALIDA", "template_not_approved")
    if not _decision_registrada(
        decisiones,
        tipo=TIPO_LOTE,
        objeto_id=lote_id,
        decision=DECISION_APRUEBO_LOTE,
        rol=ROL_APROBACION_UTILITARIA,
    ):
        return rechazo_lote("INVALIDA", "batch_not_approved")

    _auditar_lote(
        log_path,
        correlation_id=correlation_id,
        evento="autorizacion_lote",
        estado="AUTORIZADA",
        resultado="ok",
        actividad_id=actividad_id,
        plantilla_id=plantilla_id,
        lote_id=lote_id,
        destinatarios=len(destinatarios),
    )

    resultados: list[ResultadoItemActividad] = []
    for destinatario in destinatarios:
        asunto, cuerpo = renderizar_pieza_actividad(
            documento=documento,
            fila=fila,
            plan=plan,
            destinatario=destinatario,
        )
        clave = clave_item_actividad(
            actividad_id=actividad_id,
            id_inscripcion=destinatario.id_inscripcion,
            documento=documento,
        )
        if not registro.crear(clave, asunto, cuerpo):
            estado_item = "DUPLICADA"
            resultado_item = "idempotency_duplicate"
        elif registro.transicionar(
            clave,
            frozenset({"PENDIENTE_VALIDACION"}),
            ESTADO_ENVIO_ENCOLADO,
        ):
            cola.encolar(
                ItemEnvio(
                    idempotency_key=clave,
                    destinatario=destinatario.email_destinatario,
                    input_hash=_hash(f"{lote_id}|{clave}"),
                )
            )
            estado_item = ESTADO_ENVIO_ENCOLADO
            resultado_item = "ok"
        else:
            # La transición es la materialización de la aprobación del
            # lote: si no se toma, el ítem no llega a la cola — visible
            # para revisión humana antes que encolado sin autorización
            # reflejada en el registro.
            estado_item = "ERROR"
            resultado_item = "enqueue_transition_failed"
        _auditar_item(
            log_path,
            correlation_id=correlation_id,
            actividad_id=actividad_id,
            plantilla_id=plantilla_id,
            lote_id=lote_id,
            clave=clave,
            estado=estado_item,
            resultado=resultado_item,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        resultados.append(
            ResultadoItemActividad(idempotency_key=clave, estado=estado_item)
        )

    if not destinatarios:
        estado_lote = "VACIO"
    elif all(item.estado == "DUPLICADA" for item in resultados):
        estado_lote = "DUPLICADA"
    else:
        estado_lote = ESTADO_ENVIO_ENCOLADO
    return ResultadoLoteActividad(
        estado=estado_lote,
        plantilla_id=plantilla_id,
        lote_id=lote_id,
        log_path=log_path,
        correlation_id=correlation_id,
        items=tuple(resultados),
    )


def correr_lote_actividad(
    *,
    documento: str,
    fila: dict[str, str],
    plan: PlanPago | None,
    destinatarios: Sequence[DestinatarioActividad],
    decisiones: RegistroDecisiones,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    destino: DestinoConfirmaciones,
    directorio_salida: Path,
) -> tuple[ResultadoLoteActividad, tuple[ResultadoEnvioEncolado, ...]]:
    """El circuito completo: encolar el lote habilitado y drenar la cola.

    El drenaje es `drenar_envios` con su candado de destino habilitado,
    igual que en recordatorios: la entrega existe sólo contra el destino
    explícito — el fake en la demostración — nunca contra un transporte
    real implícito.
    """

    resultado_lote = encolar_lote_actividad(
        documento=documento,
        fila=fila,
        plan=plan,
        destinatarios=destinatarios,
        decisiones=decisiones,
        registro=registro,
        cola=cola,
        directorio_salida=directorio_salida,
    )
    drenajes = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=directorio_salida,
    )
    return resultado_lote, drenajes


# --- Auditoría y resultados ---------------------------------------------------


def _log_generacion(directorio_salida: Path) -> Path:
    return Path(directorio_salida) / "logs" / "plantillas-actividad.jsonl"


def _log_lote(directorio_salida: Path) -> Path:
    return Path(directorio_salida) / "logs" / "lotes-actividad.jsonl"


def _linea_log(
    *,
    correlation_id: str,
    id_solicitud: str,
    generator: Generator,
    latencia_s: float,
    estado: str,
    resultado: str,
    error: str | None,
    input_hash: str | None = None,
    output_hash: str | None = None,
    plantilla_id: str | None = None,
    lote_id: str | None = None,
    con_plan: bool | None = None,
    validation_errors: list[str] | None = None,
) -> dict[str, object]:
    linea: dict[str, object] = {
        "correlation_id": correlation_id,
        "id_solicitud": id_solicitud,
        "HU": HU,
        "contract_version": CONTRACT_VERSION,
        "circuito": CIRCUITO,
        "modelo": getattr(generator, "modelo", None),
        "num_predict": _num_predict(generator),
        "prompt_version": PROMPT_VERSION,
        "latencia_s": latencia_s,
        "estado": estado,
        "resultado": resultado,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if input_hash is not None:
        linea["input_hash"] = input_hash
    if output_hash is not None:
        linea["output_hash"] = output_hash
    if plantilla_id is not None:
        linea["plantilla_id"] = plantilla_id
    if lote_id is not None:
        linea["lote_id"] = lote_id
    if con_plan is not None:
        linea["con_plan"] = con_plan
    if validation_errors:
        linea["validation_errors"] = validation_errors
    return linea


def _resultado_fuente(
    *,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    source_error_code: str,
) -> ResultadoPlantillaActividad:
    log_path = _log_generacion(directorio_salida)
    _registrar(
        log_path,
        _linea_log(
            correlation_id=correlation_id,
            id_solicitud=id_solicitud,
            generator=generator,
            latencia_s=latencia_s,
            estado="INVALIDA" if source_error_code != "source_unavailable" else "FALLIDA",
            resultado=source_error_code,
            error="La solicitud no existe o la fuente no está disponible",
        ),
    )
    return ResultadoPlantillaActividad(
        estado=(
            "INVALIDA" if source_error_code != "source_unavailable" else "FALLIDA"
        ),
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="La solicitud no existe o la fuente no está disponible",
    )


def _resultado_fallido(
    *,
    fila: dict[str, str],
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    resultado: str,
    error: str,
    validation_errors: list[str] | None = None,
) -> ResultadoPlantillaActividad:
    log_path = _log_generacion(directorio_salida)
    _registrar(
        log_path,
        _linea_log(
            correlation_id=correlation_id,
            id_solicitud=id_solicitud,
            generator=generator,
            latencia_s=latencia_s,
            estado="FALLIDA",
            resultado=resultado,
            error=error,
            input_hash=_hash_json(fila),
            validation_errors=validation_errors,
        ),
    )
    return ResultadoPlantillaActividad(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_destino(
    *,
    fila: dict[str, str],
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    destination_error_code: str,
) -> ResultadoPlantillaActividad:
    log_path = _log_generacion(directorio_salida)
    _registrar(
        log_path,
        _linea_log(
            correlation_id=correlation_id,
            id_solicitud=id_solicitud,
            generator=generator,
            latencia_s=latencia_s,
            estado="FALLIDA",
            resultado="destination_failure",
            error=destination_error_code,
            input_hash=_hash_json(fila),
        ),
    )
    return ResultadoPlantillaActividad(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="La plantilla generada no pudo guardarse",
    )


def _auditar_lote(
    log_path: Path,
    *,
    correlation_id: str,
    evento: str,
    estado: str,
    resultado: str,
    actividad_id: str,
    plantilla_id: str,
    lote_id: str,
    destinatarios: int,
) -> None:
    _registrar(
        log_path,
        {
            "correlation_id": correlation_id,
            "evento": evento,
            "HU": HU,
            "circuito": CIRCUITO,
            "actividad_id": actividad_id,
            "plantilla_id": plantilla_id,
            "lote_id": lote_id,
            "destinatarios": destinatarios,
            "estado": estado,
            "resultado": resultado,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def _auditar_item(
    log_path: Path,
    *,
    correlation_id: str,
    actividad_id: str,
    plantilla_id: str,
    lote_id: str,
    clave: str,
    estado: str,
    resultado: str,
    asunto: str,
    cuerpo: str,
) -> None:
    """Constancia por ítem encolado: hashes, nunca texto ni correo.

    `output_hash` cubre el cuerpo ya renderizado —con medios de pago y
    enlaces dentro— así que la línea prueba qué se encoló sin guardar ni
    los datos de pago ni los del destinatario.
    """

    _registrar(
        log_path,
        {
            "correlation_id": correlation_id,
            "evento": "encolado_lote",
            "HU": HU,
            "circuito": CIRCUITO,
            "actividad_id": actividad_id,
            "plantilla_id": plantilla_id,
            "lote_id": lote_id,
            "idempotency_key": clave,
            "asunto_hash": _hash(asunto),
            "output_hash": _hash(cuerpo),
            "estado": estado,
            "resultado": resultado,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


__all__ = [
    "BASE_TEMPLATE_VERSION",
    "CIRCUITO",
    "CONTRATO",
    "CAMPOS_FILA_OBLIGATORIOS",
    "DestinatarioActividad",
    "PROMPT_VERSION",
    "ResultadoItemActividad",
    "ResultadoLoteActividad",
    "ResultadoPlantillaActividad",
    "TEMPLATE_VERSION",
    "VARIABLES_REQUERIDAS",
    "clave_item_actividad",
    "correr_lote_actividad",
    "documento_desde_borrador",
    "encolar_lote_actividad",
    "id_lote",
    "id_plantilla",
    "procesar_plantilla_actividad",
    "renderizar_pieza_actividad",
]
