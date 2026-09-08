# Estado interno de Sprint 3 — Agente 1

- **Fecha de medición:** 2026-08-26
- **Fecha de corte documental:** 2026-09-06
- **Proceso BPM:** P4 — Comunicación y Difusión Institucional
- **Propósito:** consolidar el avance interno verificable antes del hito del
  2026-08-28, sin atribuir cierres a SEU, DSI o Dirección.

## Resultado de regresión

La suite de `Implementacion/Agente1` se ejecutó fuera del sandbox el
2026-08-26. El primer corte fue histórico; el incremento posterior del mismo
corte dejó el conteo canónico usado en esta actualización documental:

| Alcance | Resultado | Límite de interpretación |
|---|---:|---|
| Suite completa (corte documental 2026-09-06, hoy histórico) | **513 pruebas verdes** | Verifica comportamiento local y contratos; no prueba servicios institucionales live. El conteo vigente es 534 en el corte del 2026-09-08. |
| Suite completa, primer corte histórico del 26/08 | **457 pruebas verdes** | Línea base previa al incremento; no describe la candidata vigente. |
| Bloque HU-011 estructurado, corte histórico | **68 pruebas verdes** | Incluye regresiones para controles mecánicos de `DEF-A1-012`; no sustituye validación editorial SEU. |
| Suite dentro del sandbox | 16 fallas `EPERM` de loopback | Restricción ambiental conocida; no se reproduce fuera del sandbox. |

Comando de reproducción fuera del sandbox, con `pytest` disponible:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache python -m pytest -q
```

## Avance interno cerrado o preparado

| Frente | HU / DoD | Evidencia o artefacto | Estado al corte | Próximo paso interno |
|---|---|---|---|---|
| Gate de creatividad | HU-011 / sin invención ni circuito no autorizado | `posts.py`, prompts v3 y regresiones | `IMPLEMENTADO_Y_REGRESIONADO` | Conservar el gate fail-closed y registrar hallazgos de la futura revisión SEU. |
| Registro lingüístico | HU-011 / tono | Rechazo mecánico de tuteo explícito | `PARCIAL_TECNICO` | La SEU debe definir el registro editorial; el control no infiere calidad. |
| Persistencia | Sprint 3 / integridad | Migraciones `0001`, `0002`, `0003` y validación PostgreSQL efímera | `REGRESIONADA_EN_MOTOR` | Mantener el spike aislado; concurrencia, performance y recuperación quedan para una necesidad operativa validada. |
| HU-012 | Trigger, borrador, HITL, idempotencia y registro | Contrato, matriz offline y tests | `BASELINE_OFFLINE` | Mantener el fake y completar la trazabilidad del DoD para Sprint 4; no integrar correo real. |
| Evidencia | Gate G2 / trazabilidad | Registro de defectos, README y este corte | `ACTUALIZADA_PARCIALMENTE` | Mantener el índice alineado con el conteo canónico de 513 y vincular cada resultado a su evidencia; no atribuir validación SEU. |

## Controles incorporados para `DEF-A1-012`

El gate de salida creativa v3 ahora rechaza:

- modalidad no autorizada, incluida la palabra `remoto`;
- CTAs que prometen inscripción, registro, reserva, compra o agenda sin que el
  circuito esté respaldado por la fuente;
- formas explícitas de tuteo; y
- fragmentos significativos del **título** de la actividad en la creatividad.

Los hechos de fuente continúan siendo agregados por el renderer determinista.
Los controles anteriores son mecánicos y deliberadamente conservadores: no
autorizan publicar, enviar ni reemplazan el checklist humano.

## Riesgos y dependencias que permanecen abiertas

| ID / dependencia | Estado | Responsable de cierre |
|---|---|---|
| `DEF-A1-003` — performance cold/warm | `RESUELTO_PENDIENTE_VALIDACION` | Medido y documentado el 26/08; el umbral y el host objetivo requieren aceptación institucional. |
| `DEF-A1-010` — concurrencia, backup/restauración y permisos | `PENDIENTE_POST_SPIKE` | Juan Ignacio/DSI según el entorno que se autorice. |
| Validación SEU de HU-010/HU-011 | `BLOQUEADO_EXTERNO` | Validadores SEU designados. |
| Workspace D2/D3 y OAuth | `BLOQUEADO_EXTERNO` | DSI y administrador designado. |
| Criterio y decisión Gate G2 | `BLOQUEADO_EXTERNO` | Dirección y SEU. |

## Incremento posterior del mismo día

| Frente | Entregable | Estado | Límite |
|---|---|---|---|
| Política de redes | `politica_redes_provisional_v1` + `test_politica_redes.py` | `IMPLEMENTADO_Y_REGRESIONADO` | 14 reglas activas con caso negativo; 6 siguen dependiendo de criterio SEU |
| Capacidad | `medir_capacidad_hu011.py` + `benchmark-capacidad-a1-2026-08-26.md` | `MEDIDO` | El cómputo alcanza de sobra para el volumen informado; la conformidad de contenido no |
| HU-012 | `matriz_origenes_inscripcion_v1` + `origenes_inscripcion.py` | `CANDIDATO_REGRESIONADO` | Ningún origen habilita envío; ningún campo está confirmado por SEU |
| HU-010 | `Solicitud-Activos-Gacetilla-Agente-1.md` | `PEDIDO_PREPARADO` | Sin respuesta, `DEF-A1-002` sigue `BLOQUEADO_EXTERNO` |

La suite integral quedó en **513 pruebas verdes** fuera del sandbox tras este
incremento, conteo del corte documental 2026-09-06. Se abrieron `DEF-A1-013`,
`DEF-A1-014` y `DEF-A1-015`; `DEF-A1-003` pasó a
`RESUELTO_PENDIENTE_VALIDACION` en su componente técnico.

`DEF-A1-013` y `DEF-A1-014` se cerraron después, en el corte del 2026-09-08
(`a2c33b1`), que deja la suite en **534 pruebas verdes**. `DEF-A1-015` sigue
`BLOQUEADO_EXTERNO`.

## Lectura del Gantt

El Sprint 3 queda al día en su frente interno: persistencia documentada,
fortalecida y regresionada en PostgreSQL efímero; secretos/logging ya
preparados y controles locales disponibles. No se declara el hito `m3` como
cerrado: la gestión de bloqueantes institucionales y la evidencia live siguen
pendientes. El inicio del Sprint 4 puede enfocarse en HU-012 sobre su baseline
offline, sin anticipar Gmail, SMTP, FastAPI, Celery, Redis ni publicación.
