# Manual de operación del Agente 1

- **Estado:** vigente para la versión `0.1.0`; se actualiza con cada versión
  etiquetada.
- **Alcance:** operar el Agente 1 después del traspaso: puesta en marcha,
  credenciales, incidentes, diagnóstico, control de cambios, políticas, SLO y
  SLA.
- **Decidido en:** traspaso del Agente 1 a Informática (issue #63, ADR 0007),
  SLO/SLA y políticas (issue #65), control de cambios (issue #66), modelo de
  seguridad de la cuenta Google (issue #64).
- **Fuente única:** este archivo. El PDF que se adjunta al acta y a la versión
  etiquetada se regenera con `scripts/renderizar-artefactos.sh manual` y **no se
  versiona** (política de artefactos del repositorio).

## Cómo leer este manual

Está escrito para **el operador designado**: la persona que la Dirección de la
carrera designe en el acta de traspaso (issue #63, ADR 0007). No supone quién
es, no supone que escribió el código y no deja ningún contacto personal como
referencia: los nombres y los contactos quedan en el acta de traspaso.

El manual **no repite** lo que ya está decidido en otro lugar; lo enlaza:

| Tema | Documento vigente |
|---|---|
| Decisiones de seguridad de la cuenta Google y de la credencial | `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`; ADR 0011 |
| Cómo se corta una versión y qué lleva el manifest | `PROCEDIMIENTO-CORTE-DE-VERSION.md` |
| Cómo se revierte el esquema de la base | `Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md` |
| Scheduler y Workspace, paso a paso | `Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md` y `.../Runbook-Workspace-D2-D3-Agente-1.md` |
| Historia de las versiones y de los cambios de configuración | `CHANGELOG.md` |
| Vocabulario del proyecto (versión del agente, cambio controlado, ventana de operación, retención acotada, etc.) | `CONTEXT.md` |
| Lo que Google ya documenta | Se enlaza en el modelo de seguridad; no se reescribe acá |

---

## 1. Los tres responsables y qué decide cada uno

El traspaso reparte el Agente 1 en tres responsables (issue #63, ADR 0007). La
administración del Workspace —recuperación, revocación y suspensión de la cuenta
técnica— queda del área de servicios informáticos (DSI) en cualquier caso, sin
ser por eso responsable de la operación.

| Responsable | Quién es | Qué decide |
|---|---|---|
| **Responsable de operación** | La Dirección de la carrera de Ingeniería en Informática, que designa un **operador** en el acta de traspaso. Puede delegar la ejecución en DSI; si lo hace, el operador designado es DSI y nada del diseño cambia. | Que el Agente 1 siga funcionando, quién lo ejecuta, la puesta en marcha, el soporte dentro de la ventana de operación y el cumplimiento del SLA. |
| **Dueño funcional** | La Secretaría de Extensión Universitaria (SEU). | El contenido y la autorización de lo que el agente produce: plantillas aprobadas, padrón de roles, lista de cierre y quién aprueba cada pieza. También los criterios de contenido y sumar una cuenta suplantable a la lista cerrada. |
| **Responsable de evolución** | Los alumnos de Ingeniería en Informática que continúan el P100. | El código y las historias de usuario: los cambios controlados de código, prompts y contratos, con la revisión de los dueños de cada clase. |
| **DSI** (no decide sobre el P100; administra el Workspace) | El área de servicios informáticos de la FIE. | La cuenta técnica, el proyecto de Google Cloud y la cuenta de servicio: recuperación, rotación y revocación de la clave, suspensión y rehabilitación de la cuenta, unidad compartida, alertas y aprobación de los cambios que se le piden en la consola de Google. |

**Regla de decisión ante un incidente de credencial:** DSI y el operador deciden
juntos la reanudación; ninguno de los dos rehabilita por su cuenta (modelo de
seguridad §7).

---

## 2. Puesta en marcha en una máquina limpia

"Puesta en marcha" es poner el Agente 1 a operar en un host que no lo tuvo
nunca, siguiendo sólo este manual. La prueba de que el sistema está "listo para
operar" es exactamente esa: alguien que no escribió el código lo pone en marcha
con este documento (issue #63).

### 2.1 Requisitos del host

| Requisito | Detalle |
|---|---|
| Sistema | Linux con `systemd --user` para el disparo por timer, o cualquier host con `sleep` para el disparo por bucle (`--loop`). |
| Python | `>=3.11` (lo fija `pyproject.toml`). |
| Gestor de dependencias | `uv`, con el `uv.lock` versionado. `uv sync --frozen` reconstruye el entorno exacto. |
| `openssl` | El binario del host firma el *assertion* JWT de la cuenta de servicio. Si falta, el agente se detiene con `workspace_auth_signing_unavailable` (fail-closed). |
| Modelo local | Un servidor Ollama en loopback (`http://127.0.0.1:11434` por omisión) con el modelo descargado. El generador sólo acepta loopback: no hay API de LLM externa. |
| Salida a Internet | Sólo hacia `oauth2.googleapis.com` (intercambio de credencial), `sheets.googleapis.com`, `docs.googleapis.com`, `www.googleapis.com` (Drive), `gmail.googleapis.com` y las descargas de Ollama. |
| PostgreSQL | Sólo para verificar las migraciones (`down`). No es necesario para operar. |

El **modelo concreto** no lo fija el repositorio: es configuración
(`--ollama-model` / `OLLAMA_MODEL`). Cambiarlo es un cambio controlado de la
clase «prompts y parámetros de inferencia» (§9). La evidencia histórica midió
`llama3.2:3b` y `llama3.1:8b`; el modelo que se elija para operar es decisión
del dueño técnico de esa clase, no de este manual.

### 2.2 Pasos

1. **Traer la versión.** Clonar el checkout del tag etiquetado
   (`agente1-vX.Y.Z`) con su `manifest-version.json`. El manifest viaja con la
   versión: no se regenera en el host. El detalle está en
   `PROCEDIMIENTO-CORTE-DE-VERSION.md` §7.
2. **Instalar dependencias.**
   ```bash
   cd <CHECKOUT>/Implementacion/Agente1
   uv sync --frozen
   ```
3. **Levantar el modelo local.** Instalar Ollama (runtime local, fuera del
   repo), iniciarlo y descargar el modelo elegido:
   ```bash
   OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama serve   # ejemplo user-local
   OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama pull <modelo>
   ```
4. **Provisionar la identidad y la configuración fuera del repo** (§2.3). Sin
   esto el modo operación no arranca.
5. **Verificar el camino manual antes del automático.** Primero offline, después
   live (doble opt-in):
   ```bash
   PYTHONPATH=src python -m agente1 insumos-agentes \
     --tabla insumos.csv --directorio salida/insumos --fake-output "salida"

   PYTHONPATH=src python -m agente1 insumos-agentes \
     --directorio ~/agente1/salida --live --confirm-write-workspace --ollama-model <modelo>
   ```
6. **Instalar el scheduler.** Copiar las plantillas de `systemd/`, reemplazar
   `__CHECKOUT__` y `__MODELO_OLLAMA__`, y habilitar el timer (o el bucle). El
   paso a paso está en
   `Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md` §7.
   ```bash
   mkdir -p ~/.config/systemd/user
   cp systemd/agente1-scheduler.{service,timer} ~/.config/systemd/user/
   $EDITOR ~/.config/systemd/user/agente1-scheduler.service   # __CHECKOUT__ y __MODELO_OLLAMA__
   systemctl --user daemon-reload
   systemctl --user enable --now agente1-scheduler.timer
   loginctl enable-linger "$USER"    # para que corra sin sesión iniciada
   ```

**Paso en vivo de integridad (ADR 0010).** Con el host en modo operación
(`--live`), el agente verifica el árbol contra el manifest antes de tocar la
red. Si un archivo controlado no coincide, no arranca (código de salida 2) y
deja el motivo en `logs/integridad-arranque.jsonl`. Es el comportamiento
buscado, no una falla (§9).

### 2.3 Configuración fuera del repo

El repositorio **nunca** guarda secretos: guarda referencias. Todo lo que
depende del ambiente vive en archivos de entorno fuera del repo, con permisos
restringidos (`chmod 600`), y se inyecta por variables de entorno.

| Qué | Dónde | Contenido |
|---|---|---|
| Clave JSON de la cuenta de servicio | `~/.config/agente1/` (o la gestión de secretos de la facultad después del traspaso) | El secreto con el que el agente obtiene su token. Ruta en `AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY`. |
| Env de Workspace | `~/.config/agente1/workspace-d2.env` | `AGENTE1_WORKSPACE_*` (ambiente, IDs de planilla/carpeta/plantilla, rango, timeout, cuenta por la que se hace pasar). |
| Env del scheduler | `~/.config/agente1/scheduler.env` | `AGENTE1_SCHEDULER_*`, `AGENTE1_INSUMOS_RANGO_A1`, `AGENTE1_RESPALDO_*` y las `AGENTE1_WORKSPACE_*`. |
| Padrón de roles | Fuera del repo, ruta en `AGENTE1_PADRON_ROLES_PATH` | Identidad y rol por persona, mantenido por la SEU (ADR 0005). |
| Datos operativos | Planillas de Google del ambiente | Planilla de actividades, respuestas de Forms, novedades de pago. Los mantiene su dueño; no son configuración del agente. |

La lista completa de variables por subsistema está en los runbooks de
`Documentos/PlanDespliegue/`. Las variables del prefijo `AGENTE1_*` que no se
reconocen o llegan vacías hacen fallar el arranque con un código propio
(`workspace_config_unknown_key`, `scheduler_config_unknown_key`,
`insumos_config_unknown_key`, `respaldo_config_unknown_key`): la configuración
que corre es la que está escrita, no un default silencioso.

### 2.4 Verificación de la puesta en marcha

| Verificación | Comando o señal |
|---|---|
| Suite y linter verdes | `uv run pytest -q` y `uv run ruff check .` |
| Smoke local de punta a punta | `bash scripts/smoke.sh` |
| Smoke opt-in contra Ollama | `bash scripts/smoke_ollama.sh` (Ollama ya iniciado, modelo descargado) |
| Integridad del arranque | El primer `--live` asienta `resultado: PASS` en `logs/integridad-arranque.jsonl`. |
| El scheduler corre | Una línea `resultado: "completada"` en `logs/scheduler-corridas.jsonl` dentro de la ventana. |
| El token se emite y se audita | Una línea en `logs/cuenta-suplantada.jsonl` por token pedido. |
| Reportes operativos | `scripts/operaciones_seguras.py health\|reconcile\|consolidate\|retention` (dry-run, no modifican nada). |

---

## 3. Credenciales

La política completa y su fundamento están en
`docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md` (§2, §4 y §7) y en
ADR 0011. Acá se resume **dónde vive cada credencial, cómo se rota y quién
puede hacerlo**, para que se rote sin depender de quien escribió el código.

### 3.1 Dónde vive cada credencial

| Credencial | Dónde vive | Para qué sirve |
|---|---|---|
| **Clave JSON de la cuenta de servicio** (secreto principal) | Hasta el traspaso, en `~/.config/agente1/` con `chmod 600`, fuera del repo y en un host con disco cifrado. Después del traspaso, en la gestión de secretos de la facultad (DSI-G2). La ruta la lee el agente desde `AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY`; nunca entra a los logs, a las excepciones ni a la configuración visible. | Firmar el *assertion* JWT con el que el agente se hace pasar por una cuenta de la lista cerrada. |
| **Cuenta por la que se hace pasar** | `AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT`. Debe estar en la lista cerrada `src/agente1/contracts/cuentas_suplantables_v1.json` (hash de cada dirección, sin la dirección en claro). | Indicar por quién actúa el agente. Hoy la lista tiene sólo a la cuenta técnica. |
| **Contraseña de la cuenta técnica** | No se custodia: en el acta DSI la resetea y no se la da a nadie. Nadie inicia sesión con esa cuenta para operar. | — |
| **Segundo factor (2SV) de la cuenta técnica** | *Previsto – no implementado.* No hay llave física en el alcance actual. | — |
| **Recuperación de la cuenta del agente** | No es un secreto. DSI la configura en la propia cuenta del agente (DSI-A5). | Recuperar el acceso a la cuenta si se pierde. |
| **Refresh token y client secret OAuth** (credencial anterior) | El trío `AGENTE1_WORKSPACE_OAUTH_{CLIENT_ID,CLIENT_SECRET,REFRESH_TOKEN}` es un **respaldo explícito**, no silencioso: un par de cuenta de servicio a medio configurar falla, no cae a OAuth. | Acceso de respaldo mientras la cuenta de servicio no esté instalada en vivo. |
| **Destinatarios de prueba de Gmail** | `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`. Corresponde a la lista cercada de prueba. | Limitar todo envío real a direcciones declaradas. |

El agente pide los tres scopes autorizados en la delegación (`drive`,
`gmail.send`, `gmail.readonly`) y **sólo puede hacerse pasar por cuentas de la
lista cerrada**: si el entorno indica otra, no arranca con
`workspace_impersonation_not_allowed` (ADR 0011).

La cuenta del agente tiene **50 GB** de espacio (DSI-R5); ahí viven, entre
otros, los respaldos diarios hasta que la retención de 30 días los borra
(ADR 0009).

### 3.2 Cómo se rota cada credencial

**Clave de la cuenta de servicio** — la rota **el responsable de DSI**, porque
el proyecto de Google Cloud es suyo (ADR 0011). Sin rotación periódica: se rota
en el acta de traspaso y ante un incidente.

1. El operador o el responsable técnico pide la rotación al responsable de DSI.
2. DSI crea una clave nueva en el proyecto de Google Cloud y borra la anterior
   (Google documenta el procedimiento: *best-practices-for-managing-service-account-keys*).
3. La clave nueva se deja en la ruta de custodia (§3.1) con `chmod 600` y se
   actualiza `AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY` si cambió de nombre.
4. Reiniciar el scheduler y confirmar una corrida `completada`: el agente pide
   un token nuevo en cada operación, así que la clave nueva entra sin reinicio
   de estado.
5. Anotar el cambio en la sección *Configuración* de `CHANGELOG.md` con fecha,
   motivo y quién lo aprobó (§9).

**Contraseña de la cuenta técnica** — la resetea **DSI**, en el acta y ante un
incidente, sin dársela a nadie (modelo de seguridad §2). No hay rotación de
rutina.

**Refresh token y client secret OAuth** — los rota el **operador** en el acta:
revoca el refresh token y genera un client secret nuevo, y se prueba que el
sistema funciona con las credenciales anteriores ya revocadas (ADR 0007). El
trío queda dado de baja definitivamente cuando la cuenta de servicio funciona en
vivo (issue #99).

**Lista cerrada de cuentas suplantables** — no es un secreto; es un archivo
controlado del repo dentro del manifest. Sumar una cuenta es un cambio
controlado que **aprueba la SEU** como dueña funcional (ADR 0011), con el hash
de la dirección normalizada.

### 3.3 Quién puede rotar

| Credencial | Quién la rota |
|---|---|
| Clave de la cuenta de servicio | Responsable de DSI (proyecto de Google Cloud). |
| Contraseña de la cuenta técnica | DSI, en el acta y ante incidente. |
| Refresh token / client secret OAuth | Operador designado, en el acta. |
| Lista cerrada de cuentas suplantables | SEU (dueño funcional), por el circuito de cambio controlado. |

Ninguna de estas rotaciones requiere a quien escribió el código: la clave se
pide al rol de DSI y la lista cerrada se cambia por el circuito normal.

---

## 4. Revocación y suspensión ante un incidente

Sólo hay **dos casos de emergencia** (issue #66): una **credencial comprometida**
o una **pieza enviada o emitida por error**. En ambos, la respuesta es
**suspender el agente, no corregirlo en caliente** (cambio de emergencia,
`CONTEXT.md`). El arreglo vuelve por el circuito normal.

**Qué hace el operador, del lado del agente:**

```bash
systemctl --user disable --now agente1-scheduler.timer   # detener las corridas
# y revocar el token vigente de la identidad (§3.2)
```

No se edita nada en el host para "arreglarlo": un archivo controlado editado a
mano hace que el agente no arranque (ADR 0010) y deja la pieza fuera de
trazabilidad.

**Qué hace DSI:**

- **Contención:** bloquea la cuenta técnica desde la alerta (DSI-D3). Con la
  cuenta suspendida, la cuenta de servicio no puede hacerse pasar por ella. Si
  se sospecha de la clave, DSI la deshabilita o la borra.
- **Reanudación (decisión conjunta con el operador):**
  1. DSI rehabilita la cuenta (DSI-D4).
  2. DSI rota la clave y resetea la contraseña de la cuenta técnica.
  3. El operador corre el smoke en vivo.
  4. El cambio queda en `CHANGELOG.md` como **cambio de emergencia**.

DSI **no** hace pruebas conjuntas de revocación (acta del 13/10). Por eso el
lado del agente prueba que una credencial inválida lo detiene de forma
reproducible: el agente se detiene con `workspace_token_exchange_denied`
(código de la prueba de clave inválida).

**Detección.** Las seis reglas de actividad de DSI sobre la cuenta técnica
(inicio de sesión, contraseña o 2SV, permiso OAuth nuevo, miembros o uso
compartido de la unidad, cambios del admin, cambios en la delegación) avisan al
responsable de DSI y al operador designado; quedan además en el registro de
auditoría de Workspace, con 6 meses de retención (modelo de seguridad §6).

**Si hubo un envío.** Un `ENVIO_INDETERMINADO` o una `EMISION_INDETERMINADA`
significa que un envío pudo o no haber ocurrido: se trata como incidente y **no
se reenvía solo**. Se cruza contra Gmail Enviados y decide una persona (§5.11).

---

## 5. Diagnóstico: qué hacer cuando algo falla

Los códigos que siguen son los que el agente **ya usa**; no hay códigos
inventados. Aparecen en la salida JSON de la CLI, en los registros JSONL del
directorio de salida o en el `journalctl` del servicio. El inventario completo
de los códigos del *gate* de contenido vive en el código y en las políticas
versionadas (`src/agente1/politicas/`, `src/agente1/posts.py`); acá se listan
los que tienen significado operativo.

Regla general: el agente es **fail-closed**. Ante una duda, no produce un
borrador, no envía y no arranca; cada falla queda asentada con hashes, sin
copiar datos personales ni contenido.

### 5.1 Arranque e integridad (ADR 0010)

| Código | Significado | Qué hacer |
|---|---|---|
| `integridad_archivos_no_coinciden` | Un archivo controlado del host no coincide con `manifest-version.json`; el agente **no arranca** (salida 2). El motivo por archivo (`modificado`, `faltante`, `sobrante`) y los dos hashes quedan en `logs/integridad-arranque.jsonl`. | Restaurar el archivo de la versión instalada o cortar una versión nueva. **No** editar el host ni regenerar el manifest en el host. |
| `manifest_version_ausente` | Falta el manifest de la versión. | Reinstalar el manifest que viaja con la versión etiquetada. |
| `manifest_version_invalido` / `manifest_sin_archivos` | El manifest está dañado o vacío. | Reinstalar el manifest de la versión; un manifest vacío no verifica nada. |
| `workspace_key_unreadable` / `workspace_key_invalid` | La clave de la cuenta de servicio no se puede leer o no parsea. | Revisar la ruta y los permisos; si está corrupta, pedir una rotación a DSI (§3.2). |
| `workspace_auth_signing_unavailable` | Falta `openssl` o falla la firma del *assertion*. | Instalar `openssl` en el host. |
| `workspace_auth_config_missing` / `workspace_auth_config_incomplete` / `workspace_auth_config_invalid` | Configuración de la identidad ausente, incompleta o inválida. | Completar el env file (§2.3). |
| `workspace_cuentas_suplantables_invalid` | La lista cerrada de cuentas suplantables está dañada. | Restaurar el archivo de la versión (es controlado). |
| `workspace_impersonation_not_allowed` | La cuenta indicada por el entorno no está en la lista cerrada. | Corregir `AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT` o sumar la cuenta por cambio controlado (aprueba la SEU). |
| `workspace_cuenta_audit_unavailable` | No se pudo escribir la auditoría del token. | Revisar permisos del directorio de salida. |

### 5.2 Credencial e intercambio de token (ADR 0011)

| Código | Significado | Qué hacer |
|---|---|---|
| `workspace_token_exchange_denied` | Google denegó el intercambio (clave inválida o revocada, delegación caída). Es la señal de credencial inválida. | Verificar que la clave y la delegación están vigentes; pedir rotación a DSI. |
| `workspace_token_exchange_rate_limited` | Google limitó la tasa. | No reintentar en bucle; esperar la próxima corrida. |
| `workspace_token_exchange_unavailable` | El endpoint de token no responde (red/DNS). | Revisar conectividad a `oauth2.googleapis.com`. |
| `workspace_token_exchange_response_invalid` / `workspace_token_exchange_response_too_large` | Respuesta del endpoint con forma inesperada o demasiado grande. | Revisar si hubo un intermediario; el agente no la acepta. |
| `workspace_config_incomplete` / `workspace_config_invalid` / `workspace_config_unknown_key` | Configuración de Workspace incompleta, inválida o con una clave desconocida. | Revisar el env file (§2.3). |
| `workspace_auth_unavailable` / `workspace_auth_denied` | El token no está disponible o la identidad no tiene acceso. | Revisar el mecanismo de token y la compartición del recurso. |
| `workspace_unavailable` / `workspace_response_invalid` / `workspace_response_too_large` | Falla de red o contrato remoto en el plano de datos. | Revisar conectividad y contrato; no reintentar a ciegas. |

### 5.3 Fuentes y servicios de Google

| Código | Significado | Qué hacer |
|---|---|---|
| `sheets_headers_invalid` | Los encabezados de la planilla no son los del contrato. | Confirmar la pestaña y sus nueve columnas; un cambio de encabezado rompe el contrato. |
| `sheets_row_invalid` / `insumos_fila_invalida` / `estado_fila_invalid` | Una fila no cumple el contrato. | Corregir el dato en la fuente. |
| `workspace_source_not_found` | No se encontró la planilla o el rango. | Confirmar el ID y el rango con DSI/SEU. |
| `source_contract_invalid` / `source_request_invalid` / `source_request_not_found` / `source_duplicate_id` | El origen de solicitudes no cumple el contrato o no tiene el pedido. | Revisar el dataset o la planilla. |
| `gmail_auth_denied` / `gmail_auth_unavailable` | El envío o la lectura de Gmail no está autorizado o no está disponible. | Revisar el scope y la identidad. |
| `gmail_rate_limited` / `gmail_paginacion_excedida` | Límite de tasa o tope de paginación alcanzado. | Esperar; revisar el volumen del buzón. |
| `gmail_test_list_missing` / `gmail_test_list_invalid` / `recipient_off_test_list` | Falta o es inválida la lista de prueba, o el destinatario queda fuera de ella. | Declarar la lista de prueba (`AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`); el agente no envía fuera de ella. |
| `gmail_mode_invalid` / `gmail_production_list_missing` / `gmail_production_list_invalid` / `recipient_off_approved_list` | El modo de envío no es `prueba` ni `produccion`, falta o es inválida la lista aprobada, o el destinatario queda fuera de ella. | Revisar `AGENTE1_GMAIL_MODO` y la lista que aprueba la SEU (`AGENTE1_GMAIL_DESTINATARIOS_APROBADOS`). Sin lista válida el agente no construye el destino. |
| `draft_marker_in_production` / `draft_marker_missing` | El cuerpo lleva marca de borrador en modo producción, o le falta en modo prueba. | En producción, usar la plantilla aprobada por la SEU sin marcas; en prueba, conservar `BORRADOR — NO ENVIAR`. |
| `gmail_source_not_found` / `gmail_response_invalid` / `gmail_response_too_large` / `gmail_unavailable` | Falla del buzón o contrato remoto inesperado. | Revisar la conexión y el mensaje. |
| `drive_unavailable` / `drive_auth_denied` / `drive_rate_limited` / `drive_resource_not_found` | Falla de Drive. | Revisar permisos, cuota y pertenencia a la unidad compartida. |
| `drive_response_invalid` / `drive_response_too_large` / `drive_request_too_large` | Contrato remoto o tamaño fuera de límite. | Revisar el artefacto que se intenta subir. |
| `docs_unavailable` / `docs_response_invalid` / `docs_response_too_large` | Falla de Docs. | Revisar la conexión y el contrato. |
| `docs_update_failed_orphaned` | La copia del documento quedó huérfana tras un fallo. | Revisar el documento en Drive; puede requerir limpieza manual. |
| `destination_contract_invalid` / `destination_unavailable` | El destino del borrador no cumple el contrato o no está disponible. | Revisar la carpeta y la plantilla configuradas. |
| `draft_marker_missing` | Falta la marca de borrador donde el contrato la exige. | Revisar el destino; una pieza sin marca no se presenta como borrador. |

### 5.4 Scheduler

| Código | Significado | Qué hacer |
|---|---|---|
| `scheduler_config_invalid` / `scheduler_config_unknown_key` | Variable `AGENTE1_SCHEDULER_*` con valor inválido o desconocida. | Revisar el env file; la agenda que corre es la escrita. |
| `scheduler_ventana_sin_ticks` | La ventana declarada no genera ningún tick. | Revisar `INTERVALO_S`, `VENTANA_DESDE`/`HASTA` y `TZ`. |
| `scheduler_lock_inaccesible` | No se puede tomar el lock de corrida. | Revisar permisos y procesos colgados. |
| `scheduler_log_inaccesible` / `scheduler_log_invalid` | El log de corridas no se puede leer o está corrupto. | Revisar `logs/scheduler-corridas.jsonl`; no se procesa hasta revisarlo. |
| `entrada_inaccesible` | La tabla/entrada offline no existe. | Revisar `--tabla`. |
| `scheduler_corrida_error` | La corrida falló sin un código propio. | Ver el `detalle` del log y el `journalctl` del servicio. |

En `logs/scheduler-corridas.jsonl`, `resultado` puede ser `completada`,
`falla`, `omitida_ventana`, `omitida_lock` u `omitida_duplicada`. Una
`omitida_lock` sostenida indica un disparo anterior que sigue corriendo o que
murió con el lock.

### 5.5 Insumos de agentes

| Código | Significado | Qué hacer |
|---|---|---|
| `insumos_config_incomplete` / `insumos_config_invalid` / `insumos_config_unknown_key` | Configuración de la corrida de insumos. | Revisar el env file y el rango `AGENTE1_INSUMOS_RANGO_A1`. |
| `insumos_encabezado_invalid` | Los encabezados de la pestaña de insumos no cumplen el contrato. | Confirmar la pestaña «Insumos de agentes». |
| `insumos_registro_invalid` | El registro de idempotencia está dañado. | Revisar `insumos-procesados.jsonl`; no se reprocesa a ciegas. |
| `insumos_tabla_inaccesible` | La pestaña o el archivo de insumos no se puede leer. | Revisar el rango y los permisos. |
| `evento_campos_faltantes` / `evento_campos_desconocidos` / `evento_valor_invalido` / `evento_datos_incompletos` | El insumo A3 `evento` no cumple el contrato de campos. | Corregir el insumo en la fuente; el productor lo vuelve a cargar. |
| `evento_actividad_invalid` / `evento_enlace_no_disponible` | Falta la actividad o el enlace del evento. | Completar el insumo. |
| `evento_generacion_fallida` | La generación del borrador a partir del insumo falló. | Ver el `detalle`; el insumo queda rechazado con motivo. |

### 5.6 Generación y gate (calidad, no operación)

Una gacetilla declara su **tipo** y el tipo declara su **modo** y su **forma**
(ADR 0012). Sin tipo declarado no hay pieza: el agente no aproxima la clase más
parecida. Los siete tipos del corpus y su modo están en
`src/agente1/contracts/tipos_gacetilla_v1.json`; las partes institucionales
fijas de cada tipo, en `src/agente1/contracts/formas/<tipo>_v1.json`; sus
campos, en `src/agente1/contracts/entradas/<tipo>_v1.json`.

- **Difusión de actividad** y **saludo o efeméride** *generan*: el modelo
  escribe la prosa con el prompt del tipo y el renderer le pone la forma.
- **Crónica de evento, aviso de otra área, convocatoria interna, fallecimiento
  y newsletter** *extraen y confirman*: los datos los carga quien pide y el
  agente sólo los formatea. No llaman al modelo, no tienen prompt y el gate
  compara la pieza contra **lo confirmado**, no contra texto generado.

Cuando el modelo produce una salida que no cumple, el agente **no crea
borrador**: la ejecución queda `FALLIDA` con un código del *gate*. Son la señal
de que el contenido no es apto, no de que el sistema esté roto. Ejemplos de
códigos reales: `data_structure`, `document_structure`,
`document_marker_in_output`, `place_missing` / `place_mismatch` /
`unexpected_place`, `length_out_of_range`, `output_too_long`,
`personal_data`, `prompt_injection_echo`, `source_fact_in_creative_field`,
`source_fact_in_template`, `non_rioplatense_register` y la familia
`unauthorized_*` (fechas, montos, lugares, enlaces, afirmaciones, etc.). En las
gacetillas, el núcleo común agrega `marcador_sin_resolver`, `proceso_interno` y
`hecho_perdido`, y cada tipo suma su regla: `aviso_afirma_invitacion`,
`fallecimiento_sin_nombre_confirmado` y `emisor_area_no_confirmada`. El
inventario completo está en `src/agente1/posts.py`, en `gacetillas.py` y en la
política de redes versionada.

Qué hacer: **no** tocar el gate para que "pase". Si la regla es correcta y el
modelo falla seguido, es una decisión sobre el modelo o el prompt, que entra
por el circuito de cambio controlado (§9). Cuando el presupuesto de
decodificación se agota, el pipeline lo registra como `presupuesto_agotado` en
vez de dejar que el corte llegue al parser.

La **integridad del gate** es un compromiso operativo: toda pieza que llega a
validación humana pasó el gate y ninguna pieza no conforme se presenta como
conforme. La tasa de conformidad, en cambio, es una medida de calidad (§7).

### 5.7 Cola, envío y emisión

| Código | Significado | Qué hacer |
|---|---|---|
| `notification_mode_mismatch` | El tipo de notificación no corresponde al modo de circuito de la vía usada (por envío vs. por lote). | Revisar el catálogo de tipos y la vía; no forzar el envío. |
| `notification_type_blocked` / `notification_type_invalid` | El tipo está bloqueado (fail-closed) o no existe. | No habilitar sin decisión; el tipo bloqueado no produce borrador. |
| `recipient_invalid` / `required_fields_missing` / `input_contract_invalid` | Destinatario o datos de entrada inválidos. | Corregir el dato en la fuente. |
| `approval_required` / `approval_invalid` | Falta la aprobación humana o es inválida. | Registrar la aprobación por el Form de decisiones con el rol correcto. |
| `queue_required` / `offline_destination_required` | Falta la cola o el destino offline. | Revisar la configuración de la corrida. |
| `idempotency_duplicate` / `idempotency_record_invalid` | El ítem ya fue procesado o el registro de idempotencia está dañado. | No reenviar; revisar el registro. |
| `fake_delivery_failed` / `fake_emission_failed` | Falló la entrega o emisión simulada. | Revisar el destino fake declarado. |
| `certificate_type_invalid` / `descriptive_line_invalid` | El tipo de certificado o la línea descriptiva no cumplen el contrato. | Revisar la solicitud y sus precondiciones de aprobación. |
| `lista_cierre_vacia` / `lista_cierre_duplicada` / `lista_cierre_fila_invalida` / `lista_cierre_condicion_vacia` | La lista de cierre no cumple el contrato. | Corregir la lista en la fuente; la cierra quien gestiona el curso. |
| `padron_roles_missing` / `padron_roles_invalid` / `padron_fila_invalid` / `padron_id_duplicado` / `padron_actividad_distinta` | El padrón de roles no cumple el contrato. | Corregir el padrón (lo mantiene la SEU). |
| `plan_*` (p. ej. `plan_cuotas_inconsistentes`, `plan_procedencia_invalid`, `plan_dato_obligatorio_ausente`, `plan_campo_desconocido`) | El plan de pago no cumple el contrato. | Corregir el plan de pago en la fuente. |

Los códigos `runner_*` (por ejemplo `runner_live_not_enabled`,
`runner_live_write_not_confirmed`, `runner_live_config_invalid`,
`runner_mode_invalid`, `runner_channel_required`, `runner_type_invalid`) son
guardas del doble opt-in y de la forma de invocación: indican que la corrida se
pidió mal o sin la segunda confirmación, no una falla del sistema.

### 5.8 Respaldo y restauración (ADR 0009)

| Código | Significado | Qué hacer |
|---|---|---|
| `respaldo_config_incomplete` / `respaldo_config_invalid` / `respaldo_config_unknown_key` | Configuración del respaldo. | Revisar el prefijo `AGENTE1_RESPALDO_*` y elegir un modo. |
| `respaldo_config_write_not_confirmed` | Falta la segunda señal del opt-in de escritura real. | Confirmar explícitamente o quedarse en modo fake. |
| `respaldo_artefacto_invalid` / `respaldo_artefacto_too_large` | El artefacto no verifica o supera el tamaño. | Revisar el artefacto; no se restaura a medias. |
| `respaldo_borrado_error` / `respaldo_borrado_invalid` / `respaldo_nombre_invalid` / `respaldo_marca_invalid` / `respaldo_retencion_invalid` | El borrado de respaldos vencidos no cumple sus condiciones. | Revisar `logs/respaldo-diario.jsonl`; sólo se borran los propios y vencidos. |
| `respaldo_tras_purga_fallida` | El respaldo no corrió porque la purga del día falló. | Se reintenta en el tick siguiente; no saltear la purga (ADR 0009). |
| `respaldo_diario_error` | Falla general del paso de respaldo. | Revisar el log y el aviso al operador; la corrida de insumos no se cae. |
| `purga_registro_error` | Falla la purga de datos personales. | Revisar el registro; el respaldo espera a que la purga cierre. |

La restauración es manual y no destructiva: se baja el `.tar.gz` de Drive y se
corre `scripts/restaurar_respaldo.py --artefacto <...> --salida <dir>
--registro <dir>`. Al restaurar, todo lo posterior a la marca del respaldo pasa
a `ENVIO_INDETERMINADO` y no se reenvía solo. El detalle está en el runbook del
scheduler §6.2.

### 5.9 Canal de pedidos, decisiones y padrón

El canal de pedidos lee la hoja de respuestas con un contrato versionado:
`canal_form_respuestas_v1` (una sola pregunta abierta, default) y
`canal_form_respuestas_v2`, opt-in con
`AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO=canal_form_respuestas_v2`. Esa misma
variable elige la forma de hoja en los dos modos: el runner offline la lee
también, y un valor desconocido falla cerrado con
`canal_form_config_invalid` antes de leer nada. La v2 pide el
**tipo de gacetilla** como primera pregunta (lista cerrada del catálogo de
tipos), la **actividad** sólo para los tipos que la llevan y el **área
emisora** por el padrón cerrado de `contracts/areas_emisoras_v1.json`. El
desplegable de actividades se carga a mano como insumo provisional con
identificadores de la planilla de actividades; su sincronización automática
(Apps Script) queda declarada como destino del canal y no existe hoy.

En la forma v2, una fila que declara un tipo fuera de la lista cerrada, una
actividad que no corresponde («No es una actividad / no figura», campo
vacío, texto libre) o un área fuera del padrón **no llega al núcleo**:
termina en un desenlace acotado con aviso al correo del pedido y línea en el
registro de atendidos (`estado: INVALIDA`, `resultado: <código del
bloqueo>`, `origen_hechos: solicitud`), sin generar nada. Cargar una
actividad en la planilla institucional no es tarea del agente: la planilla
manda. Una difusión con identificador bien formado de una actividad no
cargada entra al núcleo igual que por prosa y vuelve `INVALIDA` sin
generación.

| Código | Significado | Qué hacer |
|---|---|---|
| `canal_form_config_incomplete` / `canal_form_config_invalid` / `canal_form_config_unknown_key` | Configuración del canal de pedidos por Form, incluida la versión de contrato de hoja (`AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO`). | Revisar el env file. |
| `canal_form_hoja_contrato_desconocido` / `canal_form_hoja_contrato_invalido` | El contrato de la hoja de respuestas no está declarado o su contenido no es legible. | Confirmar la versión declarada y que el archivo del repo exista y tenga sus columnas. |
| `canal_form_areas_padron_invalido` | El padrón cerrado de áreas emisoras no se puede leer o está mal armado. | Revisar `contracts/areas_emisoras_v1.json`; el arranque sin padrón de áreas no habilita a medias. |
| `canal_form_registry_invalid` / `canal_form_registry_unavailable` | El registro de atendidos está dañado o no está. | Revisar `atendidos-canal-form.jsonl`. |
| `canal_form_decisiones_config_incomplete` / `canal_form_decisiones_config_invalid` / `canal_form_decisiones_config_unknown_key` | Configuración del Form de decisiones. | Revisar el env file. |
| `decisiones_registry_invalid` | El registro de decisiones está dañado. | Revisar `decisiones-procesadas.jsonl`. |
| `decision_objeto_invalid` / `decision_tipo_invalid` / `decision_link_invalid` / `decision_detalle_invalid` | La decisión no corresponde a un objeto, tipo, enlace o detalle válidos. | Registrar la decisión con el objeto y el rol correctos. |

### 5.10 Historia Viva (A2)

| Código | Significado | Qué hacer |
|---|---|---|
| `historia_viva_config_incomplete` / `historia_viva_config_base_url` / `historia_viva_config_token_invalid` / `historia_viva_config_unknown_key` | Configuración del cliente de Historia Viva. | Revisar el env file; el token vive fuera de todo repo. |
| `historia_viva_unauthorized` | El token no autoriza la consulta. | Revisar el token de sólo lectura. |
| `historia_viva_request_invalid` / `historia_viva_response_invalid` / `historia_viva_unavailable` | Contrato de la consulta o disponibilidad del servicio. | Revisar la consulta o esperar; la consulta vacía no produce post. |

### 5.11 Estados que no son códigos de error

| Estado | Significado | Qué hacer |
|---|---|---|
| `PENDIENTE_VALIDACION` | Borrador generado que espera validación humana; lleva `BORRADOR — NO PUBLICAR`. | Es el estado normal de toda pieza hasta que una persona decide. |
| `PENDIENTE_CONFIRMACION` | El pedido no se reconoció y el modelo propuso una intención permitida; no hay borrador. El aviso trae el enlace al mismo Form, prellenado por código. | Abrir el enlace no hace nada: revisá, editá si hace falta y **enviá** el formulario; ese envío es el pedido que genera. |
| `FALLIDA` / `INCOMPLETA` / `INICIADA` | La ejecución no produjo un borrador válido. | Revisar el código del gate o del contrato (§5.6). |
| `ENVIO_INDETERMINADO` / `EMISION_INDETERMINADA` | El envío o la emisión pudo haber ocurrido o no (p. ej. una caída, o una restauración posterior al respaldo). | **Incidente S1**: no se reenvía solo; cruzar contra Gmail Enviados y decidir por caso. |
| `ENVIADA_SIMULADA` / `EMITIDA_SIMULADA` | El envío o la emisión se hizo contra el destino declarado, en un ambiente controlado. | Registrar; son los estados terminales que la retención purga a los 30 días. |

Los códigos de salida de la CLI local son `0` sólo cuando quedó un borrador
`PENDIENTE_VALIDACION`, y `2` para cualquier otro desenlace (incluidos los
legítimos, como datos incompletos): un encadenamiento no debe seguir como si se
hubiera generado algo. El smoke de Workspace usa `0`/`2`/`3`/`4` (éxito,
configuración inválida, token ausente o inseguro, y falla cerrada de red o
contrato), según su runbook §4.

---

## 6. Políticas

Las políticas son secciones de este manual, no documentos aparte (issue #65).

### 6.1 Credenciales

La política de credenciales sale del modelo de seguridad (§2, §4 y §7) y de
ADR 0011: una sola clave de cuenta de servicio, custodiada fuera del repo, que
**rota y revoca el responsable de DSI** en el acta y ante un incidente; sin
rotación periódica de contraseña; el par OAuth anterior se da de baja cuando la
cuenta de servicio funciona en vivo; y ninguna credencial se comparte por
correo, chat ni repositorio. Detalle y fundamento en el documento enlazado en
§3.

### 6.2 Acceso por rol

La identidad la verifica Google por el correo del Form y el rol sale de un
padrón mantenido por la SEU fuera del repositorio (ADR 0005): quien no está en
el padrón, o no tiene el rol que la decisión exige, queda **rechazado y
registrado**. Para este canal, ADR 0005 reemplaza a ADR 0002. Los roles del
padrón son los que la SEU designó por escrito; el sistema no los asigna leyendo
el organigrama.

### 6.3 Retención acotada

"El sistema no retiene datos" se interpreta así: el texto con datos personales
se purga a los **30 días** del estado terminal; la auditoría conserva **sólo
hashes**; y los respaldos no duran más de **30 días**. La purga corre antes del
respaldo del día para que ningún respaldo conserve texto ya vencido (ADR 0009).
Es la interpretación de lo que la SEU dijo el 22/09; **falta llevarla
formalmente a la SEU** (issue #56).

### 6.4 Respaldo y restauración

El scheduler respalda el estado una vez por día en la primera corrida de la
ventana: un archivo nuevo en una carpeta de la cuenta técnica que no se comparte
con nadie. El RPO queda en un día hábil. Si el respaldo falla, queda auditado y
se avisa al operador; la corrida sigue. Al restaurar, todo lo posterior al
respaldo pasa a `ENVIO_INDETERMINADO` y no se reenvía sin cruzarlo contra Gmail
Enviados (ADR 0009; runbook §6.1–6.2).

### 6.5 Uso aceptable del modelo

El modelo **redacta y, de forma acotada, clasifica**: nunca decide envíos,
nunca publica y ninguna pieza llega a un destinatario sin pasar por validación
humana. Sus usos están cerrados y su salida se valida contra un contrato antes
de usarse:

- **Redacta** el contenido de la pieza. Nunca escribe montos, fechas, enlaces ni
  datos de la persona: esos van como variables que completa el renderer.
- **Extrae términos de búsqueda** cuando el camino determinístico no resuelve la
  actividad: aporta la forma normalizada de lo que la persona escribió, y el
  código sigue siendo el único que elige la actividad.
- **Propone una intención** (`generar_gacetilla` o `generar_post`) sólo cuando
  ninguna regla reconoce el pedido. La propuesta no genera nada: vuelve por
  correo con un enlace al mismo Form, prellenado por código, y recién el envío
  de ese formulario (un pedido nuevo, con identidad, rol, actividad y gates
  verificados otra vez) produce el borrador: el circuito Form → correo → Form.
  Abrir el enlace no ejecuta nada.

No recibe datos personales que no necesite la pieza y corre **sólo en local**
(loopback), sin enviar prompts ni datos a APIs de LLM externas (ADR 0001, con
su enmienda del 16/10/2026).

---

## 7. SLO

Los SLO se definen para la **operación después del traspaso**, que es lo que
compromete el SLA (issue #65). Cada uno tiene un **nivel verificado** medido
sobre el sistema de demostración; ese nivel verificado es lo que cita el Anexo 2,
no el objetivo. El numerador y el denominador salen de la auditoría que la
operación ya deja: la medición se corre con
`PYTHONPATH=src python scripts/medir_nivel_slo.py` (lectura solamente, no toca la
red ni escribe en las fuentes) y se versiona en `evidencias/`. Un ejemplo real
está en `evidencias/nivel-verificado-slo-2026-10-12.md`.

### 7.1 Ventana de operación

La ventana es **provisional**: días hábiles de 8 a 16, hora de
`America/Argentina/Buenos_Aires`. La confirma la SEU (issue #56). Fuera de la
ventana no hay compromiso de servicio y lo aprobado sale en la primera corrida
de la ventana siguiente.

### 7.2 Objetivos y forma de medirlos

| SLO | Definición | Objetivo | Cómo se mide |
|---|---|---|---|
| **Disponibilidad** | Corridas programadas completadas a tiempo / corridas programadas, **dentro de la ventana**. El denominador son los ticks esperados de la agenda, no las líneas del log. | 99 % | `logs/scheduler-corridas.jsonl` contra la agenda de `AGENTE1_SCHEDULER_*`. |
| **Tiempo de atención** | Desde el envío del Form de pedido hasta el aviso con el borrador (incluye la espera hasta la corrida). | p95 ≤ intervalo de sondeo + 5 min | `atendidos-canal-form.jsonl` cruzado con el CSV de respuestas del Form (la marca del Form no se persiste: entra al hash). |
| **Latencia por pieza** | Generación por tipo de pieza (interna; alimenta la eficiencia de desempeño). | p95; el número sale de la medición sobre el modelo elegido (issues #50/#51) | `latencia_s` de los logs de generación. Mientras #50/#51 no cierren, la celda dice `pendiente #50/#51`; no se inventa un tope. |
| **Aprobación → envío** | Desde la doble aprobación (plantilla y lote) hasta el envío. Fuera de la ventana se envía en la primera corrida de la siguiente. `ENVIO_INDETERMINADO` cuenta como incidente. | p95 ≤ 2 × intervalo de sondeo | `decisiones-procesadas.jsonl` y el `actualizado_en` del registro durable (circuito de lote por actividad). |
| **Integridad del gate** | Piezas en validación humana que pasaron el gate. | 100 %, y 0 no conformes presentadas como conformes | Tres verificaciones sobre lo ya escrito (generación, artefactos locales y envíos). |
| **RPO** | Estado local. Lo que está en Google sigue el RPO de Google. | ≤ 1 día hábil | Antigüedad del último respaldo diario en Drive de la cuenta técnica respecto del incidente (ADR 0009). |
| **RTO** | Puesta en marcha siguiendo este manual. | 1 jornada hábil | Desde el inicio de la puesta en marcha hasta el servicio operando. Al restaurar un respaldo, todo lo posterior a su marca pasa a `ENVIO_INDETERMINADO`. |

**La tasa de conformidad no es un SLO.** Es una medida de calidad que va al
perfil del Anexo 2 (issue #59). El medidor declara `muestra insuficiente (n=...)`
o `sin_fuente` cuando no alcanza la muestra mínima (20 observaciones por
omisión) o falta una fuente, en vez de publicar un número.

---

## 8. SLA tipo

Este SLA va **a nombre de "el operador designado"**, se firma en el acta de
traspaso y **no rige durante el PPS** (issue #65).

- **Soporte** sólo dentro de la ventana de operación (§7.1). No hay 24/7.
- **Severidades:**
  - **S1** — envío erróneo o indeterminado: respuesta en la misma jornada
    hábil.
  - **S2** — agente detenido: respuesta en la jornada hábil siguiente.
  - **S3** — calidad de los borradores: se atiende en el circuito normal de
    contenido, sin compromiso de plazo aparte.
- **Exclusiones:** los servicios de Google, el modelo local y el hardware del
  host.
- **Suspensión por defecto:** entre la presentación final y el inicio de clases
  el agente queda suspendido, salvo que ya haya un operador designado que
  acepte sostenerlo (ADR 0007).

---

## 9. Control de cambios

El proceso rige desde el traspaso. Hasta el acta, el responsable técnico del PPS
es el único aprobador técnico; después del acta, cada clase pasa a su dueño
(issue #66).

### 9.1 Clases de cambio y quién aprueba

| Clase | Qué incluye | Aprueba |
|---|---|---|
| **Código y dependencias** | `src/`, `uv.lock`, scripts operativos, units de `systemd/`, migraciones. | Responsable de evolución (alumnos del P100), con revisión de los dueños. |
| **Prompts y parámetros de inferencia** | Prompts, modelo, `num_predict`, temperatura. | Responsable de evolución, **con la matriz de regresión de la HU afectada**. No pasa por la SEU: el gate y la validación humana protegen cada pieza. |
| **Criterios de contenido de la SEU** | Política de redes, plantilla base, plantillas de actividad, línea descriptiva. | La SEU, por su propio circuito (aprobación semántica y utilitaria). No se duplica. |
| **Contratos de interfaz** | Schemas, contrato v2 de la planilla, pestaña de insumos. | Responsable de evolución + el dueño del otro lado (agente productor). |
| **Configuración de Workspace y credenciales** | Scopes, cuenta técnica, proyecto de Google Cloud, IDs, cuenta suplantable. | DSI (hoy; el operador designado después). El repo guarda referencias, nunca secretos. |

Los **datos operativos** (padrón de roles, lista de cierre, planilla de
actividades) **no son cambios controlados**: los mantiene su dueño y quedan
rastreados por la auditoría.

### 9.2 Registro

- `main` protegida con PR obligatorio y CI (`agente1-ci`) como check requerido.
  Sin segundo revisor humano obligatorio hasta el traspaso (autor único,
  declarado "B: con observaciones").
- Cada versión instalada lleva tag `agente1-vX.Y.Z`, entrada en `CHANGELOG.md` y
  un **manifest de versión** con el sha256 de lo controlado. Cada registro de
  auditoría lleva `version_agente` y el hash del manifest.
- **Los cambios en la consola de Google los aprueba DSI** y quedan en el log de
  auditoría de la consola, que dura 6 meses y **se enlaza, no se reescribe**.
  DSI no lleva registro propio. El **motivo** de cada cambio pedido a DSI se
  anota en la sección *Configuración* de `CHANGELOG.md`, con fecha y quién lo
  aprobó.

### 9.3 Cortar una versión

Se corta una versión cada vez que cambia algo controlado y el cambio se instala
en el host. El procedimiento paso a paso (número de versión, manifest, entrada
de changelog, tag, instalación) está en
`PROCEDIMIENTO-CORTE-DE-VERSION.md`. La versión sale de un solo lugar:
`pyproject.toml`.

### 9.4 Cuando el agente no arranca por un archivo controlado que no coincide

El agente **no arranca** (ADR 0010): un prompt, una política o un contrato
editado a mano en el host cambia lo que el agente redacta o lo que deja pasar el
gate, sin PR y sin evidencia de regresión. La auditoría muestra el archivo y los
dos hashes. La respuesta **no es editar el host**: es restaurar el archivo de la
versión o cortar una versión nueva (ver §5.1 y el runbook del scheduler §9).

La configuración por entorno (IDs, scopes) queda **fuera** de ese fail-closed:
Informática la cambia sin pasar por el repo. Su huella —sin secretos— se compara
con la de la corrida anterior y, si cambió, se registra y se avisa al operador.

### 9.5 Cambio de emergencia

Sólo ante una credencial comprometida o una pieza enviada o emitida por error:
se **suspende** (detener el scheduler y revocar el token, §4), no se parchea en
caliente. La corrección vuelve por el circuito normal.

### 9.6 Reversión

Volver a la versión anterior instala el tag anterior completo (código, prompts,
políticas, contratos, migraciones y `uv.lock`). Si hay migraciones en el medio,
se aplica el `down` cuando CI lo prueba; si el `down` descarta datos, se
restaura el respaldo de Drive. El detalle —qué migración pierde datos y cuál
no— está en `Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md`.

---

## 10. Referencias

**Decisiones**

- `docs/adr/0007-el-traspaso-reparte-tres-responsables-y-el-autor-no-conserva-acceso.md`
- `docs/adr/0009-el-agente-respalda-su-estado-en-drive-y-borra-sus-propios-respaldos.md`
- `docs/adr/0010-el-agente-no-arranca-si-sus-archivos-controlados-no-coinciden-con-su-version.md`
- `docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`
- `docs/adr/0005-identidad-verificada-por-formulario-rol-por-padron.md`
- `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`

**Seguridad y credenciales**

- `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`
- `Documentos/Reuniones/DSI-2026-10-13/Acta-DSI-2026-10-13.md`

**Procedimientos y runbooks**

- `PROCEDIMIENTO-CORTE-DE-VERSION.md`
- `Documentos/PlanDespliegue/Runbook-Scheduler-Agente-1.md`
- `Documentos/PlanDespliegue/Runbook-Workspace-D2-D3-Agente-1.md`
- `Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md`

**Glosario y estado**

- `CONTEXT.md` (secciones *Traspaso* y *Operacion*)
- `CHANGELOG.md`

**Evidencia de medición**

- `evidencias/nivel-verificado-slo-2026-10-12.md`
- `evidencias/integridad-arranque-2026-10-14.md`
- `evidencias/cuenta-servicio-delegada-2026-10-14.md`

**Política de artefactos**

- `Documentos/PoC/Politica-Artefactos-Versionados-v1.md`

---

## Apéndice — regenerar el PDF de este manual

El PDF no se versiona (política de artefactos). Se regenera desde esta fuente
con el script del repositorio:

```bash
scripts/renderizar-artefactos.sh manual
```

El script convierte este Markdown a HTML con la extensión `markdown` traída
transitoriamente por `uv` y lo imprime a PDF con Chromium headless, siguiendo la
convención de los demás renders del repositorio. Escribe
`MANUAL-OPERACION-AGENTE-1.html` y `MANUAL-OPERACION-AGENTE-1.pdf` junto a esta
fuente, en rutas que `.gitignore` excluye.
