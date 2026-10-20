# Banco de preguntas difíciles de IA: presentación de avance del 21/10/2026

**Para:** Juan Ignacio Goñe, Agente 1 (Extension Bot), Proceso 4.
**Uso:** mesa de examen con Cicerchia y Q&A con invitados externos que preguntan sobre IA.
**Evidencia principal:** medición del 19/10/2026 en `labredesfie`, código `cff6a16`, y validación final del 20/10 en `main` (`87e7ab5`). Datos reales del corpus FIE INFORMA. No acredita validación SEU, Gate G2 ni TRL 3.

## Actualización 20/10: modelo elegido

El modelo único del sistema de demostración es **`gemma4:e4b`** (Ollama 0.40.6, `think=false`, temperatura 0, `num_predict` 512, timeout 180 s). Validación final en `labredesfie`: **44/48 (91,7 %)** en gacetilla+posts, **48/48 revalidado** tras DEF-A1-026; HU-014 **18/18**; HU-012 **18/18**; canal **16/16**. Las respuestas que comparan 3b/8b son la **línea base del 19/10** y quedan como historia; no son la configuración vigente.

El E2E en el servidor **no se corrió**: falta acceso a Sheets y Docs. Por eso `s7c` sigue abierto y la demo tiene Plan B: OAuth anterior como contingencia y, si tampoco, HU-014/HU-012 offline. La identidad objetivo sigue siendo la cuenta de servicio (#99).

## Cómo usar este banco

- Responder en tres movimientos: qué hace el sistema, qué límite tiene, dónde está la evidencia.
- Si no hay dato, decirlo. Varias respuestas de este banco declaran un hueco a propósito: es más defendible que improvisar.
- No usar «garantiza», «100 %», «revolucionario» ni «no alucina». La promesa correcta es otra: **el agente no puede publicar solo**.
- Las respuestas están escritas para decirse en voz alta, no para leerse. La evidencia queda para cuando pidan el respaldo.

### Si tenés diez minutos

Estas diez son las más probables entre Cicerchia y un invitado externo. El resto del banco queda para consultar por sección.

1. ¿Cómo evitan que el modelo invente datos? (§1)
2. ¿Qué pasa si el modelo alucina en vivo, delante de todos? (§1)
3. ¿Esto es un agente o un pipeline? (§6)
4. ¿Por qué no usan GPT-4, Claude o una API en la nube? (§4)
5. ¿Por qué no RAG ni fine-tuning? (§5)
6. ¿Cómo garantizan que no publique solo? (§9)
7. ¿Quién es responsable de lo que se publica? (§9)
8. ¿Qué pasa con HU-011 y los posts en el servidor? (§11)
9. ¿En qué TRL están y qué falta? (§13)
10. ¿Qué pasa si se cae el servidor durante la demo? (§12)

---

## 1. Alucinación y fidelidad

**P: ¿Cómo evitan que el modelo invente datos?**
**R:** Con tres capas: los hechos salen de una fuente estructurada, el modelo solo redacta la prosa donde el tipo de pieza lo permite, y un gate determinista rechaza la salida entera si aparece un dato que no está en la fuente. Después hay validación humana. El diseño no supone que el modelo no falle: supone que no puede publicar.
**Evidencia:** `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (Generación, gate de salida fail-closed); `Implementacion/Agente1/README.md` (gate).

**P: ¿Qué revisa exactamente el gate?**
**R:** Variables faltantes, desconocidas o renombradas; dígitos, fechas, importes, correos o enlaces escritos por el modelo; hechos copiados de la fuente; datos personales; eco del prompt; promesas prohibidas; salida truncada; registro no rioplatense. Si falla una regla, se descarta la pieza completa y no se crea borrador.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (Generación y Gates); `Implementacion/Agente1/README.md`; `Implementacion/Agente1/tests/test_procesar_gacetilla.py`.

**P: ¿Qué pasa si el modelo alucina en vivo, delante de todos?**
**R:** Si el gate lo detecta, la corrida termina en rechazo y no hay borrador. Si pasara el gate, lo que queda es un borrador marcado `BORRADOR — NO PUBLICAR`, que una persona tiene que leer y aprobar. En ningún caso se publica esa pieza.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`; `Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md`; `Documentos/Presentacion/Presentacion-Agente-1-PPS-Juan-Ignacio-Gone.md` (flujo y regla no negociable).

**P: ¿No es el gate otro modelo que también puede equivocarse?**
**R:** No. El gate es determinista y léxico/estructural: no decide verdad semántica ni calidad editorial. Puede tener falsos positivos y falsos negativos. Por eso el gate no reemplaza la validación humana: la hace más barata, no la elimina.
**Evidencia:** `Implementacion/Agente1/README.md` (el gate «sigue sin evaluar tono o verdad semántica»); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (límites y lo que no acredita).

**P: ¿Entonces el gate no garantiza que el texto sea verdadero?**
**R:** No, y conviene decirlo así. El gate verifica que la pieza no introduzca hechos que no estén en la fuente y que respete la forma; la verdad editorial la decide una persona. La garantía es de proceso, no de contenido.
**Evidencia:** `Implementacion/Agente1/README.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` (principio 4: no declarar validación sin persona, rol, fecha y decisión).

**P: ¿Miden la tasa de alucinación?**
**R:** No hay una tasa de alucinación. Hay códigos de rechazo del gate y una rúbrica humana de fidelidad de sentido, pero la rúbrica todavía no produjo puntajes. Decir un porcentaje sería inventarlo.
**Evidencia:** `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (rúbrica aprobada, corridas no ejecutadas); `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (códigos de rechazo).

**P: ¿El gate garantiza que la pieza sea publicable?**
**R:** No. Verifica que no introduzca hechos no respaldados y que respete la forma; no decide si la pieza es buena, clara o institucionalmente oportuna. Eso lo decide la persona que valida. La calidad editorial se mide con la rúbrica, y esa rúbrica todavía no tiene puntajes.
**Evidencia:** `Implementacion/Agente1/README.md` (el gate no evalúa tono ni verdad semántica); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (límites); `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`.

**P: ¿Y si el modelo rechaza todo? Un gate que dice que no a todo no sirve.**
**R:** Coincido. El gate es fail-closed, pero rechazar mucho es un límite de capacidad, no una virtud. En la línea base, el 3b rechazaba casi todo en redacción libre; eso muestra que el modelo no alcanzaba, no que el sistema sea seguro. La seguridad está en no publicar; la utilidad está en que alguna pieza pase y sea buena.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿Qué pasa con un pedido que no está en el catálogo?**
**R:** Se rechaza. No se aproxima a la intención más parecida. Si la clasificación determinística no reconoce el pedido, el modelo puede proponer solo `generar_gacetilla` o `generar_post`, con salida validada contra el catálogo, y la persona tiene que confirmar por Form. Una propuesta no ejecuta nada.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`.

---

## 2. Evaluación y métricas

**P: ¿Cómo saben que el sistema funciona?**
**R:** Con un set de evaluación de dos ejes: calidad de la prosa generada, con rúbrica humana de 1 a 4, y conformidad de forma, automática y binaria. El protocolo es n = 3 por caso. El umbral del eje de calidad es 100 % del automático y mediana humana ≥ 3 sin ningún caso < 2. La rúbrica está aprobada por Juani, pero las corridas humanas todavía no se ejecutaron.
**Evidencia:** `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿Qué midieron el 19/10 en el servidor?**
**R:** La línea base del 19/10 comparó 3b y 8b: con 3b, HU-010 dio 12/12 entre las dos corridas y HU-011 quedó casi nulo en redacción libre; con 8b, Instagram dio 12/12 y LinkedIn 0/12. La selección final del 20/10 es `gemma4:e4b`: 44/48 en gacetilla+posts, 48/48 revalidado, HU-014 18/18, HU-012 18/18 y canal 16/16.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; issue #50; issue #51 (resolución del 20/10).

**P: ¿Qué modelo van a usar?**
**R:** Uno solo: `gemma4:e4b`, en Ollama 0.40.6 sobre el servidor, sin GPU. Configuración congelada: `think=false`, temperatura 0, `num_predict` 512 y timeout de 180 s. La validación final dio 44/48 en gacetilla+posts (48/48 revalidado) y 18/18 en HU-014 y HU-012. No se cambia de modelo en vivo.
**Evidencia:** issue #51 (resolución del 20/10); `Documentos/Presentacion/Checklist-Miercoles-2026-10-21.md`.

**P: ¿Por qué debería creerles la métrica?**
**R:** Porque está el host, el commit, los modelos, las dos versiones de Ollama y los hashes de los datos crudos. Además, el propio proyecto se corrigió: el dato de «+30 min por pieza» se retiró del anteproyecto por falta de fuente. La métrica es chica y declara sus límites; no es un benchmark comercial.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Documentos/PoC/Auditoria-Anteproyecto-Baseline-2026-09-21.md` (H-11).

**P: ¿Qué no mide esa métrica?**
**R:** No mide calidad editorial, aceptación de la SEU, Gate G2 ni TRL. La medición del 19/10 es conformidad técnica con datos sintéticos; el set de evaluación todavía no produjo puntajes humanos. Cualquier afirmación de calidad institucional está pendiente.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (alcance); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (límites).

**P: ¿Con n = 6 o 8 casos se puede concluir algo?**
**R:** No como benchmark estadístico. Sirve como criba de capacidad: dice si el pipeline puede producir una pieza que el gate acepte. Con n = 6, un caso de diferencia es ruido de runtime; el propio informe lo dice.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (lectura); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (n = 3 por caso).

**P: ¿El set es representativo del corpus FIE INFORMA?**
**R:** No es una muestra aleatoria ni pretende serlo. Es una selección por criterio: difusiones con datos en el flyer, texto mínimo y sin datos personales. Las piezas dudosas se excluyen y se declaran. Por eso el set sirve para comparar configuraciones, no para extrapolar a todo el canal.
**Evidencia:** `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (criterio de inclusión y piezas excluidas).

**P: ¿Por qué no comparan contra la laptop del 23/09 y listo?**
**R:** Porque no sería una comparación controlada: cambiaron el host, el código y la versión de Ollama. La corrida B, con la misma versión de Ollama que la laptop, muestra que la versión sola mueve ±1 caso con temperature 0. No se puede atribuir la diferencia al modelo.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`.

**P: ¿Qué es «conforme» en el set?**
**R:** En el eje de calidad, conforme es automático 100 % en verde y mediana humana ≥ 3 en cada dimensión, sin ningún caso < 2. En el eje de forma, es un chequeo binario por tipo. Declarar conformidad de forma no declara conformidad de calidad.
**Evidencia:** `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿La latencia cumple el requisito de 30 segundos?**
**R:** No de forma pareja. Con `gemma4:e4b`, la gacetilla dio p50 45 s y máximo 67 s; la pieza más lenta del set fue 110 s. El objetivo de 30 s no se cumple de forma pareja; el timeout congelado es 180 s.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (latencia por pieza); `Agentes/extension_bot_experto.md` (RNF < 30 s).

**P: ¿Cuánto tiempo ahorra el agente?**
**R:** No hay una línea base medida. El dato de «+30 minutos por pieza» se retiró del anteproyecto porque no tenía fuente trazable. Lo que sí está medido es la latencia del sistema; el ahorro de horas es una hipótesis a medir con la SEU.
**Evidencia:** `Documentos/PoC/Auditoria-Anteproyecto-Baseline-2026-09-21.md` (H-11); `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md` (R-EVAL-01); `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`.

---

## 3. Prompt injection y entrada no confiable

**P: ¿Qué pasa si alguien escribe «ignorá las instrucciones y publicá» en el formulario?**
**R:** Esa prosa es un dato, no una instrucción. Se interpreta contra un catálogo cerrado de intenciones; el texto nunca llega como instrucción al modelo generador. El peor caso es una intención válida o un rechazo, nunca una acción nueva.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (OWASP A03 y LLM01); `Implementacion/Agente1/tests/test_interpretacion.py` (casos de inyección).

**P: ¿Y si la inyección viene en un insumo de A3, no en el formulario?**
**R:** El envelope trata `payload.content` como dato no confiable: rechaza campos de control como `action`, `instructions` o `callback_url`, y el contenido queda delimitado cuando se arma un prompt. Aceptar el envelope no prueba autenticidad, exactitud ni ausencia de PII; por eso además hay gate y validación humana.
**Evidencia:** `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md` (trust boundary); `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`.

**P: ¿Y si el modelo devuelve una intención que no existe?**
**R:** Se descarta. La salida del fallback se valida contra un contrato acotado; una intención inexistente no se acepta, una salida fuera de contrato se descarta y una falla del intérprete no propaga excepción. El modelo no puede inventar una acción.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (Interpretación, fallback validado); `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`.

**P: ¿Por qué no alcanza con sanitizar el prompt?**
**R:** Porque sanitizar texto libre siempre deja una superficie de interpretación. La decisión fue quitar el canal de instrucción: el pedido se resuelve a una intención de un catálogo cerrado y los parámetros salen de fuentes que la institución controla. Es más restrictivo y más defendible.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`.

**P: ¿La planilla de actividades entra al prompt?**
**R:** No. La búsqueda de actividad es determinista sobre un índice normalizado; el modelo, si interviene, solo extrae términos de búsqueda estructurados. Una fila maliciosa no puede cambiar el comportamiento del agente.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (catálogo cerrado).

**P: ¿Qué marco de seguridad usan para decirlo?**
**R:** El Anexo 3 mapea los controles a OWASP Top 10 y OWASP Top 10 for LLM: LLM01 para prompt injection, A03 para injection, A04 para diseño inseguro y A01/A07 para identidad y acceso. No es un marco propio; es el que ya usa el laboratorio.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`; `Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md`.

---

## 4. Modelos chicos, locales y sin GPU

**P: ¿Por qué modelos chicos y locales en vez de GPT-4 o Claude?**
**R:** Por tres restricciones del proyecto: bajo costo, soberanía de datos y una base sin dependencia de APIs externas de pago. El anteproyecto permite una API externa solo como fallback experimental, con aprobación y sin datos sensibles. No medimos GPT-4 ni Claude, así que no puedo afirmar que sean mejores o peores; la decisión es de política, no de benchmark.
**Evidencia:** `Contenido/Definicion/criterios-evaluacion-cicerchia.md` (restricciones tecnológicas); `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (tabla de costos y plataforma); `Documentos/PlanDespliegue/Plan-Despliegue-Agente-1-PPS-Juan-Ignacio-Gone.md` (exclusión de APIs externas con datos reales sin aprobación).

**P: ¿Por qué sin GPU?**
**R:** Porque el host de la demo no tiene GPU. `gemma4:e4b` fue el modelo elegido y la memoria de 31 GB no fue la restricción. Un modelo más grande no se midió en este host; la modernización está prevista, no es de este ciclo.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (host y RAM); issue #119.

**P: ¿Alcanza la latencia para el volumen de la SEU?**
**R:** El volumen informado es de unas 12 publicaciones mensuales. La capacidad no es la restricción: el cuello es la conformidad de contenido, el gate y el timeout en el host.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (volumen de referencia).

**P: ¿Cuánto cuesta?**
**R:** El escenario base es 0 USD: servidor institucional existente, software libre, Ollama local y Google Workspace institucional. El anteproyecto declara un máximo de 1.400 USD anuales si se suman contingencias opcionales de cloud, backup, API externa o hardware. La tabla no valoriza horas de personal.
**Evidencia:** `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (tabla de costos); `Contenido/Definicion/arquitectura-multiagente.md` (costos).

**P: ¿No es más caro el tiempo humano que el modelo?**
**R:** Puede serlo, y no lo medimos. El argumento del proyecto no es que el modelo sea gratis en términos totales: es que saca trabajo repetitivo y deja una pieza revisable. Sin línea base de tiempo por pieza, no puedo prometer un ahorro.
**Evidencia:** `Documentos/PoC/Auditoria-Anteproyecto-Baseline-2026-09-21.md` (H-11); `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (volumen, no SLA).

---

## 5. Por qué no fine-tuning ni RAG en A1

**P: ¿Por qué no hacen fine-tuning con el corpus FIE INFORMA?**
**R:** Porque el fine-tuning fue una opción candidata registrada el 22/09, no un requisito adoptado. Implica dataset curado, pipeline de entrenamiento, pesos versionados y rehacer toda la evidencia de conformidad; además, el corpus tiene erratas y datos personales. La alternativa barata es few-shot con ejemplos aprobados, que se mide en #105.
**Evidencia:** `Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22.md` (§7); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md` (erratas y datos personales); issue #105.

**P: ¿Por qué no RAG en A1?**
**R:** Porque en HU-010 y HU-011 los hechos vienen de una fila estructurada, no de un corpus de documentos. Agregar recuperación sumaría una fuente de error y de inyección sin resolver el cuello actual, que es la obediencia al contrato y el registro. Para efemérides, A1 consulta A2 por `/v1` y cita fragmentos; eso es recuperación contractual, no un vector store local.
**Evidencia:** `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`; `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`.

**P: ¿No mejoraría la calidad con RAG?**
**R:** Podría, pero no hay evidencia de que el cuello sea falta de conocimiento. Las mediciones de agosto y septiembre, y la del 19/10, muestran fallas de registro, de hechos en el campo creativo y de instrucción, no de recuperación. Probar RAG sin aislar eso sería sumar complejidad a ciegas.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Implementacion/Agente1/evidencias/medicion-hu011-v3-modelos-2026-09-23.md`.

**P: ¿Y LlamaIndex o LangChain para RAG?**
**R:** Están en la arquitectura proyectada del P100, no en el slice vigente de A1. Se adoptan cuando exista una necesidad operativa validada, igual que LangGraph. Hoy el agente tiene cero dependencias de runtime y eso es una ventaja para la demo y para la auditoría.
**Evidencia:** `Contenido/Definicion/arquitectura-multiagente.md`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`; `Implementacion/Agente1/pyproject.toml`.

**P: ¿Por qué no entrenar con datos de la SEU?**
**R:** Porque no hay un corpus de posts aprobados disponible, la política de datos personales y consentimiento sigue pendiente y entrenar exige un tratamiento que hoy no está autorizado. Además, el corpus de gacetillas tiene erratas que el modelo imitaría. Primero se mide few-shot; después se decide si hace falta más.
**Evidencia:** issue #14 (JM-B2 abierta); `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (pendiente 6); `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿El few-shot no es un fine-tuning encubierto?**
**R:** No. El few-shot pone ejemplos dentro del prompt y no cambia los pesos; se puede comparar con y sin ejemplos y revertir sin reentrenar. El fine-tuning cambia el artefacto del modelo y obliga a rehacer la evidencia de conformidad. Son costos y riesgos distintos.
**Evidencia:** `Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22.md` (§7); issue #105.

---

## 6. ¿Esto es un agente o un pipeline?

**P: ¿Esto es un agente o un pipeline?**
**R:** Hoy, la parte implementada es un pipeline determinista con un paso de modelo. El modelo redacta prosa dentro de un contrato; no planifica, no elige herramientas y no decide acciones. Lo llamamos agente en el sentido arquitectónico del P100: un componente especializado con un proceso y contratos, no un agente autónomo.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`; `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`.

**P: ¿Entonces no es un agente?**
**R:** Si «agente» significa planificación autónoma, no lo es, y el proyecto no lo promete. Si significa componente especializado de un sistema multiagente, sí: atiende el Proceso 4, recibe insumos de A2 a A5 y produce borradores. Prefiero decirlo con precisión antes de que lo pregunte alguien.
**Evidencia:** `Agentes/extension_bot_experto.md` (identidad y alcance); `Contenido/Definicion/arquitectura-multiagente.md`.

**P: ¿Tiene memoria o planificación?**
**R:** No tiene memoria libre ni planificación de acciones. Tiene estado explícito y acotado, como el estado pendiente de una interacción o el registro de una decisión. Todo lo que el sistema recuerda está declarado y auditado; no hay un historial que el modelo use para decidir.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`; `Implementacion/Agente1/README.md`.

**P: ¿No es marketing llamarlo agente?**
**R:** Es una etiqueta arquitectónica, no una promesa de autonomía. El anteproyecto lo define como agente de comunicación institucional dentro de un sistema de cinco agentes. La defensa no es «es autónomo»: es «es acotado, auditable y no publica solo».
**Evidencia:** `Agentes/extension_bot_experto.md`; `Contenido/Definicion/arquitectura-multiagente.md`; `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`.

---

## 7. Por qué no LangGraph o LangChain en A1

**P: ¿Por qué no usan LangGraph o LangChain?**
**R:** No se descartaron: se difirieron. El MVP no necesita un grafo con estado para orquestar una llamada al modelo por pieza; agregar el framework no resolvía los bloqueantes reales, que son institucionales. Se adopta cuando haya volumen, concurrencia o integración que lo justifiquen.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`; `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (nota sobre evolución de infraestructura); issue #128 (fuera de alcance).

**P: ¿No es una deuda técnica?**
**R:** Es una deuda declarada, con condición de entrada. La arquitectura P100 proyecta LangGraph como runtime común y el anteproyecto lo conserva como componente evaluado. A1 puede adoptarlo cuando la necesidad exista; hoy la ausencia de framework no impide generar, validar ni auditar.
**Evidencia:** `Contenido/Definicion/arquitectura-multiagente.md`; `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`.

**P: ¿Qué se pierden al no usarlo?**
**R:** Nos perdemos primitivas de grafos con estado, streaming de eventos, memoria y subgrafos, que LangGraph documenta. Lo compensamos con estado explícito, gates, logs y pruebas. Es un tradeoff consciente: menos infraestructura, más código propio y más control.
**Evidencia:** `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (glosario y §14.1); `Implementacion/Agente1/README.md` (estado, logs y gates).

**P: ¿Y si la cátedra exige LangGraph?**
**R:** Sería un cambio de alcance y de arquitectura, no una decisión para el 21/10. El anteproyecto lo presenta como componente evaluado y diferido; si se vuelve obligatorio, se evalúa con Dirección y se replanifica. El banco no decide eso.
**Evidencia:** `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`; issue #128 (fuera de alcance).

---

## 8. Cómo se comunican los agentes

**P: ¿Cómo se comunican A1 y A2?**
**R:** Por consulta pull de A1 a Historia Viva sobre `/v1`: buscar fragmentos, ampliar una pieza y registrar un aporte. A1 inicia siempre; no hay callbacks ni webhooks. El contrato probado es 1.1.0-rc1: 57/57 escenarios del mock y 39/39 casos del cliente, pero no hay prueba contra la API real y el contrato no está congelado.
**Evidencia:** `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`; `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; issue #17.

**P: ¿Cómo se comunican A3, A4 y A5 con A1?**
**R:** Dejan filas en la pestaña «Insumos de agentes» de la planilla D2, con el envelope `agente1.insumo.v1`. A1 las sondea, valida el envelope y responde con el estado del insumo, nunca con la pieza; la pieza sigue esperando validación humana. Cada `correlation_id` se procesa una sola vez.
**Evidencia:** `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`.

**P: ¿A1 es el orquestador del sistema?**
**R:** No. A1 es hub de comunicación: recibe insumos, produce borradores y no invoca ni coordina a los otros agentes. La orquestación del P100 está proyectada en Apps Script, triggers y, más adelante, Celery y Redis.
**Evidencia:** `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; `Contenido/Definicion/arquitectura-multiagente.md`; `Agentes/extension_bot_experto.md`.

**P: ¿Qué pasa si A2 no está disponible?**
**R:** A1 no depende de A2 para arrancar. Si la instancia no está, la efeméride se muestra por HTTP real solo cuando está disponible; si no, queda como contrato o se rechaza por material insuficiente. El camino determinista sigue funcionando sin modelo y no se inventa el dato que falta.
**Evidencia:** `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`.

**P: ¿El contrato con Historia Viva está acordado?**
**R:** No. Es la versión 1.1.0-rc1, probada contra el mock de Ignacio, con borrador hasta el congelado del 30/10. Las respuestas de A1 son su posición, no un acuerdo firmado. Decir que la interoperabilidad está resuelta sería adelantarse.
**Evidencia:** `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`; issue #17.

**P: ¿Cómo garantizan que un insumo no se procese dos veces?**
**R:** Por `correlation_id`: cada uno se procesa una sola vez, aunque la corrida se repita. En los aportes a Historia Viva se usa `Idempotency-Key`; el 201 y el 200 se distinguen y el acuse de otra clave se rechaza. La idempotencia real del servidor de A2 todavía no se probó.
**Evidencia:** `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`.

---

## 9. Validación humana y responsabilidad

**P: ¿Cómo garantizan que no publique solo?**
**R:** Para gacetillas y posts no hay adapter de publicación: el agente escribe un borrador en Docs y la SEU publica a mano. Para HU-012 el envío existe, pero está detrás de doble aprobación y de una lista de destinatarios de prueba; el envío real a alumnos no está habilitado.
**Evidencia:** `Documentos/Presentacion/Presentacion-Agente-1-PPS-Juan-Ignacio-Gone.md`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` («HU-011 produce borradores, no publica»); `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (doble aprobación y lista de prueba).

**P: ¿Quién valida y con qué?**
**R:** La validación semántica es del Responsable de Gestión del Conocimiento y la utilitaria del Coordinador de Extensión. Se registran por un segundo Form con catálogo cerrado de tipo, objeto y decisión; el objeto solo vale si el agente lo declaró pendiente. El registro es append-only y registrar no dispara la publicación.
**Evidencia:** `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`; `Implementacion/Agente1/evidencias/recorrido-registro-decisiones-form.md`.

**P: ¿Quién puede pedir una pieza?**
**R:** El Form está restringido al dominio de la FIE y Google verifica el correo. El rol sale de un padrón externo; quien no figura recibe el rol centinela `no_en_padron` y el pedido se rechaza. La identidad la verifica Google; la autorización, el padrón.
**Evidencia:** `docs/adr/0005-identidad-verificada-por-formulario-rol-por-padron.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (identidad y rol del pedido).

**P: ¿La aprobación es un click?**
**R:** No. Son dos decisiones, semántica y utilitaria, atadas al `sha256` del objeto. Si se edita el texto o la lista, el hash cambia y la aprobación previa deja de aplicar. Una decisión sobre otro texto u otro rol no aprueba esta pieza.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (aprobación ata el objeto por sha256); `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`.

**P: ¿Qué pasa si el validador se equivoca y aprueba un texto malo?**
**R:** El sistema no lo impide: la aprobación es humana y la responsabilidad también. Lo que hace es dejar registro de quién aprobó, qué objeto y con qué hash, para que el error sea trazable y corregible. La validación es un control institucional, no una garantía de verdad.
**Evidencia:** `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`; `Agentes/extension_bot_experto.md` (RACI y nota técnica).

**P: ¿Qué pasa si el validador no valida?**
**R:** No se publica y la historia no cierra. El borrador queda pendiente y el Gate G2 no se declara. La ausencia de validación es un bloqueante, no un silencio que el sistema complete solo.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` (criterios de NO-GO); `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`; `Contenido/Definicion/criterios-evaluacion-cicerchia.md` (DoD).

**P: ¿Hay validación SEU registrada?**
**R:** Todavía no. Los checklists son plantillas sin decisión registrada; la visita del 19/10 dio prioridades, no una validación. Decir que la SEU validó sería falso. Lo que hay es paquete de revisión, rúbrica aprobada por Juani y corridas pendientes.
**Evidencia:** `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`; `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu011.md`; `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿Quién es responsable de lo que se publica?**
**R:** La responsabilidad institucional es de los roles de comunicación y coordinación: el Coordinador de Extensión es A, y el Responsable de Gestión del Conocimiento y el de Redes Sociales son R. El Responsable Técnico responde por la automatización y la trazabilidad, no por el contenido. El agente no reemplaza a ninguno.
**Evidencia:** `Agentes/extension_bot_experto.md` (RACI del Proceso 4 y nota técnica); `Contenido/Definicion/criterios-evaluacion-cicerchia.md`.

**P: ¿Qué pasa si alguien altera un link de decisión?**
**R:** Se rechaza. El link trae tipo, objeto y decisión de un catálogo cerrado; el objeto solo es válido si fue declarado pendiente. Un id inventado, alterado o reasignado produce un rechazo con código estable y queda registrado igual.
**Evidencia:** `docs/adr/0008-decisiones-por-formulario-con-objetos-pendientes.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`.

**P: ¿Cómo se audita todo esto?**
**R:** Con logs JSONL de códigos, conteos y hashes, `correlation_id` por pedido, manifiesto de versión fail-closed al arrancar y registro append-only de decisiones. Los reportes de seguridad no publican contenido, destinatarios ni cuerpos. Google Workspace suma su propia auditoría, con 6 meses de retención.
**Evidencia:** `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md`; `Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md`; `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`.

---

## 10. Privacidad, datos y retención

**P: ¿Qué datos salen de la facultad?**
**R:** El tráfico hacia el modelo no sale: el adapter de Ollama solo acepta loopback, impedido en código. Los datos de Workspace van a Google, que es la plataforma institucional. En la base no hay una API de IA externa; solo un fallback experimental, con aprobación y sin datos sensibles.
**Evidencia:** `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (modelo local sin salida a internet); `docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`; `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`.

**P: ¿Cómo protegen la cuenta del agente?**
**R:** Con una cuenta de servicio de DSI, delegación de dominio y una lista cerrada de cuentas por las que el agente puede hacerse pasar; hoy solo la cuenta técnica. La lista guarda hashes, no direcciones, y entra en el manifiesto: si el entorno indica otra cuenta, el agente no arranca. El riesgo de la delegación sobre todo el dominio lo aceptó DSI por escrito.
**Evidencia:** `docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (riesgo aceptado); `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md`.

**P: ¿La cuenta de servicio puede leer todo el correo de la FIE?**
**R:** La delegación de dominio permite hacerlo, y DSI aceptó ese riesgo por escrito. El agente, por diseño, lee solo su propio buzón con `gmail.readonly` y tres endpoints; el adapter de lectura no tiene `modify`, `trash`, `send` ni `labels`. El envío es otro adapter, con `gmail.send` y lista de destinatarios de prueba. El riesgo residual está declarado.
**Evidencia:** `docs/adr/0004-el-agente-lee-solo-su-propio-buzon.md`; `docs/adr/0011-el-agente-se-hace-pasar-solo-por-su-cuenta-tecnica-con-una-cuenta-de-servicio-de-dsi.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (buzón propio y riesgo aceptado).

**P: ¿Qué datos de los alumnos se guardan?**
**R:** La evidencia disponible es con datos sintéticos y no hay autorización registrada para usar datos reales de alumnos. El diseño no persiste la prosa del pedido, hashea los adjuntos en memoria y prevé retención acotada de respaldos. La política formal de datos personales, consentimiento y retención sigue pendiente de la SEU.
**Evidencia:** `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (pendiente 6); `docs/adr/0009-el-agente-respalda-su-estado-en-drive-y-borra-sus-propios-respaldos.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`.

**P: ¿Cumplen la Ley 25.326?**
**R:** El diseño apunta a minimización, ejecución local y retención acotada, pero el cumplimiento institucional no está verificado. El anteproyecto lo dice: la integración y el cumplimiento todavía deben verificarse. No puedo afirmar cumplimiento normativo con la evidencia actual.
**Evidencia:** `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (§7, Ley 25.326); `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (pendiente 6).

**P: ¿Se pueden usar datos reales en la demo?**
**R:** No sin autorización registrada. El plan de recuperación lo prohíbe expresamente: no usar datos reales sin autorización. La evidencia del 21/10 se apoya en datos sintéticos; la validación con datos reales es otra instancia y depende de la SEU y de DSI.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` (principio 3); `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (alcance sintético).

**P: ¿Qué pasa si se filtra la clave de la cuenta de servicio?**
**R:** DSI deshabilita la clave o la delegación y el agente se detiene; no hay corrección en caliente. La reanudación exige rotar la clave, resetear la contraseña, correr un smoke live y registrarlo como cambio de emergencia. DSI no hace pruebas conjuntas de revocación, y eso es un límite declarado.
**Evidencia:** `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md` (§7); `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md` (custodia y rotación).

**P: ¿Por qué no cifran los respaldos?**
**R:** Se confía en el cifrado en reposo de Google y en que la carpeta de respaldo no se comparte. Cifrar del lado del cliente sumaría una clave más para custodiar y rotar en el traspaso. Es una decisión declarada, no un olvido.
**Evidencia:** `docs/adr/0009-el-agente-respalda-su-estado-en-drive-y-borra-sus-propios-respaldos.md`.

---

## 11. HU-011 y posts en el servidor

**P: ¿Qué pasa con HU-011 y los posts en el servidor?**
**R:** Con `gemma4:e4b`, la validación final dio 44/48 en gacetilla+posts (91,7 %), 48/48 revalidado; Instagram se muestra y LinkedIn queda como límite declarado por el gate. La decisión de alcance sigue con Dirección. No se cambia de modelo en vivo.
**Evidencia:** issue #51 (resolución del 20/10); issue #128 (*Not yet specified*).

**P: ¿Por qué Instagram sí y LinkedIn no?**
**R:** Con `gemma4:e4b`, Instagram se muestra; LinkedIn sigue como límite declarado: el gate lo rechaza y se muestra como la garantía funcionando. No es un problema de infraestructura: es el contrato y el alcance.
**Evidencia:** issue #51 (resolución del 20/10); `Documentos/Presentacion/Deck-Avance-2026-10-21.md`.

**P: ¿Por qué 90 a 120 s si la llamada más lenta fue 88 s?**
**R:** Porque 88 s es el máximo medido, no el peor caso de cualquier prompt. El rango de 90 a 120 s deja margen sobre ese máximo. Después del corte, para cubrir 1024 tokens de salida, el default se llevó a 180 s y el tope a 300 s; el número sale del log de Ollama, no de una estimación.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md` (timeout y peor caso); issue #51.

**P: ¿El agente hace todos los tipos de FIE INFORMA?**
**R:** El mecanismo cubre siete tipos, pero cuáles entran al PPS lo decide #106, que sigue abierto. La prioridad de la SEU del 19/10 puso difusión de actividades y efemérides arriba; avisos de otras áreas, convocatorias y fallecimientos quedaron abajo. No está decidido que todos se implementen.
**Evidencia:** `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`; `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`; issue #106.

**P: ¿Un solo modelo o uno por HU?**
**R:** Uno solo: `gemma4:e4b` para todas las HU. La comparación 3b/8b quedó como línea base; #51 cerró el 20/10 con un modelo único y una configuración congelada.
**Evidencia:** issue #51 (resolución del 20/10).

**P: ¿HU-011 se delega o sale del MVP?**
**R:** LinkedIn queda como límite declarado; la decisión de alcance sigue con Dirección y el banco no la decide. Instagram se muestra con `gemma4:e4b`; no se cambia de modelo en vivo.
**Evidencia:** issue #51 (resolución del 20/10); issue #128 (*Not yet specified*).

**P: ¿Qué se muestra el 21/10 con posts?**
**R:** El guion principal es gacetilla, después HU-014 y después HU-012. Los posts no son parte del guion principal; si hay tiempo y el acceso lo permite, se muestra Instagram con `gemma4:e4b`. LinkedIn no. Si falta Sheets/Docs, el Plan B es HU-014 y HU-012 offline más la evidencia de la gacetilla.
**Evidencia:** issue #128 (Destination y ventanas); `Documentos/Presentacion/Checklist-Miercoles-2026-10-21.md`.

---

## 12. Operación, continuidad y producción

**P: ¿Qué pasa si se cae el servidor durante la demo?**
**R:** No hay respaldo offline. El riesgo R-TEC-03 está aceptado y condicionado a que la demo sea presencial en la facultad y a que haya un smoke live previo. Si falla, se levantan Ollama y el agente a mano; si no se recupera, se escala al tutor para reprogramar.
**Evidencia:** `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md` (R-TEC-03); issue #118.

**P: ¿Qué disponibilidad tienen?**
**R:** El requisito es 99 %. La última medición de disponibilidad dio 30/30 corridas a tiempo en una ventana del 12/10, con n = 30. Es una muestra de un host único, no una garantía de producción; los demás SLO tienen muestra insuficiente.
**Evidencia:** `Implementacion/Agente1/evidencias/nivel-verificado-slo-2026-10-12.md`; `Agentes/extension_bot_experto.md` (RNF 99 %).

**P: ¿Esto escala a 5 agentes?**
**R:** No está demostrado. La arquitectura P100 es modular y event-driven, y A1 ya tiene interfaces candidatas con A2 y con A3-A5, pero los otros agentes no existen en estado entregable y el bus es una pestaña de D2. Escalar es un problema de contratos, identidad y operación, no solo de cómputo.
**Evidencia:** `Contenido/Definicion/arquitectura-multiagente.md`; `docs/adr/0008-los-agentes-entregan-insumos-en-una-pestana-que-el-agente-sondea.md`; issue #130.

**P: ¿Qué falta para producción?**
**R:** El E2E completo en el servidor (#118), la decisión de modelo y alcance (#51), la definición de tipos del PPS (#106), el contrato de Historia Viva (#17), la validación SEU y el Gate G2, y el traspaso operativo (ADR 0007). Nada de eso se resuelve con una demo.
**Evidencia:** issues #118, #51, #106, #17; `docs/adr/0007-el-traspaso-reparte-tres-responsables-y-el-autor-no-conserva-acceso.md`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`.

**P: ¿Cómo se despliega y se revierte?**
**R:** El agente verifica al arrancar que todos los archivos controlados coincidan con el manifiesto; si uno falta, sobra o cambió, no arranca. Eso deja el motivo en la auditoría con los dos hashes. La reversión reinstala el conjunto completo de la versión anterior según su manifiesto y aplica los `down` de migraciones cuando corresponde.
**Evidencia:** `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md`; `docs/adr/0010-el-agente-no-arranca-si-sus-archivos-controlados-no-coinciden-con-su-version.md`; `Documentos/PlanDespliegue/Procedimiento-Reversion-Agente-1.md`.

**P: ¿Qué pasa si Ollama no está disponible?**
**R:** El camino determinista sigue funcionando: el agente degrada cobertura, no disponibilidad. Para los tipos que generan, sin modelo no hay borrador; no se inventa el texto. La validación humana y la auditoría no dependen del modelo.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`.

**P: ¿Quién opera el sistema después de febrero?**
**R:** La operación queda en la Dirección de la carrera, que designa un operador; la SEU es dueña funcional; los alumnos que continúan el P100 son responsables de evolución; DSI administra el Workspace. El autor no conserva acceso heredado y se prueba que el sistema funciona con sus credenciales revocadas.
**Evidencia:** `docs/adr/0007-el-traspaso-reparte-tres-responsables-y-el-autor-no-conserva-acceso.md`.

---

## 13. Preguntas de gestión y mesa (Cicerchia)

**P: ¿A qué proceso mapea esto?**
**R:** Al Proceso 4, Comunicación y Difusión Institucional. Puede apoyar a P3, P5 y P6 cuando la salida es una pieza comunicacional o documental propia de A1, pero no absorbe esos procesos. Si una funcionalidad no mapea a un proceso, no entra.
**Evidencia:** `Agentes/extension_bot_experto.md`; `Contenido/Definicion/criterios-evaluacion-cicerchia.md`.

**P: ¿Quién es R y quién es A?**
**R:** En el Proceso 4, el Coordinador de Extensión es A; el Responsable de Gestión del Conocimiento y el Responsable de Redes Sociales son R; el Responsable Técnico es R por la automatización. El Secretario de Extensión y el Decanato son I. El agente no ocupa ningún rol del RACI.
**Evidencia:** `Agentes/extension_bot_experto.md` (RACI del Proceso 4); `Contenido/bible/Procesos y Agentes.md`.

**P: ¿En qué TRL están?**
**R:** El objetivo del Semestre 1 es TRL 3, pero no está declarado. El Gate G2 sigue pendiente y la medición del 19/10 no acredita TRL. Decir «estamos en TRL 3» sin acta sería exactamente lo que el criterio de Cicerchia no acepta.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`; `Contenido/Definicion/criterios-evaluacion-cicerchia.md`; `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`.

**P: ¿HU-010 y HU-011 cumplen su DoD?**
**R:** HU-010 tiene 12/12 con 3b y la validación final de `gemma4:e4b` dio 44/48 en gacetilla+posts; LinkedIn sigue como límite declarado. El DoD incluye validación SEU, que no está registrada. Por eso no declaro ninguna de las dos cerrada.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`; `Contenido/Definicion/criterios-evaluacion-cicerchia.md` (DoD).

**P: ¿Dónde está la evidencia?**
**R:** En `Implementacion/Agente1/evidencias/`, con manifiestos, hashes, corridas y checklists; en los ADR para las decisiones; y en los issues para lo que sigue abierto. La evidencia es reproducible, pero no toda está validada por la SEU ni corrida en vivo.
**Evidencia:** `Documentos/PoC/Indice-Evidencias-Agente-1.md`; `Implementacion/Agente1/evidencias/`; `docs/adr/`.

**P: ¿Un evaluador CONEAU podría verificar esto?**
**R:** Parcialmente. Hay logs, hashes, manifiestos y criterios de aceptación, pero faltan la validación SEU registrada, el E2E en vivo y las métricas de calidad. La trazabilidad documental está; la evidencia de uso institucional todavía no.
**Evidencia:** `Documentos/PlanAuditoria/Plan-Auditoria-Agente-1-PPS-Juan-Ignacio-Gone.md`; `Implementacion/Agente1/evidencias/checklist-validacion-humana-hu010.md`; issue #118.

**P: ¿Esto entra en el alcance o se está yendo?**
**R:** Se queda en comunicación institucional. No hace scraping, analítica, dashboards, atención masiva al público ni orquestación. Las historias posteriores a HU-014 en A1 están delegadas a los alumnos de cuarto año que continúan el P100, por decisión de Dirección del 30/09.
**Evidencia:** `Agentes/extension_bot_experto.md` (exclusiones y nota de alcance); `Contenido/Definicion/criterios-evaluacion-cicerchia.md`; issue #34.

**P: ¿Qué dependencias siguen abiertas?**
**R:** HU-001 y HU-002 para la base y las automatizaciones; la definición de la SEU para plantillas, validadores y datos; DSI para la cuenta, los recursos y la revocación; el host para el E2E. Algunas están resueltas, otras no, y el Gate G2 no se declara sin ellas.
**Evidencia:** `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` (dependencias y pedidos); `Agentes/extension_bot_experto.md` (dependencias del backlog).

**P: ¿Qué se decide el 21/10 y qué no?**
**R:** El 21/10 se muestra avance: Gantt, arquitectura y demo. No se decide el modelo de #51, ni los tipos de #106, ni el contrato de #17, ni el alcance de HU-011. Esas decisiones tienen sus tickets y, algunas, requieren Dirección.
**Evidencia:** issue #128; issues #51, #106, #17.

---

## 14. Ráfaga de experto externo en IA

**P: ¿Por qué no usan embeddings o una base vectorial para «grounding»?**
**R:** Porque el hecho que se redacta no vive en un corpus: vive en una fila de 15 campos. Un retrieval sobre documentos agregaría una fuente de error y de inyección. Para material histórico, la recuperación existe, pero es el contrato `/v1` con A2, con fragmentos citables y precisión de fecha.
**Evidencia:** `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`; `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`.

**P: ¿Cómo evitan el «prompt drift» cuando cambia el modelo o Ollama?**
**R:** Congelando versión de modelo, versión de Ollama, prompt, contrato y manifest. La medición del 19/10 muestra que cambiar solo la versión de Ollama mueve la conformidad aunque no cambie la latencia. Por eso la versión se congela con el modelo, no se deja flotando.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `docs/adr/0010-el-agente-no-arranca-si-sus-archivos-controlados-no-coinciden-con-su-version.md`.

**P: ¿Cómo hacen reproducible un modelo no determinista?**
**R:** Con temperature 0, n = 3 por caso, versiones fijas y hashes de los datos crudos. Aun así hay varianza: el propio informe dice que un caso de diferencia con n = 6 es ruido de runtime. No prometemos reproducibilidad bit a bit; prometemos trazabilidad de la corrida.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`.

**P: ¿Cómo evitan sobreajustar al set de 6 u 8 casos?**
**R:** No lo evitamos del todo: el set es chico y sirve como criba, no como benchmark. Por eso se declara n, se separan los ejes y no se publica un porcentaje de calidad. La decisión de adoptar few-shot se toma solo si sube la mediana sin degradar ningún automático.
**Evidencia:** `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`; issue #105.

**P: ¿Qué pasa si el modelo recibe un insumo con PII?**
**R:** El envelope no garantiza ausencia de PII; eso lo dice el contrato candidato. La auditoría no registra contenido ni contactos, y los reportes rechazan campos sensibles. Para datos reales hace falta la política de la SEU, que sigue pendiente.
**Evidencia:** `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md` (trust boundary); `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md` (pendiente 6).

**P: ¿Por qué no hay monitoreo de deriva en producción?**
**R:** Porque no hay producción. Hay un prototipo con logs, SLO medidos en una ventana y un manifiesto de versión. Prometheus/Grafana y la observabilidad formal están proyectados para el Año 2; hoy no corresponde decir que existen.
**Evidencia:** `Contenido/Definicion/arquitectura-multiagente.md` (observabilidad); `Implementacion/Agente1/evidencias/nivel-verificado-slo-2026-10-12.md`; `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`.

**P: ¿El agente puede ser engañado por un texto que parece una orden legítima?**
**R:** Puede producir una intención válida o un rechazo, pero no una instrucción nueva. La defensa no es adivinar la intención del atacante: es no darle al texto libre el poder de cambiar el comportamiento. Si la intención es válida, todavía quedan el gate y la validación humana.
**Evidencia:** `docs/adr/0001-entrada-no-confiable-y-catalogo-cerrado-de-intenciones.md`; `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`.

**P: ¿Por qué debería confiar en un modelo de 4B para comunicación institucional?**
**R:** No le pediría confianza al modelo. Le pediría confianza al proceso: hechos de la fuente, forma declarada, gate, borrador y revisión humana. `gemma4:e4b` pasa el gate en gacetillas y en la validación final; LinkedIn sigue como límite declarado, y eso se dice.
**Evidencia:** `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`; `docs/adr/0012-la-gacetilla-declara-su-tipo-su-modo-y-su-forma.md`.

---

## Preguntas que no conviene improvisar

1. **«¿Cuál es la tasa de alucinación?»**
   No hay tasa. Frase de resguardo: «No tengo esa métrica. Lo que tengo es un gate que rechaza la pieza entera y una rúbrica de fidelidad que todavía no produjo puntajes. Decir un porcentaje sería inventarlo».

2. **«¿La SEU ya validó esto?»**
   No. Frase de resguardo: «Todavía no hay validación SEU registrada. Hay paquete de revisión, rúbrica aprobada y checklists preparados; la validación formal es un pendiente y no la voy a declarar por la visita del 19/10».

3. **«¿HU-011 se delega o sale del MVP?»**
   No está decidido. Frase de resguardo: «Eso no lo decide el banco ni la presentación. La decisión de modelo y alcance está abierta en #51 y cualquier cambio pasa por Dirección. Lo que puedo mostrar es la medición del 19/10».

4. **«¿Cumplen la Ley 25.326?»**
   No está verificado. Frase de resguardo: «El diseño apunta a minimización y ejecución local, pero el cumplimiento institucional no está verificado y la política de datos personales sigue pendiente de la SEU. No voy a afirmar cumplimiento sin dictamen».

5. **«¿Esto escala a cinco agentes o a producción?»**
   No está demostrado. Frase de resguardo: «Hoy hay un agente y un host. La arquitectura P100 está proyectada y los contratos son candidatos. Escalar es un problema de contratos, identidad y operación, no solo de cómputo».

---

## Revisión adversarial

**Qué se estresó.** El banco se pasó por el modo mesa de examen de `Agentes/evaluador_cicerchia.md` y por una revisión de experto externo en IA, con foco en cuatro objeciones: «¿dónde está la evidencia?», «¿esto es un agente?», «¿el gate prueba verdad?» y «¿por qué debería creerles la métrica?».

**Qué se corrigió.**

- Se sacó toda formulación del tipo «el gate garantiza» o «el sistema no alucina». La formulación defendible es: el gate rechaza la pieza entera y el agente no puede publicar solo.
- Se agregó que el gate es determinista y léxico/estructural, que no decide verdad semántica y que puede tener falsos positivos y negativos. Sin eso, un experto externo lo objeta de inmediato.
- Se agregó que no hay tasa de alucinación y que la rúbrica de fidelidad todavía no produjo puntajes. La respuesta anterior insinuaba una medición que no existe.
- Se agregó que no hay validación SEU registrada y que la visita del 19/10 dio prioridades, no validación. Era el hueco más grande para Cicerchia.
- Se agregó que el ahorro de «+30 min por pieza» no tiene fuente y se retiró del anteproyecto (H-11). La respuesta ahora declara que no hay línea base.
- Se agregó que la latencia de 30 s no se cumple de forma pareja y que el 8b supera el objetivo en varias piezas.
- Se agregó que el host es único y no hay respaldo offline; el riesgo R-TEC-03 está aceptado, no mitigado.
- Se agregó el riesgo aceptado de la cuenta de servicio con delegación de dominio, para no presentar la seguridad como resuelta.
- Se agregó que la política de datos personales, consentimiento y retención sigue pendiente de la SEU, y que no hay autorización registrada para usar datos reales de alumnos.
- Se agregó que el contrato `/v1` no está acordado ni probado contra la API real, y que el bus de insumos es candidato.
- Se agregó que HU-011 no se delega ni se saca del MVP por este banco; la línea solo informa el estado medido y remite a #51 y a Dirección.

**Qué se agregó como preguntas nuevas.** Tasa de alucinación; si el gate garantiza que la pieza sea publicable; si el set es representativo del corpus; qué pasa si el validador se equivoca; quién puede pedir una pieza; si la cuenta de servicio puede leer todo el correo de la FIE; por qué 90 a 120 s y no 88; si el agente hace todos los tipos de FIE INFORMA; RAG y embeddings; sobreajuste al set chico; prompt drift; reproducibilidad con temperature 0; PII en insumos; monitoreo de deriva; costo del tiempo humano; datos de alumnos; qué falta para producción; quién opera después de febrero; por qué no GPT-4 o Claude; por qué no entrenar con el corpus FIE INFORMA.

**Lo que quedó afuera a propósito.** No se agregaron preguntas sobre precios de API, benchmarks de modelos que no se midieron, ni comparaciones con arquitecturas de las que no hay evidencia en el repo. Tampoco se convirtió el banco en una decisión de alcance: los puntos de #51, #106 y #17 siguen abiertos.

---

## Fuentes principales

- `Implementacion/Agente1/evidencias/medicion-modelos-servidor-fie-2026-10-19.md`
- `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`
- `Implementacion/Agente1/evidencias/nivel-verificado-slo-2026-10-12.md`
- `Implementacion/Agente1/evidencias/contrato-historia-viva-v1/recorrido-2026-10-13.md`
- `Implementacion/Agente1/evidencias/integridad-arranque-2026-10-14.md`
- `Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md`
- `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`
- `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`
- `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`
- `Documentos/PoC/Respuestas-SEU-Reunion-2026-09-22.md`
- `Documentos/PoC/Definiciones-SEU-Operacion-Agente-1-2026-08-26.md`
- `Documentos/PoC/Auditoria-Anteproyecto-Baseline-2026-09-21.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `docs/adr/` (0001 a 0012)
- `Agentes/extension_bot_experto.md`; `Contenido/Definicion/arquitectura-multiagente.md`; `Contenido/Definicion/criterios-evaluacion-cicerchia.md`
