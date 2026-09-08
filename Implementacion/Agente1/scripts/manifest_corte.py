"""Emite el manifest de reconstrucción de un corte de evidencia.

Responde una sola pregunta: con qué fuentes y con qué configuración se produjo
la evidencia de este corte. Registra hashes de las entradas versionadas —
dataset sintético, prompts, contratos, política de redes y módulos que rinden
la salida — más la configuración por defecto del adapter y la referencia Git.

No copia borradores, prompts renderizados ni datos de actividades: un hash
alcanza para verificar que una fuente no cambió, y copiar el contenido sería
arrastrar material que la evidencia no necesita.

Uso:
    uv run python scripts/manifest_corte.py --corte 2026-09-08 \\
        > evidencias/manifest-corte-2026-09-08.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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

# Entradas versionadas de las que depende cualquier corrida de HU-010 y HU-011.
# Si alguna cambia, el corte deja de ser el mismo aunque el resultado se parezca.
FUENTES = (
    "data/actividades_sinteticas.csv",
    "src/agente1/contracts/gacetilla_input_v1.schema.json",
    "src/agente1/contracts/post_input_v1.schema.json",
    "src/agente1/contracts/post_creative_output_v2.schema.json",
    "src/agente1/contracts/post_creative_output_v3.schema.json",
    "src/agente1/politicas/politica_redes_provisional_v1.json",
    "src/agente1/prompts/gacetilla_v3.txt",
    "src/agente1/prompts/post_instagram_structured_v3.txt",
    "src/agente1/prompts/post_linkedin_structured_v3.txt",
    "src/agente1/procesamiento.py",
    "src/agente1/posts.py",
    "src/agente1/politica_redes.py",
    "src/agente1/presupuesto.py",
    "src/agente1/ollama.py",
)


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


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

    faltantes = [ruta for ruta in FUENTES if not (ROOT / ruta).is_file()]
    if faltantes:
        print(f"faltan fuentes declaradas: {faltantes}", file=sys.stderr)
        return 1

    manifest = {
        "corte": args.corte,
        "alcance": "HU-010 y HU-011 en entorno local controlado con datos sintéticos",
        # El commit es una referencia de contexto, no la fuente de verdad del
        # manifest: los hashes valen por si solos, y este archivo se genera
        # antes del commit que lo va a contener.
        "commit_padre": _git("rev-parse", "HEAD"),
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
        "fuentes_sha256": {ruta: _sha256(ROOT / ruta) for ruta in FUENTES},
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
