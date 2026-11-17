"""Ajuste generativo sobre la revisión vigente del canal web.

Un pedido de ajuste no vuelve a generar desde el pedido original: parte del
texto de la revisión vigente —incluidas las correcciones que una persona
hizo en el Doc y que «Traer cambios» importó— y le pide al modelo que lo
reescriba según una indicación corta (más breve, sumá el horario, tono más
formal). El resultado es una revisión nueva, escrita en el mismo Doc, con
origen `ajuste_generativo` y base declarada; la anterior no se sobrescribe.

Decisiones que no se ven en el código:

- **Antes de encolar se importa el Doc.** Si la persona editó el Doc y no
  pulsó «Traer cambios», la base del ajuste sería otra que lo que se lee en
  pantalla. El pedido reexporta y, si el hash cambió, la revisión importada
  pasa a ser la base.
- **La indicación es una instrucción acotada, no prosa libre del pedido.**
  Viaja al prompt dentro de un bloque propio, con el texto base delimitado:
  el modelo reescribe ese texto, no decide qué hacer con un pedido nuevo.
- **La marca y el gate son los mismos de la generación.** La salida tiene
  que empezar con `# BORRADOR — NO PUBLICAR` y pasar `validar_pieza`; una
  salida vacía, fuera de contrato o un fallo del generador cierra el ajuste
  en error visible y deja la revisión vigente intacta. El fallo del
  generador no se reintenta: el adapter ya agotó su timeout y reintentarlo
  multiplicaría la espera con la solicitud en `AJUSTANDO`.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files

from ..destinos import BORRADOR_MARKER, DestinoBorradoresError
from ..gacetillas import fecha_larga, normalizar_texto, validar_pieza
from ..ollama import OllamaTimeoutError
from ..presupuesto import PresupuestoAgotadoError
from ..procesamiento import Generator
from .docs_canal import ExportadorDocs, aviso_exportador
from .persistencia import (
    ConflictoIdempotencia,
    RepositorioWeb,
)

PROMPT_AJUSTE = "ajuste_generativo_v1"
LARGO_MINIMO_INDICACION = 3
LARGO_MAXIMO_INDICACION = 500
LARGO_MAXIMO_LLAVE = 200

AVISOS_AJUSTE = {
    "indicacion_corta": "La indicación tiene que tener al menos 3 caracteres.",
    "indicacion_larga": "La indicación no puede superar los 500 caracteres.",
    "cerrada": "La solicitud ya está cerrada: no admite ajustes.",
    "sin_revision": "La solicitud todavía no tiene una revisión vigente.",
    "ajuste_en_curso": "Ya hay un ajuste en curso para esta solicitud.",
    "llave_repetida": "El formulario venció. Recargá la página.",
    "llave_invalida": "El formulario venció. Recargá la página.",
    "doc_no_disponible": "No hay un Doc disponible para el ajuste.",
    "revision_obsoleta": "La revisión cambió: volvé a pedir el ajuste.",
    "inexistente": "La solicitud no existe.",
    "doc_inexistente": "El Doc ya no existe.",
    "exportador_invalido": "No se pudo interpretar el Doc.",
    "workspace_no_disponible": "Workspace no está disponible.",
    "no_disponible": "La solicitud no admite ajustes en este estado.",
}


@dataclass(frozen=True)
class ResultadoAjusteWeb:
    """Lo que dejó el POST de ajuste: redirigir o mostrar el aviso."""

    codigo: str
    aviso: str = ""
    es_error: bool = False
    status_code: int = 200
    redirigir: bool = False


def validar_indicacion(indicacion: str) -> str | None:
    """Código del problema de la indicación, o `None` si es válida."""
    if len(indicacion) < LARGO_MINIMO_INDICACION:
        return "indicacion_corta"
    if len(indicacion) > LARGO_MAXIMO_INDICACION:
        return "indicacion_larga"
    return None


def construir_prompt_ajuste(*, texto_base: str, indicacion: str) -> str:
    """El prompt versionado con el texto base y la indicación del pedido."""
    plantilla = (
        files("agente1")
        .joinpath("prompts", f"{PROMPT_AJUSTE}.txt")
        .read_text(encoding="utf-8")
    )
    # `format` sustituye una sola vez: si el texto base trae literalmente
    # `{indicacion}` o `{texto_base}`, queda como contenido y no se vuelve a
    # interpretar como marcador.
    return plantilla.format(texto_base=texto_base, indicacion=indicacion)


def _quitar_marca(texto: str) -> str:
    """Saca la cabecera aunque el modelo la haya repetido con otro espaciado.

    La marca se vuelve a anteponer canónica: el destino exige el prefijo
    exacto y una cabecera duplicada en el Doc sería ruido para la persona.
    """
    if texto.startswith(BORRADOR_MARKER):
        return texto[len(BORRADOR_MARKER):].lstrip("\n").strip()
    primera, _, resto = texto.partition("\n")
    if primera.strip() == BORRADOR_MARKER.strip():
        return resto.lstrip("\n").strip()
    return texto.strip()


def _campos_de_la_base(campos: dict, texto_base: str) -> dict:
    """Hechos confirmados que siguen presentes en el texto base.

    La revisión vigente puede traer correcciones humanas: si una persona
    cambió el título en el Doc, el valor del pedido original ya no está en
    la base y exigirlo haría fallar el ajuste por un dato que la persona
    corrigió a propósito. El gate conserva entonces sólo los hechos que la
    base efectivamente declara; la prosa (`cuerpo`, `bajada`) queda fuera
    porque es lo que el ajuste reescribe.
    """
    normalizado = normalizar_texto(texto_base)
    presentes: dict = {}
    for clave, valor in campos.items():
        if clave in ("cuerpo", "bajada"):
            continue
        texto = str(valor).strip()
        if not texto:
            continue
        fecha = fecha_larga(texto)
        if normalizar_texto(texto) in normalizado or (
            fecha is not None and normalizar_texto(fecha) in normalizado
        ):
            presentes[clave] = valor
    return presentes


# El pie institucional (después de la línea `--`) es fijo de la forma: no
# viaja al modelo —menos tokens que el modelo pueda cortar o retocar— y se
# repone tal cual en la salida.
SEPARADOR_PIE = "\n--\n"
# Un segundo intento cuando la salida no sirve: el modelo local es
# estocástico y una salida vacía o que pierde un dato suele no repetirse.
INTENTOS_AJUSTE = 2


def _separar_pie(texto: str) -> tuple[str, str]:
    """`(cuerpo, pie)`; el pie incluye el separador `--` y puede ser vacío."""
    corte = texto.rfind(SEPARADOR_PIE)
    if corte < 0:
        return texto, ""
    return texto[:corte], texto[corte:]


# Una línea de asunto en cualquier posición o capitalización: el modelo
# puede moverla, duplicarla o escribir «asunto :». La línea entera se
# descarta y se repone la de la base, canónica y única, al inicio.
_PATRON_LINEA_ASUNTO = re.compile(r"\s*asunto\s*:", re.IGNORECASE)
_BLANCOS_REPETIDOS = re.compile(r"\n{3,}")


def _es_linea_asunto(linea: str) -> bool:
    return _PATRON_LINEA_ASUNTO.match(linea) is not None


def _fijar_asunto(pieza: str, asunto: str) -> str:
    """Un solo `Asunto:` canónico, el de la base, en la primera línea.

    El asunto es parte fija de la forma, no prosa: si se lo deja al modelo
    lo reescribe, lo mueve tras un encabezado propio o lo repite, y el
    gate no lo distingue cuando el título aparece también en el cuerpo.
    Se descartan todas las líneas de asunto del modelo y se antepone la de
    la base. Como una línea descartada podía cargar un hecho que no está
    en otro lado, el llamador vuelve a validar la pieza recompuesta.
    """
    lineas = [
        linea.rstrip()
        for linea in pieza.splitlines()
        if not _es_linea_asunto(linea)
    ]
    cuerpo = _BLANCOS_REPETIDOS.sub("\n\n", "\n".join(lineas)).strip()
    return f"{asunto}\n\n{cuerpo}"


def normalizar_pieza_ajustada(
    salida: str, *, tipo: str, campos: dict, texto_base: str
) -> tuple[str, list[str]]:
    """Normaliza la salida del modelo y la somete al gate de la pieza.

    La marca se conserva si el modelo la repitió y se antepone si no: es una
    cabecera obligatoria del destino, no prosa creativa. El pie de la base
    reemplaza al que haya escrito el modelo. El texto se valida contra el
    mismo `validar_pieza` que usa la generación, con los hechos de la base
    que el ajuste debe conservar. El asunto se repone después del gate y
    la pieza recompuesta se valida de nuevo: descartar las líneas de
    asunto del modelo puede llevarse un hecho que sólo vivía en ellas.
    """
    texto = salida.strip()
    if not texto:
        return "", ["salida_vacia"]
    base = _quitar_marca(texto_base)
    cuerpo, _ = _separar_pie(_quitar_marca(texto))
    cuerpo = cuerpo.strip()
    if not cuerpo:
        return "", ["salida_vacia"]
    _, pie = _separar_pie(base)
    # La forma deja una línea en blanco antes del `--` del pie.
    pieza = cuerpo + "\n" + pie.rstrip() if pie else cuerpo
    campos_base = _campos_de_la_base(campos, texto_base)
    errores = validar_pieza(tipo, pieza, campos_base)
    if errores:
        return "", errores
    # El gate corre sobre lo que escribió el modelo: reponer el asunto
    # antes dejaría pasar una salida que perdió el título. Después de
    # recomponer se valida de nuevo por el mismo motivo: si un hecho sólo
    # estaba en la línea de asunto descartada, la salida no se rescata.
    asunto = base.partition("\n")[0].strip()
    if asunto.startswith("Asunto:"):
        pieza = _fijar_asunto(pieza, asunto)
        errores = validar_pieza(tipo, pieza, campos_base)
        if errores:
            return "", errores
    return f"{BORRADOR_MARKER}{pieza}\n", []


@dataclass(frozen=True)
class FalloIntentoAjuste:
    """Un intento fallido: código estable y duración, nunca el mensaje."""

    intento: int
    codigos: tuple[str, ...]
    duracion_ms: int


@dataclass(frozen=True)
class SalidaAjuste:
    """La pieza ajustada (o vacía), los códigos del último intento y el detalle.

    `fallos` conserva el código y la duración de cada intento fallido, para
    que `logs/ajustes.jsonl` explique en el servidor qué pasó sin guardar el
    prompt, la prosa ni el mensaje del adapter.
    """

    texto: str
    errores: list[str]
    intentos: int
    duracion_ms: int = 0
    fallos: tuple[FalloIntentoAjuste, ...] = ()


# El adapter conserva el timeout como subtipo de `RuntimeError`
# (`OllamaTimeoutError`); el resto de sus fallas de red o de forma llega
# como `RuntimeError` genérico. El mensaje nunca se registra: podría
# arrastrar el prompt.
def _codigo_error_generador(error: Exception) -> str:
    if isinstance(error, (TimeoutError, OllamaTimeoutError)):
        return "timeout_generador"
    if isinstance(error, PresupuestoAgotadoError):
        return "presupuesto_agotado"
    return "generador_error"


def _transcurrido_ms(inicio: float) -> int:
    return max(0, int((time.monotonic() - inicio) * 1000))


def ajustar(
    *,
    texto_base: str,
    indicacion: str,
    tipo: str,
    campos: dict,
    generator: Generator,
    intentos: int = INTENTOS_AJUSTE,
) -> SalidaAjuste:
    """Pide el ajuste y reintenta sólo si la salida no pasa el gate.

    Un fallo del generador no se reintenta: el adapter ya esperó su timeout y
    otro intento sólo multiplica la espera. Devuelve el fallo con su código
    para que el worker cierre el ajuste y la solicitud vuelva a `LISTA` de
    inmediato, sin esperar a que venza la reserva.
    """
    cuerpo_base, _ = _separar_pie(texto_base)
    prompt = construir_prompt_ajuste(
        texto_base=cuerpo_base.rstrip() + "\n", indicacion=indicacion
    )
    comienzo = time.monotonic()
    fallos: list[FalloIntentoAjuste] = []
    texto, errores = "", ["salida_vacia"]
    for intento in range(1, intentos + 1):
        inicio = time.monotonic()
        try:
            salida = generator.generar(prompt)
        except Exception as error:
            codigo = _codigo_error_generador(error)
            fallos.append(
                FalloIntentoAjuste(
                    intento, (codigo,), _transcurrido_ms(inicio)
                )
            )
            return SalidaAjuste(
                "", [codigo], intento, _transcurrido_ms(comienzo), tuple(fallos)
            )
        texto, errores = normalizar_pieza_ajustada(
            salida,
            tipo=tipo,
            campos=campos,
            texto_base=texto_base,
        )
        if texto:
            return SalidaAjuste(
                texto, [], intento, _transcurrido_ms(comienzo), tuple(fallos)
            )
        fallos.append(
            FalloIntentoAjuste(
                intento, tuple(errores), _transcurrido_ms(inicio)
            )
        )
    return SalidaAjuste(
        "", errores, intentos, _transcurrido_ms(comienzo), tuple(fallos)
    )


def ajustar_texto(
    *,
    texto_base: str,
    indicacion: str,
    tipo: str,
    campos: dict,
    generator: Generator,
) -> tuple[str, list[str]]:
    """Pide el ajuste al generador y devuelve la pieza normalizada o el fallo."""
    salida = ajustar(
        texto_base=texto_base,
        indicacion=indicacion,
        tipo=tipo,
        campos=campos,
        generator=generator,
    )
    return salida.texto, salida.errores


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _resultado(codigo: str, status_code: int) -> ResultadoAjusteWeb:
    return ResultadoAjusteWeb(
        codigo,
        aviso=AVISOS_AJUSTE.get(codigo, codigo),
        es_error=True,
        status_code=status_code,
    )


def ejecutar_ajuste_web(
    *,
    repositorio: RepositorioWeb,
    exportador: ExportadorDocs | None,
    id_solicitud: str,
    indicacion: str,
    llave: str,
    solicitante_hash: str,
    rol: str,
    origen_identidad: str,
    version_agente: str,
    ahora: datetime | None = None,
) -> ResultadoAjusteWeb:
    """El POST de «Pedir ajuste»: valida, importa el Doc y encola.

    La app pone la sesión, el CSRF y el gate de rol antes de llamar acá. El
    reenvío con la misma llave devuelve la redirección sin encolar de nuevo;
    la misma llave con otra indicación es conflicto, como en el pedido
    guiado.
    """
    ahora = ahora or datetime.now(timezone.utc)
    detalle = repositorio.obtener(id_solicitud)
    if detalle is None:
        return _resultado("inexistente", 404)
    indicacion = indicacion.strip()
    problema = validar_indicacion(indicacion)
    if problema is not None:
        return _resultado(problema, 400)

    llave = (llave or "").strip() or uuid.uuid4().hex
    if len(llave) > LARGO_MAXIMO_LLAVE:
        return _resultado("llave_invalida", 400)
    clave = f"ajuste:{llave}"
    existente = repositorio.buscar_ajuste(idempotency_key=clave)
    if existente is not None:
        misma_firma = (
            existente.id_solicitud == id_solicitud
            and existente.solicitante_hash == solicitante_hash
            and existente.indicacion_hash == _hash(indicacion)
        )
        if misma_firma:
            return ResultadoAjusteWeb("existente", redirigir=True)
        return _resultado("llave_repetida", 409)

    if detalle.estado_web in ("APROBADA", "DESCARTADA", "VENCIDA"):
        return _resultado("cerrada", 409)
    if detalle.estado_web == "AJUSTANDO":
        return _resultado("ajuste_en_curso", 409)
    if detalle.estado_web != "LISTA":
        return _resultado("sin_revision", 400)
    if exportador is None or detalle.doc_ref is None:
        return _resultado("doc_no_disponible", 400)
    try:
        texto = exportador.exportar_texto(detalle.doc_ref)
    except DestinoBorradoresError as error:
        return _resultado(aviso_exportador(error), 400)
    importacion = repositorio.importar_revision(
        id_solicitud=id_solicitud, texto=texto, ahora=ahora
    )
    if importacion.codigo in ("inexistente", "no_disponible"):
        status = 404 if importacion.codigo == "inexistente" else 400
        return _resultado(importacion.codigo, status)

    actualizado = repositorio.obtener(id_solicitud) or detalle
    if not actualizado.revisiones:
        return _resultado("sin_revision", 400)
    vigente = actualizado.revisiones[-1]
    try:
        resultado = repositorio.crear_ajuste(
            idempotency_key=clave,
            id_solicitud=id_solicitud,
            id_borrador_base=vigente.id_borrador,
            base_output_hash=vigente.output_hash,
            indicacion=indicacion,
            solicitante_hash=solicitante_hash,
            rol=rol,
            origen_identidad=origen_identidad,
            version_agente=version_agente,
            ahora=ahora,
        )
    except ConflictoIdempotencia:
        return _resultado("llave_repetida", 409)
    if resultado.codigo in ("encolado", "existente"):
        return ResultadoAjusteWeb(resultado.codigo, redirigir=True)
    status = 409 if resultado.codigo == "revision_obsoleta" else 400
    return _resultado(resultado.codigo, status)
