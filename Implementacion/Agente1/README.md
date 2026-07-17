# Agente 1 — slice controlado de HU-010

Este directorio inicia la implementación del Agente 1 con el primer tracer bullet del Sprint 1 del Gantt semanal: generar una gacetilla a partir de datos estructurados, sin publicar ni enviar contenido.

El alcance actual es deliberadamente local y reproducible:

- CSV sintético como adapter temporal del futuro ingreso desde Google Sheets.
- Generador fake determinista para regresión y adapter HTTP para Ollama local.
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

La CLI imprime un JSON con estado, correlation ID y paths de evidencia. Un caso válido debe finalizar en `PENDIENTE_VALIDACION`; uno incompleto finaliza en `INCOMPLETA`, retorna código 2, no invoca al generador y no crea un borrador. Una falla o salida vacía del generador finaliza en `FALLIDA`, retorna código 2 y tampoco crea borrador.

Un identificador rechazado o una solicitud inexistente finaliza en `INVALIDA` con un error genérico y código 2, sin traceback. Esos casos no generan audit log: el sistema todavía no aceptó una solicitud ni asignó correlation ID, y el mensaje evita copiar el identificador o el path consultado.

## Probar Ollama local

Ollama todavía no está instalado en este host. Docker está disponible, pero esa vía se descartó para este slice por el peso adicional de imagen, capas y modelo. Para el PoC se fija `llama3.2:3b`: la [ficha oficial de Ollama](https://ollama.com/library/llama3.2:3b) publica un artefacto de 2,0 GB y la variante 3B permite empezar con un host limitado. Ese tamaño corresponde a la descarga del modelo, no garantiza por sí solo un consumo equivalente de RAM.

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

El binario, sus librerías y los modelos son runtime local: NO deben agregarse a Git. La descarga o instalación queda como paso operativo explícito porque todavía debe verificarse arquitectura, espacio y memoria disponibles en el host.

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
  --ollama-timeout 25
```

El timeout debe ser mayor que cero y no puede superar los 30 segundos del requisito de performance. Se aplica como deadline total a conexión, envío, recepción de headers y lectura completa del cuerpo; un servidor que entregue bytes lentamente no puede reiniciarlo. Errores HTTP, timeouts o respuestas inválidas terminan como `FALLIDA`: no crean borrador ni exponen prompt, URL o cuerpo remoto en la CLI o el audit log. Por seguridad, el adapter sólo acepta HTTP hacia `localhost`, direcciones `127.0.0.0/8` o `::1`; no admite hosts remotos, HTTPS, credenciales embebidas ni paths adicionales.

El smoke real deja sus resultados en un subdirectorio temporal de `salida/`, ignorado por Git. Verifica controles técnicos; no reemplaza la revisión humana, la validación SEU ni permite declarar cumplido el Gate TRL 3.

## Próximo incremento según el Gantt

Manteniendo este contrato y sus pruebas, el siguiente slice debe reemplazar un límite por vez: primero el adapter de lectura desde Google Sheets, después la plantilla/salida controlada en Google Docs. La validación humana y el registro de esa decisión siguen siendo obligatorios antes de considerar cumplido el DoD. HU-011 debe reutilizar el mismo seam de generación, no adelantarse a esos límites pendientes del Gantt.
