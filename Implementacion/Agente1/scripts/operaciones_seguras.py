#!/usr/bin/env python3
"""CLI offline para planes y reportes operativos sanitizados del Agente 1."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.operaciones_seguras import (
    ContratoOperativoInvalido,
    consolidar_manifests,
    evaluar_health,
    planificar_reconciliacion,
    planificar_retencion,
)


MAX_INPUT_BYTES = 1_048_576


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Opera sólo sobre manifests sanitizados; nunca modifica recursos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health")
    health.add_argument("input", type=Path)
    health.add_argument("--live", action="store_true")

    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("input", type=Path)

    consolidate = subparsers.add_parser("consolidate")
    consolidate.add_argument("input", type=Path)

    retention = subparsers.add_parser("retention")
    retention.add_argument("input", type=Path)
    retention.add_argument("--base-dir", type=Path, required=True)
    retention.add_argument("--now", required=True)
    retention.add_argument("--retention-days", type=int, required=True)

    args = parser.parse_args(argv)
    try:
        if args.input.is_symlink() or args.input.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if args.command == "health":
            if args.live:
                raise ContratoOperativoInvalido("health_live_probe_adapter_unavailable")
            report = evaluar_health(payload)
        elif args.command == "reconcile":
            report = planificar_reconciliacion(payload)
        elif args.command == "consolidate":
            report = consolidar_manifests(payload)
        else:
            report = planificar_retencion(
                args.base_dir,
                payload,
                now=datetime.fromisoformat(args.now.replace("Z", "+00:00")),
                retention_days=args.retention_days,
            )
    except (ContratoOperativoInvalido, json.JSONDecodeError, OSError, ValueError) as exc:
        code = (
            exc.code
            if isinstance(exc, ContratoOperativoInvalido)
            else "operations_input_invalid"
        )
        print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
        return 2

    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
