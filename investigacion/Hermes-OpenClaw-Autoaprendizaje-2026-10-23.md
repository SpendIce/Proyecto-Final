# Hermes Agent y OpenClaw: qué aprende su autoaprendizaje y si cabe en el control de cambios del Agente 1

- **Fecha:** 2026-10-23
- **Ticket:** [#144](https://github.com/SpendIce/Proyecto-Final/issues/144) (investigación). La decisión de adoptar o no se toma en [#145](https://github.com/SpendIce/Proyecto-Final/issues/145): este documento no recomienda nada.
- **Fuentes:** documentación oficial versionada en cada repositorio (rama `main` consultada el 23/10/2026: Hermes ≈ `cb757fac59c9`, OpenClaw ≈ `11eaa003bc8c`), código fuente, notas de release, GitHub Security Advisories, Docker Hub y el registro npm. Las fuentes secundarias solo aparecen cuando se pide verificarlas y van marcadas como tales.
- **Convención:** **[V]** significa verificado en una fuente primaria y **[M/S]** significa afirmación de marketing o de fuente secundaria que no se pudo confirmar o que la fuente primaria contradice. Una **[I]** es una inferencia propia para el Agente 1, no un dato de las fuentes.

## Resumen

| Pregunta | Hermes Agent (Nous Research) | OpenClaw |
|---|---|---|
| ¿Qué aprende? | *Skills* (`SKILL.md`) y dos archivos de memoria. No toca pesos | *Learned skills* (Skill Workshop) y memoria Markdown (`MEMORY.md`, notas diarias, *Dreaming*). No toca pesos |
| ¿Se aplica solo? | **Sí, por defecto** (`write_approval: false`) | **Sí, siempre que esté encendido.** Desde 2026.10.5 ya no hay modo «proponer» |
| ¿Puede dejar un diff para revisar? | **Sí:** con `skills.write_approval: true` y `memory.write_approval: true` cada escritura queda pendiente, con `/skills diff <id>` | **No.** Solo admite `auto` (aplica y guarda la versión anterior para deshacer) u `off` |
| ¿Se puede apagar? | Sí: revisión en segundo plano, *nudges*, memoria y *curator* por separado | Sí: `skills.workshop.autonomous.mode: off` y `dreaming.enabled: false` |
| Puertos por defecto | El CLI no abre ninguno. El *gateway* de mensajería, la API (8642) y el *dashboard* (9119) son opcionales | Un *gateway* siempre activo en 18789 (WS + HTTP + Control UI). Escucha en loopback en el host y en `0.0.0.0` dentro de un contenedor |
| Avisos de seguridad | 10 en la GitHub Advisory DB (1 alto). Incidente documentado en junio de 2026 (*dashboards* expuestos) | 722 GHSA publicados desde el 31/01/2026 (14 críticos, 249 altos) |
| ¿«Más liviano»? | Imagen Docker de ≈1,06 GB comprimida | Imagen de ≈0,67 GB comprimida y paquete npm de ≈250 MB. Prende más servicios por defecto y su superficie de ataque es mucho mayor |
| Sin root / CPU / Ollama | Instalación como usuario de servicio: sí. Exige **≥64K de contexto**. Su guía de Ollama recomienda `gemma4:31b` para usar herramientas | Instalación en prefijo local: sí. Ejemplo oficial con `gemma-4-e4b-it` en «modo *lean*». Su revisión de aprendizaje usa un presupuesto de 16K |
| Licencia y madurez | MIT. `v0.22.5` (22/10). 8 releases en octubre. Pre-1.0 | MIT. `2026.10.6` (22/10). 11 estables y 8 betas en octubre |

## 1. Qué aprende y dónde lo guarda

### Hermes Agent

- **[V] *Skills* como «memoria procedimental».** El agente crea, edita y borra sus propias *skills* con la herramienta `skill_manage` (`create`, `patch`, `delete`, `write_file`, `remove_file`). Viven en `~/.hermes/skills/`, que la doc llama «*source of truth*», y la doc aclara: «*The agent can modify or delete any skill*» ([skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), secciones *Skills System* y *Agent-Managed Skills*).
- **[V] Cuándo las escribe.** El *system prompt* le pide guardar un flujo no trivial que resolvió, un camino que funcionó después de errores o una corrección del usuario. Además, **después de cada turno puede correr una «revisión de automejora» en segundo plano**: un *fork* del agente que repasa la conversación y decide si guarda o actualiza memoria o *skills*. Según el código, esas escrituras «*go straight to the memory + skill stores*» ([memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), *Background review*; [agent/background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py), docstring).
- **[V] Memoria.** Son dos archivos en `~/.hermes/memories/`: `MEMORY.md` (2200 caracteres) y `USER.md` (1375). Se inyectan en el *system prompt* como una foto fija al empezar cada sesión, y el agente los edita con la herramienta `memory` ([memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), *How It Works*). A eso se suma `session_search` sobre las conversaciones pasadas y, como opción, proveedores externos de memoria (Honcho, Mem0, etc.).
- **[V] *Curator*.** Es un mantenimiento en segundo plano de las *skills* creadas por el agente. Viene **encendido por defecto**: corre cada 7 días si hubo 2 horas de inactividad, marca como `stale` lo que no se usó en 14 días y archiva lo que no se usó en 30. La consolidación por LLM (fusionar o reescribir *skills*) viene **apagada por defecto** (`curator.consolidate: false`). Nunca borra: archiva en `~/.hermes/skills/.archive/` ([curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md)).
- **[V] Trazabilidad.** Cada cambio sobre una *skill* (del agente, del *curator* o del usuario) agrega una entrada a un *ledger* JSONL de solo agregado (`~/.hermes/skills/.curator_ledger.jsonl`), con actor, acción y **manifiestos `{path, sha256}` de antes y después**, y permite revertir una entrada puntual. La doc aclara que el *ledger* «*is telemetry, never a gate*»: si no se puede escribir, la mutación se aplica igual ([curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md), *Audit ledger*).
- **[V] Pesos.** No cambia pesos en ejecución. Lo único relacionado con entrenamiento es «*batch trajectory generation… for training the next generation of tool-calling models*», una función de investigación *offline* ([README](https://github.com/NousResearch/hermes-agent/blob/main/README.md)).
- **[V] ¿Queda versionado y revisable antes de aplicarse?** Por defecto **no**: «*By default the agent writes skills freely — including from the background self-improvement review*». Lo mismo pasa con la memoria (`memory.write_approval: false`) ([skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), *Gating agent skill writes*).

**Afirmación a verificar: «reescribe las *skills* cada 15 tareas».** **[M/S] No es así.** Lo que existe en la fuente primaria:

- `skills.creation_nudge_interval`: «*Every N tool-calling iterations, remind the model to consider saving a skill*». El ejemplo de configuración trae `15` ([cli-config.yaml.example](https://github.com/NousResearch/hermes-agent/blob/main/cli-config.yaml.example), línea ≈1169), pero el valor por defecto en el código es **10** ([agent/agent_init.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/agent_init.py), `_apply_agent_section`).
- `memory.nudge_interval: 10`, es decir, un recordatorio cada 10 turnos del usuario.
- Estos intervalos regulan cada cuánto se dispara la revisión en segundo plano ([memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), *Same-model review reasoning*). Son **recordatorios para que el modelo considere guardar algo**, contados en iteraciones con herramientas y no en «tareas». Tampoco obligan a reescribir nada.

**[M/S]** El README dice que es «*the only agent with a built-in learning loop*». OpenClaw tiene un ciclo equivalente (sección siguiente), así que la frase es marketing.

### OpenClaw

- **[V] *Learned skills* (Skill Workshop).** El agente guarda un procedimiento después de un trabajo difícil de varios pasos y corrige una *skill* aprendida cuando lo llevó a un error. Una **revisión en segundo plano** corre cada 10 iteraciones del modelo dentro de una sesión. **«*Every change applies immediately, saves the previous version first, and can be undone*»** ([docs/tools/skill-workshop.md](https://github.com/openclaw/openclaw/blob/main/docs/tools/skill-workshop.md) · [docs.openclaw.ai/tools/skill-workshop](https://docs.openclaw.ai/tools/skill-workshop); [docs/tools/self-learning.md](https://github.com/openclaw/openclaw/blob/main/docs/tools/self-learning.md)).
- **[V] Dónde.** En `<state-dir>/agents/<agentId>/agent/workshop-skills/<name>/SKILL.md`, con `.archive/<name>/<versionId>/` (una copia completa antes de cada cambio, y se conservan las 10 últimas). El *feed* de cambios (quién, cuándo, por qué) vive en la base de estado y guarda las 500 últimas entradas por agente.
- **[V] Viene encendido por defecto.** `skills.workshop.autonomous.mode: "auto"`. El modo `off` apaga la revisión en segundo plano y la limpieza, pero el agente igual puede crear o editar *skills* aprendidas si se le pide o con `/learn` (Skill Workshop, *Configuration*).
- **[V] Memoria.** OpenClaw usa Markdown en el *workspace* (`~/.openclaw/workspace`): `USER.md`, `MEMORY.md`, notas diarias `memory/YYYY-MM-DD.md` y `DREAMS.md` ([docs/concepts/memory.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/memory.md)).
- **[V] *Dreaming*.** Es la consolidación de memoria en segundo plano. Está **«*enabled by default*»** y corre como un *cron* gestionado. La fase *deep* **reescribe `MEMORY.md`** guardando antes la versión previa en SQLite y deja un resumen con *highlights* tipo diff en `DREAMS.md`. La doc avisa: «*Transcript text is not secret-masked before ingestion*» ([docs/concepts/dreaming.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/dreaming.md)).
- **[V] Pesos.** La documentación consultada no describe ningún mecanismo de ajuste de pesos. El aprendizaje es de *skills* y memoria en archivos.

## 2. ¿Se puede apagar o encauzar para que proponga en vez de aplicar?

### Hermes: sí, hay un modo de propuesta con diff

- **[V]** Con `skills.write_approval: true`, «*every `skill_manage` write (create / edit / patch / delete / write_file / remove_file) is staged instead of committed*», tanto en turnos en primer plano como en la revisión en segundo plano. Lo pendiente sobrevive a reinicios en `~/.hermes/pending/skills/` y se revisa con `/skills pending`, **`/skills diff <id>` («*full unified diff*»)**, `/skills approve <id>` y `/skills reject <id>` ([skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), *Gating agent skill writes*).
- **[V]** `memory.write_approval: true` hace lo mismo con la memoria: fuera del CLI interactivo las escrituras quedan pendientes (`/memory pending|approve|reject`). Un `patch` o `remove` aprobado se ancla a la entrada exacta que tocaba: si esa entrada cambió mientras tanto, se rechaza ([memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), *Controlling memory writes*).
- **[V] Apagado por partes:**
  - `auxiliary.background_review.enabled: false` (no hay *forks* después de cada turno; `/refine` manual sigue disponible);
  - `memory.nudge_interval: 0` y `skills.creation_nudge_interval: 0`;
  - `memory.memory_enabled: false` y `user_profile_enabled: false` (la herramienta `memory` desaparece);
  - `curator.enabled: false` o `hermes curator pause`.

  Fuentes: memory.md (*Disabling automatic reviews*), curator.md (*Disabling per environment*).
- **[V] Para encauzar escrituras a un repositorio,** `skills.create_dir` redirige las *skills* nuevas a otro directorio, y la doc menciona como ejemplo «*a git-tracked repo*». Ojo: **los directorios externos no son una barrera de escritura**. Si el proceso puede escribir ahí, el agente puede modificarlos (skills.md, *External Skill Directories*). Las *skills* de proyecto (`.hermes/skills` dentro de un repo confiable) el *curator* no las toca nunca.
- **[V] Límite importante:** `/skills approve` **aplica el cambio en el host**. No genera un PR ni un corte de versión. El diff existe, pero el circuito de aprobación es el de Hermes y no el del repo.

### OpenClaw: hoy no hay modo «proponer»

- **[V]** Las notas de release muestran el retroceso:
  1. 2026.7.1: «*Skills created by agents now remain pending for Skill Workshop review and approval instead of becoming active immediately*» ([CHANGELOG/2026.7.1.md](https://github.com/openclaw/openclaw/blob/main/CHANGELOG/2026.7.1.md), PR #98346).
  2. 2026.8.1: aplicar automáticamente pasa a ser el comportamiento por defecto y la aprobación queda como opción con `skills.workshop.approvalPolicy: "pending"` ([CHANGELOG/2026.8.1.md](https://github.com/openclaw/openclaw/blob/main/CHANGELOG/2026.8.1.md), #115576 y #107690).
  3. **2026.10.5 (18/10/2026):** «*Skill Workshop saves learned procedures directly, with change history, saved versions and Undo*» y «*The Workshop migration retires approval-first settings; … older proposal modes move to Off*» ([CHANGELOG/2026.10.5.md](https://github.com/openclaw/openclaw/blob/main/CHANGELOG/2026.10.5.md), #161057 y #167641).
- **[V]** La doc vigente lo confirma: «*Earlier releases staged learned skills as drafts for review. `openclaw doctor --fix` exports any pending drafts and removes the old settings*». Los métodos `skills.proposals.*` siguen registrados, pero devuelven un error (Skill Workshop, *Upgrading from earlier releases*).
- **[V]** Lo que sí ofrece: deshacer por revisión (`/learn undo <id>`, botón *Undo*) o por *skill* (`openclaw skills workshop restore`), historial con comparación entre versiones en la Control UI y el *hook* `skill_changed`, que **observa** cada cambio ya aplicado. Es control *a posteriori*, no previo.
- **[V]** `skills.workshop.autonomous.mode: off` apaga la revisión automática, y *Dreaming* se apaga con `plugins.entries.memory-core.config.dreaming.enabled: false`. En sesiones con *sandbox* el agente no recibe la herramienta `skill_workshop`.

## 3. Huella y seguridad

### Qué instala y qué abre

| | Hermes | OpenClaw |
|---|---|---|
| Runtime | Python 3.14 gestionado (uv con versión fijada) más un Node.js gestionado, que necesita `libatomic` en glibc ([installation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md)). 46 dependencias directas en `pyproject.toml` y extras opcionales por canal o herramienta | Node ≥24.22.1 (o ≥26.12.1) según `engines`. El paquete npm `openclaw@2026.10.6` pesa ≈249,5 MB descomprimido y tiene 66 dependencias directas ([registry.npmjs.org/openclaw](https://registry.npmjs.org/openclaw/latest)) |
| Imagen Docker (comprimida, amd64, 22–23/10) | `nousresearch/hermes-agent:stable`: ≈1059 MB | `openclaw/openclaw:latest`: ≈673 MB (la variante `slim` publica el mismo tamaño) |
| Procesos y puertos por defecto | El CLI no abre puertos. El *gateway* de mensajería sale hacia las plataformas (Telegram, etc.). La API compatible con OpenAI (8642) exige `API_SERVER_ENABLED=true` y el *dashboard* usa 9119; los dos son opcionales ([docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md)) | **Un proceso *gateway* siempre activo** con un único puerto multiplexado (18789): WebSocket de control y RPC, APIs HTTP (`/v1/chat/completions`, `/v1/responses`, `/tools/invoke`…), Control UI y *hooks*. Escucha en `loopback` en el host y en `auto` (`0.0.0.0`) dentro de un contenedor ([docs/gateway/index.md](https://github.com/openclaw/openclaw/blob/main/docs/gateway/index.md)) |
| Encendido por defecto | Memoria, revisión en segundo plano y *curator* (solo poda) | Self-learning (`auto`), *Dreaming* (*cron*) y el *gateway* con canales |
| Autenticación | Allowlists por plataforma; si no hay ninguna configurada, «*all users are denied*». Emparejamiento por código para DMs. El *dashboard* en una dirección que no es loopback **falla cerrado** si no hay un proveedor de autenticación ([security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md), *User Authorization*; docker.md) | «*Auth is required by default*», con token o *password* compartidos (el asistente de instalación genera un token) o `trusted-proxy`. Existe `gateway.auth.mode: "none"`, explícito y fuera del asistente, «*only for trusted local loopback setups*» ([docs/gateway/config-gateway.md](https://github.com/openclaw/openclaw/blob/main/docs/gateway/config-gateway.md)) |

**¿OpenClaw es «más liviano»?** **[V] Depende de qué se mida.** En bytes, sí: su imagen comprimida pesa ≈0,67 GB contra ≈1,06 GB de Hermes. En lo que queda corriendo y expuesto, no: OpenClaw siempre levanta un *gateway* residente con APIs HTTP y WebSocket, el autoaprendizaje, un *cron* de *Dreaming* y decenas de integraciones de canal. Hermes puede usarse como CLI sin ningún puerto abierto. **[I]** Para el Agente 1, que no necesita canales de chat ni un plano de control remoto, la superficie que importa es la segunda.

### Modelo de confianza declarado

- **[V] Hermes:** «*The only security boundary against an adversarial LLM is the operating system. Nothing inside the agent process constitutes containment — not the approval gate, not output redaction, not any pattern scanner, not any tool allowlist*». Lo soportado para producción o para contenido no confiable es envolver todo el proceso (su propio Docker o NVIDIA OpenShell). El *backend* por defecto ejecuta comandos directamente en el host ([SECURITY.md](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md), §2.2). Aprobación de comandos peligrosos: `approvals.mode: smart` por defecto (un LLM auxiliar evalúa el riesgo) y `cron_mode: deny`.
- **[V] OpenClaw:** «*One trust boundary per gateway… not a hostile multi-tenant security boundary*». Las imágenes de contenedor exponen por defecto (*exposed bind*) y la doc pide combinarlas con autenticación ([docs/gateway/security/index.md](https://github.com/openclaw/openclaw/blob/main/docs/gateway/security/index.md)).

### Incidentes y avisos conocidos

- **[V] OpenClaw: 722 avisos GHSA** publicados en el repositorio entre el 31/01/2026 y el 11/09/2026 (14 críticos, 249 altos, 390 medios y 69 bajos), consultados con la API de GitHub Security Advisories el 23/10. Algunos ejemplos de primera mano:
  - [GHSA-g8p2-7wf7-98mq](https://github.com/openclaw/openclaw/security/advisories/GHSA-g8p2-7wf7-98mq) (alto, CVSS 8,8, versiones ≤2026.1.28, paquete `clawdbot`): la Control UI aceptaba `gatewayUrl` desde la URL y enviaba el token del *gateway*. «*1-click RCE… exploitable even on instances configured to listen on loopback only*».
  - `GHSA-g55j-c2v4-pjcg` (CVE-2026-25593): «*Unauthenticated Local RCE via WebSocket config.apply*».
  - Varios críticos de escalada a `operator.admin` y RCE en nodos (marzo de 2026), entre ellos `GHSA-4jpw-hj22-2xmc` y `GHSA-hf68-49fm-59cq`.
  - Relacionados con *skills*: `GHSA-qrq5-wjgg-rvqw` (crítico, «*Path Traversal in Plugin Installation*»), `GHSA-3vvq-q2qc-7rmp` (alto, «*ClawHub package downloads are not enforced with integrity verification*»), `GHSA-cqwv-9qjx-vxw2` («*Skill Workshop apply flow could override pending approval*») y `GHSA-7cp7-87pj-p32v` (alto, «*Skill tool dispatch could skip owner-only policy*»).
  - **[M/S]** Un blog cita «CVE-2026-25253». El GHSA más parecido (g8p2) no trae CVE asignado en la API, así que esa correspondencia no está verificada.
- **[V] ClawHub (el *marketplace*).** El modelo de amenazas oficial describe moderación con patrones estáticos y casi AST, más revisión por LLM y VirusTotal, y reconoce que estas dos últimas «*depend on operator-side API keys/config being enabled*» y que «***No runtime execution sandbox isolates a skill from the agent's own privileges once installed***» ([docs/security/THREAT-MODEL-ATLAS.md](https://github.com/openclaw/openclaw/blob/main/docs/security/THREAT-MODEL-ATLAS.md), §4). Hermes también busca en ClawHub desde su Skills Hub (skills.md, *Skills Hub*).
- **[M/S] «Más de 17.000 *skills* en ClawHub».** No se pudo verificar en una fuente primaria. La página de [clawhub.ai](https://clawhub.ai/) no publica un total coherente y otro listado secundario dice 10.700.
- **[V/S] Preprints.** *ClawdPwned: Malicious Instructions in the OpenClaw AI Agent Skills repository* (A. Krishna, póster del *workshop* «Agents in the Wild», ICLR 2026, [ficha](https://iclr.cc/virtual/2026/10016269)) audita 2556 *skills* contra OWASP LLM Top 10 y marca 49 como probablemente maliciosas. El mecanismo más común es la divulgación de información sensible (92,4 %). Las cifras de campañas (*ClawHavoc*: 341 o 1184 paquetes maliciosos según la fuente) solo aparecen en blogs y no se verificaron.
- **[V] Hermes.** La GitHub Advisory DB lista 10 avisos para `hermes-agent` (1 alto, 6 medios, 3 bajos; mayo y junio de 2026), entre ellos [GHSA-4pqm-j46f-795x](https://github.com/advisories/GHSA-4pqm-j46f-795x) (*DNS rebinding* en WebSockets) y GHSA-99f9-j8r3-p853 (archivos con permisos 0644). La propia doc documenta un incidente: «*An unauthenticated public dashboard was the entry point for the June 2026 MCP-config persistence campaign: internet scanners reached exposed dashboards … and drove the agent into planting an SSH-key backdoor*». Desde entonces la autenticación es obligatoria en cualquier dirección que no sea loopback (docker.md).
- **[I]** Comparar la cantidad de avisos entre proyectos tiene un sesgo: OpenClaw publica cada hallazgo como GHSA y su superficie (decenas de canales, nodos, apps móviles) es mucho mayor. Aun así, la diferencia de órdenes de magnitud y la concentración en autenticación del *gateway* son datos.

## 4. Requisitos de host (labredesfie: Xeon E-2224G de 4 núcleos, 31 GB, sin GPU, sin sudo)

Referencia medida en este host (evidencia `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`): con `llama3.1:8b` en CPU, ≈22 tokens/s de procesamiento de prompt y 5–10 tokens/s de generación, con prompts de hasta ≈1200 tokens. El servidor tiene Docker instalado (lo usa el laboratorio), pero el usuario del proyecto no tiene sudo, así que no hay que contar con poder usar el *daemon*.

### Hermes

- **[V] Sin root:** hay un camino documentado de instalación como usuario de servicio, con un único paquete de sistema (`libatomic`) que instala un administrador si falta, y `loginctl enable-linger` para un servicio de usuario ([installation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md), *Non-Sudo / System Service User Installs*). La doc de seguridad pide «*Run as non-root*».
- **[V] Contenedor:** hay una imagen oficial (≈1 GB comprimida). Como *backend* de terminal Docker, los contenedores corren como root salvo `terminal.docker_run_as_host_user` (configuration.md). Depende de tener acceso a Docker o Podman sin root.
- **[V] Ollama:** `provider: ollama` con `base_url` local está soportado (configuration.md). **El mínimo de contexto es de 64.000 tokens**: «*Hermes requires at least 64,000 tokens for agentic work with tools*» ([local-ollama-setup.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/local-ollama-setup.md)), y está fijado en código (`MINIMUM_CONTEXT_LENGTH = 64_000` en [agent/model_metadata.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/model_metadata.py)). La guía de Ollama lista como requisitos mínimos 4 núcleos y 8 GB, sin GPU. Para trabajo con herramientas recomienda `gemma4:31b` («*only model with reliable tool calling*» en su tabla) y no menciona `gemma4:e4b`.
- **[I]** Con `gemma4:e4b` en este host hay dos riesgos sin medir: (a) que el modelo chico no use las herramientas con fiabilidad, y la propia doc de Hermes advierte que los modelos chicos «*misjudge what they learned*»; (b) la latencia del prompt frío. Ejemplo aritmético con la velocidad medida del 8b: cada 10.000 tokens de prompt sin caché son ≈7–8 minutos. El e4b es más chico y probablemente más rápido, pero no está medido con prompts de agente. Hermes además corre la revisión de aprendizaje con el mismo modelo, salvo que se configure otro.

### OpenClaw

- **[V] Sin root:** hay un instalador en prefijo local (`install-cli.sh`) que deja Node y OpenClaw bajo `~/.openclaw` sin un Node del sistema ([docs/install/index.md](https://github.com/openclaw/openclaw/blob/main/docs/install/index.md)), y el servicio va como `systemctl --user`. La doc dice que correr el *gateway* y sus comandos como root es «*unsafe and unsupported*» (gateway/index.md).
- **[V] Contenedor:** hay imágenes oficiales (`ghcr.io/openclaw/openclaw`, espejo en Docker Hub) y una página de Podman sin root. Construir la imagen desde el código pide ≥6 GB de RAM; las imágenes publicadas no lo necesitan ([docs/install/docker.md](https://github.com/openclaw/openclaw/blob/main/docs/install/docker.md)).
- **[V] Ollama y modelos chicos:** Ollama es un proveedor soportado. Las recetas propias de llama.cpp usan 64K de contexto, con un piso de 8 GiB. Para backends locales activa por defecto *Tool Search*, que difiere los *schemas* de herramientas, y ofrece `localModelLean` para recortar herramientas. Su ejemplo de configuración usa justamente `lmstudio/gemma-4-e4b-it` ([docs/gateway/local-models.md](https://github.com/openclaw/openclaw/blob/main/docs/gateway/local-models.md)). La revisión de aprendizaje usa un presupuesto de 16.384 tokens, hasta 2048 de salida y un máximo de 2 minutos (self-learning.md). **[I]** En este host, ese tope de 2 minutos con un prompt de ≈16K tokens probablemente no alcance.

## 5. Licencia y madurez

| | Hermes Agent | OpenClaw |
|---|---|---|
| Licencia | MIT (API de GitHub) | MIT (API de GitHub) |
| Repositorio | `NousResearch/hermes-agent`, Python, creado el 22/07/2025, ≈256 mil estrellas | `openclaw/openclaw`, TypeScript, creado el 24/11/2025, ≈393 mil estrellas |
| Última estable | [v0.22.5](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.5) (22/10/2026). La nota dice: «*rolls up the ~81 PRs merged since v0.22.4*» y «*231 non-merge commits across 804 changed files*» en una semana | [v2026.10.6](https://github.com/openclaw/openclaw/releases/tag/v2026.10.6) (22/10/2026). Hay canal beta (`2026.10.10-beta.3`) y `extended-stable` |
| Cadencia (octubre de 2026) | 8 releases (v0.21.6 → v0.22.5). Pasó de etiquetas por fecha (`v2026.9.24`) a semver **0.x** a principios de octubre | 11 releases estables (contando mantenimiento de líneas viejas) y 8 betas |
| Señales de estabilidad | Pre-1.0. Las notas de 0.22.5 difieren la documentación curada a 0.23.0 | Cambios de comportamiento entre versiones menores: la aprobación previa de *skills* se agregó (julio), se volvió opcional (agosto) y se eliminó (octubre) en tres meses |

**[I]** Ninguno de los dos ofrece una línea estable con soporte largo que se pueda fijar por un cuatrimestre sin quedar atrás en parches de seguridad. OpenClaw tiene `extended-stable`, pero no se revisó su política de soporte.

## Implicancias para el Agente 1

Lo que rige hoy (ver [#66](https://github.com/SpendIce/Proyecto-Final/issues/66), [#92](https://github.com/SpendIce/Proyecto-Final/issues/92), ADR 0010 y `CONTEXT.md`):

- un **cambio controlado** (código, prompts, parámetros, criterios, contratos) solo entra en operación aprobado por el dueño de su clase, con un PR y un corte de versión;
- el manifest guarda el sha256 de todo lo controlado y el agente **no arranca** si algo difiere;
- un **dato operativo** lo mantiene su dueño institucional y el agente solo lo lee;
- nada sale sin validación humana;
- LangGraph y FastAPI están diferidos hasta que una necesidad operativa lo justifique.

### Qué choca y qué es compatible

- **[I] Choca de raíz:** cualquier escritura del agente, en ejecución, sobre algo que cambia lo que redacta. Eso incluye *skills* aprendidas, `MEMORY.md`, *Dreaming*, la revisión en segundo plano y el *curator* con consolidación. No es un dato operativo, porque lo escribe el propio agente y no un dueño institucional. Por definición es un cambio controlado hecho por fuera del circuito. Hay dos casos:
  - Si esos archivos quedan dentro del manifest, el primer aprendizaje hace que el agente no arranque. El *fail-closed* funciona, pero el aprendizaje queda inútil.
  - Si quedan fuera, se reabre exactamente el hueco que ADR 0010 cerró: un prompt efectivo distinto, sin PR, sin regresión y sin que la auditoría registre de qué salió la pieza.
- **[I] También choca:** la aprobación integrada de Hermes (`/skills approve`) y el *Undo* de OpenClaw. Las dos son aprobaciones o reversiones **en el host**, sin corte de versión. El ADR descarta expresamente «probar algo en caliente».
- **[I] Compatible con condiciones:**
  - El **modo de propuesta de Hermes** (`skills.write_approval: true` + `memory.write_approval: true`) como **generador de diffs**, siempre que el diff salga del host y entre por el circuito normal (PR → revisión del dueño de la clase → nueva `PROMPT_VERSION` → manifest nuevo), y que nadie use `/skills approve` en producción. OpenClaw **no** tiene un equivalente en la versión vigente.
  - El *ledger* de Hermes con manifiestos sha256 por archivo es conceptualmente afín al manifest del Agente 1, pero es telemetría que no frena nada y vive en el host. No reemplaza la verificación de ADR 0010.
  - El **formato `SKILL.md`** (estándar agentskills.io, que usan los dos) se puede tomar como formato de documento sin adoptar ningún runtime.
- **[I] Sin relación con la validación humana:** ningún mecanismo de aprendizaje de los dos toca la validación de piezas por la SEU. Esa regla no se gana ni se pierde con ellos, pero su modelo de ejecución (agente con terminal, herramientas y canales) es mucho más amplio que el pipeline acotado del Agente 1. Adoptar cualquiera de los dos sería además un cambio de arquitectura del mismo tamaño que el que se difirió con LangGraph y FastAPI.

### Forma mínima de «aprender sin reintentos» que no rompe el manifest

**[I]** La idea útil de los dos sistemas es convertir correcciones repetidas en una instrucción persistente para no repetir el error. Se puede conservar moviendo el aprendizaje **entre versiones** en lugar de **dentro de la corrida**:

1. **Captura (en ejecución, solo lectura de lo controlado).** El pipeline ya registra en la auditoría los códigos de rechazo de los *gates* (`source_fact_in_creative_field`, `unauthorized_fact_claim`, etc.) y las decisiones y ediciones de la validación humana. Esos registros son la materia prima, equivalente al *transcript* que repasan Hermes y OpenClaw. No se escribe nada controlado.
2. **Propuesta (fuera de línea, fuera del host de operación).** Un comando, determinístico o asistido por LLM, agrupa rechazos y ediciones repetidas y **escribe una propuesta como diff** contra el prompt, los ejemplos o la regla del *gate* en el repo. Es lo mismo que hace `write_approval` de Hermes, pero con un PR en lugar de `~/.hermes/pending/`.
3. **Aprobación por el circuito vigente.** El dueño de la clase revisa el PR (la SEU si es un criterio de contenido, el responsable técnico si es prompt o código). Al mergearlo se sube `PROMPT_VERSION`, se corre la regresión y se corta una versión con su manifest nuevo.
4. **Efecto.** La corrida siguiente arranca con la versión nueva verificada y no repite el error sin necesidad de reintentar en caliente. Si la lección resultó mala, se vuelve a la versión anterior, que es lo que ADR 0010 ya prevé.

Así el agente nunca se modifica a sí mismo: el manifest sigue cubriendo todo lo que define su comportamiento, la auditoría sigue pudiendo atribuir cada pieza a una versión y la validación humana no cambia. El costo es la latencia de un ciclo de PR por lección, que es justamente el control que se eligió.

## Preguntas abiertas para #145

- ¿Hay alguna lección que deba aplicarse más rápido que un ciclo de PR? Si la hay, ¿cabe en la definición de cambio de emergencia (suspender, no corregir en caliente)?
- ¿El paso de propuesta (2) se hace con un script propio sobre la auditoría o se usa Hermes en modo propuesta en una máquina de desarrollo, sin acceso a producción, solo como generador de diffs?
- Si en algún momento se evalúa ejecutar alguno de los dos en `labredesfie`, falta medir la latencia de un turno de agente con `gemma4:e4b` y el contexto mínimo (64K en Hermes) antes de discutir más.
