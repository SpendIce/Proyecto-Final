# Inventario de la extracción del repositorio del Agente 1

- **Issue:** [#80](https://github.com/SpendIce/Proyecto-Final/issues/80), decidido por ADR 0007 (el traspaso reparte tres responsables).
- **Script:** `scripts/extraer_repositorio.sh` (en este repo vive en `Implementacion/Agente1/scripts/`; en el repo extraído queda en `scripts/`).
- **Cuándo se ejecuta:** después de la mesa del 18/11/2026. Este documento y el script se escriben antes, como preparación reproducible; el ensayo está en `ensayo-extraccion-2026-11-11.md`.
- **Cómo se produce:** clon limpio de `main` fuera del repo, `git filter-repo` sobre las rutas listadas abajo, reacondicionamiento de rutas a la raíz, redacciones de `scripts/extraccion-redacciones.txt` en toda la historia, escaneo de secretos y suite.

## Criterio general

El repositorio nuevo le queda al **responsable de operación** (Dirección de
Ingeniería en Informática) y al **responsable de evolución** (los alumnos que
continúan el P100). Viaja:

1. Todo lo que hace funcionar al Agente 1 y permite seguir desarrollándolo con su historia.
2. La documentación que el operador necesita para instalar, operar y revertir el agente.
3. Las fuentes citadas por los contratos, las políticas, el manual y los ADR: una referencia a un documento que no viaja queda como cita externa, y se prefirió que las citas más operativas resuelvan.
4. El registro de defectos y la evidencia sanitizada, como pide el cuerpo del issue.

No viaja:

1. El anteproyecto y los entregables académicos (la materia, el PPS), ni el material de cátedra.
2. Las configuraciones de agentes y herramientas del workspace (`Agentes/`, `.claude/`, `.codex/`, `.opencode/`, `.agents/`, `.playwright-mcp/`).
3. Los rastros del workspace anterior del autor del Agente 2 (su archivo de pedidos y afines): los documentos que él **firmó como autor del contrato A2** dentro de `evidencias/` o que los contratos citan como fuente **sí** viajan, porque forman parte del registro operativo del Agente 1, no de su workspace; su nombre y sus identificadores quedan redactados como `autor-a2`/`el autor del Agente 2` por las reglas privadas de la extracción.
4. Las notas de trabajo (`notas/`), los apuntes de estudio (`learning-*`, `GLOSSARY.md`, `MISSION.md`, `RESOURCES.md`, `EVALUATION-RULES.md`) y el material de campus (`Contenido/`).

## Documentación incluida

| Ruta en el workspace | Destino en el repo nuevo | Por qué entra |
|---|---|---|
| `Implementacion/Agente1/` (completa) | raíz del repo | Código, tests, contratos, datos sintéticos, `evidencias/` sanitizadas, `MANUAL-OPERACION-AGENTE-1.md`, `CHANGELOG.md`, `PROCEDIMIENTO-CORTE-DE-VERSION.md`, Dockerfile, compose, systemd, migrations. Es el Agente 1. |
| `CONTEXT.md` | `CONTEXT.md` | Lenguaje compartido del dominio; lo citan los ADR y el código. |
| `docs/adr/` | `docs/adr/` | ADR 0001–0015: las decisiones de arquitectura vigentes. |
| `docs/research/` | `docs/research/` | Research de controles de Google que sostiene el modelo de seguridad. |
| `docs/seguridad/` | `docs/seguridad/` | Modelo de seguridad de la cuenta Google del agente (decisiones #64). |
| `docs/traspaso/` | `docs/traspaso/` | Este inventario y la evidencia del ensayo: es la bitácora de cómo se produjo el repo. |
| `.github/pull_request_template.md` | mismo lugar | Plantilla de PR vigente; describe el control de cambios que hereda el repo nuevo. |
| `.github/workflows/agente1-*.yml` | mismo lugar | CI/CD del agente (`agente1-ci`, `agente1-imagen`): viajan con rutas retocadas a la raíz. |
| `Documentos/PlanDespliegue/` (7 archivos) | `docs/operacion/` | Documentación de operación que el operador sí corre: plan de despliegue, especificación de entornos, runbooks (scheduler, contenedores, Workspace D2-D3, protección de `main`) y procedimiento de reversión. Está bajo `Documentos/` por la convención del workspace, pero es material operativo, no entregable académico. |
| `Documentos/Reuniones/DSI-2026-10-13/` | `docs/fuentes/reuniones/DSI-2026-10-13/` | Acta, correos y cuestionario de la reunión con DSI que fijó la custodia de la cuenta de servicio y la delegación: fuente del modelo de seguridad. |
| `Documentos/PoC/Corpus-FIE-Informa-Historico-2026-10-13.md` | `docs/fuentes/` | Corpus histórico de FIE Informa citado como `x-fuente` por las formas declaradas y el padrón de áreas (15 referencias). |
| `Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md` | `docs/fuentes/` | Corpus de comunicaciones reales de la SEU citado por insumos y evidencias. |
| `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md` | `docs/fuentes/` | Diseño del contrato candidato de insumos A3–A5: lo necesita quien continúe el intercambio entre agentes del P100. |
| `Documentos/PoC/Registro-Defectos-Agente-1.md` | `docs/fuentes/` | Registro de defectos y bloqueantes (nombrado explícitamente en el issue). |
| `Documentos/PoC/Politica-Artefactos-Versionados-v1.md` | `docs/fuentes/` | Política de artefactos versionados citada por el manual, `.gitignore` y `renderizar_manual.py`. |
| `Documentos/PoC/Diseno-HU-012-Control-Pagos-v1.md` | `docs/fuentes/` | Diseño citado como `x-fuente` por los contratos de pagos. |
| `Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22.md` | `docs/fuentes/` | Respuestas de la SEU citadas como fuente por `politica_redes_provisional_v1.json`. |
| `Documentos/PoC/Registro-Actividades-Fuentes-Documentales-v1.md` | `docs/fuentes/` | Registro de fuentes documentales citado por el ADR 0006. |
| `Documentos/PoC/Nota-Solicitud-SEU-Agente-1-PPS-Juan-Ignacio-Gone.md` | `docs/fuentes/` | Nota a la SEU citada como fuente por la política de redes. |

## Documentación excluida

| Ruta | Por qué queda fuera |
|---|---|
| `Documentos/Anteproyecto/`, `Documentos/CasosUso/`, `Documentos/Gantt/`, `Documentos/Presentacion/`, `Documentos/Laboratorio/`, `Documentos/Inventario/`, `Documentos/Arquitectura/`, `Documentos/Diagrama*/`, `Documentos/ModeloNegocio/`, `Documentos/Plan*/`, `Documentos/Comun/`, `Documentos/Reuniones/Laboratorio-2026-10-12/` | Entregables académicos del PPS (anteproyecto, anexos de laboratorio, planes de cátedra, presentaciones, reuniones académicas). El issue los excluye expresamente. Las referencias a ellos que quedan dentro del código (scripts `anexo*`, `plantilla_laboratorio.py`, docstrings) son citas externas: esos scripts son herramientas de la cursada y el repo nuevo los conserva por historia, no para correrlos. |
| `Documentos/PoC/` (el resto) | Material de trabajo del PoC: checklists, auditorías del proceso, spikes, notas a áreas institucionales, `Validacion-SEU/` (paquete de revisión), índices y matrices de gestión. No son citados por artefactos que viajan ni necesarios para operar. `registro-defectos.csv` de `Validacion-SEU/` es sólo una plantilla vacía. |
| `Adjuntos/`, `Contenido/` (bible, campus) | Material de cátedra y fuentes institucionales del workspace; el issue los excluye. |
| `Agentes/` | Perfiles de agentes del workspace académico (incluye material heredado del autor del Agente 2). El repo nuevo define sus propias instrucciones en `AGENTS.md`/`CLAUDE.md` generadas por el script. |
| `AGENTS.md`, `CLAUDE.md` (raíz) | Describen el workspace académico entero, no el repo del agente. En el repo nuevo los escribe el script, apuntando al manual de operación. |
| `notas/` | Notas de trabajo del workspace (excluida expresamente). |
| `.claude/`, `.codex/`, `.opencode/`, `.agents/`, `.playwright-mcp/` | Estado y configuración de herramientas del workspace. |
| `learning-explainers/`, `learning-records/`, `GLOSSARY.md`, `MISSION.md`, `RESOURCES.md`, `EVALUATION-RULES.md` | Sistema de estudio para el parcial de Gestión de Proyectos; nada que ver con el Agente 1. |
| El archivo de pedidos del workspace anterior (raíz) | Rastro del intercambio del autor del Agente 2↔workspace (excluido expresamente; su nombre va en las reglas privadas). Las citas a él en `historia_viva.py` y `test_historia_viva.py` se reescriben a `docs/fuentes/reuniones/DSI-2026-10-13/` en el commit de reacondicionamiento. |
| `run-demo.sh`, `run-demo-plan-a.sh` | Wrappers de demo del workspace; las demos del agente viven en `scripts/` dentro del propio agente. |
| `scripts/` (raíz: `sync_bible.py`, `renderizar-artefactos.sh`) | Herramientas del workspace (sincronización de la bible, render de entregables LaTeX). |
| `.gitignore` (raíz) | Reglas del workspace (`Documentos/`, `.local-recovery/`); en el repo nuevo queda el `.gitignore` del agente. |
| `DSI2.zip` | Material de cátedra en binario. |
| `docs/agents/` | Convenciones del harness del workspace (issue tracker apunta a `SpendIce/Proyecto-Final`, esquema single-context del workspace). En el repo nuevo no aplican tal cual. |
| `EVALUATION-RULES.md` | Reglas de evaluación del parcial; es del sistema de estudio. |

## Decisiones tomadas en el diseño del script

- **Ubicación del script:** `Implementacion/Agente1/scripts/extraer_repositorio.sh`, no `scripts/` de la raíz. Es una herramienta del traspaso del Agente 1: viaja con el repo extraído y documenta cómo se produjo. La raíz `scripts/` se excluye por ser herramientas del workspace.
- **Reacondicionamiento:** `Implementacion/Agente1/` pasa a la raíz (`--path-rename`); `Documentos/PlanDespliegue/` → `docs/operacion/`, `Documentos/Reuniones/DSI-2026-10-13/` → `docs/fuentes/reuniones/DSI-2026-10-13/` y los archivos citados de `Documentos/PoC/` → `docs/fuentes/`. Las referencias internas se reescriben en un commit de reacondicionamiento sobre la punta; la historia conserva la estructura vieja, como corresponde a un `filter-repo`. El commit de reacondicionamiento también corrige lo que asumía el agente anidado: `REPO_ROOT`/`REPO` de scripts y tests que subían un nivel (`parents[1]`/`parents[3]`) pasa a la raíz misma, el `join` por componentes de `cli_scheduler.py` (`repo/"Implementacion"/"Agente1"/"scripts"`) pasa a `repo/"scripts"`, y los hashes del manifest del set de evaluación vigente se recomputan sobre los artefactos ya redactados (los manifests históricos son evidencia congelada y no se tocan).
- **`AGENTS.md`/`CLAUDE.md` del repo nuevo** los genera el script apuntando al manual de operación (criterio de aceptación: no lo repiten).
- **Redacciones en dos capas.** `scripts/extraccion-redacciones.txt` (versionado) sólo tiene reglas genéricas, que no nombran a nadie: dominios institucionales y sus direcciones → `*@example.invalid`/`*.example.invalid`, cuentas de servicio `*.iam.gserviceaccount.com` → `local@example.invalid` y homes de usuario → `/home/<usuario>`. Las reglas que **sí nombran** una persona, cuenta, host, usuario, proyecto, IP o hash concreto viven en `extraccion-redacciones-privadas.txt`, un archivo **fuera del repo** (en el workspace: `.local-recovery/traspaso/`, ignorado por git, permisos `0600`): correos personales del autor y del autor del Agente 2, la cuenta técnica y su sha256 (el contrato `cuentas_suplantables_v1.json` y la evidencia que lo cita quedan coherentes), el ID del proyecto interno, el hostname y los usuarios del servidor, el nombre del archivo del workspace anterior, una IP interna de un fixture (→ `192.0.2.10`, rango de documentación) y un valor con forma de token. El repo trae la plantilla `scripts/extraccion-redacciones-privadas.ejemplo.txt` con marcadores `<…>`: se copia fuera del repo y se reemplaza cada marcador por el valor real. El script las exige con `--reglas-privadas RUTA` (sin ellas no corre), verifica que no vivan en un repo versionado y las combina con las genéricas para `--replace-text` (blobs) y `--replace-message` (mensajes de commit y tag). Formato: una regla por línea `literal:`/`regex:` + `==>` reemplazo; **no admite comentarios** — una línea `#` reemplazaría todos los `#` de la historia, verificado en el ensayo. Las direcciones públicas de contacto también quedan sintéticas: la real vive en el corpus institucional, no aporta a la evidencia, y el dominio uniforme permite un invariante auditable («cero direcciones institucionales en la historia»).
- **Autoría:** autor/committer/tagger reescritos con `--mailmap`, un archivo que también vive fuera del repo junto a las reglas privadas (plantilla versionada: `scripts/extraccion-mailmap.ejemplo.txt`): los correos personales y de cuentas internas mapean a `users.noreply.github.com` y el nombre del autor del Agente 2 pasa a `Autor A2`. Un `--email-callback` genérico (sin datos reales) normaliza formatos raros (`<<correo>>`) y degrada cualquier institucional residual a `anonimizado@users.noreply.github.com`. Los demás nombres de autor se conservan (atribución de la historia).
- **Escaneo de secretos:** sobre toda la historia extraída —blobs, mensajes de commit y tag, correos y nombres de autor/committer/tagger y nombres de archivo— con gitleaks si está instalado, si no con un grep documentado: las clases genéricas (tokens OAuth/API key/PEM/IP privada/correos personales/host interno/dominios/homes) más el **lado izquierdo de cada regla privada**, así todo lo redactado queda verificado. Un hallazgo frena el proceso: se agrega la cadena a las reglas y se vuelve a correr.
- **Ramas/tags:** se clona una sola rama (`main` por defecto). Los tags `agente1-v*` viajan con su historia (las versiones del agente siguen citándose). La rama `deploy` no viaja: la escribe el workflow `agente1-imagen` y se regenera al cortar la próxima versión.
- **Limitación conocida:** los scripts `anexo*.py`, `plantilla_laboratorio.py` y referencias `x-fuente`/`provenance` a documentos no incluidos quedan como citas externas. Los scripts de anexos son herramientas de la cursada, no de la operación.

## Qué NO hace este script (a propósito)

No crea el repositorio en GitHub, no agrega remotes ni empuja el repo extraído. Después del 18/11: correr el script, revisar el informe, crear el repo en la cuenta que indique la Dirección, `git remote add` y `git push --all` + `--tags` a mano.
