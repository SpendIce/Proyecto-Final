# Guion de la prueba presencial del laboratorio (iLab/rLab)

Vista de trabajo del autor para la prueba presencial. **No se entrega al laboratorio.**

- **Ticket:** [#114](https://github.com/SpendIce/Proyecto-Final/issues/114), que sale de [#57](https://github.com/SpendIce/Proyecto-Final/issues/57).
- **Ventana acordada:** semana del **2 al 6 de noviembre de 2026** (lunes, miércoles o viernes por la mañana).
- **Formato:** demo del sistema funcionando, **~1 hora, sin presentación**. El sistema corre en el **servidor de la facultad** (`labredesfie`), en contenedores (ADR 0013), y se opera desde la notebook del autor: la consola por túnel SSH y los comandos en la consola del contenedor en Portainer. La cátedra exige que no corra en localhost.
- **Insumos:** los tres anexos ([Anexo 1](Anexo1-Presentacion-v1.md), [Anexo 2](Anexo2-Calidad-Proyeccion-v1.md), [Anexo 3](Anexo3-Seguridad-Proyeccion-v1.md)) y sus tablas fuente (`Perfil-Calidad-Sistema-Demostracion-v1.md`, `Perfil-Seguridad-Sistema-Demostracion-v1.md`).
- **Estado:** guion y respuestas preparados en esta sesión. **El ensayo completo de punta a punta queda pendiente y lo corre Juani** (es el criterio de aceptación de #114).

## Qué evalúa el laboratorio

Del correo de A. Maiorano del 14/10 (`Documentos/Reuniones/Laboratorio-2026-10-12/`):

1. Es una **demo del sistema funcionando**, sin presentación, en la notebook del autor, la nube o donde prefiera.
2. Preguntan por **calidad** (tests unitarios y/o de stress).
3. Preguntan por **seguridad** (por ejemplo, cómo se almacenan las contraseñas en la base).
4. **Pueden pedir mostrar porciones del código fuente.**

**Dónde corre cada cosa.** Los comandos del sistema (`uv run python scripts/X ...` en este guion) se corren **dentro del contenedor** `agente1-consola-1`, desde Portainer (*Containers → Console*), como `AGENTE1_OLLAMA_UPSTREAM= python scripts/contenedor_entrypoint.py python scripts/X ...`. El entrypoint carga el env file y el relay de la consola ya está escuchando. Las salidas van bajo `/state/...`, no `/tmp`. Los tests (`uv run pytest`) se corren en la notebook sobre el repo, porque la imagen de runtime no los lleva; el CI los corre también dentro de la imagen de prueba antes de publicarla. Fuera de la red de la facultad, Portainer se abre por túnel (runbook de contenedores).

Regla de oro del guion: **todo lo que se muestra corre de verdad**. Lo que dependa de un tercero corre contra un destino de prueba o un insumo provisional **declarado**, por el mismo mecanismo productivo, nunca contra un fake.

## Antes de empezar (10 minutos, fuera del horario de la prueba)

- [ ] **Stack sano**: en Portainer, `agente1-ollama-1` *healthy* y `agente1-consola-1` y `agente1-scheduler-1` *running*, con la versión cortada vigente (la rama `deploy` dice cuál).
- [ ] **Consola abierta**: `./run-demo-plan-a.sh` desde la notebook (túnel al puerto 8090).
- [ ] **Modelo caliente**: la consola lo calienta al arrancar; confirmar «cargado» en su encabezado, o hacer una generación de calentamiento. En frío la primera pieza puede tardar varios minutos.
- [ ] **Smoke en vivo** desde la consola del contenedor: `AGENTE1_OLLAMA_UPSTREAM= python scripts/contenedor_entrypoint.py smoke --live --id-solicitud FIE-DIF-08` → `lectura_confirmada`.
- [ ] Notebook con el repo sincronizado (`cd Implementacion/Agente1 && uv sync`) para los tests y el recorrido de código.
- [ ] Carpeta de prueba en D2 y **lista de direcciones de prueba** cargadas.
- [ ] **Suite ya corrida y verde** antes de la prueba, con el número a mano (no se corre entera en vivo: tarda poco más de un minuto y no aporta verla entera).
- [ ] Todas las salidas de la demo en un **directorio de trabajo fuera del repo** (`/tmp/...` o `salida/demo-laboratorio/`), que está en `.gitignore`.
- [ ] Terminal con fuente grande y el repo abierto en el editor para saltar a las rutas de código.

## Guion (55 minutos)

| # | Bloque | Min | Qué se muestra |
|---|---|---|---|
| 1 | Canal → interpretación → gate → borrador (HU-010) | 10 | Un pedido entra por el Form, se interpreta, pasa el gate y sale un borrador |
| 2 | Control de pagos (HU-012) | 6 | Situación de pago derivada, sin estado propio |
| 3 | Post de efeméride (HU-011) | 6 | Consulta a Historia Viva, cita con precisión de fecha, sin material si no hay |
| 4 | Doble aprobación y envío por lista de prueba (HU-012) | 8 | Sin las dos aprobaciones no hay encolado; fuera de la lista se rechaza |
| 5 | Certificados con línea descriptiva y lote (HU-014) | 8 | Lista de cierre, aprobación de lote atada al `sha256`, emisión |
| 6 | Gates y auditoría: códigos, conteos y hashes | 6 | Fail-closed y auditoría sin contenido ni destinatarios |
| 7 | Recorrido por el código fuente | 8 | Las rutas de la columna *Evidencia* del Anexo 3, por componente |
| 8 | Cierre | 3 | Qué no se muestra y por qué |

### Bloque 1. Canal → interpretación → gate → borrador (HU-010), 10 min

Pedido de la SEU por el Form de D2 (respondido en vivo, si hay red) o, si no, con el CSV que imita la hoja de respuestas. Comando offline **verificado** (con `data/padron_roles_sintetico.csv`, que trae un rol habilitado y ninguno más):

```bash
printf 'marca_temporal,correo,pedido\n2026-11-03 09:00:00,solicitante@example.invalid,Necesito una gacetilla para la actividad SYN-001 del martes\n2026-11-03 09:05:00,ajeno@example.invalid,Necesito una gacetilla para la actividad SYN-001\n' > /tmp/lab/respuestas.csv

uv run python scripts/atender_canal_form.py \
  --directorio /tmp/lab/canal --respuestas-csv /tmp/lab/respuestas.csv \
  --padron data/padron_roles_sintetico.csv --csv data/actividades_sinteticas.csv
```

Salida verificada el 16/10/2026: `{"atendidos": 2, "modo": "offline_fake"}`, con un `borrador_generado` en `PENDIENTE_VALIDACION` y un `rol_no_habilitado` en `RECHAZADA` (`solicitante_rol: no_en_padron`).

Qué decir: el pedido en prosa **nunca** llega como instrucción al modelo (ADR 0001). Se clasifica contra un catálogo cerrado; lo que no entra se rechaza y no se aproxima a la intención más parecida. La prosa **no se persiste** en claro: el registro guarda `mensaje_hash` y `solicitante_hash`, nunca el texto ni el correo. La salida es siempre `PENDIENTE_VALIDACION` (y `identidad_verificada: false` en este canal).

Mostrar también el caso que falla: un pedido ambiguo produce **repregunta con candidatas**, nunca una elección silenciosa.

### Bloque 2. Control de pagos (HU-012), 6 min

```bash
uv run python -m agente1 control-pagos \
  --plan data/plan_pagos_notebooklm_n2.csv --padron data/padron_pagos_sintetico.csv --buzon <dir>
```

Qué decir: la situación de pago se **deriva** de las fuentes en cada corrida, como función pura sin estado propio (ADR 0003). Un comprobante presentado **nunca** cuenta como pago confirmado. El informe sale por `stdout` en JSON ordenado y **no se persiste**. El buzón se lee con `gmail.readonly` sobre el usuario `me`, con solo tres endpoints de lectura (ADR 0004).

### Bloque 3. Post de efeméride (HU-011), 6 min

```bash
uv run python scripts/post_efemeride_demo.py --directorio /tmp/lab/hu011   # usa los defaults: instagram y el fixture sintético
```

Salida verificada el 16/10/2026: un borrador `PENDIENTE_VALIDACION` en `borradores/`, los dos enlaces de decisión, y el caso sin material cerrando `INCOMPLETA` con `La consulta no devolvió material histórico`.

Qué decir: el agente **consulta** Historia Viva, recibe fragmentos citables con su precisión de fecha y redacta. Una precisión de mes, año o década **no** se presenta como fecha exacta. Una consulta sin resultados no habilita afirmaciones históricas.

**Estado de la redacción libre**: con el modelo de la demo (`gemma4:e4b`, #51) los posts superan el control de contenido (gacetilla y posts 48/48 en la medición del servidor; Instagram y LinkedIn generados en vivo desde el contenedor el 23/10). Lo que sigue abierto es la validación editorial de la SEU, que entra por la validación humana obligatoria. Si preguntan por las mediciones viejas (1/6 con `llama3.2:3b`): quedaron superadas al cambiar de modelo.

### Bloque 4. Doble aprobación y envío por lista de prueba (HU-012), 8 min

```bash
uv run python scripts/matriz_hu012.py --salida /tmp/lab/hu012   # circuito completo, offline
uv run python scripts/registrar_form_decisiones.py --directorio /tmp/lab/decisiones --respuestas-csv <csv>
```

Qué decir: la doble aprobación (semántica del Responsable de Gestión del Conocimiento y utilitaria del Coordinador de Extensión) es **requisito de la máquina de estados**: sin las dos decisiones no hay encolado ni entrega. La identidad se verifica por Google y el rol sale de un padrón que mantiene la SEU (ADR 0005). El envío por Gmail opera **cercado por la lista de direcciones de prueba** y un destinatario fuera de la lista se rechaza **antes** de tocar el token o la red, sin reintento.

Mostrar: `--live --confirm-write-workspace` sobre el Form de decisiones de D2, con la carpeta de prueba.

### Bloque 5. Certificados con línea descriptiva y lote (HU-014), 8 min

```bash
uv run python scripts/matriz_hu014.py --salida /tmp/lab/hu014   # circuito completo, offline
```

Qué decir: la lista de cierre la **carga la SEU**; el agente nunca infiere asistencia ni aprobación. La aprobación del lote la da el Secretario de Extensión y queda **atada al `sha256`** del objeto: editar la lista de cierre o la plantilla cambia el hash y la aprobación previa deja de aplicar. El certificado lleva el bloque de firma del Secretario de Extensión y del Decano; la **firma digital está fuera de alcance** porque el DoD no la exige. El destino es un correo al titular con el PDF adjunto, contra la lista de prueba. Después de emitir solo queda la auditoría con hashes.

### Bloque 6. Gates, auditoría y aislamiento del contenedor, 6 min

```bash
uv run python scripts/auditar_seguridad_d2.py --manifest data/security_d2_manifest.synthetic.json --reporte /tmp/lab/reporte.json
uv run python -m agente1 ...   # mostrar la línea del log JSONL con sus hashes
# En Portainer, consola de agente1-ollama-1: el modelo no tiene salida a internet
bash -c 'echo > /dev/tcp/1.1.1.1/443'      # → Network is unreachable
# En Portainer, Inspect de agente1-consola-1: usuario 1003, ReadonlyRootfs, CapDrop ALL, sin socket de Docker
```

Qué decir del aislamiento: el modelo corre en su propio contenedor en una red interna sin salida; el agente corre sin root, con el sistema de archivos de sólo lectura y sin capacidades; la imagen la publica el CI sólo al cortar una versión y Portainer la despliega desde la rama `deploy`. La vuelta atrás de versión y la recuperación ante caída están probadas (`Implementacion/Agente1/evidencias/contenedores-servidor-2026-10-23.md`).

Qué decir: el reporte expone **códigos, conteos y hashes**, nunca contenido, destinatarios ni cuerpos; rechaza campos sensibles aunque el valor no esté declarado. Un registro corrupto se trata como ausente y **no habilita entrega**. En modo operación el agente **no arranca** si algún archivo controlado no coincide con el manifest (ADR 0010).

### Bloque 7. Recorrido por el código fuente, 8 min

Abrir las rutas de la tabla de abajo, en el orden de los componentes. Es exactamente la columna *Evidencia versionada* del Anexo 3, para que lo que se muestra en pantalla y lo que el laboratorio tiene escrito coincidan.

### Bloque 8. Cierre, 3 min

Decir qué **no** se muestra, con el motivo, sin maquillarlo: ver la sección «Qué no se muestra».

## Respuestas de calidad, listas

### Tests unitarios

- **Cómo se corren:** `cd Implementacion/Agente1 && uv run pytest -q`. Son **2444 pruebas** en verde y 8 salteadas, en menos de dos minutos (medido el 23/10/2026). En vivo conviene correr un subconjunto por componente en lugar de la suite entera.
- **Cobertura medida:** `uv run pytest -q --cov=src --cov-report=term` da **90 %** (9795 sentencias, 795 sin cubrir, 3086 ramas). El número sale de la corrida del 16/10/2026 y hay que refrescarlo el día de la prueba si cambió el código.
- **Matrices por historia de usuario**, reproducibles y offline: `scripts/matriz_hu010.py`, `matriz_hu011_v2.py`, `matriz_hu012.py`, `matriz_hu014.py`. Ejercitan el circuito completo (pendiente, aprobación parcial, aprobada en ambos órdenes, rechazada, duplicada, emisión simulada, recuperación durable).
- **Linter y CI:** `.github/workflows/agente1-ci.yml` corre `uv run ruff check .` (E/F/I/W, sin hallazgos) y la suite con cobertura, publica la cobertura en el resumen del job y además prueba el ciclo `up`/`down` de las migraciones 0001-0003 sobre PostgreSQL efímero.

Comandos de un subconjunto, para correr en vivo sin comerse el reloj:

```bash
uv run pytest -q tests/test_canal_form.py -k "prosa"          # no persistencia de la prosa
uv run pytest -q tests/test_interpretacion.py -k "inyeccion"  # la prosa es dato, nunca instrucción
uv run pytest -q tests/test_politica_redes.py tests/test_tipos_notificacion.py
uv run pytest -q tests/test_confirmaciones_durables.py -k "indeterminado or paralelo"
uv run pytest -q tests/test_auditoria_seguridad_d2.py
```

### Tests de stress: no hay, y este es el motivo

**Declararlo así, sin rodeos.** La suite es determinista y de contrato: cubre reglas, gates y máquinas de estado, no comportamiento bajo carga. No hay prueba de stress ni de concurrencia sobre el sistema completo, y el sistema de demostración corre en un **servidor compartido de 4 núcleos, sin GPU, con modelo local en CPU**: una prueba de carga ahí mediría el hardware y molestaría a los otros usuarios del servidor, no al sistema.

Lo que sí existe y se puede mostrar como sustituto parcial:

- **Idempotencia durable y concurrencia acotada**, que es la parte donde la carga sí importa: `tests/test_confirmaciones_durables.py` cubre dos creaciones en paralelo que producen un solo borrador, una reserva colgada que pasa a `ENVIO_INDETERMINADO` sin reenviar y una re-corrida que termina `DUPLICADA`.
- **Medición de latencia y presupuesto de decodificación**: `evidencias/medicion-presupuesto-decodificacion-2026-09-08.md` y la latencia por pieza que fija #50/#51.

**Previsto:** una prueba de stress del circuito de generación y de la cola sobre el servidor, donde ya corre el sistema. Queda como trabajo a futuro declarado, no como capacidad detenida.

## Respuestas de seguridad, listas

### El agente no guarda contraseñas

Respuesta corta, para decir textual: **el sistema no almacena contraseñas ni tiene base de usuarios**. No hay adapter de base de datos cableado: la persistencia del producto es un puerto en memoria que guarda solo referencias opacas y hashes, y los reportes rechazan campos sensibles aunque el valor no esté declarado. En el Anexo 3 el ítem *Almacenamiento de credenciales y contraseñas* está declarado **«No aplica»** con ese motivo, y remite a OWASP A02 y A07.

### Identidad

Cuenta de **servicio** de Google de **DSI**, en un proyecto de Google Cloud de DSI, con domain-wide delegation, que se hace pasar **solo** por la cuenta técnica (`bot_ia1@`); la lista de cuentas suplantables es cerrada y vive en un archivo controlado del repo; si el entorno indica otra cuenta, el agente **no arranca** (ADR 0011, #98). **Nadie inicia sesión con la cuenta técnica.** El proyecto es de DSI, así que no queda nada a nombre del autor (ADR 0007).

El alcance de la delegación sobre todo el dominio es un **riesgo aceptado por DSI** por escrito (correo del 13/10), y está declarado en el Anexo 3 como `A + RA` con su control compensatorio.

### Secretos

El único secreto es la **clave JSON de la cuenta de servicio**: se custodia fuera del repo, en `~/.config/agente1/` del servidor, con `chmod 600`, y se monta en sólo lectura en el contenedor (nunca entra a la imagen). **El disco del servidor no está cifrado** (sin root no se puede): se declara como riesgo aceptado, con el control compensatorio de que la clave sólo se hace pasar por la cuenta técnica y DSI la revoca. La OAuth anterior se dio de baja el 23/10. No se versiona ni se escribe en logs, manifests ni mensajes de error. El proyecto tiene **cero dependencias de runtime** (`dependencies = []`), lo que deja el árbol de dependencias enumerable y sin transitivas.

### Auditoría

Los reportes y la auditoría exponen **códigos, conteos y hashes opacos**; nunca contenido, destinatarios ni cuerpos. Los errores HTTP se mapean **sin filtrar token ni cuerpo**. El token se pide por operación, se valida que no tenga saltos de línea (no se puede inyectar cabecera) y solo se usa en el header `Authorization`. Hay una allowlist de hosts del plano de datos y la auditoría contrasta las llamadas reales contra esa lista.

### Marco

El Anexo 3 cita **OWASP Top 10 for LLM** por ítem (es la referencia que sugirió Maiorano), más OWASP web, MITRE ATT&CK para lo habilitado y NIST CSF una vez a nivel `Sistema`. La prueba de revocación es **local y reproducible**: DSI no hace prueba conjunta, y la revocación del lado de Google queda declarada como responsabilidad de DSI.

### Lo que se declara previsto y no implementado

- **2SV de la cuenta técnica**: prevista, no implementada.
- **Context-Aware Access y eventos de llamadas a API**: exigen Workspace Standard o Plus; con Education Fundamentals quedan declarados como previstos con su justificación.
- **Límite de CPU de los contenedores**: no hay, a propósito, para no penalizar la inferencia en 4 núcleos sin GPU (sí hay techo de memoria y de procesos).
- **Riesgo aceptado**: el acceso a Docker es por Portainer con rol de administrador (equivale a root sobre el host); es la credencial de desarrollo del autor y el agente nunca la recibe.

## Rutas de código por componente (columna *Evidencia versionada* del Anexo 3)

| Componente | Rutas y evidencia |
|---|---|
| Canal | `src/agente1/canal_form.py`; `tests/test_canal_form.py`; `tests/test_canal_planilla.py`; `docs/adr/0005-*.md` |
| Interpretación | `src/agente1/interpretacion.py`; `src/agente1/contracts/intenciones_v3.schema.json`; `src/agente1/contracts/interpretacion_fallback_v3.schema.json`; `tests/test_interpretacion.py` |
| Generación | `src/agente1/procesamiento.py`; `src/agente1/destinos.py`; `src/agente1/ollama.py`; `tests/test_plantillas_actividad.py`; `tests/test_posts.py`; `tests/test_posts_structured.py`; `tests/test_linea_descriptiva.py`; `tests/test_procesar_gacetilla.py`; `tests/test_ollama.py` |
| Gates | `src/agente1/origenes_inscripcion.py`; `src/agente1/tipos_notificacion.py`; `src/agente1/politica_redes.py`; `tests/test_matriz_origenes_inscripcion.py`; `tests/test_politica_redes.py`; `tests/test_tipos_notificacion.py` |
| Control de pagos | `src/agente1/pagos.py`; `src/agente1/cli_pagos.py`; `src/agente1/buzon_gmail.py`; `docs/adr/0003-*.md`; `docs/adr/0004-*.md`; `tests/test_pagos.py`; `tests/test_novedades_pagos.py`; `tests/test_buzon_gmail.py` |
| Aprobación | `src/agente1/decisiones_form.py`; `src/agente1/linea_descriptiva.py`; `evidencias/recorrido-registro-decisiones-form.md`; `tests/test_decisiones_form.py`; `tests/test_linea_descriptiva.py`; `tests/test_certificados_emision.py` |
| Cola y envío | `src/agente1/confirmaciones.py`; `src/agente1/gmail_envio.py`; `evidencias/recuperacion-hu012-idempotencia-durable-2026-09-08.md`; `tests/test_confirmaciones.py`; `tests/test_confirmaciones_durables.py`; `tests/test_gmail_envio.py` |
| Persistencia y auditoría | `src/agente1/persistencia.py`; `src/agente1/auditoria_d2.py`; `src/agente1/operaciones_seguras.py`; `evidencias/auditoria-seguridad-d2-d3.md`; `tests/test_auditoria_seguridad_d2.py` |
| Integraciones | `src/agente1/google_workspace.py`; `evidencias/limites-historia-viva-cliente.md`; `tests/test_auditoria_seguridad_d2.py`; `tests/test_google_sheets.py` |
| Google Workspace | `src/agente1/workspace_auth.py`; `src/agente1/contracts/cuentas_suplantables_v1.json`; `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`; `docs/adr/0011-*.md`; `evidencias/cuenta-servicio-delegada-2026-10-14.md`; `tests/test_workspace_cuenta_servicio.py`; `tests/test_workspace_config.py` |
| Sistema | `.github/workflows/agente1-ci.yml`; `src/agente1/manifest_version.py`; `evidencias/integridad-arranque-2026-10-14.md`; `evidencias/ciclo-migraciones-down-postgresql-2026-10-14.md`; `tests/test_integridad_arranque.py`; `tests/test_manifest_version.py`; `tests/test_migraciones_down_ciclo.py` |

## Qué no se muestra y por qué

No es falta de trabajo: es alcance detenido por un tercero, declarado en el Anexo 1 y en la columna *Estado declarado* de los perfiles.

- **Validación de calidad por referentes de la SEU** (operabilidad, reconocibilidad, prueba guiada de HU-013): prevista, sin validación registrada (#56).
- **Envío real por Gmail y Forms reales de HU-012/HU-014**: el circuito corre completo contra destinos de prueba y la lista de prueba; la emisión real no está configurada.
- **Unidad compartida de Google de D3**: el cómputo ya corre en el servidor, pero los recursos siguen en D2 (#100).
- **Niveles verificados de los SLO** de disponibilidad, tiempo de atención y aprobación a envío: sin medición a la fecha (#88). La latencia por pieza sí está medida en el servidor.
- **Criterio formal del gate**: la Dirección de carrera no fijó un criterio formal; la evidencia se presenta contra el TRL 4 de la documentación del P100 y el go/no-go lo fija el informe del laboratorio.
- **Plantilla de certificado y firma definitivas de la SEU**: corre la plantilla base provisional declarada.
- **Firma digital de certificados**: fuera de alcance, el DoD no la exige.

## Ensayo completo (pendiente: lo corre Juani)

Criterio de aceptación de #114. Registrar acá la corrida, sin maquillar lo que salga mal:

- **Fecha del ensayo:**
- **Duración real:** (objetivo: menos de 60 minutos)
- **Modelo y versión:** (`gemma4:e4b` sobre Ollama 0.40.6, #51; versión del agente según la rama `deploy`)
- **Credencial usada:** (cuenta de servicio de DSI, #99)
- **Bloques que se pasaron de tiempo:**
- **Preguntas de calidad y seguridad que no se pudieron responder en el momento:**
- **Rutas de código que faltó tener a mano:**
- **Correcciones que hay que hacer antes del 2/11:**

## Registro de la prueba presencial

- **Fecha y hora:**
- **Quiénes estuvieron:** (iLab lo ve Maiorano; rLab lo confirma Olivieri, que pidió hablar la parte de redes en persona)
- **Qué pidieron ver del código fuente:**
- **Qué quedó como observación o corrección:**
- **Requisito nuevo del laboratorio, si hubo:**
