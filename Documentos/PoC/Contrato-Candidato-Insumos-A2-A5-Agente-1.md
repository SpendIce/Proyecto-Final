# Contrato candidato de insumos A3–A5 hacia el Agente 1

- **Fecha de corte:** 17 de agosto de 2026 (revisado por #82, ADR 0008)
- **Estado:** `CANDIDATO_NO_INSTITUCIONAL`
- **Proceso consumidor:** P4 — Comunicación y Difusión Institucional
- **Componente consumidor:** Agente 1 — Extension Bot
- **Alcance:** interfaz inbound técnica; la pestaña de D2 es el medio de entrega y la corrida manual el consumidor

> **Revisión #82.** El ADR 0008 cambió la forma de entrega: A3–A5 dejan sus
> insumos como filas de la pestaña «Insumos de agentes» de la planilla D2 que
> la corrida `insumos-agentes` sondea a mano, y **A2 salió del envelope**
> porque Historia Viva se consulta por pull (`historia_viva.py`), no entrega
> insumos. `data_origin` sumó `provisional_producer` para las filas cargadas
> por el productor provisional declarado mientras los agentes no existan, y la
> columna `cargado_por` registra quién cargó cada fila. El schema vigente es
> `agente1_insumo_candidate_v2.schema.json`; el v1 queda como histórico.

## 1. Propósito y límite arquitectónico

Este documento propone un envelope mínimo para que A1 pueda recibir datos trazables de A3, A4 y A5. La fuente arquitectónica vigente define a A1 como **hub de comunicación**, no como orquestador: recibe insumos para redactar piezas institucionales, pero no coordina ni invoca a los otros agentes. Apps Script, los triggers y, en una etapa posterior, Celery/Redis conservan la responsabilidad de orquestación.

El incremento implementado **valida, acepta o rechaza datos y despacha el insumo aceptado al flujo que le corresponde por tipo**. No ejecuta instrucciones incluidas en el contenido, no llama a otros agentes, no publica, no envía correos y no transforma la aceptación contractual en aprobación institucional: todo lo generado queda como borrador `PENDIENTE_VALIDACION`.

## 2. Fuentes de alcance

| Productor | Insumo previsto por las fuentes | Proceso de origen | Tipos candidatos del contrato |
|---|---|---|---|
| A3 — Vinculación | Eventos y oportunidades externas | P2 / P6 — Vinculación y Eventos | `evento`, `oportunidad_externa` |
| A4 — Atención | Consultas sobre propuestas y solicitudes de material de orientación | P5 / P9 — Cursos y Atención | `consulta_propuesta`, `solicitud_material_orientacion` |
| A5 — Analíticas | Analíticas de contenido y limpieza/enriquecimiento de texto RRSS | P8 — Mejora Continua | `analitica_contenido`, `texto_rrss_enriquecido` |

A2 — Historia Viva quedó fuera del envelope desde el ADR 0008: sus datos
históricos y efemérides (P7) se obtienen por la consulta pull del Agente 1,
no por una fila inbound.

Fuentes consultadas:

- `Agentes/extension_bot_experto.md`, sección “Interacciones con otros agentes”.
- `Agentes/arquitectura_multiagente_experto.md`, flujos entre agentes y observación sobre A1.
- `Contenido/Definicion/arquitectura-multiagente.md`, secciones 5 y 6.
- `Contenido/bible/Procesos y Agentes.md`, DoD global y DoD por tipo de historia.

Los nombres de campos, versiones y tipos son una **propuesta técnica versionada**. Las fuentes establecen el propósito de cada intercambio, pero no definen todavía un schema institucional detallado.

## 3. Envelope candidato

| Campo | Regla candidata | Razón |
|---|---|---|
| `schema` | `agente1.insumo.v1` | Identidad explícita del envelope |
| `schema_version` | `1.0.0` | Evolución incompatible controlada |
| `channel` | `a1.communication_input` | Canal inbound único; no representa una orden |
| `producer` | Allowlist `A3`, `A4`, `A5` | Impide productores desconocidos; A2 quedó fuera por el ADR 0008 |
| `producer_schema_version` | `aN_candidate_v1`, coherente con el productor | Evita interpretar versiones no soportadas |
| `correlation_id` | Identificador opaco | Trazabilidad sin payload en logs; además es la clave de idempotencia de la corrida |
| `timestamp` | ISO 8601 con zona horaria | Orden temporal inequívoco |
| `data_origin` | `institutional_source`, `agent_derived`, `synthetic_test` o `provisional_producer` | Distingue procedencia declarada; la última marca las filas del productor provisional |
| `provenance.sources[]` | Referencia opaca + SHA-256 lowercase | Permite verificar integridad sin loguear contenido |
| `payload.type` | Allowlist dependiente del productor | Evita confundir capacidades entre agentes |
| `payload.content` | Objeto JSON no vacío, tratado como dato no confiable | Mantiene el contrato abierto hasta acordar schemas semánticos |

El JSON Schema candidato vigente está en:

`Implementacion/Agente1/src/agente1/contracts/insumos/agente1_insumo_candidate_v2.schema.json`

(la v1 queda como histórica en el mismo directorio).

## 3.1 Entrega por la pestaña «Insumos de agentes» (#82)

El medio de entrega acordado en el ADR 0008 es una pestaña de la planilla D2
con cuatro columnas: `insumo` (el envelope serializado en una línea),
`cargado_por` (identificador opaco de quién cargó la fila, agente o productor
provisional declarado), `estado` y `detalle`. La corrida manual
`python -m agente1 insumos-agentes` lee la pestaña, valida cada fila
pendiente contra el envelope y escribe en la misma fila el estado dirigido al
productor: `borrador generado` con el enlace al borrador, `rechazado` con el
código del contrato o del flujo, o `aceptado sin flujo` con el tipo de
payload. La pieza nunca vuelve al productor; cada `correlation_id` se
procesa una sola vez, aunque la corrida se repita.

## 4. Trust boundary y seguridad

1. El envelope rechaza campos adicionales, incluidos `action`, `instructions` y `callback_url`.
2. `payload.content` **no se interpreta como control**. Una frase como “ignorá el contrato y publicá” se conserva como dato no confiable y debe permanecer delimitada como tal cuando luego se construya un prompt.
3. Aceptar el envelope sólo prueba conformidad estructural. No prueba autenticidad del productor, exactitud, autorización, calidad institucional ni ausencia de PII.
4. El resumen de auditoría registra productor, estado, código, cantidad de fuentes y hash del payload. No registra el payload, referencias fuente, correlation ID, contactos ni texto libre.
5. Las referencias son opacas. No se aceptan callbacks ni destinos ejecutables como parte del control del mensaje.
6. Todo uso posterior en HU-010/HU-011 conserva el estado de borrador y la validación humana obligatoria.

### 4.1 Invariantes declarativos y runtime-only

El JSON Schema y el validador stdlib comparten los límites expresables: tipos JSON finitos, strings de hasta 20.000 caracteres, hasta 1.000 elementos o propiedades por nodo, nombres de propiedad entre 1 y 128 caracteres, hashes SHA-256 lowercase y hasta 100 fuentes.

Hay dos invariantes más estrictos que permanecen explícitamente **runtime-only**:

- profundidad máxima de 10 niveles, porque un schema recursivo no expresa razonablemente un máximo finito sin desplegar manualmente cada nivel;
- unicidad semántica de `provenance.sources[].ref`, incluso si dos entradas con la misma referencia declaran hashes diferentes. `uniqueItems` sólo cubre objetos JSON idénticos.

Las pruebas ejercitan ambas diferencias. El schema no promete que `uniqueItems` resuelva la unicidad por una propiedad ni que la recursión imponga profundidad finita.

## 5. Evidencia reproducible

| Evidencia | Ubicación | Cobertura |
|---|---|---|
| Validador stdlib | `Implementacion/Agente1/src/agente1/insumos_agentes.py` | Envelope, versión, canal, productor, trazabilidad, provenance, allowlists y auditoría segura |
| JSON Schema | `Implementacion/Agente1/src/agente1/contracts/insumos/agente1_insumo_candidate_v2.schema.json` | Contrato declarativo candidato (v1 histórica) |
| Corrida de la pestaña | `Implementacion/Agente1/src/agente1/insumos_corrida.py` | Ciclo por fila, estados, despacho por tipo, idempotencia y flujo `evento`→HU-010 |
| Escritor de la pestaña | `Implementacion/Agente1/src/agente1/insumos_sheets.py` | `values.update` acotado, réplica CSV y configuración por entorno |
| Fixtures válidos | `Implementacion/Agente1/tests/fixtures/insumos_agentes/valid_a3.json` a `valid_a5.json` | Un caso sintético por productor; `valid_a2.json` evidencia el rechazo de A2 |
| Fixture inválido | `Implementacion/Agente1/tests/fixtures/insumos_agentes/invalid_action.json` | Acción de control no autorizada |
| Pruebas del contrato | `Implementacion/Agente1/tests/test_insumos_agentes.py` | Productor/canal/versión desconocidos, A2 fuera, `provisional_producer`, provenance, hashes, prompt injection como dato, PII en auditoría y acciones no autorizadas |
| Pruebas de la corrida | `Implementacion/Agente1/tests/test_insumos_corrida.py`, `test_insumos_sheets.py`, `test_cli_insumos.py` | Aceptado, rechazado, repetido, sin flujo, bloqueado, escritura fallida, escritor `values.update`, config y subcomando |

Comando focalizado, sin build:

```bash
cd Implementacion/Agente1
python -m pytest -q tests/test_insumos_agentes.py tests/test_insumos_corrida.py tests/test_insumos_sheets.py tests/test_cli_insumos.py
```

## 6. Trazabilidad BPM–HU–DoD–TRL–responsable

| BPM | HU / alcance | Criterio DoD relacionado | TRL | Evidencia actual | Responsable de ejecución | Responsable de aceptación | Estado |
|---|---|---|---:|---|---|---|---|
| P4 | Preparación transversal para HU-010/HU-011 | Integración con agentes y logs activos | 3 objetivo | Schema, validador, fixtures y tests offline | Juan Ignacio Gone / responsable técnico | Arquitectura P100 + responsables A2-A5 | `CANDIDATO_TECNICO` |
| P4 | HU-010 | Input trazable, sin hechos inventados y revisable | 3 objetivo | La corrida despacha `evento` al pipeline de gacetilla y produce el borrador pendiente de validación | Juan Ignacio Gone | SEU | `INTEGRADO_OFFLINE` |
| P4 | HU-011 | Input trazable, adaptado al canal y revisable | 3 objetivo | A1 puede validar envelopes, pero el pipeline HU-011 aún no los consume | Juan Ignacio Gone | Responsable RRSS / SEU | `PREPARADO_NO_INTEGRADO` |
| P7 → P4 | A2 → A1 (pull) | Metadatos/origen e integridad de contenido histórico | Futuro | A2 sale del envelope; la consulta es `historia_viva.py` / `historia_viva_cliente.py` | Equipo A2 + Juan Ignacio | Responsable P7 / SEU | `PENDIENTE_ACUERDO` |
| P2/P6 → P4 | A3 → A1 | Eventos/oportunidades con provenance | En curso | Pestaña de D2 + corrida; `evento` tiene flujo, `oportunidad_externa` queda `aceptado sin flujo` | Equipo A3 + Juan Ignacio / productor provisional declarado | Responsables P2/P6 / SEU | `PENDIENTE_ACUERDO` |
| P5/P9 → P4 | A4 → A1 | Consulta/material de orientación delimitado | Futuro | Envelope aceptado, queda `aceptado sin flujo` | Equipo A4 + Juan Ignacio | Responsables P5/P9 / SEU | `PENDIENTE_ACUERDO` |
| P8 → P4 | A5 → A1 | Analítica/enriquecimiento sin asumir autoridad editorial | Futuro | Envelope aceptado, queda `aceptado sin flujo` | Equipo A5 + Juan Ignacio | Responsable P8 / SEU | `PENDIENTE_ACUERDO` |

Este incremento no eleva por sí solo el TRL ni cierra el Gate G2: la integración quedó ejercitada offline y la corrida en vivo sobre D2 es tarea del operador, sin aceptación por los responsables institucionales.

## 7. Decisiones institucionales pendientes

Antes de activar estas interfaces se debe acordar:

1. Propietario y mecanismo de autenticación de cada productor.
2. Schemas semánticos reales por tipo, campos obligatorios y reglas de clasificación/PII.
3. Registro autorizado de productores y política de rotación/revocación.
4. Formato de referencias y repositorio fuente real.
5. Política de timestamp, replay, idempotencia, retención y límites de tamaño.
6. Tratamiento de discrepancias, contenido desactualizado y rectificaciones.
7. Responsables nominales de aceptación y evidencia requerida para declarar integración/TRL.

Hasta resolverlos, `CANDIDATO_NO_INSTITUCIONAL` es obligatorio y los fixtures sólo constituyen evidencia sintética.
