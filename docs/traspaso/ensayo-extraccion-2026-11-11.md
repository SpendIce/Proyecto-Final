# Ensayo de extracción — 11/11/2026

Bitácora del ensayo de `Implementacion/Agente1/scripts/extraer_repositorio.sh`
corrido en `/tmp` sobre la rama `chore/80-script-extraccion`, con las reglas
privadas y el mailmap externos (ver el
[inventario](inventario-extraccion-agente-1.md) para el criterio completo).
La extracción definitiva corre después de la mesa del 18/11 sobre `main`;
este ensayo valida el procedimiento de punta a punta.

## Comando

```bash
git clone --single-branch --branch chore/80-script-extraccion <workspace> /tmp/ws-clon
/tmp/ws-clon/Implementacion/Agente1/scripts/extraer_repositorio.sh \
    /tmp/ws-clon /tmp/agente1-extraido \
    --rama chore/80-script-extraccion \
    --reglas-privadas <workspace>/.local-recovery/traspaso/extraccion-redacciones-privadas.txt
# --mailmap toma por defecto extraccion-mailmap.txt, junto a las reglas privadas
```

Las reglas privadas y el mailmap viven fuera del repo (`.local-recovery/`,
ignorado por git, `0600`), armados a partir de las plantillas
`scripts/extraccion-redacciones-privadas.ejemplo.txt` y
`scripts/extraccion-mailmap.ejemplo.txt`. El script frena si faltan o si
viven en una ruta versionada no ignorada — verificado: sin `--reglas-privadas`
sale con código 1 y con un archivo privado dentro de un repo no ignorado
también.

## Resultado

| Magnitud | Valor |
| --- | --- |
| Commits en el origen | 513 |
| Commits en el repo extraído | 369 |
| Archivos en la punta | 498 |
| Tags conservados | 11 (`agente1-v0.1.0`, `agente1-v0.5.0`…`v0.5.9`) |
| Tamaño `.git` | 4.6M |
| Remotes | 0 (filter-repo los elimina; no se agrega ninguno) |
| Escaneo de secretos | limpio — 12 clases genéricas + LHS de las reglas privadas (grep documentado; gitleaks no instalado) |
| `uv run pytest -q` en el repo extraído | 2489 passed, 16 skipped |
| `uv run ruff check .` | all checks passed |

La estructura quedó como espera el inventario: `Implementacion/` ausente,
`AGENTS.md`/`CLAUDE.md`/`CONTEXT.md`/`MANUAL-OPERACION-AGENTE-1.md` en la
raíz, `docs/` con `adr/`, `operacion/`, `fuentes/` y `traspaso/`, y el
commit de reacondicionamiento `chore(traspaso): reacondicionar la punta
del repositorio` sobre la punta.

## Verificación de autoría

`git log --format='%ae %ce'` del repo extraído, dominios agregados:

- 730 `users.noreply.github.com` (autores personales y cuentas internas,
  mapeados por el mailmap externo y el callback genérico);
- 6 `noreply@github.com` (merge commits hechos por la web de GitHub);
- 2 `example.invalid` (el autor sintético del commit de reacondicionamiento).

Ningún correo real: ni personal, ni institucional, ni de la cuenta técnica.
Taggers: sólo `…@users.noreply.github.com`. La rama fuente también quedó
verificada: `git log -p origin/main..HEAD` filtrado por cada valor del
archivo de reglas privadas no produce hallazgos — los commits nuevos de la
rama nunca contuvieron esos valores.

## Iteraciones del ensayo

El ensayo se corrió varias veces hasta quedar en verde; cada hallazgo se
convirtió en una corrección:

1. **Rutas asumidas anidadas.** Varios scripts y tests subían un nivel por
   encima del agente (`parents[1]`/`parents[3]`, join por componentes en
   `cli_scheduler.py`) esperando el workspace completo. El commit de
   reacondicionamiento los corrige a la raíz nueva — de 17 fallos de suite
   a cero.
2. **Hashes de artefactos.** El manifest del set de evaluación vigente
   guarda sha256 de artefactos que la redacción altera; se recomputan en
   el reacondicionamiento. Los manifests históricos quedan congelados como
   evidencia.
3. **Comentarios en el archivo de reglas.** `--replace-text` no admite
   comentarios: una línea `#` se interpreta como patrón y borraba todos
   los `#` de la historia. Las reglas son una por línea, sin comentarios;
   la explicación vive en el inventario y en la plantilla.
4. **Mensajes y metadatos.** `--replace-text` sólo toca blobs: los mensajes
   de commit/tag van por `--replace-message`, la autoría por `--mailmap`
   (externa) y un `--email-callback` genérico de respaldo.
5. **Autoría del commit de reacondicionamiento.** Por defecto usaba el
   `user.email` local real; ahora firma una identidad sintética
   `example.invalid` salvo que el operador la pise por entorno.
6. **Dominio institucional raíz.** Un correo de la DSI mencionaba el
   dominio padre `undef.edu.ar` a secas (firma DKIM); se agregó a las
   reglas genéricas, después de los subdominios para que éstos se
   reemplacen primero.
7. **Reglas privadas fuera del repo.** La primera versión versionaba las
   reglas con datos reales; el repo es público. Ahora el script las exige
   por `--reglas-privadas` y el escaneo deriva sus patrones del lado
   izquierdo de cada regla — incluidos correos, cuentas, hosts, usuarios,
   IDs internos, IPs y hashes concretos.
