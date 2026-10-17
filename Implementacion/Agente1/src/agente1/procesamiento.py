"""HU-010: de una fila de actividad a un borrador de gacetilla auditado.

Este módulo es el pipeline completo de la gacetilla: leer la fila, validarla,
pedirle el texto al generador, verificar mecánicamente lo que devolvió,
guardarlo por el puerto de salida y registrar la ejecución. Cada camino
—incluidos todos los de falla— termina escribiendo exactamente una línea en
`logs/ejecuciones.jsonl`.

Decisiones que no se ven en el código:

- **Fail-closed en cada frontera.** Falta de datos, generador caído, salida que
  no cumple el contrato o destino inaccesible: en todos los casos no queda
  borrador. Nunca se produce una salida "parcial" o "mejor que nada", porque el
  destinatario del borrador es una comunicación institucional.
- **La validación de la salida es mecánica, no de calidad.** `_validar_salida`
  comprueba estructura y que los hechos coincidan con la fuente; no juzga si el
  texto está bien escrito. Eso lo decide la SEU en la revisión humana.
- **El log guarda hashes, no contenido.** `input_hash` y `output_hash` permiten
  probar después que un borrador salió de una fila determinada, sin copiar
  datos de la actividad ni el texto generado a un segundo lugar.
- **La procedencia de un insumo de agente se declara, no se infiere.** El
  llamador que despacha un insumo de la pestaña (ADR 0008) pasa una
  `ProcedenciaInsumo` con puros identificadores opacos: la línea de auditoría
  suma el bloque `procedencia` y el borrador lleva una línea visible de
  origen (productor, tipo, flag de productor provisional, `cargado_por` y
  `correlation_id` del insumo) entre la marca `BORRADOR — NO PUBLICAR` y la
  pieza. Una solicitud del canal de la SEU no la declara y el artefacto queda
  igual que siempre.
- **Los códigos de error se filtran contra una allowlist**
  (`SOURCE_ERROR_CODES`, `DESTINATION_ERROR_CODES`) antes de registrarse: un
  adapter no puede inyectar texto arbitrario en la auditoría.
- **El estado de éxito se llama `PENDIENTE_VALIDACION`, no `OK`.** Generar el
  borrador no completa el trabajo: recién lo deja listo para revisión humana.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Protocol

from .destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
    ReferenciaBorrador,
)
from .fuentes import (
    COLUMNAS_ACTIVIDADES_V2,
    CsvFuenteSolicitudes,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)
from .gacetillas import (
    MAX_BORRADOR_CHARS as _MAX_BORRADOR_CHARS,
)
from .gacetillas import (
    TIPO_DIFUSION,
    TipoGacetillaError,
    cargar_entrada,
    cargar_forma,
    fecha_larga,
    validar_pieza,
)
from .gacetillas import (
    campos_obligatorios as _campos_obligatorios,
)
from .gacetillas import (
    nombre_doc as _nombre_doc_gacetilla,
)
from .gacetillas import (
    normalizar_texto as _normalizar_texto,
)
from .gacetillas import (
    renderizar as _renderizar_pieza,
)
from .presupuesto import (
    MENSAJE_PRESUPUESTO_AGOTADO,
    RESULTADO_PRESUPUESTO_AGOTADO,
    PresupuestoAgotadoError,
)
from .registro_auditoria import escribir_registro

HU = "HU-010"
# Alias histórico: las pruebas y el resto del módulo nombran `_fecha_larga`. La
# implementación vive en `gacetillas` para que el renderer y el gate tengan una
# sola definición del formato de fecha del corpus.
_fecha_larga = fecha_larga
# La forma declarada de difusión es la primera que existe (ADR 0012). De ella
# salen el prompt vigente y el nombre del contrato de entrada; del contrato de
# entrada salen los campos obligatorios. Ningún texto institucional fijo vive
# en este módulo: el marco lo copia `gacetillas.renderizar` desde la forma.
_FORMA_DIFUSION = cargar_forma(TIPO_DIFUSION)
# Estas tres versiones se escriben en cada línea del log. Si alguna cambia hay
# que subirle el número: es lo que permite explicar, meses después, por qué dos
# ejecuciones de la misma fila dieron textos distintos.
PROMPT_VERSION = str(_FORMA_DIFUSION["salida_modelo"]["prompt_version"])
CONTRACT_VERSION = str(cargar_entrada(TIPO_DIFUSION)["x-contract-version"])
RENDERER_VERSION = "gacetilla_forma_declarada_v4"
MAX_BORRADOR_CHARS = _MAX_BORRADOR_CHARS
# Prefijo del nombre del Doc del borrador. El título del Doc no lleva la marca
# completa (`BORRADOR_MARKER`, que va en el cuerpo): lleva este prefijo, para
# que un borrador se reconozca al mirarlo desde Drive, donde el cuerpo no se ve.
PREFIJO_BORRADOR_DOC = "BORRADOR — "
# Límites de extensión de la prosa de la gacetilla. Son técnicos y
# provisionales (DEF-A1-007): calibrados contra el corpus de correos reales
# FIE Informa (Corpus-Comunicaciones-Reales-SEU-2026-09-30), donde la bajada
# de una pieza ronda las 15-20 palabras y el cuerpo es un párrafo corto.
# La prosa no puede llevar datos concretos (números, fechas, correos,
# enlaces, montos): esos van en las secciones de hechos y los pone el
# renderer desde la fila.
MAX_CUERPO_WORDS = 120
MAX_BAJADA_WORDS = 40
PATRON_PROSA_SIN_DATOS = re.compile(r"\d|@|https?://|www\.|\$")
CONTRATO_ENTRADA = json.loads(
    files("agente1")
    .joinpath("contracts", "gacetilla_input_v2.schema.json")
    .read_text(encoding="utf-8")
)
CAMPOS_OBLIGATORIOS = tuple(CONTRATO_ENTRADA["required"])
ENCABEZADOS_OBLIGATORIOS = (
    "## TÍTULO",
    "## DATOS DE LA ACTIVIDAD",
    "## CONTACTO",
    "## BAJADA",
    "## CUERPO",
)
PATRON_BORRADOR = re.compile(
    r"\A## TÍTULO\n(?P<titulo>.+?)\n\n"
    r"## DATOS DE LA ACTIVIDAD\n(?P<datos>.+?)\n\n"
    r"## CONTACTO\n(?P<contacto>.+?)\n\n"
    r"## BAJADA\n(?P<bajada>.+?)\n\n"
    r"## CUERPO\n(?P<cuerpo>.+)\Z",
    flags=re.DOTALL,
)
PATRON_DATOS = re.compile(
    r"\AFecha: (?P<fecha>[^\n]+)\n"
    r"Organiza: (?P<organiza>[^\n]+)"
    r"(?:\nLugar: (?P<lugar>[^\n]+))?\Z"
)
ID_SOLICITUD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
# Allowlists de códigos de error registrables. Un adapter que devuelva un
# código fuera de estos conjuntos se registra como fallo genérico
# (`source_unavailable` / `destination_unavailable`): la auditoría sólo admite
# vocabulario conocido, para que sea analizable y para que ningún mensaje de
# excepción termine copiado en el log.
SOURCE_ERROR_CODES = frozenset(
    {
        "sheets_headers_invalid",
        "sheets_row_invalid",
        "source_contract_invalid",
        "source_duplicate_id",
        "source_id_mismatch",
        "source_request_invalid",
        "source_request_not_found",
        "source_unavailable",
        "workspace_auth_denied",
        "workspace_auth_unavailable",
        "workspace_rate_limited",
        "workspace_response_invalid",
        "workspace_response_too_large",
        "workspace_source_not_found",
        "workspace_unavailable",
    }
)
DESTINATION_ERROR_CODES = frozenset(
    {
        "destination_contract_invalid",
        "destination_unavailable",
        "docs_auth_denied",
        "docs_rate_limited",
        "docs_response_invalid",
        "docs_response_too_large",
        "docs_unavailable",
        "docs_update_failed_orphaned",
        "drive_auth_denied",
        "drive_rate_limited",
        "drive_request_too_large",
        "drive_resource_not_found",
        "drive_response_invalid",
        "drive_response_too_large",
        "drive_unavailable",
        "workspace_auth_unavailable",
    }
)


class Generator(Protocol):
    """Puerto del generador de texto.

    `modelo` y `num_predict` no son detalles internos del adapter: se registran
    en el log, porque un borrador sólo es reproducible si consta con qué modelo
    y con qué límite de tokens se produjo.
    """

    modelo: str
    num_predict: int | None

    def generar(self, prompt: str) -> str: ...


class FakeGenerator:
    """Generador determinista: devuelve siempre el texto que se le pasó.

    Existe para que las pruebas y las matrices de regresión ejerciten el
    pipeline completo —validación, destino, auditoría— sin depender de un
    modelo instalado ni de su variabilidad. Se identifica como
    `fake-determinista` en el log, así una evidencia producida con él nunca se
    confunde con una corrida real contra un modelo.
    """

    modelo = "fake-determinista"
    num_predict = None

    def __init__(self, respuesta: str) -> None:
        self._respuesta = respuesta

    def generar(self, prompt: str) -> str:
        return self._respuesta


@dataclass(frozen=True)
class ResultadoProceso:
    """Salida del pipeline.

    `borrador_path` viene en `None` cuando no hubo borrador (falla) y también
    cuando el destino es remoto y no dejó archivo local; para saber dónde quedó
    en ese caso hay que mirar `referencia_borrador`.
    """

    estado: str
    borrador_path: Path | None
    log_path: Path
    correlation_id: str
    error: str | None = None
    referencia_borrador: ReferenciaBorrador | None = None


@dataclass(frozen=True)
class ProcedenciaInsumo:
    """De dónde salió el pedido cuando no vino del canal de la SEU.

    Una gacetilla también puede nacer de un insumo de agente entregado en la
    pestaña «Insumos de agentes» (ADR 0008). Cuando el llamador declara esa
    procedencia, el pipeline la registra en la línea de auditoría y la estampa
    en el propio borrador, debajo de la marca `BORRADOR — NO PUBLICAR`: qué
    agente la produjo, con qué tipo de payload, con qué `data_origin` (de
    donde sale el flag de productor provisional) y los identificadores opacos
    que la vinculan con la fila de origen (`correlation_id` del envelope,
    `cargado_por` de la celda).

    Todos los campos portan identificadores opacos o vocabulario cerrado del
    envelope ya validado: ningún dato libre del insumo llega ni a la
    auditoría ni al documento.
    """

    producer: str
    payload_type: str
    data_origin: str
    productor_provisional: bool
    insumo_correlation_id: str
    cargado_por: str


def procesar_fila_csv(
    *,
    csv_path: Path,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    tipo: str = TIPO_DIFUSION,
) -> ResultadoProceso:
    """Atajo para el camino local: CSV como fuente y Markdown como destino."""

    return procesar_solicitud(
        fuente=CsvFuenteSolicitudes(csv_path),
        id_solicitud=id_solicitud,
        directorio_salida=directorio_salida,
        generator=generator,
        tipo=tipo,
    )


def procesar_solicitud(
    *,
    fuente: FuenteSolicitudes,
    id_solicitud: str,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
    procedencia: ProcedenciaInsumo | None = None,
    tipo: str = TIPO_DIFUSION,
) -> ResultadoProceso:
    """Ejecuta el pipeline de gacetilla para una solicitud.

    Devuelve siempre un `ResultadoProceso` y nunca propaga excepciones del
    generador, de la fuente ni del destino: cada falla se traduce a un estado y
    a una línea de auditoría. Estados posibles: `PENDIENTE_VALIDACION` (hay
    borrador), `INCOMPLETA` (faltan datos obligatorios), `INVALIDA` (la
    solicitud no existe, el id no es válido o el tipo no se produce por este
    pipeline) y `FALLIDA` (falló el generador, la salida no cumplió el
    contrato, o falló el destino).

    `tipo` es el tipo de gacetilla declarado (ADR 0012). Este pipeline produce
    los tipos cuya forma declara salida de clase `ficha_actividad`, hoy sólo
    difusión de actividad; los otros seis se producen por
    `gacetillas.confirmar_pieza` o `gacetillas.generar_pieza`. El tipo selecciona
    el contrato de entrada, la forma declarada y el gate.

    El `correlation_id` se genera antes de tocar nada para que hasta el fallo
    más temprano quede correlacionado con el resto de la evidencia.

    `procedencia` sólo lo declara el camino de insumos de agentes (ADR 0008):
    con él, la línea de auditoría suma el bloque `procedencia` y el borrador
    lleva una línea visible de origen bajo la marca `BORRADOR — NO PUBLICAR`.
    Una solicitud del canal de la SEU no lo declara y el artefacto queda igual
    que siempre.
    """

    correlation_id = str(uuid.uuid4())
    inicio_fuente = time.perf_counter()
    try:
        forma = cargar_forma(tipo)
    except TipoGacetillaError:
        return _resultado_tipo_invalido(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            tipo=tipo,
            procedencia=procedencia,
        )
    clase_salida = str((forma.get("salida_modelo") or {}).get("clase"))
    if clase_salida != "ficha_actividad":
        return _resultado_tipo_invalido(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            tipo=tipo,
            procedencia=procedencia,
        )
    try:
        _validar_id_solicitud(id_solicitud)
    except (TypeError, ValueError):
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_request_invalid",
            procedencia=procedencia,
        )
    try:
        fila = fuente.obtener(id_solicitud)
    except FuenteSolicitudesError as error_fuente:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=error_fuente.code,
            procedencia=procedencia,
        )
    except Exception:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code="source_unavailable",
            procedencia=procedencia,
        )
    fila, source_error_code = _normalizar_fila_fuente(fila, id_solicitud)
    if source_error_code is not None:
        return _resultado_fuente_fallida(
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_fuente, 6),
            source_error_code=source_error_code,
            procedencia=procedencia,
        )
    # Control previo a la generación: si falta un campo obligatorio no se
    # llama al modelo. Además de evitar una comunicación incompleta, ahorra el
    # costo de una generación que igual se descartaría. Los campos v2 nuevos
    # (fecha_fin, fecha_limite_inscripcion, hora, modalidad, duracion_horas,
    # enlace_inscripcion) no están en CAMPOS_OBLIGATORIOS: la planilla no
    # decide qué exige cada pieza, y este contrato no los declara obligatorios
    # —la SEU todavía no fijó si deben exigirse. Tampoco `lugar`: hay
    # actividades sin sede definida.
    faltantes = [campo for campo in _campos_obligatorios(tipo) if not fila.get(campo, "").strip()]
    if faltantes:
        # El nombre de los campos faltantes sí va al log: son nombres de
        # columna del contrato, no datos de la actividad.
        error = f"Campos obligatorios faltantes: {', '.join(faltantes)}"
        log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
        _registrar(
            log_path,
            _con_procedencia(
                {
                    "correlation_id": correlation_id,
                    "id_solicitud": id_solicitud,
                    "HU": HU,
                    "contract_version": CONTRACT_VERSION,
                    "tipo_gacetilla": tipo,
                    "forma_version": str(forma["schema_version"]),
                    "modelo": generator.modelo,
                    "num_predict": _num_predict(generator),
                    "prompt_version": PROMPT_VERSION,
                    "latencia_s": 0.0,
                    "estado": "INCOMPLETA",
                    "resultado": "datos_incompletos",
                    "error": error,
                    "input_hash": _hash_json(fila),
                    "output_hash": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                procedencia,
            ),
        )
        return ResultadoProceso(
            estado="INCOMPLETA",
            borrador_path=None,
            log_path=log_path,
            correlation_id=correlation_id,
            error=error,
        )

    inicio = time.perf_counter()
    prompt = _construir_prompt(fila)
    try:
        contenido_generado = generator.generar(prompt)
    # Ver DEF-A1-013: el agotamiento de presupuesto se registra aparte porque
    # se corrige cambiando la configuración, no el prompt ni el modelo.
    except PresupuestoAgotadoError:
        latencia_s = round(time.perf_counter() - inicio, 6)
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado=RESULTADO_PRESUPUESTO_AGOTADO,
            error=MENSAJE_PRESUPUESTO_AGOTADO,
            procedencia=procedencia,
        )
    except Exception:
        latencia_s = round(time.perf_counter() - inicio, 6)
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="error_generacion",
            error="Falló la generación del borrador",
            procedencia=procedencia,
        )
    latencia_s = round(time.perf_counter() - inicio, 6)
    contenido = contenido_generado.strip() if isinstance(contenido_generado, str) else ""
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
            procedencia=procedencia,
        )
    validation_errors = _validar_salida(contenido, fila)
    if validation_errors:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_no_conforme",
            error="La salida generada no cumple el contrato mínimo",
            validation_errors=validation_errors,
            procedencia=procedencia,
        )

    # El artefacto durable es el correo en forma FIE Informa, no la ficha:
    # la ficha validada es la entrada del renderer determinista que arma el
    # mail con los hechos de la fila (mismo patrón que los posts).
    match_borrador = PATRON_BORRADOR.fullmatch(contenido)
    assert match_borrador is not None  # garantizado por _validar_salida
    contenido_mail = _renderizar_mail(fila, match_borrador)
    errores_render = _validar_render_mail(contenido_mail, fila)
    if errores_render:
        return _resultado_fallido(
            fila=fila,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            resultado="salida_no_conforme",
            error="La salida generada no cumple el contrato mínimo",
            validation_errors=errores_render,
            procedencia=procedencia,
        )

    # La marca y la procedencia se anteponen recién acá, después de que la
    # salida pasó el contrato: nada que no haya sido validado llega a tener
    # forma de borrador. La línea de procedencia queda entre la marca y la
    # pieza, como metadato visible del documento: no forma parte del correo
    # que una persona copiaría para difundir.
    borrador = (
        f"{BORRADOR_MARKER}{_bloque_procedencia(procedencia)}{contenido_mail}\n"
    )
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    # El nombre visible del Doc sigue la convención institucional del corpus
    # FIE Informa («Fie informa D-M <título>»), con la fecha de generación. El
    # cuerpo del correo no lleva esa línea: el nombre vive en el título del
    # documento y sólo lo aplica el destino remoto.
    nombre_doc = _nombre_doc(fila, _fecha_generacion())
    try:
        referencia_borrador = destino_efectivo.guardar(
            id_solicitud, borrador, nombre=nombre_doc
        )
        if not isinstance(referencia_borrador, ReferenciaBorrador):
            raise DestinoBorradoresError("destination_contract_invalid")
    except DestinoBorradoresError as error_destino:
        return _resultado_destino_fallido(
            fila=fila,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            borrador=borrador,
            destination_error_code=error_destino.code,
            reconciliation_ref_hash=error_destino.reconciliation_ref_hash,
            procedencia=procedencia,
        )
    except Exception:
        return _resultado_destino_fallido(
            fila=fila,
            directorio_salida=directorio_salida,
            generator=generator,
            correlation_id=correlation_id,
            latencia_s=latencia_s,
            borrador=borrador,
            destination_error_code="destination_unavailable",
            reconciliation_ref_hash=None,
            procedencia=procedencia,
        )

    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        _con_procedencia(
            {
                "correlation_id": correlation_id,
                "id_solicitud": id_solicitud,
                "HU": HU,
                "contract_version": CONTRACT_VERSION,
                "tipo_gacetilla": tipo,
                "forma_version": str(forma["schema_version"]),
                "modelo": generator.modelo,
                "num_predict": _num_predict(generator),
                "prompt_version": PROMPT_VERSION,
                "renderer_version": RENDERER_VERSION,
                "latencia_s": latencia_s,
                "estado": "PENDIENTE_VALIDACION",
                "resultado": "borrador_generado",
                "error": None,
                "input_hash": _hash_json(fila),
                "output_hash": _hash_texto(borrador),
                "destination_type": referencia_borrador.tipo,
                "borrador_ref_hash": _hash_texto(referencia_borrador.referencia),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            procedencia,
        ),
    )
    return ResultadoProceso(
        estado="PENDIENTE_VALIDACION",
        borrador_path=referencia_borrador.path,
        log_path=log_path,
        correlation_id=correlation_id,
        referencia_borrador=referencia_borrador,
    )


def _validar_id_solicitud(id_solicitud: str) -> None:
    if not isinstance(id_solicitud, str) or not ID_SOLICITUD_RE.fullmatch(id_solicitud):
        raise ValueError(
            "id_solicitud inválido: use entre 1 y 128 caracteres alfanuméricos, "
            "guion o guion bajo"
        )


def _con_procedencia(
    registro: dict[str, object], procedencia: ProcedenciaInsumo | None
) -> dict[str, object]:
    """Suma el bloque `procedencia` a la línea de auditoría cuando aplica.

    Sólo entran identificadores opacos y vocabulario cerrado del envelope:
    `insumo_correlation_id` y `cargado_por` enlazan la ejecución con la fila
    de la pestaña sin copiar ningún dato del insumo.
    """

    if procedencia is not None:
        registro["procedencia"] = {
            "origen": "insumo_agente",
            "producer": procedencia.producer,
            "payload_type": procedencia.payload_type,
            "data_origin": procedencia.data_origin,
            "productor_provisional": procedencia.productor_provisional,
            "insumo_correlation_id": procedencia.insumo_correlation_id,
            "cargado_por": procedencia.cargado_por,
        }
    return registro


def _bloque_procedencia(procedencia: ProcedenciaInsumo | None) -> str:
    """Línea visible de procedencia, entre la marca de borrador y la pieza.

    Es lo que lee quien revisa el documento: el origen del insumo, si lo
    cargó un productor provisional declarado y las claves opacas que lo
    vinculan con la fila de la pestaña y con la línea de auditoría.
    """

    if procedencia is None:
        return ""
    provisional = "sí" if procedencia.productor_provisional else "no"
    return (
        f"[Procedencia: insumo de {procedencia.producer}, "
        f"tipo {procedencia.payload_type}; "
        f"productor provisional: {provisional}; "
        f"cargado_por: {procedencia.cargado_por}; "
        f"correlation_id: {procedencia.insumo_correlation_id}.]\n\n"
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
    procedencia: ProcedenciaInsumo | None = None,
) -> ResultadoProceso:
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro: dict[str, object] = {
        "correlation_id": correlation_id,
        "id_solicitud": id_solicitud,
        "HU": HU,
        "contract_version": CONTRACT_VERSION,
        "modelo": generator.modelo,
        "num_predict": _num_predict(generator),
        "prompt_version": PROMPT_VERSION,
        "latencia_s": latencia_s,
        "estado": "FALLIDA",
        "resultado": resultado,
        "error": error,
        "input_hash": _hash_json(fila),
        "output_hash": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if validation_errors is not None:
        registro["validation_errors"] = validation_errors
    _registrar(log_path, _con_procedencia(registro, procedencia))
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_fuente_fallida(
    *,
    # `id_solicitud` entra como `object` a propósito: este camino también cubre
    # el caso en que el id no es siquiera un string válido, y nunca se escribe
    # tal cual en el log sino como hash (ver abajo).
    id_solicitud: object,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    source_error_code: str,
    procedencia: ProcedenciaInsumo | None = None,
) -> ResultadoProceso:
    if source_error_code not in SOURCE_ERROR_CODES:
        source_error_code = "source_unavailable"
    # Se distingue "la solicitud está mal o no existe" (INVALIDA, no se
    # reintenta: hay que corregir el origen) de "la fuente falló" (FALLIDA,
    # puede reintentarse cuando el servicio vuelva). La diferencia importa para
    # decidir qué hacer con la solicitud, no sólo para el reporte.
    invalida = source_error_code in {
        "source_request_invalid",
        "source_request_not_found",
    }
    estado = "INVALIDA" if invalida else "FALLIDA"
    resultado = "source_invalid" if invalida else "source_failure"
    error = (
        "Solicitud inválida o inexistente"
        if invalida
        else "Falló la lectura de la fuente"
    )
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        _con_procedencia(
            {
                "correlation_id": correlation_id,
                # Cuando la fuente falla no se pudo confirmar que el id
                # corresponda a una solicitud real, así que se registra su hash
                # en vez del valor: un id inválido puede venir de afuera y no
                # debe quedar escrito literal en la auditoría.
                "id_solicitud": None,
                "id_solicitud_hash": (
                    _hash_texto(id_solicitud)
                    if isinstance(id_solicitud, str)
                    else None
                ),
                "HU": HU,
                "contract_version": CONTRACT_VERSION,
                "modelo": generator.modelo,
                "num_predict": _num_predict(generator),
                "prompt_version": PROMPT_VERSION,
                "latencia_s": latencia_s,
                "estado": estado,
                "resultado": resultado,
                "error": error,
                "source_error_code": source_error_code,
                "input_hash": None,
                "output_hash": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            procedencia,
        ),
    )
    return ResultadoProceso(
        estado=estado,
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_tipo_invalido(
    *,
    id_solicitud: object,
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    tipo: str,
    procedencia: ProcedenciaInsumo | None = None,
) -> ResultadoProceso:
    """El tipo no esta declarado o no se produce por el pipeline de actividad.

    Es `INVALIDA` y no `FALLIDA` porque no hay nada que reintentar: la
    correccion es declarar un tipo del contrato cerrado o usar el seam del
    tipo. El `id_solicitud` se registra como hash, igual que en el resto de los
    caminos que no pudieron confirmar que la solicitud exista.
    """

    estado = "INVALIDA"
    resultado = "tipo_no_declarado"
    error = "El tipo de gacetilla no se produce por este pipeline"
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    _registrar(
        log_path,
        _con_procedencia(
            {
                "correlation_id": correlation_id,
                "id_solicitud": None,
                "id_solicitud_hash": (
                    _hash_texto(id_solicitud)
                    if isinstance(id_solicitud, str)
                    else None
                ),
                "HU": HU,
                "contract_version": CONTRACT_VERSION,
                "tipo_gacetilla": tipo if isinstance(tipo, str) else None,
                "modelo": generator.modelo,
                "num_predict": _num_predict(generator),
                "prompt_version": PROMPT_VERSION,
                "latencia_s": latencia_s,
                "estado": estado,
                "resultado": resultado,
                "error": error,
                "input_hash": None,
                "output_hash": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            procedencia,
        ),
    )
    return ResultadoProceso(
        estado=estado,
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _resultado_destino_fallido(
    *,
    fila: dict[str, str],
    directorio_salida: Path,
    generator: Generator,
    correlation_id: str,
    latencia_s: float,
    borrador: str,
    destination_error_code: str,
    reconciliation_ref_hash: str | None,
    procedencia: ProcedenciaInsumo | None = None,
) -> ResultadoProceso:
    if destination_error_code not in DESTINATION_ERROR_CODES:
        destination_error_code = "destination_unavailable"
        reconciliation_ref_hash = None
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"
    registro: dict[str, object] = {
        "correlation_id": correlation_id,
        "id_solicitud": None,
        "id_solicitud_hash": _hash_texto(fila["id_actividad"]),
        "HU": HU,
        "contract_version": CONTRACT_VERSION,
        "modelo": generator.modelo,
        "num_predict": _num_predict(generator),
        "prompt_version": PROMPT_VERSION,
        "latencia_s": latencia_s,
        "estado": "FALLIDA",
        "resultado": "destination_failure",
        "error": "Falló la persistencia del borrador",
        "destination_error_code": destination_error_code,
        "input_hash": _hash_json(fila),
        "output_hash": _hash_texto(borrador),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if reconciliation_ref_hash is not None:
        registro["reconciliation_ref_hash"] = reconciliation_ref_hash
    _registrar(log_path, _con_procedencia(registro, procedencia))
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="Falló la persistencia del borrador",
    )


def _normalizar_fila_fuente(
    fila: object, id_solicitud: str
) -> tuple[dict[str, str], str | None]:
    """Lleva lo que devolvió el adapter a la forma canónica del contrato.

    Devuelve `(fila, None)` o `({}, codigo_de_error)` en lugar de levantar: el
    llamador necesita registrar el código, no manejar una excepción más.

    El control de `source_id_mismatch` parece redundante —se pidió ese id— pero
    protege contra un adapter que devuelva la fila equivocada: sin él, un
    borrador podría construirse con los datos de otra actividad.
    """

    if not isinstance(fila, dict) or any(
        campo not in fila for campo in CAMPOS_OBLIGATORIOS
    ):
        return {}, "source_contract_invalid"
    fila_canonica: dict[str, str] = {}
    for campo in COLUMNAS_ACTIVIDADES_V2:
        valor = fila.get(campo, "")
        if not isinstance(valor, str):
            return {}, "source_contract_invalid"
        fila_canonica[campo] = valor
    if fila_canonica["id_actividad"] != id_solicitud:
        return {}, "source_id_mismatch"
    return fila_canonica, None


# `DEF-A1-014`: la plantilla v2 mostraba siempre la línea `Lugar:` en la
# estructura y en el ejemplo, con la excepción escrita como una anotación
# dentro del placeholder. Un modelo de 3B copia la forma que ve: para las filas
# sin lugar emitía `Lugar:` sin valor, `PATRON_DATOS` lo rechazaba y el
# resultado quedaba registrado como `data_structure` de manera reproducible.
# Por eso la línea deja de estar presente cuando no corresponde, en los dos
# lugares donde el modelo la puede copiar, y la regla se dice en positivo.
REGLA_LUGAR_INFORMADO = (
    "- Esta actividad informa lugar: el bloque DATOS DE LA ACTIVIDAD lleva "
    "exactamente tres líneas."
)
REGLA_LUGAR_AUSENTE = (
    "- Esta actividad NO informa lugar: el bloque DATOS DE LA ACTIVIDAD lleva "
    "exactamente dos líneas y no incluye ninguna línea `Lugar:`. Escribir "
    "`Lugar:` sin valor es un error de formato."
)


def _lineas_de_lugar(fila: dict[str, str]) -> dict[str, str | None]:
    """Qué dice la plantilla sobre el lugar, según lo que traiga la fila.

    `None` significa que la línea entera se borra, con su salto: dejarla vacía
    volvería a mostrarle al modelo el hueco que rellenaba.
    """

    if fila.get("lugar", "").strip():
        return {
            "regla_lugar": REGLA_LUGAR_INFORMADO,
            "linea_lugar_estructura": "Lugar: <lugar exacto>",
            "linea_lugar_ejemplo": "Lugar: Aula Ficticia",
        }
    return {
        "regla_lugar": REGLA_LUGAR_AUSENTE,
        "linea_lugar_estructura": None,
        "linea_lugar_ejemplo": None,
    }


def _construir_prompt(fila: dict[str, str]) -> str:
    plantilla = (
        files("agente1")
        .joinpath("prompts", f"{PROMPT_VERSION}.txt")
        .read_text(encoding="utf-8")
    )
    sustituciones: dict[str, str | None] = {
        **_lineas_de_lugar(fila),
        "datos_fuente": "\n".join(
            f"{campo}: {valor}" for campo, valor in fila.items()
        ),
    }
    for marcador, valor in sustituciones.items():
        if valor is None:
            plantilla = plantilla.replace("{" + marcador + "}\n", "")
        else:
            plantilla = plantilla.replace("{" + marcador + "}", valor)
    return plantilla


def _registrar(path: Path, registro: dict[str, object]) -> None:
    # Append a un JSONL, una línea por ejecución: el archivo se puede analizar
    # incrementalmente y ninguna corrida pisa a la anterior. La escritura suma
    # `version_agente` y el hash del manifest (#93); `sort_keys` deja las claves
    # en orden estable para poder comparar (o hashear) evidencias.
    escribir_registro(path, registro)


def _hash_json(valor: dict[str, str]) -> str:
    serializado = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_texto(serializado)


def _hash_texto(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _validar_salida(contenido: str, fila: dict[str, str]) -> list[str]:
    """Contrato mecánico mínimo de la gacetilla generada.

    Verifica dos cosas distintas: que el documento tenga la estructura pactada
    (las cinco secciones, en orden) y que los hechos que declara —título,
    fecha, organiza, lugar, contacto— sean exactamente los de la fila. El
    objetivo es detectar que el modelo haya inventado o alterado un dato, que
    es la falla con consecuencias institucionales; no evaluar la redacción.

    Las comparaciones pasan por `_normalizar_texto` (sin acentos, sin
    mayúsculas, espacios colapsados) porque el modelo tiende a reescribir con
    otra capitalización o acentuación, y eso no es invención de un hecho.

    Devuelve una lista de códigos, no un booleano, para que el log diga
    exactamente qué falló. Algunas verificaciones cortan y devuelven de
    inmediato: sin estructura válida, el resto de los controles no tendría
    sobre qué operar.
    """

    errores: list[str] = []
    if len(contenido) > MAX_BORRADOR_CHARS:
        errores.append("length_out_of_range")
        return errores
    if any(contenido.count(encabezado) != 1 for encabezado in ENCABEZADOS_OBLIGATORIOS):
        errores.append("document_structure")
        return errores
    match = PATRON_BORRADOR.fullmatch(contenido)
    if match is None:
        errores.append("document_structure")
        return errores

    titulo = _normalizar_texto(match.group("titulo").strip())
    contacto = _normalizar_texto(match.group("contacto").strip())
    bajada = match.group("bajada").strip()
    cuerpo = match.group("cuerpo").strip()
    if titulo != _normalizar_texto(fila["titulo"]):
        errores.append("title_mismatch")
    datos_match = PATRON_DATOS.fullmatch(match.group("datos").strip())
    if datos_match is None:
        errores.append("data_structure")
        return errores
    if _normalizar_texto(datos_match.group("fecha")) != _normalizar_texto(
        fila["fecha_inicio"]
    ):
        errores.append("date_mismatch")
    if _normalizar_texto(datos_match.group("organiza")) != _normalizar_texto(
        fila["organiza"]
    ):
        errores.append("organizer_mismatch")
    # El lugar es opcional en la fuente, así que se controla en los dos
    # sentidos: si la fila no trae lugar, el borrador tampoco puede traerlo
    # (sería un dato inventado); si la fila lo trae, tiene que estar y coincidir.
    lugar = fila.get("lugar", "").strip()
    lugar_generado = datos_match.group("lugar")
    if not lugar and lugar_generado is not None:
        errores.append("unexpected_place")
    elif lugar and lugar_generado is None:
        errores.append("place_missing")
    elif lugar and _normalizar_texto(lugar_generado or "") != _normalizar_texto(lugar):
        errores.append("place_mismatch")
    if contacto != _normalizar_texto(fila["contacto"]):
        errores.append("contact_mismatch")
    if len(bajada.split()) > MAX_BAJADA_WORDS:
        errores.append("bajada_too_long")
    if len(cuerpo.split()) > MAX_CUERPO_WORDS:
        errores.append("cuerpo_too_long")
    # El cuerpo es un párrafo corto (varias oraciones permitidas) pero tiene
    # que cerrar con puntuación: un corte de generación deja el borrador
    # truncado y nadie debería tener que descubrirlo en el mail final.
    if re.search(r"[.!?]$", cuerpo) is None:
        errores.append("cuerpo_sentence_invalid")
    # La prosa no puede llevar datos concretos: cualquier número, correo,
    # enlace o monto que el correo necesite lo agrega el renderer desde la
    # fila, no el modelo. Esto elimina de raíz la invención de hechos en la
    # parte creativa.
    if PATRON_PROSA_SIN_DATOS.search(bajada) or PATRON_PROSA_SIN_DATOS.search(cuerpo):
        errores.append("unauthorized_fact_in_prose")
    return errores


# Partes institucionales de difusión: se leen de la forma declarada, no se
# escriben acá. Ningún texto fijo del canal vive en el código (ADR 0012).
_FIRMA_INSTITUCIONAL = str(_FORMA_DIFUSION["firmante"])
_PIE_DIFUSION = str(_FORMA_DIFUSION["pie"])


def _fecha_generacion() -> date:
    """Día en que se generó el borrador, para el nombre del Doc.

    Aislado en una función para poder fijarlo en las pruebas: el nombre del
    documento es el único artefacto del renderer que depende de la fecha de
    generación y no de un dato de la fila.
    """

    return datetime.now().date()


def _nombre_doc(fila: dict[str, str], generado_en: date) -> str:
    """Nombre del Doc del borrador, según la convención del corpus FIE Informa.

    «BORRADOR — Fie informa D-M <título>» con la fecha de generación en
    día-mes y el título de la fila. El prefijo va primero porque el nombre es
    lo único que se ve desde Drive. La convención «Fie informa D-M» la declara
    la forma del tipo; el cuerpo del correo no lleva esta línea.
    """

    return f"{PREFIJO_BORRADOR_DOC}{_nombre_doc_gacetilla(TIPO_DIFUSION, fila, generado_en)}"


def _renderizar_mail(fila: dict[str, str], ficha: "re.Match[str]") -> str:
    """Arma el correo FIE Informa a partir de la ficha validada y la fila.

    Delega en el renderer único de `gacetillas`: el marco (asunto, etiquetas,
    pie y firmante) sale de la forma declarada de difusión y los hechos se
    copian de la fila. Acá no queda ninguna frase institucional literal: la
    antigua línea fija de invitación se retiró (ADR 0012) y la introducción la
    aporta la prosa del modelo en `bajada` y `cuerpo`.
    """

    secciones = ficha.groupdict()
    return _renderizar_pieza(
        TIPO_DIFUSION,
        fila,
        prosa={
            "bajada": secciones["bajada"].strip(),
            "cuerpo": secciones["cuerpo"].strip(),
        },
    )


def _validar_render_mail(contenido_mail: str, fila: dict[str, str]) -> list[str]:
    """Gate de la pieza renderizada: núcleo común más reglas de difusión.

    Delega en `gacetillas.validar_pieza`, que compara la pieza contra los hechos
    de la fila. El código histórico de hecho perdido se conserva como
    `renderer_fact_missing` para que la auditoría y las regresiones del pipeline
    sigan diciendo lo mismo.
    """

    errores = validar_pieza(TIPO_DIFUSION, contenido_mail, fila)
    return [
        "renderer_fact_missing" if error == "hecho_perdido" else error
        for error in errores
    ]


def _num_predict(generator: Generator) -> int | None:
    return getattr(generator, "num_predict", None)
