# Planteo breve — Agente 1 (Extension Bot)

**Reunión:** Dirección de Carrera / Dirección de Proyecto y laboratorio de pruebas
**Duración:** 5 minutos
**Objetivo:** presentar qué problema resuelve el Agente 1, delimitar qué corresponde evaluar y acordar el siguiente paso de validación.

---

## Idea central

El **Agente 1 — Extension Bot** es un asistente de comunicación institucional para la Secretaría de Extensión Universitaria (SEU). A partir de datos controlados de una actividad, genera borradores de gacetillas y publicaciones para redes sociales.

No reemplaza al personal ni publica por sí solo: toda salida queda identificada como **`BORRADOR — NO PUBLICAR`** y en estado **`PENDIENTE_VALIDACION`** hasta la revisión humana registrada.

Su alcance pertenece al **Proceso 4 — Comunicación y Difusión Institucional**. Puede recibir insumos de otros agentes, pero no los orquesta ni realiza analítica, scraping o atención masiva al público.

---

## Guion oral (5 minutos)

### 0:00–0:40 — Problema y propuesta

> Hoy, una actividad de Extensión puede requerir una gacetilla y piezas para distintos canales. La propuesta no es automatizar decisiones institucionales: es asistir la preparación de esos textos a partir de datos estructurados, para reducir tareas repetitivas y conservar trazabilidad. El Agente 1 se llama Extension Bot y se concentra exclusivamente en comunicación institucional de la SEU.

### 0:40–1:35 — Alcance concreto

> El MVP se acota a dos historias de usuario: HU-010, generación de gacetillas, y HU-011, generación de borradores de posts para Instagram y LinkedIn. A partir de una entrada con datos de la actividad, el sistema valida que la información esté completa, genera un borrador y registra la ejecución. Si faltan datos o falla un control, no debe producir una comunicación oficial.

> Quedan fuera de este alcance el chatbot público, la publicación automática, el scraping, las integraciones externas no definidas y la analítica. El agente asiste al Proceso 4; no es el orquestador del Proyecto Centenario.

### 1:35–2:20 — Flujo y responsabilidad humana

```text
Datos autorizados de actividad
            ↓
Validación de completitud y generación local
            ↓
BORRADOR — NO PUBLICAR + log de ejecución
            ↓
Revisión humana de la SEU
            ↓
Aprobación o rechazo registrado
```

> El punto de control es deliberado: el agente propone; la institución decide. La responsabilidad del contenido no se transfiere al modelo ni al desarrollador. Antes de una publicación o envío oficial debe existir validación humana.

### 2:20–3:25 — Estado real, sin sobreprometer

> A nivel técnico, HU-010 y HU-011 cuentan con implementación y pruebas **offline** sobre datos y transportes simulados. Existen controles para no crear borradores ante entradas incompletas, conservar trazabilidad y bloquear acciones de distribución. También hay una auditoría offline de seguridad que verifica, entre otros puntos, allowlists, ausencia de secretos en logs, bloqueo de revocación simulada y la marca obligatoria de borrador.

> Esto es evidencia de un entorno controlado; **no equivale todavía a una aprobación institucional ni al cierre del Gate G2 / TRL 3**. Siguen pendientes la integración con Google Workspace real, la definición de la identidad técnica y permisos mínimos, y la validación de calidad por referentes de la SEU.

### 3:25–4:30 — Qué se propone evaluar en el laboratorio

> Para pasar de la prueba controlada a una validación defendible, necesito acordar un entorno de prueba acotado y los criterios de verificación. La prueba no requiere datos reales ni capacidad de publicar.

> El laboratorio podría evaluar: primero, que la identidad técnica tenga privilegio mínimo; segundo, que sólo acceda a una planilla, plantilla y carpeta de prueba autorizadas; tercero, que no queden credenciales ni contenido sensible en los logs; cuarto, que una revocación de permisos bloquee la operación sin generar salida; y quinto, que el sistema no tenga rutas de compartir, enviar o publicar durante esta etapa.

### 4:30–5:00 — Pedido y cierre

> El pedido concreto es definir con el laboratorio un sandbox de Google Workspace y un responsable técnico para las pruebas de permisos y revocación; y con la SEU, una plantilla inicial, criterios de tono por canal y responsables de validación. Con esos insumos se podrá ejecutar un caso de punta a punta, registrar la evidencia y decidir objetivamente si el MVP alcanza el gate de TRL 3.

> En síntesis: no presento un agente autónomo que publica contenido, sino una capacidad institucional acotada, auditable y bajo control humano.

---

## Láminas de apoyo (3)

Para proyectar. Texto grande, legible desde el fondo del aula. Una lámina por tramo del guion:

| # | Lámina | Cuándo |
|---|---|---|
| 1 | ![Problema y propuesta](Laminas-Agente-1-Extension-Bot-2026-08-26/01-problema-y-propuesta.png) `01-problema-y-propuesta.png` | 0:00–1:35 — problema, alcance y el límite: el agente propone, la institución decide. |
| 2 | ![Generación sintética](Laminas-Agente-1-Extension-Bot-2026-08-26/02-generacion-real.png) `02-generacion-real.png` | 1:35–3:25 — ejemplo sintético SYN-003: entrada, borrador de LinkedIn, registro y el caso incompleto. Se conserva el nombre histórico del archivo PNG. |
| 3 | ![Control humano y pedido](Laminas-Agente-1-Extension-Bot-2026-08-26/03-control-humano-y-pedido.png) `03-control-humano-y-pedido.png` | 3:25–5:00 — quién decide, qué está verificado offline y qué se pide al laboratorio y a la SEU. |

### Cómo proyectarlas

Dos opciones, ninguna requiere abrir los archivos uno por uno:

- **`Laminas-Agente-1-Extension-Bot-2026-08-26.html`** — se abre en el navegador y funciona como presentación: `→` / `espacio` avanza, `←` retrocede, `F` pantalla completa, `P` imprime o guarda en PDF. También se puede hacer clic para avanzar (clic en el borde izquierdo retrocede). La lámina se escala sola a la pantalla o al proyector.
- **`Laminas-Agente-1-Extension-Bot-2026-08-26.pdf`** — las mismas tres láminas en 16:9, para pasar con cualquier visor en otra máquina.

Los PNG sueltos de la carpeta quedan por si hacen falta para el informe o un mail.

> Para regenerar todo desde el HTML: PDF con `chromium --headless --no-pdf-header-footer --print-to-pdf=... archivo.html`; cada PNG con `chromium --headless --force-device-scale-factor=2 --window-size=1600,900 --screenshot=... "archivo.html?limpio#l1"` (`#l2`, `#l3` para las otras). Los textos del ejemplo sintético son la salida literal de la corrida offline del 17/08/2026 (`Implementacion/Agente1/salida/matriz-hu011-live-v3-final/`), realizada con datos sintéticos.

También queda disponible la versión de una sola hoja, más densa, útil como handout impreso o anexo del informe (no para proyectar):

![Lámina resumen de una hoja](Lamina-Agente-1-Extension-Bot-2026-08-26.png)

| Qué es | Qué ya está demostrado | Qué deben evaluar / habilitar |
|---|---|---|
| Asistente de comunicación institucional de la SEU para el Proceso 4. Genera borradores de gacetillas y posts. | Flujo offline de HU-010/HU-011, validación de datos, logs, estado `PENDIENTE_VALIDACION` y controles offline de seguridad. | Sandbox D2, identidad técnica de mínimo privilegio, recursos de prueba autorizados, pruebas negativas de permisos/revocación y validación humana SEU. |
| **Nunca publica ni envía sin aprobación humana registrada.** | **TRL 3 / Gate G2: pendiente de validación institucional.** | **Sin datos reales, sin credenciales expuestas y sin publicación en esta etapa.** |

---

## Preguntas que conviene llevar respondidas

- **¿Contra qué proceso mapea?** Proceso 4 — Comunicación y Difusión Institucional; con apoyo secundario a los procesos 3, 5 y 6 cuando corresponda.
- **¿Quién controla el contenido?** Los roles de comunicación y coordinación de la SEU; el agente sólo prepara el borrador y el responsable técnico mantiene la automatización y trazabilidad.
- **¿Qué evidencia existe hoy?** Pruebas y auditoría offline; no se debe afirmar integración real de Workspace ni aceptación SEU, porque siguen pendientes.
- **¿Qué se prueba en el laboratorio?** Permisos mínimos, recursos autorizados, aislamiento del entorno de prueba, protección de secretos y bloqueo seguro ante revocación o acciones no autorizadas.
- **¿Cuál es el criterio de éxito inmediato?** Una ejecución controlada Sheets → Agente 1 → Docs con recursos de prueba, validación de seguridad satisfactoria y revisión humana documentada de los borradores.

---

## Video opcional (45 segundos)

No hace falta un video si vas a estar presente: para cinco minutos, la lámina única y una muestra de borrador son más directas. Si querés enviar un anticipo antes o después de la reunión, podés grabar este texto sobre la lámina:

> El Agente 1, Extension Bot, busca asistir la comunicación institucional de la Secretaría de Extensión. A partir de datos autorizados de una actividad, genera borradores de gacetillas y posts. No publica ni envía contenido: cada salida queda pendiente de validación humana y registrada para su trazabilidad. Hoy el flujo está verificado offline; el próximo paso es validarlo en un sandbox institucional, con permisos mínimos, recursos de prueba y controles de seguridad. Lo que proponemos evaluar no es sólo si el modelo redacta: es si puede operar de forma acotada, segura y auditable dentro del Proceso 4.

---

## Respaldo documental

- Alcance y exclusiones: `Agentes/extension_bot_experto.md`.
- Estado, defectos y gate: `Documentos/PoC/Plan-Recuperacion-MVP-Agente-1-2026-08-17.md` y `Documentos/PoC/Registro-Defectos-Agente-1.md`.
- Evidencia de auditoría offline: `Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md`.
- Solicitud técnica de sandbox: `Documentos/PoC/Nota-Solicitud-DSI-Agente-1-PPS-Juan-Ignacio-Gone.md`.
