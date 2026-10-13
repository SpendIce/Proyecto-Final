"""Medición del nivel verificado de los SLO desde la auditoría (#88).

Calcula los cinco indicadores de la resolución de #65 sobre los registros
que la operación ya deja, sin tocar la red ni escribir en las fuentes:

- **Disponibilidad** — `logs/scheduler-corridas.jsonl` (#84) contra la
  agenda que la configuración `AGENTE1_SCHEDULER_*` declara. El
  denominador no son las líneas del log sino los **ticks esperados** del
  rango (`desde + k * intervalo` en los días y horario de la ventana):
  una corrida programada que nunca se disparó no deja línea, y medir sólo
  lo disparado escondería el hueco. Un tick cuenta `completada a tiempo`
  si existe una entrada `en_ventana` con `resultado == "completada"` y
  `fin <= inicio_previsto + intervalo` —la corrida cerró dentro de su
  slot—; una `completada` que pasó el slot se reporta aparte
  (`completadas_tardias`) y no entra al numerador.
- **Tiempo de atención** — `atendidos-canal-form.jsonl` tiene el instante
  en que el pedido quedó respondido (`timestamp`, escrito tras el intento
  de aviso), pero la marca temporal del Form **no se persiste**: entra al
  hash de `id_pedido` por diseño anti-PII. El ancla de envío sale entonces
  de un CSV de respuestas del Form que el operador exporta a la fecha de
  corte: el script recomputa `id_pedido` como `canal_form` lo hace
  (`sha256(marca|correo|texto)`) y cruza por ese id, sin persistir marca,
  correo ni prosa. Sin CSV el indicador se declara `sin_fuente`, nunca se
  aproxima.
- **Latencia por pieza** — `latencia_s` de las líneas
  `PENDIENTE_VALIDACION` por tipo (gacetilla HU-010 y post HU-011 en
  `logs/ejecuciones.jsonl`; plantilla de correo por actividad HU-012 en
  `logs/plantillas-actividad.jsonl`). El objetivo numérico queda
  declarado `pendiente #50/#51`: el script reporta lo medido, no un tope
  inventado. La línea descriptiva (`lineas-descriptivas.jsonl`) no lleva
  `latencia_s` y el certificado se renderiza determinista: ambos quedan
  como huecos explícitos.
- **Aprobación → envío** — el circuito de lote por actividad (#73) es el
  único que deja las dos anclas: las tres decisiones exigidas
  (`apruebo_semantica` + `apruebo_utilitaria` sobre `tpl-…` y
  `apruebo_lote` sobre `lote-…`) con su `timestamp` en
  `decisiones-procesadas.jsonl`, y el envío en el `actualizado_en` del
  registro durable cuando el ítem queda `ENVIADA_SIMULADA`. El ancla de
  aprobación es el `timestamp` de la última decisión requerida registrada
  (el momento en que el agente la asentó; la `marca_temporal_form` se
  conserva pero es la fecha de la hoja, sin zona declarada). El tiempo se
  mide **dentro de la ventana de operación**: fuera de ella no hay
  compromiso y lo aprobado sale en la primera corrida de la siguiente
  (#65). `ENVIO_INDETERMINADO` y `EMISION_INDETERMINADA` cuentan como
  incidentes y quedan fuera de la muestra; `FALLIDA` se reporta aparte.
  Los ítems encolados por el circuito de recordatorios o la confirmación
  individual quedan `sin_ancla`: su aprobación viaja como
  `AprobacionHumana` y la auditoría sólo conserva su hash — hueco
  declarado.
- **Integridad del gate** — tres verificaciones sobre lo ya escrito: (a)
  ninguna línea `PENDIENTE_VALIDACION` de los logs de generación lleva
  `validation_errors` no vacío; (b) todo archivo de `borradores/` debe
  cuyo `sha256` figure como `output_hash` de una línea
  `PENDIENTE_VALIDACION` —un archivo que sólo matchea una línea no
  conforme, o ninguna, es una pieza presentada a validación sin gate—;
  (c) todo ítem del registro durable en `ENVIADA_SIMULADA` debe tener
  traza de su gate de envío: una línea `encolado_lote` bajo una
  `autorizacion_lote` `AUTORIZADA` (lote por actividad o recordatorios),
  o una línea de `confirmaciones-hu012.jsonl` con la aprobación presente
  (`human_decision_present` / `approval_role`) para esa clave.
  `EMITIDA_SIMULADA` no se exige traza acá: el circuito de emisión de
  certificados no deja auditoría por clave — hueco declarado, no
  violación.

Reglas de muestra: `muestra_minima` (default 20) es la convención
declarada del medidor, configurable por el operador, nunca un dato
institucional. Un indicador con `n < muestra_minima` reporta los números
parciales y declara `muestra insuficiente (n=...)` en `nivel_verificado`;
`n == 0` o fuente ausente/ilegible declara `sin_fuente` con el hueco.

Nada acá mide contenido: las fuentes sólo aportan hashes, estados y
fechas, igual que en el resto de la auditoría.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .canal_form import ATENDIDOS_NOMBRE
from .confirmaciones import CLAVE_REGISTRO_RE, email_valido
from .decisiones_form import PROCESADAS_NOMBRE
from .scheduler import LOG_NOMBRE as SCHEDULER_LOG
from .scheduler import ConfiguracionScheduler

REGISTRO_FORMATO = "nivel_verificado_slo_v1"
MUESTRA_MINIMA_DEFAULT = 20
HOLGURA_AVISO_S = 300  # "+ 5 min" del objetivo de tiempo de atención (#65)

LOG_EJECUCIONES = "ejecuciones.jsonl"
LOG_PLANTILLAS = "plantillas-actividad.jsonl"
LOG_LINEAS = "lineas-descriptivas.jsonl"
LOG_LOTES = "lotes-actividad.jsonl"
LOG_RECORDATORIOS = "recordatorios-hu012.jsonl"
LOG_CONFIRMACIONES = "confirmaciones-hu012.jsonl"
ATENDIDOS_VERSION = "canal_form_atendidos_v1"

ESTADO_PRESENTADA = "PENDIENTE_VALIDACION"
RESULTADOS_CONFORMES = frozenset({"borrador_generado", "linea_generada"})
ESTADOS_ENVIO_INCIDENTE = frozenset(
    {"ENVIO_INDETERMINADO", "EMISION_INDETERMINADA", "FALLIDA"}
)
ESTADOS_ENVIO_ENTREGADO = frozenset({"ENVIADA_SIMULADA", "EMITIDA_SIMULADA"})

# Tipos de pieza con generación por modelo: nombre público del tipo y los
# identificadores que lo marcan en cada log. La línea descriptiva entra a
# la lista con su propio hueco (su log no registra `latencia_s`).
PIEZAS_GENERADAS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("gacetilla", LOG_EJECUCIONES, ("HU-010",)),
    ("post", LOG_EJECUCIONES, ("HU-011",)),
    ("plantilla_correo_actividad", LOG_PLANTILLAS, ("HU-012",)),
    ("linea_descriptiva", LOG_LINEAS, ("HU-014",)),
)

_MARCA_NAIVE_RE = re.compile(
    r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})[ T]"
    r"(?P<hh>\d{1,2}):(?P<mm>\d{1,2})(?::(?P<ss>\d{1,2}))?\Z"
)
_MARCA_US_RE = re.compile(
    r"(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{4})[ T]"
    r"(?P<hh>\d{1,2}):(?P<mm>\d{1,2})(?::(?P<ss>\d{1,2}))?\Z"
)


@dataclass(frozen=True)
class FuentesAuditoria:
    """Ubicación de cada registro que la medición lee.

    `directorio` es la salida de la operación: contiene `logs/` y
    `borradores/`. `estado_canal`, `estado_decisiones` y
    `registro_confirmaciones` son los directorios de estado que los
    runners crean bajo ese directorio; se pasan aparte porque en la
    disposición de la demo pueden vivir en otro lado. `respuestas_csv` es
    la exportación del Form de pedidos que el ancla de tiempo de atención
    necesita; `None` deja el indicador declarado `sin_fuente`.
    """

    directorio: Path
    estado_canal: Path | None = None
    estado_decisiones: Path | None = None
    registro_confirmaciones: Path | None = None
    respuestas_csv: Path | None = None


@dataclass(frozen=True)
class LecturaLog:
    """Una fuente JSONL ya leída: entradas dict o un código de falla."""

    entradas: tuple[dict[str, Any], ...]
    estado: str = "ok"  # "ok" | "ausente" | "invalida"


def _leer_jsonl(path: Path | None) -> LecturaLog:
    """Lee un log JSONL; un archivo ilegible se declara, no se adivina."""

    if path is None or not path.is_file():
        return LecturaLog((), "ausente")
    entradas: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8", newline="") as archivo:
            for linea in archivo:
                texto = linea.strip()
                if not texto:
                    continue
                valor = json.loads(texto)
                if not isinstance(valor, dict):
                    return LecturaLog((), "invalida")
                entradas.append(valor)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return LecturaLog((), "invalida")
    return LecturaLog(tuple(entradas))


def _parsear_instante(valor: object) -> datetime | None:
    """ISO-8601 aware o `None`: un instante sin zona no es comparable."""

    if not isinstance(valor, str):
        return None
    try:
        instante = datetime.fromisoformat(valor)
    except ValueError:
        return None
    return instante if instante.tzinfo is not None else None


def _parsear_marca_form(valor: object, config: ConfiguracionScheduler) -> datetime | None:
    """La marca temporal del Form: ISO naive (en la zona de la ventana) o US.

    La hoja entrega la marca sin zona; la interpretación declarada es la
    zona de la ventana de operación, porque es la referencia horaria que
    el sistema usa para todo lo demás. Cualquier otra forma queda
    `None` y se cuenta como `marcas_no_parseables`.
    """

    if not isinstance(valor, str) or not valor.strip():
        return None
    texto = valor.strip()
    try:
        instante = datetime.fromisoformat(texto)
        if instante.tzinfo is not None:
            return instante
        return instante.replace(tzinfo=config.zona)
    except ValueError:
        pass
    for patron in (_MARCA_NAIVE_RE, _MARCA_US_RE):
        match = patron.fullmatch(texto)
        if match is None:
            continue
        try:
            return datetime(
                int(match["y"]),
                int(match["m"]),
                int(match["d"]),
                int(match["hh"]),
                int(match["mm"]),
                int(match["ss"] or 0),
                tzinfo=config.zona,
            )
        except ValueError:
            return None
    return None


def _fecha_local(instante: datetime, config: ConfiguracionScheduler) -> date:
    return instante.astimezone(config.zona).date()


def _en_rango(
    instante: datetime | None,
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    corte: datetime | None = None,
) -> bool:
    """El evento entra a la muestra si su fecha local cae en `[desde, hasta]`
    y, cuando hay `corte`, no es posterior a ese instante: un tick o un
    envío que todavía no ocurrió al cortar no es una observación.
    """

    if instante is None:
        return False
    if corte is not None and instante > corte:
        return False
    return desde <= _fecha_local(instante, config) <= hasta


def _percentil(valores: list[float], q: float) -> float | None:
    """Percentil con interpolación lineal (posición `(n-1)*q`).

    Con muestras chicas el p95 coincide con el máximo: se reporta igual,
    la declaración de `muestra_minima` es la que evita leerlo como nivel.
    """

    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    posicion = (len(ordenados) - 1) * q
    piso = int(posicion)
    if piso >= len(ordenados) - 1:
        return ordenados[-1]
    fraccion = posicion - piso
    return ordenados[piso] + (ordenados[piso + 1] - ordenados[piso]) * fraccion


def _estadisticas(valores: list[float]) -> dict[str, Any]:
    if not valores:
        return {"n": 0, "p95_s": None, "min_s": None, "max_s": None}
    return {
        "n": len(valores),
        "p95_s": round(_percentil(valores, 0.95) or 0.0, 3),
        "min_s": round(min(valores), 3),
        "max_s": round(max(valores), 3),
    }


def ticks_agenda(
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    corte: datetime | None = None,
) -> list[datetime]:
    """Los ticks que la agenda declara en el rango, aware en `config.zona`.

    Con `corte` sólo entran los ticks que ya debieron ocurrir a ese
    instante: medir «hoy» al mediodía no puede contar como corridas
    programadas las que la agenda declara para la tarde.
    """

    ticks: list[datetime] = []
    dia = desde
    while dia <= hasta:
        if dia.isoweekday() in config.dias:
            tick = datetime.combine(dia, config.desde, tzinfo=config.zona)
            cierre = datetime.combine(dia, config.hasta, tzinfo=config.zona)
            while tick < cierre:
                if corte is None or tick <= corte:
                    ticks.append(tick)
                tick += timedelta(seconds=config.intervalo_s)
        dia += timedelta(days=1)
    return ticks


def segundos_en_ventana(
    inicio: datetime, fin: datetime, config: ConfiguracionScheduler
) -> float:
    """Segundos de `[inicio, fin)` que caen dentro de la ventana.

    Es el reloj del compromiso: fuera de la ventana el SLO no corre, así
    que una aprobación hecha un sábado mide desde el lunes 8:00, no desde
    el sábado.
    """

    inicio_local = inicio.astimezone(config.zona)
    fin_local = fin.astimezone(config.zona)
    if fin_local <= inicio_local:
        return 0.0
    total = 0.0
    dia = inicio_local.date()
    while dia <= fin_local.date():
        if dia.isoweekday() in config.dias:
            apertura = datetime.combine(dia, config.desde, tzinfo=config.zona)
            cierre = datetime.combine(dia, config.hasta, tzinfo=config.zona)
            borde_inf = max(inicio_local, apertura)
            borde_sup = min(fin_local, cierre)
            if borde_sup > borde_inf:
                total += (borde_sup - borde_inf).total_seconds()
        dia += timedelta(days=1)
    return total


def _resultado_indicador(
    *,
    slo: str,
    definicion: str,
    objetivo: str,
    unidad: str,
    muestra: int,
    muestra_minima: int,
    valor: float | None,
    cumple: bool | None,
    detalle: Mapping[str, Any],
    huecos: tuple[str, ...] = (),
) -> dict[str, Any]:
    """La forma común de cada indicador del reporte.

    `nivel` es lo medido (proporción o segundos); `nivel_verificado` es la
    declaración publicable: el número, `muestra insuficiente (n=...)`,
    `sin_fuente` o `pendiente #50/#51`. `cumple` es `None` cuando el
    objetivo no está fijado o la muestra no alcanza: la celda no afirma
    ni cumplimiento ni incumplimiento.
    """

    if valor is None:
        nivel_verificado = "sin_fuente"
    elif muestra < muestra_minima:
        nivel_verificado = f"muestra insuficiente (n={muestra})"
    else:
        nivel_verificado = (
            f"{valor:.4f}" if unidad == "proporcion" else f"{valor:.3f} s"
        )
    return {
        "slo": slo,
        "definicion": definicion,
        "objetivo": objetivo,
        "unidad": unidad,
        "muestra_minima": muestra_minima,
        "n": muestra,
        "nivel": valor,
        "nivel_verificado": nivel_verificado,
        "cumple": cumple,
        "detalle": dict(detalle),
        "huecos": list(huecos),
    }


def _indicador_sin_fuente(
    *,
    slo: str,
    definicion: str,
    objetivo: str,
    unidad: str,
    detalle: Mapping[str, Any],
    huecos: tuple[str, ...],
    muestra_minima: int,
    muestra: int = 0,
) -> dict[str, Any]:
    return _resultado_indicador(
        slo=slo,
        definicion=definicion,
        objetivo=objetivo,
        unidad=unidad,
        muestra=muestra,
        muestra_minima=muestra_minima,
        valor=None,
        cumple=None,
        detalle=detalle,
        huecos=huecos,
    )


# ---------------------------------------------------------------------------
# Disponibilidad
# ---------------------------------------------------------------------------


def indicador_disponibilidad(
    *,
    entradas: tuple[dict[str, Any], ...],
    estado_fuente: str,
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    muestra_minima: int,
    corte: datetime | None = None,
) -> dict[str, Any]:
    """Corridas programadas completadas a tiempo / corridas programadas.

    El denominador es la agenda: los ticks que la ventana declara en el
    rango, exista o no línea de disparo. `en_ventana` separa el disparo
    programado del tardío; el previsto de cada entrada se compara contra
    la agenda reconstruida, así una línea de otra configuración o de otro
    rango no contamina el conteo.
    """

    definicion = (
        "corridas programadas completadas a tiempo / corridas "
        "programadas, dentro de la ventana de operación"
    )
    if estado_fuente in ("ausente", "invalida"):
        # Sin log no hay forma de distinguir «no corrió nada» de «corrió
        # y no quedó registro»: se declara la fuente, no el número.
        return _indicador_sin_fuente(
            slo="disponibilidad",
            definicion=definicion,
            objetivo="99 %",
            unidad="proporcion",
            detalle={"fuente": f"logs/{SCHEDULER_LOG}", "estado_fuente": estado_fuente},
            huecos=(f"log de corridas del scheduler {estado_fuente}",),
            muestra_minima=muestra_minima,
        )

    esperados = ticks_agenda(desde, hasta, config, corte)
    ticks_esperados = {tick.isoformat() for tick in esperados}

    por_tick: dict[str, list[dict[str, Any]]] = {}
    fuera_de_agenda = 0
    fuera_de_ventana = 0
    for entrada in entradas:
        if entrada.get("record") != "scheduler_corrida_v1":
            continue
        if entrada.get("en_ventana") is not True:
            fuera_de_ventana += 1
            continue
        previsto = entrada.get("inicio_previsto")
        instante_previsto = _parsear_instante(previsto)
        if instante_previsto is None:
            continue
        if instante_previsto.isoformat() not in ticks_esperados:
            fuera_de_agenda += 1
            continue
        por_tick.setdefault(instante_previsto.isoformat(), []).append(entrada)

    a_tiempo = 0
    tardias = 0
    falladas = 0
    omitidas = 0
    atrasos: list[float] = []
    duraciones: list[float] = []
    for tick in ticks_esperados:
        previsto_dt = _parsear_instante(tick)
        if previsto_dt is None:
            continue
        entradas_tick = por_tick.get(tick, [])
        completadas = [
            e for e in entradas_tick if e.get("resultado") == "completada"
        ]
        if completadas:
            # El tick cumple si alguna de sus corridas cerró dentro del
            # slot: puede tener además una falla previa o una omitida.
            limite = previsto_dt + timedelta(seconds=config.intervalo_s)
            en_slot = False
            for entrada in completadas:
                inicio = _parsear_instante(entrada.get("inicio_real"))
                fin = _parsear_instante(entrada.get("fin"))
                if inicio is None or fin is None:
                    continue
                atrasos.append((inicio - previsto_dt).total_seconds())
                duraciones.append((fin - inicio).total_seconds())
                if fin <= limite:
                    en_slot = True
            if en_slot:
                a_tiempo += 1
            else:
                tardias += 1
        elif any(e.get("resultado") == "falla" for e in entradas_tick):
            falladas += 1
        elif entradas_tick:
            omitidas += 1

    sin_disparo = len(ticks_esperados) - len(por_tick)
    nivel = (a_tiempo / len(esperados)) if esperados else None
    cumple = (
        (nivel is not None and nivel >= 0.99)
        if len(esperados) >= muestra_minima
        else None
    )
    return _resultado_indicador(
        slo="disponibilidad",
        definicion=definicion,
        objetivo="99 %",
        unidad="proporcion",
        muestra=len(esperados),
        muestra_minima=muestra_minima,
        valor=nivel,
        cumple=cumple,
        detalle={
            "fuente": f"logs/{SCHEDULER_LOG}",
            "estado_fuente": estado_fuente,
            "corridas_programadas": len(esperados),
            "corridas_disparadas": len(por_tick),
            "completadas_a_tiempo": a_tiempo,
            "completadas_tardias": tardias,
            "falladas": falladas,
            "omitidas_sin_completar": omitidas,
            "sin_disparo": sin_disparo,
            "entradas_fuera_de_agenda": fuera_de_agenda,
            "entradas_fuera_de_ventana": fuera_de_ventana,
            "atraso_inicio_s": _estadisticas(atrasos),
            "duracion_corrida_s": _estadisticas(duraciones),
        },
        huecos=(),
    )


# ---------------------------------------------------------------------------
# Tiempo de atención
# ---------------------------------------------------------------------------


def _id_pedido_canal(marca: str, correo: str, texto: str) -> str:
    """El mismo id que `canal_form._id_pedido`, recomputado sin persistirlo.

    Se reimplementa a propósito y una prueba lo contrasta con el adapter:
    la composición (`marca|correo|texto`, con el correo ya normalizado
    como la hoja lo entrega) es la que el canal usa para deduplicar
    respuestas, y el CSV de respuestas es la única fuente que conserva la
    marca en claro.
    """

    return hashlib.sha256(
        f"{marca}|{correo}|{texto}".encode("utf-8")
    ).hexdigest()


def indicador_tiempo_atencion(
    *,
    atendidos: tuple[dict[str, Any], ...],
    estado_fuente: str,
    respuestas_csv: Path | None,
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    muestra_minima: int,
    corte: datetime | None = None,
) -> dict[str, Any]:
    """Envío del Form de pedido → aviso con el resultado, en segundos.

    El sello de llegada es `timestamp` del registro de atendidos, escrito
    después del intento de aviso: incluye la entrega misma. Sólo entran a
    la muestra los pedidos con `aviso == "enviada"` —un aviso rechazado o
    fallido no es el evento del SLO— y el resto se cuenta como incidente.
    """

    definicion = (
        "desde el envío del Form de pedido hasta el aviso con el "
        "resultado (incluye la espera hasta la corrida)"
    )
    objetivo_s = config.intervalo_s + HOLGURA_AVISO_S
    objetivo = f"<= {objetivo_s} s (intervalo de sondeo + 5 min)"
    huecos: list[str] = []
    if estado_fuente == "invalida":
        return _indicador_sin_fuente(
            slo="tiempo_atencion",
            definicion=definicion,
            objetivo=objetivo,
            unidad="segundos",
            detalle={
                "fuente": f"{ATENDIDOS_NOMBRE}",
                "estado_fuente": "invalida",
            },
            huecos=("registro de atendidos del canal ilegible",),
            muestra_minima=muestra_minima,
        )
    if estado_fuente == "ausente":
        huecos.append("registro de atendidos del canal ausente")
    if respuestas_csv is None or not respuestas_csv.is_file():
        huecos.append(
            "la marca temporal del Form de pedido no se persiste en la "
            "auditoría (entra hasheada a id_pedido): la medición exige el "
            "CSV de respuestas exportado a la fecha de corte"
        )
        return _indicador_sin_fuente(
            slo="tiempo_atencion",
            definicion=definicion,
            objetivo=objetivo,
            unidad="segundos",
            detalle={
                "fuente": ATENDIDOS_NOMBRE,
                "estado_fuente": estado_fuente,
                "respuestas_csv": "ausente",
            },
            huecos=tuple(huecos),
            muestra_minima=muestra_minima,
        )

    marcas: dict[str, datetime] = {}
    marcas_no_parseables = 0
    filas_respuestas = 0
    try:
        with respuestas_csv.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.reader(archivo):
                filas_respuestas += 1
                if len(fila) < 3:
                    continue
                marca_texto, correo, texto = (
                    fila[0].strip(),
                    fila[1].strip().lower(),
                    fila[2].strip(),
                )
                # Misma regla que el adapter (`_celda` + `email_valido` +
                # correo en minúsculas): una respuesta tiene marca y
                # correo válido; el encabezado queda afuera por esto, y
                # el id se recompone exactamente como lo escribió el
                # registro de atendidos.
                if not marca_texto or not email_valido(correo):
                    continue
                instante = _parsear_marca_form(marca_texto, config)
                if instante is None:
                    marcas_no_parseables += 1
                    continue
                marcas[_id_pedido_canal(marca_texto, correo, texto)] = instante
    except OSError:
        return _indicador_sin_fuente(
            slo="tiempo_atencion",
            definicion=definicion,
            objetivo=objetivo,
            unidad="segundos",
            detalle={
                "fuente": ATENDIDOS_NOMBRE,
                "estado_fuente": estado_fuente,
                "respuestas_csv": "ilegible",
            },
            huecos=tuple(huecos + ["CSV de respuestas del Form ilegible"]),
            muestra_minima=muestra_minima,
        )

    atendidos_en_rango = 0
    aviso_enviada = 0
    aviso_incidente = 0
    sin_respuesta_csv = 0
    deltas: list[float] = []
    deltas_negativos = 0
    for linea in atendidos:
        if linea.get("version") != ATENDIDOS_VERSION:
            continue
        atendido_en = _parsear_instante(linea.get("timestamp"))
        if not _en_rango(atendido_en, desde, hasta, config, corte):
            continue
        atendidos_en_rango += 1
        if linea.get("aviso") != "enviada":
            aviso_incidente += 1
            continue
        aviso_enviada += 1
        marca = marcas.get(str(linea.get("id_pedido")))
        if marca is None:
            sin_respuesta_csv += 1
            continue
        delta = (atendido_en - marca).total_seconds()  # type: ignore[operator]
        if delta < 0:
            deltas_negativos += 1
            continue
        deltas.append(delta)

    respuestas_sin_atender = sum(
        1 for id_pedido in marcas if id_pedido not in {
            str(linea.get("id_pedido")) for linea in atendidos
        }
    )
    nivel = _percentil(deltas, 0.95)
    cumple = (
        (nivel is not None and nivel <= objetivo_s)
        if len(deltas) >= muestra_minima
        else None
    )
    return _resultado_indicador(
        slo="tiempo_atencion",
        definicion=definicion,
        objetivo=objetivo,
        unidad="segundos",
        muestra=len(deltas),
        muestra_minima=muestra_minima,
        valor=nivel,
        cumple=cumple,
        detalle={
            "fuente": ATENDIDOS_NOMBRE,
            "estado_fuente": estado_fuente,
            "respuestas_csv": respuestas_csv.name,
            "filas_respuestas": filas_respuestas,
            "atendidos_en_rango": atendidos_en_rango,
            "aviso_enviada": aviso_enviada,
            "aviso_rechazada_o_fallida": aviso_incidente,
            "atendidos_sin_fila_en_csv": sin_respuesta_csv,
            "respuestas_sin_atender": respuestas_sin_atender,
            "marcas_no_parseables": marcas_no_parseables,
            "deltas_negativos_descartados": deltas_negativos,
            "nota": (
                "la marca temporal del CSV se interpreta en la zona de la "
                "ventana de operación cuando viene sin zona"
            ),
        },
        huecos=tuple(huecos),
    )


# ---------------------------------------------------------------------------
# Latencia por pieza
# ---------------------------------------------------------------------------


def indicador_latencia_piezas(
    *,
    logs: Mapping[str, LecturaLog],
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    muestra_minima: int,
    corte: datetime | None = None,
) -> dict[str, Any]:
    """p95 de `latencia_s` por tipo de pieza con generación por modelo.

    La muestra son las piezas que llegaron a `PENDIENTE_VALIDACION`: es la
    latencia de la pieza producida, no de los intentos descartados. El
    objetivo numérico sale de #50 sobre el modelo de #51: se declara y el
    `modelo` observado viaja por tipo para que el Anexo 2 lo cite.
    """

    por_tipo: dict[str, dict[str, Any]] = {}
    huecos: list[str] = []
    for tipo, nombre_log, hus in PIEZAS_GENERADAS:
        lectura = logs.get(nombre_log, LecturaLog(()))
        latencias: list[float] = []
        modelos: set[str] = set()
        for linea in lectura.entradas:
            if (
                linea.get("HU") not in hus
                and linea.get("hu") not in hus
            ):
                continue
            if linea.get("estado") != ESTADO_PRESENTADA:
                continue
            instante = _parsear_instante(linea.get("timestamp"))
            if not _en_rango(instante, desde, hasta, config, corte):
                continue
            latencia = linea.get("latencia_s")
            if isinstance(latencia, (int, float)) and not isinstance(
                latencia, bool
            ):
                latencias.append(float(latencia))
            modelo = linea.get("modelo")
            if isinstance(modelo, str) and modelo:
                modelos.add(modelo)
        detalle: dict[str, Any] = {
            "log": f"logs/{nombre_log}",
            "estado_fuente": lectura.estado,
            **_estadisticas(latencias),
        }
        if modelos:
            detalle["modelos"] = sorted(modelos)
        if tipo == "linea_descriptiva" and not latencias:
            detalle["sin_latencia_s"] = True
            huecos.append(
                "lineas-descriptivas.jsonl no registra `latencia_s`: la "
                "línea descriptiva queda sin medición aunque genere piezas"
            )
        por_tipo[tipo] = detalle

    # Una pieza entra a la muestra del indicador si su log la registró con
    # latencia: la `n` publicada es la del tipo con más piezas medidas, y
    # el desglose por tipo lleva su propia `n`.
    muestra_total = sum(
        detalle["n"] for detalle in por_tipo.values()
    )
    resultado = _resultado_indicador(
        slo="latencia_por_pieza",
        definicion=(
            "p95 de la latencia de generación por tipo de pieza "
            "(interna, alimenta eficiencia de desempeño)"
        ),
        objetivo="pendiente #50/#51 (se fija con la medición sobre el "
        "modelo elegido)",
        unidad="segundos",
        muestra=muestra_total,
        muestra_minima=muestra_minima,
        valor=None,
        cumple=None,
        detalle={"por_tipo": por_tipo},
        huecos=tuple(huecos),
    )
    if muestra_total:
        # Hay medición real en `detalle.por_tipo`, pero sin objetivo
        # fijado no hay nivel que verificar: se declara la dependencia.
        resultado["nivel_verificado"] = "pendiente #50/#51"
    return resultado


# ---------------------------------------------------------------------------
# Aprobación → envío
# ---------------------------------------------------------------------------


def _primeras_decisiones(
    procesadas: tuple[dict[str, Any], ...],
) -> dict[tuple[str, str, str], datetime]:
    """Primer `timestamp` registrada por (tipo, objeto_id, decision)."""

    primeras: dict[tuple[str, str, str], datetime] = {}
    for linea in procesadas:
        if linea.get("resultado") != "registrada":
            continue
        instante = _parsear_instante(linea.get("timestamp"))
        if instante is None:
            continue
        clave = (
            str(linea.get("tipo")),
            str(linea.get("objeto_id")),
            str(linea.get("decision")),
        )
        if clave not in primeras or instante < primeras[clave]:
            primeras[clave] = instante
    return primeras


def _leer_registro_confirmaciones(
    directorio: Path | None,
) -> tuple[dict[str, dict[str, Any]], str]:
    """Estado y `actualizado_en` por clave del registro durable.

    Un archivo ilegible se trata como ausente igual que en el registro
    mismo: si el directorio no existe el indicador queda `sin_fuente`.
    """

    if directorio is None or not directorio.is_dir():
        return {}, "ausente"
    registros: dict[str, dict[str, Any]] = {}
    for ruta in sorted(directorio.glob("*.json")):
        clave = ruta.stem
        if CLAVE_REGISTRO_RE.fullmatch(clave) is None:
            continue
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(datos, dict):
            continue
        estado = datos.get("estado")
        if not isinstance(estado, str):
            continue
        registros[clave] = datos
    return registros, "ok"


def indicador_aprobacion_envio(
    *,
    lotes: tuple[dict[str, Any], ...],
    estado_lotes: str,
    procesadas: tuple[dict[str, Any], ...],
    estado_decisiones: str,
    registros: Mapping[str, dict[str, Any]],
    estado_registro: str,
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    muestra_minima: int,
    corte: datetime | None = None,
) -> dict[str, Any]:
    """Doble aprobación + lote → envío, p95 en segundos de ventana.

    Ancla: el `timestamp` de la última de las tres decisiones requeridas
    registrada (`apruebo_semantica` y `apruebo_utilitaria` sobre la
    plantilla, `apruebo_lote` sobre el lote). El envío es el
    `actualizado_en` del registro durable en `ENVIADA_SIMULADA`. El SLO
    corre dentro de la ventana, así que la muestra descuenta los tramos
    fuera de ella; el delta total viaja como auxiliar.
    """

    definicion = (
        "desde la doble aprobación (plantilla y lote) hasta el envío; "
        "ENVIO_INDETERMINADO cuenta como incidente fuera de la muestra"
    )
    objetivo_s = 2 * config.intervalo_s
    objetivo = f"<= {objetivo_s} s dentro de la ventana (2 x sondeo)"
    huecos: list[str] = []
    if estado_decisiones == "invalida":
        huecos.append("decisiones-procesadas.jsonl ilegible")
    elif estado_decisiones == "ausente":
        huecos.append("decisiones-procesadas.jsonl ausente")
    if estado_lotes == "invalida":
        huecos.append("lotes-actividad.jsonl ilegible")
    elif estado_lotes == "ausente":
        huecos.append("lotes-actividad.jsonl ausente")
    if estado_registro == "ausente":
        huecos.append("registro durable de confirmaciones ausente")

    autorizados: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    for linea in lotes:
        evento = linea.get("evento")
        instante = _parsear_instante(linea.get("timestamp"))
        if evento == "autorizacion_lote" and linea.get("estado") == "AUTORIZADA":
            lote_id = linea.get("lote_id")
            if isinstance(lote_id, str):
                autorizados[lote_id] = linea
        elif evento == "encolado_lote":
            clave = linea.get("idempotency_key")
            if isinstance(clave, str) and _en_rango(
                instante, desde, hasta, config, corte
            ):
                items.append(linea)

    primeras = _primeras_decisiones(procesadas)
    deltas: list[float] = []
    deltas_total: list[float] = []
    incidentes_indeterminado = 0
    incidentes_fallida = 0
    pendientes = 0
    sin_ancla = 0
    registro_ausente = 0
    entregados = 0
    for item in items:
        lote_id = item.get("lote_id")
        clave = item.get("idempotency_key")
        autorizado = autorizados.get(str(lote_id))
        if autorizado is None:
            sin_ancla += 1
            continue
        plantilla_id = autorizado.get("plantilla_id")
        requeridas = (
            ("plantilla", str(plantilla_id), "apruebo_semantica"),
            ("plantilla", str(plantilla_id), "apruebo_utilitaria"),
            ("lote", str(lote_id), "apruebo_lote"),
        )
        instantes = [primeras.get(clave_dec) for clave_dec in requeridas]
        if any(instante is None for instante in instantes):
            sin_ancla += 1
            continue
        aprobacion = max(instante for instante in instantes if instante is not None)
        registro = registros.get(str(clave))
        if registro is None:
            registro_ausente += 1
            continue
        estado = registro.get("estado")
        if estado in ESTADOS_ENVIO_INCIDENTE:
            if estado == "FALLIDA":
                incidentes_fallida += 1
            else:
                incidentes_indeterminado += 1
            continue
        if estado not in ESTADOS_ENVIO_ENTREGADO:
            pendientes += 1
            continue
        envio = _parsear_instante(registro.get("actualizado_en"))
        if corte is not None and envio is not None and envio > corte:
            # Al instante del corte la entrega todavía no había ocurrido.
            pendientes += 1
            continue
        if envio is None:
            huecos.append(
                "registro durable sin `actualizado_en` legible: entrega "
                "sin fecha, excluida de la muestra"
            )
            registro_ausente += 1
            continue
        entregados += 1
        deltas_total.append((envio - aprobacion).total_seconds())
        deltas.append(segundos_en_ventana(aprobacion, envio, config))

    # Ítems del registro que no salieron del circuito de lote medido: sus
    # aprobaciones no viajan por el Form de decisiones medible.
    claves_medidas = {str(item.get("idempotency_key")) for item in items}
    otros_entregados = sum(
        1
        for clave, datos in registros.items()
        if clave not in claves_medidas
        and datos.get("estado") in ESTADOS_ENVIO_ENTREGADO
    )
    otros_incidentes = sum(
        1
        for clave, datos in registros.items()
        if clave not in claves_medidas
        and datos.get("estado") in ESTADOS_ENVIO_INCIDENTE
    )
    if otros_entregados or otros_incidentes:
        huecos.append(
            "registros fuera del circuito de lote por Form de decisiones "
            "(confirmación individual, recordatorios): su aprobación sólo "
            "queda como hash en la auditoría y el ancla no se puede "
            "reconstruir — quedan fuera de la muestra"
        )

    nivel = _percentil(deltas, 0.95)
    cumple = (
        (nivel is not None and nivel <= objetivo_s)
        if len(deltas) >= muestra_minima
        else None
    )
    return _resultado_indicador(
        slo="aprobacion_envio",
        definicion=definicion,
        objetivo=objetivo,
        unidad="segundos",
        muestra=len(deltas),
        muestra_minima=muestra_minima,
        valor=nivel,
        cumple=cumple,
        detalle={
            "fuentes": {
                "decisiones": estado_decisiones,
                "lotes": estado_lotes,
                "registro": estado_registro,
            },
            "lotes_autorizados": len(autorizados),
            "items_encolados_en_rango": len(items),
            "items_entregados": entregados,
            "incidentes_indeterminado": incidentes_indeterminado,
            "incidentes_fallida": incidentes_fallida,
            "items_pendientes": pendientes,
            "items_sin_ancla": sin_ancla,
            "items_sin_registro": registro_ausente,
            "registros_fuera_del_circuito_entregados": otros_entregados,
            "registros_fuera_del_circuito_incidentes": otros_incidentes,
            "delta_total_s": _estadisticas(deltas_total),
            "delta_en_ventana_s": _estadisticas(deltas),
            "nota": (
                "la muestra descuenta el tiempo fuera de la ventana de "
                "operación; `delta_total_s` muestra el reloj completo"
            ),
        },
        huecos=tuple(dict.fromkeys(huecos)),
    )


# ---------------------------------------------------------------------------
# Integridad del gate
# ---------------------------------------------------------------------------


def indicador_integridad_gate(
    *,
    logs: Mapping[str, LecturaLog],
    directorio_borradores: Path | None,
    lotes: tuple[dict[str, Any], ...],
    recordatorios: tuple[dict[str, Any], ...],
    confirmaciones: tuple[dict[str, Any], ...],
    registros: Mapping[str, dict[str, Any]],
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    muestra_minima: int,
    corte: datetime | None = None,
) -> dict[str, Any]:
    """Toda pieza en validación humana pasó el gate; 0 no conformes como conformes.

    Tres verificaciones sobre la evidencia ya escrita:

    - `generacion`: las líneas `PENDIENTE_VALIDACION` de los logs de
      generación no llevan `validation_errors` no vacío (una línea que lo
      llevara es una no conforme presentada como conforme).
    - `artefactos`: cada `borradores/*.md` tiene que matchear el
      `output_hash` de una línea `PENDIENTE_VALIDACION`; un archivo que
      sólo matchea una línea rechazada, o ninguna, es una pieza
      presentada sin gate.
    - `envios`: cada clave del registro durable en `ENVIADA_SIMULADA`
      tiene traza del gate de envío (encolado bajo `autorizacion_lote`
      AUTORIZADA, o línea de confirmaciones con la aprobación presente).
      `EMITIDA_SIMULADA` queda contado sin exigir traza: el circuito de
      emisión no audita por clave.
    """

    violaciones: list[str] = []
    huecos: list[str] = []
    verificaciones: list[dict[str, Any]] = []

    # a) Logs de generación: PENDIENTE_VALIDACION => gate aprobado.
    presentadas = 0
    violadas_generacion = 0
    por_log: dict[str, dict[str, int]] = {}
    for nombre in (LOG_EJECUCIONES, LOG_PLANTILLAS, LOG_LINEAS):
        lectura = logs.get(nombre, LecturaLog(()))
        presentadas_log = 0
        violadas_log = 0
        for linea in lectura.entradas:
            if linea.get("estado") != ESTADO_PRESENTADA:
                continue
            instante = _parsear_instante(linea.get("timestamp"))
            if not _en_rango(instante, desde, hasta, config, corte):
                continue
            presentadas_log += 1
            errores = linea.get("validation_errors")
            if isinstance(errores, list) and errores:
                violadas_log += 1
                violaciones.append(
                    f"{nombre}: PENDIENTE_VALIDACION con "
                    f"validation_errors (correlation_id "
                    f"{linea.get('correlation_id')})"
                )
        por_log[nombre] = {
            "estado_fuente": lectura.estado,
            "presentadas": presentadas_log,
            "violaciones": violadas_log,
        }
        presentadas += presentadas_log
        violadas_generacion += violadas_log
    verificaciones.append(
        {
            "alcance": "generacion",
            "presentadas": presentadas,
            "violaciones": violadas_generacion,
            "por_log": por_log,
        }
    )

    # b) Artefactos locales: todo borrador en disco con línea conforme.
    conformes: set[str] = set()
    no_conformes: set[str] = set()
    for nombre in (LOG_EJECUCIONES, LOG_PLANTILLAS, LOG_LINEAS):
        for linea in logs.get(nombre, LecturaLog(())).entradas:
            output_hash = linea.get("output_hash")
            if not isinstance(output_hash, str):
                continue
            instante = _parsear_instante(linea.get("timestamp"))
            if not _en_rango(instante, desde, hasta, config, corte):
                continue
            if (
                linea.get("estado") == ESTADO_PRESENTADA
                and linea.get("resultado") in RESULTADOS_CONFORMES
            ):
                conformes.add(output_hash)
            else:
                no_conformes.add(output_hash)
    archivos = 0
    archivos_conformes = 0
    archivos_violados = 0
    if directorio_borradores is not None and directorio_borradores.is_dir():
        for ruta in sorted(directorio_borradores.glob("*.md")):
            archivos += 1
            try:
                hash_archivo = hashlib.sha256(ruta.read_bytes()).hexdigest()
            except OSError:
                continue
            if hash_archivo in conformes:
                archivos_conformes += 1
            else:
                archivos_violados += 1
                origen = (
                    "línea no conforme"
                    if hash_archivo in no_conformes
                    else "sin línea de auditoría"
                )
                violaciones.append(
                    f"borradores/{ruta.name}: artefacto presentado con "
                    f"{origen}"
                )
        estado_borradores = "ok"
    else:
        estado_borradores = "ausente"
        huecos.append(
            "directorio `borradores/` ausente: la verificación de "
            "artefactos no corrió (en live los borradores viven en Drive "
            "y la integridad se mide sobre las líneas de auditoría)"
        )
    verificaciones.append(
        {
            "alcance": "artefactos_locales",
            "estado_fuente": estado_borradores,
            "archivos": archivos,
            "conformes": archivos_conformes,
            "violaciones": archivos_violados,
        }
    )

    # c) Envíos: toda ENVIADA_SIMULADA con traza del gate de envío.
    autorizados_lote = {
        str(linea.get("lote_id"))
        for linea in lotes
        if linea.get("evento") == "autorizacion_lote"
        and linea.get("estado") == "AUTORIZADA"
    }
    claves_lote = {
        str(linea.get("idempotency_key"))
        for linea in lotes
        if linea.get("evento") == "encolado_lote"
        and str(linea.get("lote_id")) in autorizados_lote
    }
    autorizados_recordatorio = {
        str(linea.get("lote_clave"))
        for linea in recordatorios
        if linea.get("evento") == "autorizacion_lote"
        and linea.get("estado") == "AUTORIZADA"
    }
    claves_recordatorio = {
        str(linea.get("idempotency_key"))
        for linea in recordatorios
        if linea.get("evento") == "encolado_lote"
        and str(linea.get("lote_clave")) in autorizados_recordatorio
    }
    claves_con_aprobacion = {
        str(linea.get("idempotency_key"))
        for linea in confirmaciones
        if linea.get("human_decision_present") is True
        or isinstance(linea.get("approval_role"), str)
    }
    enviadas = 0
    enviadas_trazadas = 0
    enviadas_violadas = 0
    emitidas_sin_traza = 0
    for clave, datos in registros.items():
        estado = datos.get("estado")
        actualizado = _parsear_instante(datos.get("actualizado_en"))
        if corte is not None and actualizado is not None and actualizado > corte:
            # El estado al instante del corte es anterior a esta marca:
            # no se reconstruye desde el registro, así que la clave no
            # entra a la muestra (ni cuenta como conforme ni como falla).
            continue
        if estado == "EMITIDA_SIMULADA":
            emitidas_sin_traza += 1
            continue
        if estado != "ENVIADA_SIMULADA":
            continue
        enviadas += 1
        if (
            clave in claves_lote
            or clave in claves_recordatorio
            or clave in claves_con_aprobacion
        ):
            enviadas_trazadas += 1
        else:
            enviadas_violadas += 1
            violaciones.append(
                f"registro {clave[:12]}…: ENVIADA_SIMULADA sin traza de "
                "gate de envío en los logs"
            )
    if emitidas_sin_traza:
        huecos.append(
            "el circuito de emisión de certificados no audita por clave: "
            "las EMITIDA_SIMULADA del registro se cuentan sin exigir traza"
        )
    verificaciones.append(
        {
            "alcance": "envios",
            "presentadas": enviadas,
            "conformes": enviadas_trazadas,
            "violaciones": enviadas_violadas,
            "emitidas_sin_traza": emitidas_sin_traza,
        }
    )

    total_presentadas = presentadas + archivos + enviadas
    total_violaciones = (
        violadas_generacion + archivos_violados + enviadas_violadas
    )
    nivel = (
        (total_presentadas - total_violaciones) / total_presentadas
        if total_presentadas
        else None
    )
    cumple = (
        total_violaciones == 0
        if total_presentadas >= muestra_minima
        else None
    )
    return _resultado_indicador(
        slo="integridad_gate",
        definicion=(
            "piezas en validación humana que pasaron el gate: 100 %, y "
            "0 no conformes presentadas como conformes"
        ),
        objetivo="100 %",
        unidad="proporcion",
        muestra=total_presentadas,
        muestra_minima=muestra_minima,
        valor=nivel,
        cumple=cumple,
        detalle={
            "verificaciones": verificaciones,
            "violaciones_detalle": violaciones[:50],
            "violaciones_total": len(violaciones),
        },
        huecos=tuple(huecos),
    )


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------


def _estado_fuentes(fuentes: FuentesAuditoria) -> dict[str, str]:
    directorio = fuentes.directorio

    def marca(path: Path | None) -> str:
        return "ausente" if path is None else ("ok" if path.exists() else "ausente")

    return {
        "directorio": marca(directorio),
        "logs": marca(directorio / "logs" if directorio is not None else None),
        "borradores": marca(
            directorio / "borradores" if directorio is not None else None
        ),
        "estado_canal": marca(fuentes.estado_canal),
        "estado_decisiones": marca(fuentes.estado_decisiones),
        "registro_confirmaciones": marca(fuentes.registro_confirmaciones),
        "respuestas_csv": marca(fuentes.respuestas_csv),
    }


def medir_nivel_slo(
    *,
    fuentes: FuentesAuditoria,
    desde: date,
    hasta: date,
    config: ConfiguracionScheduler,
    corte: datetime,
    muestra_minima: int = MUESTRA_MINIMA_DEFAULT,
) -> dict[str, Any]:
    """Los cinco indicadores sobre `[desde, hasta]`, nada más que lectura.

    `corte` es el instante de la medición (aware): la agenda y los eventos
    posteriores a él no son observaciones, son futuro. Devuelve el reporte
    versionado (`nivel_verificado_slo_v1`): cada indicador lleva su `n`,
    su nivel medido o la declaración de por qué no hay número, y los
    huecos encontrados. La función no escribe nada: la evidencia la emite
    el runner.
    """

    if hasta < desde:
        raise ValueError("rango de fechas inválido: hasta < desde")
    if corte.tzinfo is None:
        raise ValueError("corte sin zona horaria: el instante sería ambiguo")

    directorio = fuentes.directorio
    logs_dir = directorio / "logs"
    logs: dict[str, LecturaLog] = {
        "scheduler": _leer_jsonl(logs_dir / SCHEDULER_LOG),
        LOG_EJECUCIONES: _leer_jsonl(logs_dir / LOG_EJECUCIONES),
        LOG_PLANTILLAS: _leer_jsonl(logs_dir / LOG_PLANTILLAS),
        LOG_LINEAS: _leer_jsonl(logs_dir / LOG_LINEAS),
        LOG_LOTES: _leer_jsonl(logs_dir / LOG_LOTES),
        LOG_RECORDATORIOS: _leer_jsonl(logs_dir / LOG_RECORDATORIOS),
        LOG_CONFIRMACIONES: _leer_jsonl(logs_dir / LOG_CONFIRMACIONES),
    }
    atendidos = _leer_jsonl(
        fuentes.estado_canal / ATENDIDOS_NOMBRE
        if fuentes.estado_canal is not None
        else None
    )
    procesadas = _leer_jsonl(
        fuentes.estado_decisiones / PROCESADAS_NOMBRE
        if fuentes.estado_decisiones is not None
        else None
    )
    registros, estado_registro = _leer_registro_confirmaciones(
        fuentes.registro_confirmaciones
    )

    lotes = logs[LOG_LOTES].entradas
    recordatorios = logs[LOG_RECORDATORIOS].entradas
    confirmaciones = logs[LOG_CONFIRMACIONES].entradas

    indicadores = {
        "disponibilidad": indicador_disponibilidad(
            entradas=logs["scheduler"].entradas,
            estado_fuente=logs["scheduler"].estado,
            desde=desde,
            hasta=hasta,
            config=config,
            muestra_minima=muestra_minima,
            corte=corte,
        ),
        "tiempo_atencion": indicador_tiempo_atencion(
            atendidos=atendidos.entradas,
            estado_fuente=atendidos.estado,
            respuestas_csv=fuentes.respuestas_csv,
            desde=desde,
            hasta=hasta,
            config=config,
            muestra_minima=muestra_minima,
            corte=corte,
        ),
        "latencia_por_pieza": indicador_latencia_piezas(
            logs=logs,
            desde=desde,
            hasta=hasta,
            config=config,
            muestra_minima=muestra_minima,
            corte=corte,
        ),
        "aprobacion_envio": indicador_aprobacion_envio(
            lotes=lotes,
            estado_lotes=logs[LOG_LOTES].estado,
            procesadas=procesadas.entradas,
            estado_decisiones=procesadas.estado,
            registros=registros,
            estado_registro=estado_registro,
            desde=desde,
            hasta=hasta,
            config=config,
            muestra_minima=muestra_minima,
            corte=corte,
        ),
        "integridad_gate": indicador_integridad_gate(
            logs=logs,
            directorio_borradores=directorio / "borradores",
            lotes=lotes,
            recordatorios=recordatorios,
            confirmaciones=confirmaciones,
            registros=registros,
            desde=desde,
            hasta=hasta,
            config=config,
            muestra_minima=muestra_minima,
            corte=corte,
        ),
    }

    huecos: list[str] = []
    for indicador in indicadores.values():
        huecos.extend(indicador["huecos"])

    return {
        "record": REGISTRO_FORMATO,
        "corte": corte.isoformat(),
        "rango": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "configuracion": config.resumen_seguro(),
        "muestra_minima": muestra_minima,
        "fuentes": _estado_fuentes(fuentes),
        "indicadores": indicadores,
        "huecos": sorted(set(huecos)),
    }


def render_markdown(reporte: Mapping[str, Any], *, comando: str) -> str:
    """La evidencia versionable del corte: markdown fijo, sin dependencias.

    `comando` es la línea exacta que produjo el corte, para que la
    evidencia sea reproducible tal como exige el acceptance criteria.
    """

    config = reporte["configuracion"]
    rango = reporte["rango"]
    lineas: list[str] = [
        "# Nivel verificado de los SLO desde la auditoría (#88)",
        "",
        f"- **Instante de corte:** {reporte['corte']} — los ticks y "
        "eventos posteriores a él no entran a las muestras.",
        f"- **Rango medido:** {rango['desde']} a {rango['hasta']} "
        "(fechas locales de la ventana).",
        f"- **Configuración declarada:** intervalo de sondeo "
        f"{config['intervalo_s']} s; ventana días {config['ventana_dias']} "
        f"de {config['ventana_desde']} a {config['ventana_hasta']} "
        f"({config['zona']}). Sale de `AGENTE1_SCHEDULER_*`, igual que el "
        "scheduler.",
        f"- **Muestra mínima declarada:** {reporte['muestra_minima']} "
        "observaciones por indicador; debajo de eso se declara `muestra "
        "insuficiente` en vez de publicar un número.",
        "- **Comando que produjo este corte:**",
        "",
        "```bash",
        comando,
        "```",
        "",
        "## Indicadores",
        "",
        "| SLO | Definición | Objetivo | n | Nivel verificado | Cumple |",
        "|---|---|---|---|---|---|",
    ]
    for nombre in (
        "disponibilidad",
        "tiempo_atencion",
        "latencia_por_pieza",
        "aprobacion_envio",
        "integridad_gate",
    ):
        indicador = reporte["indicadores"][nombre]
        cumple = indicador["cumple"]
        marca_cumple = (
            "sí" if cumple is True else ("no" if cumple is False else "—")
        )
        lineas.append(
            f"| {nombre} | {indicador['definicion']} | "
            f"{indicador['objetivo']} | {indicador['n']} | "
            f"{indicador['nivel_verificado']} | {marca_cumple} |"
        )
    lineas.append("")

    for nombre in (
        "disponibilidad",
        "tiempo_atencion",
        "latencia_por_pieza",
        "aprobacion_envio",
        "integridad_gate",
    ):
        indicador = reporte["indicadores"][nombre]
        lineas.append(f"### {nombre}")
        lineas.append("")
        lineas.append("```json")
        lineas.append(
            json.dumps(indicador["detalle"], ensure_ascii=False, indent=2, sort_keys=True)
        )
        lineas.append("```")
        lineas.append("")

    if reporte["huecos"]:
        lineas.append("## Huecos declarados")
        lineas.append("")
        for hueco in reporte["huecos"]:
            lineas.append(f"- {hueco}")
        lineas.append("")
    lineas.append(
        "Los objetivos que dependen de #50/#51 quedan declarados "
        "`pendiente` y ningún indicador inventa un número: donde la "
        "muestra o la fuente no alcanza, la celda lo dice."
    )
    lineas.append("")
    return "\n".join(lineas)


__all__ = [
    "ATENDIDOS_VERSION",
    "FuentesAuditoria",
    "LecturaLog",
    "MUESTRA_MINIMA_DEFAULT",
    "REGISTRO_FORMATO",
    "indicador_aprobacion_envio",
    "indicador_disponibilidad",
    "indicador_integridad_gate",
    "indicador_latencia_piezas",
    "indicador_tiempo_atencion",
    "medir_nivel_slo",
    "render_markdown",
    "segundos_en_ventana",
    "ticks_agenda",
]
