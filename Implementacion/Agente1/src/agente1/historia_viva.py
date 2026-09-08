"""Puerto de consulta a Historia Viva (Agente 2), y composición del lado de A1.

Historia Viva custodia el acervo histórico validado. El Agente 1 lo consulta
para redactar; no al revés.

Decisiones que no se ven en el código:

- **A1 siempre inicia.** El puerto sólo tiene métodos que A1 llama. No hay
  registro de callbacks, ni webhook, ni cola entrante: que esa capacidad no
  exista es el control, no un pendiente. El envelope push candidato de
  `insumos_agentes.py` va en la dirección contraria y no se usa acá.
- **Historia Viva no redacta.** Devuelve fragmentos citables, no prosa. Por eso
  no existe un tipo `Efemeride` que llegue del otro lado: la efeméride la
  compone A1 con `componer_material_efemeride`, a partir de una búsqueda por
  período. Si el material llegara redactado, A1 estaría publicando texto de
  otro agente sin poder citarlo ni someterlo a su propia validación.
- **La precisión de fecha es un control, no un metadato.** Una pieza cuya
  precisión es `mes`, `anio` o `decada` no puede presentarse como una fecha
  exacta. `RangoHistorico.expresion_temporal` sólo devuelve lo que la precisión
  sostiene, y es la única manera de obtener una fecha para redactar: no hay un
  atributo de fecha suelto que se pueda formatear por afuera.
- **Sin material no hay afirmación.** `MaterialEfemeride.afirmaciones` deriva
  de los fragmentos recuperados. Con material vacío devuelve una tupla vacía:
  quien redacte a partir de ahí no tiene nada que decir, en lugar de tener un
  hueco que el modelo pueda rellenar.
- **Los errores se cierran a un vocabulario conocido.** Como en los demás
  adapters, ningún mensaje remoto llega al log: `HistoriaVivaError` lleva un
  código de una allowlist y nada más.
- **El aporte nace pendiente.** `registrar_aporte` no tiene forma de declarar
  un aporte validado ni publicado, y la clave de idempotencia es obligatoria
  porque un POST reintentado a ciegas duplica el aporte.

Este seam es offline y no fija el transporte: `insumos_agentes.py` sigue siendo
el contrato candidato inbound, y el cliente HTTP definitivo depende del
contrato con Ignacio (issue #17), que todavía no está cerrado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Protocol


CONTRACT_VERSION = "historia_viva_consulta_candidate_v1"
CONTRACT_STATUS = "CANDIDATO_NO_INSTITUCIONAL"

# Límite y tope de la búsqueda, según la propuesta respondida en
# `respuesta-nacho.md`. El tope se aplica acá y no sólo del lado remoto: A1 no
# debería poder pedir una página que no piensa citar.
LIMITE_FRAGMENTOS_DEFAULT = 10
LIMITE_FRAGMENTOS_MAX = 50

# Precisión declarada de un rango histórico, de la más fina a la más gruesa.
# El orden importa: `expresion_temporal` decide cuánto puede decir a partir de
# él, y una precisión desconocida no se degrada en silencio, se rechaza.
PRECISIONES_FECHA = ("dia", "mes", "anio", "decada")

MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

# Mismo criterio que el resto del proyecto: identificadores acotados antes de
# que lleguen a un path, una URL o un registro de auditoría.
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")

# Vocabulario cerrado de fallas. Un adapter que devuelva otra cosa se registra
# como `historia_viva_unavailable`, para que la auditoría no reciba texto
# remoto arbitrario.
CODIGOS_ERROR = frozenset(
    {
        "historia_viva_unauthorized",
        "historia_viva_forbidden",
        "historia_viva_rate_limited",
        "historia_viva_unavailable",
        "historia_viva_response_invalid",
        "historia_viva_request_invalid",
    }
)

TIPOS_CONTENIDO_APORTE = frozenset({"gacetilla", "post", "newsletter", "mail"})
CANALES_APORTE = frozenset({"instagram", "linkedin", "web", "correo", "ninguno"})
# Único estado que A1 puede declarar al registrar un aporte. No existe
# "publicado": el MVP produce borradores y no conoce una URL final.
ESTADO_APORTE = "PENDIENTE_VALIDACION"


class HistoriaVivaError(RuntimeError):
    """Falla de consulta, reducida a un código conocido.

    No transporta el mensaje remoto ni el cuerpo de la respuesta: el pipeline
    sólo necesita saber que Historia Viva no entregó material utilizable, y
    cualquier detalle podría arrastrar contenido no validado hacia el log.
    """

    def __init__(self, code: str) -> None:
        self.code = code if code in CODIGOS_ERROR else "historia_viva_unavailable"
        super().__init__(self.code)


@dataclass(frozen=True)
class RangoHistorico:
    """Cuándo pasó algo, y con cuánta certeza se sabe.

    Un rango sin precisión declarada no se admite: sería una fecha que parece
    exacta y no lo es, que es justo el error que este tipo existe para impedir.
    """

    desde: date
    hasta: date
    precision: str

    def __post_init__(self) -> None:
        if self.precision not in PRECISIONES_FECHA:
            raise ValueError("precision de fecha inválida")
        if self.hasta < self.desde:
            raise ValueError("rango histórico invertido")

    @property
    def es_fecha_exacta(self) -> bool:
        """Sólo un día declarado como tal es una fecha exacta."""

        return self.precision == "dia" and self.desde == self.hasta

    def expresion_temporal(self) -> str:
        """Cómo se puede nombrar este rango sin afirmar de más.

        Es la única forma de obtener una fecha para redactar. Devolver el
        `date` crudo permitiría formatearlo como día exacto aunque la precisión
        fuera de década, que es exactamente la afirmación sin sustento que hay
        que evitar.
        """

        if self.es_fecha_exacta:
            return f"{self.desde.day} de {MESES[self.desde.month - 1]} de {self.desde.year}"
        if self.precision == "dia":
            return (
                f"entre el {self.desde.day} de {MESES[self.desde.month - 1]} "
                f"de {self.desde.year} y el {self.hasta.day} de "
                f"{MESES[self.hasta.month - 1]} de {self.hasta.year}"
            )
        if self.precision == "mes":
            if (self.desde.year, self.desde.month) == (self.hasta.year, self.hasta.month):
                return f"{MESES[self.desde.month - 1]} de {self.desde.year}"
            return (
                f"entre {MESES[self.desde.month - 1]} de {self.desde.year} y "
                f"{MESES[self.hasta.month - 1]} de {self.hasta.year}"
            )
        if self.precision == "anio":
            if self.desde.year == self.hasta.year:
                return str(self.desde.year)
            return f"entre {self.desde.year} y {self.hasta.year}"
        decada_desde = self.desde.year - self.desde.year % 10
        decada_hasta = self.hasta.year - self.hasta.year % 10
        if decada_desde == decada_hasta:
            return f"la década de {decada_desde}"
        return f"entre las décadas de {decada_desde} y {decada_hasta}"


@dataclass(frozen=True)
class Fragmento:
    """Un pasaje citable de una pieza validada.

    `fragmento_id` y `ubicacion` existen porque `pieza_id` identifica el
    documento pero no el pasaje que fundamenta una afirmación. Sin ellos, una
    cita no se puede verificar contra la fuente.
    """

    fragmento_id: str
    pieza_id: str
    texto: str
    rango: RangoHistorico
    tipo: str
    resumen_pieza: str
    url_original: str
    validada_el: date
    ubicacion: str | None = None

    def __post_init__(self) -> None:
        if not ID_RE.fullmatch(self.fragmento_id) or not ID_RE.fullmatch(self.pieza_id):
            raise ValueError("identificador de fragmento inválido")
        if not self.texto.strip():
            raise ValueError("fragmento sin texto")

    def cita(self) -> str:
        """Referencia verificable del pasaje, no del documento entero."""

        ubicacion = f", {self.ubicacion}" if self.ubicacion else ""
        return f"{self.pieza_id}{ubicacion} ({self.rango.expresion_temporal()})"


@dataclass(frozen=True)
class Pieza:
    """Una pieza completa del acervo, para ampliar una recuperación corta."""

    pieza_id: str
    titulo: str
    resumen: str
    rango: RangoHistorico
    tipo: str
    url_original: str
    validada_el: date
    fragmentos: tuple[Fragmento, ...] = ()

    def __post_init__(self) -> None:
        if not ID_RE.fullmatch(self.pieza_id):
            raise ValueError("identificador de pieza inválido")


@dataclass(frozen=True)
class ConsultaFragmentos:
    """Qué se le pide a Historia Viva.

    `desde`/`hasta` son opcionales por separado para poder pedir "todo lo
    anterior a" o "todo lo posterior a"; el tope de resultados no lo es.
    """

    texto: str | None = None
    desde: date | None = None
    hasta: date | None = None
    tipo: str | None = None
    limite: int = LIMITE_FRAGMENTOS_DEFAULT

    def __post_init__(self) -> None:
        if not 1 <= self.limite <= LIMITE_FRAGMENTOS_MAX:
            raise ValueError(f"limite debe estar entre 1 y {LIMITE_FRAGMENTOS_MAX}")
        if self.desde is not None and self.hasta is not None and self.hasta < self.desde:
            raise ValueError("rango de consulta invertido")
        if self.texto is None and self.desde is None and self.hasta is None:
            raise ValueError("la consulta necesita texto o período")


@dataclass(frozen=True)
class Aporte:
    """Lo que A1 devuelve al acervo después de redactar.

    `clave_idempotencia` es obligatoria: sin ella, un POST reintentado tras una
    respuesta perdida duplica el aporte. `piezas_fuente` también, porque un
    aporte sin procedencia no se puede validar contra nada.
    """

    clave_idempotencia: str
    tipo_contenido: str
    canal: str
    titulo: str
    cuerpo: str
    piezas_fuente: tuple[str, ...]

    def __post_init__(self) -> None:
        if not ID_RE.fullmatch(self.clave_idempotencia):
            raise ValueError("clave de idempotencia inválida")
        if self.tipo_contenido not in TIPOS_CONTENIDO_APORTE:
            raise ValueError("tipo de contenido inválido")
        if self.canal not in CANALES_APORTE:
            raise ValueError("canal inválido")
        if not self.titulo.strip() or not self.cuerpo.strip():
            raise ValueError("aporte sin título o sin cuerpo")
        if not self.piezas_fuente:
            raise ValueError("aporte sin piezas fuente")
        if any(not ID_RE.fullmatch(pieza) for pieza in self.piezas_fuente):
            raise ValueError("pieza fuente inválida")


@dataclass(frozen=True)
class RecepcionAporte:
    """Acuse de Historia Viva. Nunca dice "validado" ni "publicado"."""

    aporte_id: str
    estado: str = ESTADO_APORTE
    duplicado: bool = False

    def __post_init__(self) -> None:
        if self.estado != ESTADO_APORTE:
            raise ValueError("un aporte sólo puede quedar pendiente de validación")


class HistoriaViva(Protocol):
    """Puerto único: buscar, ampliar y aportar.

    Tres operaciones y ninguna más. En particular no hay `suscribir`,
    `recibir` ni nada que permita a Historia Viva empujar contenido hacia A1.
    """

    def buscar_fragmentos(
        self, consulta: ConsultaFragmentos
    ) -> tuple[Fragmento, ...]: ...

    def obtener_pieza(self, pieza_id: str) -> Pieza | None: ...

    def registrar_aporte(self, aporte: Aporte) -> RecepcionAporte: ...


@dataclass(frozen=True)
class MaterialEfemeride:
    """Lo que A1 tiene para escribir una efeméride, y nada más.

    No trae prosa. Trae los pasajes recuperados y la manera segura de nombrar
    su fecha. Si la búsqueda no devolvió nada, `afirmaciones` queda vacía: quien
    redacte a partir de acá no tiene un hueco para rellenar, tiene ausencia de
    material.
    """

    rango_consultado: RangoHistorico
    fragmentos: tuple[Fragmento, ...] = field(default_factory=tuple)

    @property
    def hay_material(self) -> bool:
        return bool(self.fragmentos)

    def afirmaciones(self) -> tuple[tuple[str, str], ...]:
        """Pares de texto citable y su cita verificable."""

        return tuple(
            (fragmento.texto, fragmento.cita()) for fragmento in self.fragmentos
        )

    def piezas_fuente(self) -> tuple[str, ...]:
        """Piezas distintas que respaldan el material, en orden de aparición."""

        vistas: list[str] = []
        for fragmento in self.fragmentos:
            if fragmento.pieza_id not in vistas:
                vistas.append(fragmento.pieza_id)
        return tuple(vistas)


def componer_material_efemeride(
    cliente: HistoriaViva,
    *,
    desde: date,
    hasta: date,
    precision: str = "dia",
    tema: str | None = None,
    limite: int = LIMITE_FRAGMENTOS_DEFAULT,
) -> MaterialEfemeride:
    """Arma el material de una efeméride desde el lado de A1.

    Es una búsqueda por período, no un pedido de efeméride: Historia Viva no
    sabe que esto va a ser una efeméride, y no debería. `tema` se agrega sólo
    cuando la solicitud lo determina; para una efeméride pura alcanza el
    período, porque inventar un tipo de pieza sería decidir por la fuente.

    Una falla de Historia Viva se propaga como `HistoriaVivaError`: el material
    incompleto no se disimula con una efeméride sin sustento.
    """

    consulta = ConsultaFragmentos(
        texto=tema,
        desde=desde,
        hasta=hasta,
        limite=limite,
    )
    fragmentos = cliente.buscar_fragmentos(consulta)
    return MaterialEfemeride(
        rango_consultado=RangoHistorico(desde=desde, hasta=hasta, precision=precision),
        fragmentos=tuple(fragmentos),
    )


class HistoriaVivaFake:
    """Implementación en memoria del puerto, sin red ni credenciales.

    Sirve para ejercitar el seam completo —búsqueda, ampliación y aporte— antes
    de que exista el transporte, y para probar las fallas que importan sin
    simular HTTP: un adapter real las va a colapsar a los mismos códigos.

    `falla_en` fuerza el error de una operación concreta en lugar de romper
    todo el cliente, porque los casos interesantes son parciales: la búsqueda
    anda y el aporte no, o al revés.
    """

    def __init__(
        self,
        *,
        fragmentos: tuple[Fragmento, ...] = (),
        piezas: tuple[Pieza, ...] = (),
        falla_en: dict[str, str] | None = None,
    ) -> None:
        self._fragmentos = tuple(fragmentos)
        self._piezas = {pieza.pieza_id: pieza for pieza in piezas}
        self._falla_en = dict(falla_en or {})
        # Clave de idempotencia → aporte ya recibido. Es lo que hace que un
        # reintento devuelva el mismo id en lugar de crear otro aporte.
        self._aportes: dict[str, str] = {}
        self.consultas: list[ConsultaFragmentos] = []

    def _fallar_si_corresponde(self, operacion: str) -> None:
        codigo = self._falla_en.get(operacion)
        if codigo is not None:
            raise HistoriaVivaError(codigo)

    def buscar_fragmentos(self, consulta: ConsultaFragmentos) -> tuple[Fragmento, ...]:
        self._fallar_si_corresponde("buscar_fragmentos")
        self.consultas.append(consulta)
        encontrados = [
            fragmento
            for fragmento in self._fragmentos
            if _coincide(fragmento, consulta)
        ]
        return tuple(encontrados[: consulta.limite])

    def obtener_pieza(self, pieza_id: str) -> Pieza | None:
        self._fallar_si_corresponde("obtener_pieza")
        # `None` cubre tanto "no existe" como "no está validada": el contrato
        # acordado responde 404 en los dos casos, sin revelar cuál ocurrió.
        return self._piezas.get(pieza_id)

    def registrar_aporte(self, aporte: Aporte) -> RecepcionAporte:
        self._fallar_si_corresponde("registrar_aporte")
        existente = self._aportes.get(aporte.clave_idempotencia)
        if existente is not None:
            return RecepcionAporte(aporte_id=existente, duplicado=True)
        aporte_id = f"apo-{len(self._aportes) + 1:04d}"
        self._aportes[aporte.clave_idempotencia] = aporte_id
        return RecepcionAporte(aporte_id=aporte_id)


def _coincide(fragmento: Fragmento, consulta: ConsultaFragmentos) -> bool:
    """Filtro del fake: período, tipo y coincidencia textual simple.

    No pretende imitar la búsqueda semántica del servicio real. Alcanza para
    distinguir "hay material" de "no hay material", que es la decisión que el
    lado de A1 tiene que tomar bien.
    """

    if consulta.desde is not None and fragmento.rango.hasta < consulta.desde:
        return False
    if consulta.hasta is not None and fragmento.rango.desde > consulta.hasta:
        return False
    if consulta.tipo is not None and fragmento.tipo != consulta.tipo:
        return False
    if consulta.texto is not None:
        aguja = consulta.texto.casefold()
        pajar = f"{fragmento.texto} {fragmento.resumen_pieza}".casefold()
        if aguja not in pajar:
            return False
    return True
