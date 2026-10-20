"""Registro y aviso de cambios en la configuración por entorno (#94, ADR 0010).

La configuración por entorno —qué planilla, qué carpeta, qué plantilla, qué
rango— la cambia Informática sin pasar por el repo: es la clase que el ADR 0010
dejó **fuera** del fail-closed, porque frenar el arranque por una rotación solo
agrega fricción. Pero sigue siendo un cambio controlado, y un cambio que nadie
registra es indistinguible de una alteración: por eso su huella se compara con
la de la corrida anterior y, cuando difiere, queda en la auditoría —con las
claves afectadas, **sin sus valores**— y sale un aviso al operador.

Decisiones que no se ven en el código:

- **La huella sale de `resumen_seguro()`, nunca del entorno crudo.** El resumen
  que publica `ConfiguracionWorkspace` trae hashes de los identificadores,
  ambiente, endpoints y límites: entra lo que define los recursos y **no entra
  ni el token ni el refresh token**, así que rotar una credencial no dispara el
  aviso. Hashear el entorno entero habría metido los secretos en la huella y
  delatado cada rotación.
- **La auditoría es el estado.** El registro `logs/config-entorno.jsonl` es
  append-only y cada línea lleva el `resumen` vigente; la corrida anterior es la
  última línea válida. No hay un segundo archivo de estado que pueda divergir
  del asiento, y el respaldo diario (#86) ya recoge `logs/*.jsonl`.
- **Un cambio se avisa una sola vez.** La base se actualiza al observar la
  configuración, no al confirmar la entrega: si el correo falla, el error queda
  en la auditoría (`aviso=fallido`) y la próxima corrida no vuelve a avisar el
  mismo cambio. Reintentar por un canal roto llenaría el registro sin agregar
  información.
- **Nada de esto frena el arranque.** Ni el aviso ni la escritura del registro
  levantan hacia el llamador: el cambio queda asentado como mejor se pueda y la
  corrida sigue (ADR 0010). El fail-closed es del árbol de archivos, no de acá.
- **El aviso va a UNA dirección declarada, no a la lista entera.** La
  dirección sale de `AGENTE1_CONFIG_ENTORNO_AVISO_DESTINATARIO` y tiene que
  estar en la lista del modo de envío vigente: la de prueba (D12) por
  omisión, o la aprobada si `AGENTE1_GMAIL_MODO=produccion` (ticket #141).
  Sin dirección declarada el cambio se asienta `aviso=no_configurado` y no
  sale correo.
- **El cuerpo del aviso sólo nombra claves y cita hashes.** Los valores de los
  identificadores no viajan ni a la auditoría ni al correo: el aviso dice *qué*
  cambió, no *a qué*, y así no se convierte en un canal de fuga.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .confirmaciones import MARCADOR_BORRADOR, email_valido
from .gmail_envio import MODO_ENVIO_PRUEBA, GmailDestinoConfirmaciones
from .registro_auditoria import escribir_registro
from .workspace_config import ConfiguracionWorkspace, ConfiguracionWorkspaceError

AUDITORIA_RECORD = "agente1_config_entorno_v1"
AUDITORIA_NOMBRE = "config-entorno.jsonl"

# Dirección del operador que recibe el aviso. Prefijo propio: no es
# configuración de los adapters de Workspace y ningún loader la reclama.
ENV_AVISO_DESTINATARIO = "AGENTE1_CONFIG_ENTORNO_AVISO_DESTINATARIO"

# Los tres desenlaces de una corrida: primera vez (base, sin aviso), huella
# igual (nada que hacer) y huella distinta (se registra y se avisa).
RESULTADO_BASE = "BASE"
RESULTADO_SIN_CAMBIO = "SIN_CAMBIO"
RESULTADO_CAMBIO = "CAMBIO"

# Cómo quedó el aviso: salió por `gmail.send`, no había dirección declarada, o
# falló (y el error quedó asentado aparte).
AVISO_ENVIADO = "enviado"
AVISO_NO_CONFIGURADO = "no_configurado"
AVISO_FALLIDO = "fallido"

_AVISO_GMAIL_ERROR = "aviso_config_entorno_no_disponible"


class AvisoConfiguracion(Protocol):
    """Puerto del aviso al operador por un cambio de configuración.

    `avisar` devuelve el modo en que quedó registrado el envío (`enviado`).
    Levantar es una falla del medio: el llamador la convierte en un asiento
    con código y sigue.
    """

    def avisar(self, *, asunto: str, cuerpo: str) -> str: ...


@dataclass(frozen=True)
class ResultadoConfigEntorno:
    """Lo que dejó la revisión de la configuración en el arranque."""

    resultado: str
    huella: str
    huella_anterior: str | None
    claves_cambiadas: tuple[str, ...]
    aviso: str | None
    aviso_error: str | None
    audit_path: Path


def huella_configuracion(resumen: Mapping[str, object]) -> str:
    """El sha256 del resumen seguro, en JSON canónico.

    El mismo resumen produce siempre la misma huella: la comparación entre
    corridas no depende del orden de las claves ni del espaciado.
    """

    canonico = json.dumps(
        dict(resumen),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def claves_cambiadas(
    anterior: Mapping[str, object], actual: Mapping[str, object]
) -> tuple[str, ...]:
    """Los nombres de las claves cuyo valor difiere entre dos resúmenes.

    Devuelve sólo nombres, ordenados: el valor —el identificador o su hash— no
    sale de acá. Una clave que aparece o desaparece cuenta como cambio; los
    resúmenes del repo no usan `None` como valor, así que "ausente" y "nulo" no
    se confunden.
    """

    return tuple(
        clave
        for clave in sorted(set(anterior) | set(actual))
        if anterior.get(clave) != actual.get(clave)
    )


class AuditoriaConfigEntorno:
    """El registro de la configuración: una línea JSONL append-only por arranque.

    Vive en `logs/config-entorno.jsonl` bajo el directorio de salida, junto a
    los otros registros de operación, y viaja en el respaldo del día siguiente.
    Cada línea lleva la huella y el resumen seguro; la corrida anterior es la
    última línea válida, así que no hace falta un archivo de estado aparte.
    """

    def __init__(self, directorio_salida: Path) -> None:
        self._path = Path(directorio_salida) / "logs" / AUDITORIA_NOMBRE

    @property
    def path(self) -> Path:
        return self._path

    def leer_resumen_previo(self) -> dict[str, object] | None:
        """El resumen de la última corrida asentada, o `None` si no hay base.

        Tolerante a propósito: una línea cortada a mitad de escritura (un
        proceso muerto) se saltea y la base sigue siendo la anterior válida.
        """

        try:
            contenido = self._path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        for linea in reversed(contenido.splitlines()):
            if not linea.strip():
                continue
            try:
                entrada = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if not isinstance(entrada, dict) or entrada.get("record") != AUDITORIA_RECORD:
                continue
            resumen = entrada.get("resumen")
            if isinstance(resumen, dict):
                return dict(resumen)
        return None

    def anexar(
        self,
        *,
        resultado: str,
        huella: str,
        huella_anterior: str | None,
        claves: tuple[str, ...],
        resumen: Mapping[str, object],
        aviso: str | None,
        aviso_error: str | None,
        ejecutado_en: datetime,
    ) -> dict[str, object]:
        entrada = {
            "record": AUDITORIA_RECORD,
            "resultado": resultado,
            "huella": huella,
            "huella_anterior": huella_anterior,
            "claves_cambiadas": list(claves),
            "resumen": dict(resumen),
            "aviso": aviso,
            "aviso_error": aviso_error,
            "ejecutado_en": ejecutado_en.astimezone(timezone.utc).isoformat(),
        }
        return escribir_registro(self._path, entrada)


def revisar_configuracion_al_arrancar(
    *,
    config: ConfiguracionWorkspace,
    directorio_salida: Path,
    aviso: AvisoConfiguracion | None = None,
    clock: Callable[[], datetime] | None = None,
) -> ResultadoConfigEntorno:
    """Compara la huella de la configuración con la de la corrida anterior.

    La primera corrida asienta la base sin avisar. Si la huella no cambió,
    deja constancia de que se comparó. Si cambió, asienta las claves afectadas
    (sin valores) e intenta el aviso: una falla del aviso no levanta, queda en
    la auditoría y la corrida sigue.
    """

    resumen = dict(config.resumen_seguro())
    huella = huella_configuracion(resumen)
    auditoria = AuditoriaConfigEntorno(directorio_salida)
    reloj = clock or (lambda: datetime.now(timezone.utc))
    previo = auditoria.leer_resumen_previo()

    if previo is None:
        auditoria.anexar(
            resultado=RESULTADO_BASE,
            huella=huella,
            huella_anterior=None,
            claves=(),
            resumen=resumen,
            aviso=None,
            aviso_error=None,
            ejecutado_en=reloj(),
        )
        return ResultadoConfigEntorno(
            resultado=RESULTADO_BASE,
            huella=huella,
            huella_anterior=None,
            claves_cambiadas=(),
            aviso=None,
            aviso_error=None,
            audit_path=auditoria.path,
        )

    huella_previa = huella_configuracion(previo)
    if huella_previa == huella:
        auditoria.anexar(
            resultado=RESULTADO_SIN_CAMBIO,
            huella=huella,
            huella_anterior=huella_previa,
            claves=(),
            resumen=resumen,
            aviso=None,
            aviso_error=None,
            ejecutado_en=reloj(),
        )
        return ResultadoConfigEntorno(
            resultado=RESULTADO_SIN_CAMBIO,
            huella=huella,
            huella_anterior=huella_previa,
            claves_cambiadas=(),
            aviso=None,
            aviso_error=None,
            audit_path=auditoria.path,
        )

    claves = claves_cambiadas(previo, resumen)
    aviso_resultado, aviso_error = _intentar_aviso(
        aviso=aviso,
        claves=claves,
        huella=huella,
        huella_anterior=huella_previa,
    )
    auditoria.anexar(
        resultado=RESULTADO_CAMBIO,
        huella=huella,
        huella_anterior=huella_previa,
        claves=claves,
        resumen=resumen,
        aviso=aviso_resultado,
        aviso_error=aviso_error,
        ejecutado_en=reloj(),
    )
    return ResultadoConfigEntorno(
        resultado=RESULTADO_CAMBIO,
        huella=huella,
        huella_anterior=huella_previa,
        claves_cambiadas=claves,
        aviso=aviso_resultado,
        aviso_error=aviso_error,
        audit_path=auditoria.path,
    )


def cargar_destinatario_aviso(
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Lee la dirección del operador; ausente es "no declarado", no error.

    `None` cuando la variable no está: el cambio igual se asienta y no sale
    correo. Una dirección declarada pero vacía o mal formada sí falla, con
    código y sin el valor adentro.
    """

    env = os.environ if environ is None else environ
    crudo = env.get(ENV_AVISO_DESTINATARIO)
    if crudo is None:
        return None
    valor = crudo.strip()
    if not valor or not email_valido(valor):
        raise ConfiguracionWorkspaceError("config_entorno_aviso_invalid")
    return valor


class AvisoConfiguracionGmail:
    """Aviso real por `gmail.send`, cercado por la lista del destino.

    Reusa `GmailDestinoConfirmaciones`, el único destino de correo habilitado:
    la dirección tiene que estar en la lista o la entrega se rechaza antes de
    la red. En modo prueba el cuerpo sale con la marca de borrador como
    cualquier correo del agente; en modo producción (ticket #141) sale sin
    marca, porque el destinatario es el operador real y el modo producción no
    admite cuerpos marcados. La clave de idempotencia es un hash del aviso, no
    un dato.
    """

    def __init__(
        self, *, destinatario: str, destino: GmailDestinoConfirmaciones
    ) -> None:
        if not email_valido(destinatario):
            raise ValueError("destinatario del aviso inválido")
        self._destinatario = destinatario
        self._destino = destino

    def avisar(self, *, asunto: str, cuerpo: str) -> str:
        cuerpo_final = (
            MARCADOR_BORRADOR + "\n" + cuerpo
            if self._destino.modo == MODO_ENVIO_PRUEBA
            else cuerpo
        )
        self._destino.entregar(
            idempotency_key=hashlib.sha256(
                f"aviso-config-entorno|{asunto}|{cuerpo}".encode("utf-8")
            ).hexdigest(),
            destinatario=self._destinatario,
            asunto=asunto,
            cuerpo=cuerpo_final,
        )
        return AVISO_ENVIADO


def _intentar_aviso(
    *,
    aviso: AvisoConfiguracion | None,
    claves: tuple[str, ...],
    huella: str,
    huella_anterior: str,
) -> tuple[str, str | None]:
    """Intenta el aviso y traduce el desenlace a un par (modo, error).

    Nunca levanta: la falla del aviso es un asiento más, no una razón para
    frenar el arranque (ADR 0010).
    """

    if aviso is None:
        return AVISO_NO_CONFIGURADO, None
    asunto = "Agente 1: cambió la configuración por entorno"
    cuerpo = _cuerpo_aviso(
        claves=claves, huella=huella, huella_anterior=huella_anterior
    )
    try:
        return aviso.avisar(asunto=asunto, cuerpo=cuerpo), None
    except Exception as exc:
        return AVISO_FALLIDO, _codigo_error(exc)


def _cuerpo_aviso(
    *, claves: tuple[str, ...], huella: str, huella_anterior: str
) -> str:
    """El texto del aviso: claves y hashes, nunca los valores.

    Dice *qué* claves cambiaron y cita las dos huellas, sin los
    identificadores: sirve para que el operador sepa qué revisar en el log de
    la consola de Google, no para reconstruir la configuración desde el correo.
    """

    listado = ", ".join(claves) if claves else "(sin claves identificadas)"
    return (
        "La configuración por entorno del Agente 1 cambió entre corridas.\n\n"
        f"Claves afectadas: {listado}\n"
        f"Huella anterior: {huella_anterior}\n"
        f"Huella actual:   {huella}\n\n"
        "El aviso no lleva los identificadores, sólo sus claves y hashes. "
        "Revisar el cambio también en la sección «Configuración» de "
        "CHANGELOG.md y en el log de la consola de Google.\n"
    )


def _codigo_error(exc: BaseException) -> str:
    """El código estable de la falla; nunca el mensaje ni el valor adentro."""

    codigo = getattr(exc, "code", None)
    if isinstance(codigo, str) and codigo:
        return codigo
    return _AVISO_GMAIL_ERROR
