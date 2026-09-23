# Instrumento — prueba guiada de usabilidad HU-013 (canal de lenguaje natural)

- **Fecha:** 2026-09-25 (confirmada el 22/09)
- **Participante SEU:** Juan Manuel (voluntario registrado en el acta del
  22/09 — `Respuestas-SEU-Reunion-2026-09-22.md` §4)
- **Conduce:** Juan Ignacio Goñe
- **Tarea del cronograma:** `s5d` — *Regresión de solicitudes y prueba guiada
  de usabilidad con SEU* (Sprint 5, cierra 25/09)
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
no verificada — ADR 0002, `identidad_verificada: false` en toda la auditoría),
Workspace live, ni validación institucional. El dataset es sintético
(`data/actividades_sinteticas.csv`).

## 2. Prerrequisitos de la sesión

- Carpeta compartida entre quien conduce y el participante (local proyectada
  o sincronizada), con `pedidos.csv` inicializado con encabezado
  `id_pedido,identificador,rol,texto`.
- Terminal en `Implementacion/Agente1` con el script
  `scripts/atender_canal_planilla.py` listo para correr.
- El participante escribe sus pedidos en sus propias palabras; los casos de la
  sección 3 son guía, no guion obligatorio — si propone pedidos propios, mejor
  evidencia de usabilidad.
- Roles habilitados provisionales para la fila: `coordinador_seu` o
  `auxiliar_seu`.

## 3. Casos guionados

| # | Consigna para el participante | Comportamiento esperado |
|---|---|---|
| C1 | «Pedí una gacetilla para la actividad SYN-001» (id explícito) | `PENDIENTE_VALIDACION` + borrador en `borradores/` |
| C2 | «Pedí una gacetilla para el taller de vinculación» (sin id) | Resolución difusa sobre el índice de actividades: borrador si hay coincidencia única, si no repregunta con candidatas |
| C3 | Tras una repregunta: responder con la elección en el turno siguiente | La pendiente guarda candidatas (orden, id, título, fecha) y el turno siguiente despacha el pedido |
| C4 | «Generá un post para LinkedIn de la jornada sintética» | `PENDIENTE_VALIDACION` con post del canal LinkedIn |
| C5 | «Generá un post de la jornada sintética» (sin canal) | `INCOMPLETA` — sin default silencioso de canal |
| C6 | «Mandame el newsletter de la semana» u otro pedido fuera del catálogo | Rechazo con `intencion_sin_pipeline` / `fuera_de_alcance`, sin aproximación |
| C7 | Una fila con rol no habilitado (p.ej. `visitante`) | `RECHAZADA` + línea de auditoría con el intento |
| C8 | Pedido redactado de forma que el clasificador determinístico no lo resuelva (opcional) | Fallback con modelo local: sólo extrae términos contra el catálogo, fail-closed; si tampoco resuelve, rechazo limpio |

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
escrita), exportable a `reunion-hu013-2026-09-25.json` si el instrumento es
digital o a Markdown consolidado si es en papel.

## 5. Criterio de éxito de s5d

`s5d` queda acreditable si:

- El participante completó al menos C1–C6 (C7–C8 deseables).
- Cada desviación del comportamiento esperado quedó registrada como defecto
  nuevo en `Registro-Defectos-Agente-1.md` o como observación de usabilidad.
- El acta quedó recuperable en `Documentos/PoC/Validacion-SEU/`.

Si la sesión no se realiza o se corta, `s5d` sigue sin marcar: protocolo
escrito no cuenta como prueba hecha.
