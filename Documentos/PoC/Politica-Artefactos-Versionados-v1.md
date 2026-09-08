# Politica de artefactos versionados — v1

- **Issue:** `SpendIce/Proyecto-Final#8`
- **Fecha de corte:** 2026-09-08
- **Estado:** `VIGENTE`
- **Alcance:** todo el repositorio del proyecto final de Juan Ignacio Gone.
- **Insumo previo:** `Documentos/PoC/Auditoria-Worktree-Issue-2-2026-09-05.md` e
  `Inventario-Worktree-Issue-2-2026-09-05.csv` (issue #2).

## 1. Proposito

Definir que entra a Git y que no, de manera que la baseline tecnica recuperable
pueda reconstruirse desde el repositorio sin arrastrar ruido de compilacion ni
publicar material que todavia depende de una decision humana.

Esta politica no autoriza publicacion institucional y no modifica el contenido
academico de ningun entregable.

## 2. Clasificacion

| Clase | Definicion | Tratamiento |
|---|---|---|
| Fuente deliberada | Archivo escrito a mano del que derivan los demas: `.tex`, `.md`, `.html`, `.bib`, `.puml`, codigo, fixtures, politicas y contratos JSON | Versionado |
| Entregable historico | Render ya versionado que forma parte del historial academico entregado | Se conserva versionado; no se desversiona |
| Artefacto reproducible | Salida que un comando documentado regenera desde una fuente versionada | Fuera de Git |
| Runtime local | Modelos, entornos, caches, salidas de ejecucion | Fuera de Git |
| Respaldo de recuperacion | `.local-recovery/` | Fuera de Git, deliberadamente local |

La clase se decide por como se produce el archivo, no por su extension. Un
`.pdf` puede ser entregable historico o artefacto reproducible segun exista o no
un comando versionado que lo regenere.

## 3. Verificacion de reproducibilidad

La clase `artefacto reproducible` solo es valida si el comando existe en el
repositorio. Por eso esta politica se publica junto con
`scripts/renderizar-artefactos.sh`, que regenera cada salida desversionada
desde su fuente versionada.

Ejecucion completa del 2026-09-08 sobre el corte `c36a6fa`, comparada contra los
archivos que estaban sin trackear:

| Artefacto | Resultado | Lectura |
|---|---|---|
| `Ficha-Definiciones-Operativas-SEU-Agente-1.{aux,out}` | identicos byte a byte | reproducible |
| `Ficha-Definiciones-Operativas-SEU-Agente-1.pdf` | 153.314 bytes, 78 bytes distintos | reproducible salvo `CreationDate`, `ModDate` e `ID` |
| `Paquete-Revision-SEU-Agente-1.{aux,out,toc}` | identicos byte a byte | reproducible |
| `Paquete-Revision-SEU-Agente-1.pdf` | 194.864 bytes, 78 bytes distintos | reproducible salvo metadatos de fecha |
| `Flujo-Aprobacion-SEU-Agente-1-2026-08-26.png` | identico byte a byte | reproducible y determinista |
| `Flujo-Aprobacion-SEU-Agente-1-2026-08-26.pdf` | 67.696 bytes, 14 bytes distintos | reproducible salvo metadatos de fecha |
| `Lamina-Agente-1-Extension-Bot-2026-08-26.png` | 3200x1800, contenido distinto | la fuente HTML se edito el 2026-09-06; el render sin trackear era anterior |
| `Laminas-Agente-1-Extension-Bot-2026-08-26.pdf` | 3 paginas, contenido distinto | mismo motivo |
| `Laminas-.../0{1,2,3}-*.png` | 3200x1800, contenido distinto | mismo motivo; se rasterizan desde el PDF, no por captura de deck |

Los `.log` de LaTeX quedan fuera de la tabla porque registran rutas locales y
marcas de tiempo por definicion.

**Hallazgo:** los renders del 2026-08-26 que estaban sin trackear ya no
correspondian a sus fuentes. Versionarlos habria publicado material que
contradice la fuente versionada en el mismo commit. Ese es el argumento
principal para dejarlos fuera de Git y regenerarlos cuando se necesiten.

## 4. Reglas aplicadas

`.gitignore` incorpora:

- intermedios de LaTeX por extension (`.aux`, `.fdb_latexmk`, `.fls`, `.log`,
  `.out`, `.synctex.gz`, `.toc`);
- las rutas explicitas de los renders regenerables de `Documentos/PoC/` y
  `Documentos/Presentacion/`;
- `.playwright-mcp/` para snapshots nuevos de navegador.

Git no desversiona por ignore: las reglas solo afectan archivos que todavia no
estan trackeados.

## 5. Lo que no se desversiona

Se verifico que ningun entregable ni flujo academico depende de un archivo que
esta politica saca de Git. Se conservan versionados, sin cambios:

- `Documentos/Anteproyecto/` completo, incluidos `.aux`, `.bbl`, `.blg`, `.log`,
  `.out`, `.run.xml`, `.toc` y el PDF entregado;
- `Documentos/CasosUso/` completo, con los mismos intermedios;
- los cuatro `console-*.log` y los `page-*.yml` de `.playwright-mcp/` del corte
  historico. Se revisaron con busqueda de correos institucionales o personales y
  de identificadores de recursos de Google: cero coincidencias.

No se ejecuta ninguna purga masiva de artefactos academicos historicos. Esta
politica no desversiona ningun archivo: todos los objetivos que alcanza ya
estaban sin trackear al momento de aplicarla.

## 6. Material bloqueado por decision humana

Estos artefactos quedan fuera de Git tanto por reproducibilidad como por
gobernanza; regenerarlos es local y no equivale a autorizacion de circulacion:

- `Documentos/PoC/Validacion-SEU/Paquete-Revision-SEU-Agente-1.pdf` —
  `NO_PUBLICAR_HASTA_REVISION_INSTITUCIONAL` segun el inventario del issue #2;
  depende del issue #14.
- `Documentos/PoC/Ficha-Definiciones-Operativas-SEU-Agente-1.pdf` —
  `REVISAR_ANTES_DE_PUBLICAR`; depende del issue #14.

Sus fuentes `.tex` si estan versionadas: lo que requiere decision humana es la
circulacion del render, no la existencia del instrumento.

## 7. Procedimiento para agregar un artefacto nuevo

1. Clasificarlo con la tabla de la seccion 2.
2. Si es reproducible, agregar su comando a `scripts/renderizar-artefactos.sh` y
   su ruta al `.gitignore` en el mismo commit.
3. Si es fuente o entregable deliberado, versionarlo con allowlist explicita de
   paths y control de secretos sobre esos paths antes del staging, como exige la
   auditoria del issue #2.
4. No usar `git clean`, `reset`, `checkout` ni `chmod -R` para resolver ruido.
