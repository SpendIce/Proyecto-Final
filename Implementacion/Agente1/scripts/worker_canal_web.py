#!/usr/bin/env python3
"""Worker de generación del canal web (issue #149, ADR 0016).

Toma las ejecuciones reservables de la base —`SELECT ... FOR UPDATE SKIP
LOCKED` con plazo—, corre el pipeline vigente por tipo y deja el estado
durable. Las ejecuciones `clase='ajuste'` no generan desde el pedido
original: reescriben la revisión vigente con la indicación registrada y
crean la revisión nueva sobre el mismo Doc. Corre fuera de la respuesta
HTTP, un trabajo por ciclo; ante una caída, la reserva vence y otra corrida
retoma sin duplicar el Doc.

Entorno:

- `AGENTE1_POSTGRES_DSN` (obligatoria): DSN de la base; en producción
  conecta como `agente1_app`.
- `AGENTE1_WORKER_ID`: nombre de la reserva (default `worker-1`).

Uso:

    python scripts/worker_canal_web.py --tabla data/actividades_sinteticas.csv \
        --salida salida --generador-salida "texto fijo" [--una-vez]

`--generador-salida` es el modo offline determinista (FakeGenerator); sin
él se exige `--ollama-model` para el modelo real del stack. El destino del
Doc se inyecta con una opción explícita:

- `--destino-fake` usa el destino en memoria con marca de solicitud
  (desarrollo y evidencia).
- `--destino-docs` usa `GoogleDocsDestinoPorMarca` sobre Drive real
  (#153): exige la config `AGENTE1_WORKSPACE_*` completa y falla cerrado
  si falta — nunca cae al fake en silencio.

Con `AGENTE1_WEB_DOCS_COMPARTIR=si` el worker da `writer` al correo de
quien pidió (resuelto contra `AGENTE1_PADRON_ROLES_CSV`) al generar el Doc
—lo cree o lo reutilice—;
sin la variable no toca permisos y el Doc queda accesible por la carpeta.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _invalida(code: str) -> int:
    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Worker de generación del canal web (ADR 0016)."
    )
    parser.add_argument("--tabla", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--generador-salida", default=None)
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--destino-fake", action="store_true")
    parser.add_argument("--destino-docs", action="store_true")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--plazo-segundos", type=int, default=300)
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--una-vez", action="store_true")
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    if not dsn:
        return _invalida("worker_dsn_ausente")
    if args.destino_fake == args.destino_docs:
        return _invalida("worker_destino_no_declarado")

    from agente1.fuentes import CsvFuenteSolicitudes
    from agente1.procesamiento import FakeGenerator
    from agente1.web.persistencia import RepositorioWeb, conectar
    from agente1.web.worker import DestinoPorMarcaMemoria, correr_una_vez

    if args.generador_salida is not None:
        generator = FakeGenerator(args.generador_salida)
        generator_ajuste = generator
    elif args.ollama_model:
        from agente1.ollama import OllamaGenerator

        # Sin thinking: gemma4 gasta el `num_predict` pensando y la
        # respuesta llega vacía (mismo arreglo que el scheduler en 0.5.3).
        generator = OllamaGenerator(modelo=args.ollama_model, think=False)
        # El ajuste reescribe la pieza entera (sin el pie): con el tope de
        # la generación el modelo puede cortarla. Va con el techo de tokens
        # y de tiempo; `num_predict` es un tope, no alarga una salida corta.
        from agente1.ollama import MAX_OLLAMA_NUM_PREDICT, MAX_OLLAMA_TIMEOUT_S

        generator_ajuste = OllamaGenerator(
            modelo=args.ollama_model,
            think=False,
            num_predict=MAX_OLLAMA_NUM_PREDICT,
            timeout_s=MAX_OLLAMA_TIMEOUT_S,
        )
    else:
        return _invalida("worker_generador_no_declarado")

    fuente = CsvFuenteSolicitudes(args.tabla)
    repositorio = RepositorioWeb(functools.partial(conectar, dsn))
    compartir = entorno.get("AGENTE1_WEB_DOCS_COMPARTIR", "").lower() == "si"
    if args.destino_docs:
        try:
            from agente1.workspace_auth import construir_token_provider
            from agente1.workspace_config import (
                ConfiguracionWorkspaceError,
                cargar_configuracion_workspace,
            )

            config_ws = cargar_configuracion_workspace(entorno)
            token_provider = construir_token_provider(
                entorno,
                timeout_s=config_ws.timeout_s,
                directorio_auditoria=Path(
                    entorno.get("AGENTE1_ESTADO") or "."
                ),
            )
        except ConfiguracionWorkspaceError:
            return _invalida("worker_workspace_config_invalid")
        from agente1.google_workspace import GoogleDocsDestinoPorMarca

        destino = GoogleDocsDestinoPorMarca(
            plantilla_id=config_ws.template_id,
            carpeta_id=config_ws.folder_id,
            token_provider=token_provider,
            timeout_s=config_ws.timeout_s,
        )
    else:
        destino = DestinoPorMarcaMemoria()
    correo_para_hash = None
    if compartir:
        padron_csv = entorno.get("AGENTE1_PADRON_ROLES_CSV")
        if not padron_csv:
            return _invalida("worker_padron_ausente")
        try:
            from agente1.canal_form import cargar_padron_roles_csv

            padron = cargar_padron_roles_csv(Path(padron_csv))
        except Exception:
            return _invalida("worker_padron_invalid")
        correo_para_hash = padron.correo_para_hash
    worker_id = (
        args.worker_id
        or entorno.get("AGENTE1_WORKER_ID")
        or "worker-1"
    )
    args.salida.mkdir(parents=True, exist_ok=True)

    while True:
        trabajo = correr_una_vez(
            repositorio=repositorio,
            worker_id=worker_id,
            fuente=fuente,
            generator=generator,
            generator_ajuste=generator_ajuste,
            directorio_salida=args.salida,
            destino=destino,
            correo_para_hash=correo_para_hash,
            plazo_segundos=args.plazo_segundos,
        )
        if args.una_vez:
            print(
                json.dumps(
                    {
                        "status": "OK",
                        "trabajo": trabajo.id_ejecucion if trabajo else None,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if trabajo is None:
            time.sleep(args.intervalo)


if __name__ == "__main__":
    sys.exit(main())
