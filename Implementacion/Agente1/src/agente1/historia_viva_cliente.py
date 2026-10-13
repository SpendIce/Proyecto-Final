"""Cliente pull del lado de A1 hacia Historia Viva, sobre transporte inyectado.

`historia_viva.py` define el puerto y los tipos; este módulo es la capa que los
produce a partir de respuestas crudas: consume un `TransporteHistoriaViva`
intercambiable, valida cada respuesta contra el contrato `/v1` de Historia
Viva (`openapi-agentes.yaml` 1.1.0-rc1, borrador hasta el congelado del
30-oct-2026) y devuelve los objetos del dominio (`Fragmento`, `Pieza`,
`RecepcionAporte`). El esquema que se valida está espejado en
`contracts/historia_viva_v1.schema.json`.

Decisiones que no se ven en el código:

- **El contrato es el `/v1` de Historia Viva, no una posición de A1.** El
  OpenAPI lo publica Ignacio; A1 contesta sus cambios en `PREGUNTAS.md` del
  paquete `contratojuan` y no edita el YAML. Si el contrato cambia, cambia
  este decodificador y su espejo, no el dominio.
- **Lo que no entra por contrato no existe.** Una respuesta fuera de forma —
  un fragmento sin `fragmento_id`, una precisión de fecha no declarada, un
  campo de más en una forma cerrada, un aporte que no está `Pendiente`— se
  rechaza con `historia_viva_response_invalid`. El cliente nunca completa ni
  inventa el campo que faltó.
- **El tipo de Pieza es un string opaco.** `/v1` lo declara enum abierto: un
  tipo nuevo (`planilla`, `video`) no rompe el parseo. La precisión de fecha,
  en cambio, es cerrada, porque decide cuánto se puede afirmar.
- **El transporte es un puerto.** `TransporteHistoriaViva` lo implementan el
  fake de este módulo y el adapter HTTP de `historia_viva_http.py`, que
  traduce `codigo` a los códigos cerrados de `historia_viva.py` y arma las
  cabeceras (`Authorization`, `Idempotency-Key`).
- **El timeout se declara, no se finge.** El cliente entrega el presupuesto al
  transporte en cada llamada. El default de 20 s queda por encima del corte de
  12 s del servidor y es una política separada del presupuesto del LLM.
- **Sólo las consultas se reintentan, y respetando `Retry-After`.** `buscar` y
  `ampliar` reintentan ante `limite_superado`/`servicio_no_disponible` (`429`/
  `503`) esperando lo que pide el servidor; si pide más que
  `espera_maxima_segundos`, el cliente no se queda bloqueado: falla y el
  flujo lo registra. `aportar` no reintenta por default: los aportes no
  forman parte de la demo del 18/11 (#13) y el reintento se habilita con
  `PoliticaCliente.reintentar_aportes`. Ningún `4xx` se reintenta.
- **Pull significa que nada llega solo.** El cliente no registra handlers ni
  sondea: cada llamada de transporte es consecuencia de una llamada del puerto
  `HistoriaViva`, que A1 inicia. Una consulta sin resultados produce una tupla
  vacía, no una afirmación.
- **`url_original` es para una persona.** Apunta a la Pieza en Historia Viva y
  la abre alguien de la FIE con su sesión; el agente la conserva como
  referencia y nunca la sigue.

La efeméride no se consulta: se compone del lado de A1 con
`componer_material_efemeride`, que funciona igual contra este cliente porque el
cliente implementa el mismo puerto. `GET /v1/efemerides` y `GET /v1/relatos`
existen en el contrato pero A1 no los consume.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Protocol, TypeVar

from .historia_viva import (  # noqa: F401 — CONTRACT_* se reexportan: es lo que se valida
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    ESTADO_APORTE,
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

# Ids de `/v1`: prefijo y el patrón del contrato 1.0.0. El UUID lo valida
# Historia Viva; acá alcanza con que el id no pueda escapar de un path.
PIEZA_ID_RE = re.compile(r"pza_[A-Za-z0-9._-]{1,60}\Z")
FRAGMENTO_ID_RE = re.compile(r"frg_[A-Za-z0-9._-]{1,60}\Z")
APORTE_ID_RE = re.compile(r"apt_[A-Za-z0-9._-]{1,60}\Z")
LOTE_ID_RE = re.compile(r"lot_[A-Za-z0-9._-]{1,60}\Z")

# Estado que `/v1` declara para lo que devuelve y para lo que recibe.
ESTADO_PIEZA_V1 = "Validada"
ESTADO_APORTE_V1 = "Pendiente"
MODOS_VALIDACION_V1 = frozenset({"individual", "bloque"})

CAMPOS_FRAGMENTO_V1 = frozenset(
    {
        "fragmento_id",
        "pieza_id",
        "texto",
        "fecha_inicio",
        "fecha_fin",
        "precision_fecha",
        "tipo",
        "resumen_pieza",
        "url_original",
        "validada_el",
        "pagina",
        "seccion",
    }
)
CAMPOS_RESPUESTA_FRAGMENTOS_V1 = frozenset({"total", "limite", "fragmentos"})
CAMPOS_PIEZA_V1 = frozenset(
    {
        "pieza_id",
        "tipo",
        "estado",
        "resumen",
        "texto",
        "fecha_inicio",
        "fecha_fin",
        "precision_fecha",
        "origen",
        "lote_id",
        "lote_nombre",
        "url_original",
        "validada_por",
        "validada_el",
        "modo_validacion",
        "fragmentos",
    }
)
CAMPOS_APORTE_CREADO_V1 = frozenset(
    {"aporte_id", "pieza_id", "estado", "recibido_el", "idempotency_key"}
)

# Códigos que el adapter traduce desde `limite_superado` y
# `servicio_no_disponible`: transitorios, con sentido de reintentar.
# `unauthorized`, `forbidden`, `request_invalid` y `aporte_rechazado` son
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

    `timeout_segundos` es el presupuesto que se le da al transporte por llamada.
    `reintentos` cuenta los intentos *extra* de las operaciones idempotentes.
    Entre intentos se espera el `Retry-After` del servidor y, si no vino,
    `espera_segundos`. Un `Retry-After` mayor que `espera_maxima_segundos` no
    se espera: la falla se propaga (el `503` del interruptor pide 300 s, y un
    flujo de borradores no se bloquea cinco minutos).
    """

    timeout_segundos: float = 20.0
    reintentos: int = 2
    espera_segundos: float = 0.5
    espera_maxima_segundos: float = 30.0
    reintentar_aportes: bool = False

    def __post_init__(self) -> None:
        if self.timeout_segundos <= 0:
            raise ValueError("timeout_segundos debe ser positivo")
        if self.reintentos < 0:
            raise ValueError("reintentos no puede ser negativo")
        if self.espera_segundos < 0:
            raise ValueError("espera_segundos no puede ser negativa")
        if self.espera_maxima_segundos < self.espera_segundos:
            raise ValueError("espera_maxima_segundos no puede ser menor que espera_segundos")


class RelojEspera(Protocol):
    """La espera entre reintentos, inyectada para que el tiempo sea un dato."""

    def dormir(self, segundos: float) -> None: ...


class RelojSistema:
    """Reloj real: el único lugar donde el reintento espera de verdad."""

    def dormir(self, segundos: float) -> None:
        time.sleep(segundos)


@dataclass(frozen=True)
class RespuestaAporte:
    """Cuerpo crudo de `POST /v1/aportes` y si fue un `200` (clave repetida).

    `/v1` devuelve el mismo cuerpo en el `201` y en el `200`: lo único que
    distingue un aporte nuevo de uno ya registrado es el status.
    """

    cuerpo: object
    repetido: bool


class TransporteHistoriaViva(Protocol):
    """Lo que un transporte entrega al cliente.

    Cada operación recibe el timeout por llamada y devuelve el cuerpo crudo
    ya parseado (un `dict`), o `None` en `get_pieza` cuando el servidor
    responde `404 pieza_no_disponible` —inexistente, no validada y retirada
    son indistinguibles por contrato—. Las fallas llegan como
    `HistoriaVivaError` con un código del vocabulario cerrado.
    """

    def get_fragmentos(
        self, consulta: ConsultaFragmentos, *, timeout: float
    ) -> dict[str, Any]: ...

    def get_pieza(self, pieza_id: str, *, timeout: float) -> dict[str, Any] | None: ...

    def post_aporte(self, aporte: Aporte, *, timeout: float) -> RespuestaAporte: ...


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
        respuesta = self._llamar(
            lambda timeout: self._transporte.post_aporte(aporte, timeout=timeout),
            reintentable=self._politica.reintentar_aportes,
        )
        return _recepcion_desde_crudo(
            respuesta.cuerpo,
            repetido=respuesta.repetido,
            clave_enviada=aporte.clave_idempotencia,
        )

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
                espera = (
                    error.reintentar_en
                    if error.reintentar_en is not None
                    else self._politica.espera_segundos
                )
                if espera > self._politica.espera_maxima_segundos:
                    raise
                self._reloj.dormir(espera)
        raise AssertionError("inaccesible")  # pragma: no cover


# --- Validación contra el contrato /v1 ---------------------------------------
#
# Cada `_..._desde_crudo` construye el objeto del dominio o levanta
# `HistoriaVivaError("historia_viva_response_invalid")`. Los `ValueError` de
# los dataclasses —un rango invertido, un id con caracteres prohibidos— se
# colapsan al mismo código: para el pipeline son lo mismo, una respuesta que
# no respeta el contrato.


def _fragmentos_desde_crudo(
    crudo: object, *, limite: int
) -> tuple[Fragmento, ...]:
    campos = _objeto_cerrado(crudo, CAMPOS_RESPUESTA_FRAGMENTOS_V1)
    fragmentos_crudos = campos["fragmentos"]
    if not isinstance(fragmentos_crudos, list):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    # `total` cuenta las coincidencias, no la página: nunca menos que lo recibido.
    _entero(campos["total"], minimo=len(fragmentos_crudos))
    _entero(campos["limite"], minimo=1)
    # El contrato prohíbe devolver más de lo pedido: una página mayor que el
    # límite es una respuesta fuera de forma, no material de más que recortar.
    if len(fragmentos_crudos) > limite or len(fragmentos_crudos) > LIMITE_FRAGMENTOS_MAX:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return tuple(_fragmento_desde_crudo(crudo_) for crudo_ in fragmentos_crudos)


def _pieza_desde_crudo(crudo: object, *, pieza_id_esperada: str) -> Pieza:
    campos = _objeto_cerrado(crudo, CAMPOS_PIEZA_V1)
    # Una pieza cuyo id no es el pedido no es "otra pieza": es una respuesta
    # que no corresponde a la consulta y se rechaza entera.
    if campos["pieza_id"] != pieza_id_esperada or not _id_valido(
        campos["pieza_id"], PIEZA_ID_RE
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    if campos["estado"] != ESTADO_PIEZA_V1:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    if campos["modo_validacion"] not in MODOS_VALIDACION_V1:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    lote_id = campos["lote_id"]
    if lote_id is not None and not _id_valido(lote_id, LOTE_ID_RE):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    _cadena_o_nula(campos["lote_nombre"])
    _cadena(campos["origen"], obligatoria=True)
    _cadena(campos["validada_por"], obligatoria=True)
    fragmentos_crudos = campos["fragmentos"]
    if not isinstance(fragmentos_crudos, list) or len(fragmentos_crudos) > (
        LIMITE_FRAGMENTOS_MAX
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    fragmentos = tuple(_fragmento_desde_crudo(crudo_) for crudo_ in fragmentos_crudos)
    # Un fragmento de otra pieza dentro de esta pieza rompería la cita.
    if any(fragmento.pieza_id != pieza_id_esperada for fragmento in fragmentos):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return Pieza(
            pieza_id=campos["pieza_id"],
            texto=_cadena(campos["texto"], obligatoria=True),
            resumen=_cadena(campos["resumen"]),
            rango=_rango_desde_crudo(campos),
            tipo=_cadena(campos["tipo"], obligatoria=True),
            url_original=_url(campos["url_original"]),
            validada_el=_momento_desde_crudo(campos["validada_el"]),
            fragmentos=fragmentos,
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _recepcion_desde_crudo(
    crudo: object, *, repetido: bool, clave_enviada: str
) -> RecepcionAporte:
    campos = _objeto_cerrado(crudo, CAMPOS_APORTE_CREADO_V1)
    if campos["estado"] != ESTADO_APORTE_V1:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    # El acuse de otra clave no es el acuse de este aporte.
    if campos["idempotency_key"] != clave_enviada:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    if not _id_valido(campos["aporte_id"], APORTE_ID_RE) or not _id_valido(
        campos["pieza_id"], PIEZA_ID_RE
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    _momento_desde_crudo(campos["recibido_el"])
    # El dominio sólo conoce un estado de aporte: `Pendiente` de /v1 es
    # `PENDIENTE_VALIDACION` de A1. Nunca "validado" ni "publicado".
    return RecepcionAporte(
        aporte_id=campos["aporte_id"],
        estado=ESTADO_APORTE,
        duplicado=repetido,
        pieza_id=campos["pieza_id"],
    )


def _fragmento_desde_crudo(crudo: object) -> Fragmento:
    campos = _objeto_cerrado(crudo, CAMPOS_FRAGMENTO_V1)
    if not _id_valido(campos["fragmento_id"], FRAGMENTO_ID_RE) or not _id_valido(
        campos["pieza_id"], PIEZA_ID_RE
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return Fragmento(
            fragmento_id=campos["fragmento_id"],
            pieza_id=campos["pieza_id"],
            texto=_cadena(campos["texto"], obligatoria=True),
            rango=_rango_desde_crudo(campos),
            tipo=_cadena(campos["tipo"], obligatoria=True),
            resumen_pieza=_cadena(campos["resumen_pieza"]),
            url_original=_url(campos["url_original"]),
            validada_el=_momento_desde_crudo(campos["validada_el"]),
            ubicacion=_ubicacion(campos["pagina"], campos["seccion"]),
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _ubicacion(pagina: object, seccion: object) -> str | None:
    """Lugar del pasaje dentro de la pieza, a partir de `pagina` y `seccion`.

    Una planilla trae la hoja en `seccion` y un video la marca `HH:MM:SS`;
    los dos con `pagina` nula. Sin ninguno de los dos no hay ubicación.
    """

    if pagina is not None and (
        not isinstance(pagina, int) or isinstance(pagina, bool) or pagina < 1
    ):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    seccion = _cadena_o_nula(seccion)
    partes = []
    if pagina is not None:
        partes.append(f"p. {pagina}")
    if seccion is not None and seccion.strip():
        partes.append(seccion.strip())
    return ", ".join(partes) or None


def _rango_desde_crudo(campos: dict[str, Any]) -> RangoHistorico:
    precision = campos["precision_fecha"]
    # Una precisión que el catálogo no conoce no se degrada: se rechaza. Peor
    # que perder el fragmento sería presentar su fecha con más exactitud de la
    # que la fuente declaró.
    if precision not in PRECISIONES_FECHA:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return RangoHistorico(
            desde=_fecha_desde_crudo(campos["fecha_inicio"]),
            hasta=_fecha_desde_crudo(campos["fecha_fin"]),
            precision=precision,
        )
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _objeto_cerrado(crudo: object, campos: frozenset[str]) -> dict[str, Any]:
    """Dict con exactamente los campos del contrato, ni uno más ni uno menos.

    Las formas de `/v1` son cerradas (`additionalProperties: false`): un campo
    extra es tan sospechoso como uno que falta, porque una versión distinta
    del servicio no tiene que pasar desapercibida dentro de una respuesta
    parseable.
    """

    if not isinstance(crudo, dict) or set(crudo) != campos:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return crudo


def _id_valido(valor: object, patron: re.Pattern[str]) -> bool:
    return isinstance(valor, str) and patron.fullmatch(valor) is not None


def _entero(valor: object, *, minimo: int) -> int:
    if not isinstance(valor, int) or isinstance(valor, bool) or valor < minimo:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return valor


def _cadena(valor: object, *, obligatoria: bool = False) -> str:
    if not isinstance(valor, str) or (obligatoria and not valor.strip()):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return valor


def _cadena_o_nula(valor: object) -> str | None:
    if valor is None:
        return None
    return _cadena(valor)


def _url(valor: object) -> str:
    """`url_original` se guarda como referencia para una persona; no se sigue."""

    url = _cadena(valor, obligatoria=True)
    if not url.startswith(("http://", "https://")) or any(c.isspace() for c in url):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    return url


def _fecha_desde_crudo(valor: object) -> date:
    if not isinstance(valor, str):
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


def _momento_desde_crudo(valor: object) -> date:
    """Momento RFC 3339 en UTC (`2026-11-10T15:22:41Z`), reducido a su día."""

    if not isinstance(valor, str) or not valor.endswith("Z") or "T" not in valor:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA)
    try:
        return datetime.fromisoformat(valor).date()
    except ValueError:
        raise HistoriaVivaError(_RESPUESTA_INVALIDA) from None


# --- Transporte fake ----------------------------------------------------------

#: Marca de guion: aplica la conducta por defecto —que puede persistir el
#: aporte— y después responde como si la respuesta se hubiera perdido.
#: Reproduce el escenario que la clave de idempotencia existe para resolver.
PERDER_RESPUESTA = object()


class TransporteHistoriaVivaFake:
    """Transporte crudo en memoria: devuelve cuerpos `/v1` como el adapter HTTP.

    A diferencia de `HistoriaVivaFake` —que implementa el puerto ya tipado—
    este fake vive del otro lado de la validación: entrega cuerpos crudos y
    por eso puede servir respuestas fuera de contrato, que es justo lo que el
    cliente tiene que rechazar.

    - `respuestas` fija el cuerpo por defecto de cada operación.
    - `guiones` encola resultados por operación, consumidos en orden: un
      `dict` (o una `RespuestaAporte`) se devuelve, un `HistoriaVivaError` se
      levanta y `PERDER_RESPUESTA` aplica la conducta por defecto y luego falla
      como si la respuesta se hubiera perdido en la red.
    - `llamadas` registra `(operacion, timeout)` de cada intento, para
      verificar reintentos y que el presupuesto declarado llega al transporte.
    - `post_aporte` aplica por defecto la semántica de `Idempotency-Key` de
      `/v1`: misma clave y mismo cuerpo devuelven el acuse original como `200`;
      misma clave con cuerpo distinto es `idempotency_key_reutilizada`.
    """

    def __init__(
        self,
        *,
        respuestas: dict[str, object] | None = None,
        guiones: dict[str, tuple[object, ...]] | None = None,
    ) -> None:
        self._respuestas = dict(respuestas or {})
        self._guiones = {k: list(v) for k, v in (guiones or {}).items()}
        # clave de idempotencia → (huella del cuerpo, acuse original)
        self._aportes: dict[str, tuple[str, dict[str, Any]]] = {}
        self.llamadas: list[tuple[str, float]] = []

    def get_fragmentos(
        self, consulta: ConsultaFragmentos, *, timeout: float
    ) -> dict[str, Any]:
        self.llamadas.append(("get_fragmentos", timeout))
        return self._resolver(
            "get_fragmentos",
            lambda: {"total": 0, "limite": consulta.limite, "fragmentos": []},
        )

    def get_pieza(
        self, pieza_id: str, *, timeout: float
    ) -> dict[str, Any] | None:
        self.llamadas.append(("get_pieza", timeout))
        return self._resolver("get_pieza", lambda: None)

    def post_aporte(self, aporte: Aporte, *, timeout: float) -> RespuestaAporte:
        self.llamadas.append(("post_aporte", timeout))
        resultado = self._resolver("post_aporte", lambda: self._registrar(aporte))
        if isinstance(resultado, RespuestaAporte):
            return resultado
        return RespuestaAporte(cuerpo=resultado, repetido=False)

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

    def _registrar(self, aporte: Aporte) -> RespuestaAporte:
        huella = _huella_aporte(aporte)
        registrado = self._aportes.get(aporte.clave_idempotencia)
        if registrado is not None:
            if registrado[0] != huella:
                # `400 idempotency_key_reutilizada`, colapsado al vocabulario
                # cerrado como un problema del request.
                raise HistoriaVivaError("historia_viva_request_invalid")
            return RespuestaAporte(cuerpo=dict(registrado[1]), repetido=True)
        numero = len(self._aportes) + 1
        acuse = {
            "aporte_id": f"apt_fake-{numero:04d}",
            "pieza_id": f"pza_fake-aporte-{numero:04d}",
            "estado": ESTADO_APORTE_V1,
            "recibido_el": "2026-11-03T14:07:55Z",
            "idempotency_key": aporte.clave_idempotencia,
        }
        self._aportes[aporte.clave_idempotencia] = (huella, acuse)
        return RespuestaAporte(cuerpo=dict(acuse), repetido=False)


def _huella_aporte(aporte: Aporte) -> str:
    """Huella del cuerpo del aporte, sin la clave: es lo que la clave cubre."""

    cuerpo = {
        "tipo_contenido": aporte.tipo_contenido,
        "canal": aporte.canal,
        "titulo": aporte.titulo,
        "cuerpo": aporte.cuerpo,
        "piezas_fuente": list(aporte.piezas_fuente),
        "fragmentos_fuente": list(aporte.fragmentos_fuente),
    }
    serializado = json.dumps(
        cuerpo, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()
