# Contrato `/v1` de Historia Viva — prueba contra el mock (2026-10-13)

**Issues:** #12 (consultas HTTP), #13 (aportes idempotentes), #17 (contrato con Ignacio).
**Contrato:** `openapi-agentes.yaml` 1.1.0-rc1 del paquete `contratojuan` (Ignacio Becerra, commit `ce599d3`), huella
`2af852e591ede5701adf7599be69d992fe6112d55fc44459e71feab9f8c60d7b`. Borrador hasta el congelado del 30/10.
**Estado institucional:** PENDIENTE (el contrato no está congelado ni hubo sesión presencial).
**Estado técnico:** cliente y transporte implementados y probados contra el mock; sin prueba contra la API real.

## Qué se corrió

1. `node ejecutar-contrato.mjs` del paquete de Ignacio: levanta Prism 5.16.0, comprueba los 57 escenarios del mock y corre
   el cliente del Agente 1 con `cliente.comando`
   (`.venv/bin/python -m pytest -v -p no:cacheprovider contrato/test_contrato_hv_v1.py`). Resultado:
   `RESULTADO-2026-10-13.md`, **Veredicto PASA**, 57/57 escenarios, 39/39 casos del cliente.
2. `scripts/post_efemeride_demo.py` en modo Historia Viva (`AGENTE1_HV_BASE_URL` al mock, token de mentira en un archivo
   fuera del repo con permisos `600`, `--procedencia synthetic_test`, consulta abril de 2016):

| Escenario (`--hv-escenario`) | Estado | Motivo |
| --- | --- | --- |
| `code=200, example=precisionRango` | `PENDIENTE_VALIDACION` | Borrador con cita `pza_… / frg_…, p. 12, Capítulo 3 — Convenios (entre 2015 y 2019)` |
| `code=200, example=conResultados` | `FALLIDA` | `length_out_of_range`: tres fragmentos largos superan los 1000 caracteres de Instagram (también tras el reintento) |
| `code=200, example=sinResultados` | `INCOMPLETA` | `material_insuficiente`, sin invocar al generador |
| `code=401, example=tokenInvalido` | `FALLIDA` | Falla de consulta, sin reintento |
| `code=503, example=pausado` | `FALLIDA` | `Retry-After: 300` supera el tope de 30 s: no se espera |

La auditoría registra `hv_contract_version = historia_viva_v1_1.1.0-rc1`.

## Qué demuestra

- El cliente decodifica las formas cerradas de `/v1` (`RespuestaFragmentos`, `Fragmento`, `Pieza`, `AporteCreado`) y
  rechaza todo lo demás con `historia_viva_response_invalid`.
- `rango`, los tipos nuevos (`plano`, `planilla`, `video`, `nota`) y `pagina`/`seccion` nulos se aceptan; la ubicación
  de la cita sale de `pagina` y `seccion`.
- Se decide por `codigo`; ningún `4xx` se reintenta; `429` espera `Retry-After`; el 422 de C48 es definitivo.
- El token sale de un archivo fuera de todo repo git, no legible por otros, y se relee en cada pedido.
- Los aportes llevan `Idempotency-Key`; `201` y `200` se distinguen; el acuse de otra clave se rechaza.

## Qué no demuestra

- **Nada contra la API real.** Prism no guarda estado: idempotencia real, cupos, rotación de token, el 422 por contenido y
  `X-Solicitud-Id` igual a `solicitud_id` quedan para la sesión presencial con Ignacio (#17).
- **El contrato no está acordado.** Las respuestas de `PREGUNTAS-2026-10-13.md` son la posición de A1; los pedidos de
  `PEDIDOS-AGENTE1-2026-10-13.md` esperan respuesta.
- **El post de efeméride con varios fragmentos falla por largo.** Ver el issue abierto desde esta corrida sobre cuántos
  fragmentos cita un post de efeméride y cómo se eligen.
- El generador del recorrido es `FakeGenerator`; no se midió el modelo local sobre material de Historia Viva.
