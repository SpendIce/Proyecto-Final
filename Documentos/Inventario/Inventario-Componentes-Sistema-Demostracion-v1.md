# Inventario de componentes del sistema de demostración — v1

- **Estado:** vigente.
- **Commit de la base:** `e436aab` (`git rev-parse --short HEAD`, 2026-10-12). Este documento describe esa base; los anexos del laboratorio citan el commit junto con la foto que revisaron.
- **Qué inventaría:** el **sistema de demostración** del Agente 1 (`CONTEXT.md`): el agente en todo su alcance declarado —ambiente, flujos y componentes— funcionando de punta a punta en vivo, sobre el hilo **NotebookLM Nivel 2**, en la revisión de laboratorio y en la mesa final (18/11/2026). Ambiente: laptop del autor con Ollama local + Workspace D2 live con la cuenta técnica (decisión [#49](https://github.com/SpendIce/Proyecto-Final/issues/49)). La corrida offline ensayada (`run-demo.sh`) es el respaldo, no un componente.
- **Qué es un componente:** un módulo de `Implementacion/Agente1/src/agente1/` o un servicio externo del sistema (Ollama, Google Sheets/Drive/Docs/Forms, Gmail).
- **Principio rector:** ningún componente figura como fake ni como capacidad detenida. Lo que depende de un tercero corre contra un **destino de prueba** o un **insumo provisional declarado** (ver § Insumos provisionales), nunca contra un fake.
- **Consumidores:** es la base de los anexos 2 (calidad, #59) y 3 (seguridad, #58) de la revisión de laboratorio.
- **Decisiones que componen el sistema:** #49 (ambiente, recorrido, respaldo, insumos), #52 (canal de pedidos, registro de decisiones, identidad y validación humana por tipo de pieza), #53 (emisión de certificados con lista de cierre), #54 (fuente de actividades: lectura de planilla, no ingesta), #38 (control de pagos). ADR 0001–0006 (`docs/adr/`).

## Regla de mantenimiento

Este inventario **se actualiza en el mismo commit en que un componente entra a `main`**: agregar, mover de capa o quitar un componente sin tocar este archivo deja el inventario desactualizado, y eso es un defecto del commit, no un pendiente documental.

Los anexos 2 y 3 del laboratorio son **una foto de este inventario con el commit de la base**. Si la base crece entre la revisión de laboratorio y la mesa final (decisión #49: no hay congelamiento), el anexo declara la foto que el laboratorio revisó y este archivo sigue describiendo `main`.

## Cómo leer las tablas

- **Capa:** la sección donde aparece la fila. Cuando un componente aporta también a otra capa, se indica en su responsabilidad.
- **HU:** historia de usuario servida —HU-010 gacetilla, HU-011 posts, HU-012 confirmaciones y pagos, HU-013 lenguaje natural, HU-014 certificados— o `transversal`.
- **Ambiente:** `laptop` (proceso local), `Workspace D2` (recurso Google del ambiente de demostración) o `laptop → D2` (módulo local que toca D2). La migración a D3 sólo ocurre si DSI entrega el host y el E2E completo pasa ahí antes de la revisión de laboratorio (#49); hoy el host es la laptop.
- **Dueño op.:** dueño operativo después del traspaso a Informática. `PENDIENTE` en todas las filas: el traspaso está abierto (#63) y define al receptor.
- **Insumo provisional:** remite a la tabla de § Insumos provisionales. `—` significa que el componente no depende de ninguno.
- Los artefactos versionados `contracts/`, `politicas/` y `prompts/` no son módulos: viajan con el módulo que los consume y figuran dentro de su responsabilidad.

## Canal

Transporta pedidos de la SEU hacia el agente y resultados hacia la persona. No es una conversación abierta (glosario `CONTEXT.md`).

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `canal.py` | módulo | Puerto `CanalInteraccion` y bucle `atender_canal`: lee un pedido pendiente, lo pasa al núcleo de interpretación y escribe la respuesta, con estado entre turnos delegado al núcleo. Incluye `CanalInteraccionFake` en memoria para pruebas. No clasifica ni resuelve: eso pertenece al núcleo. Transporta la identidad afirmada, nunca la verifica (ADR 0002). | HU-013 | laptop | PENDIENTE | identidad y rol |
| `canal_planilla.py` | módulo | Adapter offline del canal sobre un directorio CSV (`pedidos.csv` → `respuestas.csv`): permite la prueba guiada con una persona de la SEU sin OAuth ni credenciales. La identidad sale de las columnas de la fila; lo pendiente se calcula comparando archivos, sin reescribir pedidos. | HU-013 | laptop | PENDIENTE | identidad y rol |
| `cli.py` (+`__main__.py`, `__init__.py`) | módulo | Interfaz local de operación: una solicitud → un borrador, JSON en stdout con código de salida por estado. Sin modo Workspace a propósito (salir a Google es el runner E2E con doble opt-in). La usan pruebas, smokes, matrices y la corrida de respaldo. `__main__.py` habilita `python -m agente1`; `__init__.py` fija la API pública del paquete. | HU-010, HU-011 | laptop | PENDIENTE | — |
| Google Form de pedidos + su Sheet de respuestas | servicio externo | Canal declarado del sistema de demostración (#52, ADR 0005): Form restringido al dominio y con correo verificado; el agente sólo lee la Sheet de respuestas (se mantiene la regla «escribir es siempre crear nuevo»). La repregunta vuelve por links prellenados con el id del pedido y la candidata, sin prosa. El adapter que conecta la Sheet con el bucle `atender_canal` es trabajo de #71. | HU-013 | Workspace D2 | PENDIENTE | canal provisional, identidad y rol |

## Interpretación

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `interpretacion.py` | módulo | Seam de HU-013: clasifica la prosa a una **intención** del catálogo cerrado (`contracts/intenciones_v1`), resuelve la actividad por identificador explícito, por búsqueda difusa determinística sobre `fuente.enumerar()` o por repregunta con candidatas (estado entre turnos vía puerto `RegistroPendientes`), con fallback al modelo local validado contra `contracts/interpretacion_fallback_v1`. Despacha a los pipelines de gacetilla y de post. La prosa nunca llega como instrucción al generador y la planilla nunca entra a un prompt (ADR 0001); el registro de interacciones no guarda prosa ni identidad en claro. | HU-013 → HU-010, HU-011 | laptop | PENDIENTE | identidad y rol |

## Generación

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `procesamiento.py` | módulo | Pipeline HU-010 completo: leer la fila, validar campos obligatorios, generar, gate mecánico de salida (estructura anclada + hechos contra la fuente), escribir por el puerto de destino y auditar una línea JSONL con hashes. Fail-closed en cada frontera; el éxito es `PENDIENTE_VALIDACION`. Incluye `FakeGenerator` para regresión determinista. Contrato `gacetilla_input_v1`, prompts `prompts/gacetilla_v*`. | HU-010 | laptop | PENDIENTE | plantilla de gacetilla |
| `posts.py` | módulo | Pipeline HU-011: el modelo devuelve un JSON creativo acotado (`contracts/post_creative_output_v2/v3`) y `_renderizar_post_estructurado` arma el post intercalando los datos de la fuente —el modelo nunca toca un dato institucional—. Gate de hechos sobre la zona creativa, control mecánico de registro rioplatense, hashtags por allowlist y un reintento acotado con feedback de regla. El camino `text-v1` queda sólo por selección explícita. | HU-011 | laptop | PENDIENTE | política de redes, plantilla de gacetilla (criterios editoriales) |
| `certificados.py` | módulo | Lifecycle HU-014: certificado de `ASISTENCIA` o `APROBACION` → circuito de doble aprobación reutilizado de `confirmaciones.py` → emisión con reserva intermedia y reconciliación a `EMISION_INDETERMINADA`. PDF de una página, determinista byte a byte, sólo stdlib; plantilla `certificado_provisional_v1` con marca `BORRADOR — NO EMITIR` (mientras rija la lista de prueba, #53 declara «DOCUMENTO DE PRUEBA — SIN VALIDEZ»). | HU-014 | laptop | PENDIENTE | plantilla y firma del certificado |
| `presupuesto.py` | módulo | Dimensiona `num_predict` contra el contrato vigente: documento máximo admisible × relación caracteres/token menos favorable medida con el tokenizador real (`MEDICION_DOCUMENTO_MAXIMO_V3`, DEF-A1-013). | transversal generación | laptop | PENDIENTE | — |
| `ollama.py` | módulo | Adapter del generador local: sólo loopback (impedido en código), `temperature: 0`, `format_schema` opcional con hash auditado, detección de `done_reason == "length"` y errores colapsados para que el prompt nunca llegue al log. | HU-010, HU-011, HU-013 | laptop | PENDIENTE | — |
| Ollama (runtime local) | servicio externo | Runtime user-local en `Implementacion/Agente1/.runtime/` (ignorado por Git), con `llama3.2:3b` y `llama3.1:8b` descargados, escuchando en loopback. El agente no administra el runtime: lo exige ya iniciado. | HU-010, HU-011, HU-013 | laptop | PENDIENTE | — |

## Gates

Controles fail-closed que deciden antes de generar, escribir o tocar el registro. Los gates mecánicos de salida de gacetilla y de hechos de post viven dentro de `procesamiento.py` y `posts.py` (capa Generación).

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `politica_redes.py` | módulo | Política de redes como inventario de reglas verificables (`politicas/politica_redes_provisional_v1.json`): 20 reglas con estado `ACTIVA` (con código de gate y caso negativo), `NO_APLICADA_PENDIENTE_SEU` o `NO_MECANIZABLE`, más parámetros por canal y allowlist de hashtags. | HU-011 | laptop | PENDIENTE | política de redes |
| `tipos_notificacion.py` | módulo | Catálogo cerrado de tipos de notificación (`contracts/tipos_notificacion_v1.json`) con evaluación fail-closed antes de tocar el registro: un tipo fuera del catálogo es `INVALIDA`. `situacion_pagos` está declarada: su fuente ya está confirmada (#38) y su implementación corre por los tickets #39–#47. | HU-012 | laptop | PENDIENTE | — |
| `origenes_inscripcion.py` | módulo | Matriz operativa por origen de inscripción (`contracts/matriz_origenes_inscripcion_v1.json`) con decisión de envío fail-closed: enumera por origen qué dato falta (`id_inscripcion`, nombre interno del estado habilitante, administrador del padrón por entorno, medio autorizado) en vez de habilitar a ciegas. | HU-012 | laptop | PENDIENTE | matriz de orígenes |

## Aprobación

La validación humana: aprobación semántica y utilitaria de la plantilla aprobada, aprobación de lote y decisión de publicación (glosario `CONTEXT.md`, decisión #52). El circuito in-code —doble aprobación, estados parciales, idempotencia de la decisión— está implementado dentro de `confirmaciones.py` (capa Cola y envío) y reutilizado por `certificados.py` (capa Generación).

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| Google Form de registro de decisiones | servicio externo | Segundo Form al que se llega por links prellenados en los correos del agente: registra aprobaciones de plantilla (semántica y utilitaria), aprobaciones de lote y decisiones de publicación, con correo verificado por Google (#52; implementación #72). La decisión de publicación de una pieza de difusión no gatilla nada en el agente. | transversal | Workspace D2 | PENDIENTE | canal provisional, identidad y rol |
| Padrón de roles | recurso externo | Mapea correo verificado → rol autorizado (ADR 0005): los roles son los que la SEU designó por escrito (acta del 22/09; semántica Juan Manuel, utilitaria y firma Moreira). Quien no está en el padrón, o no tiene el rol que la decisión exige, queda rechazado y registrado. Vive fuera del repo y lo mantiene provisionalmente el autor. | transversal | fuera del repo (D2) | PENDIENTE | padrón provisional |

## Cola y envío

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `confirmaciones.py` | módulo | Lifecycle HU-012 completo: borrador → `APROBADA_SEMANTICA`/`APROBADA_UTILITARIA` → `APROBADA` → `ENVIO_RESERVADO` → entrega. Cola `ColaEnvios`/`ColaEnviosArchivo` con `drenar_envios` (pista de trabajo, nunca la autoridad), registro durable archivo-por-clave (`os.link` + `flock`), reconciliación de reservas colgadas a `ENVIO_INDETERMINADO` e idempotencia por clave con el tipo de notificación dentro. El destino productivo declarado es Gmail con lista de prueba (#40); el puerto `DestinoConfirmaciones` admite hoy un único destino, que #40 reemplaza por el adapter Gmail. | HU-012 | laptop | PENDIENTE | plantilla de actividad para correos, envío a lista de prueba |
| Gmail — envío | servicio externo | `gmail.send` desde la cuenta técnica, restringido a una lista de direcciones de prueba que sale de la configuración fuera del repo: un destinatario fuera de la lista se rechaza antes de cualquier llamada de red (#40). También transporta el correo de aviso del canal de pedidos (#71) y el certificado adjunto al titular (#53, #75). | HU-012, HU-014, HU-013 | Workspace D2 | PENDIENTE | envío a lista de prueba |
| Gmail — buzón propio | servicio externo | `gmail.readonly` sólo sobre el buzón de la cuenta técnica: lee los **comprobantes presentados** que el Departamento reenvía con un filtro desde `cursoscomplementarios@` (ADR 0004). Es una de las fuentes confirmadas de situación de pagos (#38), junto con las novedades de pago y el plan de pago. | HU-012 | Workspace D2 | PENDIENTE | — |

## Persistencia y auditoría

La persistencia operativa del sistema la producen `procesamiento.py` (log JSONL `logs/ejecuciones.jsonl` con hashes), `confirmaciones.py` (registro durable por clave) y `workspace_e2e.py` (manifest sanitizado por ejecución + reservas de idempotencia): figuran en sus capas. Esta sección agrupa los componentes dedicados a auditar y operar esas evidencias. El puerto `persistencia.py` queda fuera del sistema (ver § Módulos fuera del sistema de demostración).

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `auditoria_d2.py` | módulo | Auditoría offline y fail-closed de invariantes de seguridad D2/D3 sobre un manifest ya sanitizado: logs redactados, recursos allowlisteados, errores remotos sin datos, ausencia de endpoints de distribución, revocación que bloquea y salidas que son borradores. El reporte expone códigos, conteos y hashes opacos: nunca contenido. | transversal | laptop | PENDIENTE | — |
| `operaciones_seguras.py` | módulo | Contratos operativos fail-closed sobre manifests sanitizados: health (única capacidad live admitida: una lectura sin argumentos), reconciliación, consolidación y plan de retención en dry-run. Sus salidas son planes o reportes: nunca publica, comparte, borra ni modifica recursos. | transversal | laptop | PENDIENTE | — |

## Integraciones

| Componente | Tipo | Responsabilidad | HU | Ambiente | Dueño op. | Insumo provisional |
|---|---|---|---|---|---|---|
| `fuentes.py` | módulo | Puerto `FuenteSolicitudes` de sólo lectura —`obtener` por id y `enumerar` el catálogo— y adapter CSV compatible con el flujo local y el respaldo. Errores por código estable para la auditoría. `COLUMNAS_GACETILLA` fija el contrato vigente de la planilla (migra a la v2 por #77). | transversal entrada | laptop | PENDIENTE | planilla de actividades |
| `destinos.py` | módulo | Puerto `DestinoBorradores` deliberadamente limitado a *guardar* —no existen compartir, enviar, publicar ni permisos— y adapter Markdown local. Revalida la marca `BORRADOR — NO PUBLICAR` y la allowlist de identificadores; las referencias son opacas hacia arriba. | transversal salida | laptop | PENDIENTE | — |
| `google_workspace.py` | módulo | Adapters HTTP a mano (sin SDK, superficie auditable): lee la planilla (Sheets), copia la plantilla en la carpeta autorizada (Drive) y vuelca el borrador (Docs `create` + `batchUpdate`). Deadline absoluto, tope 1 MiB por respuesta, errores a códigos por servicio y 401/403 sin reintento; `docs_update_failed_orphaned` informa un hash de reconciliación. Escribir es siempre crear nuevo. | HU-010, HU-011 | laptop → D2 | PENDIENTE | plantilla de documento |
| `workspace_config.py` | módulo | Configuración de Workspace por entorno (`AGENTE1_WORKSPACE_*`) validada de una sola vez: sin defaults para identificadores, rechaza claves desconocidas del prefijo y `resumen_seguro()` publica sólo hashes. Incluye `TokenEntornoProvider`, el camino original con access token efímero. | transversal D2 | laptop | PENDIENTE | — |
| `workspace_auth.py` | módulo | Credencial durable: `OAuthRefreshTokenProvider` mintea access tokens por intercambio contra `oauth2.googleapis.com/token` —único host habilitado fuera del plano de datos— y `construir_token_provider()` prefiere el trío `AGENTE1_WORKSPACE_OAUTH_*` completo. El intercambio tiene deadline, tope y nunca se reintenta. | transversal D2 | laptop → D2 | PENDIENTE | — |
| `workspace_e2e.py` | módulo | Runner de punta a punta planilla → generación → documento: reserva de idempotencia `O_EXCL` antes de escribir, política `manual_only` ante una ejecución cortada (nada de takeover automático), manifest sanitizado por ejecución y modo live con doble opt-in (`habilitar_live` + `confirmar_escritura`) sobre ambiente D2/D3. | HU-010, HU-011 | laptop → D2 | PENDIENTE | — |
| Google Sheets — planilla de actividades | servicio externo | Fuente de actividades del sistema: una fila por actividad. **La original es la pestaña de D2**; el CSV del repo es una copia exportada para pruebas y respaldo. El Agente 1 la lee y nunca la escribe (ADR 0006). Su pestaña de plan de pago, unida por `id_actividad`, alimenta el control de pagos (#38). | HU-010, HU-011, HU-013, HU-012, HU-014 | Workspace D2 | PENDIENTE | planilla de actividades (carga Juani) |
| Google Drive — carpeta autorizada y plantilla | servicio externo | Carpeta autorizada de la cuenta técnica donde vive la plantilla de documento que se copia por borrador; una carpeta restringida de la misma cuenta aloja las imágenes de firma cuando la SEU las entregue (#53). | HU-010, HU-011, HU-014 | Workspace D2 | PENDIENTE | plantilla de documento, firmas |
| Google Docs — documentos de borrador | servicio externo | Cada borrador es una copia de la plantilla con título `BORRADOR — NO PUBLICAR — <id>`, creada por las dos operaciones del adapter. Nada existente se modifica, comparte ni publica. | HU-010, HU-011 | Workspace D2 | PENDIENTE | plantilla de documento |
| Google Sheets — lista de cierre | servicio externo | Sheet D2 con la **lista de cierre** de la actividad —nombre, apellido, DNI, mail, tratamiento y condición— que carga quien gestiona el curso: fuente única de quién recibe certificado y de qué tipo; el agente nunca infiere un resultado académico (#53). | HU-014 | Workspace D2 | PENDIENTE | lista de cierre |

## Sección transversal — identidad y credenciales

Sección **documental**: declara qué existe y dónde vive. Ningún valor sensible figura en este archivo ni en el repo.

| Elemento | Qué es y dónde vive |
|---|---|
| Cuenta técnica | Cuenta Google **dedicada** del Agente 1, institucional del dominio de la FIE, provisionada por DSI. Su dirección vive fuera del repo. Es la identidad definitiva con la que el agente opera contra Workspace y Gmail: no es un insumo provisional. |
| Credencial OAuth durable | Trío `AGENTE1_WORKSPACE_OAUTH_{CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN}` leído del entorno por `OAuthRefreshTokenProvider` (`workspace_auth.py`), que mintea access tokens contra `oauth2.googleapis.com/token` —único host fuera del plano de datos—. Proyecto GCP dentro de la organización `fie.undef.edu.ar` con consent screen *Internal*: refresh token durable, sin la caducidad de 7 días. Verificado live el 2026-09-28 (smoke con access token vencido que sólo pudo salir del minteo). |
| Credencial efímera heredada | `AGENTE1_WORKSPACE_ACCESS_TOKEN` (~1 h de vida, consentimiento manual) vía `TokenEntornoProvider` (`workspace_config.py`). Queda como camino manual; el provider prefiere el trío OAuth cuando está completo. |
| Env file | `~/.config/agente1/workspace-d2.env` (chmod 600, **fuera del repo**; backup `workspace-d2.env.bak`): ambiente, ids de planilla/carpeta/plantilla —referenciados por hash en la evidencia—, el trío OAuth y la lista de direcciones de prueba de Gmail. |
| Scopes OAuth concedidos | `documents`, `drive`, `spreadsheets`, `gmail.send` y `gmail.readonly` (2026-10-07, #41). El aviso a DSI por los scopes de Gmail quedó pendiente (decisión D11 de Juani). |
| Reglas vigentes | Ningún secreto se versiona ni se escribe en logs, manifests ni mensajes de error: los reportes publican hashes (`resumen_seguro()`). El token no se acepta como flag de CLI. La revocación detiene al agente (`workspace_token_exchange_denied`, `workspace_auth_denied`). El plano de datos queda limitado a los hosts declarados (Sheets, Docs, Drive y, declarado por #40, el endpoint de envío de Gmail). |
| Decisiones abiertas relacionadas | El modelo de seguridad de la cuenta (#64, bloqueado por #61/#62/#63) y el traspaso con rotación por el receptor (#63) siguen abiertos: son decisiones de diseño, no insumos provisionales. |

## Insumos provisionales

Todo lo que depende de un tercero y hoy corre contra un **destino de prueba** o un **insumo provisional declarado**. Nada de esto corre contra un fake. La meta es conseguir el original; el reemplazo es el plan B, con fecha límite en la entrega de los anexos al laboratorio (#49).

| Insumo | Marca | Cómo corre hoy | Reemplazo | Pedido abierto |
|---|---|---|---|---|
| Plantilla de gacetilla | `PENDIENTE_SEU` | Prompts y estructura provisionales versionados (`prompts/gacetilla_v*`, contrato `PROVISIONAL_NO_INSTITUCIONAL`) | Plantilla base y ejemplos aprobados por la SEU | #14 |
| Política de redes (límites, allowlist de hashtags, criterios editoriales) | `PENDIENTE_SEU` | `politica_redes_provisional_v1.json`, fijado por el equipo técnico (DEF-A1-007) | Política aprobada por la SEU | #14 |
| Plantilla de certificado | `PENDIENTE_SEU` | `certificado_provisional_v1` versionada, armada con los campos confirmados | Plantilla base de la SEU | #76 |
| Firma del certificado | `PENDIENTE_SEU` | Bloque con nombre y cargo de los dos firmantes (Secretario de Extensión y Decano) más recuadro vacío declarado provisional; las imágenes de firma vivirán en una carpeta D2 restringida de la cuenta técnica, nunca versionadas. La firma digital del enunciado queda fuera de alcance (#53) | Imágenes de firma provistas por la SEU junto con la plantilla | #76 |
| Envío a destinatarios reales | `DESTINO DE PRUEBA` | `gmail.send` restringido a la lista de direcciones de prueba configurada fuera del repo; marca de prueba en el cuerpo | Lista de destinatarios real, tras la aprobación de cada plantilla por la SEU (D12 de #38) | #40 |
| Identidad y rol del personal | `PROVISIONAL` | Canal offline/planilla: identidad afirmada (ADR 0002). Canal Form: correo verificado por Google + rol por padrón (ADR 0005, provisional) | Confirmación con Dirección de Carrera; padrón mantenido por la SEU | #69 |
| Canal de pedidos y registro de decisiones | `PROVISIONAL` | Google Forms restringidos al dominio con links prellenados (#52) | Confirmación de Cicerchia y Carullo | #69, #71, #72 |
| Planilla de actividades de D2 | `INSUMO PROVISIONAL DECLARADO` | La pestaña D2 la carga el autor; el CSV del respaldo es una copia exportada con fecha (contrato vigente v1; la v2 es #77) | Carga por la SEU o por Historia Viva (ADR 0006, #54) | #77, #78 |
| Datos supuestos de la fila NotebookLM Nivel 2 (año de las fechas, `organiza`) | `SUPUESTO_TECNICO` | Valores supuestos declarados al cargar la fila: los documentos no los informan | Confirmación de la SEU | #78 |
| Lista de cierre | `INSUMO PROVISIONAL DECLARADO` | Sheet D2 cargada por quien gestiona el curso, con personas sintéticas (#53) | Export del SIU o carga real de la SEU | #75 |
| Padrón de roles | `PROVISIONAL` | Recurso fuera del repo mantenido por el autor, con los roles del acta del 22/09 | Padrón mantenido por la SEU tras confirmación de Dirección | #69 |
| Plantilla de actividad para los correos de HU-012 | `PENDIENTE_SEU` | `confirmacion_inscripcion_provisional_v1` versionada; el modelo redacta la prosa descriptiva y los datos quedan como variables (#52) | Plantilla base aprobada por la SEU | #73, #14 |
| Matriz de orígenes de inscripción (id de inscripción, nombre interno del estado, administrador del padrón, medio autorizado) | `SUPUESTO_TECNICO` / `DESCONOCIDO` | `matriz_origenes_inscripcion_v1.json` fail-closed: lo `DESCONOCIDO` bloquea el envío por ese origen | Datos confirmados por la SEU | #14 (acta 22/09 deja abiertos esos campos) |
| Host D3 | `PROVISIONAL` (hoy laptop) | El sistema corre en la laptop del autor + D2 | Host D3 entregado por DSI, sólo si el E2E completo pasa ahí antes de la revisión de laboratorio | DSI (#62) |

**Confirmado, no provisional:** la fuente de situación de pagos —comprobantes presentados en el buzón propio, novedades de pago y plan de pago (#38, ADR 0003/0004)—; la cuenta técnica; el mecanismo de credencial por refresh token. El certificado no exige firma digital: queda fuera de alcance por DoD (#53).

## Módulos fuera del sistema de demostración

Módulos de `src/agente1/` que no integran el sistema de demostración en esta base, con su justificación. Ninguno figura como fake ni como capacidad detenida: son seams o puertos que el recorrido de la demo no invoca.

| Módulo | Justificación |
|---|---|
| `persistencia.py` | Puerto de persistencia auditable con adapter en memoria y esquema SQL del spike PostgreSQL (`migrations/`). No está cableado a los pipelines: la persistencia del sistema de demostración la producen el registro durable de `confirmaciones.py`, el log JSONL de `procesamiento.py` y los manifests y reservas de `workspace_e2e.py`. |
| `historia_viva.py` | Puerto de consulta a Historia Viva (A2) y composición de efemérides del lado de A1. Seam offline sin adapter de transporte: el contrato A1↔A2 es candidato no institucional y el issue #17 sigue abierto. El hilo de demostración no lo invoca. |
| `historia_viva_cliente.py` | Cliente pull sobre transporte inyectado de ese mismo puerto; misma justificación: sin transporte ni contrato cerrado, no forma parte del recorrido. |
| `insumos_agentes.py` | Validador del contrato candidato inbound de insumos A2–A5 (`contracts/insumos/`). Es la dirección push, sin transporte ni consumidor en el hilo de demostración. |

No son módulos de `src/agente1/` y quedan fuera por definición: `scripts/` (matrices, mediciones, smokes, wizards), `tests/`, `migrations/`, `data/`, `golden/`, `evidencias/` y `run-demo.sh` (respaldo offline declarado).

## Cobertura de `src/agente1/`

| Módulo | Dónde aparece |
|---|---|
| `auditoria_d2.py` | Persistencia y auditoría |
| `canal.py` | Canal |
| `canal_planilla.py` | Canal |
| `certificados.py` | Generación |
| `cli.py` | Canal (incluye `__main__.py` y `__init__.py`) |
| `confirmaciones.py` | Cola y envío (su circuito de aprobación sostiene la capa Aprobación) |
| `destinos.py` | Integraciones |
| `fuentes.py` | Integraciones |
| `google_workspace.py` | Integraciones |
| `historia_viva.py` | Fuera del sistema (justificado) |
| `historia_viva_cliente.py` | Fuera del sistema (justificado) |
| `__init__.py` | Canal, dentro de la fila de `cli.py` (API pública del paquete) |
| `insumos_agentes.py` | Fuera del sistema (justificado) |
| `interpretacion.py` | Interpretación |
| `__main__.py` | Canal, dentro de la fila de `cli.py` (entry point `python -m agente1`) |
| `ollama.py` | Generación |
| `operaciones_seguras.py` | Persistencia y auditoría |
| `origenes_inscripcion.py` | Gates |
| `persistencia.py` | Fuera del sistema (justificado) |
| `politica_redes.py` | Gates |
| `posts.py` | Generación |
| `presupuesto.py` | Generación |
| `procesamiento.py` | Generación |
| `tipos_notificacion.py` | Gates |
| `workspace_auth.py` | Integraciones |
| `workspace_config.py` | Integraciones |
| `workspace_e2e.py` | Integraciones |
