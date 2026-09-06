#!/usr/bin/env python3
"""Runner de línea de comandos del flujo Sheets → Agente 1 → Docs.

Es el único ejecutable que puede salir a Google Workspace, y sólo si se lo pide
de forma explícita: sin `--live` y `--confirmar-escritura` corre íntegramente
con fuente y destino en memoria (`FuenteMemoria` / `DestinoMemoria`), que no
tocan red ni disco remoto. Toda la evidencia disponible al 26/08/2026 se
produjo por ese camino offline.

En modo live la configuración sale del entorno (`AGENTE1_WORKSPACE_*`) y el
token de su propia variable; nada de eso se pasa por argv, porque los
argumentos quedan visibles en la lista de procesos y en el historial del shell.

Cada corrida deja un manifest sanitizado bajo `manifests/`, incluso cuando no
genera nada: una ejecución bloqueada o duplicada también es evidencia.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from agente1.ollama import OllamaGenerator
from agente1.posts import CONTRATO_SALIDA_ESTRUCTURADA
from agente1.procesamiento import FakeGenerator
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
    cargar_configuracion_workspace,
)
from agente1.workspace_e2e import (
    DestinoMemoria,
    FuenteMemoria,
    RegistroIdempotenciaArchivo,
    RunnerWorkspaceError,
    crear_dependencias_workspace_live,
    ejecutar_workspace_e2e,
)


ROOT = Path(__file__).resolve().parents[1]
FILA_OFFLINE = {
    "id_solicitud": "SYN-001",
    "titulo": "Taller sintético de vinculación",
    "descripcion": "Actividad ficticia para probar el flujo.",
    "fecha": "2026-08-05",
    "publico": "Comunidad universitaria ficticia",
    "organiza": "Equipo de prueba",
    "contacto": "pruebas@example.invalid",
    "fuente": "Dataset sintético versionado",
    "lugar": "Aula de prueba",
}


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _respuesta_offline(tipo: str, canal: str | None) -> str:
    if tipo == "gacetilla":
        path = ROOT / "golden" / "SYN-001.md"
        marcador = "# BORRADOR — NO PUBLICAR\n\n"
        contenido = path.read_text(encoding="utf-8")
        if not contenido.startswith(marcador):
            raise RunnerWorkspaceError("runner_offline_fixture_invalid")
        return contenido.removeprefix(marcador).strip()
    fixture_path = ROOT / "data" / "workspace_e2e_creativity_v2.synthetic.json"
    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        creatividad = fixture[canal]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        raise RunnerWorkspaceError("runner_offline_fixture_invalid") from None
    if fixture.get("schema_version") != "workspace_e2e_creativity_fixture_v2":
        raise RunnerWorkspaceError("runner_offline_fixture_invalid")
    return json.dumps(creatividad, ensure_ascii=False, sort_keys=True)


def _crear_generator_live(*, tipo: str, modelo: str) -> OllamaGenerator:
    return OllamaGenerator(
        modelo=modelo,
        format_schema=CONTRATO_SALIDA_ESTRUCTURADA if tipo == "post" else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Runner Sheets→HU-010/HU-011→Drive. Por defecto sólo usa fakes offline; "
            "live requiere doble opt-in explícito."
        )
    )
    parser.add_argument("--tipo", choices=("gacetilla", "post"), default="gacetilla")
    parser.add_argument("--canal", choices=("instagram", "linkedin"))
    parser.add_argument("--id-solicitud", default="SYN-001")
    parser.add_argument("--salida", type=Path, default=ROOT / "tmp" / "workspace-e2e")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-write-workspace", action="store_true")
    parser.add_argument("--modelo", default="llama3.2:3b")
    try:
        args = parser.parse_args(argv)
        if args.tipo == "post" and args.canal is None:
            raise RunnerWorkspaceError("runner_channel_required")
        if args.tipo == "gacetilla" and args.canal is not None:
            raise RunnerWorkspaceError("runner_channel_not_allowed")
        if not args.live and args.confirm_write_workspace:
            raise RunnerWorkspaceError("runner_live_not_enabled")

        if args.live:
            config = cargar_configuracion_workspace()
            fuente, destino = crear_dependencias_workspace_live(
                habilitar_live=True,
                confirmar_escritura=args.confirm_write_workspace,
                config=config,
                token_provider=TokenEntornoProvider(),
            )
            generator = _crear_generator_live(tipo=args.tipo, modelo=args.modelo)
            ambiente = config.ambiente
        else:
            if args.id_solicitud != "SYN-001":
                raise RunnerWorkspaceError("runner_offline_fixture_not_found")
            fuente = FuenteMemoria(FILA_OFFLINE)
            destino = DestinoMemoria()
            generator = FakeGenerator(_respuesta_offline(args.tipo, args.canal))
            ambiente = "OFFLINE"

        resultado = ejecutar_workspace_e2e(
            tipo=args.tipo,
            canal=args.canal,
            id_solicitud=args.id_solicitud,
            fuente=fuente,
            generator=generator,
            destino=destino,
            directorio_salida=args.salida,
            registro=RegistroIdempotenciaArchivo(args.salida / "idempotency"),
            ambiente=ambiente,
            live=args.live,
        )
    except ConfiguracionWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except RunnerWorkspaceError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3

    _emitir(
        {
            "correlation_id": resultado.correlation_id,
            "duplicada": resultado.duplicada,
            "estado": resultado.estado,
            "modo": "live_write_opt_in" if args.live else "offline_fake",
            "reconciliation_required": resultado.reconciliation_ref_hash is not None,
        }
    )
    return 0 if resultado.estado in {"PENDIENTE_VALIDACION", "DUPLICADA"} else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
