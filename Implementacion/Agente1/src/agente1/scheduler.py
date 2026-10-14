"""Scheduler local de las corridas programadas del agente (#84).

Dispara la corrida de insumos de agentes cada pocos minutos en el host de la
demo, para que el Agente 1 reaccione solo cuando un productor carga una fila
en la pestaña «Insumos de agentes». El disparo automático sólo produce
borradores: la validación humana no cambia y el agente nunca envía ni publica
nada por su cuenta. La corrida manual (`insumos-agentes`) sigue disponible.

El módulo no es un demonio: conoce dos mecanismos de disparo externos y
deja que el operador elija (ver el runbook
`Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md`):

- **Timer `systemd --user`** (mecanismo natural en el host de la demo): un
  `.timer` dispara un `.service` oneshot que corre `agente1 scheduler
  --una-corrida` cada intervalo. Cada proceso calcula el tick al que responde,
  ejecuta la corrida una vez y termina. Las unidades se versionan como
  plantillas instalables en `Implementacion/Agente1/systemd/`; instalarlas y
  habilitarlas es tarea del operador designado (ADR 0007).
- **Bucle con `sleep`** (`agente1 scheduler --loop`): un proceso único que
  espera al próximo tick y corre dentro de la ventana de operación. Sirve
  para ensayos y para hosts sin systemd; el mismo `disparar` se ejercita en
  las pruebas con reloj y `dormir` inyectados.

Decisiones que no se ven en el código:

- **La agenda se ancla a la ventana de operación.** Los ticks son
  `desde + k * intervalo` en la zona configurada, dentro de los días y el
  horario declarados (provisional: días hábiles de 8 a 16, la confirma la
  SEU en #56). Fuera de la ventana no hay corridas programadas: el bucle
  duerme hasta el próximo tick y un disparo externo tardío queda asentado
  como `omitida_ventana` sin tocar nada.
- **Cada disparo responde a un tick, no al momento en que llegó.**
  `inicio_previsto` es el tick más reciente anterior al disparo dentro de la
  ventana, así un timer que se atrasa (suspend, contención) deja en la
  auditoría la agenda comprometida y el atraso real. Si un tick ya quedó
  `completada`, un disparo extra sobre el mismo tick se asienta
  `omitida_duplicada` y no vuelve a correr: un timer más fino que el
  intervalo configurado queda absorbido por deduplicación.
- **El lock de corrida cierra el solapamiento.** `disparar` toma un
  `flock` no bloqueante sobre `scheduler-corrida.lock`: un segundo disparo
  concurrente se asienta `omitida_lock` sin ejecutar nada. Debajo queda la
  red de seguridad de la corrida misma (estado en la fila e idempotencia
  por `correlation_id`), así aun un solapamiento manual queda cubierto.
- **Una falla de la corrida queda auditada y no deja filas a medias.** El
  informe de la corrida distingue fallas de tabla de fallas de fila; el
  scheduler no agrega un segundo criterio: si la corrida produce informe el
  tick es `completada` (los conteos van en el log), si levanta es `falla`
  con el código cerrado. La línea del scheduler nunca lleva payload, filas
  ni contenido generado.
- **El mantenimiento diario es una secuencia ordenada en la primera corrida
  de la ventana.** La purga de datos personales (#87) y el respaldo del
  estado local en Drive (#86) corren una vez por día y reintentan en el
  tick siguiente si fallaron. El orden importa y además se encadena: si la
  purga falló, el respaldo falla a propósito, porque ningún respaldo debe
  conservar texto que la retención acotada ya venció (ADR 0009). Sin
  carpeta declarada (`AGENTE1_RESPALDO_*`) el respaldo se asienta
  `pendiente`.
- **El log del scheduler es la fuente del nivel verificado de
  disponibilidad** (#88): una línea JSONL append-only por disparo con
  `inicio_previsto`, `inicio_real`, `fin` y `resultado`, más la fecha
  local y el detalle del mantenimiento cuando el slot diario corrió.
  `en_ventana` separa las corridas programadas (denominador del SLO) de
  los disparos fuera de ventana. Un registro ilegible invalida la lectura
  (`scheduler_log_invalid`): igual que el registro de insumos, se prefiere
  no procesar a procesar dos veces.
- **Nada de esto envía.** El scheduler sólo sondea la pestaña y genera
  borradores `PENDIENTE_VALIDACION`: ni el timer, ni el bucle, ni la purga
  habilitan publicación ni envío.

Configuración por entorno, prefijo `AGENTE1_SCHEDULER_` (claves desconocidas
rechazadas, sin defaults implícitos para los valores declarados):

- `AGENTE1_SCHEDULER_INTERVALO_S`: segundos entre ticks (default 300).
- `AGENTE1_SCHEDULER_VENTANA_DIAS`: días ISO separados por coma
  (1 = lunes; default `1,2,3,4,5`).
- `AGENTE1_SCHEDULER_VENTANA_DESDE` / `..._HASTA`: `HH:MM` local; la ventana
  es `[desde, hasta)` (default `08:00` a `16:00`, provisional #56).
- `AGENTE1_SCHEDULER_TZ`: zona IANA (default
  `America/Argentina/Buenos_Aires`, la misma que `pagos.py`).
- `AGENTE1_SCHEDULER_REPO`: raíz del checkout del repo; el scheduler la
  usa para ubicar `Implementacion/Agente1/scripts/purgar_registro.py` y
  las unidades la toman como `WorkingDirectory` (default derivado de la
  ubicación del paquete, sirve para instalaciones editables; en una
  instalación empaquetada hay que declararla).
- `AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES`: directorio del registro
  durable de HU-012 que la purga diaria procesa; si falta, el paso
  `purga` no se declara y el slot diario sólo marca los pasos futuros.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .registro_auditoria import escribir_registro

RECORD_CORRIDA = "scheduler_corrida_v1"
LOG_NOMBRE = "scheduler-corridas.jsonl"
LOCK_NOMBRE = "scheduler-corrida.lock"

RESULTADOS_DISPARO = frozenset(
    {
        "completada",
        "falla",
        "omitida_lock",
        "omitida_ventana",
        "omitida_duplicada",
    }
)
RESULTADOS_PASO = frozenset({"completada", "falla", "pendiente"})

# Las claves del informe de la corrida que se republican en el log del
# scheduler: conteos cerrados y estado, nunca el detalle por fila (que ya
# incluye identificadores y pertenece al informe propio de la corrida).
_CLAVES_RESUMEN_CORRIDA = (
    "estado",
    "filas_leidas",
    "filas_nuevas",
    "filas_escritas",
    "filas_omitidas",
    "filas_bloqueadas",
    "filas_fallidas",
)

_PREFIX = "AGENTE1_SCHEDULER_"
ENV_INTERVALO = "AGENTE1_SCHEDULER_INTERVALO_S"
ENV_VENTANA_DIAS = "AGENTE1_SCHEDULER_VENTANA_DIAS"
ENV_VENTANA_DESDE = "AGENTE1_SCHEDULER_VENTANA_DESDE"
ENV_VENTANA_HASTA = "AGENTE1_SCHEDULER_VENTANA_HASTA"
ENV_TZ = "AGENTE1_SCHEDULER_TZ"
ENV_REPO = "AGENTE1_SCHEDULER_REPO"
ENV_REGISTRO_CONFIRMACIONES = "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES"
_ALLOWED_KEYS = frozenset(
    {
        ENV_INTERVALO,
        ENV_VENTANA_DIAS,
        ENV_VENTANA_DESDE,
        ENV_VENTANA_HASTA,
        ENV_TZ,
        ENV_REPO,
        ENV_REGISTRO_CONFIRMACIONES,
    }
)

# Defaults provisionales: el intervalo responde a «cada pocos minutos» del
# issue #84; la ventana replica la declarada para el SLO de disponibilidad
# (días hábiles de 8 a 16, pendiente de confirmación por la SEU en #56).
DEFAULT_INTERVALO_S = 300
DEFAULT_VENTANA_DIAS = "1,2,3,4,5"
DEFAULT_VENTANA_DESDE = "08:00"
DEFAULT_VENTANA_HASTA = "16:00"
DEFAULT_TZ = "America/Argentina/Buenos_Aires"

_HORA_RE = re.compile(r"(?P<hh>[0-9]{2}):(?P<mm>[0-9]{2})\Z")


class ConfiguracionSchedulerError(ValueError):
    """Falla de la configuración del scheduler, con código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SchedulerError(RuntimeError):
    """Falla estructural del scheduler (log ilegible, lock inaccesible)."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class ConfiguracionScheduler:
    """Agenda y ventana de operación, validadas de una sola vez.

    `dias` usa el número ISO de día de semana (lunes = 1). La ventana es
    `[desde, hasta)` en la zona `zona`: un tick en `hasta` ya está fuera, así
    que la última corrida programada siempre empieza dentro de la ventana.
    """

    intervalo_s: int
    dias: frozenset[int]
    desde: dtime
    hasta: dtime
    zona: ZoneInfo
    repo: Path
    registro_confirmaciones: Path | None = None

    def resumen_seguro(self) -> dict[str, object]:
        """Vista publicable: nada sensible, igual que los otros resúmenes."""

        return {
            "intervalo_s": self.intervalo_s,
            "ventana_dias": sorted(self.dias),
            "ventana_desde": self.desde.strftime("%H:%M"),
            "ventana_hasta": self.hasta.strftime("%H:%M"),
            "zona": self.zona.key,
            "registro_confirmaciones": self.registro_confirmaciones is not None,
        }


def cargar_configuracion_scheduler(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionScheduler:
    """Lee `AGENTE1_SCHEDULER_*`, con errores cerrados.

    Mismo contrato que los otros loaders: una clave propia desconocida se
    rechaza, un valor mal formado falla con código y sin el valor adentro.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave
        for clave in env
        if clave.startswith(_PREFIX) and clave not in _ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionSchedulerError("scheduler_config_unknown_key")

    intervalo = _entero_positivo(
        _valor_env(env, ENV_INTERVALO, str(DEFAULT_INTERVALO_S))
    )
    dias = _parsear_dias(_valor_env(env, ENV_VENTANA_DIAS, DEFAULT_VENTANA_DIAS))
    desde = _parsear_hora(_valor_env(env, ENV_VENTANA_DESDE, DEFAULT_VENTANA_DESDE))
    hasta = _parsear_hora(_valor_env(env, ENV_VENTANA_HASTA, DEFAULT_VENTANA_HASTA))
    if desde >= hasta:
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    try:
        zona = ZoneInfo(_valor_env(env, ENV_TZ, DEFAULT_TZ))
    except ZoneInfoNotFoundError:
        raise ConfiguracionSchedulerError("scheduler_config_invalid") from None

    repo: Path | None = None
    if ENV_REPO in env:
        repo = Path(_valor_env(env, ENV_REPO, ""))
    if repo is None:
        repo = Path(__file__).resolve().parents[4]

    registro: Path | None = None
    if ENV_REGISTRO_CONFIRMACIONES in env:
        registro = Path(_valor_env(env, ENV_REGISTRO_CONFIRMACIONES, ""))

    return ConfiguracionScheduler(
        intervalo_s=intervalo,
        dias=dias,
        desde=desde,
        hasta=hasta,
        zona=zona,
        repo=repo,
        registro_confirmaciones=registro,
    )


def _valor_env(env: Mapping[str, str], clave: str, default: str) -> str:
    """Una variable declarada pero vacía es configuración rota, no default.

    `VAR=` en el entorno del timer suele ser un Environment= olvidado:
    tratarlo como default dejaría corriendo una agenda que no es la que el
    operador cree haber puesto.
    """

    if clave not in env:
        return default
    valor = env[clave].strip()
    if not valor:
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    return valor


def _entero_positivo(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError:
        raise ConfiguracionSchedulerError("scheduler_config_invalid") from None
    if valor <= 0:
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    return valor


def _parsear_dias(texto: str) -> frozenset[int]:
    try:
        dias = frozenset(int(parte) for parte in texto.split(",") if parte.strip())
    except ValueError:
        raise ConfiguracionSchedulerError("scheduler_config_invalid") from None
    if not dias or any(dia < 1 or dia > 7 for dia in dias):
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    return dias


def _parsear_hora(texto: str) -> dtime:
    match = _HORA_RE.fullmatch(texto.strip())
    if match is None:
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    hora, minutos = int(match["hh"]), int(match["mm"])
    if hora > 23 or minutos > 59:
        raise ConfiguracionSchedulerError("scheduler_config_invalid")
    return dtime(hora, minutos)


def en_ventana(local: datetime, config: ConfiguracionScheduler) -> bool:
    """Un instante local está dentro de la ventana `[desde, hasta)`."""

    return (
        local.isoweekday() in config.dias
        and config.desde <= local.time() < config.hasta
    )


def tick_previsto(ahora: datetime, config: ConfiguracionScheduler) -> datetime | None:
    """El tick de agenda al que responde un disparo en `ahora`, o `None`.

    Los ticks son `desde + k * intervalo` de cada día permitido. Si `ahora`
    cae fuera de la ventana no hay tick al que responder: el disparo es
    `omitida_ventana`.
    """

    local = ahora.astimezone(config.zona)
    if not en_ventana(local, config):
        return None
    base = datetime.combine(local.date(), config.desde, tzinfo=config.zona)
    transcurrido = (local - base).total_seconds()
    k = int(transcurrido // config.intervalo_s)
    return base + timedelta(seconds=k * config.intervalo_s)


def proximo_disparo(ahora: datetime, config: ConfiguracionScheduler) -> datetime:
    """El próximo tick de agenda en `ahora` o después, aware en `config.zona`.

    Recorre hasta ocho días hacia adelante: una ventana de un solo día por
    semana siempre encuentra su próximo tick. `desde >= hasta` o `dias`
    vacío no pueden llegar: la configuración los rechaza al cargar.
    """

    local = ahora.astimezone(config.zona)
    for delta in range(9):
        fecha = local.date() + timedelta(days=delta)
        if fecha.isoweekday() not in config.dias:
            continue
        tick = datetime.combine(fecha, config.desde, tzinfo=config.zona)
        cierre = datetime.combine(fecha, config.hasta, tzinfo=config.zona)
        while tick < cierre:
            if tick >= ahora:
                return tick
            tick += timedelta(seconds=config.intervalo_s)
    raise SchedulerError("scheduler_ventana_sin_ticks")


class RegistroCorridasArchivo:
    """Auditoría append-only de las corridas programadas.

    Una línea JSON por disparo bajo `logs/` del directorio de salida, con la
    agenda (`inicio_previsto`), lo real (`inicio_real`, `fin`), el desenlace
    y el detalle del mantenimiento cuando corrió. Es la entrada que #88
    necesita para medir la disponibilidad dentro de la ventana. La fecha
    local viaja en cada línea: agrupa el día de operación sin recomputar
    zonas horarias.
    """

    def __init__(self, directorio: Path) -> None:
        self._path = Path(directorio) / "logs" / LOG_NOMBRE

    @property
    def path(self) -> Path:
        return self._path

    def anexar(self, entrada: Mapping[str, Any]) -> dict[str, Any]:
        try:
            return escribir_registro(self._path, entrada)
        except OSError:
            raise SchedulerError("scheduler_log_inaccesible") from None

    def entradas(self) -> list[dict[str, Any]]:
        """Relee el registro entero; una línea inválida lo invalida todo."""

        if not self._path.exists():
            return []
        entradas: list[dict[str, Any]] = []
        try:
            with self._path.open(encoding="utf-8", newline="") as archivo:
                for linea in archivo:
                    texto = linea.strip()
                    if not texto:
                        continue
                    entradas.append(_entrada_valida(json.loads(texto)))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise SchedulerError("scheduler_log_invalid") from None
        return entradas


def _entrada_valida(valor: object) -> dict[str, Any]:
    """La forma cerrada de una línea del log del scheduler."""

    if (
        not isinstance(valor, dict)
        or valor.get("record") != RECORD_CORRIDA
        or valor.get("resultado") not in RESULTADOS_DISPARO
        or not isinstance(valor.get("en_ventana"), bool)
        or not isinstance(valor.get("fecha"), str)
        or not valor["fecha"]
    ):
        raise ValueError("entrada de log de scheduler inválida")
    mantenimiento = valor.get("mantenimiento")
    if mantenimiento is not None and (
        not isinstance(mantenimiento, dict)
        or any(res not in RESULTADOS_PASO for res in mantenimiento.values())
    ):
        raise ValueError("entrada de log de scheduler inválida")
    return valor


@contextmanager
def lock_corrida(directorio: Path) -> Iterator[bool]:
    """Exclusión entre disparos concurrentes: `flock` no bloqueante.

    Cede `True` si el lock se tomó (el llamador corre la corrida) o `False`
    si otro disparo lo tiene (el llamador asienta `omitida_lock`). El
    archivo vive en el directorio de salida, igual que el registro de
    insumos: la exclusión es entre procesos, no entre objetos.
    """

    ruta = Path(directorio) / LOCK_NOMBRE
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(ruta, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        raise SchedulerError("scheduler_lock_inaccesible") from None
    try:
        with os.fdopen(descriptor, "r+") as archivo:
            try:
                fcntl.flock(archivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(archivo.fileno(), fcntl.LOCK_UN)
    except OSError:
        raise SchedulerError("scheduler_lock_inaccesible") from None


@dataclass(frozen=True)
class PasoDiario:
    """Un paso del mantenimiento diario: nombre cerrado y operación.

    `correr` levanta ante una falla: el scheduler la asienta `falla` y la
    reintenta en el tick siguiente, así un día sin éxito no queda tapado.
    """

    nombre: str
    correr: Callable[[], None]


def disparar(
    *,
    ahora: datetime,
    corrida: Callable[[], Mapping[str, Any]],
    config: ConfiguracionScheduler,
    directorio: Path,
    pasos_diarios: Sequence[PasoDiario] = (),
    pasos_declarados: Sequence[str] = (),
    clock: Callable[[], datetime] | None = None,
    registro: RegistroCorridasArchivo | None = None,
) -> dict[str, Any]:
    """Un disparo de la agenda: ventana, dedupe, lock, mantenimiento, corrida.

    Devuelve (y anexa) la línea de auditoría del disparo. `corrida` es la
    corrida de insumos ya cableada: devuelve el informe como mapping (los
    conteos se republican sin el detalle por fila) o levanta; cualquier
    excepción termina en `falla` con código cerrado, nunca en traceback.
    `pasos_declarados` nombra pasos del diseño que aún no existen (el
    respaldo diario de #86): se asientan `pendiente` en el slot diario.
    """

    reloj = clock or (lambda: datetime.now(timezone.utc))
    registro = registro or RegistroCorridasArchivo(directorio)
    local = ahora.astimezone(config.zona)
    previsto = tick_previsto(ahora, config)

    entrada: dict[str, Any] = {
        "record": RECORD_CORRIDA,
        "correlation_id": str(uuid.uuid4()),
        "fecha": local.date().isoformat(),
        "en_ventana": previsto is not None,
        "inicio_previsto": _iso(previsto) if previsto is not None else None,
        "zona": config.zona.key,
    }

    if previsto is None:
        ahora_mismo = _iso(reloj())
        entrada.update(
            {
                "inicio_real": ahora_mismo,
                "fin": ahora_mismo,
                "resultado": "omitida_ventana",
            }
        )
        return registro.anexar(entrada)

    if _previsto_completado(registro, previsto):
        ahora_mismo = _iso(reloj())
        entrada.update(
            {
                "inicio_real": ahora_mismo,
                "fin": ahora_mismo,
                "resultado": "omitida_duplicada",
            }
        )
        return registro.anexar(entrada)

    with lock_corrida(directorio) as adquirido:
        if not adquirido:
            ahora_mismo = _iso(reloj())
            entrada.update(
                {
                    "inicio_real": ahora_mismo,
                    "fin": ahora_mismo,
                    "resultado": "omitida_lock",
                }
            )
            return registro.anexar(entrada)

        # Segunda consulta al registro ya bajo el lock: un disparo que
        # esperaba puede haber completado el tick entre la deduplicación de
        # afuera y la adquisición, y entonces no corre una segunda vez.
        if _previsto_completado(registro, previsto):
            ahora_mismo = _iso(reloj())
            entrada.update(
                {
                    "inicio_real": ahora_mismo,
                    "fin": ahora_mismo,
                    "resultado": "omitida_duplicada",
                }
            )
            return registro.anexar(entrada)

        entrada["inicio_real"] = _iso(reloj())
        mantenimiento = _correr_mantenimiento(
            registro,
            fecha=entrada["fecha"],
            pasos_diarios=pasos_diarios,
            pasos_declarados=pasos_declarados,
        )
        if mantenimiento:
            entrada["mantenimiento"] = mantenimiento
        try:
            informe = corrida()
        except OSError:
            entrada["resultado"] = "falla"
            entrada["detalle"] = "entrada_inaccesible"
        except Exception as exc:
            entrada["resultado"] = "falla"
            entrada["detalle"] = getattr(exc, "code", "scheduler_corrida_error")
        else:
            if isinstance(informe, Mapping):
                entrada["corrida"] = {
                    clave: informe[clave]
                    for clave in _CLAVES_RESUMEN_CORRIDA
                    if clave in informe
                }
                entrada["resultado"] = "completada"
            else:
                entrada["resultado"] = "falla"
                entrada["detalle"] = "scheduler_corrida_invalid"
        entrada["fin"] = _iso(reloj())

        # El asiento va adentro del lock: si quedara afuera, un disparo que
        # tomara el lock en el intervalo entre soltar y asentar no vería el
        # tick completado y correría una segunda vez la misma agenda.
        return registro.anexar(entrada)


def _correr_mantenimiento(
    registro: RegistroCorridasArchivo,
    *,
    fecha: str,
    pasos_diarios: Sequence[PasoDiario],
    pasos_declarados: Sequence[str],
) -> dict[str, str] | None:
    """El slot diario: corre una vez por fecha y reintenta lo que falló.

    La evidencia de "ya corrió hoy" es el propio log: una fecha con paso
    `completada` no se repite. El primer disparo del día en ventana corre
    todos los pasos; los siguientes sólo reintentan los que fallaron. Los
    pasos declarados (respaldo, #86) se listan `pendiente` cada vez que el
    slot corre, para que el hueco quede a la vista hasta implementarse.
    """

    completados: set[str] = set()
    hubo_slot = False
    for previa in registro.entradas():
        if previa.get("fecha") != fecha or not isinstance(
            previa.get("mantenimiento"), dict
        ):
            continue
        hubo_slot = True
        completados.update(
            paso for paso, res in previa["mantenimiento"].items() if res == "completada"
        )

    pendientes = [paso for paso in pasos_diarios if paso.nombre not in completados]
    if hubo_slot and not pendientes:
        return None

    bloque: dict[str, str] = {}
    for paso in pendientes:
        try:
            paso.correr()
        except Exception:
            bloque[paso.nombre] = "falla"
        else:
            bloque[paso.nombre] = "completada"
    for nombre in pasos_declarados:
        bloque[nombre] = "pendiente"
    return bloque or None


def _previsto_completado(registro: RegistroCorridasArchivo, previsto: datetime) -> bool:
    """Un tick ya completado no vuelve a correr ante un disparo extra.

    Sólo `completada` deduplica: una `falla` se reintenta en el disparo
    siguiente (otro tick), y las omitidas no ejecutaron nada que deduplicar.
    """

    texto = _iso(previsto)
    return any(
        entrada.get("inicio_previsto") == texto
        and entrada.get("resultado") == "completada"
        for entrada in registro.entradas()
    )


def bucle(
    *,
    corrida: Callable[[], Mapping[str, Any]],
    config: ConfiguracionScheduler,
    directorio: Path,
    pasos_diarios: Sequence[PasoDiario] = (),
    pasos_declarados: Sequence[str] = (),
    dormir: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] | None = None,
    max_disparos: int | None = None,
) -> int:
    """El mecanismo alternativo: esperar al próximo tick y disparar.

    `dormir` y `clock` son las costuras de las pruebas: el reloj falso
    avanza lo que el sleep pide y el bucle se ejercita sin espera real.
    `max_disparos` acota el bucle para corridas acotadas (pruebas, ensayos
    operativos); `None` corre para siempre, que es como lo deja el
    operador.
    """

    reloj = clock or (lambda: datetime.now(timezone.utc))
    corridas = 0
    posterior_a: datetime | None = None
    while True:
        ahora = reloj()
        # Si el reloj no avanzó más allá del tick recién corrido (una corrida
        # instantánea, o `ahora` cayó justo sobre el tick), la referencia de
        # búsqueda salta ese tick: sin esto el bucle dispararía el mismo
        # tick para siempre.
        referencia = ahora
        if posterior_a is not None and posterior_a > ahora:
            referencia = posterior_a
        proximo = proximo_disparo(referencia, config)
        espera = (proximo - ahora).total_seconds()
        if espera > 0:
            dormir(espera)
        disparar(
            ahora=reloj(),
            corrida=corrida,
            config=config,
            directorio=directorio,
            pasos_diarios=pasos_diarios,
            pasos_declarados=pasos_declarados,
            clock=reloj,
        )
        # Los ticks son segundos enteros: el próximo es estrictamente
        # posterior al recién disparado.
        posterior_a = proximo + timedelta(microseconds=1)
        corridas += 1
        if max_disparos is not None and corridas >= max_disparos:
            return 0


def _iso(valor: datetime) -> str:
    return valor.isoformat()
