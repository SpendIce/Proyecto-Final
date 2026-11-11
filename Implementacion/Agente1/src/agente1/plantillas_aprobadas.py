"""Plantillas de correo aprobadas por tipo, para el modo producción (#142).

En modo prueba los renderers componen el cuerpo con la marca de borrador —
`BORRADOR — NO ENVIAR` en correos, `BORRADOR — NO EMITIR` en certificados —
y un destino de prueba la exige. En modo producción el adapter Gmail la
rechaza: el cuerpo que se entrega tiene que salir de una **plantilla
aprobada por tipo**, sin marcas.

La plantilla no la inventa el agente: el texto es redacción de la SEU y
vive fuera del repo, igual que la lista aprobada de destinatarios, en el
archivo que declara `AGENTE1_PLANTILLAS_APROBADAS_PATH`. Pero «aprobada»
no se infiere de que el archivo exista: por la definición del 11/11
(#125, glosario «Validación humana») toda aprobación queda registrada.
La versión usable en producción es la que tiene una `apruebo_contenido`
`registrada` de `APROBADOR_CONTENIDO` en el registro de decisiones, sobre
el objeto `tpl-<tipo>-<hash del texto>` — mismo circuito que las
plantillas de actividad. Una plantilla sin esa decisión, o cuyo texto
cambió desde la aprobada — el hash ya no coincide y la decisión queda
atada a la versión vieja —, se rechaza con `template_version_unapproved`
y no se entrega nada.

Tipos declarados por el mecanismo:

- Los cinco tipos `por_envio` de HU-012: `inscripcion`, `participacion`,
  `situacion_pagos`, `aprobacion` e `instrucciones_pago`.
- `recordatorio_pago`: el ítem del lote de recordatorios de HU-012.
- `correo_actividad`: el correo por destinatario del lote de actividad.
- `certificado_asistencia`: el cuerpo del certificado HU-014 de
  `asistencia`, hasta que llegue su variante institucional (`aprobacion`
  compone el diseño SEU recibido en #126 y no exige entrada acá).
- `correo_certificado`: el correo que lleva el PDF al titular.

Este módulo deja el mecanismo compartido: `PlantillaCorreo` por tipo, la
carga del archivo, el id de versión que el registro de decisiones
autoriza, la sustitución `{{variable}}` sin llaves sueltas y la
validación de forma que todos los circuitos repiten.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .workspace_config import ConfiguracionWorkspaceError

PLANTILLAS_APROBADAS_PATH_ENV = "AGENTE1_PLANTILLAS_APROBADAS_PATH"

# La línea provisional que comparten las plantillas provisionales: es
# parte del texto de prueba que el circuito aprueba como borrador, no del
# texto institucional, y ningún renderer la poda para producción — en
# producción el cuerpo sale entero de la plantilla aprobada del tipo.
LINEA_PROVISIONAL = (
    "Este texto es una plantilla provisional y requiere validación "
    "humana antes de cualquier envío."
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_TIPO_RE = re.compile(r"[a-z0-9_]+\Z")

# Códigos de rechazo compartidos de la vía producción. `*_file_*` es la
# falla del archivo de plantillas (la carga); `approved_template_*` es la
# del tipo concreto que una corrida pidió; `template_version_unapproved`
# es la versión sin decisión registrada — los pares singular/plural que
# sólo se distinguían por una «s» quedaron renombrados para que un typo
# no cambie el diagnóstico.
PLANTILLAS_FILE_MISSING = "approved_templates_file_missing"
PLANTILLAS_FILE_INVALID = "approved_templates_file_invalid"
PLANTILLA_TIPO_MISSING = "approved_template_missing"
PLANTILLA_TIPO_INVALID = "approved_template_invalid"
PLANTILLA_VERSION_NO_APROBADA = "template_version_unapproved"


@dataclass(frozen=True)
class PlantillaCorreo:
    """Una redacción aprobada para un tipo de pieza.

    `asunto` y `cuerpo` llevan variables `{{nombre}}` que el renderer
    completa con los datos del circuito. `asunto=None` declara que el
    asunto lo fija el dato y no la plantilla — `instrucciones_pago` lo
    toma del `asunto_preinscripcion` del plan — así que un tipo que
    necesita asunto aprobado tiene que declararlo no vacío.
    """

    asunto: str | None
    cuerpo: str


class PlantillaAprobadaError(RuntimeError):
    """Falla del render contra una plantilla aprobada, con código auditable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def cargar_plantillas_aprobadas(
    environ: Mapping[str, str] | None = None,
) -> dict[str, PlantillaCorreo]:
    """Lee el archivo de plantillas aprobadas declarado por el entorno.

    El archivo es JSON de la forma
    `{"<tipo>": {"asunto": "...", "cuerpo": "..."}}` y vive fuera del
    repo, como la lista aprobada: la SEU redacta el texto y quien opera
    lo escribe en el env file. `asunto` puede omitirse en los tipos que
    lo derivan del dato.

    Falla cerrado como el resto de la configuración de producción: sin la
    variable o sin archivo legible es `approved_templates_file_missing`;
    un JSON mal armado, una entrada sin la forma esperada o un texto que
    todavía lleva marcas de borrador es `approved_templates_file_invalid`.
    Los códigos no traen datos: el contenido de una plantilla nunca va a
    un log.

    La carga sólo lee el texto: la aprobación de cada versión la verifica
    el circuito contra el registro de decisiones — ver
    `id_version_plantilla` y `plantilla_version_registrada`.
    """

    env = os.environ if environ is None else environ
    crudo = env.get(PLANTILLAS_APROBADAS_PATH_ENV)
    if crudo is None or not crudo.strip():
        raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_MISSING)
    try:
        texto = Path(crudo.strip()).expanduser().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_MISSING) from None
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_INVALID) from None
    if not isinstance(datos, dict) or not datos:
        raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_INVALID)
    plantillas: dict[str, PlantillaCorreo] = {}
    for tipo, entrada in datos.items():
        if (
            not isinstance(tipo, str)
            or _TIPO_RE.fullmatch(tipo) is None
            or not isinstance(entrada, dict)
            or any(clave not in {"asunto", "cuerpo"} for clave in entrada)
            or not isinstance(entrada.get("cuerpo"), str)
            or not entrada["cuerpo"].strip()
            or (
                "asunto" in entrada
                and (
                    not isinstance(entrada["asunto"], str)
                    or not entrada["asunto"].strip()
                )
            )
        ):
            raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_INVALID)
        asunto = entrada.get("asunto")
        if _tiene_marcas_borrador(entrada["cuerpo"]) or (
            isinstance(asunto, str) and _tiene_marcas_borrador(asunto)
        ):
            # Una marca de borrador no es texto aprobado: aceptarla dejaría
            # un cuerpo que el adapter rechaza con `draft_marker_in_production`
            # o, peor, una marca que pasa inadvertida a mitad del cuerpo.
            raise ConfiguracionWorkspaceError(PLANTILLAS_FILE_INVALID)
        plantillas[tipo] = PlantillaCorreo(
            asunto=asunto.strip() if isinstance(asunto, str) else None,
            cuerpo=entrada["cuerpo"],
        )
    return plantillas


def _tiene_marcas_borrador(texto: str) -> bool:
    """Las marcas de borrador del sistema, en cualquier posición."""

    # Imports perezosos: `confirmaciones` y `certificados_emision` consumen
    # este módulo y las marcas son constantes de esos árboles; un import de
    # módulo haría un ciclo.
    from .certificados import MARCADOR_BORRADOR as MARCADOR_BORRADOR_CERT
    from .confirmaciones import MARCADOR_BORRADOR
    from .destinos import BORRADOR_MARKER

    return (
        MARCADOR_BORRADOR in texto
        or BORRADOR_MARKER in texto
        or MARCADOR_BORRADOR_CERT in texto
    )


def id_version_plantilla(tipo: str, plantilla: PlantillaCorreo) -> str:
    """Id del objeto `plantilla` de esta versión, para el registro.

    Deriva del texto íntegro — asunto y cuerpo — igual que
    `plantillas_actividad.id_plantilla` deriva del documento: aprobar
    este objeto con `apruebo_contenido` es aprobar esa redacción exacta.
    Un texto que cambia produce un id distinto, así que la decisión
    registrada queda atada a la versión aprobada y una edición posterior
    del archivo no «hereda» la aprobación.
    """

    texto = f"{plantilla.asunto or ''}\n{plantilla.cuerpo}"
    return f"tpl-{tipo}-{hashlib.sha256(texto.encode('utf-8')).hexdigest()[:24]}"


def plantilla_version_registrada(
    decisiones, *, tipo: str, plantilla: PlantillaCorreo
) -> bool:
    """¿La versión de esta plantilla tiene la aprobación registrada?

    Consulta el registro de decisiones por la `apruebo_contenido`
    `registrada` del rol `APROBADOR_CONTENIDO` sobre
    `id_version_plantilla(tipo, plantilla)`: la definición del 11/11
    (#125) exige que «aprobada» sea un hecho del registro, no del
    archivo. Devuelve `False` sin el registro — producción no puede
    verificar sin él — y con un texto editado después de la decisión.
    """

    if decisiones is None or not callable(
        getattr(decisiones, "procesadas", None)
    ):
        return False
    # Import perezoso: `decisiones_form` importa `confirmaciones`, que a
    # su vez consume este módulo — un ciclo a nivel de módulo.
    from .confirmaciones import ROL_APROBADOR_CONTENIDO
    from .decisiones_form import (
        DECISION_APRUEBO_CONTENIDO,
        TIPO_PLANTILLA,
        decision_registrada,
    )

    return decision_registrada(
        decisiones,
        tipo=TIPO_PLANTILLA,
        objeto_id=id_version_plantilla(tipo, plantilla),
        decision=DECISION_APRUEBO_CONTENIDO,
        rol=ROL_APROBADOR_CONTENIDO,
    )


def variables_plantilla(texto: str) -> frozenset[str]:
    """El conjunto de nombres `{{variable}}` que un texto declara.

    Lo usan los circuitos para verificar, antes de componer nada, que la
    plantilla aprobada no nombre un dato que no existe para ese tipo:
    validar el conjunto es más claro que descubrir la llave suelta a mitad
    del render.
    """

    return frozenset(_PLACEHOLDER_RE.findall(texto))


def validar_forma_plantilla(
    plantilla: PlantillaCorreo,
    *,
    asunto_requerido: bool,
    variables_permitidas: frozenset[str],
) -> str | None:
    """La forma que toda plantilla aprobada tiene que cumplir por tipo.

    Devuelve `None` si cierra o el código de rechazo si no:
    `approved_template_invalid` cubre las dos fallas — el asunto
    obligatorio vacío y una variable que el circuito no completa — porque
    ambas son «la redacción registrada no tiene la forma que el tipo
    exige». La usan todos los circuitos de producción para no repetir la
    validación a mano.
    """

    if asunto_requerido and not (plantilla.asunto or "").strip():
        return PLANTILLA_TIPO_INVALID
    variables = variables_plantilla(plantilla.cuerpo) | variables_plantilla(
        plantilla.asunto or ""
    )
    if not variables <= variables_permitidas:
        return PLANTILLA_TIPO_INVALID
    return None


def renderizar_plantilla(texto: str, valores: Mapping[str, str]) -> str:
    """Sustituye cada `{{variable}}` por su valor. Sin variables sueltas.

    Una variable sin valor declarado es un error de configuración o de
    programación — la plantilla que la SEU aprobó nombra un dato que el
    circuito no completa — y falla cerrado antes de entregar una llave
    suelta al destinatario, mismo criterio que los renderers existentes.
    """

    resultado = _PLACEHOLDER_RE.sub(
        lambda match: valores.get(match.group(1), match.group(0)), texto
    )
    if _PLACEHOLDER_RE.search(resultado):
        raise PlantillaAprobadaError("template_variable_without_value")
    return resultado


def modo_envio_efectivo(
    destino: object, modo_envio: str | None
) -> str | None:
    """La única fuente del modo: el destino (#142, revisión).

    Devuelve el `modo` que el destino declara — el Protocol de destinos
    lo exige —; con un destino que no lo declara, el parámetro que el
    llamador pasó, y sin ninguno de los dos, `prueba`. Si el parámetro
    sobrevive al lado de un destino que declara otro modo, devuelve
    `None`: el llamador lo convierte en `send_mode_mismatch`, porque un
    modo por dos vías que no coincide es ambiguo y falla cerrado.
    """

    from .gmail_envio import MODO_ENVIO_PRUEBA

    modo_destino = (
        getattr(destino, "modo", None) if destino is not None else None
    )
    if modo_destino is not None:
        if modo_envio is not None and modo_envio != modo_destino:
            return None
        return modo_destino
    return modo_envio or MODO_ENVIO_PRUEBA


__all__ = [
    "LINEA_PROVISIONAL",
    "PLANTILLAS_APROBADAS_PATH_ENV",
    "PLANTILLAS_FILE_INVALID",
    "PLANTILLAS_FILE_MISSING",
    "PLANTILLA_TIPO_INVALID",
    "PLANTILLA_TIPO_MISSING",
    "PLANTILLA_VERSION_NO_APROBADA",
    "PlantillaAprobadaError",
    "PlantillaCorreo",
    "cargar_plantillas_aprobadas",
    "id_version_plantilla",
    "modo_envio_efectivo",
    "plantilla_version_registrada",
    "renderizar_plantilla",
    "validar_forma_plantilla",
    "variables_plantilla",
]
