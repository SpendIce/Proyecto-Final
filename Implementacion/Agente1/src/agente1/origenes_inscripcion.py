"""Matriz operativa de HU-012 por origen de inscripción.

La SEU comunicó dónde se inscribe cada tipo de actividad, pero no comunicó
identificadores, estados de preinscripción, responsables del dato ni regla de
autorización de envío. Este módulo hace explícita esa distinción: expone la
matriz declarada en `contracts/matriz_origenes_inscripcion_v1.json` y una
decisión de envío **fail-closed** que enumera, por origen, exactamente qué
falta.

No conecta SIU Guaraní, Google Forms ni correo, y no habilita envío en ningún
caso: sirve para especificar el adapter futuro y para que el pedido pendiente a
la SEU sea puntual.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


MATRIZ = json.loads(
    files("agente1")
    .joinpath("contracts", "matriz_origenes_inscripcion_v1.json")
    .read_text(encoding="utf-8")
)

CONTRACT_VERSION = MATRIZ["x-contract-version"]
STATUS = MATRIZ["x-status"]
PROCEDENCIAS = frozenset(MATRIZ["procedencia_dato"])
MOTIVOS_DE_BLOQUEO = frozenset(MATRIZ["motivos_de_bloqueo"])
CAMPOS_REQUERIDOS_POR_CONTRATO = tuple(MATRIZ["campos_requeridos_por_contrato"])
ESTADOS_PREINSCRIPCION_CANDIDATOS = tuple(
    MATRIZ["estados_preinscripcion_candidatos"]["valores"]
)
ORIGENES = {str(item["origen"]): item for item in MATRIZ["origenes"]}
ORIGENES_DE_INSCRIPCION = tuple(
    origen
    for origen, item in ORIGENES.items()
    if item["clase"] == "ORIGEN_DE_INSCRIPCION"
)
PREGUNTAS_ABIERTAS = tuple(MATRIZ["preguntas_abiertas"])


class OrigenDesconocidoError(KeyError):
    """Un origen fuera de la matriz no puede evaluarse ni asumirse seguro."""


@dataclass(frozen=True)
class DecisionEnvio:
    """Resultado fail-closed de evaluar si A1 puede enviar una confirmación."""

    origen: str
    tipo_actividad: str | None
    autorizado: bool
    motivos: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.autorizado and self.motivos:
            raise ValueError("una decisión autorizada no puede tener motivos abiertos")
        if not self.autorizado and not self.motivos:
            raise ValueError("un bloqueo debe declarar al menos un motivo")


def descripcion(origen: str) -> dict[str, object]:
    try:
        return ORIGENES[origen]
    except KeyError as exc:
        raise OrigenDesconocidoError(origen) from exc


def campos_sin_confirmar(origen: str) -> tuple[str, ...]:
    """Campos del contrato v2 que el origen no tiene confirmados por la SEU."""
    disponibles = descripcion(origen)["campos_disponibles"]
    return tuple(
        campo
        for campo in CAMPOS_REQUERIDOS_POR_CONTRATO
        if campo in disponibles and disponibles[campo] != "CONFIRMADO_SEU"
    )


def evaluar_envio(
    origen: str,
    *,
    tipo_actividad: str | None = None,
    estado_preinscripcion: str | None = None,
) -> DecisionEnvio:
    """Decide si A1 puede enviar. Hoy la respuesta es siempre no.

    El valor de la función no es el booleano sino la enumeración de motivos:
    cada uno corresponde a una definición institucional faltante y a una
    pregunta concreta de `PREGUNTAS_ABIERTAS`.
    """

    item = descripcion(origen)
    motivos = list(item["motivos_de_bloqueo"])
    if tipo_actividad is not None and tipo_actividad not in item["tipos_actividad"]:
        motivos.append("combinacion_origen_tipo_no_confirmada")
    if estado_preinscripcion is not None:
        motivos.append("estado_preinscripcion_no_confirmado")
    return DecisionEnvio(
        origen=origen,
        tipo_actividad=tipo_actividad,
        autorizado=False,
        motivos=tuple(dict.fromkeys(motivos)),
    )
