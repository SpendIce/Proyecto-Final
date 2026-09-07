# Paquete para cerrar el contrato Historia Viva ↔ Agente 1

**Issue:** #17 — Cerrar el contrato Historia Viva con Ignacio<br>
**Estado:** `READY_FOR_HUMAN` — preparado para revisión y acuerdo humano<br>
**Fecha de consolidación:** 2026-09-05<br>
**Responsable de preparación:** Juan Ignacio Gone / Agente 1<br>
**Fuente primaria de la posición de A1:** `respuesta-nacho.md` (31/08/2026)<br>
**Aceptación de Ignacio:** pendiente; este paquete no la presume ni la sustituye.
**Estado de acuerdo:** `PENDIENTE_HUMANO`; las etiquetas de aceptación son sólo la posición de Juan.

## 1. Propósito y límite

Este documento convierte la respuesta de Juan en una agenda verificable para cerrar
el contrato con Ignacio. Distingue lo que Juan considera aceptable, los cambios
que solicita y los puntos que siguen abiertos. No es el OpenAPI de Historia Viva,
no implementa el servicio A2 y no constituye aceptación institucional.

El intercambio queda acotado a Historia Viva como repositorio de fuentes históricas
validadas y al Agente 1 como consumidor que prepara una pieza comunicacional. A1
no es orquestador, no publica sin validación humana y no recibe una efeméride
redactada como autoridad.

## 2. Evidencia revisada y sanitización

Se revisaron:

- `respuesta-nacho.md`;
- `Agentes/historia_viva_experto.md` y `Contenido/Definicion/agente-2-historia-viva.md`;
- `Agentes/extension_bot_experto.md` y `Agentes/arquitectura_multiagente_experto.md`;
- `Documentos/PlanIntegracion/Plan-Integracion-Agente-1-PPS-Juan-Ignacio-Gone.md`;
- `Documentos/PoC/Contrato-Candidato-Insumos-A2-A5-Agente-1.md`;
- los contratos de entrada de gacetilla/post y la implementación offline de A1;
- `Documentos/Gantt/diagrama-gantt-implementacion-semanal.mmd`.

El paquete sólo conserva nombres de artefactos, roles, estados, fechas de plan y
campos contractuales. No contiene tokens, credenciales, URLs privadas, IDs de
Drive/Sheets, datos personales sensibles, contactos reales ni payloads de producción;
los nombres de responsables que aparecen son sólo contexto de gestión ya declarado.
Las
fechas son las del plan de Juan y están marcadas como no comprometidas por Ignacio.

## 3. Estado de cada punto

Las etiquetas de esta tabla son deliberadamente unilaterales: `Aceptado por Juan`
no significa `acordado con Ignacio`.

| Punto | Posición registrada de Juan | Estado para el acuerdo | Evidencia que falta para cerrar |
|---|---|---|---|
| Transporte | HTTP/REST, JSON UTF-8, `/v1`; A1 inicia las llamadas | Aceptado por Juan | Confirmación escrita de Ignacio y versión canónica |
| Autenticación | Bearer token revocable por agente; distinguir `401`/`403`; secreto fuera de Git | Aceptado por Juan | Esquema de identidad, scopes y responsable de provisión |
| Datos servidos | Sólo material validado; inexistente/no validado responde `404` indistinguible | Aceptado por Juan | Prueba de contrato y regla vigente en OpenAPI |
| Búsqueda | `GET /v1/fragmentos`; consulta, período, tipo; límite 10, tope 50; vacío `200` | Aceptado por Juan | Parámetros, enums y respuesta cerrada en OpenAPI |
| Ampliación | `GET /v1/piezas/{pieza_id}` | Cambio solicitado | Schema completo y cerrado, incluidos errores |
| Aportes | `POST /v1/aportes` | Cambio solicitado | `Idempotency-Key` y semántica de repetición documentadas |
| Fuente de cada pasaje | `fragmento_id` estable y ubicación interna cuando exista | Cambio solicitado | Regla de estabilidad, formato y `ubicacion` en OpenAPI |
| Efemérides | A1 consulta por período/tema y redacta; A2 entrega fragmentos, no prosa | Cambio solicitado | Retiro explícito de `efemeride` del contrato candidato y confirmación A2 |
| Tipo/canal del aporte | Conservar `tipo_contenido` y `canal` | Cambio solicitado | Enums versionados y valores permitidos acordados |
| Publicación | `fecha_publicacion` y `url_publicacion` pueden no existir al aprobar | Cambio solicitado | Campos opcionales o estados separados en el schema |
| Imágenes | Historia Viva no sirve binarios; URL institucional sólo si A1 tiene permiso | Aceptado por Juan | Permisos institucionales y regla de acceso |
| Fallas | Códigos `400`, `401`, `403`, `404`, `429`, `503`; sin colas/reintentos A2 | Aceptado por Juan | Contratos de error, `Retry-After` si aplica y prueba |
| Latencia | Objetivo de respuesta menor a 15 s; timeout de A1 aún no fijado | Parcial / pendiente | SLA, timeout cliente y conducta ante `429`/`503` |
| Caché | Sin caché de Historia Viva en esta entrega | Aceptado por Juan | Confirmación de alcance y documentación de ausencia de caché |
| Fecha del endpoint | Plan de Juan: 30/10/2026 | No es compromiso | Disponibilidad confirmada por Ignacio |
| Inicio de pruebas A1 | Plan de Juan: 02/11/2026 | No es compromiso | Mock/endpoint estable y coordinación de prueba |
| OpenAPI canónico | Debe vivir en el repositorio de Ignacio; A1 consume tag/commit fijado | Propuesta de gobierno | Repositorio, ruta, versión, tag/commit y checksum |

## 4. Checklist de cierre contractual para llevar a la reunión

Marcar una casilla sólo con evidencia verificable. La columna final debe contener
un tag, commit, acta/minuta o referencia equivalente; nunca una inferencia de
conformidad técnica.

### OpenAPI 3.1 y endpoints

- [ ] Se identifica un único repositorio fuente de OpenAPI 3.1.
- [ ] Se identifica la ruta del archivo y la versión `info.version`.
- [ ] Se fija un tag o commit exacto; se registra su SHA completo o referencia equivalente.
- [ ] A1 conserva únicamente mocks/fixtures derivados de esa versión.
- [ ] Quedan documentados `GET /v1/fragmentos`, `GET /v1/piezas/{pieza_id}` y `POST /v1/aportes`.
- [ ] Cada endpoint tiene parámetros, headers, request, respuesta `2xx`, errores, límites y `additionalProperties` definidos.
- [ ] `GET /v1/piezas/{pieza_id}` tiene respuesta completa y cerrada; no se acepta “todos sus campos”.
- [ ] Resultado vacío de fragmentos es `200`; `404` no revela falta de pieza versus falta de validación.

### Identidad, fechas y fragmentos

- [ ] Cada elemento de `fragmentos` tiene `fragmento_id` estable y reproducible para el mismo pasaje.
- [ ] Se define la relación entre `fragmento_id` y `pieza_id`.
- [ ] Se define `ubicacion` (`pagina`, `seccion` o equivalente) y su opcionalidad.
- [ ] Se conservan `texto`, rango de fechas, `precision_fecha`, `tipo`, `resumen_pieza`, `pieza_id`, `url_original` y `validada_el`, con tipos y nulabilidad explícitos.
- [ ] Se cierra el enum de precisión temporal y se impide mostrar `mes`, `anio` o `decada` como fecha exacta.
- [ ] Se cierra el enum `tipo` de pieza. Este repositorio no define valores normativos: no completar por supuesto.

### Aportes e idempotencia

- [ ] `POST /v1/aportes` define si `Idempotency-Key` es requerido o aceptado y su formato, longitud y vigencia.
- [ ] Misma clave y mismo payload devuelven el mismo resultado lógico, sin duplicar el aporte.
- [ ] Misma clave con payload distinto tiene una respuesta explícita, sin mutar silenciosamente el primer aporte.
- [ ] Si se pierde la primera respuesta después de persistir, A1 puede repetir sin crear otro aporte.
- [ ] Se define la respuesta de primera llamada y repetición, incluidos `status`, identificador, estado y headers.
- [ ] Se define el comportamiento ante clave ausente, inválida, vencida o concurrente.
- [ ] El aporte conserva `titulo`, `cuerpo`, `piezas_fuente`, `tipo_contenido` y `canal`, con obligatoriedad/nulabilidad explícita.
- [ ] Se acuerdan los enums de `tipo_contenido` y `canal`; `gacetilla`, `post`, `Instagram` y `LinkedIn` son sólo referencias observadas, no acuerdos.
- [ ] `fecha_publicacion` y `url_publicacion` son opcionales para aprobado aún no publicado, o existe un estado separado.
- [ ] Se aclara qué actor y qué estado habilitan el registro; aprobar no equivale a publicar.

### Operación, seguridad y fechas

- [ ] Se acuerdan timeout de cliente A1, presupuesto de respuesta de A2 y conducta ante timeout.
- [ ] Se acuerda si A1 puede reintentar `GET` y con qué cantidad/backoff; no se habilita retry ciego de `POST` sin idempotencia cerrada.
- [ ] Se documentan `429`/`503`, incluyendo `Retry-After` si corresponde.
- [ ] Se registra el límite de consultas por token o se marca como pendiente de medir en la prueba integrada.
- [ ] Ignacio confirma disponibilidad del endpoint o mock para el 30/10/2026.
- [ ] Juan confirma que su lado estará listo para probar desde el 02/11/2026.
- [ ] Cada fecha queda etiquetada como compromiso confirmado, objetivo de plan o pendiente.
- [ ] La evidencia de decisión se registra sin secretos, PII ni datos privados.

## 5. Semántica propuesta para discutir (no acuerdo vigente)

Para que la reunión produzca decisiones operables, Juan puede llevar estas reglas
como propuesta explícita. Hasta que Ignacio las confirme y queden en el OpenAPI,
su estado es `PROPUESTA_NO_ACORDADA`.

1. **Idempotencia:** `Idempotency-Key` identifica una intención de aporte durante
   la ventana de retención acordada. Misma clave y misma huella de request deben
   devolver el mismo resultado lógico; misma clave con huella distinta debe
   rechazarse como conflicto. La repetición no crea un segundo registro.
2. **Precisión temporal:** la fecha mostrada por A1 no puede tener mayor precisión
   que `precision_fecha`; un rango `mes`, `anio` o `decada` se mantiene como
   rango o texto temporal equivalente.
3. **Trazabilidad:** `fragmento_id` identifica el pasaje, `pieza_id` el documento,
   y `ubicacion` permite recuperar el lugar interno cuando existe. La URL no
   reemplaza al identificador estable del pasaje.
4. **Publicación:** un aporte aprobado puede registrarse sin fecha ni URL de
   publicación. Esos campos se completan sólo cuando exista publicación externa,
   o se modela esa transición como estado posterior.
5. **Fuente única:** el OpenAPI canónico se referencia por repositorio, ruta,
   `info.version`, tag/commit y checksum. Los fixtures de A1 se regeneran o
   revisan cuando cambia esa referencia.

## 6. Reparto de acciones y pendientes

| Responsable | Acción necesaria | Evidencia de cierre |
|---|---|---|
| Ignacio / A2 | Publicar o señalar OpenAPI 3.1 canónico; completar schemas, enums, idempotencia y errores | Repo + ruta + `info.version` + tag/commit |
| Ignacio / A2 | Confirmar disponibilidad de endpoint/mock y límites operativos | Confirmación fechada o registro de pendiente |
| Juan / A1 | Sustituir el envelope push `a1.communication_input` y tipos A2 `dato_historico`/`efemeride` por cliente pull | Cambio versionado + tests/mocks derivados |
| Juan / A1 | Incorporar `fragmento_id`, ubicación y `precision_fecha`; retirar expectativa de efeméride redactada | Contratos A1 actualizados + regresiones |
| Juan / A1 | Conservar tipo/canal y admitir aporte aprobado sin datos de publicación | Schema/flujo A1 + prueba de estados |
| Juan / A1 | No hacer retry ciego de `POST`; separar timeout de A2 del presupuesto LLM | Política y prueba de fallo |
| Juan e Ignacio | Alinear fixture válido, fixture inválido y prueba de repetición | Prueba de contrato contra versión fijada |
| Juan e Ignacio | Registrar decisión, disensos y pendientes sin datos privados | Minuta/acta sanitizada versionada |

## 7. Trazabilidad del paquete

| Elemento | Proceso / HU | DoD o control | Evidencia actual | Responsable de aceptación | Estado |
|---|---|---|---|---|---|
| Consulta de fuentes históricas | P4 con origen P7; HU-010/HU-011 | Fuente verificable, metadatos y validación humana | Respuesta de Juan; no integración real | Ignacio/A2 + SEU según corresponda | Preparado |
| Contrato de fragmentos | P7 → P4 | Identidad, ubicación, fecha y cita recuperable | Requisito documentado; falta OpenAPI | Juan e Ignacio | Pendiente |
| Contrato de pieza | P7 → P4 | Respuesta completa para cliente/mock/prueba | Falta schema cerrado | Juan e Ignacio | Pendiente |
| Aporte | P4; salida de A1 hacia A2 | No duplicación, procedencia y estado explícito | A1 tiene precedentes de idempotencia offline | Juan e Ignacio | Pendiente |
| Validación humana | P4 | No publicar/enviar/emitir sin decisión registrada | Política A1 y planes de integración | SEU / responsables institucionales | No sustituida por este paquete |
| Disponibilidad y prueba | Integración S2 | Endpoint/mock y prueba reproducible | Fechas del plan de Juan | Juan e Ignacio | No comprometido |

## 8. Condición de cierre del issue

El issue #17 debe permanecer `ready-for-human` y abierto hasta contar, como mínimo,
con:

1. respuesta o minuta atribuible a Ignacio que confirme, modifique o rechace cada
   punto de la sección 3;
2. OpenAPI 3.1 identificado por repositorio, ruta, versión y tag/commit;
3. schemas cerrados para fragmentos, pieza y aporte, incluidos enums, fechas,
   errores e idempotencia;
4. evidencia de las fechas de disponibilidad/prueba o declaración explícita de
   que siguen pendientes;
5. paquete y evidencia revisados para que no contengan secretos ni datos privados.

La conformidad técnica de los mocks, la existencia de `respuesta-nacho.md` o la
preparación de este documento no equivalen a aceptación de Ignacio ni a validación
institucional. Sin esa evidencia humana, el estado correcto es `PENDIENTE_ACUERDO`.
