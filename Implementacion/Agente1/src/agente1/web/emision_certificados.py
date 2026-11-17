"""Servicio web de la emisión durable del lote de certificados (#168).

La única interfaz que la UI consume. La pantalla nunca encola al aprobar:
la fila de `emisiones_certificados` existe sólo después del POST
explícito de `solicitar`, que además es idempotente —un doble POST
devuelve el trabajo ya pedido, no uno nuevo.

El estado que se muestra es una traducción de la cola durable, no un
estado propio: `SIN_PEDIDO` cuando todavía no hay fila, `EN_COLA` y
`EMITIENDO` mientras el trabajo vive, los cierres del motor tal cual, y
`BLOQUEADA` cuando lo que falta no es una decisión sino un insumo
(firma en custodia, plantilla aprobada, línea con aprobación registrada,
configuración del despliegue).

Decisiones que no se ven en la firma:

- **El rol se revalida fresco.** Cuando hay padrón disponible el rol del
  actor se lee del padrón por su hash en cada operación, no del token de
  sesión: una revocación pega en la primera consulta siguiente.
- **Demo nunca toca la red.** Un lote con `origen_creacion == 'demo'` o
  de la semilla ficticia sólo puede terminar `GENERADA_DEMO`: el worker
  compone el render real con marcas permanentes y la descarga lo vuelve
  a componer al vuelo sobre el snapshot. Fuera de modo demo, el trabajo
  demo cierra `FALLIDA` sin llegar a ningún destino.
- **La descarga no muta.** `descargar` vuelve a componer el ZIP del
  snapshot retenido y no toca la fila: regenerar no es emitir de nuevo.
- **El ambiguo no se reintenta.** `INDETERMINADA` se muestra como
  `EMISION_INDETERMINADA` y ninguna acción web lo vuelve a encolar.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ..canal_form import PadronRoles
from ..certificados_emision import (
    ResultadoEmisionCertificados,
    procesar_emision_certificados,
)
from ..certificados_plantilla_seu import RecursosFirma
from ..confirmaciones import ROL_APROBADOR_CONTENIDO
from ..decisiones_form import RegistroDecisiones
from ..emisiones_certificados import (
    ESTADO_EMITIDA,
    ESTADO_EMITIDA_PARCIAL,
    ESTADO_ENVIANDO,
    ESTADO_EXPIRADA,
    ESTADO_FALLIDA,
    ESTADO_GENERADA_DEMO,
    ESTADO_INDETERMINADA,
    ESTADO_PENDIENTE,
    ESTADO_RESERVADA,
    LEASE_SEGUNDOS,
    MODO_DEMO,
    MODO_REAL,
    EmisionCertificados,
    RepositorioEmisiones,
    construir_zip_certificados,
    ejecutar_trabajo_demo,
    ejecutar_trabajo_emision,
    hash_plantillas_aprobadas,
)
from ..linea_descriptiva import linea_descriptiva_aprobada
from ..lote_demo import es_lote_demo
from ..plantillas_aprobadas import (
    PlantillaCorreo,
    plantilla_version_registrada,
)
from .certificados_web import (
    ESTADO_APROBADA,
    LoteCertificados,
    estado_firmas,
)

ESTADO_SIN_PEDIDO = "SIN_PEDIDO"
ESTADO_EN_COLA = "EN_COLA"
ESTADO_EMITIENDO = "EMITIENDO"
ESTADO_GENERADA_DEMO_WEB = "GENERADA_DEMO"
ESTADO_EMITIDA_WEB = "EMITIDA"
ESTADO_EMITIDA_PARCIAL_WEB = "EMITIDA_PARCIAL"
ESTADO_BLOQUEADA = "BLOQUEADA"
ESTADO_FALLIDA_WEB = "FALLIDA"
ESTADO_INDETERMINADA_WEB = "EMISION_INDETERMINADA"

_ESTADOS_WEB = {
    ESTADO_PENDIENTE: ESTADO_EN_COLA,
    ESTADO_RESERVADA: ESTADO_EN_COLA,
    ESTADO_ENVIANDO: ESTADO_EMITIENDO,
    ESTADO_EMITIDA: ESTADO_EMITIDA_WEB,
    ESTADO_EMITIDA_PARCIAL: ESTADO_EMITIDA_PARCIAL_WEB,
    ESTADO_FALLIDA: ESTADO_FALLIDA_WEB,
    ESTADO_INDETERMINADA: ESTADO_INDETERMINADA_WEB,
    ESTADO_GENERADA_DEMO: ESTADO_GENERADA_DEMO_WEB,
    ESTADO_EXPIRADA: ESTADO_FALLIDA_WEB,
}

# Lo que el motor exige de la ficha de actividad para certificar.
_REQUERIDOS_MOTOR = (
    "titulo",
    "duracion_horas",
    "modalidad",
    "fecha_inicio",
    "organiza",
)


class ErrorEmisionWeb(RuntimeError):
    """Rechazo del servicio. `code` es el código estable para avisos."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ActorCertificadosWeb:
    """Quien opera la pantalla, con la identidad de su sesión."""

    solicitante_hash: str
    rol: str
    origen_identidad: str
    modo_demo: bool


@dataclass(frozen=True)
class EstadoEmisionWeb:
    """Lo que la pantalla muestra; el origen de verdad es la fila."""

    estado: str
    codigo: str | None = None
    bloqueos: tuple[str, ...] = ()
    generadas: int = 0
    enviadas: int = 0
    fallidas: int = 0
    es_demo: bool = False
    disponible: bool = False
    descargable: bool = False


class RepositorioLotesPuerto(Protocol):
    def obtener(self, id_lote: str) -> LoteCertificados | None: ...


def _sin_destino() -> None:
    raise RuntimeError("destino_no_configurado")


class EmisionCertificadosWeb:
    """El servicio del contrato: consulta, pide, descarga y corre la cola.

    Todas las dependencias son inyectables para probar sin red ni base;
    `emision_certificados_runtime` las arma desde el entorno. `padron`
    acepta una fábrica para que cada operación lea el padrón vigente.
    """

    def __init__(
        self,
        *,
        lotes: RepositorioLotesPuerto,
        emisiones: RepositorioEmisiones | None = None,
        padron: PadronRoles | Callable[[], PadronRoles | None] | None = None,
        registro_decisiones: RegistroDecisiones | None = None,
        directorio_salida: Path | str | None = None,
        fabrica_destino: Callable[[], object] | None = None,
        recursos_firma: RecursosFirma | None = None,
        plantillas_aprobadas: Mapping[str, PlantillaCorreo] | None = None,
        modo_demo: bool = False,
        modo_envio: str | None = None,
        bloqueos_config: tuple[str, ...] = (),
        motor: Callable[..., ResultadoEmisionCertificados] = (
            procesar_emision_certificados
        ),
        lease_segundos: int = LEASE_SEGUNDOS,
    ) -> None:
        self._lotes = lotes
        self._emisiones = emisiones
        self._padron = padron
        self._registro = registro_decisiones
        self._directorio_salida = Path(
            directorio_salida if directorio_salida is not None else "emisiones"
        )
        self._fabrica_destino = fabrica_destino
        self._recursos_firma = recursos_firma
        self._plantillas = dict(plantillas_aprobadas or {})
        self._modo_demo = modo_demo
        self._modo_envio = modo_envio
        self._bloqueos_config = tuple(bloqueos_config)
        self._motor = motor
        self._lease_segundos = lease_segundos

    # ---------- identidad ----------

    @staticmethod
    def _exigir_actor(actor: ActorCertificadosWeb | None) -> ActorCertificadosWeb:
        if actor is None or not actor.solicitante_hash:
            raise ErrorEmisionWeb("sin_permiso")
        return actor

    def _padron_actual(self) -> PadronRoles | None:
        if callable(self._padron):
            return self._padron()
        return self._padron

    def _rol_actual(self, actor: ActorCertificadosWeb) -> str | None:
        """El rol vigente del actor: padrón si hay, sesión si no."""
        padron = self._padron_actual()
        if padron is None:
            return actor.rol or None
        correo = padron.correo_para_hash(actor.solicitante_hash)
        if correo is None:
            return None
        return padron.rol_para(correo, (ROL_APROBADOR_CONTENIDO,))

    def _exigir_aprobador(self, actor: ActorCertificadosWeb) -> None:
        if self._rol_actual(actor) != ROL_APROBADOR_CONTENIDO:
            raise ErrorEmisionWeb("rol_no_autorizado")

    @staticmethod
    def _es_demo(lote: LoteCertificados) -> bool:
        return (
            getattr(lote, "origen_creacion", None) == "demo"
            or es_lote_demo(lote)
        )

    # ---------- consulta ----------

    def consultar(
        self, id_lote: str, *, actor: ActorCertificadosWeb
    ) -> EstadoEmisionWeb:
        actor = self._exigir_actor(actor)
        lote = self._lotes.obtener(id_lote)
        if lote is None:
            raise ErrorEmisionWeb("inexistente")
        self._exigir_aprobador(actor)
        emision = (
            self._emisiones.obtener_por_lote(id_lote)
            if self._emisiones is not None
            else None
        )
        return self._estado(lote, emision, actor=actor)

    def solicitar(
        self,
        id_lote: str,
        *,
        hash_lote: str,
        actor: ActorCertificadosWeb,
    ) -> EstadoEmisionWeb:
        actor = self._exigir_actor(actor)
        lote = self._lotes.obtener(id_lote)
        if lote is None:
            raise ErrorEmisionWeb("inexistente")
        self._exigir_aprobador(actor)
        if hash_lote != lote.objeto_lote:
            raise ErrorEmisionWeb("lote_obsoleto")
        if lote.estado != ESTADO_APROBADA:
            raise ErrorEmisionWeb("lote_no_aprobado")
        if actor.solicitante_hash != lote.generada_por_hash:
            raise ErrorEmisionWeb("aprobador_no_es_generador")
        es_demo = self._es_demo(lote)
        if es_demo:
            if not (actor.modo_demo or self._modo_demo):
                raise ErrorEmisionWeb("demo_fuera_de_modo")
            modo = MODO_DEMO
        else:
            if actor.modo_demo or self._modo_demo:
                raise ErrorEmisionWeb("demo_no_emite_real")
            if actor.origen_identidad != "google" or lote.origen_identidad != "google":
                raise ErrorEmisionWeb("identidad_no_verificada")
            modo = MODO_REAL
        if self._emisiones is None:
            raise ErrorEmisionWeb("cola_no_configurada")
        existente = self._emisiones.obtener_por_lote(id_lote)
        if existente is not None:
            # Doble POST: la fila es la reserva, devolverla no la rehace.
            return self._estado(lote, existente, actor=actor)
        if not es_demo:
            bloqueado = self._estado(lote, None, actor=actor)
            if bloqueado.bloqueos:
                return bloqueado
        emision = self._emisiones.encolar(
            id_lote=id_lote,
            modo=modo,
            plantillas_hash=(
                hash_plantillas_aprobadas(self._plantillas)
                if modo == MODO_REAL
                else None
            ),
        )
        return self._estado(lote, emision, actor=actor)

    def descargar(
        self, id_lote: str, *, actor: ActorCertificadosWeb
    ) -> bytes:
        actor = self._exigir_actor(actor)
        lote = self._lotes.obtener(id_lote)
        if lote is None:
            raise ErrorEmisionWeb("inexistente")
        self._exigir_aprobador(actor)
        if not self._es_demo(lote):
            raise ErrorEmisionWeb("lote_no_demo")
        if not (actor.modo_demo or self._modo_demo):
            raise ErrorEmisionWeb("demo_fuera_de_modo")
        emision = (
            self._emisiones.obtener_por_lote(id_lote)
            if self._emisiones is not None
            else None
        )
        if emision is None or emision.estado != ESTADO_GENERADA_DEMO:
            raise ErrorEmisionWeb("estado_invalido")
        if not lote.personas or lote.linea_descriptiva is None:
            raise ErrorEmisionWeb("personas_purgadas")
        return construir_zip_certificados(
            lote=lote,
            demo=True,
            recursos_firma=self._recursos_firma,
            plantillas_aprobadas=self._plantillas,
        )

    # ---------- worker ----------

    def correr_una_vez(
        self, *, worker_id: str, ahora: datetime | None = None
    ) -> str | None:
        """Reclama un trabajo y lo ejecuta. `id_emision` o `None`.

        El tipo del trabajo sale del lote, no de la fila ni del modo del
        proceso: un lote demo corre `ejecutar_trabajo_demo` aunque la
        fila diga lo contrario, y uno real corre el motor con todas las
        barreras antes de tocar la red.
        """
        if self._emisiones is None:
            raise ErrorEmisionWeb("cola_no_configurada")
        trabajo = self._emisiones.reclamar(worker_id=worker_id, ahora=ahora)
        if trabajo is None:
            return None
        lote = self._lotes.obtener(trabajo.id_lote)
        if lote is not None and self._es_demo(lote):
            ejecutar_trabajo_demo(
                trabajo,
                repositorio=self._emisiones,
                lotes=self._lotes,
                padron=self._padron_actual(),
                recursos_firma=self._recursos_firma,
                plantillas_aprobadas=self._plantillas,
                modo_demo=self._modo_demo,
                ahora=ahora,
            )
        else:
            ejecutar_trabajo_emision(
                trabajo,
                repositorio=self._emisiones,
                lotes=self._lotes,
                padron=self._padron_actual(),
                registro_decisiones=self._registro,
                directorio_salida=self._directorio_salida,
                fabrica_destino=self._fabrica_destino or _sin_destino,
                recursos_firma=self._recursos_firma,
                plantillas_aprobadas=self._plantillas,
                motor=self._motor,
                ahora=ahora,
                lease_segundos=self._lease_segundos,
                modo_demo=self._modo_demo,
            )
        return trabajo.id_emision

    # ---------- estado visible ----------

    def _bloqueos(
        self,
        lote: LoteCertificados,
        emision: EmisionCertificados | None,
        *,
        es_demo: bool,
    ) -> tuple[str, ...]:
        bloqueos: list[str] = []
        if lote.estado != ESTADO_APROBADA:
            bloqueos.append("lote_no_aprobado")
        if not lote.personas or lote.linea_descriptiva is None:
            bloqueos.append("personas_purgadas")
        if not es_demo:
            bloqueos.extend(self._bloqueos_reales(lote))
        if emision is not None and emision.estado == ESTADO_INDETERMINADA:
            bloqueos.append("emision_indeterminada")
        if self._emisiones is None and "config_incompleta" not in bloqueos:
            bloqueos.append("config_incompleta")
        return tuple(dict.fromkeys(bloqueos))

    def _bloqueos_reales(self, lote: LoteCertificados) -> list[str]:
        """Lo que falta para que un lote real emita; sólo informativo acá.

        Las barreras duras viven en `ejecutar_trabajo_emision`: esto las
        anticipa para que la pantalla muestre el motivo en vez de un
        fallo a destiempo. Sólo corre con el snapshot presente y se salta
        las comprobaciones que ya marcó `config_incompleta`.
        """
        if not lote.personas or lote.linea_descriptiva is None:
            return []
        bloqueos: list[str] = []
        if lote.origen_identidad != "google":
            bloqueos.append("identidad_no_verificada")
        actividad = lote.actividad or {}
        if any(not str(actividad.get(c, "") or "").strip()
               for c in _REQUERIDOS_MOTOR):
            bloqueos.append("actividad_datos_incompletos")
        if self._registro is None or self._padron_actual() is None:
            bloqueos.append("config_incompleta")
        elif not linea_descriptiva_aprobada(
            self._registro,
            id_actividad=lote.id_actividad,
            linea=lote.linea_descriptiva,
        ):
            bloqueos.append("linea_descriptiva_no_aprobada")
        condiciones = tuple(p.condicion for p in lote.personas)
        if not estado_firmas(self._recursos_firma, condiciones).disponible:
            bloqueos.append("signature_resources_missing")
        # Las plantillas son gate sólo de la emisión en producción: en
        # modo prueba el motor las saltea y bloquear acá apagaría el
        # envío de prueba.
        if self._modo_envio != "prueba":
            for tipo in self._tipos_plantilla_requeridos(condiciones):
                plantilla = self._plantillas.get(tipo)
                if plantilla is None:
                    bloqueos.append("approved_template_missing")
                elif self._registro is not None and not (
                    plantilla_version_registrada(
                        self._registro, tipo=tipo, plantilla=plantilla
                    )
                ):
                    bloqueos.append("template_version_unapproved")
        for codigo in self._bloqueos_config:
            bloqueos.append(codigo)
        return bloqueos

    @staticmethod
    def _tipos_plantilla_requeridos(condiciones: tuple[str, ...]) -> tuple[str, ...]:
        tipos = ["correo_certificado"]
        if "asistencia" in condiciones:
            tipos.append("certificado_asistencia")
        return tuple(tipos)

    def _estado(
        self,
        lote: LoteCertificados,
        emision: EmisionCertificados | None,
        *,
        actor: ActorCertificadosWeb,
    ) -> EstadoEmisionWeb:
        es_demo = self._es_demo(lote)
        bloqueos = self._bloqueos(lote, emision, es_demo=es_demo)
        es_generador = actor.solicitante_hash == lote.generada_por_hash
        if not es_demo and actor.origen_identidad != "google":
            bloqueos += ("identidad_no_verificada",)
        if not es_generador:
            bloqueos += ("aprobador_no_es_generador",)
        if emision is None:
            estado = (
                ESTADO_BLOQUEADA if bloqueos else ESTADO_SIN_PEDIDO
            )
            codigo = None
        else:
            estado = _ESTADOS_WEB.get(emision.estado, ESTADO_FALLIDA_WEB)
            codigo = emision.error_codigo or (
                "expirada" if emision.estado == ESTADO_EXPIRADA else None
            )
        if es_demo:
            contexto_ok = actor.modo_demo or self._modo_demo
        else:
            contexto_ok = not (actor.modo_demo or self._modo_demo)
        disponible = (
            emision is None
            and not bloqueos
            and es_generador
            and contexto_ok
        )
        descargable = (
            es_demo
            and emision is not None
            and emision.estado == ESTADO_GENERADA_DEMO
            and bool(lote.personas)
        )
        return EstadoEmisionWeb(
            estado=estado,
            codigo=codigo,
            bloqueos=bloqueos,
            generadas=emision.total if emision is not None else 0,
            enviadas=emision.enviadas if emision is not None else 0,
            fallidas=emision.fallidas if emision is not None else 0,
            es_demo=es_demo,
            disponible=disponible,
            descargable=descargable,
        )


__all__ = [
    "ESTADO_BLOQUEADA",
    "ESTADO_EMITIDA_PARCIAL_WEB",
    "ESTADO_EMITIDA_WEB",
    "ESTADO_EMITIENDO",
    "ESTADO_EN_COLA",
    "ESTADO_FALLIDA_WEB",
    "ESTADO_GENERADA_DEMO_WEB",
    "ESTADO_INDETERMINADA_WEB",
    "ESTADO_SIN_PEDIDO",
    "ActorCertificadosWeb",
    "EmisionCertificadosWeb",
    "ErrorEmisionWeb",
    "EstadoEmisionWeb",
]
