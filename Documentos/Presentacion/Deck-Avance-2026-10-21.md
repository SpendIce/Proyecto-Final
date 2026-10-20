# Guion de orador · Presentación de avance del 21/10/2026

**Deck:** `Documentos/Presentacion/Deck-Avance-2026-10-21.html`
**PDF:** `Documentos/Presentacion/Deck-Avance-2026-10-21.pdf`
**Fecha y hora:** miércoles 21/10/2026, 09:00, Facultad de Ingeniería del Ejército.
**Expositor:** Juan Ignacio Goñe.

Este archivo es para Juani. El deck no lleva notas de orador ni barras de navegación en el PDF: todo lo que hay que decir está acá.

## Cómo se usa

- Abrir el HTML con doble clic. Navegar con `←` `→`, espacio, `Inicio` y `Fin`.
- `F` entra y sale de pantalla completa. `P` abre el diálogo de impresión.
- Si se abre con `?limpio` al final de la ruta, se ocultan la barra y la ayuda. Sirve para proyectar sin controles.
- El PDF es el respaldo: 11 páginas, una por lámina, sin encabezados ni pies.
- Duración sugerida: 8 a 12 minutos de láminas y después la demo, con el corte de 45 minutos que ya está en la checklist del servidor.

## Antes de empezar (martes y miércoles)

1. Abrir el HTML una vez en la máquina que se va a usar y pasar todas las láminas con las flechas.
2. Probar `F` y `P`. Si la máquina del aula no tiene Chromium, llevar el PDF y abrirlo en pantalla completa.
3. No abrir el HTML desde una carpeta sincronizada ni desde un pendrive lento: las fuentes y los logos están embebidos, pero el archivo pesa 230 KB.
4. Para la demo, seguir `Checklist-Miercoles-2026-10-21.md`. El deck no reemplaza el smoke previo del servidor.

---

## Lámina 1 · Portada

**Texto visible**

- Presentación de avance · 21/10/2026 · 09:00.
- Agente 1 · Extension Bot.
- Comunicación institucional para la Secretaría de Extensión Universitaria. El agente redacta borradores; la decisión queda en la institución.
- Juan Ignacio Goñe · Proyecto de Promoción y Síntesis · FIE.
- Logos FIE y UNDEF.

**Notas de orador**

- Buenos días. Soy Juan Ignacio Goñe y esta es una presentación de avance del PPS, no la presentación final de la carrera.
- El Agente 1 es el nodo de comunicación institucional del Proyecto Centenario: redacta borradores para la SEU y nunca publica por su cuenta.
- Hoy voy a mostrar tres cosas: cómo está el plan, cómo se lee la arquitectura compartida y una corrida en el servidor de la facultad.
- La idea que quiero dejar desde el principio es la del cierre: el agente propone, la institución decide.

**Preguntas probables**

- **¿Esto reemplaza al personal de la SEU?** No. El agente redacta un borrador y una persona con rol lo valida, lo corrige o lo descarta. La exclusión está en la bible y en el diseño. Ver banco §9.
- **¿Es un chatbot?** No. Es un pipeline determinista con un paso de modelo, dentro de un proceso administrativo. Ver banco §6.

## Lámina 2 · Qué se muestra hoy

**Texto visible**

- Tres piezas: el estado del plan, la arquitectura compartida y una corrida en vivo en el servidor de la facultad.
- 01 · El Gantt semanal. El plan intacto y el avance marcado con evidencia: 47 tareas e hitos, 23 con `done` y 24 sin marcar. Corte 19/10/2026, sin rebaseline.
- 02 · La arquitectura P100 en tres capas. Lo compartido hoy, lo proyectado con condición de entrada y la frontera del Agente 1.
- 03 · La demo en vivo. En `labredesfie`, operado desde la facultad: gacetilla, certificados y confirmaciones.
- Alcance: es una presentación de avance, no cierra el PPS, el Gate G2 ni el TRL.

**Notas de orador**

- Ordeno la presentación en tres bloques para que se entienda qué es evidencia y qué es horizonte.
- El Gantt no se rebaselineó: lo que cambió es la lectura del avance, no las fechas ni los IDs del plan.
- La arquitectura es una propuesta para llegar a una vista común con Ignacio, no un diseño cerrado de los cinco agentes.
- La demo corre en el servidor de la facultad porque la cátedra no admite localhost.
- Aclaro desde acá: esto no cierra el PPS, ni el Gate G2, ni el TRL.

**Preguntas probables**

- **¿Por qué tan pocas láminas?** Porque es una presentación de avance y el detalle está en los informes. Preferí pocas ideas sostenidas con evidencia. Ver banco §13.
- **¿Esto cierra el PPS?** No. El PPS cierra en febrero de 2027; hoy se muestra el estado al 21/10. Ver banco §13.

## Lámina 3 · El plan no se toca; el avance se marca con evidencia

**Texto visible**

- 47 tareas e hitos en el plan. 23 con `done`. 24 sin marcar.
- El `.mmd` conserva IDs y fechas. Cambia la lectura del avance, no el plan.
- Barras por sprint: S0 4/4, S1 3/6, S2 3/5, S3 2/5, S4 4/6, S5 2/5, S6 5/6, S7 0/5, Cierre 0/5.
- Lo que avanzó desde septiembre: contrato Historia Viva rc2 (57/57 contra mock), cuenta de servicio (ADR 0011), certificados con línea descriptiva, medición 3b/8b en el servidor (19/10), anexos 1–3.

**Notas de orador**

- El corte es del lunes 19 a la noche y no agregué ninguna tarea nueva a `done` para esta presentación.
- Los sprints con más avance son S0, S4 y S6: bootstrap, confirmaciones y certificados.
- S7 y Cierre están en cero porque dependen de la integración en el servidor y de la validación institucional, no de código que falte escribir.
- La franja de abajo es lo que sí avanzó desde septiembre: contrato, identidad, certificados, medición y anexos.
- Si alguien pregunta por el CI: la suite local está verde, el run del 19/10 tiene un test en rojo y por eso no marqué el hito.

**Preguntas probables**

- **¿Por qué no está todo el Gantt en verde?** Porque hay tareas bloqueadas por terceros y no las marco sin evidencia. El detalle está en `Revision-Avance-2026-10-19.md`. Ver banco §13.
- **¿Movieron fechas del plan?** No. El `.mmd` no se tocó; se contrastó contra `gantt-progreso.js`.
- **¿Qué es lo más importante que avanzó?** El contrato con Historia Viva probado contra el mock y la cuenta de servicio de DSI. La API real se prueba el 27/10.

## Lámina 4 · Lo que no está marcado, y por qué

**Texto visible**

- s1e · s2d · s3b · s4e · s5d · c1: validación SEU de muestras. El paquete está listo desde septiembre; la visita del 19/10 dio definiciones, no revisión de muestras.
- s1c · m1: plantilla institucional de gacetilla. La salida a Docs corrió live el 28/09; falta la plantilla aprobada.
- s3a: D3 y aval formal de DSI. D2 está live; D3 y el aval siguen abiertos.
- HU-011 · posts: el 3b no resuelve redacción libre; el 8b resuelve Instagram pero no LinkedIn. La decisión de alcance está abierta.
- s7c · m7: E2E en el servidor de la demo. Se corre el 21/10; no se declara antes.
- No marcamos lo que no podemos sostener. El detalle está en el informe del Gantt.

**Notas de orador**

- No voy a recorrer las 24 tareas sin marcar. Hay cinco frentes que explican casi todo.
- El primero es la validación de la SEU: el paquete de muestras está listo desde septiembre y la visita del 19/10 aportó definiciones, no revisión.
- El segundo es la plantilla de gacetilla; la salida a Docs ya se probó en vivo, lo que falta es la plantilla aprobada.
- El tercero es D3 y el aval de DSI. D2 está live desde el 28/09.
- Posts y E2E tienen estado propio: la decisión de modelo y alcance está en #51, y el E2E se corre hoy, no antes.
- La frase que resume la lámina: no marco lo que no puedo sostener con un archivo, un issue o una corrida.

**Preguntas probables**

- **¿Qué pasa con los posts?** El 3b no resuelve redacción libre y el 8b resuelve Instagram pero no LinkedIn. La decisión de modelo y alcance está abierta en #51 y cualquier cambio pasa por Dirección. Ver banco §11.
- **¿La SEU está bloqueando el proyecto?** No. La SEU todavía no revisó las muestras; el resto del circuito técnico sigue avanzando. Ver banco §9 y §13.
- **¿Por qué el E2E no está marcado si la demo es hoy?** Porque se corre hoy. No lo declaro antes de que exista la evidencia.

## Lámina 5 · Arquitectura P100 en tres capas

**Texto visible**

- Etiqueta 1: lo compartido hoy, con evidencia. Piezas que los dos equipos pueden mirar hoy, con su límite declarado.
- Etiqueta 2: lo proyectado por la bible, con condición de entrada. Se enciende sólo si el problema operativo lo justifica.
- Etiqueta 3: la frontera de A1. Consume, redacta y registra. No invoca ni coordina a los otros agentes.
- Capa 1: D2 · Insumos (ADR 0008), Historia Viva `/v1` rc2 (mock 57/57), cuenta de servicio (ADR 0011), `labredesfie` con Ollama (19/10), manifest y auditoría (ADR 0010).
- Capa 2: Apps Script, Celery + Redis, FastAPI, LangChain/LlamaIndex, Docker, LangGraph (no está en la bible).
- Condición de entrada: volumen, concurrencia, integración.
- Capa 3: consume → A1 redacta `PENDIENTE_VALIDACION` → produce → validación humana.
- Remate: **A1 es nodo, no orquestador**.
- Nota al pie: esquema del diagrama de tres capas, redibujado para proyección.

**Notas de orador**

- Esta es la vista que quiero acordar con Ignacio. No es un diseño de detalle de los cinco agentes.
- La capa 1 es lo que existe hoy con evidencia: bus de entrada, contrato pull, identidad, host y auditoría.
- La capa 2 es la bible como horizonte, no como plano de obra. Cada pieza tiene una condición de entrada y un costo.
- La capa 3 es la frontera: A1 consume insumos, redacta borradores y registra decisiones; no orquesta a nadie.
- Si hay una sola frase para retener: A1 es nodo, no orquestador.
- El diagrama completo está en `Documentos/Arquitectura/Arquitectura-P100-Tres-Capas-2026-10-21.svg`; acá se redibujó para que se lea desde el fondo del aula.

**Preguntas probables**

- **¿Esto es un agente o un pipeline?** Hoy la parte implementada es un pipeline determinista con un paso de modelo. Lo llamo agente en el sentido arquitectónico del P100: componente especializado con proceso y contratos. Ver banco §6.
- **¿Por qué no GPT-4 o Claude?** Por costo, soberanía de datos y una base sin APIs externas de pago. No medimos esos modelos, así que no afirmo que sean mejores o peores. Ver banco §4.
- **¿LangGraph no está en la bible?** No está. Entra por la cursada y el anteproyecto, está en la capa 2 y no está en uso. Ver banco §7.

## Lámina 6 · Capa 1: lo compartido hoy, con su evidencia

**Texto visible**

- Pestaña de insumos en D2 (ADR 0008): A3–A5 entregan filas con envelope `agente1.insumo.v1`; A1 las sondea, responde estado y procesa cada `correlation_id` una sola vez. Probado offline; la corrida live está preparada y no ejecutada.
- Historia Viva `/v1` (rc2): 57/57 escenarios y 39/39 casos contra el mock Prism. La API real se prueba el 27/10; el tag del 30/10 todavía no está congelado.
- Identidad Workspace (ADR 0011): cuenta de servicio con delegación de dominio, lista cerrada y auditoría por token. El paso live y la baja de la OAuth anterior están en #99.
- `labredesfie` con Ollama (medición 19/10): Xeon E-2224G, 4 núcleos sin GPU, 31 GB de RAM. Modelos 3b y 8b medidos. Es el host de la demo.
- Manifest y auditoría (ADR 0010): 184 archivos controlados al 19/10; si un hash no coincide, el agente no arranca.
- «Compartido» no significa «productivo en vivo»: cada pieza tiene un límite declarado y verificable.

**Notas de orador**

- «Compartido» quiere decir que hay un artefacto, una decisión o una interfaz que los dos equipos pueden mirar hoy.
- La pestaña de insumos es el punto de entrada propio de A1, no el bus conjunto de los cinco agentes.
- El contrato con Historia Viva está probado contra mock, no contra la API real. Esa diferencia importa y la digo.
- La cuenta de servicio existe y está auditada, pero el paso en vivo contra Google todavía no se hizo.
- El servidor es el host de la demo porque la cátedra no acepta localhost. Hoy sólo corre A1 y no es una plataforma compartida.

**Preguntas probables**

- **¿Qué significa «compartido» si no está en vivo?** Que existe el artefacto o la interfaz con un límite declarado. No es lo mismo que producción. Ver banco §12.
- **¿El contrato con Historia Viva funciona?** Contra el mock, 57/57. Contra la API real se prueba el 27/10; no lo declaro antes. Ver banco §8.
- **¿La cuenta de servicio es segura?** Tiene delegación de todo el dominio, aceptada por DSI, con lista cerrada y auditoría. El riesgo residual está declarado. Ver `Arquitectura-Multiagente-P100-Tres-Capas-2026-10-21.md`, §10.5.

## Lámina 7 · Capa 2: lo proyectado, con condición de entrada

**Texto visible**

- Apps Script: triggers institucionales sin una persona detrás. Hoy: scheduler local y ADR 0008.
- Celery + Redis: concurrencia o volumen sostenido, o tareas que sobrevivan al reinicio. Hoy: cola durable en archivo, sin broker.
- FastAPI: un servicio con más de un consumidor o una API estable. Hoy: CLI y scheduler; `/v1` es el contrato de Historia Viva.
- LangChain / LlamaIndex: RAG con indexación y reranking, o cadenas multi-paso. Hoy: HTTP directo a Ollama.
- Docker: entorno multi-servicio o despliegue en otro host. Hoy: venv de uv.
- LangGraph: estado durable, ciclos, checkpointing o varios agentes. Hoy: flujos lineales y estado en JSONL. Proyectado, no está en la bible.
- Nota al pie: LangGraph no está en la bible; entra por la cursada y el anteproyecto, y no está en uso. `deepagents` se lee igual.

**Notas de orador**

- La bible no es un plano de obra que se ejecuta completo el primer día. Es un horizonte de arquitectura.
- Cada pieza de esta capa tiene una condición de entrada concreta: volumen, concurrencia o integración.
- Hoy A1 demuestra que el camino de valor se recorre con un stack menor: HTTP directo a Ollama, archivos JSONL y un scheduler local.
- La deuda existe y está declarada. No la presento como una promesa de implementación.
- LangGraph es el caso más delicado: no está en la bible y lo digo expresamente. Entra por la cursada y el anteproyecto, y no está en uso.

**Preguntas probables**

- **¿Por qué no usan LangGraph o LangChain?** No se descartaron: se difirieron. El MVP no necesita un grafo con estado para una llamada al modelo por pieza. Ver banco §7.
- **¿No es deuda técnica?** Sí, es deuda declarada con condición de entrada y costo asociado. Ver banco §7.
- **¿Si la cátedra exige LangGraph?** Sería un cambio de alcance y de arquitectura, no una decisión para hoy. Se evalúa con Dirección. Ver banco §7.

## Lámina 8 · Capa 3: la frontera del Agente 1

**Texto visible**

- Consume insumos, redacta borradores y registra decisiones. No invoca, no coordina y no orquesta a los otros agentes.
- 01 · Consume: filas de A3–A5 en D2, consulta pull a Historia Viva y lectura de la planilla y los Form de la SEU.
- 02 · Redacta: toda pieza nace `BORRADOR` y `PENDIENTE_VALIDACION`. El gate de hechos rechaza la salida completa si algo no está en la fuente.
- 03 · Produce: borradores de gacetilla, post, certificado y notificación; decisiones humanas por Form; aportes a Historia Viva.
- 04 · Validación humana: una persona con rol lee, corrige y publica o descarta. El agente no publica ni envía nada por sí solo.
- No hace: no publica ni envía; no orquesta a A2, A3, A4 ni A5; no hace scraping, analítica ni atención masiva.

**Notas de orador**

- Esta es la lámina que responde la pregunta más importante: dónde termina el agente.
- Consume tres cosas: insumos de A3–A5, consultas a Historia Viva y la planilla con los Form de la SEU.
- Todo lo que produce nace como borrador y pendiente de validación. El gate de hechos es determinista y rechaza la pieza completa si algo no está en la fuente.
- La validación humana no es un adorno: es la condición que hace que el sistema sea usable en una institución.
- Las tres exclusiones de abajo son las que evitan convertirlo en otra cosa: no publica, no orquesta, no hace analítica ni atención masiva.

**Preguntas probables**

- **¿Cómo evitan que invente?** Con tres capas: hechos desde una fuente estructurada, redacción acotada y gate determinista, más validación humana. No supone que el modelo no falle: supone que no puede publicar. Ver banco §1.
- **¿Quién es responsable de lo que se publica?** Una persona con rol del Proceso 4. El RACI no cambia: RGC valida y COORD aprueba. Ver banco §9.
- **¿El agente puede publicar solo?** No. No hay ruta de publicación ni de envío sin una persona.

## Lámina 9 · La demo en vivo

**Texto visible**

- Host: `labredesfie`. Servidor de la facultad, operado desde la facultad. No es localhost.
- Ollama 0.40.6 en loopback, sin GPU, sin sudo, un solo host y sin respaldo offline.
- 1 · Gacetilla: Sheets → modelo local → Google Doc marcado `BORRADOR`.
- 2 · HU-014 · certificados: dos aprobaciones de línea y del lote → PDF de prueba `SIN VALIDEZ`.
- 3 · HU-012 · confirmaciones: correo simulado con marca `BORRADOR — NO ENVIAR`.
- Corte a los 45 minutos: si sólo entra la gacetilla, es un resultado válido. Si algo falla, se muestra la evidencia de la mañana y no se depura en clase.

**Notas de orador**

- La demo corre en el servidor de la facultad. No es localhost y no hay respaldo offline: el riesgo R-TEC-03 está aceptado con esa condición.
- El orden es gacetilla, certificados y confirmaciones. La gacetilla es el flujo completo de comunicación.
- En la gacetilla miren tres cosas: lee la planilla, genera con el modelo local y deja el documento marcado como borrador.
- En HU-014 miren el gate: sin las dos aprobaciones de línea y la del lote no hay PDF. El certificado es de prueba y dice `SIN VALIDEZ`.
- En HU-012 miren el correo simulado: sale marcado `BORRADOR — NO ENVIAR` y no se envía nada real.
- Si el reloj aprieta, cortamos a los 45 minutos. Que sólo entre la gacetilla es un resultado válido, no una falla.

**Preguntas probables**

- **¿Qué pasa si se cae el servidor durante la demo?** No hay respaldo offline. Se levantan Ollama y el agente a mano; si no se recupera, se escala al tutor para reprogramar. Ver banco §12.
- **¿Por qué no corren la demo en la laptop?** Porque la cátedra exige que no sea localhost. Es una restricción de la consigna, no una elección técnica. Ver banco §12.
- **¿Qué pasa si el modelo alucina en vivo?** Si el gate lo detecta, no hay borrador. Si pasa el gate, queda un borrador que una persona tiene que aprobar; no se publica. Ver banco §1.

## Lámina 10 · Límites declarados y próximos hitos

**Texto visible**

- Límites: validación SEU pendiente (muestras y plantilla); un solo host, sin respaldo offline (R-TEC-03); contrato `/v1` en rc2, API real el 27/10; posts con decisión de alcance abierta; el sistema no está en producción.
- Hitos: 23/10 anexos al laboratorio; 27/10 prueba con la API real de Historia Viva; 2–6/11 revisión de laboratorio; 18/11 presentación de cursada.
- Los hitos no dependen sólo del código. La API real es de Historia Viva, la revisión es del laboratorio y la validación es de la SEU.

**Notas de orador**

- Los límites no son un descargo: son las condiciones con las que el sistema se puede usar hoy.
- La validación de la SEU es el límite más importante: sin muestras revisadas no se puede declarar el DoD de las historias.
- El contrato está en rc2 y la API real se prueba el 27/10. Hasta entonces, la interoperabilidad está probada contra mock.
- Los posts dependen de la decisión de #51: el 3b no resuelve redacción libre y el 8b no resuelve LinkedIn.
- Los cuatro hitos ordenan el resto del año. Tres de ellos dependen de una contraparte, no sólo del equipo.

**Preguntas probables**

- **¿En qué TRL están?** No declaro TRL 3 ni TRL 4. El Gate G2 y la validación SEU están pendientes. Ver banco §13.
- **¿Qué falta para producción?** E2E en el servidor, decisión de modelo y alcance, tipos del PPS, contrato real de Historia Viva, validación SEU y traspaso operativo. Ver banco §12.
- **¿Qué pasa con los posts en la presentación de cursada?** Depende de #51. Hoy no son parte del guion principal. Ver banco §11.

## Lámina 11 · Cierre

**Texto visible**

- El agente propone. La institución decide.
- Lo que sigue no depende sólo del código: depende de tres acuerdos concretos.
- 01 · Revisar la arquitectura con Ignacio. Una propuesta para acordar la vista, no un diseño cerrado.
- 02 · Revisar las muestras de la SEU. El paquete está listo desde septiembre y sigue sin revisión.
- 03 · Llegar al 18/11 con el sistema funcionando. Demo, evidencia y traspaso, no una promesa de producción.
- Logos FIE y UNDEF.

**Notas de orador**

- Cierro con la frase que ordena todo el proyecto: el agente propone, la institución decide.
- Los tres pedidos son concretos. El primero es con Ignacio: acordar la vista de las tres capas.
- El segundo es con la SEU: revisar las muestras que están listas desde septiembre.
- El tercero es del equipo: llegar al 18/11 con el sistema funcionando y la evidencia ordenada.
- Gracias. Quedo a disposición para las preguntas.

**Preguntas probables**

- **¿Qué necesitan de la cátedra?** El criterio formal del Gate G2 y una devolución sobre la arquitectura, no una habilitación para publicar. Ver banco §13.
- **¿Qué pasa después del 18/11?** Queda el cierre del PPS en febrero de 2027 y el traspaso operativo a la Dirección, la SEU, los alumnos que continúan y DSI. Ver banco §12.

---

## Exportación del PDF

Comando exacto usado, desde la raíz del worktree:

```bash
chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="Documentos/Presentacion/Deck-Avance-2026-10-21.pdf" \
  "file://$PWD/Documentos/Presentacion/Deck-Avance-2026-10-21.html?limpio"
```

El `?limpio` oculta la barra de navegación y la ayuda. El CSS de impresión también las oculta y fuerza una lámina por página con `@page{size:1600px 900px;margin:0}`.

## Verificación hecha

- `pdfinfo` da **11 páginas** y página de **1200 × 675,12 pts**, equivalente a 1600 × 900 px a 96 dpi.
- `pdftoppm -r 96 -png` generó las 11 páginas como imagen. Se revisaron visualmente las páginas 1, 3, 5 y 9.
- `rg -n 'https?://|src="//|@import'` sobre el HTML no devuelve coincidencias: no hay pedidos a la red.
- Las fuentes Encode Sans y Roboto y los logos FIE y UNDEF están embebidos como data URI.
- El PDF no incluye notas de orador ni barras de navegación: las notas viven sólo en este archivo.

## Identidad visual aplicada

- Azul `#081E4B`, neutros `#EAE9E5`, `#A59F97` y `#3E3A42`, según el Manual de Identidad Visual FIE 2026 (pág. 20).
- Encode Sans para títulos y rótulos; Roboto para textos corridos, según la pág. 23 del manual.
- Logo FIE isologo en versión color sobre fondos claros y versión blanco sobre azul. Logo UNDEF horizontal (`Artboard 5`) en versión color sobre claro y versión blanca (`Artboard 5 copy 3`) sobre oscuro. Se respetó el área de resguardo con márgenes amplios.
- No se usaron colores de carrera.
