"""Emite el manifest de reconstrucción de un corte de evidencia.

Responde una sola pregunta: con qué versión del agente y con qué configuración
se produjo la evidencia de este corte. Ya no mantiene su propia lista de
fuentes: referencia la **versión** y el **hash del manifest de versión**
(`manifest-version.json`, #92), que cubre código, prompts, políticas,
contratos, migraciones, `uv.lock`, `pyproject.toml`, `scripts/` y `systemd/`.
Lo que agrega es lo propio del corte: la configuración del adapter y la
referencia Git.

No copia borradores, prompts renderizados ni datos de actividades: el hash del
manifest alcanza para verificar que la versión no cambió, y copiar el
contenido sería arrastrar material que la evidencia no necesita.

Uso:
    uv run python scripts/manifest_corte.py --corte 2026-09-08 \\
        > evidencias/manifest-corte-2026-09-08.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.manifest_version import (  # noqa: E402
    MANIFEST_VERSION_NOMBRE,
    IntegridadError,
    leer_manifest,
    sha256_archivo,
)
from agente1.ollama import (  # noqa: E402
    DEFAULT_OLLAMA_NUM_PREDICT,
    DEFAULT_OLLAMA_TIMEOUT_S,
    MAX_OLLAMA_NUM_PREDICT,
    MIN_OLLAMA_NUM_PREDICT,
)
from agente1.posts import CONTRATO_SALIDA_ESTRUCTURADA_V3  # noqa: E402
from agente1.presupuesto import (  # noqa: E402
    CHARS_POR_TOKEN_MENOS_FAVORABLE,
    presupuesto_minimo_num_predict,
)
from agente1.procesamiento import PROMPT_VERSION  # noqa: E402


def _git(*argumentos: str) -> str | None:
    try:
        salida = subprocess.run(
            ["git", *argumentos],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return salida.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corte", required=True, help="Fecha del corte, AAAA-MM-DD.")
    args = parser.parse_args()

    ruta_manifest = ROOT / MANIFEST_VERSION_NOMBRE
    try:
        manifest_version = leer_manifest(ruta_manifest)
    except IntegridadError as exc:
        print(
            f"manifest de versión no utilizable ({exc.code}): {ruta_manifest}",
            file=sys.stderr,
        )
        return 1

    manifest = {
        "corte": args.corte,
        "alcance": "HU-010 y HU-011 en entorno local controlado con datos sintéticos",
        # El commit es una referencia de contexto, no la fuente de verdad del
        # manifest: los hashes valen por si solos, y este archivo se genera
        # antes del commit que lo va a contener.
        "commit_padre": _git("rev-parse", "HEAD"),
        # La versión y su manifest reemplazan la lista de fuentes que este
        # script mantenía congelada: lo controlado lo cubre el manifest de
        # versión, y su hash ata el corte a una versión exacta.
        "version": manifest_version["version"],
        "manifest_version_sha256": sha256_archivo(ruta_manifest),
        "configuracion": {
            "prompt_version_gacetilla": PROMPT_VERSION,
            "ollama_num_predict_default": DEFAULT_OLLAMA_NUM_PREDICT,
            "ollama_num_predict_rango": [
                MIN_OLLAMA_NUM_PREDICT,
                MAX_OLLAMA_NUM_PREDICT,
            ],
            "ollama_timeout_s_default": DEFAULT_OLLAMA_TIMEOUT_S,
            "presupuesto_minimo_contrato_v3": presupuesto_minimo_num_predict(
                CONTRATO_SALIDA_ESTRUCTURADA_V3
            ),
            "chars_por_token_menos_favorable": CHARS_POR_TOKEN_MENOS_FAVORABLE,
        },
        "no_incluye": [
            "borradores generados",
            "prompts renderizados",
            "datos de actividades",
            "credenciales o identificadores institucionales",
        ],
        "no_acredita": [
            "validación de la SEU",
            "revisión humana registrada",
            "operación live de Google Workspace",
            "Gate G2",
            "TRL 3",
        ],
    }
    json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
