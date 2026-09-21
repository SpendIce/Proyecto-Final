"""Cliente pull del lado de A1 hacia Historia Viva, sobre transporte inyectado.

`historia_viva.py` define el puerto y los tipos; este módulo es la capa que los
produce a partir de respuestas crudas: consume un `TransporteHistoriaViva`
intercambiable, valida cada respuesta contra el contrato candidato
`contracts/historia_viva_cliente_candidate_v1.schema.json` y devuelve los
objetos del dominio (`Fragmento`, `Pieza`, `RecepcionAporte`).

Decisiones que no se ven en el código:

- **El contrato que se valida es el candidato de A1, no un acuerdo.** El issue
  #17 sigue abierto: este cliente implementa la posición documentada en
  `respuesta-nacho.md` y en el paquete de cierre, no una integración cerrada.
  Cada respuesta declara su forma con un marcador `schema` para que un cambio
  de contrato se rechace explícitamente en vez de parsearse a medias.
- **Lo que no entra por contrato no existe.** Una respuesta fuera de forma —
  un fragmento sin `fragmento_id`, una precisión de fecha no declarada, un
  aporte "publicado"— se rechaza con `historia_viva_response_invalid`. El
  cliente nunca completa ni inventa el campo que faltó: la ausencia de un dato
  citable es una falla del intercambio, no un hueco a rellenar.
- **El transporte es un puerto, no HTTP.** `TransporteHistoriaViva` define lo
  mínimo que un adapter REST va a implementar cuando #17 cierre: tres
  operaciones, timeout por llamada y errores reducidos al vocabulario cerrado
  de `historia_viva.py`. La conversión `Idempotency-Key` ← `clave_idempotencia`
  y el mapeo de `401`/`403`/`404`/`429`/`503` a códigos conocidos quedan del
  lado del adapter, que hoy no existe a propósito.
- **El timeout se declara, no se finge.** El cliente entrega el presupuesto al
  transporte en cada llamada; aplicarlo al socket es responsabilidad del
  adapter futuro. El default de 20 s queda por encima del objetivo de 15 s de
  respuesta de A2 y es una política separada del presupuesto del LLM, como pide
  la respuesta de Juan.
- **Sólo las consultas se reintentan.** `buscar` y `ampliar` son idempotentes
  por naturaleza y reintentan ante `rate_limited`/`unavailable` (los `429`/`503`
  del contrato). `aportar` no reintenta por default: la deduplicación por
  `Idempotency-Key` es `PROPUESTA_NO_ACORDADA` y reintentar un POST contra un
  servidor que aún no garantizó deduplicar puede crear el segundo aporte que la
  clave existe para evitar. `PoliticaCliente.reintentar_aportes` habilita el
  reintento el día que #17 lo cierre.
- **Pull significa que nada llega solo.** El cliente no registra handlers ni
  sondea: cada llamada de transporte es consecuencia de una llamada del puerto
  `HistoriaViva`, que A1 inicia. Una consulta sin resultados produce una tupla
  vacía, no una afirmación.

La efeméride no se consulta: se compone del lado de A1 con
`componer_material_efemeride`, que funciona igual contra este cliente porque el
cliente implementa el mismo puerto.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Protocol, TypeVar

from .historia_viva import (
    ESTADO_APORTE,
    ID_RE,
    LIMITE_FRAGMENTOS_MAX,
    PRECISIONES_FECHA,
    Aporte,
    ConsultaFragmentos,
    Fragmento,
    HistoriaVivaError,
    Pieza,
    RangoHistorico,
    RecepcionAporte,
)


CONTRACT_VERSION = "historia_viva_cliente_candidate_v1"
CONTRACT_STATUS = "CANDIDATO_NO_INSTITUCIONAL"

# Marcador de forma que cada respuesta declara. Permite distinguir "servidor
# correcto, contrato equivocado" de "respuesta dañada", y hace visible un
# cambio de versión sin depender de que el parseo rompa por casualidad.
SCHEMA_FRAGMENTOS = "historia_viva.fragmentos.v1"
SCHEMA_PIEZA = "historia_viva.pieza.v1"
SCHEMA_APORTE = "historia_viva.aporte.v1"

# Códigos que un adapter mapea desde `429` y `503`: transitorios, con sentido
# de reintentar. `unauthorized`, `forbidden` y `request_invalid` son
# definitivos y `response_invalid` es una falla del intercambio, no del canal:
# ninguno mejora por esperar.
CODIGOS_REINTENTABLES = frozenset(
    {"historia_viva_rate_limited", "historia_viva_unavailable"}
)

_RESPUESTA_INVALIDA = "historia_viva_response_invalid"

_T = TypeVar("_T")


@dataclass(frozen=True)
class PoliticaCliente:
    """Timeout y reintentos como configuración declarada, no como constantes.

    `timeout_segundos` es el presupuesto que se le da al transporte por llamada;
    default 20 s: mayor que el objetivo de 15 s de respuesta de A2 y separado
    del presupuesto del LLM. `reintentos` cuenta los intentos *extra* de las
    operaciones idempotentes y `espera_segundos` es la espera fija entre ellos:
    no hay jitter porque tampoco hay congestión real que dispersar todavía.
    """

    timeout_segundos: float = 20.0
    reintentos: int = 2
    espera_segundos: float = 0.5
    reintentar_aportes: bool = False

    def __post_init__(self) -> None:
        if self.timeout_segundos <= 0:
            raise ValueError("timeout_segundos debe ser positivo")
        if self.reintentos < 0:
            raise ValueError("reintentos no puede ser negativo")
        if self.espera_segundos < 0:
            raise ValueError("espera_segundos no puede ser negativa")


class RelojEspera(Protocol):
    """La espera entre reintentos, inyectada para que el tiempo sea un dato."""

    def dormir(self, segundos: float) -> None: ...


class RelojSistema:
    """Reloj real: el único lugar donde el reintento espera de verdad."""

    def dormir(self, segundos: float) -> None:
        time.sleep(segundos)


class TransporteHistoriaViva(Protocol):
    """Lo mínimo que un adapter REST va a implementar cuando #17 cierre.

    Cada operación recibe el timeout por llamada y devuelve el cuerpo crudo
    ya parseado (un `dict`), o `None` en `get_pieza` cuando el servidor
    responde `404` —inexistente y no validada son indistinguibles por
    contrato—. Las fallas llegan como `HistoriaVivaError` con un código del
    vocabulario cerrado: el adapter colapsa `400`, `401`, `403`, `429`, `503`
    y cualquier otro estado a esos códigos, y convierte
    `aporte.clave_idempotencia` en el header `Idempotency-Key`.

    No hay implementación productiva en este repo: el adapter HTTP queda
    declarado como pendiente del acuerdo con A2, junto con la identidad por
    token y la URL base.
    """

    def get_fragmentos(
        self, consulta: ConsultaFragmentos, *, timeout: float
    ) -> dict[str, Any]: ...

    def get_pieza(self, pieza_id: str, *, timeout: float) -> dict[str, Any] | None: ...

    def post_aporte(self, aporte: Aporte, *, timeout: float) -> dict[str, Any]: ...


class ClienteHistoriaViva:
    """Implementación del puerto `HistoriaViva` que valida antes de creer.

    Cada operación llama al transporte con el timeout configurado, reintenta
    las consultas idempotentes ante fallas transitorias y sólo devuelve
    objetos del dominio construidos desde respuestas en contrato. Lo que el
    contrato no contempla se rechaza; lo que falta no se inventa.
    """

    def __init__(
        self,
        transporte: TransporteHistoriaViva,
        *,
        politica: PoliticaCliente | None = None,
        reloj: RelojEspera | None = None,
    ) -> None:
        self._transporte = transporte
        self._politica = politica or PoliticaCliente()
        self._reloj = reloj or RelojSistema()

    def buscar_fragmentos(
        self, consulta: ConsultaFragmentos
    ) -> tuple[Fragmento, ...]:
        crudo = self._llamar(
            lambda timeout: self._transporte.get_fragmentos(consulta, timeout=timeout),
            reintentable=True,
        )
        return _fragmentos_desde_crudo(crudo, limite=consulta.limite)

    def obtener_pieza(self, pieza_id: str) -> Pieza | None:
        crudo = self._llamar(
            lambda timeout: self._transporte.get_pieza(pieza_id, timeout=timeout),
            reintentable=True,
        )
        if crudo is None:
            return None
        return _pieza_desde_crudo(crudo, pieza_id_esperada=pieza_id)

    def registrar_aporte(self, aporte: Aporte) -> RecepcionAporte:
        crudo = self._llamar(
            lambda timeout: self._transporte.post_aporte(aporte, timeout=timeout),
            reintentable=self._politica.reintentar_aportes,
        )
        return _recepcion_desde_crudo(crudo)

    def _llamar(
        self,
        operacion: Callable[[float], _T],
        *,
        reintentable: bool,
    ) -> _T:
        """Ejecuta con timeout declarado y reintenta sólo lo idempotente.

        Un error no reintentable sale en el primer intento: esperar no cambia
        un `401` ni una respuesta que viola el contrato.
        """

        intentos = self._politica.reintentos + 1 if reintentable else 1
        for intento in range(intentos):
            try:
                return operacion(self._politica.timeout_segundos)
            except HistoriaVivaError as error:
                ultimo = intento == intentos - 1
                if ultimo or error.code not in CODIGOS_REINTENTABLES:
                    raise
                self._reloj.dormir(self._politica.espera_segundos)
        raise AssertionError("inaccesible")  # pragma: no cover


# --- Validación contra el contrato candidato ---------------------------------
#
# Cada `_..._desde_crudo` construye el objeto del dominio o levanta
# `HistoriaVivaError("historia_viva_response_invalid")`. Los `ValueError` de
# los dataclasses —un rango invertido, un id con caracteres prohibidos— se
# colapsan al mismo código: para el pipeline son lo mismo, una respuesta que
# no respeta el contrato.


def _fragmentos_desde_crudo(
    crudo: object, *, limite: int
) -> tuple[Fragmento, ...]:
    campos = _objeto_cerrado(crudo, {"schema", "fragmentos"})
    if campos["schema"] != SCHEMA_FRAGMENTOS:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    fragmentos_crudos = campos["fragmentos"]
    if not isinstance(fragmentos_crudos, list):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    # El contrato prohíbe devolver más de lo pedido: una página mayor que el
    # límite es una respuesta fuera de forma, no material de más que recortar.
    if len(fragmentos_crudos) > limite or len(fragmentos_crudos) > LIMITE_FRAGMENTOS_MAX:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return tuple(_fragmento_desde_crudo(crudo_) for crudo_ in fragmentos_crudos)


def _pieza_desde_crudo(crudo: object, *, pieza_id_esperada: str) -> Pieza:
    campos = _objeto_cerrado(crudo, {"schema", "pieza"})
    if campos["schema"] != SCHEMA_PIEZA:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    pieza_cruda = _objeto_cerrado(
        campos["pieza"],
        {
            "pieza_id",
            "titulo",
            "resumen",
            "rango",
            "tipo",
            "url_original",
            "validada_el",
            "fragmentos",
        },
        opcionales=set(),
    )
    # Una pieza cuyo id no es el pedido no es "otra pieza": es una respuesta
    # que no corresponde a la consulta y se rechaza entera.
    if pieza_cruda["pieza_id"] != pieza_id_esperada:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    fragmentos_crudos = pieza_cruda["fragmentos"]
    if not isinstance(fragmentos_crudos, list) or len(fragmentos_crudos) > (
        LIMITE_FRAGMENTOS_MAX
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return Pieza(
            pieza_id=pieza_cruda["pieza_id"],
            titulo=_cadena(pieza_cruda["titulo"], obligatoria=True),
            resumen=_cadena(pieza_cruda["resumen"]),
            rango=_rango_desde_crudo(pieza_cruda["rango"]),
            tipo=_cadena(pieza_cruda["tipo"], obligatoria=True),
            url_original=_cadena(pieza_cruda["url_original"], obligatoria=True),
            validada_el=_fecha_desde_crudo(pieza_cruda["validada_el"]),
            fragmentos=tuple(
                _fragmento_desde_crudo(crudo_) for crudo_ in fragmentos_crudos
            ),
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _recepcion_desde_crudo(crudo: object) -> RecepcionAporte:
    campos = _objeto_cerrado(crudo, {"schema", "aporte_id", "estado", "duplicado"})
    if campos["schema"] != SCHEMA_APORTE:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    if not isinstance(campos["duplicado"], bool):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    aporte_id = campos["aporte_id"]
    if not isinstance(aporte_id, str) or ID_RE.fullmatch(aporte_id) is None:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        # `RecepcionAporte` ya rechaza cualquier estado que no sea
        # PENDIENTE_VALIDACION: un "publicado" remoto es fuera de contrato.
        return RecepcionAporte(
            aporte_id=aporte_id,
            estado=campos["estado"],
            duplicado=campos["duplicado"],
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _fragmento_desde_crudo(crudo: object) -> Fragmento:
    campos = _objeto_cerrado(
        crudo,
        {
            "fragmento_id",
            "pieza_id",
            "texto",
            "rango",
            "tipo",
            "resumen_pieza",
            "url_original",
            "validada_el",
        },
        opcionales={"ubicacion"},
    )
    ubicacion = campos.get("ubicacion")
    try:
        return Fragmento(
            fragmento_id=_cadena(campos["fragmento_id"], obligatoria=True),
            pieza_id=_cadena(campos["pieza_id"], obligatoria=True),
            texto=_cadena(campos["texto"], obligatoria=True),
            rango=_rango_desde_crudo(campos["rango"]),
            tipo=_cadena(campos["tipo"], obligatoria=True),
            resumen_pieza=_cadena(campos["resumen_pieza"]),
            url_original=_cadena(campos["url_original"], obligatoria=True),
            validada_el=_fecha_desde_crudo(campos["validada_el"]),
            ubicacion=(
                _cadena(ubicacion, obligatoria=True)
                if ubicacion is not None
                else None
            ),
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _rango_desde_crudo(crudo: object) -> RangoHistorico:
    campos = _objeto_cerrado(crudo, {"desde", "hasta", "precision_fecha"})
    precision = campos["precision_fecha"]
    # Una precisión que el catálogo no conoce no se degrada: se rechaza. Peor
    # que perder el fragmento sería presentar su fecha con más exactitud de la
    # que la fuente declaró.
    if precision not in PRECISIONES_FECHA:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return RangoHistorico(
            desde=_fecha_desde_crudo(campos["desde"]),
            hasta=_fecha_desde_crudo(campos["hasta"]),
            precision=precision,
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _objeto_cerrado(
    crudo: object, requeridos: set[str], *, opcionales: set[str] | None = None
) -> dict[str, Any]:
    """Dict con exactamente los campos del contrato, ni uno más ni uno menos.

    Un campo extra es tan sospechoso como uno que falta: el contrato es
    cerrado para que una versión distinta del servicio no pase desapercibida
    dentro de una respuesta parseable.
    """

    if not isinstance(crudo, dict):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    if set(crudo) != requeridos | (opcionales or set()):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return crudo


def _cadena(valor: object, *, obligatoria: bool = False) -> str:
    if not isinstance(valor, str) or (obligatoria and not valor.strip()):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return valor


def _fecha_desde_crudo(valor: object) -> date:
    if not isinstance(valor, str):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


# --- Transporte fake ----------------------------------------------------------

#: Marca de guion: aplica la conducta por defecto —que puede persistir el
#: aporte— y después responde como si la respuesta se hubiera perdido.
#: Reproduce el escenario que la clave de idempotencia existe para resolver.
PERDER_RESPUESTA = object()


class TransporteHistoriaVivaFake:
    """Transporte crudo en memoria: devuelve `dict`s como un adapter parseado.

    A diferencia de `HistoriaVivaFake` —que implementa el puerto ya tipado—
    este fake vive del otro lado de la validación: entrega cuerpos crudos y
    por eso puede servir respuestas fuera de contrato, que es justo lo que el
    cliente tiene que rechazar.

    - `respuestas` fija el cuerpo por defecto de cada operación.
    - `guiones` encola resultados por operación, consumidos en orden: un
      `dict` se devuelve, un `HistoriaVivaError` se levanta y
      `PERDER_RESPUESTA` aplica la conducta por defecto y luego falla como si
      la respuesta se hubiera perdido en la red.
    - `llamadas` registra `(operacion, timeout)` de cada intento, para
      verificar reintentos y que el presupuesto declarado llega al transporte.
    - `post_aporte` aplica por defecto la semántica propuesta en el paquete de
      cierre: misma clave y mismo payload devuelven el mismo `aporte_id` con
      `duplicado: true`; misma clave con payload distinto es conflicto.
    """

    def __init__(
        self,
        *,
        respuestas: dict[str, object] | None = None,
        guiones: dict[str, tuple[object, ...]] | None = None,
    ) -> None:
        self._respuestas = dict(respuestas or {})
        self._guiones = {k: list(v) for k, v in (guiones or {}).items()}
        # clave de idempotencia → (huella del payload, aporte_id)
        self._aportes: dict[str, tuple[str, str]] = {}
        self.llamadas: list[tuple[str, float]] = []

    def get_fragmentos(
        self, consulta: ConsultaFragmentos, *, timeout: float
    ) -> dict[str, Any]:
        self.llamadas.append(("get_fragmentos", timeout))
        return self._resolver(
            "get_fragmentos",
            lambda: {"schema": SCHEMA_FRAGMENTOS, "fragmentos": []},
        )

    def get_pieza(
        self, pieza_id: str, *, timeout: float
    ) -> dict[str, Any] | None:
        self.llamadas.append(("get_pieza", timeout))
        return self._resolver("get_pieza", lambda: None)

    def post_aporte(self, aporte: Aporte, *, timeout: float) -> dict[str, Any]:
        self.llamadas.append(("post_aporte", timeout))
        return self._resolver("post_aporte", lambda: self._registrar(aporte))

    def _resolver(
        self, operacion: str, por_defecto: Callable[[], Any]
    ) -> Any:
        cola = self._guiones.get(operacion)
        if cola:
            resultado = cola.pop(0)
            if resultado is PERDER_RESPUESTA:
                por_defecto()
                raise HistoriaVivaError("historia_viva_unavailable")
            if isinstance(resultado, HistoriaVivaError):
                raise resultado
            return resultado
        if operacion in self._respuestas:
            return self._respuestas[operacion]
        return por_defecto()

    def _registrar(self, aporte: Aporte) -> dict[str, Any]:
        """Semántica `PROPUESTA_NO_ACORDADA` del paquete de cierre, sección 5.1."""

        huella = _huella_aporte(aporte)
        registrado = self._aportes.get(aporte.clave_idempotencia)
        if registrado is not None:
            if registrado[0] != huella:
                # Misma clave con payload distinto: conflicto, colapsado al
                # vocabulario cerrado como un problema del request.
                raise HistoriaVivaError("historia_viva_request_invalid")
            return {
                "schema": SCHEMA_APORTE,
                "aporte_id": registrado[1],
                "estado": ESTADO_APORTE,
                "duplicado": True,
            }
        aporte_id = f"apo-{len(self._aportes) + 1:04d}"
        self._aportes[aporte.clave_idempotencia] = (huella, aporte_id)
        return {
            "schema": SCHEMA_APORTE,
            "aporte_id": aporte_id,
            "estado": ESTADO_APORTE,
            "duplicado": False,
        }


def _huella_aporte(aporte: Aporte) -> str:
    """Huella del payload del aporte, sin la clave: es lo que la clave cubre."""

    cuerpo = {
        "tipo_contenido": aporte.tipo_contenido,
        "canal": aporte.canal,
        "titulo": aporte.titulo,
        "cuerpo": aporte.cuerpo,
        "piezas_fuente": list(aporte.piezas_fuente),
    }
    serializado = json.dumps(
        cuerpo, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()
