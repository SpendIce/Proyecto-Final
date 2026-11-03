# Prototipo descartable del recorrido de gacetillas de A1

Fecha de construcción: 03/11/2026. Responsable técnico: Juan Ignacio Goñe.

Pregunta: ¿qué disposición permite a la SEU pedir, revisar, corregir y decidir sobre una gacetilla sin perder contexto?

Abrir `prototipo.html` directamente en un navegador; no requiere instalación, servidor, credenciales ni conexión. Desde la raíz del repositorio:

```bash
xdg-open Implementacion/Agente1/prototipos/interfaz-gacetillas/prototipo.html
```

Las variantes se eligen con la barra inferior o con las flechas del teclado fuera de los campos de edición. También se pueden abrir con `?variant=A`, `?variant=B` o `?variant=C`. El cambio de variante conserva el estado; una recarga lo reinicia.

- **A — Bandeja y pieza:** lista compartida junto al documento para continuar pedidos sin cambiar de pantalla.
- **B — Recorrido por pasos:** bandeja inicial en filas, documento centrado y etapas visibles.
- **C — Documento y acciones:** bandeja en tarjetas, documento amplio y acciones al costado.

No existe todavía una página web de A1 donde insertar estas variantes. Este archivo autónomo está junto a su implementación y no incorpora un stack de producción. La rama `prototype/interfaz-a1-gacetillas-2026-11-03` conserva el artefacto; no se promueve ni se mergea a main como implementación.

## Recorrido disponible

Ingreso simulado → bandeja compartida → pedido guiado → preparación de muestra → revisión → edición aparte o ajuste → aprobación del borrador o descarte.

El pedido permite elegir los siete tipos existentes y un área del catálogo cerrado; la actividad aparece sólo en difusión. El asunto y los datos propios de cada tipo están fijados a su muestra. Las indicaciones adicionales se conservan para revisar el formulario, pero no se interpretan. El área seleccionada se aplica a la firma de la muestra.

La edición abre otra pestaña del mismo archivo, identificada como **editor externo simulado**, sin Google Docs. Guardar y volver incorpora una revisión humana nueva; cerrar sin guardar conserva la anterior. Mientras se edita, el pedido no admite ajuste ni decisión. El ajuste usa la última revisión, conserva correcciones humanas y crea otra; sólo ofrece transformaciones locales explícitas. No interpreta instrucciones libres.

El historial permite mirar revisiones anteriores, con acciones deshabilitadas sobre ellas. La decisión se confirma sobre la captura visible y vigente. Una pieza cerrada no admite otra decisión. Se muestra una señal que distingue intervención humana, ajuste simulado y ausencia de cambios de la muestra. El comentario es opcional. La aprobación termina el recorrido: no existe un paso posterior de publicación ni un aporte automático a Historia Viva.

## Procedencia y límites

Diseño: `Documentos/Arquitectura/Interfaz-Web-Agente-1-PPS-Juan-Ignacio-Gone.md` y ADR 0014. Vocabulario: `CONTEXT.md`. Ticket: [Prototipar el recorrido de gacetillas de A1 para revisar interfaz y contenido con SEU](https://github.com/SpendIce/Proyecto-Final/issues/152).

Las siete piezas son copias de `Implementacion/Agente1/golden/formas/<tipo>.md`, **casos de prueba del renderer**, no piezas institucionales vigentes ni contenido aceptado por la SEU. La difusión corresponde a la actividad sintética SYN-001 de `data/actividades_sinteticas.csv`. Las fechas de los casos son históricas; no anuncian actividades vigentes. No se copiaron intercambios privados.

Tipos, modos y condición de actividad proceden de `src/agente1/contracts/tipos_gacetilla_v1.json`; las áreas, de `src/agente1/contracts/areas_emisoras_v1.json`. Ambos catálogos son provisionales, pendientes de confirmación institucional. El HTML incluye snapshots y hashes SHA-256 de los archivos de las piezas, consultables en «Estado de la demostración y procedencia».

Identidad, permisos, espera, generación, edición externa, revisiones y decisiones están simulados. El panel de estado expone la revisión visible y vigente, sus vínculos, la fuente y las señales. No hay backend ni almacenamiento del navegador, recuperación, auditoría real, acceso a Workspace ni ejecución de un LLM. El archivo no verifica login Google, permisos de Docs o controles concurrentes de un servidor. Los bloqueos de acciones de esta maqueta sólo sirven para discutir el recorrido.

## Revisión con Juani y prueba guiada

**Reacción de Juani: pendiente. Variante elegida: pendiente. Prueba SEU: pendiente.** Construir o comprobar el archivo no permite completar esos campos ni cerrar el ticket.

Primero comparar las tres disposiciones con la misma pieza. Registrar preferencia, fricciones y elementos que convenga combinar. Después usar las tareas siguientes para preparar la prueba guiada, conservando separados usabilidad y contenido:

| Tarea | Qué observar |
|---|---|
| Continuar un pedido de otra persona | Encuentra la pieza y reconoce estado y revisión sin ayuda. |
| Pedir una difusión y luego un aviso | Reconoce cuándo corresponde elegir actividad y qué datos están precargados. |
| Editar la muestra en la pestaña aparte | Vuelve a A1 e identifica el texto recuperado y su revisión nueva. |
| Pedir un ajuste después de editar | Reconoce que se conservaron cambios y que existe otra revisión para revisar. |
| Consultar una revisión anterior | Distingue historial y revisión vigente antes de decidir. |
| Aprobar o descartar sin comentario | Comprende que cierra el borrador, sin inferir publicación o envío. |

Por tarea, registrar resultado, ayuda requerida, errores, cambios de contexto, tiempo observado y comentario de la persona. No se establecen metas nuevas. Registrar variante, fecha y versión del prototipo; identificar al participante sólo con el dato necesario y autorizado para esa instancia. No usar el panel de estado como evidencia institucional de identidad o auditoría.

Para valorar contenido, usar por separado la rúbrica vigente de `Implementacion/Agente1/evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`: eje 1 para tipos que generan; eje 2 para conformidad de forma. Estos snapshots no sustituyen las corridas del agente ni producen puntajes humanos por sí solos. La coordinación SEU y su evidencia siguen en los tickets existentes de visita y validación.

Trazabilidad: P4; HU-013 como canal; HU-010 como primer recorrido; responsable técnico Juani; reacción de diseño Juani; validación institucional SEU. Este prototipo no acredita DoD del canal real ni avance de TRL.

## Comprobación técnica del artefacto

El 03/11 se recorrió el HTML en Chromium con automatización temporal: tres variantes a 1440 px y 390 px, ingreso simulado, edición externa y captura de r2, ajuste desde r2 conservando la corrección humana, consulta de r1 con decisión bloqueada, aprobación de r3 con señal de intervención humana, pedido sin actividad y descarte, continuación de un pedido ajeno y reinicio por recarga. Resultado: recorrido completado, sin errores JavaScript ni desborde horizontal a 390 px. Esto verifica la maqueta local; no constituye reacción humana, prueba SEU ni verificación de controles del canal real.
