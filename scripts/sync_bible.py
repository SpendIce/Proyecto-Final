#!/usr/bin/env python3
"""Sincroniza la bible `Contenido/bible/Procesos y Agentes.md` con la última
versión exportada del Google Doc fuente.

Fuentes posibles (en orden de prioridad):
  --src <path>    Markdown ya exportado (el .md que baja Nacho del Doc)
  --doc-id <id>   Baja el Google Doc directamente con el export nativo
                  `export?format=md` (requiere que el doc sea link-shared)
  (default)       Auto-detecta el "Procesos y Agentes*.md" más nuevo en ~/Downloads

Modo polling:
  --doc-id <id> --check   Descarga `export?format=txt` (probe liviano), compara
                          el hash contra ~/.cache/bible-watch/<id>.hash y solo
                          sincroniza/notifica si el documento cambió.

Qué hace:
  1. Extrae imágenes base64 inline a Contenido/bible/assets/procesos-y-agentes/
     y reapunta las referencias (convención del repo).
  2. Escribe la nueva versión sobre la bible.
  3. Genera diff contra HEAD (git) y clasifica hunks que afectan al Agente 1.
  4. Imprime resumen, guarda reporte en notas/bible-sync-<fecha>.md y manda
     notify-send si hay cambios.
"""

import argparse
import base64
import difflib
import hashlib
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BIBLE = REPO / "Contenido/bible/Procesos y Agentes.md"
ASSETS = REPO / "Contenido/bible/assets/procesos-y-agentes"
DOWNLOADS = Path.home() / "Downloads"
NOTES = REPO / "notas"

# Patrones que marcan un hunk como relevante para el Agente 1
A1_PATTERNS = re.compile(
    r"HU-01[0-9]|HU-016|HU-017|Agente 1|Extensi[oó]n ?Bot|ExtensionBot|"
    r"[ÉE]PICA E2|EPIC E2|RGC|Coordinador de Extensi[oó]n|"
    r"Proceso [3456]\b|\bP[3456]\b",
    re.IGNORECASE,
)

IMG_DEF = re.compile(
    r"^\[(image\d+)\]:\s*<data:image/(png|jpe?g);base64,([A-Za-z0-9+/=\s]+?)>\s*$",
    re.M,
)


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def fetch(url: str, dest: Path, timeout: int = 60) -> bool:
    r = subprocess.run(
        ["curl", "-sfL", "--max-time", str(timeout), url, "-o", str(dest)],
        capture_output=True,
    )
    return r.returncode == 0 and dest.stat().st_size > 100


def resolve_source(args) -> tuple[Path, str]:
    if args.src:
        p = Path(args.src).expanduser()
        return (p if p.is_file() else die(f"no existe {p}")), "archivo local"
    if args.doc_id:
        md = Path(tempfile.mkdtemp(prefix="bible-export-")) / "doc.md"
        url = f"https://docs.google.com/document/d/{args.doc_id}/export?format=md"
        if not fetch(url, md):
            die("export falló (¿el doc es link-shared? ¿hay conexión?)")
        return md, f"export doc-id {args.doc_id}"
    cands = sorted(
        DOWNLOADS.glob("Procesos y Agentes*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cands:
        die("no se encontró 'Procesos y Agentes*.md' en ~/Downloads")
    return cands[0], f"auto-detectado ({cands[0].name})"


def check_changed(doc_id: str) -> bool:
    """Probe liviano con format=txt. True si el doc cambió o no hay baseline."""
    state = Path.home() / ".cache" / "bible-watch"
    state.mkdir(parents=True, exist_ok=True)
    hashfile = state / f"{doc_id}.hash"
    probe = Path(tempfile.mkdtemp(prefix="bible-probe-")) / "doc.txt"
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    if not fetch(url, probe, timeout=30):
        print("warning: probe falló, se omite este ciclo", file=sys.stderr)
        return False
    h = hashlib.md5(probe.read_bytes()).hexdigest()
    prev = hashfile.read_text().strip() if hashfile.exists() else ""
    if h == prev:
        return False
    hashfile.write_text(h)
    return True


def extract_images(text: str) -> str:
    ASSETS.mkdir(parents=True, exist_ok=True)

    def repl(m):
        name, ext, b64 = m.groups()
        suffix = "png" if ext == "png" else "jpg"
        (ASSETS / f"{name}.{suffix}").write_bytes(
            base64.b64decode(re.sub(r"\s", "", b64))
        )
        return f"[{name}]: assets/procesos-y-agentes/{name}.{suffix}"

    return IMG_DEF.sub(repl, text)


def baseline() -> list[str]:
    r = subprocess.run(
        ["git", "show", f"HEAD:{BIBLE.relative_to(REPO)}"],
        capture_output=True, text=True, cwd=REPO,
    )
    if r.returncode == 0:
        return r.stdout.splitlines(keepends=True)
    return BIBLE.read_text(encoding="utf-8").splitlines(keepends=True)


def hunks(diff_lines: list[str]) -> list[list[str]]:
    hs, cur = [], []
    for ln in diff_lines:
        if ln.startswith("@@"):
            if cur:
                hs.append(cur)
            cur = [ln]
        elif cur:
            cur.append(ln)
    if cur:
        hs.append(cur)
    return hs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help="path al .md exportado")
    ap.add_argument("--doc-id", help="ID del Google Doc (requiere link-shared)")
    ap.add_argument("--check", action="store_true",
                    help="modo polling: solo sincroniza si el doc cambió (requiere --doc-id)")
    ap.add_argument("--quiet", action="store_true", help="sin notify-send")
    args = ap.parse_args()

    if args.check:
        if not args.doc_id:
            die("--check requiere --doc-id")
        if not check_changed(args.doc_id):
            sys.exit(0)
        print("documento modificado — sincronizando")

    src, origen = resolve_source(args)
    print(f"fuente: {origen}")

    raw = src.read_text(encoding="utf-8")
    new = extract_images(raw)

    old_lines = baseline()
    new_lines = new.splitlines(keepends=True)
    if "".join(old_lines) == "".join(new_lines):
        print("sin cambios respecto a HEAD — nada que hacer")
        return

    BIBLE.write_text(new, encoding="utf-8")
    print(f"bible actualizada: {BIBLE.relative_to(REPO)}")

    diff = list(difflib.unified_diff(old_lines, new_lines, n=3))
    hs = hunks(diff)
    a1 = [
        h for h in hs
        if A1_PATTERNS.search("".join(
            l for l in h if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))
        ))
    ]

    today = date.today().isoformat()
    NOTES.mkdir(exist_ok=True)
    report = NOTES / f"bible-sync-{today}.md"
    report.write_text(
        f"# Bible sync {today}\n\nFuente: {origen}\n\n"
        f"Hunks totales: {len(hs)} | Relevantes a Agente 1: {len(a1)}\n\n"
        + "".join(f"```diff\n{''.join(h)}```\n\n" for h in hs),
        encoding="utf-8",
    )

    print(f"\n{len(hs)} hunks modificados, {len(a1)} tocan al Agente 1:")
    for h in a1:
        changed = [l for l in h if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        preview = next((l.strip() for l in changed if l.strip()[1:].strip()), "")
        print(f"  {h[0].strip()}  {preview[:100]}")
    print(f"\nreporte completo: {report.relative_to(REPO)}")

    if not args.quiet:
        subprocess.run(
            ["notify-send", "Bible actualizada",
             f"{len(hs)} cambios, {len(a1)} afectan al Agente 1"],
            capture_output=True,
        )


if __name__ == "__main__":
    main()
