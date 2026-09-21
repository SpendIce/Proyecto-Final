# Cliente Historia Viva — Límites del slice offline

**Estado institucional:** PENDIENTE
**Estado técnico:** cliente contractual offline, provisional.
**Contrato:** `historia_viva_cliente_candidate_v1` (`CANDIDATO_NO_INSTITUCIONAL`), posición unilateral de A1 pendiente de acuerdo en el issue #17.

## Qué demuestra

- Semántica pull completa del puerto `HistoriaViva`: A1 inicia las tres operaciones (buscar fragmentos, ampliar pieza, registrar aporte) y no existe superficie de entrada: sin callbacks, webhooks ni cola.
- Validación de respuestas crudas contra `contracts/historia_viva_cliente_candidate_v1.schema.json`: se exige `fragmento_id`, `precision_fecha` declarada y los campos citables; un campo extra o faltante, una versión distinta del marcador `schema` o un estado de aporte que no sea `PENDIENTE_VALIDACION` se rechazan con `historia_viva_response_invalid`.
- El cliente nunca completa ni inventa el dato que faltó: una respuesta fuera de contrato es una falla del intercambio, no un hueco a rellenar.
- Una consulta sin resultados produce una lista vacía (`200` semántico), no una afirmación.
- La precisión de fecha se conserva como control: con `mes`, `anio` o `decada` el material no se presenta como fecha exacta aunque el cuerpo traiga `desde`/`hasta` precisos.
- Idempotencia de aportes según la semántica propuesta en el paquete de cierre (`PROPUESTA_NO_ACORDADA`): misma clave y mismo payload devuelven el mismo `aporte_id` con `duplicado`; misma clave con payload distinto es conflicto; una respuesta perdida tras persistir no crea un segundo aporte.
- Timeout y reintentos como objetos de configuración (`PoliticaCliente`): el presupuesto se declara al transporte por llamada, las consultas idempotentes reintentan ante `rate_limited`/`unavailable` con espera inyectada, y `POST /aportes` no reintenta por default.
- La efeméride se compone del lado de A1 con `componer_material_efemeride`, que funciona sin cambios porque el cliente implementa el puerto tipado.

## Qué no demuestra

- **No hay transporte productivo.** `TransporteHistoriaViva` es un protocolo; el adapter HTTP/REST (URL base, serialización, header `Authorization: Bearer`, mapeo `401`/`403`/`404`/`429`/`503` a códigos, `Idempotency-Key`) queda diferido al acuerdo del issue #17. Ninguna prueba tocó la red.
- **El contrato no está acordado.** Los enums de `tipo` de pieza quedan abiertos a propósito; la deduplicación por `Idempotency-Key`, la forma cerrada de `GET /v1/piezas/{id}` y la opcionalidad de `fecha_publicacion`/`url_publicacion` son propuestas de A1 sin confirmación de A2.
- **Identidad pendiente.** No se probó autenticación, scopes, revocación de tokens ni límites de consultas por token; todo eso depende de la identidad por agente que falta acordar.
- **La deduplicación es del lado del servidor.** El fake la implementa para verificar la semántica esperada; hasta que A2 la confirme, reintentar un aporte permanece deshabilitado por default.
- El timeout se declara al transporte pero no se aplica a un socket real: la medición de latencia y la conducta ante `429`/`503` reales quedan para la prueba integrada.
- No acredita Gate G2 ni TRL 3.

## Fronteras de seguridad

Las respuestas se validan como datos cerrados: `additionalProperties: false` lógico en cada nivel, identificadores acotados por patrón antes de tocar un registro, y errores reducidos al vocabulario de `historia_viva.py` para que ningún mensaje remoto llegue a la auditoría. Una pieza cuyo `pieza_id` no es el pedido se rechaza entera.

Agregar el transporte HTTP requiere cerrar #17 (OpenAPI canónico, tag/commit fijado, idempotencia y enums), gestión de secretos fuera del repo y una regresión de contrato contra la versión acordada.
