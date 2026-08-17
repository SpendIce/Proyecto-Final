"""Contrato candidato para insumos de A2-A5 hacia el Agente 1.

El módulo sólo valida datos. No despacha tareas, no invoca agentes y no interpreta
texto del payload como instrucciones ejecutables.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


CONTRACT_VERSION = "agente1_insumo_candidate_v1"
SCHEMA_NAME = "agente1.insumo.v1"
SCHEMA_VERSION = "1.0.0"
CHANNEL = "a1.communication_input"
CONTRACT_STATUS = "CANDIDATO_NO_INSTITUCIONAL"

PRODUCER_CONTRACTS = {
    "A2": {
        "version": "a2_candidate_v1",
        "payload_types": frozenset({"dato_historico", "efemeride"}),
    },
    "A3": {
        "version": "a3_candidate_v1",
        "payload_types": frozenset({"evento", "oportunidad_externa"}),
    },
    "A4": {
        "version": "a4_candidate_v1",
        "payload_types": frozenset(
            {"consulta_propuesta", "solicitud_material_orientacion"}
        ),
    },
    "A5": {
        "version": "a5_candidate_v1",
        "payload_types": frozenset(
            {"analitica_contenido", "texto_rrss_enriquecido"}
        ),
    },
}

DATA_ORIGINS = frozenset(
    {"institutional_source", "agent_derived", "synthetic_test"}
)
ENVELOPE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "channel",
        "producer",
        "producer_schema_version",
        "correlation_id",
        "timestamp",
        "data_origin",
        "provenance",
        "payload",
    }
)
PROVENANCE_FIELDS = frozenset({"sources"})
SOURCE_FIELDS = frozenset({"ref", "sha256"})
PAYLOAD_FIELDS = frozenset({"type", "content"})
OPAQUE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ResultadoValidacionInsumo:
    aceptado: bool
    codigo: str
    envelope: dict[str, Any] | None
    producer: str | None
    payload_hash: str | None
    source_count: int


def validar_insumo_agente(raw: object) -> ResultadoValidacionInsumo:
    """Valida y copia un envelope candidato sin ejecutar su contenido."""

    if not isinstance(raw, dict):
        return _rechazo("envelope_not_object")
    raw_producer = raw.get("producer")
    producer = (
        raw_producer
        if isinstance(raw_producer, str) and raw_producer in PRODUCER_CONTRACTS
        else None
    )
    if set(raw) != ENVELOPE_FIELDS:
        return _rechazo("envelope_fields_invalid", producer)
    if raw["schema"] != SCHEMA_NAME or raw["schema_version"] != SCHEMA_VERSION:
        return _rechazo("version_not_supported", producer)
    if raw["channel"] != CHANNEL:
        return _rechazo("channel_not_allowed", producer)
    if producer is None:
        return _rechazo("producer_not_allowed", producer)
    producer_contract = PRODUCER_CONTRACTS[producer]
    if raw["producer_schema_version"] != producer_contract["version"]:
        return _rechazo("version_not_supported", producer)
    if not _identificador_opaco_valido(raw["correlation_id"]):
        return _rechazo("correlation_id_invalid", producer)
    if not _timestamp_con_zona_valido(raw["timestamp"]):
        return _rechazo("timestamp_invalid", producer)
    if not isinstance(raw["data_origin"], str) or raw["data_origin"] not in DATA_ORIGINS:
        return _rechazo("data_origin_invalid", producer)

    sources = _validar_provenance(raw["provenance"])
    if sources is None:
        return _rechazo("provenance_invalid", producer)
    payload = raw["payload"]
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS:
        return _rechazo("payload_fields_invalid", producer, len(sources))
    if (
        not isinstance(payload["type"], str)
        or payload["type"] not in producer_contract["payload_types"]
    ):
        return _rechazo("payload_type_not_allowed", producer, len(sources))
    if not isinstance(payload["content"], dict) or not payload["content"]:
        return _rechazo("payload_content_invalid", producer, len(sources))
    if not _json_data_valida(payload["content"]):
        return _rechazo("payload_content_invalid", producer, len(sources))

    envelope = copy.deepcopy(raw)
    payload_hash = _sha256_json(envelope["payload"])
    return ResultadoValidacionInsumo(
        aceptado=True,
        codigo="accepted_candidate_contract",
        envelope=envelope,
        producer=producer,
        payload_hash=payload_hash,
        source_count=len(sources),
    )


def resumen_auditoria_insumo(
    resultado: ResultadoValidacionInsumo,
) -> dict[str, str | int | bool | None]:
    """Construye evidencia segura: nunca incluye payload, PII o referencias fuente."""

    return {
        "contract_version": CONTRACT_VERSION,
        "contract_status": CONTRACT_STATUS,
        "accepted": resultado.aceptado,
        "result_code": resultado.codigo,
        "producer": resultado.producer,
        "payload_hash": resultado.payload_hash,
        "source_count": resultado.source_count,
    }


def _rechazo(
    codigo: str, producer: str | None = None, source_count: int = 0
) -> ResultadoValidacionInsumo:
    return ResultadoValidacionInsumo(
        aceptado=False,
        codigo=codigo,
        envelope=None,
        producer=producer,
        payload_hash=None,
        source_count=source_count,
    )


def _identificador_opaco_valido(value: object) -> bool:
    return isinstance(value, str) and OPAQUE_ID_RE.fullmatch(value) is not None


def _timestamp_con_zona_valido(value: object) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validar_provenance(value: object) -> list[dict[str, str]] | None:
    if not isinstance(value, dict) or set(value) != PROVENANCE_FIELDS:
        return None
    sources = value["sources"]
    if not isinstance(sources, list) or not sources or len(sources) > 100:
        return None
    refs: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
            return None
        ref = source["ref"]
        digest = source["sha256"]
        if (
            not _identificador_opaco_valido(ref)
            or not isinstance(digest, str)
            or SHA256_RE.fullmatch(digest) is None
            or ref in refs
        ):
            return None
        refs.add(ref)
    return sources


def _json_data_valida(value: object, *, depth: int = 0) -> bool:
    if depth > 10:
        return False
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not (-float("inf") < value < float("inf")):
            return False
        return not isinstance(value, str) or len(value) <= 20_000
    if isinstance(value, list):
        return len(value) <= 1_000 and all(
            _json_data_valida(item, depth=depth + 1) for item in value
        )
    if isinstance(value, dict):
        return len(value) <= 1_000 and all(
            isinstance(key, str)
            and 0 < len(key) <= 128
            and _json_data_valida(item, depth=depth + 1)
            for key, item in value.items()
        )
    return False


def _sha256_json(value: object) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
