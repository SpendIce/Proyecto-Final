# Arquitectura multiagente P100 en tres capas

**Propuesta de Juan Ignacio Goñe para llegar a una vista común con Ignacio Becerra Mas Roca.**
Corte de evidencia: lunes 19/10/2026, noche. Presentación de avance: miércoles 21/10/2026, 9:00.

## 1. Propósito

El correo de Cicerchia del 20/03/2026 asigna el punto de partida:

> «Ignacio: vas iniciar con Juan la definición de una arquitectura multiagente, segura, fiable e interoperable, apta para los 5 agentes.»

Ese mandato es conjunto. Esta propuesta no intenta cerrarlo sola: ordena lo que hoy existe, lo que la bible proyecta y la frontera del Agente 1, para que Juani e Ignacio puedan mostrar la misma vista el 21/10 o corregirla antes. La cita se toma del Markdown operativo del correo, que conserva la forma literal «vas iniciar».

La pregunta que responde el documento es acotada: **qué compone hoy la arquitectura compartida, qué se difiere y con qué condición de entrada, y dónde termina el Agente 1**. No es un diseño de detalle de los cinco agentes ni un reemplazo de la documentación oficial.

**Síntesis para la mesa.** Hoy hay un bus de entrada, un contrato pull, una identidad y un host con evidencia; el resto es horizonte con condición de entrada; A1 es nodo, no orquestador.

## 2. Alcance

- Cubre el Proyecto Centenario (P100), sus cinco agentes (A1 a A5) y los siete flujos de orquestación de la bible.
- Toma como caso concreto y evidencia principal al Agente 1, Extensión Bot, porque es el único agente con implementación en este repositorio.
- Distingue tres capas: lo compartido hoy con evidencia, lo proyectado por la bible con condición de entrada, y la frontera funcional de A1.
- El corte de evidencia es el 19/10/2026. Lo que ocurra el 21/10 en el servidor se agrega después, no se presume acá.

## 3. Qué NO decide

- **No elige modelo ni configuración de inferencia.** Esa decisión está en el ticket #51; la medición del servidor del 19/10 sólo informa conformidad, latencia y timeout, y lo dice explícitamente en su sección 6.
- **No cambia el alcance, las historias de usuario, las prioridades ni el RACI.** El alcance funcional sigue en la bible y en el anteproyecto.
- **No reemplaza la bible.** Si hay conflicto entre esta lectura y `Contenido/bible/Procesos y Agentes.md`, gana la bible.
- **No declara TRL, Gate G2 ni validación SEU.** Esas declaraciones requieren evidencia institucional y decisión registrada.
- **No cierra contratos con A2, A3, A4 ni A5.** Propone una forma de leerlos y marca qué falta acordar con el dueño de cada agente.

## 4. Cómo se leen los estados

| Estado | Significado en este documento |
|---|---|
| **Implementado** | Corre en el repositorio y tiene evidencia versionada. Puede ser offline: no implica TRL, validación SEU ni corrida en el servidor. |
| **Por contrato** | Existe contrato, envelope o esquema versionado y una prueba contra mock o fake. Falta la contraparte real o la corrida live. |
| **Proyectado** | Está en la bible o en el plan, pero no tiene contraparte ni contrato probado. Se enciende sólo si se cumple su condición de entrada. |

Una misma pieza puede tener un tramo implementado y otro proyectado. Cuando eso pasa, se dice en la justificación y no se colapsa en un estado optimista.

---

## 5. Capa 1. Lo compartido hoy, con evidencia

«Compartido» no significa «productivo en vivo». Significa que existe un artefacto, una decisión o una interfaz que los dos equipos pueden mirar hoy, con un límite declarado. Todo lo que no tenga archivo, ADR o issue verificable queda fuera de esta capa.

| Pieza | Qué hay hoy | Evidencia exacta | Límite declarado |
|---|---|---|---|
| **Pestaña «Insumos de agentes» en la planilla D2, como punto de entrada de A1 y convergencia con el bus** | El mecanismo acepta filas de A3, A4 y A5, o del productor provisional declarado mientras esos agentes no existan, con el envelope `agente1.insumo.v1`; A1 las sondea con una corrida manual o un scheduler local, valida el envelope, responde el estado en la fila y procesa cada `correlation_id` una sola vez. A2 no entrega insumos: se consulta. | ADR 0008 (`docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`); `Implementacion/Agente1/README.md`, sección «Corrida de insumos de agentes»; `Implementacion/Agente1/src/agente1/insumos_agentes.py`, `insumos_corrida.py`, `insumos_sheets.py`, `cli_insumos.py`; `Implementacion/Agente1/evidencias/runbook-corrida-insumos-a3-evento-hu010.md`. | Implementado y probado offline. La corrida live sobre D2 está preparada en el runbook y **no ejecutada**. Hoy sólo el tipo `evento` de A3 tiene pipeline (HU-010); A4 y A5 quedan «aceptado sin flujo». La pestaña es el punto de entrada propio de A1, no el bus conjunto ya operativo. |
| **Contrato HTTP `/v1` con Historia Viva** | OpenAPI 1.1.0-rc2, cliente y transporte HTTP de A1, validación de respuestas contra el esquema, token por variable de entorno y reintentos acotados para consultas. | `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/RESULTADO-rc2-2026-10-13.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/PEDIDOS-AGENTE1-2026-10-13.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/RESPUESTA-PEDIDOS-HV-2026-10-13.md`; `Implementacion/Agente1/README.md`, secciones «Seam de consulta a Historia Viva» y «Post de efeméride»; issue #17. | Contrato **compartido y probado contra el mock Prism**: 57/57 escenarios y 39/39 casos. No está congelado: el tag `contrato-a1/v1.1.0` se propone para el 30/10. La API real de Ignacio no se verificó todavía; la sesión presencial está acordada para el 27/10. |
| **Identidad Workspace por cuenta de servicio de DSI** | `CuentaServicioDelegadaProvider` con domain-wide delegation, lista cerrada de cuentas suplantables y auditoría por token. DSI entregó la cuenta de servicio el 13/10. | ADR 0011 (`docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`); `Implementacion/Agente1/evidencias/cuenta-servicio-delegada-2026-10-14.md`; `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`, §1 y §4; `Implementacion/Agente1/src/agente1/workspace_auth.py`; issue #99. | Implementado y verificado offline; el paso en vivo contra Google y la baja de la OAuth anterior quedan para el operador designado y el issue #99. La delegación es de todo el dominio: DSI otorgó ese acceso y aceptó el riesgo. |
| **Servidor de la facultad con Ollama como host de la demo y candidato a host común** | `labredesfie`: Xeon E-2224G, 4 núcleos sin GPU, 31 GB de RAM, Ubuntu 22.04. Ollama 0.40.6 y 0.32.14 en espacio de usuario, en loopback. Modelos `llama3.2:3b` y `llama3.1:8b`. Código de A1 en `~/p100/Agente1` con venv de uv y Python 3.12. | `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; issue #118; issue #119; `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`, R-TEC-03. | Es el host de la demo porque la cátedra no admite localhost. **Hoy sólo corre A1**: no hay servicio del sistema, no hay sudo y los procesos no se levantan solos después de un reinicio. No es todavía una plataforma compartida por los cinco agentes. |
| **Auditoría y control de cambios** | Manifest de versión con el sha256 de todo lo controlado que vive en el repo; el modo operación no arranca si un archivo no coincide. El agente escribe registros de auditoría por ejecución, por token y por integridad de arranque. | ADR 0010 (`docs/adr/0010-el-agente-no-arranca-si-sus-archivos-controlados-no-coinciden-con-su-version.md`); `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md` (incluye las líneas de `logs/integridad-arranque.jsonl`); `Implementacion/Agente1/evidencias/cuenta-servicio-delegada-2026-10-14.md` (incluye la línea de `logs/cuenta-suplantada.jsonl`); `Implementacion/Agente1/manifest-version.json`; `Implementacion/Agente1/src/agente1/manifest_version.py`. | Verificado offline sobre 150 archivos controlados en el corte del 14/10; el manifest vigente al 19/10 cubre 184. Un prompt editado a mano impide arrancar y deja los dos hashes en la auditoría. La verificación en el host y el tag de versión quedan para el operador; el manifest se regenera en el corte, no en cada cambio. |

**La pestaña y el bus de la bible.** La pestaña no crea un bus paralelo: la bible define Google Sheets como bus de datos en §2.2 y el ADR 0008 baja esa definición a una pestaña con envelope, idempotencia y respuesta de estado. La diferencia es de grado: hoy la pestaña es el punto de entrada de A1; el bus conjunto con los cinco agentes queda proyectado.

**Lo que esta capa no incluye.** Apps Script, Celery, Redis, FastAPI, LangGraph, LangChain, LlamaIndex y Docker no se presentan como «hoy»: no están en uso por A1 y varios están explícitamente diferidos en `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` (§1 y §6). Tampoco se presentan A2, A3, A4 ni A5 como agentes existentes: en `Implementacion/` sólo hay `Agente1`.

---

## 6. Capa 2. Lo proyectado por la bible, con condición de entrada

La bible define componentes de orquestación y un stack tecnológico. Esta capa los conserva, pero separa **lo que la bible prevé** de **lo que el PPS usa hoy**. Cada pieza tiene una condición de entrada: no se incorpora por prestigio tecnológico ni por completar una tabla, sino cuando el problema operativo la justifica.

| Pieza | Rol en la bible | Condición de entrada | Estado |
|---|---|---|---|
| **Google Apps Script** | Orquestador principal basado en eventos; triggers y automatizaciones. | Cuando el bus D2 y los triggers institucionales deban correr sin una persona y A1 viva en un host de la FIE. Hoy el scheduler local cubre la reacción y el ADR 0008 descartó el trigger por fila nueva para 2026. | Proyectado. El anteproyecto lo ubica como previsto para el Semestre 2. |
| **Celery + Redis** | Middleware de colas asincrónicas y procesamiento concurrente; en la bible se lo describe como obligatorio para el P100. | Cuando haya concurrencia o volumen sostenido que un proceso único no absorba, o cuando una tarea larga deba sobrevivir al reinicio del host. La bible menciona difusión masiva, certificados y atención multicanal de A4. | Proyectado. El Plan de Recuperación del MVP lo difiere hasta que volumen, concurrencia o integración lo justifiquen. |
| **FastAPI** | Framework del backend Python. | Cuando exista un servicio con más de un consumidor o una API estable que deba exponerse. A1 corre por CLI y scheduler; su contrato de salida no necesita un servidor propio. | Proyectado. Diferido en el Plan de Recuperación. La API `/v1` es el contrato de Historia Viva, no un FastAPI de A1. |
| **LangChain / LlamaIndex** | Frameworks de agentes, cadenas y RAG; LlamaIndex se asocia a indexación semántica. | Cuando haga falta RAG con indexación, recuperación y reranking, o cadenas multi-paso que el código propio no sostenga. A1 hoy usa HTTP directo a Ollama, prompts y contratos propios; A2 es el candidato natural a LlamaIndex por el acervo histórico. | Proyectado. No están en las dependencias de A1. |
| **Docker / Docker Compose** | Contenedores para despliegues consistentes. | Cuando haya que reproducir un entorno multi-servicio (API, cola, base de datos) o desplegar en otro host sin instalar a mano. Hoy A1 corre en venv de uv. | Proyectado para el runtime de A1. Se usó en el mock de contrato (Prism) y en el spike efímero de PostgreSQL, no como runtime del agente. |
| **LangGraph** | **No está en la bible.** Entra por la propuesta de la cursada y el anteproyecto de este PPS como runtime de agentes, marcado como diferido. | Cuando el flujo tenga ciclos, estado durable, checkpointing, intervención humana intra-grafo o varios agentes coordinados. Los flujos de A1 son lineales y su estado se persiste en archivos JSONL. | Proyectado y no en uso. El anteproyecto lo declara diferido junto con FastAPI, Celery y Redis; el Plan de Recuperación lo difiere por la misma razón. |

**Lectura para la mesa.** La bible no es un plano de obra que se ejecuta completo el primer día. Es un horizonte de arquitectura. El PPS de A1 demostró que el camino de valor se puede recorrer con un stack menor y que los bloqueantes reales son institucionales, no la falta de un framework. La capa 2 queda como deuda técnica planificada, con condición de entrada y costo asociado, no como promesa de implementación.

**`deepagents`.** El anteproyecto también menciona `deepagents` como entorno auxiliar de prototipado sobre LangGraph. No está en la bible ni en uso; se lee igual que LangGraph: proyectado, y su condición de entrada es la misma (flujos con ciclos, estado durable o varios agentes coordinados).

---

## 7. Capa 3. La frontera del Agente 1: no orquesta

A1 es un nodo de comunicación institucional. Recibe insumos, redacta borradores y registra decisiones. **No invoca, no coordina y no orquesta a los otros agentes.** La orquestación del P100 es event-driven y batch, con Google Sheets como bus de datos según la bible; A1 es un consumidor y productor dentro de ese bus, no su dueño.

### 7.1 Qué consume

| Insumo | Cómo llega hoy | Estado | Fuente |
|---|---|---|---|
| Insumos de A3, A4 y A5 | Filas en la pestaña «Insumos de agentes» de D2, envelope `agente1.insumo.v1`. | Implementado offline; sólo A3 `evento` tiene pipeline. A4 y A5 se aceptan sin flujo. | ADR 0008; README; runbook de insumos. |
| Fragmentos y piezas de Historia Viva (A2) | Consulta HTTP pull a `/v1`; A1 siempre inicia. No hay callback, webhook ni cola entrante. | Por contrato: cliente y transporte probados contra mock; API real pendiente del 27/10. | ADR 0008; README, «Seam de consulta a Historia Viva»; issue #17. |
| Actividades, formularios y decisiones de la planilla D2 | Lectura de la planilla de actividades y del Form de pedidos; registro de decisiones por el segundo Form. | Implementado offline; la corrida live sobre D2 queda del operador. | README, canal de pedidos y registro de decisiones; ADR 0005; `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`. |

### 7.2 Qué produce

| Salida | Forma y estado | Efecto externo | Fuente |
|---|---|---|---|
| Borradores de gacetilla, post, certificado y notificación | Pieza marcada `BORRADOR — NO PUBLICAR` y `PENDIENTE_VALIDACION`. | Ninguno. No publica, no envía y no comparte. | README; `matriz-conformidad-hu010-2026-07-20.md`; `matriz-conformidad-hu011-2026-08-17.md`. |
| Decisiones humanas | Registro append-only de «lo publiqué» o «lo descarté» por el segundo Form, con identidad, rol y código. | Ninguno: registrar no dispara publicación ni envío. | `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`; `Implementacion/Agente1/evidencias/recorrido-registro-decisiones-form.md`. |
| Aportes a Historia Viva | `POST /v1/aportes` con clave de idempotencia; el aporte nace `PENDIENTE_VALIDACION`. | Por contrato: se registra al publicarse, nunca sobre un borrador sin validar. No entra en la demo del 18/11. | Issue #17, C16 (#101); README, «Seam de consulta a Historia Viva». |

### 7.3 Qué queda deliberadamente afuera, y por qué

- **Publicar o enviar comunicaciones oficiales.** Lo hace una persona. La validación humana es una exclusión de la bible y una condición del diseño de A1.
- **Orquestar a A2, A3, A4 o A5.** A1 no los invoca ni recibe pedidos de ellos. El patrón es pull para Historia Viva y envelope push para insumos; no hay orquestador-agente.
- **Hacer scraping, analítica, tableros o atención masiva.** Son funciones de A5 y A4 según la bible. A1 no las absorbe.
- **FastAPI, LangGraph, Celery, Redis y PostgreSQL operativo.** El Plan de Recuperación del MVP los difiere porque no son condición para el slice controlado y porque el gate está bloqueado por dependencias institucionales, no por falta de infraestructura.
- **Publicar en Instagram o LinkedIn por API.** HU-011 produce borradores, no publica. Las APIs de redes no se implementan en este PPS.
- **Definir el modelo, el alcance o el RACI.** Son decisiones de #51, la bible y la SEU, respectivamente.

---

## 8. Los siete flujos de la bible, con estado

La bible lista siete flujos en `Contenido/bible/Procesos y Agentes.md` §3 y `Contenido/Definicion/arquitectura-multiagente.md` §4. El estado se asigna con la definición de la sección 4 de este documento.

| Flujo | Qué cubre | Estado | Justificación |
|---|---|---|---|
| **F1. Actividad → Comunicación** | Formulario o planilla, trigger, A1, contenido, validación humana, publicación. | **Implementado en el tramo A1** | A1 genera borradores desde la planilla y el Form, y registra la decisión humana por el segundo Form. El trigger es el scheduler local, no Apps Script, y la publicación la hace una persona. La corrida live en el servidor es la que se busca el 21/10. |
| **F2. RRSS → Analítica** | Scheduler, A5, APIs de redes, normalización, Sheets, dashboards, alertas. | **Proyectado** | A5 no existe en este repositorio. A1 tiene prohibido hacer scraping y analítica. No hay contrato con A5 ni corrida. |
| **F3. Repositorio histórico** | Documento en Drive, trigger, A2, indexación, generación de contenido. | **Por contrato** | El lado A1 está implementado en dos piezas separadas: el cliente HTTP `/v1` validado contra el mock y el pipeline de efeméride probado con fake. La integración de punta a punta con el transporte HTTP no está acreditada; el lado A2 no está verificado en vivo y la instancia real se prueba el 27/10. |
| **F4. Vinculación** | A3 monitorea fuentes, genera oportunidades, registra en Sheets, notifica por mail. | **Por contrato** | El lado A1 del flujo está cubierto: lee un insumo `evento` de A3 en la pestaña y produce un borrador de gacetilla, probado offline. A3 no existe; el productor provisional está declarado. La corrida live en D2 está pendiente. |
| **F5. Atención** | Consulta por mail o web, A4, respuesta automática, registro. | **Proyectado** | A4 no existe y no hay contrato específico A4→A1. El envelope genérico admitiría un tipo, pero no hay pipeline ni responsable del lado A4. |
| **F6. KPIs integrados** | Datos de Sheets y RRSS, A5, procesamiento, Looker Studio, alertas. | **Proyectado** | A5 y los tableros no están implementados. A1 no hace KPIs ni analítica. |
| **F7. Gestión académica-administrativa** | A1 genera propuestas o piezas, validación humana, coordinación con Secretaría Académica, UNDEF o DGE. | **Implementado en el tramo A1; proyectado en la coordinación externa** | La generación y la validación humana existen en el circuito de A1, implementadas y probadas offline (gacetillas, certificados y notificaciones). La coordinación con las áreas externas es un acto administrativo que A1 no ejecuta y que no está instrumentado en el repositorio. |

**Lectura honesta del cuadro.** Dos flujos tienen un tramo real de A1, dos tienen contrato probado contra mock y tres son proyección. Ningún flujo está completo de punta a punta con los cinco agentes. Decir lo contrario sería confundir la bible con el estado de implementación.

---

## 9. «Segura, fiable e interoperable»: cómo se defiende

El mandato de Cicerchia usa tres atributos. No son adjetivos: cada uno tiene un mecanismo, una evidencia y una deuda.

| Atributo | Cómo se defiende hoy | Evidencia | Qué falta |
|---|---|---|---|
| **Segura** | Entrada no confiable con catálogo cerrado de intenciones; identidad del canal por Form y padrón; cuenta de servicio con lista cerrada de cuentas suplantables; secretos fuera del repo; en modo operación el agente no arranca si su versión no coincide; ninguna pieza sale sin validación humana. | ADR 0001; ADR 0005; ADR 0011; `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`; `Implementacion/Agente1/evidencias/cuenta-servicio-delegada-2026-10-14.md`; `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md`; `Implementacion/Agente1/evidencias/recorrido-registro-decisiones-form.md`. | La corrida live contra Google (#99), la baja efectiva de la OAuth anterior, la 2SV de la cuenta técnica (prevista, no implementada), la prueba conjunta de revocación con DSI (no la hacen) y una auditoría de seguridad en el host. El riesgo de la delegación de dominio está aceptado por DSI y declarado. |
| **Fiable** | Idempotencia por `correlation_id`; manifest fail-closed; timeout derivado del peor caso del servidor; reintentos acotados y `Retry-After`; lock del scheduler contra solapamientos; recuperación durable de HU-012; estados explícitos de error. | ADR 0010; `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md`; `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Implementacion/Agente1/evidencias/recuperacion-hu012-idempotencia-durable-2026-09-08.md`; README, scheduler. | El E2E en el servidor, el Gate G2 / TRL 3 y la validación SEU. La fiabilidad mecánica no equivale a calidad editorial: en la medición del 19/10, HU-011 v3 dio 0/6 con el 3b y 2/6 con el 8b. Esa brecha es de contenido y de criterios SEU, no se tapa con infraestructura. |
| **Interoperable** | Contrato `/v1` con OpenAPI y validación de esquema; códigos 400, 401, 403, 404, 422, 429 y 503; envelope de insumos con `correlation_id` y `data_origin`; bus en Sheets; A1 siempre inicia la consulta y no acepta callbacks. | `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/RESULTADO-rc2-2026-10-13.md`; ADR 0008; README, «Seam de consulta a Historia Viva»; issue #17; `Contenido/Definicion/arquitectura-multiagente.md` §6. | El tag congelado `contrato-a1/v1.1.0` del 30/10, la prueba contra la API real del 27/10, contratos con los dueños de A3, A4 y A5, y una identidad común por agente. Hoy la interoperabilidad está probada contra mock, no contra los otros agentes. |

**Sobre «apta para los 5 agentes».** La propuesta es apta como marco de convivencia: define un bus, un contrato pull, una frontera y un criterio de incorporación. No es todavía el sistema operativo de cinco agentes, porque sólo A1 existe. La aptitud se demuestra por contratos y fronteras, no por despliegue. Esa distinción conviene decirla antes de que la pregunte la mesa.

---

## 10. Objeciones y respuestas

Las objeciones se construyeron estresando el documento con `Agentes/evaluador_cicerchia.md` (ejes BPM, alcance, evidencia, TRL, costo, DoD, dependencias y coherencia) y `Agentes/arquitectura_multiagente_experto.md`.

### 10.1 «LangGraph no está en la bible. ¿Por qué aparece en la arquitectura?»

Porque no se presenta como bible. LangGraph entra por la propuesta de la cursada y el anteproyecto de este PPS, que lo declara diferido junto con FastAPI, Celery y Redis (`Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`, nota de la sección 13). En este documento está en la capa 2, con condición de entrada y estado proyectado. Si la mesa pregunta qué dice la bible, la respuesta es: la bible no lo incluye; el PPS lo propone como runtime futuro y hoy no está en uso.

### 10.2 «La bible pone Celery + Redis como obligatorio y vos no los usás. ¿La arquitectura está incompleta?»

La bible los prevé para el P100 y los describe como middleware obligatorio para la concurrencia de los cinco agentes. El Plan de Recuperación del MVP los difiere para el slice de A1 porque no son condición para producir borradores con validación humana y porque el gate está bloqueado por dependencias institucionales. No se presentan como en uso. Si la Dirección los exige para el 21/10, eso es una decisión de alcance y de cronograma que se toma fuera de esta propuesta; la arquitectura no la contradice, sólo distingue el horizonte de la implementación.

### 10.3 «¿Cómo podés llamar multiagente a un sistema donde sólo existe A1?»

No lo llamo sistema multiagente operativo. Lo llamo arquitectura multiagente en construcción, con un nodo implementado y cuatro contratos o proyecciones. La evidencia es explícita: en `Implementacion/` sólo hay `Agente1`. Lo que sí está definido es la frontera: A1 no orquesta, consume insumos y consulta a A2. Esa frontera es la que permite sumar agentes sin reescribir A1. Presentar los cinco agentes como existentes sería incorrecto y la demo lo desmentiría.

### 10.4 «¿Contra qué proceso mapea A1 y quién valida?»

A1 es soporte principal del Proceso 4, Comunicación y Difusión Institucional, y asiste a P3, P5 y P6 en la difusión. En el RACI del Proceso 4, el Responsable de Gestión del Conocimiento de Extensión (RGC) tiene la R de validación semántica, comunicacional e institucional, y el Coordinador de Extensión (COORD) tiene la A. Esta propuesta no cambia ese RACI. La validación humana del circuito de A1 se apoya en esos roles y en el padrón externo; el agente no se autoasigna la aprobación.

### 10.5 «La cuenta de servicio tiene delegación de todo el dominio. ¿Cómo sostenés que es segura?»

No sostengo que sea segura en absoluto. Sostengo que el riesgo es explícito, aceptado por DSI y compensado: la delegación se autoriza por client ID para todo el dominio, quien tenga la clave puede leer y enviar correo y acceder al Drive como cualquier cuenta de la FIE. DSI otorgó ese acceso y aceptó el riesgo (ADR 0011, correo del 13/10). La compensación es la lista cerrada de cuentas suplantables, el hash de cada dirección en el manifest, la auditoría por token y el fail-closed si la cuenta no está en la lista. El residual sigue siendo alto y está declarado; no se presenta como mínimo privilegio.

### 10.6 «¿Cómo evitás que el modelo invente o que un texto malicioso lo instruya?»

Con dos controles distintos. Para la entrada no confiable, ADR 0001: una solicitud en prosa nunca llega como instrucción al modelo; se interpreta contra un catálogo cerrado y lo que no matchea se rechaza, no se aproxima. Para la salida, el gate de hechos y la validación humana: la pieza nace `BORRADOR — NO PUBLICAR` y ninguna persona puede publicar desde el agente. Eso no garantiza calidad editorial. La medición del 19/10, con datos sintéticos y Ollama 0.40.6, muestra que HU-011 v3 sigue por debajo de lo necesario (0/6 con 3b y 2/6 con 8b). La arquitectura protege contra acciones no autorizadas y contra invención no contrastada; la calidad del texto sigue siendo una brecha abierta de criterios SEU.

### 10.7 «Si la pestaña de insumos ya es un bus, ¿no estás duplicando la integración con A3-A5?»

La pestaña no es el bus conjunto: es el punto de entrada propio de A1 mientras el bus no existe. El ADR 0008 lo dice en sus consecuencias: cuando el bus conjunto exista, el agente productor escribe ahí. El envelope, la idempotencia por `correlation_id` y la respuesta de estado son el contrato que después se reutiliza. Hoy evita un webhook o un Apps Script por fila, que el mismo ADR descartó para 2026. La deuda es que A4 y A5 sólo tienen el tipo aceptado, sin pipeline.

### 10.8 «Si el servidor o la red fallan el 21/10, ¿qué muestra?»

No habría demo en vivo, y no hay respaldo offline: la cátedra exige que la demo no corra en localhost. El riesgo R-TEC-03 está registrado y aceptado con esa condición: host único, sin GPU, sin sudo, procesos en espacio de usuario que no se levantan solos. La respuesta es un smoke live antes de cada exposición y, si falla, levantar Ollama y el agente a mano con el procedimiento documentado; si no se recupera, escalar al tutor para reprogramar. No se promete una demo que el host no pueda sostener.

---

## 11. Fuentes y verificación

### 11.1 Fuentes principales

- `Contenido/Definicion/arquitectura-multiagente.md`, §3 (modelo de orquestación), §4 (flujos), §6 (interfaces), §7 (stack) y §12 (exclusiones).
- `Contenido/bible/Procesos y Agentes.md`, §2.2 (componentes de orquestación), §3 (flujos) y §7 (stack); RACI del Proceso 4 en las líneas 1803-1804 del Markdown operativo.
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`, correo del 20/03/2026.
- `Agentes/arquitectura_multiagente_experto.md` y `Agentes/evaluador_cicerchia.md`.
- `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`.
- `docs/adr/0005-identidad-verificada-por-formulario-rol-por-padron.md`.
- `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`.
- `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`.
- `docs/adr/0010-el-agente-no-arranca-si-sus-archivos-controlados-no-coinciden-con-su-version.md`.
- `docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`.
- `Implementacion/Agente1/README.md` y `Implementacion/Agente1/evidencias/`.
- `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`, §1 y §6.
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`, tabla y nota de la sección 13.
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`, R-TEC-03.
- Issues #17, #51, #99, #101, #118, #119, #128 y #130 del repositorio `SpendIce/Proyecto-Final`.

### 11.2 Cómo se verificó

- Cada fila de la capa 1 se contrastó con el archivo, ADR o issue citado; no se aceptó una afirmación de «hoy» sin esa fuente.
- La cita del correo se buscó de forma literal en el Markdown operativo. El original dice «vas iniciar», no «vas a iniciar»; se conserva la forma literal.
- Los estados de los flujos se asignaron con la definición de la sección 4 y se contrastaron contra la existencia real de código, contrato o sólo documentación.
- No se ejecutó ninguna corrida live nueva para este documento. Las afirmaciones sobre el servidor, la cuenta de servicio y el contrato son las que constan en la evidencia del 13, 14 y 19/10, con sus límites declarados.

### 11.3 Deudas que quedan a la vista

- Demo E2E en `labredesfie` y smoke previo del 21/10.
- Prueba contra la API real de Historia Viva y tag `contrato-a1/v1.1.0` del 30/10.
- Paso en vivo de la cuenta de servicio y baja de la OAuth anterior (#99).
- Contratos con los dueños de A3, A4 y A5.
- Validación SEU y Gate G2 / TRL 3.
- Decisión de modelo y configuración (#51).
- Calidad editorial de HU-011: la brecha sigue abierta.
