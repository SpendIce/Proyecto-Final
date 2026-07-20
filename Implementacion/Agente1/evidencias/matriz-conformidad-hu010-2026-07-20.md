# Matriz de conformidad contractual simulada — HU-010

## Alcance

El 20 de julio de 2026 se ejecutaron las cinco filas del dataset sintético con
el generador fake determinista. La corrida verifica el contrato de entrada, el
gate mecánico de salida, los estados del pipeline, la creación o ausencia de
borradores y la trazabilidad por hashes.

Esta evidencia **no evalúa generación LLM, calidad institucional, tono, verdad
semántica ni performance**. Tampoco registra revisión humana o de la SEU y no
acredita TRL 3.

## Resultado

| Caso | Perfil contractual | Estado observado | Resultado | Borrador | Revisión humana |
| --- | --- | --- | --- | --- | --- |
| `SYN-001` | Completo con lugar | `PENDIENTE_VALIDACION` | `borrador_generado` | Sí; coincide con golden | `PENDIENTE` |
| `SYN-002` | Sin contacto obligatorio | `INCOMPLETA` | `datos_incompletos` | No | No aplica hasta generar |
| `SYN-003` | Completo sin lugar opcional | `PENDIENTE_VALIDACION` | `borrador_generado` | Sí; coincide con golden | `PENDIENTE` |
| `SYN-004` | Sin fecha obligatoria | `INCOMPLETA` | `datos_incompletos` | No | No aplica hasta generar |
| `SYN-005` | Completo remoto sin lugar opcional | `PENDIENTE_VALIDACION` | `borrador_generado` | Sí; coincide con golden | `PENDIENTE` |

Totales: cinco casos ejecutados, tres borradores en
`PENDIENTE_VALIDACION` y dos solicitudes `INCOMPLETA`. El origen de todos los
datos es `SIMULADA`; `institutional_quality_assessed` y `trl3_claimed` quedan
en `false`.

## Trazabilidad de la corrida

- Base Git: `dbf3bbfae2c4a2d90c01ba0b8e1020f57e1821c5`.
- El scope de implementación no coincidía con esa base porque la matriz, sus
  goldens y sus pruebas todavía eran cambios sin commit.
- Dataset SHA-256: `fe5d712f5f41e777b5daa02ac1de0b23bfde64e0cc61433d9a89d3c0977d98f4`.
- Prompt SHA-256: `04c71756e59b3263c4eced6976120c32feccf07b740130833aaf2f5126dbff5d`.
- Contrato SHA-256: `530f383933d7fe1738526108faa3eef24a31e30fa50fcea4d6e5940ed48d8cd5`.
- Runner SHA-256: `8c8efadf6167387a798e440745872201a2a8a0908b8433bf66767ac5825cd136`.
- Resumen runtime seguro: `salida/matriz-hu010-2026-07-20/matriz.json`
  (ignorado por Git).

| Caso | Correlation ID | Input SHA-256 | Output/golden SHA-256 |
| --- | --- | --- | --- |
| `SYN-001` | `8f44af52-e5a1-45be-82cd-d0b0421be51b` | `d4971497e1f6db200ba6005e562b42313dab9637ae6ec8476a6f9c10b115e38e` | `87507e0af268cd529850e5140b825b5c432f8757753af8c4f6183932b265bd16` |
| `SYN-002` | `680aab0f-1949-4ac1-a06f-03cdb1c2fab9` | `792f2b1904117a313755cdc93ef571d44313aace96a75891d67ceb6b9a0f1249` | No aplica |
| `SYN-003` | `12b0d813-675b-41f3-a86c-053315bbc316` | `73889a1521c41d473749b7e6e5e26f893113295887e9ce4cee91acae666974d0` | `e833630acf3ecd9731d29dc5515e5a256511def6168584e71118186ac8603e2b` |
| `SYN-004` | `09b5b8ce-f645-4f0d-a315-2b62530c47ba` | `2951bc1c47fb24a126245dd7c1aeba0c5c635853f547bca2dbb75c03c65aab37` | No aplica |
| `SYN-005` | `2e82d782-78cd-4c7b-8fec-9e688972d0cf` | `e24f57881c5e3f413886e55d20baf27d0815155b015f621ee34ddd5b3449355c` | `fae2dfb3beccc52262ad178b245e660aade5420b4a0f62b9287b30b644463a0f` |

Los tres borradores deben evaluarse individualmente con
`checklist-validacion-humana-hu010.md`. Hasta que una persona responsable
complete puntajes, observaciones, fecha y decisión, permanecen pendientes. El
manifest de Ollama `manifest-hu010-syn001.json` corresponde a otro experimento
y no se reutiliza como evidencia de esta matriz contractual.
