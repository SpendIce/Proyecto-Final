# Plan de recuperación del MVP — Agente 1

- **Ventana de recuperación:** 17 al 28 de agosto de 2026
- **Fecha de actualización documental:** 6 de septiembre de 2026
- **Alcance:** HU-010 + HU-011, Proceso 4
- **Estado actualizado:** HU-010 `PARCIAL`; HU-011 `PARCIAL` con regresión integral canónica de 513 pruebas verdes fuera del sandbox; Gate G2 / TRL 3 `PENDIENTE`

## 1. Objetivo

Recuperar el camino de valor del MVP sin adelantar infraestructura que no resuelve el gate: datos estructurados → generación local → borrador no publicable → validación humana → evidencia. FastAPI, LangGraph, PostgreSQL, Celery y Redis no son condición para demostrar este slice controlado y se difieren mientras no exista una necesidad operativa validada.

## 2. Principios de ejecución

1. Consolidar la evidencia offline ya lograda y priorizar los incrementos live y la validación faltante.
2. Mantener toda salida como `BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`.
3. No usar datos reales sin autorización registrada.
4. No declarar Workspace live por pruebas con transporte fake.
5. No declarar validación SEU sin persona, rol, fecha, puntaje y decisión.
6. No declarar TRL 3 por avance documental o suite verde únicamente.

## 3. Rebaseline 17–28 de agosto

| Fecha objetivo | Frente | Entregable verificable | Responsable | Dependencia | Criterio de salida |
|---|---|---|---|---|---|
| 17–20/08 | HU-011 — contrato | Contrato de entrada, políticas provisionales por canal, prompts y goldens Instagram/LinkedIn | Juan Ignacio Gone | Ninguna para versión provisional | **Completado offline en `537402a`:** versiones explícitas, seis goldens y pruebas; sin publicación |
| 17–20/08 | Gestión institucional | Pedido consolidado de recursos, validadores y criterio G2 | Juan Ignacio Gone | Josefina, SEU, Vera/DSI y César | Solicitud enviada y responsables/fechas registrados; no basta para cerrar |
| 21–24/08 | HU-011 — pipeline | Procesador, CLI, longitud configurable, limpieza y deduplicación de hashtags | Juan Ignacio Gone | Contrato técnico provisional | **Completado offline en `537402a`:** suite integral de 151 pruebas y smoke fake verdes |
| 21–24/08 | HU-011 — matriz | Casos sintéticos completos/incompletos para ambos canales | Juan Ignacio Gone | Pipeline HU-011 | **Completado offline:** diez ejecuciones, hashes, correlation IDs, seis pendientes y cuatro incompletas |
| 25–26/08 | HU-011 — LLM/evidencia | Smoke Ollama y manifest; checklist por canal | Juan Ignacio Gone | Runtime user-local `0.32.14-1` restaurado e ignorado | **Ejecutado, resultado `NO_CONFORME`:** 6/6 transportes, 0 timeouts, 0/6 conformes y 0 borradores (`aa4765e`) |
| 25–27/08 | HU-011 — experimentos v2/v3/v4 | Salida estructurada, constrained decoding y render determinista | Juan Ignacio Gone | Runtime `0.32.14-1`; seis intentos por corte | **Cierre técnico versionado en `db06b3e`:** v2 0/6 `json_invalid`; v3 histórico 0/6 HTTP 400 grammar; v4 6/6 técnicas, 7,035854–29,485820 s |
| 25–27/08 | Seguridad y regresión | Prompt injection, acciones no autorizadas, redacción de secretos, suite HU-010/HU-011 | Juan Ignacio Gone | Implementación técnica cerrada | **Completado offline en `5484684`:** harness PASS; validación live D2/D3 pendiente |
| 25–28/08 | Workspace E2E | Sheets → HU-010/HU-011 → Drive/Docs → manifest e idempotencia | Juan Ignacio + Vera/DSI | Identidad, APIs, Sheet, Doc/Drive | **Completado offline con fakes:** live D2/D3 sigue bloqueado |
| 25–28/08 | Validación | Muestra HU-010/HU-011 revisada con escala 1–4 | Validadores SEU | Designación, plantilla y guía de canal | **Paquete listo en `1264d59`:** nueve muestras/17 referencias; acta y decisiones continúan `PENDIENTE` |
| 25–28/08 | Persistencia Sprint 3 | Puerto, adapter memoria, SQL y migraciones contractuales | Juan Ignacio + DSI | PostgreSQL/driver/entorno efímero | **Spike validado en PostgreSQL 16 efímero:** `0001→0003`, rechazos temporales, rollback y forward final; no existe adapter ni reemplazo de JSONL |
| 25–28/08 | Operaciones | Health, reconciliación, consolidación y retención | Juan Ignacio + DSI | Manifests sanitizados; probes DSI | **Tooling offline candidato:** sin escritura/borrado y sin probes live |
| 25–28/08 | HU-012 | Confirmación contractual con HITL e idempotencia | Juan Ignacio + SEU/DSI | Plantilla, validadores y transporte autorizados | **Implementado y verificado offline:** no Gmail/SMTP, email real ni aprobación SEU |
| Rebaseline documental 06/09 | Verificación y estado | Suite integral canónica: 513 pruebas verdes fuera del sandbox; no sustituye validación institucional | Juan Ignacio Gone | Evidencia técnica registrada en el incremento posterior del 26/08 | Mantener trazabilidad del corte y conservar Workspace live, validación SEU y Gate G2 como pendientes |
| 28/08 | Gate | Auditoría del paquete y decisión go/no-go | César Cicerchia + SEU | Evidencia completa | Acta o informe; sin declaración automática de TRL |

Las fechas institucionales son objetivos de coordinación, no compromisos confirmados. Si una dependencia externa no llega, se registra como bloqueante y no se falsea el cierre.

## 4. Dependencias y pedidos concretos

### Avance técnico confirmado

- HU-011 multicanal fue incorporada en `537402a`.
- Los smokes fake y matrices contractuales de HU-010/HU-011 finalizaron verdes.
- `5484684` agregó preparación D2/Drive y seguridad offline, pero ninguna corrida Workspace live.
- La suite conjunta del paquete versionado anterior registró 265 pruebas; no describe la candidata actual.
- `b187960` agregó un contrato candidato A2–A5 inbound: A1 valida insumos, no orquesta agentes y aún no integra esos envelopes a HU-010/HU-011.
- `1264d59` preparó nueve muestras y 17 referencias para SEU; el acta sigue `PENDIENTE` y no existe validación real.
- `aa4765e` registró el baseline HU-011 v1: transporte operativo, 0/6 conformes y cero borradores.
- El runtime user-local Ollama `0.32.14-1` quedó restaurado e ignorado por Git.
- El cierre structured v2/v3/v4 quedó versionado en `db06b3e`: v2 falló 0/6 por `json_invalid`; v3 histórico falló 0/6 por HTTP 400 de grammar; v4 corrigió la incompatibilidad y obtuvo 6/6 aceptaciones técnicas.
- Workspace E2E, persistencia, operaciones y HU-012 están preparados sólo offline en el worktree: no demuestran servicios institucionales operativos.
- La verificación integral histórica del 26/08 terminó con **457 pruebas verdes fuera del sandbox**. El incremento posterior registrado en ese mismo corte alcanzó **513 pruebas verdes**, conteo canónico para esta actualización documental del 06/09. Las 16 fallas de loopback `EPERM` son una restricción ambiental del sandbox y no se reproducen fuera de él.
- El cierre técnico previo está versionado en `db06b3e`; los cambios posteriores deben conservar trazabilidad antes de un nuevo commit, sin inventar hashes.
- Continúan pendientes Workspace live, validación SEU, SLA y decisión G2.

### Josefina Carullo / Coordinación de Extensión

- planilla, encabezados y campos obligatorios definitivos;
- plantilla de gacetilla y carpeta de borradores;
- criterios de tono, longitud, CTA y hashtags para Instagram y LinkedIn;
- entre tres y cinco casos representativos autorizados;
- flujo de corrección, aprobación y rechazo.

### Secretaría de Extensión

- validadores titulares y suplentes para HU-010 y HU-011;
- responsable Gestión del Conocimiento y responsable RRSS;
- agenda de validación;
- decisión registrada por cada caso, sin autorizar publicación automática.

### Vera Batista / DSI

- administrador nominal;
- identidad técnica del dominio `@fie.undef.edu.ar` y mecanismo OAuth acordado;
- proyectos, APIs, scopes, secretos y revocación por ambiente;
- recursos D2/D3 y host Ollama;
- smoke positivo/negativo de permisos y evidencia sin secretos.

### César Cicerchia

- evidencia mínima y firmantes del Gate G2;
- confirmación de cierre conjunto HU-010/HU-011;
- instrumento formal de go/no-go y aceptación de umbrales de performance.

## 5. Criterios de decisión

### GO técnico para presentar el paquete a evaluación G2

Se puede solicitar la evaluación únicamente si:

1. HU-010 y HU-011 generan borradores desde datos controlados;
2. ambas tienen casos positivos y negativos, logs y correlation ID;
3. existen prompts, contratos, goldens, outputs y manifests versionados;
4. no hay publicación, envío, sharing ni acción externa no autorizada;
5. cero defectos críticos abiertos;
6. todos los defectos altos están cerrados o aceptados formalmente con responsable y fecha;
7. las validaciones humanas requeridas están completas y vinculadas a cada output;
8. la evidencia del gate está indexada y recuperable.

### NO-GO del Gate G2 / TRL 3

Corresponde `NO-GO` si ocurre cualquiera de estas condiciones:

- falta HU-010 o HU-011 en el paquete;
- HU-011 no conserva una salida conforme después de la regresión integral fuera del sandbox;
- sólo existen fakes/adapters offline cuando el DoD exige integración controlada;
- no hay validación humana identificable;
- existe contenido que inventa hechos o evade el estado de borrador;
- existen secretos expuestos o permisos excesivos no aceptados;
- hay defectos críticos o altos sin tratamiento aceptado;
- la evidencia no permite reconstruir la ejecución;
- César/SEU no definieron o no registraron la decisión formal.

Un `NO-GO` no invalida el proyecto: preserva la frontera entre prototipo técnico y nivel de madurez demostrado.

## 6. Alcance diferido y spikes

PostgreSQL fue abordado únicamente como spike contractual: puerto, adapter memoria y migraciones validadas en un PostgreSQL 16 efímero, sin driver ni operación institucional live. No debe presentarse como persistencia operativa ni como reemplazo de JSONL. Celery, Redis, FastAPI y LangGraph continúan diferidos hasta que volumen, concurrencia o integración justifiquen su costo. Tampoco se implementan APIs de Instagram o LinkedIn: HU-011 produce borradores, no publica.

## 7. Estado esperado al 28/08

- **Estado técnico al corte documental 06/09:** suite integral canónica de 513 pruebas verdes fuera del sandbox; cero fallas no ambientales reportadas en ese corte y revisión de scope documentada.
- **Mejor caso institucional posterior:** D2 operativo, validación SEU registrada, SLA acordado y paquete listo para decisión G2.
- **Caso vigente:** HU-011 conserva conformidad técnica/offline y regresión integral canónica; D2, SEU y la decisión G2 siguen abiertos; G2 `PENDIENTE`.
- **Condición prohibida:** declarar TRL 3 por calendario, commits o cantidad de pruebas sin evidencia institucional exigida.
