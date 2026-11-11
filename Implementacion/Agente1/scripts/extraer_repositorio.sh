#!/usr/bin/env bash
# extraer_repositorio.sh — Extrae del workspace académico un repositorio
# propio del Agente 1, con su historia (issue #80, ADR 0007).
#
# Se corre DESPUÉS del 18/11/2026, una sola vez, desde cualquier máquina con
# git y git-filter-repo. No toca el workspace: trabaja sobre un clon limpio
# que queda en <destino>, fuera del repo. No crea remotes ni empuja nada.
#
# Uso:
#   scripts/extraer_repositorio.sh <fuente> <destino> --reglas-privadas RUTA \
#       [--mailmap RUTA] [--rama main] [--sin-tests] [--sin-escaneo]
#
#   fuente   URL o ruta local del workspace (por ejemplo
#            https://github.com/SpendIce/Proyecto-Final.git o el checkout local).
#   destino  Directorio NUEVO: queda el repo extraído, listo para subir a su
#            cuenta definitiva. No debe existir.
#   --reglas-privadas   Archivo de redacciones con datos reales (obligatorio;
#            vive FUERA del repo — el workspace lo tiene en
#            .local-recovery/traspaso/extraccion-redacciones-privadas.txt).
#            El repo es público: una extracción sin redacciones completas no
#            puede salir, por eso el script no corre sin él.
#   --mailmap  Mailmap de autoría (por defecto: extraccion-mailmap.txt junto
#            a las reglas privadas). Reescribe autor/committer/tagger reales;
#            también vive fuera del repo.
#   --rama   Rama a extraer (por defecto: main).
#   --sin-tests   Saltea la suite (sólo para ensayos).
#   --sin-escaneo Saltea el escaneo de secretos (sólo para ensayos).
#
# Pasos:
#   1. Clon limpio de una sola rama en <destino>.
#   2. `git filter-repo`: conserva sólo las rutas del inventario, reubica
#      `Implementacion/Agente1/` en la raíz, aplica las redacciones
#      (privadas + genéricas) a TODA la historia (blobs y mensajes de
#      commit/tag) y anonimiza la autoría con la mailmap.
#      ATENCIÓN con los archivos de reglas: el formato de
#      --replace-text/--replace-message de filter-repo NO admite comentarios
#      ni líneas con '#': cada línea es una regla `literal:`/`regex:` con
#      `==>` para el reemplazo. Una línea '#' sola reemplazaría TODOS los '#'
#      de la historia. Documentar las reglas acá o en el inventario, nunca
#      dentro de los archivos de reglas.
#   3. Commit de reacondicionamiento sobre la punta: rutas internas a la
#      raíz nueva, `AGENTS.md`/`CLAUDE.md` que apuntan al manual de
#      operación, entrada en `CHANGELOG.md` y `manifest-version.json`
#      regenerado (los scripts retocados quedan controlados, ADR 0010).
#   4. Escaneo de secretos sobre TODA la historia extraída: gitleaks si está
#      instalado, si no el grep documentado de la sección ESCANEO, que además
#      busca el lado izquierdo de CADA regla privada. Un hallazgo frena el
#      proceso: hay que agregar la cadena a las reglas y volver a correr.
#   5. Informe: commits, tamaño, escaneo y, si se puede, la suite.
#
# Requisitos: git >= 2.36, git-filter-repo (`pipx install git-filter-repo`),
# python3 >= 3.11 (el manifest usa tomllib) y uv (sólo para la suite).
# gitleaks es opcional.

set -euo pipefail

RUTA_AGENTE="Implementacion/Agente1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGLAS_GENERICAS="${REGLAS_GENERICAS:-$SCRIPT_DIR/extraccion-redacciones.txt}"

RAMA="main"
CORRER_TESTS=1
CORRER_ESCANEO=1
REGLAS_PRIVADAS=""
MAILMAP=""
FUENTE=""
DESTINO=""

uso() {
    sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reglas-privadas) REGLAS_PRIVADAS="${2:?Falta la ruta de las reglas privadas}"; shift 2 ;;
        --mailmap) MAILMAP="${2:?Falta la ruta de la mailmap}"; shift 2 ;;
        --rama) RAMA="${2:?Falta el nombre de rama}"; shift 2 ;;
        --sin-tests) CORRER_TESTS=0; shift ;;
        --sin-escaneo) CORRER_ESCANEO=0; shift ;;
        -h|--help) uso 0 ;;
        -*) echo "Opción desconocida: $1" >&2; uso 1 ;;
        *)
            if [[ -z "$FUENTE" ]]; then FUENTE="$1"
            elif [[ -z "$DESTINO" ]]; then DESTINO="$1"
            else echo "Argumento de más: $1" >&2; uso 1
            fi
            shift ;;
    esac
done

[[ -n "$FUENTE" && -n "$DESTINO" ]] || uso 1
[[ -n "$REGLAS_PRIVADAS" ]] || {
    echo "Falta --reglas-privadas RUTA: sin las reglas con datos reales" >&2
    echo "la extracción no puede salir. Plantilla: scripts/extraccion-redacciones-privadas.ejemplo.txt" >&2
    exit 1
}
MAILMAP="${MAILMAP:-$(dirname "$REGLAS_PRIVADAS")/extraccion-mailmap.txt}"

[[ -f "$REGLAS_GENERICAS" ]] || { echo "Falta el archivo de reglas genéricas: $REGLAS_GENERICAS" >&2; exit 1; }
[[ -f "$REGLAS_PRIVADAS" ]] || { echo "Falta el archivo de reglas privadas: $REGLAS_PRIVADAS" >&2; exit 1; }
[[ -f "$MAILMAP" ]] || { echo "Falta la mailmap de autoría: $MAILMAP" >&2; exit 1; }
[[ ! -e "$DESTINO" ]] || { echo "El destino ya existe: $DESTINO (tiene que ser nuevo)" >&2; exit 1; }
command -v git >/dev/null || { echo "Falta git" >&2; exit 1; }
git filter-repo --version >/dev/null 2>&1 || {
    echo "Falta git-filter-repo: pipx install git-filter-repo" >&2; exit 1; }

# Los archivos privados no pueden vivir en un repo git: si la ruta queda
# dentro de un worktree y NO está ignorada, frena (riesgo de commit del
# archivo con los datos reales). Ignorada (p. ej. .local-recovery/) o fuera
# de todo worktree es la forma correcta.
en_repo_versionado() {
    local dir; dir="$(dirname "$1")"
    git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
        && ! git -C "$dir" check-ignore -q "$1" 2>/dev/null
}
for privado in "$REGLAS_PRIVADAS" "$MAILMAP"; do
    if en_repo_versionado "$privado"; then
        echo "ERROR: $privado está dentro de un repo git sin ignorar." >&2
        echo "       Movélo a .local-recovery/ u otra carpeta ignorada." >&2
        exit 1
    fi
done
grep -q '==>' "$REGLAS_PRIVADAS" || {
    echo "ERROR: $REGLAS_PRIVADAS no contiene ninguna regla ('==>')." >&2; exit 1; }

# Reglas combinadas: las privadas primero (sus literales concretos), después
# las genéricas. Temporales, fuera de cualquier repo; se borran al salir.
REGLAS_COMBINADAS="$(mktemp)"
EMAILS_PRIVADOS="$(mktemp)"
trap 'rm -f "$REGLAS_COMBINADAS" "$EMAILS_PRIVADOS"' EXIT
cat "$REGLAS_PRIVADAS" "$REGLAS_GENERICAS" > "$REGLAS_COMBINADAS"
# Correos "viejos" de la mailmap (todo lo que sigue al primer '>'), para que
# el email-callback los atrape aunque lleguen con formato raro (<<mail>>).
grep -v '^\s*#' "$MAILMAP" | sed 's/^[^>]*>//' \
    | grep -oE '<[^>]+>' | tr -d '<>' | sed 's/^ *//;s/ *$//' | sort -u \
    > "$EMAILS_PRIVADOS"
export AGENTE1_EXTRACCION_EMAILS="$EMAILS_PRIVADOS"

echo "==> 1/5 Clon limpio de '$FUENTE' (rama $RAMA) en $DESTINO"
git clone --quiet --single-branch --branch "$RAMA" "$FUENTE" "$DESTINO"
COMMITS_FUENTE="$(git -C "$DESTINO" rev-list --count HEAD)"

echo "==> 2/5 git filter-repo: rutas del inventario + redacciones + mailmap"
cd "$DESTINO"

# Las rutas que viajan, alineadas con docs/traspaso/inventario-extraccion-agente-1.md.
git filter-repo --force \
    --path "$RUTA_AGENTE/" \
    --path CONTEXT.md \
    --path docs/adr/ \
    --path docs/research/ \
    --path docs/seguridad/ \
    --path docs/traspaso/ \
    --path .github/pull_request_template.md \
    --path-glob '.github/workflows/agente1-*.yml' \
    --path Documentos/PlanDespliegue/ \
    --path Documentos/Reuniones/DSI-2026-10-13/ \
    --path Documentos/PoC/Corpus-FIE-Informa-Historico-2026-10-13.md \
    --path Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md \
    --path Documentos/PoC/Politica-Artefactos-Versionados-v1.md \
    --path Documentos/PoC/Diseno-HU-012-Control-Pagos-v1.md \
    --path Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22.md \
    --path Documentos/PoC/Registro-Actividades-Fuentes-Documentales-v1.md \
    --path Documentos/PoC/Nota-Solicitud-SEU-Agente-1-PPS-Juan-Ignacio-Gone.md \
    --path Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md \
    --path Documentos/PoC/Registro-Defectos-Agente-1.md \
    --path-rename "$RUTA_AGENTE/": \
    --path-rename Documentos/PlanDespliegue/:docs/operacion/ \
    --path-rename Documentos/Reuniones/DSI-2026-10-13/:docs/fuentes/reuniones/DSI-2026-10-13/ \
    --path-rename Documentos/PoC/:docs/fuentes/ \
    --replace-text "$REGLAS_COMBINADAS" \
    --replace-message "$REGLAS_COMBINADAS" \
    --mailmap "$MAILMAP" \
    --email-callback '
import os
e = email.strip(b"<>")
try:
    with open(os.environ.get("AGENTE1_EXTRACCION_EMAILS", ""), "rb") as f:
        privados = {linea.strip() for linea in f if linea.strip()}
except OSError:
    privados = set()
if e in privados:
    return b"anonimizado@users.noreply.github.com"
if re.search(rb"@[a-z0-9.-]*(undef\.edu\.ar|fie\.edu\.ar|iam\.gserviceaccount\.com)$", e, re.I):
    return b"anonimizado@users.noreply.github.com"
return e'

git remote remove origin 2>/dev/null || true   # defensivo: filter-repo ya lo quita

echo "==> 3/5 Reacondicionamiento de la punta"

# 3.a Retoques exactos sobre .github: el filtro de rutas del CI y el contexto
# de la imagen no admiten una sustitución mecánica; si alguno de estos textos
# no aparece, el archivo cambió arriba y hay que revisar el script a mano.
python3 - <<'PY'
from pathlib import Path

PARCHES = {
    ".github/workflows/agente1-ci.yml": [
        ("# Este archivo vive en `.github/workflows/` del repo raiz aunque el codigo\n"
         "# que prueba esta en `Implementacion/Agente1/`: GitHub Actions solo ejecuta\n"
         "# workflows desde esa ubicacion. Cuando se extraiga el repositorio del\n"
         "# Agente 1 (issue #80), este workflow viaja con el; los paths de abajo\n"
         "# quedan relativos a la raiz del repo extraido (`src/`, `tests/`) y los\n"
         "# filtros de rutas de los jobs `cambios` habra que ajustarlos alli.",
         "# Este archivo vive en `.github/workflows/` del repo del Agente 1: venia\n"
         "# del workspace academico y viajo en la extraccion del issue #80, con las\n"
         "# rutas ya relativas a la raiz (`src/`, `tests/`). El filtro de rutas del\n"
         "# job `cambios` saltea la suite en PRs que sólo tocan documentación."),
        ("        working-directory: Implementacion/Agente1",
         "        working-directory: ."),
        ("             | grep -qE '^(Implementacion/Agente1/|\\.github/workflows/agente1-ci\\.yml$)'; then",
         "             | grep -qvE '^(docs/|CONTEXT\\.md$|AGENTS\\.md$|CLAUDE\\.md$|README\\.md$|\\.github/pull_request_template\\.md$)'; then"),
        ("          path: Implementacion/Agente1/coverage.txt",
         "          path: coverage.txt"),
    ],
    ".github/workflows/agente1-imagen.yml": [
        ("      - Implementacion/Agente1/**", '      - "**"'),
        ("  CONTEXTO: Implementacion/Agente1", "  CONTEXTO: ."),
        ('"Implementacion/Agente1/pyproject.toml"', '"pyproject.toml"'),
    ],
    ".github/pull_request_template.md": [
        ("si no hay cambios bajo `Implementacion/Agente1/`,",
         "si el PR sólo toca documentación,"),
        ("cd Implementacion/Agente1 && ", ""),
    ],
    # El scheduler subprocesa las tareas dentro del repo: en la raíz nueva
    # ya no existe el prefijo Implementacion/Agente1 en el join de Path.
    "src/agente1/cli_scheduler.py": [
        ('            / "Implementacion"\n            / "Agente1"\n            / "scripts"',
         '            / "scripts"'),
        ('        / "Implementacion"\n        / "Agente1"\n        / "scripts"',
         '        / "scripts"'),
    ],
    # El agente deja de estar anidado bajo el workspace: lo que antes era la
    # raíz del workspace ahora ES este repo. Los scripts/tests que subían un
    # nivel para llegar a la raíz quedan apuntando a la raíz misma.
    "scripts/matriz_hu010.py": [
        ("REPO_ROOT = ROOT.parents[1]", "REPO_ROOT = ROOT"),
    ],
    "scripts/matriz_hu011.py": [
        ("REPO_ROOT = ROOT.parents[1]", "REPO_ROOT = ROOT"),
    ],
    "scripts/exportar_actividades_d2.py": [
        ("REPO_ROOT = ROOT.parents[1]", "REPO_ROOT = ROOT"),
    ],
    "scripts/regenerar_gacetilla_durable.py": [
        ("REPO_ROOT = ROOT.parents[1]", "REPO_ROOT = ROOT"),
    ],
    "tests/conftest.py": [
        ("REPO = ROOT.parents[1] if len(ROOT.parents) > 1 else ROOT",
         "REPO = ROOT"),
    ],
    "tests/test_respaldo_scripts.py": [
        ("REPO = ROOT.parents[1]", "REPO = ROOT"),
    ],
    "tests/test_cli_scheduler.py": [
        ("Path(__file__).resolve().parents[3]",
         "Path(__file__).resolve().parents[1]"),
    ],
}

for archivo, pares in PARCHES.items():
    ruta = Path(archivo)
    texto = ruta.read_text(encoding="utf-8")
    for viejo, nuevo in pares:
        if viejo not in texto:
            raise SystemExit(
                f"RETOQUE FALLÓ: '{viejo[:70]}…' no está en {archivo}; "
                "el archivo cambió en el origen y hay que actualizar el script."
            )
        texto = texto.replace(viejo, nuevo)
    ruta.write_text(texto, encoding="utf-8")
print("   .github retocado (CI, imagen, plantilla de PR)")
PY

# 3.b Sustitución general de rutas del workspace por las de la raíz nueva, en
# todo archivo de texto salvo el propio material del traspaso (éste script y
# el inventario describen la estructura vieja a propósito).
EXCLUIDOS_SED='^(scripts/extraer_repositorio\.sh|scripts/extraccion-redacciones\.txt|scripts/extraccion-redacciones-privadas\.ejemplo\.txt|docs/traspaso/)'
mapfile -t ARCHIVOS_SED < <(git grep -I -l "$RUTA_AGENTE" | grep -vE "$EXCLUIDOS_SED" || true)
mapfile -t ARCHIVOS_DOCS < <(git grep -I -l -E 'Documentos/(PlanDespliegue|PoC|Reuniones)/|pedidos-agente2\.md' \
    | grep -vE "$EXCLUIDOS_SED" || true)

if (( ${#ARCHIVOS_SED[@]} + ${#ARCHIVOS_DOCS[@]} > 0 )); then
    for f in "${ARCHIVOS_SED[@]}" "${ARCHIVOS_DOCS[@]}"; do
        sed -i \
            -e 's|/Implementacion/Agente1\b||g' \
            -e 's|\bImplementacion/Agente1/||g' \
            -e 's|\bImplementacion/Agente1\b|<raiz-del-repo>|g' \
            -e 's|Documentos/PlanDespliegue/|docs/operacion/|g' \
            -e 's|Documentos/Reuniones/DSI-2026-10-13/|docs/fuentes/reuniones/DSI-2026-10-13/|g' \
            -e 's|Documentos/PoC/Corpus-FIE-Informa-Historico-2026-10-13\.md|docs/fuentes/Corpus-FIE-Informa-Historico-2026-10-13.md|g' \
            -e 's|Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30\.md|docs/fuentes/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md|g' \
            -e 's|Documentos/PoC/Politica-Artefactos-Versionados-v1\.md|docs/fuentes/Politica-Artefactos-Versionados-v1.md|g' \
            -e 's|Documentos/PoC/Diseno-HU-012-Control-Pagos-v1\.md|docs/fuentes/Diseno-HU-012-Control-Pagos-v1.md|g' \
            -e 's|Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22\.md|docs/fuentes/Respuestas-SEU-Reunion-2026-09-22.md|g' \
            -e 's|Documentos/PoC/Registro-Actividades-Fuentes-Documentales-v1\.md|docs/fuentes/Registro-Actividades-Fuentes-Documentales-v1.md|g' \
            -e 's|Documentos/PoC/Nota-Solicitud-SEU-Agente-1-PPS-Juan-Ignacio-Gone\.md|docs/fuentes/Nota-Solicitud-SEU-Agente-1-PPS-Juan-Ignacio-Gone.md|g' \
            -e 's|Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1\.md|docs/fuentes/Contrato-Candidato-Insumos-A2-A5-Agente-1.md|g' \
            -e 's|Documentos/PoC/Registro-Defectos-Agente-1\.md|docs/fuentes/Registro-Defectos-Agente-1.md|g' \
            -e 's|`pedidos-agente2\.md`|`docs/fuentes/reuniones/DSI-2026-10-13/`|g' \
            "$f"
    done
    echo "   rutas reescritas en ${#ARCHIVOS_SED[@]} + ${#ARCHIVOS_DOCS[@]} archivos"
else
    echo "   no hubo rutas que reescribir"
fi

# 3.c AGENTS.md / CLAUDE.md del repo nuevo: apuntan al manual de operación en
# vez de repetirlo (criterio de aceptación del issue #80).
cat > AGENTS.md <<'EOF'
# Agente 1 — Extensión Bot (P100)

Repositorio propio del Agente 1, el agente de comunicación institucional de la
SEU dentro del Proyecto Centenario de la FIE/UNDEF. Se extrajo del workspace
académico del PPS con `scripts/extraer_repositorio.sh` (issue #80, ADR 0007):
qué se trajo y por qué está en `docs/traspaso/inventario-extraccion-agente-1.md`.

La documentación operativa vive en un solo lugar; este archivo sólo apunta:

- `README.md` — panorama del agente, historias de usuario y estructura.
- `MANUAL-OPERACION-AGENTE-1.md` — manual de operación, la fuente de verdad
  para instalar, correr y revertir el agente en el host.
- `CONTEXT.md` — lenguaje compartido del dominio.
- `docs/adr/` — decisiones de arquitectura difíciles de revertir.
- `docs/operacion/` — runbooks y el plan de despliegue.
- `PROCEDIMIENTO-CORTE-DE-VERSION.md` — control de cambios y cortes de versión
  (ADR 0010): `src/`, `migrations/`, `uv.lock`, `pyproject.toml`, `scripts/`,
  `systemd/`, `docker/` y `Dockerfile` son rutas controladas; si cambian hay
  que regenerar `manifest-version.json` con
  `uv run python scripts/manifest_version.py --salida manifest-version.json`
  y dejar constancia en `CHANGELOG.md`.

Verificaciones: `uv run pytest -q` y `uv run ruff check .`

Convenciones del repo: español, datos sintéticos y `@example.invalid`; ningún
correo institucional, ID interno, URL privada ni secreto en el tree.
EOF

cat > CLAUDE.md <<'EOF'
# Agente 1 — Extensión Bot (P100)

Igual que `AGENTS.md` (es la misma información, no la repito): la fuente de
verdad operativa es `MANUAL-OPERACION-AGENTE-1.md`, el dominio está en
`CONTEXT.md` y las decisiones en `docs/adr/`. Suite `uv run pytest -q`,
linter `uv run ruff check .`
EOF

# 3.d Hashes de los artefactos vivos del set de evaluación: la redacción
# cambió los bytes del dataset, la procedencia y el documento, y el manifest
# "congelado por hash" tiene que seguir verificando contra el árbol nuevo
# (tests/test_set_evaluacion_fie_informa.py). Los manifests históricos
# (manifest-corte, manifest-hu010-syn001) NO se retocan: son evidencia
# congelada de un commit pasado, registran lo que se midió entonces.
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

MANIFEST_SET = Path(
    "evidencias/manifest-set-evaluacion-gacetillas-fie-informa-2026-10-14.json"
)
if MANIFEST_SET.exists():
    manifiesto = json.loads(MANIFEST_SET.read_text(encoding="utf-8"))
    artefactos = manifiesto["artefactos"]
    for clave in list(artefactos):
        if not clave.endswith("_sha256"):
            continue
        archivo = artefactos.get(clave[: -len("_sha256")])
        if isinstance(archivo, str) and Path(archivo).is_file():
            artefactos[clave] = hashlib.sha256(
                Path(archivo).read_bytes()
            ).hexdigest()
    MANIFEST_SET.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print("   hashes de artefactos del set de evaluación recomputados")
PY

# 3.e Entrada en CHANGELOG [Sin publicar] por el cambio controlado que el
# reacondicionamiento introduce sobre scripts/, systemd/, docker/ y Dockerfile.
python3 - <<'PY'
from pathlib import Path

ENTRADA = (
    "- **Extracción del repositorio (#80).** Este repo se produjo con\n"
    "  `scripts/extraer_repositorio.sh` desde el workspace académico: las\n"
    "  rutas quedaron reacondicionadas a la raíz, `manifest-version.json` se\n"
    "  regeneró sobre el árbol nuevo y las direcciones e identificadores\n"
    "  internos quedaron redactados en toda la historia\n"
    "  (inventario en `docs/traspaso/`).\n"
    "  No corta versión: no cambia el comportamiento del agente.\n"
)
ruta = Path("CHANGELOG.md")
lineas = ruta.read_text(encoding="utf-8").splitlines(keepends=True)
for i, linea in enumerate(lineas):
    if linea.startswith("## [Sin publicar]"):
        lineas.insert(i + 1, "\n" + ENTRADA)
        ruta.write_text("".join(lineas), encoding="utf-8")
        break
else:
    raise SystemExit("RETOQUE FALLÓ: no se encontró '## [Sin publicar]' en CHANGELOG.md")
print("   CHANGELOG.md actualizado")
PY

# 3.f Manifest regenerado sobre el árbol retocado (los scripts quedaron
# controlados por el sed; ADR 0010).
if command -v uv >/dev/null; then
    uv run --no-sync python scripts/manifest_version.py --salida manifest-version.json \
        || python3 scripts/manifest_version.py --salida manifest-version.json
else
    python3 scripts/manifest_version.py --salida manifest-version.json
fi
echo "   manifest-version.json regenerado"

# 3.g Control: ninguna referencia al path viejo fuera del material del traspaso.
if git grep -nI "$RUTA_AGENTE" -- . \
        ':(exclude)scripts/extraer_repositorio.sh' \
        ':(exclude)scripts/extraccion-redacciones.txt' \
        ':(exclude)scripts/extraccion-redacciones-privadas.ejemplo.txt' \
        ':(exclude)docs/traspaso/' | grep .; then
    echo "ERROR: quedaron referencias a $RUTA_AGENTE fuera de lo esperado" >&2
    exit 1
fi

# Firma sintética por defecto: la gitconfig local puede traer un correo real
# (cuenta técnica o personal) y ese dato no puede quedar en el repo extraído.
GIT_AUTOR_NOMBRE="${GIT_AUTOR_NOMBRE:-Traspaso Agente 1}"
GIT_AUTOR_EMAIL="${GIT_AUTOR_EMAIL:-traspaso-agente1@example.invalid}"
git add -A
git -c user.name="$GIT_AUTOR_NOMBRE" -c user.email="$GIT_AUTOR_EMAIL" \
    commit -q -m "chore(traspaso): reacondiciona rutas y documentos raíz tras la extracción (#80)"
echo "   commit de reacondicionamiento: $(git rev-parse --short HEAD)"

echo "==> 4/5 Escaneo de secretos sobre toda la historia extraída"

# PATRONES genéricos: nombre|I|regex  (I = case-insensitive). El último campo
# admite '|' internos (alternancias ERE). Son clases públicas: NINGUNA cadena
# concreta de persona/cuenta/host/usuario/proyecto/IP/hash vive acá — ésas se
# derivan del lado izquierdo de cada regla de $REGLAS_PRIVADAS más abajo.
# Un hallazgo frena la extracción: se agrega la cadena a las reglas y se
# vuelve a correr.
#
# EXCL_PATRONES: exenciones documentadas, por nombre de patrón. Sólo se usa
# para fixtures sintéticos del propio repo (PEMs de prueba que NO son claves
# reales); cualquier hallazgo real queda visivo igual.
declare -A EXCL_PATRONES=(
    ["clave privada PEM"]="tests/test_(workspace_cuenta_servicio|corrida_unica)\.py:[0-9]+:"
)
PATRONES=(
    "cuenta de servicio GCP|N|@[a-z0-9.-]*iam\.gserviceaccount\.com"
    "dominio institucional (correos y hosts)|I|undef\.edu\.ar|fie\.edu\.ar"
    "home de usuario|N|/home/[a-z0-9_-]+"
    "access token de Google|N|ya29\.[A-Za-z0-9_-]{10,}"
    "refresh token OAuth|N|1//[0-9A-Za-z_-]{30,}"
    "API key de Google|N|AIza[0-9A-Za-z_-]{35}"
    "client ID OAuth|N|[0-9]+-[a-z0-9]{32}\.apps\.googleusercontent\.com"
    "client secret OAuth|N|GOCSPX-[A-Za-z0-9_-]{20,}"
    "clave privada PEM|N|BEGIN[A-Z ]*PRIVATE KEY"
    "IP privada|N|(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)[0-9]{1,3}\.[0-9]{1,3}"
    "correo personal|I|[a-z0-9._%+-]+@(gmail\.com|proton\.(me|mail)|hotmail\.com|outlook\.com)"
    "host de red interna|I|\b[a-z0-9-]+\.(internal|lan|corp|intra)\b"
)

REVS="$(git rev-list --all)"
HALLAZGOS=0

# buscar_en_historia <nombre> <gflag> <modo E|F> <patron>
# Tres pasadas: blobs de todos los commits, mensajes de commit/tag y nombres
# de archivo. modo F = cadena fija (LHS de una regla literal).
buscar_en_historia() {
    local nombre="$1" gflag="$2" modo="$3" patron="$4"
    local excl grep_out msg_out nom_out
    excl="${EXCL_PATRONES[$nombre]:-}"
    filtra() { if [[ -n "$excl" ]]; then grep -vE "$excl" || true; else cat; fi; }
    if [[ "$modo" == "F" ]]; then
        grep_out=$(git grep -nI -F -e "$patron" $REVS 2>/dev/null | filtra | head -20) || true
    else
        grep_out=$(git grep -nI $gflag -E "$patron" $REVS 2>/dev/null | filtra | head -20) || true
    fi
    if [[ -n "${grep_out:-}" ]]; then
        HALLAZGOS=$((HALLAZGOS + 1))
        echo "   ✗ $nombre"
        echo "$grep_out" | sed 's/^/      /'
    fi
    if [[ "$modo" == "F" ]]; then
        msg_out=$({ git log --all --format='%h %s%n%b'; \
            git for-each-ref refs/tags --format='%(contents)'; } \
            | grep -n -F -e "$patron" | filtra | head -5) || true
    else
        msg_out=$({ git log --all --format='%h %s%n%b'; \
            git for-each-ref refs/tags --format='%(contents)'; } \
            | grep -n $gflag -E "$patron" | filtra | head -5) || true
    fi
    if [[ -n "${msg_out:-}" ]]; then
        HALLAZGOS=$((HALLAZGOS + 1))
        echo "   ✗ $nombre (en mensajes de commit/tag)"
        echo "$msg_out" | sed 's/^/      /'
    fi
    if [[ "$modo" == "F" ]]; then
        nom_out=$(git log --all --name-only --format='' | sort -u \
            | grep -n -F -e "$patron" | head -10) || true
    else
        nom_out=$(git log --all --name-only --format='' | sort -u \
            | grep -n $gflag -E "$patron" | head -10) || true
    fi
    if [[ -n "${nom_out:-}" ]]; then
        HALLAZGOS=$((HALLAZGOS + 1))
        echo "   ✗ $nombre (en nombres de archivo)"
        echo "$nom_out" | sed 's/^/      /'
    fi
}

if (( CORRER_ESCANEO )); then
    # a) Clases genéricas.
    for entrada in "${PATRONES[@]}"; do
        IFS='|' read -r nombre icase patron <<< "$entrada"
        gflag=""; [[ "$icase" == "I" ]] && gflag="-i"
        buscar_en_historia "$nombre" "$gflag" "E" "$patron"
    done

    # b) El lado izquierdo de CADA regla privada: nada de lo que se redactó
    # puede sobrevivir en blobs, mensajes ni nombres de archivo.
    while IFS= read -r linea; do
        [[ -n "$linea" ]] || continue
        regla="${linea%==>*}"
        if [[ "$linea" == literal:* ]]; then
            buscar_en_historia "regla privada: ${regla:0:40}…" "" "F" "${regla#literal:}"
        elif [[ "$linea" == regex:* ]]; then
            lhs="${regla#regex:}"
            gflag=""; [[ "$lhs" == "(?i)"* ]] && { gflag="-i"; lhs="${lhs#"(?i)"}"; }
            buscar_en_historia "regla privada: ${regla:0:40}…" "$gflag" "E" "$lhs"
        fi
    done < "$REGLAS_PRIVADAS"

    # c) Autores, committers y taggers: sólo noreply/example.invalid admitido
    # tras la anonimización.
    AUTORES_RAROS="$( { git log --all --format='%ae%n%ce'; \
        git for-each-ref --format='%(taggeremail)' refs/tags; } | sort -u \
        | grep -vE 'users\.noreply\.github\.com|noreply@github\.com|@example\.invalid|^$|^<>$' || true)"
    if [[ -n "$AUTORES_RAROS" ]]; then
        HALLAZGOS=$((HALLAZGOS + 1))
        echo "   ✗ correos de autoría no anonimizados"
        echo "$AUTORES_RAROS" | sed 's/^/      /'
    fi
    # Nombres de autoría: el autor del Agente 2 no puede quedar con nombre real.
    NOMBRES_RAROS="$( { git log --all --format='%an%n%cn'; \
        git for-each-ref --format='%(taggername)' refs/tags; } | sort -u \
        | grep -vE '^(Juan Ignacio Goñe|Autor A2|Anonimizado|Traspaso Agente 1|GitHub|github-actions\[bot\])$|^$' || true)"
    if [[ -n "$NOMBRES_RAROS" ]]; then
        HALLAZGOS=$((HALLAZGOS + 1))
        echo "   ✗ nombres de autoría no anonimizados"
        echo "$NOMBRES_RAROS" | sed 's/^/      /'
    fi

    if command -v gitleaks >/dev/null; then
        echo "   gitleaks detectado: corrida complementaria sobre toda la historia"
        if ! gitleaks git --report-format json --report-path /tmp/gitleaks-extraido.json . ; then
            HALLAZGOS=$((HALLAZGOS + 1))
            echo "   ✗ gitleaks reportó hallazgos (ver /tmp/gitleaks-extraido.json)"
        fi
    else
        echo "   (gitleaks no instalado: se usó el grep documentado)"
    fi

    if (( HALLAZGOS > 0 )); then
        echo "ERROR: el escaneo encontró $HALLAZGOS clases de hallazgos." >&2
        echo "       Agregar la cadena a las reglas privadas y volver a correr." >&2
        exit 1
    fi
    echo "   escaneo limpio: ${#PATRONES[@]} clases genéricas + LHS de las reglas privadas"
else
    echo "   escaneo salteado (--sin-escaneo)"
fi

echo "==> 5/5 Informe del repositorio extraído"
echo "   commits en el origen ($RAMA): $COMMITS_FUENTE"
echo "   commits en el repo extraído:  $(git rev-list --count HEAD)"
echo "   archivos en la punta:         $(git ls-files | wc -l)"
echo "   tags conservados:             $(git tag -l | wc -l) ($(git tag -l | tr '\n' ' '))"
echo "   tamaño .git:                  $(du -sh .git | cut -f1)"
git count-objects -v | sed 's/^/   /'
echo "   remote:                       $(git remote -v | wc -l) remotos (esperado: 0)"

if (( CORRER_TESTS )) && command -v uv >/dev/null; then
    echo "==> Suite: uv run pytest -q"
    uv run pytest -q
    echo "==> Linter: uv run ruff check ."
    uv run ruff check .
elif (( CORRER_TESTS )); then
    echo "   (uv no está instalado: la suite queda para correr a mano en el repo extraído)"
fi

echo "==> Listo: $DESTINO tiene el repo del Agente 1 con su historia, sin remotes."
