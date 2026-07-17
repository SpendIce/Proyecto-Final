# Agente 1 — slice controlado de HU-010

Este directorio inicia la implementación del Agente 1 con el primer tracer bullet del Sprint 1 del Gantt semanal: generar una gacetilla a partir de datos estructurados, sin publicar ni enviar contenido.

El alcance actual es deliberadamente local y reproducible:

- CSV sintético como adapter temporal del futuro ingreso desde Google Sheets.
- Generador fake determinista como seam del futuro LLM local.
- Markdown como evidencia temporal de la futura salida en Google Docs.
- Estado `PENDIENTE_VALIDACION` y encabezado `BORRADOR — NO PUBLICAR` en toda salida exitosa.
- Rechazo previo a la generación cuando falta un campo obligatorio.
- Rechazo de identificadores fuera de la allowlist antes de resolver paths de salida.
- Estado `FALLIDA` sin borrador cuando el generador falla o devuelve contenido vacío.
- Auditoría JSONL con correlation ID, hashes, versión de prompt, modelo y latencia, sin copiar datos fuente ni contenido generado.

Esto valida el flujo y sus controles, pero **no completa el DoD institucional de HU-010**: todavía faltan los adapters de Google Sheets/Docs, la plantilla institucional definitiva y la validación de la SEU prevista en el Gantt.

## Estructura

- `data/actividades_sinteticas.csv`: dataset ficticio de tres filas; incluye casos completo, incompleto y con campo opcional ausente.
- `src/agente1/prompts/gacetilla_v1.txt`: prompt versionado que prohíbe inventar, aprobar, publicar o enviar.
- `golden/SYN-001.md`: salida esperada del generador fake para regresión.
- `tests/`: contrato público del procesador y de la CLI.
- `scripts/smoke.sh`: ejecución end-to-end local contra dataset y golden.
- `salida/`: evidencia runtime local ignorada por Git.

## Ejecutar las pruebas

Desde este directorio:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache python -m pytest -q
```

## Ejecutar el smoke

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache bash scripts/smoke.sh
```

La CLI imprime un JSON con estado, correlation ID y paths de evidencia. Un caso válido debe finalizar en `PENDIENTE_VALIDACION`; uno incompleto finaliza en `INCOMPLETA`, retorna código 2, no invoca al generador y no crea un borrador. Una falla o salida vacía del generador finaliza en `FALLIDA`, retorna código 2 y tampoco crea borrador.

Un identificador rechazado o una solicitud inexistente finaliza en `INVALIDA` con un error genérico y código 2, sin traceback. Esos casos no generan audit log: el sistema todavía no aceptó una solicitud ni asignó correlation ID, y el mensaje evita copiar el identificador o el path consultado.

## Próximo incremento según el Gantt

Manteniendo este contrato y sus pruebas, el siguiente slice debe reemplazar un límite por vez: primero el adapter de lectura desde Google Sheets, después la plantilla/salida controlada en Google Docs. La validación humana y el registro de esa decisión siguen siendo obligatorios antes de considerar cumplido el DoD.
