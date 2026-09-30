# Instrumento — prueba guiada de usabilidad HU-013 (canal de lenguaje natural)

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

Verificar que una persona de la SEU puede operar al Agente 1 escribiendo en
prosa suelta en una planilla: pedir piezas, responder repreguntas y entender
las respuestas (borrador, pedido de aclaración o rechazo). Es una prueba de
**usabilidad e interacción**, no de calidad editorial de los borradores — eso
lo cubre la revisión asincrónica del paquete.

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
- Roles habilitados provisionales para la fila: `coordinador_seu` o
  `auxiliar_seu`.

## 3. Casos guionados

| # | Consigna para el participante | Comportamiento esperado |
|---|---|---|
| C1 | «Necesito avisar de la actividad SYN-001, ¿me armás la gacetilla?» (id explícito) | `PENDIENTE_VALIDACION` + borrador en `borradores/` (en el prototipo web se muestra también como *vista mail ilustrativa* con firma institucional; el artefacto auditado es la ficha) |
| C2 | «Tenemos que avisar del taller de vinculación» (sin id, prosa suelta) | Resolución difusa sobre el índice de actividades: borrador si hay coincidencia única, si no repregunta con candidatas |
| C3 | Tras una repregunta: responder con la elección en el turno siguiente | La pendiente guarda candidatas (orden, id, título, fecha) y el turno siguiente despacha el pedido. **Nota de ensayo (30/09):** responder con número u ordinal («la 1», «la primera») funciona; responder con el título completo puede no resolver si comparte un token con otras candidatas (en el dataset todas son «…sintética…») — conviene que la respuesta use un rasgo distintivo. Y si el pedido era un **post**, la respuesta debe repetir el canal («la 1, para LinkedIn»): la pendiente no conserva los parámetros ya resueltos — defecto candidato registrado en `Corpus-Comunicaciones-Reales-SEU-2026-09-30.md` §3 |
| C4 | «Tenemos que avisar la jornada sintética en LinkedIn, ¿me preparás el post?» | `PENDIENTE_VALIDACION` con post del canal LinkedIn |
| C5 | «Generá un post de la jornada sintética» (sin canal) | `INCOMPLETA` — sin default silencioso de canal |
| C6 | «Mandame el newsletter de la semana» u otro pedido fuera del catálogo | Rechazo con `intencion_sin_pipeline` / `fuera_de_alcance`, sin aproximación |
| C7 | Una fila con rol no habilitado (p.ej. `visitante`) | `RECHAZADA` + línea de auditoría con el intento |
| C8 | Pedido redactado de forma que el clasificador determinístico no lo resuelva (opcional) | Fallback con modelo local: sólo extrae términos contra el catálogo, fail-closed; si tampoco resuelve, rechazo limpio |

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

Por cada caso, en una tabla de registro de la sesión:

- **Estado observado** vs esperado (`PENDIENTE_VALIDACION`, `INCOMPLETA`,
  `RECHAZADA`, repregunta).
- **Si el participante entendió la respuesta** sin ayuda (sí/no + observación
  parafraseada).
- **Tiempo percibido** y cualquier confusión o fricción.
- **Devoluciones del participante** en forma parafraseada.

Nunca se registra la prosa literal del pedido: la especificación de HU-013
prohíbe conservar lo que escribe la persona, y la evidencia respeta la misma
regla — la auditoría del sistema sólo guarda `mensaje_hash`.

Al cierre: volcar la tabla en un acta recuperable (mismo criterio que la
reunión del 22/09 — el acta registrada con el referente cuenta como evidencia
escrita), exportable a `reunion-hu013-<fecha-sesion>.json` si el instrumento
es digital o a Markdown consolidado si es en papel.

## 5. Criterio de éxito de s5d

`s5d` queda acreditable si:

- El participante completó al menos C1–C6 (C7–C8 deseables).
- Cada desviación del comportamiento esperado quedó registrada como defecto
  nuevo en `Registro-Defectos-Agente-1.md` o como observación de usabilidad.
- El acta quedó recuperable en `Documentos/PoC/Validacion-SEU/`.

Si la sesión no se realiza o se corta, `s5d` sigue sin marcar: protocolo
escrito no cuenta como prueba hecha.
