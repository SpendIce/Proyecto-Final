"""Los registros de auditoría dicen con qué versión del agente salieron (#93).

Cada versión del agente se instala con su manifest (`manifest-version.json`,
ADR 0010) y la auditoría de cada pieza tiene que poder rastrearse hasta la
versión exacta que la produjo: no sólo hasta el prompt o la política, sino
hasta la huella de todo lo controlado. Por eso todo registro de auditoría nuevo
lleva `version_agente` y `manifest_version_sha256` (la versión sale de
`pyproject.toml`, fuente única; el hash es el del manifest versionado).

La escritura vive en un solo lugar para que ningún log nuevo se olvide de la
identidad: los módulos llaman a `escribir_registro` en vez de repetir el
`mkdir` + `open` + `json.dumps`. El formato es JSONL, una línea por evento, con
las claves ordenadas para que los registros sean comparables e hasheables.

No pasa por acá la identidad del gate de arranque (`integridad-arranque.jsonl`,
#92), que ya asienta su propia `version` y el hash del manifest; ni los archivos
de estado (`decisiones-pendientes.jsonl`, los registros durables), que no son
auditoría.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .manifest_version import identidad_version_agente


def registro_con_identidad(
    registro: Mapping[str, object], *, raiz: Path | None = None
) -> dict[str, object]:
    """El registro con `version_agente` y el hash del manifest agregados.

    La identidad resuelta al escribir pisa cualquier valor previo del mismo
    campo: es la versión que está corriendo, no una copia que quedó vieja.
    """

    return {**dict(registro), **identidad_version_agente(raiz=raiz)}


def escribir_registro(
    path: Path, registro: Mapping[str, object], *, raiz: Path | None = None
) -> dict[str, object]:
    """Anexa una línea JSONL al registro de auditoría, con la identidad.

    Devuelve la línea efectivamente escrita. Crea el directorio si falta y no
    pisa líneas: la auditoría es append-only.
    """

    completo = registro_con_identidad(registro, raiz=raiz)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as archivo:
        archivo.write(json.dumps(completo, ensure_ascii=False, sort_keys=True))
        archivo.write("\n")
    return completo
