# Instrumento — sesión combinada HU-013: prueba guiada de usabilidad + revisión editorial de lo generado

- **Fecha:** a confirmar con la SEU (la sesión agendada para el 2026-09-25 no
  se concretó; la nueva fecha se registra aquí cuando se cierre)
- **Participante SEU:** Juan Manuel (voluntario registrado en el acta del
  22/09 — `Respuestas-SEU-Reunion-2026-09-22.md` §4)
- **Conduce:** Juan Ignacio Goñe
- **Tarea del cronograma:** `s5d` — *Regresión de solicitudes y prueba guiada
  de usabilidad con SEU* (Sprint 5; el cierre original del 25/09 quedó sin
  sesión)
- **Base técnica:** `evidencias/recorrido-prueba-guiada-canal-planilla.md`
  (issue #24). Canal adapter de planilla offline: `pedidos.csv` →
  `respuestas.csv`, sin credenciales ni red.
- **Issue:** `SpendIce/Proyecto-Final#32` (mapa #30)

## 1. Objetivo y alcance

La sesión combina dos bloques con criterios separados:

- **Bloque A — usabilidad (lo que acredita `s5d`).** Verificar que una
  persona de la SEU puede operar al Agente 1 escribiendo en prosa suelta:
  pedir piezas, responder repreguntas y entender las respuestas (borrador,
  pedido de aclaración o rechazo). Prueba de **interacción**, no editorial.
- **Bloque B — revisión editorial guiada (observaciones, no acredita).**
  El participante revisa los borradores que el propio Bloque A generó,
  contrastándolos con las piezas reales del corpus
  (`Corpus-Comunicaciones-Reales-SEU-2026-09-30.md`). Produce devoluciones
  accionables para calibrar contratos y, de paso, respuestas a las
  preguntas abiertas de ese documento. No es una aprobación institucional:
  todo lo visto está marcado `BORRADOR — NO PUBLICAR`.

Si el tiempo no alcanza para el Bloque B, la revisión editorial vuelve al
plan original: paquete de ejemplos por mail, revisión asincrónica.

**Qué no acredita:** control de acceso (la identidad es afirmada por el canal,
no verificada — ADR 0002, `identidad_verificada: false` en toda la auditoría)
ni validación institucional. La demo live opcional de §3 ilustra el camino
Workspace ya verificado por separado (evidencia
`notas/workspace-live-d2-2026-09-28.md`): no lo re-acredita ni es requisito de
la sesión — la prueba de usabilidad se sostiene completa en modo offline. El
dataset es sintético (`data/actividades_sinteticas.csv`).

## 2. Prerrequisitos de la sesión

- Para evitar la edición alternada de dos CSV, se puede usar el prototipo web
  local descrito en `Implementacion/Agente1/scripts/prototipo_hu013.py`:
  desde `Implementacion/Agente1`, ejecutar
  `PYTHONPATH=src python scripts/prototipo_hu013.py` y abrir
  `http://127.0.0.1:8765`. El modo predeterminado es simulado y determinista;
  permite observar interpretación, estados y borradores de ejemplo, pero no
  mide la calidad de Ollama. Para una corrida con el modelo local:
  `PYTHONPATH=src python scripts/prototipo_hu013.py --modo ollama --modelo llama3.1:8b`.
  El prototipo conserva los pedidos sólo en memoria; la auditoría HU-013 guarda
  hashes y los borradores/logs quedan en el directorio temporal que informa la
  terminal. El feedback de comprensión se puede descargar sin incluir pedidos.
  Es una interfaz experimental para esta sesión, no acredita Workspace ni
  identidad.
- **Si se usa el canal CSV:** carpeta compartida entre quien conduce y el
  participante (local proyectada o sincronizada), con `pedidos.csv`
  inicializado con encabezado `id_pedido,identificador,rol,texto`, y terminal
  en `Implementacion/Agente1` con `scripts/atender_canal_planilla.py` listo.
- **Si se usa el prototipo web:** terminal local con el servidor iniciado y el
  navegador abierto en `http://127.0.0.1:8765`.
- **Si se hace la demo live opcional (§3):** `set -a; source
  ~/.config/agente1/workspace-d2.env; set +a` (env file fuera del repo, chmod
  600), Ollama local levantado con `llama3.2:3b` descargado, y modelo
  pre-calentado — el 28/09 una generación fría bajo carga cortó por el timeout
  de 45s del runner; con host descargado completó en ~19s. La credencial ya es
  durable (refresh token interno del proyecto GCP en el tenant), no hace falta
  re-correr el wizard. Comandos exactos en
  `notas/workspace-live-d2-2026-09-28.md` §Reproducir.
- El participante escribe sus pedidos en sus propias palabras; los casos de la
  sección 3 son guía, no guion obligatorio — si propone pedidos propios, mejor
  evidencia de usabilidad.
- **Para el Bloque B:** tener a mano `Corpus-Comunicaciones-Reales-SEU-2026-09-30.md`
  (o las 7 capturas de `Adjuntos/imagenes-flat-finch/`) para contrastar lo
  generado con las piezas reales durante la misma sesión.
- Roles habilitados provisionales para la fila: `coordinador_seu` o
  `auxiliar_seu`.

## 3. Bloque A — casos guionados

| # | Consigna para el participante | Comportamiento esperado |
|---|---|---|
| C1 | «Necesito avisar de la actividad SYN-001, ¿me armás la gacetilla?» (id explícito) | `PENDIENTE_VALIDACION` + borrador en `borradores/` — el artefacto auditado es el **mail en forma FIE Informa** (asunto, invitación, fecha en formato largo, firma institucional), renderizado determinísticamente desde la ficha validada |
| C2 | «Tenemos que avisar del taller de vinculación» (sin id, prosa suelta) | Resolución difusa sobre el índice de actividades: borrador si hay coincidencia única, si no repregunta con candidatas |
| C3 | Tras una repregunta: responder con la elección en el turno siguiente | La pendiente guarda candidatas (orden, id, título, fecha) **y los parámetros ya resueltos** (p. ej. el canal de un post); el turno siguiente despacha el pedido sin pedir de nuevo lo ya dicho. Resuelven el número/ordinal («la 1», «la primera»), el título («la jornada sintética») y la fecha («2026-08-07», «la del 7 de agosto») — el rasgo con dominancia estricta gana aunque otro token sea compartido («sintética»). En un **post** no hace falta repetir el canal; si la persona lo nombra igual («la 1, para LinkedIn»), lo del turno gana |
| C4 | «Tenemos que avisar la jornada sintética en LinkedIn, ¿me preparás el post?» | `PENDIENTE_VALIDACION` con post del canal LinkedIn |
| C5 | «Generá un post de la jornada sintética» (sin canal) | `INCOMPLETA` — sin default silencioso de canal |
| C6 | «Mandame el newsletter de la semana» u otro pedido fuera del catálogo | Rechazo con `intencion_sin_pipeline` / `fuera_de_alcance`, sin aproximación |
| C7 | Una fila con rol no habilitado (p.ej. `visitante`) | `RECHAZADA` + línea de auditoría con el intento |
| C8 | Pedido redactado de forma que el clasificador determinístico no lo resuelva (opcional) | Fallback con modelo local: sólo extrae términos contra el catálogo, fail-closed; si tampoco resuelve, rechazo limpio |

### Bloque B — revisión editorial guiada de lo generado

Al terminar el Bloque A, el participante ya tiene borradores reales de la
sesión (mail de gacetilla y posts). Quien conduce
los repasa uno por uno contra las piezas reales del corpus, con estas
preguntas fijas por pieza (para que la devolución sea comparable y no una
opinión suelta):

| # | Pregunta | Qué capta |
|---|----------|-----------|
| B1 | ¿Reconocés esta pieza como una comunicación de la FIE? (sí / parcial / no) | Realismo percibido del formato y el tono |
| B2 | ¿Qué le falta para poder mandarla? | Datos o secciones ausentes (hora, lugar, imagen, links…) |
| B3 | ¿Qué le sobra o suena raro? | Elementos artificiales del formato técnico (`## TÍTULO`, líneas `Fecha:` en posts, etc.) |
| B4 | ¿La marca «BORRADOR — NO PUBLICAR» se entiende y alcanza? | Comprensión del ciclo de validación humana |

Y las preguntas abiertas ya registradas en el corpus §4 — la sesión es la
primera oportunidad de tenerlas respondidas por la SEU:

- ¿Hashtags temáticos libres (`#radio`, `#vozpropia`…) o set cerrado?
- ¿El CTA puede decir «inscripción»? (hoy está prohibida en campos creativos)
- ¿Los datos van dentro de la prosa del post o en líneas aparte como hoy?
- ¿El eslogan literal «¡Si es ingeniería, es en la FIE!» es válido? (la
  variante «…la FIE te espera!» se adoptó porque el literal choca con el
  gate de lugares)
- ¿La firma institucional completa del borrador mail es la correcta?

Las respuestas se anotan parafraseadas y alimentan `Registro-Defectos-Agente-1.md`
(observaciones) o los contratos (decisiones de calibración), según aplique.

### Demo live opcional — la conduce quien presenta, no es caso del participante

Si la sesión se presta, se puede cerrar mostrando el camino real ya verificado
el 28/09: `workspace_e2e.py --live --confirm-write-workspace --tipo gacetilla
--id-solicitud SYN-001` lee la fila de la planilla institucional y deja el
borrador como Doc `BORRADOR — NO PUBLICAR — SYN-001` en la carpeta Drive
autorizada. Sirve para que el participante vea el artefacto real en el lugar
donde la SEU trabajaría; no cambia lo que acredita `s5d` ni sustituye las
decisiones formales del issue #15. Si la demo falla (revocación, red, timeout
de generación), se registra como observación y se sigue: la prueba de
usabilidad no depende de ella.

## 4. Qué se registra y qué no

Por cada caso del **Bloque A**, en una tabla de registro de la sesión:

- **Estado observado** vs esperado (`PENDIENTE_VALIDACION`, `INCOMPLETA`,
  `RECHAZADA`, repregunta).
- **Si el participante entendió la respuesta** sin ayuda (sí/no + observación
  parafraseada).
- **Tiempo percibido** y cualquier confusión o fricción.
- **Devoluciones del participante** en forma parafraseada.

Del **Bloque B**, por pieza revisada:

- Respuesta a B1–B4 (sí/parcial/no + observación parafraseada).
- Respuestas a las preguntas abiertas del corpus, parafraseadas, con la
  pieza o sección a la que refieren.

Nunca se registra la prosa literal del pedido: la especificación de HU-013
prohíbe conservar lo que escribe la persona, y la evidencia respeta la misma
regla — la auditoría del sistema sólo guarda `mensaje_hash`.

Al cierre: volcar la tabla en un acta recuperable (mismo criterio que la
reunión del 22/09 — el acta registrada con el referente cuenta como evidencia
escrita), exportable a `reunion-hu013-<fecha-sesion>.json` si el instrumento
es digital o a Markdown consolidado si es en papel.

## 5. Criterio de éxito de s5d

`s5d` queda acreditable si:

- El participante completó al menos C1–C6 del Bloque A (C7–C8 deseables).
- Cada desviación del comportamiento esperado quedó registrada como defecto
  nuevo en `Registro-Defectos-Agente-1.md` o como observación de usabilidad.
- El acta quedó recuperable en `Documentos/PoC/Validacion-SEU/`.

El Bloque B no forma parte del criterio de `s5d`: sus devoluciones son
insumo de calibración (catálogo, contratos, preguntas para la SEU) y quedan
registradas como observaciones. Si el Bloque B no se realiza, la revisión
editorial pasa al paquete de ejemplos por mail sin afectar `s5d`.

Si la sesión no se realiza o se corta, `s5d` sigue sin marcar: protocolo
escrito no cuenta como prueba hecha.
