#!/usr/bin/env python3
"""Prepara un manifest local para una sesión de validación humana de la SEU.

El comando sólo lee artefactos versionados y escribe referencias, tamaños y
hashes. No publica, envía ni copia el contenido de los borradores o del acta.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


DECISIONES = {
    "PENDIENTE",
    "APROBADO_COMO_BORRADOR",
    "REQUIERE_AJUSTES",
    "RECHAZADO",
}
DECISIONES_CIERRE = DECISIONES - {"PENDIENTE"}
CRITERIOS_REQUERIDOS = {
    "precision",
    "tono",
    "ajuste_canal",
    "gramatica",
    "longitud",
    "alucinaciones",
}
CONTROLES_REQUERIDOS = {
    "hechos_contrastados",
    "sin_claim_publicacion",
    "sin_datos_innecesarios",
}
IDS_MUESTRA_REQUERIDOS = {f"M-{numero:03d}" for numero in range(1, 10)}
CLAVES_MUESTRA_REQUERIDAS = {
    "id",
    "decision",
    "puntajes",
    "controles_obligatorios",
    "observaciones",
}
PATRON_ID_REFERENCIA = re.compile(r"REF-[0-9]{3}\Z")


class ActaInvalida(ValueError):
    """Indica que un acta pretende cerrar la revisión sin evidencia mínima."""


def _texto_no_vacio(acta: dict[str, Any], campo: str) -> bool:
    return isinstance(acta.get(campo), str) and bool(acta[campo].strip())


def _validar_fecha_con_zona(valor: Any) -> None:
    if not isinstance(valor, str):
        raise ActaInvalida("fecha_hora debe usar ISO 8601 con zona horaria")
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError as error:
        raise ActaInvalida("fecha_hora debe usar ISO 8601 con zona horaria") from error
    if fecha.tzinfo is None or fecha.utcoffset() is None:
        raise ActaInvalida("fecha_hora debe usar ISO 8601 con zona horaria")


def _validar_muestra(muestra: Any) -> None:
    if not isinstance(muestra, dict):
        raise ActaInvalida("cada muestra debe ser un objeto")
    if not CLAVES_MUESTRA_REQUERIDAS.issubset(muestra):
        raise ActaInvalida("faltan campos requeridos en una muestra")
    if (
        not isinstance(muestra["id"], str)
        or muestra["id"] not in IDS_MUESTRA_REQUERIDOS
    ):
        raise ActaInvalida("id de muestra no reconocido")
    if (
        not isinstance(muestra["decision"], str)
        or muestra["decision"] not in DECISIONES_CIERRE
    ):
        raise ActaInvalida("decisión de muestra no reconocida o pendiente")

    puntajes = muestra["puntajes"]
    if not isinstance(puntajes, dict) or set(puntajes) != CRITERIOS_REQUERIDOS:
        raise ActaInvalida("faltan criterios requeridos en una muestra")
    if any(type(valor) is not int or not 1 <= valor <= 4 for valor in puntajes.values()):
        raise ActaInvalida("los puntajes deben ser enteros entre 1 y 4")

    controles = muestra["controles_obligatorios"]
    if not isinstance(controles, dict) or set(controles) != CONTROLES_REQUERIDOS:
        raise ActaInvalida("faltan controles obligatorios en una muestra")
    if any(type(valor) is not bool for valor in controles.values()):
        raise ActaInvalida("los controles obligatorios deben ser booleanos")

    observaciones = muestra["observaciones"]
    tiene_observacion = isinstance(observaciones, str) and bool(observaciones.strip())
    if any(valor < 3 for valor in puntajes.values()) and not tiene_observacion:
        raise ActaInvalida("un puntaje menor que 3 exige observación")
    if muestra["decision"] in {"REQUIERE_AJUSTES", "RECHAZADO"} and not tiene_observacion:
        raise ActaInvalida("un ajuste o rechazo exige observación")

    if muestra["decision"] == "APROBADO_COMO_BORRADOR":
        if any(valor < 3 for valor in puntajes.values()):
            raise ActaInvalida("una aprobación exige puntaje mínimo 3")
        if any(valor is not True for valor in controles.values()):
            raise ActaInvalida("una aprobación exige todos los controles en true")


def validar_acta(acta: dict[str, Any]) -> None:
    """Valida el gate documental sin atribuir una decisión a la SEU."""

    if not isinstance(acta, dict):
        raise ActaInvalida("el acta debe ser un objeto")
    if acta.get("schema_version") != "acta_validacion_seu_v1":
        raise ActaInvalida("schema_version no soportada")

    decision = acta.get("decision")
    if not isinstance(decision, str) or decision not in DECISIONES:
        raise ActaInvalida("decision no reconocida")

    if decision == "PENDIENTE":
        if acta.get("estado") != "PENDIENTE":
            raise ActaInvalida("un acta sin decisión debe permanecer PENDIENTE")
        return

    for campo in (
        "persona_revisora",
        "rol_area",
        "fecha_hora",
        "referencia_evidencia",
    ):
        if not _texto_no_vacio(acta, campo):
            raise ActaInvalida(f"falta el campo mínimo {campo}")

    if acta.get("estado") != "CERRADA":
        raise ActaInvalida("una decisión registrada requiere estado CERRADA")
    _validar_fecha_con_zona(acta["fecha_hora"])

    if decision in {"REQUIERE_AJUSTES", "RECHAZADO"} and not _texto_no_vacio(
        acta, "motivo_decision"
    ):
        raise ActaInvalida("un ajuste o rechazo exige motivo_decision")

    muestras = acta.get("muestras")
    if not isinstance(muestras, list) or not muestras:
        raise ActaInvalida("una decisión cerrada requiere muestras evaluadas")

    for muestra in muestras:
        _validar_muestra(muestra)

    ids_muestras = {muestra["id"] for muestra in muestras}
    if ids_muestras != IDS_MUESTRA_REQUERIDOS or len(muestras) != len(
        IDS_MUESTRA_REQUERIDOS
    ):
        raise ActaInvalida("la decisión requiere las nueve muestras versionadas")

    decisiones_muestras = [muestra["decision"] for muestra in muestras]
    if decision == "APROBADO_COMO_BORRADOR":
        if any(valor != "APROBADO_COMO_BORRADOR" for valor in decisiones_muestras):
            raise ActaInvalida("toda muestra debe aprobarse como borrador")
    elif decision == "REQUIERE_AJUSTES":
        if "REQUIERE_AJUSTES" not in decisiones_muestras or "RECHAZADO" in decisiones_muestras:
            raise ActaInvalida("la decisión global no coincide con las muestras")
    elif "RECHAZADO" not in decisiones_muestras:
        raise ActaInvalida("la decisión global no coincide con las muestras")


def _resolver_dentro_del_repo(repo_root: Path, referencia: str) -> Path:
    root = repo_root.resolve()
    path = (root / referencia).resolve()
    if not path.is_relative_to(root):
        raise ValueError("referencia fuera del repositorio")
    if not path.is_file():
        raise FileNotFoundError("referencia inexistente")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for bloque in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def preparar_manifest(
    repo_root: Path,
    referencias: Iterable[dict[str, str]],
    acta_path: Path,
) -> dict[str, Any]:
    """Devuelve trazabilidad opaca; no incorpora contenido ni identidad humana."""

    root = repo_root.resolve()
    acta_resuelta = acta_path.resolve()
    if not acta_resuelta.is_relative_to(root):
        raise ValueError("el acta está fuera del repositorio")
    acta = json.loads(acta_resuelta.read_text(encoding="utf-8"))
    validar_acta(acta)

    items = []
    ids_vistos: set[str] = set()
    for referencia in referencias:
        if not isinstance(referencia, dict) or set(referencia) != {"id", "path"}:
            raise ValueError("cada referencia requiere únicamente id y path")
        referencia_id = referencia["id"]
        if not isinstance(referencia_id, str) or not PATRON_ID_REFERENCIA.fullmatch(
            referencia_id
        ):
            raise ValueError("cada referencia requiere un identificador opaco REF-NNN")
        if referencia_id in ids_vistos:
            raise ValueError(f"identificador de referencia duplicado: {referencia_id}")
        ids_vistos.add(referencia_id)
        referencia_path = referencia["path"]
        if not isinstance(referencia_path, str):
            raise ValueError("path de referencia inválido")
        path = _resolver_dentro_del_repo(root, referencia_path)
        items.append(
            {
                "id": referencia_id,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )

    return {
        "schema_version": "manifest_validacion_seu_v1",
        "estado": acta["estado"],
        "decision": acta["decision"],
        "trl3_acreditado": False,
        "publicacion_o_envio_ejecutado": False,
        "acta": {
            "id": "ACTA-VALIDACION-SEU",
            "sha256": _sha256(acta_resuelta),
            "bytes": acta_resuelta.stat().st_size,
        },
        "referencias": items,
    }


def _parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[3]
    default_package = default_root / "Documentos" / "PoC" / "Validacion-SEU"
    parser = argparse.ArgumentParser(
        description="Recopila hashes para validación SEU sin copiar contenido ni PII."
    )
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument(
        "--catalogo",
        type=Path,
        default=default_package / "referencias.json",
    )
    parser.add_argument(
        "--acta",
        type=Path,
        default=default_package / "acta-validacion.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_package / "manifest-referencias.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    catalogo = json.loads(args.catalogo.read_text(encoding="utf-8"))
    manifest = preparar_manifest(args.repo_root, catalogo["referencias"], args.acta)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "Manifest preparado: "
        f"estado={manifest['estado']} referencias={len(manifest['referencias'])} "
        "publicación/envío=no"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
