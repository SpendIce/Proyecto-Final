"""Worker de generación del canal web (ADR 0016, issue #149).

Corre fuera de la respuesta HTTP: toma una ejecución reservada por vez
(`SELECT ... FOR UPDATE SKIP LOCKED` con plazo) y la despacha por
`interpretar_solicitud` con el `DespachoGacetilla` estructurado del
pedido, para los siete tipos: la misma clasificación determinística del
texto, el mismo gate de rol y la misma auditoría HU-013 que cualquier
otro canal, sin caminos paralelos en la app.

Recuperación: si el proceso cae entre el Doc y el asiento, la reserva
vence y otra corrida retoma el trabajo; el destino busca el Doc por la
marca de la solicitud en sus propiedades antes de crear uno, así que la
segunda corrida reutiliza el mismo documento (ADR 0016, prueba 1).

Decisiones que no se ven en el código:

- **El límite de reintentos se mide por reservas tomadas.** Una falla
  reportada por el pipeline (gate rechazado, datos incompletos, tipo no
  disponible) cierra la ejecución de inmediato: no tiene sentido volver a
  intentar lo mismo. En la generación, una excepción no prevista sí
  reintenta, pero con tope `MAX_INTENTOS`: al agotarse, la ejecución
  queda `FALLIDA` con `error_generacion` y la solicitud `ERROR`, visible
  en la bandeja, en vez de colgar para siempre. En el ajuste no aplica:
  cualquier excepción dentro del tramo de generación y destino cierra el
  intento directo a `LISTA`; un fallo de persistencia posterior, fuera
  de ese tramo, sigue el camino de reserva.
- **El log nunca lleva prosa ni identidad**: una línea por falla con el
  código estable, el id de la ejecución y el intento — los identificadores
  ya son opacos y el detalle del motivo queda en el resultado durable.
- **Un ajuste es una ejecución más, no una regeneración.** La ejecución
  `clase='ajuste'` reescribe la revisión vigente con la indicación
  registrada, la vuelca en el mismo Doc y crea la revisión nueva; si el
  gate o el Doc fallan, la vigente queda intacta. Un fallo de
  persistencia posterior no entra en esa regla: sigue el camino de
  reserva, porque el Doc ya puede estar escrito y cerrar a `LISTA` sin
  reconciliar declararía vigente una revisión que el Doc ya no muestra.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from ..canal_form import hash_correo
from ..destinos import (
    DestinoBorradoresError,
    ReferenciaBorrador,
    ResultadoDestinoPorMarca,
)
from ..fuentes import FuenteSolicitudes
from ..gacetillas import requiere_actividad
from ..interpretacion import (
    DespachoGacetilla,
    IdentidadSolicitante,
    interpretar_solicitud,
)
from ..procesamiento import Generator
from .ajuste import FalloIntentoAjuste, SalidaAjuste, ajustar
from .persistencia import (
    CANAL_WEB,
    CANAL_WEB_DEMO,
    RepositorioWeb,
    TrabajoWeb,
)
from .sesiones import ORIGEN_DEMO, ORIGEN_GOOGLE

logger = logging.getLogger(__name__)

MAX_INTENTOS = 3

# Estado del pipeline → cierre durable de la ejecución. Los códigos son el
# vocabulario cerrado del esquema (`ejecuciones.resultado`): un resultado
# fuera de la lista rompe el CHECK, así que el mapa es exhaustivo.
_CIERRE_POR_ESTADO = {
    "INCOMPLETA": ("INCOMPLETA", "datos_incompletos"),
    "INVALIDA": ("FALLIDA", "source_invalid"),
    "RECHAZADA": ("FALLIDA", "channel_invalid"),
    "FALLIDA": ("FALLIDA", "error_generacion"),
    "PENDIENTE_DESAMBIGUACION": ("FALLIDA", "error_generacion"),
}


class FalloGeneracion(RuntimeError):
    """El pipeline reportó una falla esperada: la ejecución queda cerrada."""

    def __init__(
        self,
        estado: str,
        resultado: str,
        *,
        errores: tuple[str, ...] = (),
        intentos: int = 1,
        fallos: tuple[FalloIntentoAjuste, ...] = (),
        duracion_ms: int = 0,
    ) -> None:
        self.estado = estado
        self.resultado = resultado
        self.errores = errores
        self.intentos = intentos
        self.fallos = fallos
        self.duracion_ms = duracion_ms
        super().__init__(resultado)


def _registrar_ajuste(
    directorio_salida: Path,
    trabajo: TrabajoWeb,
    *,
    resultado: str,
    errores: tuple[str, ...] = (),
    intentos: int = 1,
    fallos: tuple[FalloIntentoAjuste, ...] = (),
    duracion_ms: int = 0,
) -> None:
    """Una línea por ajuste en `logs/ajustes.jsonl`: códigos, sin prosa.

    Es lo que permite saber en el servidor por qué un ajuste no se aplicó
    (qué control del gate falló, si el generador se cayó o tardó) sin abrir
    la base ni los logs del contenedor. `fallos` guarda, por intento, sólo
    códigos y duración: nunca el prompt ni el texto. Si no se puede
    escribir, el ajuste sigue igual.
    """
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "id_solicitud": trabajo.id_solicitud,
        "id_ejecucion": trabajo.id_ejecucion,
        "id_ajuste": trabajo.id_ajuste,
        "tipo_pieza": trabajo.tipo_pieza,
        "resultado": resultado,
        "errores": list(errores),
        "intentos": intentos,
        "duracion_ms": duracion_ms,
        "fallos": [
            {
                "intento": fallo.intento,
                "codigos": list(fallo.codigos),
                "duracion_ms": fallo.duracion_ms,
            }
            for fallo in fallos
        ],
    }
    try:
        logs = directorio_salida / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / "ajustes.jsonl").open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("worker_ajuste_sin_registro id=%s", trabajo.id_ejecucion)


# El resultado del destino por marca vive en `destinos.py` porque el
# adapter real (`google_workspace.GoogleDocsDestinoPorMarca`) y el fake
# compartido (`docs_canal.DocsCanalMemoria`) también lo producen. Se
# conserva el alias para no renombrar lo que ya lo importa.
ResultadoDestinoWeb = ResultadoDestinoPorMarca


class DestinoPorMarca(Protocol):
    """Puerto del destino «un Doc por solicitud» (ADR 0016).

    Antes de crear, busca por la marca de la solicitud en las propiedades
    del documento: una segunda corrida sobre la misma solicitud reutiliza
    el Doc existente y vuelca el contenido en él, nunca crea otro.

    `compartir` es el permiso `writer` opcional para quien pidió (#153):
    el worker lo llama sólo cuando el flag del stack lo declara y el
    correo se resolvió contra el padrón.
    """

    def buscar_o_crear(
        self,
        *,
        marca: str,
        id_solicitud: str,
        contenido: str,
        nombre: str | None,
    ) -> ResultadoDestinoPorMarca: ...

    def compartir(self, doc_ref: str, correo: str) -> None: ...


class DestinoPorMarcaMemoria:
    """Destino fake para desarrollo, pruebas y evidencia.

    Un dict en memoria hace de Drive: la marca es la clave, así que una
    recreación sobre la misma solicitud reutiliza el documento.
    """

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    def buscar_o_crear(
        self,
        *,
        marca: str,
        id_solicitud: str,
        contenido: str,
        nombre: str | None,
    ) -> ResultadoDestinoWeb:
        doc = self.docs.get(marca)
        if doc is None:
            ref = ReferenciaBorrador(
                tipo="docs_fake", referencia=f"doc-{marca}"
            )
            doc = {"ref": ref, "head": "head-1", "nombre": nombre}
            self.docs[marca] = doc
        doc["contenido"] = contenido
        return ResultadoDestinoWeb(
            referencia=doc["ref"],
            doc_ref=doc["ref"].referencia,
            doc_url=(
                f"https://docs.google.com/document/d/"
                f"{doc['ref'].referencia}/edit"
            ),
            head_revision_id=doc["head"],
            texto_documento=contenido,
        )

    def compartir(self, doc_ref: str, correo: str) -> None:
        pass


class _DestinoMarcado:
    """Adapter `DestinoBorradores` que ata el Doc a la solicitud web.

    Envuelve al `DestinoPorMarca` para que el pipeline —que sólo conoce
    `guardar`— termine escribiendo en el Doc marcado de la solicitud, sin
    saber que existe.
    """

    def __init__(self, destino: DestinoPorMarca, *, marca: str) -> None:
        self._destino = destino
        self._marca = marca
        self.ultimo: ResultadoDestinoWeb | None = None
        self.ultimo_contenido: str | None = None

    def guardar(
        self,
        id_solicitud: str,
        contenido: str,
        *,
        nombre: str | None = None,
    ) -> ReferenciaBorrador:
        resultado = self._destino.buscar_o_crear(
            marca=self._marca,
            id_solicitud=id_solicitud,
            contenido=contenido,
            nombre=nombre,
        )
        self.ultimo = resultado
        self.ultimo_contenido = contenido
        return resultado.referencia


def _origen_identidad(canal: str) -> str | None:
    """El origen de la identidad que afirmó el canal, para la auditoría.

    `web-demo` es la elección de identidad del modo demostración (sin
    verificar, ADR 0019); `web` pasó por el ID token de Google. Otros
    canales no declaran origen en este incremento.
    """
    return {
        CANAL_WEB: ORIGEN_GOOGLE,
        CANAL_WEB_DEMO: ORIGEN_DEMO,
    }.get(canal)


def _generar_pieza(
    trabajo: TrabajoWeb,
    *,
    fuente: FuenteSolicitudes,
    generator: Generator,
    directorio_salida: Path,
    destino: DestinoPorMarca,
) -> tuple[str, ResultadoDestinoWeb]:
    """Despacha el trabajo por `interpretar_solicitud` y vuelca el resultado.

    El `DespachoGacetilla` declara el tipo de la lista cerrada, la
    actividad de los tipos con ficha y los campos confirmados del pedido;
    el texto del mensaje es derivado y lleva la descripción del pedido
    como dato no privilegiado (ADR 0001): la clasificación la lee, el
    prompt nunca.
    """
    destino_marcado = _DestinoMarcado(destino, marca=trabajo.id_solicitud)
    if requiere_actividad(trabajo.tipo_pieza):
        texto = f"gacetilla actividad {trabajo.actividad_ref}"
    else:
        texto = f"gacetilla {trabajo.tipo_pieza}"
    if trabajo.descripcion:
        texto = f"{texto}. {trabajo.descripcion}"
    resultado = interpretar_solicitud(
        texto=texto,
        solicitante=IdentidadSolicitante(
            identificador=trabajo.solicitante_hash,
            rol=trabajo.rol,
            origen=_origen_identidad(trabajo.canal),
        ),
        fuente=fuente,
        directorio_salida=directorio_salida,
        generator=generator,
        destino=destino_marcado,
        despacho_gacetilla=DespachoGacetilla(
            tipo=trabajo.tipo_pieza,
            id_solicitud=trabajo.id_solicitud,
            actividad=trabajo.actividad_ref,
            campos={
                clave: str(valor)
                for clave, valor in trabajo.campos.get("pieza", {}).items()
            },
        ),
    )
    estado, resultado_codigo = _CIERRE_POR_ESTADO.get(
        resultado.estado, ("FALLIDA", "error_generacion")
    )
    if resultado.estado != "PENDIENTE_VALIDACION":
        raise FalloGeneracion(estado, resultado_codigo)
    if (
        destino_marcado.ultimo is None
        or destino_marcado.ultimo_contenido is None
    ):
        raise FalloGeneracion("FALLIDA", "error_generacion")
    return destino_marcado.ultimo_contenido, destino_marcado.ultimo


def _campos_de_validacion(
    trabajo: TrabajoWeb, *, fuente: FuenteSolicitudes
) -> dict:
    """Los hechos contra los que el gate evalúa la pieza ajustada.

    Para los tipos con ficha, los hechos salen de la fuente institucional
    —igual que en la generación—; para el resto, de los campos confirmados
    del pedido. Un tipo con ficha sin actividad declarada no se puede
    validar y cierra el ajuste como incompleto.
    """
    if not requiere_actividad(trabajo.tipo_pieza):
        return {
            str(clave): str(valor)
            for clave, valor in trabajo.campos.get("pieza", {}).items()
        }
    if not trabajo.actividad_ref:
        raise FalloGeneracion("INCOMPLETA", "datos_incompletos")
    try:
        return dict(fuente.obtener(trabajo.actividad_ref))
    except Exception:
        raise FalloGeneracion("FALLIDA", "error_generacion") from None


# Códigos del generador que, para el esquema durable, cierran como
# `error_generacion`: el detalle accionable queda en `logs/ajustes.jsonl`.
_CODIGOS_GENERADOR = frozenset(
    {"timeout_generador", "presupuesto_agotado", "generador_error"}
)


def _resultado_fallo_ajuste(errores: list[str]) -> str:
    if any(codigo in _CODIGOS_GENERADOR for codigo in errores):
        return "error_generacion"
    if "salida_vacia" in errores:
        return "salida_vacia"
    return "salida_no_conforme"


def _ajustar_pieza(
    trabajo: TrabajoWeb,
    *,
    fuente: FuenteSolicitudes,
    generator: Generator,
    destino: DestinoPorMarca,
) -> tuple[str, ResultadoDestinoWeb, SalidaAjuste]:
    """Reescribe la revisión vigente y la vuelca en el mismo Doc.

    El texto base es el que dejó la última revisión vigente, con las
    correcciones humanas ya importadas por el pedido. Si la salida no pasa
    el gate o el Doc no se puede escribir, no hay revisión nueva: la
    vigente queda intacta. Un fallo del generador vuelve como
    `FalloGeneracion`, no como excepción suelta: así el worker cierra el
    ajuste de inmediato en vez de reintentarlo por reserva. El cierre
    cubre sólo este tramo —generación y destino—; la persistencia de
    `completar_trabajo` corre después y sigue el camino de reserva.
    """
    if trabajo.texto_base is None or trabajo.indicacion is None:
        raise FalloGeneracion("FALLIDA", "error_generacion")
    campos = _campos_de_validacion(trabajo, fuente=fuente)
    salida = ajustar(
        texto_base=trabajo.texto_base,
        indicacion=trabajo.indicacion,
        tipo=trabajo.tipo_pieza,
        campos=campos,
        generator=generator,
    )
    texto = salida.texto
    if not texto:
        raise FalloGeneracion(
            "FALLIDA",
            _resultado_fallo_ajuste(salida.errores),
            errores=tuple(salida.errores),
            intentos=salida.intentos,
            fallos=salida.fallos,
            duracion_ms=salida.duracion_ms,
        )
    try:
        resultado_destino = destino.buscar_o_crear(
            marca=trabajo.id_solicitud,
            id_solicitud=trabajo.id_solicitud,
            contenido=texto,
            nombre=None,
        )
    except DestinoBorradoresError:
        raise FalloGeneracion(
            "FALLIDA",
            "destination_failure",
            errores=("destination_failure",),
            intentos=salida.intentos,
            fallos=salida.fallos,
            duracion_ms=salida.duracion_ms,
        ) from None
    return texto, resultado_destino, salida


def correr_una_vez(
    *,
    repositorio: RepositorioWeb,
    worker_id: str,
    fuente: FuenteSolicitudes,
    generator: Generator,
    directorio_salida: Path,
    destino: DestinoPorMarca,
    correo_para_hash: Callable[[str], str | None] | None = None,
    plazo_segundos: int = 300,
    ahora: datetime | None = None,
    max_intentos: int = MAX_INTENTOS,
    generator_ajuste: Generator | None = None,
) -> TrabajoWeb | None:
    """Un ciclo del worker: reserva, genera y asienta. `None` si no hay trabajo.

    `correo_para_hash` es el camino opcional del permiso de edición
    (#153): con el flag de compartir activo, el script inyecta la
    resolución `solicitante_hash → correo` contra el padrón y el worker
    comparte el Doc con `writer` antes de asentar. Sin correo resoluble
    la generación sigue igual — el Doc queda accesible por la carpeta— y
    el aviso queda en el log, nunca en la base. Si `compartir` falla
    también sigue: el Doc ya existe y la solicitud queda `LISTA`; el
    intento fallido se asienta como `permiso_no_otorgado` con el hash del
    correo.
    """
    trabajo = repositorio.tomar_trabajo(
        worker_id=worker_id,
        plazo_segundos=plazo_segundos,
        ahora=ahora,
    )
    if trabajo is None:
        return None
    es_ajuste = trabajo.clase == "ajuste"
    inicio_ajuste = time.monotonic()
    try:
        if es_ajuste:
            texto, resultado_destino, salida_ajuste = _ajustar_pieza(
                trabajo,
                fuente=fuente,
                generator=generator_ajuste or generator,
                destino=destino,
            )
        else:
            texto, resultado_destino = _generar_pieza(
                trabajo,
                fuente=fuente,
                generator=generator,
                directorio_salida=directorio_salida,
                destino=destino,
            )
    except FalloGeneracion as fallo:
        logger.warning(
            "worker_fallo id_ejecucion=%s resultado=%s",
            trabajo.id_ejecucion,
            fallo.resultado,
        )
        # Un ajuste que no sirve no inutiliza la solicitud: la revisión
        # vigente sigue en pie, se puede aprobar o pedir otro ajuste.
        repositorio.fallar_trabajo(
            id_ejecucion=trabajo.id_ejecucion,
            id_solicitud=trabajo.id_solicitud,
            estado=fallo.estado,
            resultado=fallo.resultado,
            ahora=ahora,
            **({"estado_solicitud": "LISTA"} if es_ajuste else {}),
        )
        if es_ajuste:
            _registrar_ajuste(
                directorio_salida,
                trabajo,
                resultado=fallo.resultado,
                errores=fallo.errores,
                intentos=fallo.intentos,
                fallos=fallo.fallos,
                duracion_ms=fallo.duracion_ms,
            )
        return trabajo
    except Exception:
        # Un ajuste que no se pudo completar en este tramo —generación o
        # destino— no se reintenta por reserva: la revisión vigente sigue
        # en pie y la persona puede pedirlo de nuevo. La recuperación es
        # sólo acá: un fallo de persistencia posterior, como el
        # `InsufficientPrivilege` observado en `completar_trabajo` cuando
        # el Doc ya puede estar escrito, sigue el camino de reserva para
        # reconciliar — cerrarlo a LISTA dejaría la revisión vieja
        # declarada vigente sobre un Doc ya modificado.
        if es_ajuste:
            duracion_ms = int((time.monotonic() - inicio_ajuste) * 1000)
            logger.warning(
                "worker_ajuste_error_no_previsto id_ejecucion=%s",
                trabajo.id_ejecucion,
            )
            repositorio.fallar_trabajo(
                id_ejecucion=trabajo.id_ejecucion,
                id_solicitud=trabajo.id_solicitud,
                resultado="error_generacion",
                ahora=ahora,
                estado_solicitud="LISTA",
            )
            _registrar_ajuste(
                directorio_salida,
                trabajo,
                resultado="error_generacion",
                errores=("error_no_previsto",),
                intentos=trabajo.intentos,
                fallos=(
                    FalloIntentoAjuste(
                        max(1, trabajo.intentos),
                        ("error_no_previsto",),
                        duracion_ms,
                    ),
                ),
                duracion_ms=duracion_ms,
            )
            return trabajo
        # Error de infraestructura o caída de una generación: la reserva
        # vence y otra corrida retoma sin duplicar el Doc, hasta el tope de
        # reintentos; después la ejecución queda cerrada y la solicitud
        # visible «Con error».
        if trabajo.intentos >= max_intentos:
            logger.warning(
                "worker_sin_reintento id_ejecucion=%s intentos=%s",
                trabajo.id_ejecucion,
                trabajo.intentos,
            )
            repositorio.fallar_trabajo(
                id_ejecucion=trabajo.id_ejecucion,
                id_solicitud=trabajo.id_solicitud,
                resultado="error_generacion",
                ahora=ahora,
            )
        else:
            logger.warning(
                "worker_error_no_previsto id_ejecucion=%s intento=%s",
                trabajo.id_ejecucion,
                trabajo.intentos,
            )
        return trabajo
    compartido_con_hash = None
    permiso_no_otorgado_hash = None
    if correo_para_hash is not None:
        correo = correo_para_hash(trabajo.solicitante_hash)
        if correo is None:
            logger.warning(
                "worker_compartir_sin_correo id_solicitud=%s",
                trabajo.id_solicitud,
            )
        else:
            try:
                destino.compartir(resultado_destino.doc_ref, correo)
            except Exception as error:
                # El Doc ya existe: un permiso que no se pudo otorgar no
                # convierte la generación en fallida. Se asienta el intento
                # con el hash del correo y la solicitud sigue `LISTA`.
                permiso_no_otorgado_hash = hash_correo(correo)
                logger.warning(
                    "worker_permiso_no_otorgado id_solicitud=%s codigo=%s",
                    trabajo.id_solicitud,
                    getattr(error, "code", type(error).__name__),
                )
            else:
                compartido_con_hash = hash_correo(correo)
    repositorio.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=trabajo.id_solicitud,
        texto_generado=texto,
        referencia=resultado_destino.doc_ref,
        doc_ref=resultado_destino.doc_ref,
        head_revision_id=resultado_destino.head_revision_id,
        doc_url=resultado_destino.doc_url,
        texto_documento=resultado_destino.texto_documento,
        compartido_con_hash=compartido_con_hash,
        permiso_no_otorgado_hash=permiso_no_otorgado_hash,
        origen="ajuste_generativo" if es_ajuste else "generada",
        id_borrador_base=trabajo.id_borrador_base if es_ajuste else None,
        id_ajuste=trabajo.id_ajuste if es_ajuste else None,
        ahora=ahora,
    )
    if es_ajuste:
        _registrar_ajuste(
            directorio_salida,
            trabajo,
            resultado="borrador_generado",
            intentos=salida_ajuste.intentos,
            fallos=salida_ajuste.fallos,
            duracion_ms=salida_ajuste.duracion_ms,
        )
    return trabajo
