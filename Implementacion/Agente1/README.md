# Agente 1 — slice controlado de HU-010

Este directorio inicia la implementación del Agente 1 con el primer tracer bullet del Sprint 1 del Gantt semanal: generar una gacetilla a partir de datos estructurados, sin publicar ni enviar contenido.

El alcance actual es deliberadamente local y reproducible:

- CSV sintético como adapter temporal del futuro ingreso desde Google Sheets.
- Generador fake determinista para regresión y adapter HTTP para Ollama local.
- Markdown como evidencia temporal de la futura salida en Google Docs.
- Estado `PENDIENTE_VALIDACION` y encabezado `BORRADOR — NO PUBLICAR` en toda salida exitosa.
- Rechazo previo a la generación cuando falta un campo obligatorio.
- Rechazo de identificadores fuera de la allowlist antes de resolver paths de salida.
- Estado `FALLIDA` sin borrador cuando el generador falla, devuelve contenido vacío o no cumple el contrato mecánico mínimo.
- Auditoría JSONL con correlation ID, hashes, versiones de contrato/prompt, modelo y latencia, sin copiar datos fuente ni contenido generado.

Esto valida el flujo y sus controles, pero **no completa el DoD institucional de HU-010**: todavía faltan los adapters de Google Sheets/Docs, la plantilla institucional definitiva y la validación de la SEU prevista en el Gantt.

## Estructura

- `data/actividades_sinteticas.csv`: dataset ficticio de cinco filas; incluye tres casos completos, dos incompletos y lugares opcionales ausentes.
- `src/agente1/contracts/gacetilla_input_v1.schema.json`: contrato técnico versionado de los campos actuales, marcado `PROVISIONAL_NO_INSTITUCIONAL`.
- `src/agente1/prompts/gacetilla_v2.txt`: prompt versionado con estructura fija, límites y ejemplo sintético; también está marcado como provisional.
- `golden/SYN-001.md`: salida esperada del generador fake para regresión.
- `tests/`: contrato público del procesador y de la CLI.
- `scripts/smoke.sh`: ejecución end-to-end local contra dataset y golden.
- `scripts/smoke_ollama.sh`: smoke opt-in contra un Ollama ya iniciado y con el modelo descargado.
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

La CLI imprime un JSON con estado, correlation ID y paths de evidencia. Un caso válido debe finalizar en `PENDIENTE_VALIDACION`; uno incompleto finaliza en `INCOMPLETA`, retorna código 2, no invoca al generador y no crea un borrador. Una falla, salida vacía o salida no conforme finaliza en `FALLIDA`, retorna código 2 y tampoco crea borrador.

Un identificador rechazado o una solicitud inexistente finaliza en `INVALIDA` con un error genérico y código 2, sin traceback. Esos casos no generan audit log: el sistema todavía no aceptó una solicitud ni asignó correlation ID, y el mensaje evita copiar el identificador o el path consultado.

## Gate mecánico provisional de salida

Antes de escribir un borrador, un parser anclado exige que el documento comience exactamente en `## TÍTULO`, contenga una sola vez y en orden `TÍTULO → DATOS DE LA ACTIVIDAD → CONTACTO → BAJADA → CUERPO`, y no tenga preámbulo, duplicados ni texto externo. El documento completo no puede superar 5000 caracteres; no se impone un mínimo arbitrario. Los hechos fuente no cuentan para un límite de palabras: BAJADA y CUERPO admiten hasta 12 palabras cada uno; el CUERPO debe ser exactamente una oración y terminar en `.`, `?` o `!`.

Cada hecho etiquetado se compara por igualdad normalizada sólo dentro de su sección: título en TÍTULO; fecha, organización y lugar en DATOS; contacto en CONTACTO. Si la fuente no informa lugar, cualquier línea `Lugar:` queda prohibida; si lo informa, el valor debe coincidir exactamente después de normalizar mayúsculas, espacios y acentos. Una salida no conforme registra códigos cerrados en `validation_errors`, nunca fragmentos rechazados. Este gate sigue sin evaluar tono o verdad semántica.

Este gate sólo evita aceptar basura evidente o pérdida de hechos críticos. NO evalúa tono institucional, claridad, gramática, pertinencia ni verdad semántica; tampoco convierte el formato provisional en plantilla oficial. Esos criterios requieren checklist y validación humana de la SEU antes de aprobar HU-010 o declarar el Gate TRL 3.

## Probar Ollama local

Ollama no está instalado a nivel global del sistema. Sí existe y fue probado el runtime user-local ignorado por Git. Docker está disponible, pero esa vía se descartó para este slice por el peso adicional de imagen, capas y modelo. Para el PoC se fija `llama3.2:3b`: la [ficha oficial de Ollama](https://ollama.com/library/llama3.2:3b) publica un artefacto de 2,0 GB y la variante 3B permite empezar con un host limitado. Ese tamaño corresponde a la descarga del modelo, no garantiza por sí solo un consumo equivalente de RAM.

La preparación del runtime es deliberadamente externa a las pruebas y al build del paquete. Como alternativa user-local, el directorio `.runtime/` está ignorado por Git y puede alojar el ejecutable obtenido de la distribución oficial y los modelos sin contaminar el repositorio:

```bash
mkdir -p .runtime/bin .runtime/models
# Ubicar el ejecutable oficial en .runtime/bin/ollama sin commitearlo.
OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama serve
```

En otra terminal, con el servicio iniciado:

```bash
OLLAMA_MODELS="$PWD/.runtime/models" .runtime/bin/ollama pull llama3.2:3b
```

El binario, sus librerías y los modelos son runtime local: NO deben agregarse a Git. El runtime user-local ya fue probado en este host. Con `llama3.2:3b` sobre CPU, una corrida warm completó en `22.859583 s`, otras generaciones superaron 30 segundos y la carga cold agotó el deadline anterior; el benchmark debe distinguir esos estados. La variante 1B fue rechazada por el gate de la prueba. Estos resultados son evidencia técnica local: no constituyen validación SEU ni habilitan declarar un nivel TRL.

Con el servicio y el modelo listos:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache bash scripts/smoke_ollama.sh
```

La CLI también admite el adapter explícitamente:

```bash
python -m agente1 \
  --csv data/actividades_sinteticas.csv \
  --id-solicitud SYN-001 \
  --salida salida/manual \
  --ollama-model llama3.2:3b \
  --ollama-base-url http://127.0.0.1:11434 \
  --ollama-timeout 45 \
  --ollama-num-predict 112
```

El timeout conserva semántica de deadline total para conexión, envío, headers y cuerpo; un servidor trickle no puede reiniciarlo. La evidencia CPU live mostró generaciones que superan 30 segundos, por lo que el presupuesto operativo usa 45 segundos por defecto y admite configuración entre más de cero y 120 segundos. Este ajuste evita confundir capacidad del host con un corte artificial; no modifica ni declara cumplido un requisito institucional de performance. Puede definirse `OLLAMA_TIMEOUT` en el smoke live. `num_predict` usa 112 por defecto, valor elegido tras el benchmark para permitir un cierre completo con puntuación, y admite valores entre 32 y 512. El valor efectivo queda auditado en cada ejecución Ollama; el fake registra `null`. También puede definirse `OLLAMA_NUM_PREDICT`. Errores HTTP, timeouts o respuestas inválidas terminan como `FALLIDA`: no crean borrador ni exponen prompt, URL o cuerpo remoto en la CLI o el audit log. Por seguridad, el adapter sólo acepta HTTP hacia `localhost`, direcciones `127.0.0.0/8` o `::1`; no admite hosts remotos, HTTPS, credenciales embebidas ni paths adicionales.

El smoke real deja sus resultados en un subdirectorio temporal de `salida/`, ignorado por Git. Verifica controles técnicos; no reemplaza la revisión humana, la validación SEU ni permite declarar cumplido el Gate TRL 3.

## Próximo incremento según el Gantt

Manteniendo este contrato y sus pruebas, el siguiente slice debe reemplazar un límite por vez: primero el adapter de lectura desde Google Sheets, después la plantilla/salida controlada en Google Docs. La validación humana y el registro de esa decisión siguen siendo obligatorios antes de considerar cumplido el DoD. HU-011 debe reutilizar el mismo seam de generación, no adelantarse a esos límites pendientes del Gantt.
