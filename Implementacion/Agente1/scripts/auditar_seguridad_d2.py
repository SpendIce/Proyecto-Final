#!/usr/bin/env python3
"""Audita offline un manifest sintético D2/D3 y emite un reporte redactado."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.auditoria_d2 import auditar_manifest, serializar_reporte  # noqa: E402


MAX_MANIFEST_BYTES = 1_048_576


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audita un manifest offline_fake. No ejecuta red ni acepta credenciales."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--reporte", required=True, type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    report_path = args.reporte.resolve()
    if manifest_path == report_path:
        parser.error("manifest y reporte deben ser archivos distintos")

    try:
        if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        manifest = None

    reporte = auditar_manifest(manifest)
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        temporal = report_path.with_name(f".{report_path.name}.tmp")
        temporal.write_text(serializar_reporte(reporte), encoding="utf-8")
        temporal.replace(report_path)
    except OSError:
        print(json.dumps({"status": "WRITE_ERROR"}), file=sys.stderr)
        return 2

    print(json.dumps({"status": reporte["status"]}))
    if reporte["status"] == "PASS":
        return 0
    if reporte["status"] == "FAIL":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
