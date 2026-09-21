# Auditoría del anteproyecto contra baseline técnica real

- **Fecha de auditoría:** 2026-09-21
- **Entregable auditado:** `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex` (1341 líneas)
- **Commit auditado:** `8824b5e` (merge del fallback con modelo local de HU-013, 2026-09-09). Nota: al momento de la auditoría el HEAD real es `803f33d` (2026-09-21), con tres commits posteriores estrictamente documentales/de higiene (`f83a0af`, `692a75d`, `803f33d`) que no alteran el estado del código. El `.tex` en sí no cambia desde `4d7be9e` (2026-09-08, "align the anteproject with the demonstrated baseline").
- **Baseline verificada en esta auditoría:** `cd Implementacion/Agente1 && uv run pytest -q` → **749 pruebas verdes** (28,1 s), re-ejecutado por el auditor sobre el worktree vigente. Coincide con `Documentos/PoC/Registro-Defectos-Agente-1.md` (regresión vigente al 2026-09-09, reverificada el 2026-09-21).
- **Alcance:** auditoría de consistencia documental. No se editó el `.tex` ni ningún archivo existente. Estados posibles: `CONSISTENTE`, `INCONSISTENTE`, `DESACTUALIZADO`, `SIN_FUENTE`, `PENDIENTE_EXTERNO`.
- **Fuentes contrastadas:** `Contenido/bible/Procesos y Agentes.md`, `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`, `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`, `Contenido/DocumentacionAnteproyecto/EstructuraAnteproyecto.md`, `Documentos/Comun/definiciones.tex`, `Documentos/PoC/` (Plan de Recuperación, Registro de Defectos, Índice de Evidencias, Nota de Consulta a Dirección), `Implementacion/Agente1/` (código, `evidencias/`, ADR 0001/0002), `respuesta-nacho.md`.

---

## 1. Estructura oficial: confirmación

**Las 20 secciones oficiales están presentes y en orden.** Verificado contra `Contenido/DocumentacionAnteproyecto/EstructuraAnteproyecto.md` y contra el `.toc` compilado:

| # | Sección oficial | Línea `\section` / comando | Estado |
|---|---|---|---|
| — | Portada | `titlepage`, líneas 89–120 | Presente (con defecto, ver H-02) |
| 0 | Índice | `\tableofcontents`, línea 124 | Presente |
| 1 | Resumen | línea 130 | Presente |
| 2 | Palabras clave | línea 143 | Presente |
| 3 | Glosario | línea 150 | Presente |
| 4 | Introducción | línea 206 | Presente |
| 5 | Formulación del problema | línea 221 | Presente (incluye tabla Causa–Efecto) |
| 6 | Antecedentes | línea 254 | Presente |
| 7 | Propósito y justificación | línea 279 | Presente |
| 8 | Objetivos globales y específicos (As Is / To Be) | línea 306 | Presente |
| 9 | Alcances (del Proyecto / del Producto) | línea 333 | Presente, ambas subsecciones |
| 10 | Marco referencial | línea 410 | Presente |
| 11 | Ciclo de vida | línea 461 | Presente |
| 12 | Metodología(s) candidata(s) | línea 563 | Presente |
| 13 | Plataforma requerida | línea 592 | Presente |
| 14 | Enunciado de factibilidad | línea 628 | Presente |
| 15 | Acuerdos preliminares de seguridad y calidad | línea 755 | Presente |
| 16 | Participantes (EdP / Interesados) | línea 818 | Presente, ambas subsecciones + RACI |
| 17 | Presentación de la propuesta (+ storyboard) | línea 886 | Presente, storyboard en §17.5 |
| 18 | Cronograma de alto nivel (EDT + cronograma) | línea 1117 | Presente |
| 19 | Métricas | línea 1246 | Presente |
| 20 | Referencias y bibliografía | `\printbibliography`, línea 1339 | Presente |

**Observación formal:** la estructura está completa. Las figuras están etiquetadas y referenciadas; no se detectaron títulos sueltos. El artefacto `Anteproyecto-PPS-Juan-Ignacio-Gone.pdf` compilado está **desactualizado** respecto de la fuente (fecha de portada renderizada: 22 de junio de 2026); conviene recompilar antes de cualquier entrega, aunque esto no afecta la auditoría de la fuente `.tex`.

---

## 2. Tabla de hallazgos

| ID | Sección .tex | Línea(s) | Afirmación | Estado | Corrección sugerida |
|---|---|---|---|---|---|
| H-01 | §8 OE3 / §9.2.1 / §17.2 / §17.3 / §18.1 | 321, 354, 967, 995, 1136 (y storyboard paso 6, línea 1043) | HU-012 describe el envío habilitado por "**una** aprobación humana registrada" (aprobación única). | `INCONSISTENTE` con la bible; consistente con la implementación defectuosa vigente | La bible exige **dos aprobaciones independientes** —semántica del RGC + utilitaria del Coordinador de Extensión— antes de habilitar publicación o envío (Bloque 2 "Human in the Loop", CU10: "si el bot detecta que el borrador recibió **ambas** aprobaciones"; CP18/CP19 del plan de pruebas). El defecto está registrado como `DEF-A1-016` (`ABIERTO`, `ALTA`) en `Documentos/PoC/Registro-Defectos-Agente-1.md` línea 42. Reformular las cinco ocurrencias para exigir doble aprobación por rol, o declarar explícitamente el modelo objetivo y su brecha. |
| H-02 | Portada | 112 (con `\companeroNombre` de `Documentos/Comun/definiciones.tex`) | "Compañero de proyecto: **Goñe, Juan Ignacio** (jgone@fie.undef.edu.ar)" — el autor figura como su propio compañero. | `INCONSISTENTE` | `definiciones.tex` fue escrito desde la perspectiva del documento de Becerra (`\companeroNombre` = Goñe). El `.tex` sobrescribe `\autorNombre`/`\autorEmail` (líneas 79–80) pero no `\companeroNombre`/`\companeroEmail`. Verificado en el PDF compilado: "Compañero de proyecto: Goñe, Juan Ignacio". Agregar `\renewcommand{\companeroNombre}{Becerra Mas Roca, Ignacio}` y `\renewcommand{\companeroEmail}{ibecerra@fie.undef.edu.ar}` en el bloque de overrides (líneas 78–83). |
| H-03 | §1 Resumen | 136 | "tecnologías de **código abierto** (Ollama, LangGraph, FastAPI, **Google Workspace** y `deepagents`…)" | `INCONSISTENTE` | Google Workspace no es código abierto (la propia Tabla `tab:plataforma` lo clasifica como "Institucional"). Además, LangGraph/FastAPI se nombran en el Resumen sin la salvedad de diferimiento que §13 sí explicita (línea 623). Sacar Google Workspace de la enumeración de código abierto y/o remitir a la nota de diferimiento. |
| H-04 | §1 Resumen | 134 | "en el Semestre 1 se implementan las funcionalidades de mayor prioridad … **alcanzando TRL 3**" | `DESACTUALIZADO` | Es lenguaje de plan, pero S1 ya transcurrió y el propio documento declara en §18 (línea 1172) que "el hito H5 no está cerrado y el TRL 3 permanece pendiente". El `manifest-corte-2026-09-08.json` lista `TRL 3` y `Gate G2` en `no_acredita`. Sugerir reformular como objetivo condicionado a decisión de gate, o remitir a la nota de estado. |
| H-05 | §18.2 nota de estado | 1168–1176 | "Al corte del **8 de septiembre de 2026**, el estado verificable…" — lista HU-010, HU-011 y HU-012 como demostradas; **omite HU-013**. | `DESACTUALIZADO` | El corte 2026-09-08 está respaldado (`evidencias/manifest-corte-2026-09-08.json`, commit `32a79d9`, 588 pruebas), pero HU-013 se mergeó el 2026-09-09 (`3cf7cfb`, `a42a5ef`, `d8c4a6d`, `fded6e6`, `8824b5e`, issues #19–#26): `src/agente1/interpretacion.py` con clasificación determinística contra catálogo cerrado, resolución difusa de actividad, repregunta con candidatas (`RegistroPendientes` sin durabilidad, vencimiento 15 min) y fallback con LLM local validado y fail-closed (ADR 0001). La suite vigente es de 749 pruebas verdes. Actualizar el corte (p. ej. al 2026-09-09/21) incorporando HU-013 como slice offline, o agregar una línea que la registre como mergeada post-corte. |
| H-06 | §7 justificación | 290 | "Los modelos de lenguaje de **7–8B parámetros** generan contenido de calidad suficiente" | `DESACTUALIZADO` | La cifra refleja la sugerencia de la bible ("LLaMA 3 (8B) o Mistral (7B)", `Procesos y Agentes.md` línea ~1755), pero la evidencia real se obtuvo con `llama3.2:3b` (3B) en CPU (`evidencias/benchmark-hu010-2026-07-17.md`, `benchmark-capacidad-a1-2026-08-26.md`). Ajustar a "~3B verificado en benchmark" o mencionar ambos rangos explícitamente, porque hoy la afirmación atribuye a 7–8B una evidencia producida por 3B. |
| H-07 | §3 glosario / §6.3 / §13 / §14.1 / §14.2 / BMC | 136, 197, 270, 607, 633, 650, 692 | `deepagents` aparece como componente del stack **sin marca de diferido** y en §14.1 "se incorpora como entorno auxiliar de desarrollo" (presente). | `SIN_FUENTE` | No hay evidencia de uso de `deepagents` en el repo: `pyproject.toml` declara `dependencies = []` y no existe mención en código, scripts ni documentación técnica fuera del propio `.tex`/`referencias.bib`. Opciones: marcarlo como diferido/previsto igual que FastAPI-LangGraph-Celery-Redis, o quitarlo del stack hasta que exista uso verificable. |
| H-08 | §8 OE4 / §9.2.1 / §17.2 / §17.3 / §18.1 / §18.4 | 322, 355, 968, 996, 1137, 1232 | HU-013 se describe como "iniciada por correo electrónico con invitación a chat". | `PENDIENTE_EXTERNO` | La lectura tiene base en la bible ("la comunicación … deberá ser mediante un email que dispara el agente al humano quien recibe una invitación a chatear", `Procesos y Agentes.md` línea 695), pero convive con otras dos definiciones del mismo documento: el DoD de HU-013 pide "interfaz simple (prompt en Sheet o Doc)" (línea 3607) y el bloque de DSI2 describe una interfaz web con login. Es exactamente la pregunta 2.1 de la `Nota-Consulta-Direccion-Gate-G2-y-Contradicciones-Agente-1.md` (enviada 2026-09-09, **respuesta pendiente**). Sugerir aclarar "canal adoptado sujeto a confirmación de Dirección". |
| H-09 | §9.2.4 / §17.3 | 398, 999 | HU-015 se excluye como "ceremonial y protocolo, Agente 3". | `PENDIENTE_EXTERNO` | La bible contiene **dos** definiciones de HU-015: "Gestión de Ceremonial y Protocolo" (Agregado, línea 3871, Agente 3) **y** "Generación de Certificados y Triggers por Eventos" (P3/P5/P6, línea 3624) que asigna comportamiento proactivo al propio Agente 1 (reforzado por la nota de línea 1748). La exclusión adopta la segunda numeración sin señalar la ambigüedad; si rige la primera, HU-015 solapa con HU-014 dentro del alcance de A1. Marcar la discrepancia y elevarla (no figura en la nota del 9/9). |
| H-10 | §4 Introducción | 208 | "la SEU … gestiona actualmente **nueve procesos sustantivos**" | `INCONSISTENTE` (leve) | La bible define 9 procesos pero los categoriza en Estratégicos (P1–P2), **Sustantivos** (P3–P6) y de Soporte (P7–P9) (`Procesos y Agentes.md` líneas 40–56). Solo cuatro son sustantivos. Reformular: "nueve procesos (estratégicos, sustantivos y de soporte)". |
| H-11 | §5 Tabla causa-efecto | 239 (fila 1) | "Tiempo excesivo por pieza (**> 30 minutos en promedio**)" | `SIN_FUENTE` | No se encontró respaldo del dato en la bible ni en `Documentos/PoC/` ni en `evidencias/`. La bible solo fija el objetivo de generación < 30 s (línea 1749). O citar la fuente de la medición/relevamiento, o reformular sin cuantificación ("tiempo excesivo por pieza") hasta medir la línea base (M3 la prevé). |
| H-12 | §17.5 storyboard / §17.6 figura | 908, 1035–1037, 1077–1098 | El storyboard y la figura de arquitectura presentan FastAPI, LangGraph, Celery+Redis y PostgreSQL como componentes del flujo, **sin marca de diferimiento**. | `CONSISTENTE` con salvedad | §13 aclara el diferimiento (línea 623), por lo que el documento no afirma que estén implementados; pero las figuras y el paso a paso ("backend del Agente 1 (FastAPI)", "ejecuta un grafo LangGraph") se leen como arquitectura vigente. Sugerir rotular los componentes diferidos en la figura/caption o agregar "(diferido)" en el storyboard. |
| H-13 | §13 tabla plataforma | 604–618 | Licencias: Python "**MIT**", Redis "**BSD**", Cron "**GPL**", Ubuntu Server "**GPL**". | `INCONSISTENTE` (leve) | Python es PSF License; Redis cambió de licencia en 2024 (RSALv2/SSPLv1; AGPLv3 como opción desde Redis 8); cron y Ubuntu aglutinan licencias heterogéneas. Precisión menor pero corregible. |
| H-14 | §13 tabla plataforma | 611 | "Tareas iniciales (S1): **Cron (scheduler nativo)**" | `SIN_FUENTE` | No hay evidencia de uso de cron en `Implementacion/Agente1/` (la ejecución es por CLI/`__main__.py` y scripts manuales). La nota de diferimiento (línea 623) no lo menciona. Marcar como previsto/no usado o retirarlo. |
| H-15 | §17.2 tabla HU | 967 | DoD de HU-012: trigger, confirmación pendiente, envío tras aprobación, registro de envío. | `INCONSISTENTE` (leve, omisión) | El DoD de la bible incluye además "**Confirmación de recepción**" (`Procesos y Agentes.md` línea 3589). Evaluar si se incorpora o se justifica su omisión. |
| H-16 | §15.1 | 772 | "Los registros se almacenan en **PostgreSQL (S2) o en Google Sheets (S1)**" | `DESACTUALIZADO` (leve) | La persistencia vigente es en **archivos** (JSONL con `flock`, `src/agente1/confirmaciones.py`, `persistencia.py`); PostgreSQL fue solo spike de migraciones sobre instancia efímera y Sheets es el bus previsto, no el store implementado. Alinear con la propia nota de línea 623. |
| H-17 | §17.5 storyboard | 1037 | "El proceso **tarda menos de 30 segundos**" | `CONSISTENTE` con salvedad | Es el objetivo M1 (< 30 s, bible línea 1749). La evidencia de benchmark muestra timeouts a ~30 s con prompt cold y ~20 s warm (`benchmark-hu010-2026-07-17.md`): la afirmación es narrativa de storyboard, no medida. Opcional: matizar "objetivo < 30 s". |
| H-18 | §18.2 | 1171–1176 | Bloqueantes "institucionales y no de software"; H5 no cerrado; TRL 3 pendiente; evidencia sin validación SEU ni Workspace live. | `CONSISTENTE` | Correcto y verificable contra `manifest-corte-2026-09-08.json` (`no_acredita`: validación SEU, revisión humana, Workspace live, Gate G2, TRL 3), `Indice-Evidencias-Agente-1.md` y `Registro-Defectos-Agente-1.md`. |
| H-19 | §17.4 | 1026 | Seam Historia Viva: "contrato de interfaz **todavía no está cerrado**; lo aquí descripto es la posición del Agente 1, no un acuerdo firmado". | `CONSISTENTE` | Coincide con `historia_viva.py` (puerto offline, `CANDIDATO_NO_INSTITUCIONAL`, "depende del contrato con Ignacio (issue #17)"), con `respuesta-nacho.md` (posición unilateral, 2026-08-31) y con `Paquete-Cierre-Contrato-Historia-Viva-A1-Issue-17.md`. La dirección del intercambio (A1 consulta, A2 no empuja ni redacta) también coincide con el código. |
| H-20 | §13 nota | 623 | "FastAPI, LangGraph, Celery y Redis **quedaron diferidos por decisión documentada**"; PostgreSQL solo spike efímero; persistencia vigente en archivos; Apps Script previsto para S2. | `CONSISTENTE` | Respaldado por `Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`, `spike-persistencia-postgresql-2026-08-17.md`, `validacion-migraciones-postgresql-0003-2026-08-26.md` y `pyproject.toml` (`dependencies = []`). La obligatoriedad de FastAPI/Celery está consultada a Dirección (punto 3 de la nota del 9/9) — respuesta pendiente, no presentada como resuelta. |
| H-21 | §9.2.1 / §17.2 | 352–356, 965–969 | HU-010 (P0, 8 SP), HU-011 (P0, 5 SP), HU-012 (P1, 5 SP), HU-013 (P1, 3 SP), HU-014 (P2, 8 SP); total 29 SP; S1 = HU-010+011, S2 = resto. | `CONSISTENTE` | Idéntico a `Procesos y Agentes.md` líneas 3550–3622 y priorización E2 S1/S2 (líneas 3884–3896). |
| H-22 | §9.2.1 / §18 (HU-013 y transcript) | 355, 968, 996, 1137, 1232 | HU-013 figura en alcance y cronograma (C4, H7, Oct 2026) como "email de inicio, invitación a chat, registro en Sheets"; evidencia: "**captura de interacción**". | `CONSISTENTE` | El documento **no** propone persistir transcripts; "captura de interacción" coincide con la evidencia que la propia bible asigna a HU-013 (línea 4445). Además, la implementación explicita que la `InteraccionPendiente` "nunca [conserva] la prosa del pedido que la originó" (`interpretacion.py`, docstring). Sin observación sobre datos personales. |
| H-23 | §16.2 interesados | 847–854 | Cicerchia (Director), Vegega y Britez (primarios), Maceira García Coni (secundario), Tozzi y Calvache (apoyo), Vera Batista (infraestructura), SEU (PO funcional). | `CONSISTENTE` | Todos los nombres y roles verificados en `Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md` líneas 21–24, 47–49, 100. |
| H-24 | §15.2 / §19 | 784, 1278 | Disponibilidad objetivo 99% presentada como "criterio de aceptación **pendiente de medición**; no constituye un resultado demostrado". | `CONSISTENTE` | El 99% existe en la bible (línea 2049) y el documento lo hedgea correctamente. Buen manejo; mismo criterio en M13. |
| H-25 | §9.2.3 | 386–387 | HU-001 y HU-002 como prerequisitos globales compartidos con el proyecto de Becerra Mas Roca. | `CONSISTENTE` | E1 (HU-001 Drive/Sheets, HU-002 Apps Script) es la plataforma base en la bible (líneas 3499–3526); la dependencia "HU-001 → base de datos / HU-002 → todas las automatizaciones" figura en líneas ~3900. |
| H-26 | §1 / §9 / §17 | 132, 214, 354, 401, 683 | Agente 1 = comunicación institucional con validación humana; no orquestador, no chatbot público, no analítica, no scraping; única salida automática a destinatario final = HU-012 post-aprobación; resto borradores con publicación manual por la SEU. | `CONSISTENTE` | Coincide con el rol P4 de la bible (líneas 1707–1736), con el código (`procesamiento.py`: éxito = `PENDIENTE_VALIDACION`; `confirmaciones.py` sin adapter de correo productivo) y con los límites del workspace. |
| H-27 | §14.2 | 637–663 | Costos 0–1.400 USD (software libre + contingencias opcionales). | `CONSISTENTE` | Estimación interna del documento, aritméticamente consistente (0–180 + 0–120 + 0–600 + 0–500 = máx. 1.400). No contradice fuentes. |
| H-28 | §18 hitos/entregables | 1155, 1189–1199, 1222–1238 | Fechas de hitos (H1–H11) y planificación mensual. | `CONSISTENTE` con salvedad | La nota de línea 1168 ya aclara que son "objetivos de planificación, no compromisos confirmados por la SEU ni por la cátedra". H3 (firma SEU 15 Jul) y H4 (MVP 31 Jul) vencieron sin cumplirse — quedan cubiertos por la misma nota. Ninguna fecha vencida se presenta como cumplida. |

---

## 3. Cambios propuestos, ordenados por severidad

### Altos

1. **H-02 — Portada: compañero = el propio autor.** Línea 112 del `.tex` (`\companeroNombre\ (\companeroEmail)`) resuelve a "Goñe, Juan Ignacio" porque `Documentos/Comun/definiciones.tex` está escrito para el documento de Becerra y el bloque de overrides (líneas 78–83) no redefine el compañero. El PDF compilado lo confirma textualmente. *Fuente:* `definiciones.tex` y PDF renderizado. *Corrección:* agregar `\renewcommand{\companeroNombre}{Becerra Mas Roca, Ignacio}` y `\renewcommand{\companeroEmail}{ibecerra@fie.undef.edu.ar}` junto a los overrides existentes.

2. **H-01 — HU-012 con aprobación única.** Líneas 321, 354, 967, 995, 1136 (y el flujo del storyboard, línea 1043) describen una sola "aprobación humana registrada". *Fuente:* `Contenido/bible/Procesos y Agentes.md`, Bloque 2 "Human in the Loop", CU10 (líneas 2182–2185) y CP18/CP19 (líneas 2397–2409): se requieren **ambas** aprobaciones (semántica RGC + utilitaria Coordinador de Extensión). El estado actual del código reproduce el defecto (`DEF-A1-016`, `ABIERTO`, `ALTA`, `Registro-Defectos-Agente-1.md` línea 42). *Corrección:* describir la doble aprobación independiente como diseño objetivo en las cinco ocurrencias, o declarar la brecha explícitamente (el anteproyecto hoy documenta la máquina de estados defectuosa como si fuera la correcta).

3. **H-03 — Resumen: "código abierto (… Google Workspace …)".** Línea 136: Google Workspace no es código abierto, y LangGraph/FastAPI se enumeran sin la salvedad de diferimiento de §13. *Fuente:* la propia Tabla `tab:plataforma` (línea 613, licencia "Institucional") y `Plan-Recuperacion-MVP-Agente-1-2026-08-17.md`. *Corrección:* excluir Google Workspace de la lista de open-source y/o agregar "(componentes diferidos, ver §13)".

### Medios

4. **H-05 — Nota de estado verificado desactualizada respecto de HU-013.** Líneas 1168–1176: el corte 2026-09-08 omite que HU-013 está mergeada desde el 2026-09-09 (749 pruebas verdes; clasificación determinística, resolución difusa, repregunta con candidatas sin durabilidad, fallback LLM fail-closed). *Fuente:* `git log` (commits `3cf7cfb`–`8824b5e`), `src/agente1/interpretacion.py`, `Registro-Defectos-Agente-1.md` ("regresión vigente al 2026-09-09 … 749 pruebas verdes"). *Corrección:* actualizar el corte o agregar HU-013 como incremento posterior con su naturaleza offline y sus límites (sin canal productivo, `RegistroPendientes` volátil, ADR 0001).

5. **H-07 — `deepagents` sin evidencia de uso.** Líneas 136, 197, 270, 607, 633, 650, 692 lo presentan como componente del stack ("se incorpora", §14.1) sin marca de diferido; no existe en `pyproject.toml` (`dependencies = []`) ni en código/scripts/docs técnicos. *Corrección:* marcarlo como previsto/diferido o retirarlo del stack hasta tener uso verificable.

6. **H-08 — Canal de HU-013 bajo consulta.** Líneas 322, 355, 968, 996, 1137, 1232 adoptan "email con invitación a chat" (bible línea 695) mientras el DoD de la propia HU pide "prompt en Sheet o Doc" (línea 3607) y el bloque DSI2 describe interfaz web: es la pregunta 2.1 de la nota a Dirección del 2026-09-09, **sin respuesta**. *Corrección:* señalar la lectura como adoptada y pendiente de confirmación.

7. **H-04 — Resumen anuncia "alcanzando TRL 3" como derrotero.** Línea 134: S1 ya cerró y TRL 3 está pendiente de decisión de gate (línea 1172 del propio documento; `manifest-corte-2026-09-08.json`). *Corrección:* reformular como objetivo condicionado al gate, evitando lectura de logro.

8. **H-06 — "7–8B parámetros" no es el modelo verificado.** Línea 290: la evidencia real es `llama3.2:3b` en CPU; 7–8B es la sugerencia de la bible, no la configuración probada. *Fuente:* `evidencias/benchmark-hu010-2026-07-17.md`, `benchmark-capacidad-a1-2026-08-26.md`. *Corrección:* declarar el modelo efectivamente verificado.

9. **H-09 — HU-015 con doble definición en la bible.** Líneas 398 y 999 la excluyen como "ceremonial, Agente 3", pero la bible también la define como "Generación de Certificados y Triggers por Eventos" asignada al Agente 1 (líneas 3624, 1748). *Corrección:* explicitar la ambigüedad y elevarla junto con las consultas pendientes.

### Bajos

10. **H-10 — "nueve procesos sustantivos".** Línea 208: la bible reserva "sustantivos" para P3–P6. *Corrección:* "nueve procesos (estratégicos, sustantivos y de soporte)".

11. **H-11 — "> 30 minutos en promedio" por pieza.** Línea 239, fila 1 de la tabla causa-efecto: sin fuente trazable. *Corrección:* citar la medición o quitar la cuantificación hasta tener línea base (M3).

12. **H-13 — Licencias imprecisas.** Línea 604: Python figura "MIT" (es PSF); línea 610: Redis "BSD" (RSALv2/SSPLv1 o AGPLv3 según versión); líneas 611/618: Cron y Ubuntu "GPL" son simplificaciones.

13. **H-16 — Logs "en PostgreSQL (S2) o Google Sheets (S1)".** Línea 772: la persistencia vigente es en archivos. *Corrección:* alinear con la nota de §13.

14. **H-14 — "Cron (scheduler nativo)" como componente S1.** Línea 611: sin evidencia de uso; la ejecución actual es por CLI/scripts. Marcar como previsto o quitar.

15. **H-15 — DoD de HU-012 omite "confirmación de recepción".** Línea 967 vs. bible línea 3589. Incorporar o justificar.

16. **H-12 — Figuras/storyboard sin marca de diferido.** Líneas 908, 1035–1037, 1077–1098: rotular FastAPI/LangGraph/Celery/Redis/PostgreSQL como "diferidos" para que la lectura visual no contradiga §13.

17. **H-17 — "tarda menos de 30 segundos" afirmado en storyboard.** Línea 1037: es el objetivo M1; benchmarks muestran timeouts a ~30 s en cold. Matizar como objetivo.

### Observaciones sin costo de corrección inmediata

- **Fortaleza evidenciable no citada:** la nota de estado (líneas 1168–1176) no menciona el tamaño de la suite (588 en el corte citado; 749 hoy) ni el hash de la regresión. Sumar el dato fortalece la trazabilidad del propio documento.
- **Issue #27 (decisión ADR 0001):** ticket abierto sobre la tensión entre la interpretación determinística y el fallback con LLM (commit `4ec19e6`). El anteproyecto no lo menciona; no es exigible en el formato, pero queda registrado como decisión pendiente.
- **PDF compilado desactualizado:** `Anteproyecto-PPS-Juan-Ignacio-Gone.pdf` muestra fecha del 22-06-2026; recompilar tras las correcciones.

---

## 4. Respuestas a las preguntas explícitas de la auditoría

- **¿FastAPI/LangGraph/Celery/Redis como implementados o planificados?** Como **planificados/diferidos**: §13 (línea 623) declara el diferimiento por decisión documentada y el stack real en uso. Salvedades: el Resumen (línea 136) los nombra sin la salvedad; las figuras y el storyboard (líneas 908, 1035–1037, 1077–1098) los dibujan sin marca de diferido; `deepagents` figura en la tabla sin diferimiento y sin evidencia de uso.
- **¿Afirma TRL o validación SEU no acreditados?** **No.** Al contrario: líneas 1168–1176 declaran TRL 3 pendiente, H5 no cerrado, validación SEU no demostrada. La única tensión es el Resumen (línea 134), que narra el plan sin la salvedad.
- **¿HU-012 con aprobación única o doble?** **Única** ("una aprobación humana registrada", líneas 321, 354, 967, 995, 1136, 1043). Coincide con la implementación defectuosa vigente y contradice la bible (CU10: doble aprobación semántica + utilitaria). `DEF-A1-016` abierto.
- **¿Historia Viva como integración cerrada o contrato en negociación?** **Contrato no cerrado**, correctamente declarado (línea 1026: "posición del Agente 1, no un acuerdo firmado"). Consistente con `historia_viva.py` (puerto offline, `CANDIDATO_NO_INSTITUCIONAL`) e issue #17 abierto.
- **¿El cronograma menciona HU-013? ¿Y "persistir transcript"?** Sí la menciona (líneas 1137, 1195, 1232) en términos consistentes con la spec. **No** propone persistir transcript: la evidencia prevista es "captura de interacción" (línea 996), alineada con la bible (línea 4445) y con la implementación (la `InteraccionPendiente` nunca conserva la prosa).
- **¿Fechas como compromiso o como plan?** Como **objetivos de planificación**, con disclaimers explícitos (línea 1168). Ninguna fecha vencida se presenta como cumplida.
- **¿Stack/pruebas/evidencia coinciden con el estado real?** Parcialmente: la nota de estado es verificable pero quedó un día corta respecto del merge de HU-013; el documento no cita el tamaño de la suite (749 hoy); el stack declarado incluye componentes sin evidencia de uso (`deepagents`, cron) y el modelo verificado (3B) no es el citado (7–8B).

---

## 5. Pendientes de respuesta externa (estado al 2026-09-21)

Ninguno está presentado como resuelto en el `.tex`; se listan para seguimiento, sin inventar estado:

1. **Issue #14 — Gestión SEU** (revisión editorial, plantilla institucional, criterios por canal, orígenes de inscripción): reconocido en la nota de línea 1176 y en `DEF-A1-005`/`DEF-A1-015` (`BLOQUEADO_EXTERNO`). SEU designó revisor (A/c Juan Manuel Gonzalez Chipont; suplente VS "ec" Tomás de Vergara) pero acta, puntajes y decisión siguen `PENDIENTE`.
2. **Issue #15 — DSI** (identidad, permisos y provisión Google Workspace): reconocido genéricamente como "identidad y permisos de infraestructura" (línea 1176). `Paquete-Gestion-DSI-Issue-15.md` preparado; provisión pendiente.
3. **Issue #16 — Gate G2 / TRL 3:** nota de consulta enviada a César Cicerchia el 2026-09-09 (`Nota-Consulta-Direccion-Gate-G2-y-Contradicciones-Agente-1.md`); **respuesta pendiente**. El documento declara el gate abierto — correcto.
4. **Issue #17 — Contrato Historia Viva (A1↔A2):** declarado no cerrado (línea 1026). `respuesta-nacho.md` es posición unilateral; `Paquete-Cierre-Contrato-Historia-Viva-A1-Issue-17.md` registra los cambios solicitados. Pendiente de acuerdo.
5. **Issue #27 — Decisión ADR 0001:** tensión entre interpretación determinística y fallback con LLM elevada como ticket; sin resolución. No mencionado en el `.tex` (no exigible, registrado aquí para completitud).
6. **Canal de HU-013** (pregunta 2.1 de la nota del 9/9) y **obligatoriedad de FastAPI/Celery** (pregunta 3): pendientes; el `.tex` adopta una lectura sin señalar la consulta (ver H-08).
7. **Doble definición de HU-015** en la bible (ceremonial/A3 vs. certificados+triggers/A1): pendiente de aclaración institucional; no está entre las preguntas de la nota del 9/9 (ver H-09).

---

*Auditoría documental sin modificación del entregable. Toda afirmación no rastreable a fuente institucional o evidencia del repo quedó marcada `SIN_FUENTE` o `PENDIENTE_EXTERNO`.*

---

## 6. Addendum: correcciones aplicadas el 2026-09-21

Tras la auditoría se corrigió la fuente `.tex` en el mismo día. Estado resultante por hallazgo:

| ID | Resultado |
|---|---|
| H-01 | **Aplicado.** Además el código quedó corregido: `DEF-A1-016` cerrado como `RESUELTO_TECNICO` (issue #28, commit `976c1f3`). El `.tex` ahora describe la doble aprobación en OE3, alcance HU-012, tabla de HU, trazabilidad, EDT y exclusiones; el paso 6 del storyboard registra ambas aprobaciones por rol. |
| H-02 | **Aplicado.** Overrides de `\companeroNombre`/`\companeroEmail` a Becerra Mas Roca en las líneas 81–82. |
| H-03 | **Aplicado.** El resumen ya no llama código abierto a Google Workspace y remite a §13 para los componentes diferidos o previstos. |
| H-04 | **Aplicado.** TRL 3 y TRL 4 quedan como objetivos condicionados a la decisión del gate. |
| H-05 | **Aplicado.** La nota de estado pasa al corte 2026-09-21: incorpora HU-013 como slice offline, la doble aprobación de HU-012 verificada en regresión y la suite de 757 pruebas verdes; agrega la prueba guiada de usabilidad con SEU a los no demostrados. |
| H-06 | **Aplicado.** §7 declara la sugerencia de 7–8B de la bibliografía y la evidencia efectiva con `llama3.2:3b` en CPU. |
| H-07 | **Aplicado.** `deepagents` queda marcado como previsto y sin uso efectivo en glosario, antecedentes, §9.1, tabla de plataforma, nota de §13, §14.1, tabla de costos y BMC. |
| H-08 | **Aplicado.** El canal de HU-013 queda señalado como adoptado y pendiente de confirmación por Dirección en OE4, alcance, tabla de HU, trazabilidad y EDT. |
| H-09 | **Aplicado.** La exclusión de HU-015 explicita la doble definición de la bible y su elevación pendiente. |
| H-10 | **Aplicado.** "nueve procesos (estratégicos, sustantivos y de soporte)". |
| H-11 | **Aplicado.** Se retiró la cuantificación "> 30 minutos"; el efecto queda pendiente de medición de línea base. |
| H-12 | **Aplicado.** Storyboard y figura rotulan FastAPI, LangGraph, Celery, Redis y PostgreSQL como diferidos. |
| H-13 | **Aplicado.** Python PSF License; Redis RSALv2/SSPLv1 o AGPLv3; Cron según implementación; Ubuntu GPL predominantemente. |
| H-14 | **Aplicado.** Cron marcado como previsto, sin uso al corte. |
| H-15 | **Aplicado.** El DoD de HU-012 incorpora la confirmación de recepción. |
| H-16 | **Aplicado.** §15.1 declara persistencia vigente en archivos; PostgreSQL y Sheets como opciones previstas. |
| H-17 | **Aplicado.** El storyboard lo reformula como objetivo de duración. |

Verificación de compilación: `lualatex` en dos pasadas sobre directorio temporal, sin errores ni referencias indefinidas (41 páginas). **Los artefactos generados en `Documentos/Anteproyecto/` no se regeneraron** (regla del repo): el PDF existente sigue siendo el del 22-06-2026 y debe recompilarse antes de cualquier entrega.

**Pendientes que no se resuelven editando el `.tex`:** las respuestas externas de la sección 5 (issues #14, #15, #16, #17, #27, canal de HU-013, doble definición de HU-015) y la firma/validación formal del documento, que sigue en el issue #10.
