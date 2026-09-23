"""Catálogo cerrado de tipos de notificación de HU-012.

La bible sincronizada el 22/09 amplió HU-012: de «confirmaciones de
inscripción» a «notificaciones automáticas de inscripción, participación,
situación de pagos y aprobación», absorbiendo la HU previa de mensajes a
deudores. Este módulo expone el catálogo declarado en
`contracts/tipos_notificacion_v1.json` y una decisión **fail-closed** por tipo:
`evaluar_tipo` enumera qué falta para que ese tipo pueda producir algo.

La decisión de tipo no es la decisión de envío. Un tipo `habilitado` sólo
puede entrar al pipeline offline de `confirmaciones.py` —borrador, doble
aprobación, entrega contra el fake—; no levanta los bloqueos de la matriz de
orígenes (`origenes_inscripcion.py`, todo `PROHIBIDO` mientras no haya
adapter) ni autoriza correo real. `situacion_pagos` queda declarada pero
bloqueada: el dato que la distingue —la deuda o el saldo del inscripto— no
tiene origen confirmado por la SEU, así que una solicitud de ese tipo se
rechaza antes de crear registro.

Por qué `SUPUESTO_TECNICO` no bloquea: es una hipótesis declarada para que la
SEU la corrija sobre algo concreto, mismo criterio que los campos de la
matriz de orígenes. Lo que no se puede ni suponer con fundamento
(`DESCONOCIDO`) sí bloquea, porque no hay manera honesta de modelarlo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


CATALOGO = json.loads(
    files("agente1")
    .joinpath("contracts", "tipos_notificacion_v1.json")
    .read_text(encoding="utf-8")
)

CONTRACT_VERSION = CATALOGO["x-contract-version"]
STATUS = CATALOGO["x-status"]
PROCEDENCIAS = frozenset(CATALOGO["procedencia_dato"])
MOTIVOS_DE_BLOQUEO = frozenset(CATALOGO["motivos_de_bloqueo"])
TIPOS = {str(item["tipo"]): item for item in CATALOGO["tipos"]}
TIPOS_NOTIFICACION = frozenset(TIPOS)
PREGUNTAS_ABIERTAS = tuple(CATALOGO["preguntas_abiertas"])

# La solicitud nació como confirmación de inscripción: las entradas que no
# declaran tipo se interpretan como ese tipo, que era el único que existía.
# El default preserva el comportamiento previo a la ampliación del 22/09.
TIPO_NOTIFICACION_PREDETERMINADO = "inscripcion"


class TipoNotificacionDesconocidoError(KeyError):
    """Un tipo fuera del catálogo no puede evaluarse ni asumirse seguro."""


@dataclass(frozen=True)
class DecisionTipoNotificacion:
    """Resultado fail-closed de evaluar si un tipo puede entrar al pipeline.

    `habilitado` no significa «puede enviarse»: significa que el tipo tiene
    definición suficiente para que una solicitud suya produzca un borrador y
    siga el circuito. La autorización de envío sigue siendo la doble
    aprobación humana más el destino fake, y el acceso a los datos sigue
    bloqueado por la matriz de orígenes.
    """

    tipo: str
    origen: str | None
    habilitado: bool
    motivos: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.habilitado and self.motivos:
            raise ValueError("una decisión habilitada no puede tener motivos abiertos")
        if not self.habilitado and not self.motivos:
            raise ValueError("un bloqueo debe declarar al menos un motivo")


def descripcion_tipo(tipo: str) -> dict[str, object]:
    try:
        return TIPOS[tipo]
    except KeyError as exc:
        raise TipoNotificacionDesconocidoError(tipo) from exc


def campos_requeridos(tipo: str) -> tuple[str, ...]:
    """Campos del contrato que el tipo exige completos en la solicitud."""

    return tuple(descripcion_tipo(tipo)["campos_requeridos"])


def datos_sin_origen_confirmado(tipo: str) -> tuple[str, ...]:
    """Datos específicos del tipo cuya procedencia es `DESCONOCIDO`.

    Es la enumeración puntual de lo que la SEU tiene que definir para que el
    tipo pueda habilitarse: hoy sólo `situacion_pagos` tiene uno.
    """

    datos = descripcion_tipo(tipo)["datos_especificos"]
    return tuple(
        dato for dato, procedencia in datos.items() if procedencia == "DESCONOCIDO"
    )


def evaluar_tipo(tipo: str, *, origen: str | None = None) -> DecisionTipoNotificacion:
    """Decide si el tipo puede entrar al pipeline. Sólo `situacion_pagos` no.

    El valor de la función no es el booleano sino la enumeración de motivos:
    cada uno corresponde a una definición institucional faltante y a una
    pregunta concreta de `PREGUNTAS_ABIERTAS`. Con `origen` informado,
    además se verifica que ese origen esté declarado como admisible para el
    tipo —un destinatario no puede provenir de un origen que el catálogo no
    contempla para ese tipo.
    """

    item = descripcion_tipo(tipo)
    motivos = list(item["motivos_de_bloqueo"])
    if origen is not None and origen not in item["origenes_admisibles"]:
        motivos.append("origen_no_admitido_para_tipo")
    return DecisionTipoNotificacion(
        tipo=tipo,
        origen=origen,
        habilitado=not motivos,
        motivos=tuple(dict.fromkeys(motivos)),
    )
