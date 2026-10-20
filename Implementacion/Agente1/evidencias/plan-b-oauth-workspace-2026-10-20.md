# Plan B OAuth: camino Workspace live verificado

**Fecha:** 2026-10-20
**Alcance:** verificar el camino Sheets → Doc con la credencial OAuth anterior, antes de la demo del 21/10.
**Resultado:** smoke live `lectura_confirmada`; corrida completa del wrapper 6/6 con un **stub de Ollama**; E2E `PENDIENTE_VALIDACION`.
**Límite principal:** el modelo real se prueba en el servidor con `gemma4:e4b`; esta evidencia acredita el camino de Workspace, no la calidad del modelo.

## Qué se armó

- Una planilla D2 v2 sintética, con el encabezado exacto de `COLUMNAS_ACTIVIDADES_V2` y las filas `SYN-001` y `SYN-002`.
- El entorno Plan B queda fuera del repo, en `~/.config/agente1/workspace-d2-planb.env` (chmod 600). Trae el trío OAuth, la hoja v2, la carpeta y la plantilla.
- El wrapper `Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh` carga ese entorno, borra el par de la cuenta de servicio y el access token efímero, y corre el comando pedido.
- El preflight de `corrida_unica.py` acepta el trío OAuth como credencial de contingencia y tiene un test propio.

## Corridas

### Smoke live de lectura

```bash
bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh --check
```

Resultado del smoke:

```json
{"ambiente": "D2", "correlation_id": "f3616407-7c73-4b64-be8d-0d5a7f3a80de", "modo": "live_read_only", "resultado": "lectura_confirmada"}
```

El dry-run previo del preflight también pasó, con `credencial: trío OAuth anterior completo (Plan B)`.

### E2E live con stub de Ollama

Se corrió el CLI real, con Sheets y Docs reales y un stub HTTP en `127.0.0.1:11434` que devuelve una ficha válida. El stub no es el modelo de la demo; su único fin es ejercitar el mismo camino del CLI sin depender del servidor.

```bash
uv run python scripts/workspace_e2e.py \
  --live --confirm-write-workspace \
  --tipo gacetilla --id-solicitud SYN-002 \
  --salida /tmp/opencode/e2e-cli-planb2 \
  --modelo gemma4:e4b
```

Resultado:

```json
{"correlation_id": "67ccebf0-6309-42bc-89ed-6c3a63e49b4d", "duplicada": false, "estado": "PENDIENTE_VALIDACION", "modo": "live_write_opt_in", "reconciliation_required": false}
```

El manifest registra `destination_type: google_drive_template`, `output_hash: 4d90674d183899d7f325397baafa33c04a444fb069cc372438985e85af2a63bc` y `resultado: borrador_generado`.

### Corrida completa del wrapper

Con el mismo stub se corrió el comando que mañana se usa en el servidor:

```bash
bash scripts/corrida_plan_b_oauth.sh
```

Resultado: **6/6 pasos**.

- Preflight: `credencial: trío OAuth anterior completo (Plan B)`.
- Ollama: 0.40.6 y `gemma4:e4b` (el stub imita `/api/version`, `/api/tags` y `/api/generate`).
- Smoke: `lectura_confirmada` (`1894f377-6f1a-4bf8-99f7-2fac97119cf8`).
- Gacetilla: `PENDIENTE_VALIDACION` (`9ca76777-bbf1-41e9-a6a1-9ea110821e1d`), con borrador en Drive.
- HU-014: `EMITIDA`, 2 certificados entregados en modo offline.
- HU-012: `ENVIO_ENCOLADO`, 3 correos simulados con `BORRADOR — NO ENVIAR`.

El stub no es el modelo de la demo. La corrida real con `gemma4:e4b` en `labredesfie` es el paso que queda; el resto del wrapper (OAuth, Sheets, Docs, HU-014 y HU-012) quedó ejercitado.

### Documento creado

En la carpeta `Agentes` quedó el documento `BORRADOR — Fie informa 20-10 Taller sintético de vinculación (demo)`. La exportación a texto verificó:

- encabezado `BORRADOR — NO PUBLICAR`;
- asunto y bajada sintéticos;
- fecha, organiza, lugar y contacto tomados de la fila;
- pie institucional y aviso de plantilla provisional D2.

No se compartió, publicó ni envió nada.

## Límites

- **El modelo no es real.** La corrida completa del wrapper usó un stub; el modelo `gemma4:e4b` se prueba en `labredesfie` con el mismo wrapper.
- **La hoja no es la de producción.** Es una hoja v2 sintética; la hoja de producción y la cuenta de servicio siguen en #99.
- **La identidad OAuth se retira.** Es una contingencia declarada, no la identidad objetivo (ADR 0011).
- **No hay validación SEU.** El documento queda en `PENDIENTE_VALIDACION` y con la marca de borrador.
- **No se probó la revocación** ni el traspaso de credenciales.

## Reproducir

1. Copiar `~/.config/agente1/workspace-d2-planb.env` al servidor, fuera del repo, con chmod 600.
2. En el servidor, desde el repo:

```bash
bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh --check
bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh
```

El primer comando no escribe; el segundo corre la demo completa con `gemma4:e4b`. Si el modelo no cumple el contrato, el gate rechaza y no se publica.
