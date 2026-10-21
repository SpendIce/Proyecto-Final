# Plan B OAuth: E2E live con modelo real y actividad real

**Fecha:** 2026-10-20, actualizado el 2026-10-21.
**Alcance:** verificar el camino Sheets → agente → Doc con la cuenta de servicio (Plan A) y con OAuth (Plan B), el modelo `gemma4:e4b` y una actividad real del corpus FIE INFORMA sobre la hoja v2.
**Resultado:** Plan A con cuenta de servicio **6/6**; Plan B con OAuth `PENDIENTE_VALIDACION`; consola visual con cuenta de servicio; borrador en Drive.
**Límite principal:** la hoja v2 es sintética y la hoja de producción real de la SEU sigue en #99. No hay validación SEU.

## Qué se armó

- Una planilla D2 v2 sintética, con el encabezado exacto de `COLUMNAS_ACTIVIDADES_V2` y las filas `SYN-001`, `SYN-002` y `FIE-DIF-08`.
- El `workspace-d2.env` del servidor se actualizó el 21/10 para apuntar a la hoja v2 (`Actividades!A1:O100`). Quedó un backup `workspace-d2.env.bak-20261021`; la vieja hoja v1 `Solicitudes` no se tocó.
- La fila `FIE-DIF-08` sale de `data/corpus-fie-informa-difusiones.csv`: Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional. Es una actividad real del corpus FIE INFORMA, no un texto inventado para la prueba.
- El entorno Plan B queda fuera del repo, en `~/.config/agente1/workspace-d2-planb.env` (chmod 600). Trae el trío OAuth, la hoja v2, la carpeta y la plantilla.
- El wrapper `Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh` carga ese entorno, quita del proceso el par de la cuenta de servicio y el access token efímero, y corre el comando pedido. No borra ni modifica `workspace-d2.env` ni `cuenta-servicio.json`: el par sigue en el servidor para Plan A.
- La consola visual tiene dos launchers: `demo_visual_plan_a.sh` para la cuenta de servicio y `demo_visual_plan_b.sh` para OAuth. El modo se elige con `AGENTE1_DEMO_AUTH`; la UI no muestra la credencial.
- El preflight de `corrida_unica.py` acepta el trío OAuth como credencial de contingencia y tiene un test propio.
- La consola visual `scripts/demo_visual_plan_b.py`, con su launcher `scripts/demo_visual_plan_b.sh` y el orquestador `run-demo-planb.sh`, que corre desde la laptop por Tailscale.

## Correcciones que salieron de la prueba

- **`think=false` en el CLI live.** La primera corrida real falló con `error_generacion` después de 169,9 s. El adaptador `OllamaGenerator` no recibía `think=False` en `workspace_e2e.py`, aunque la configuración congelada de `gemma4:e4b` sí lo pide. Se agregó `think=False` y la corrida siguiente terminó bien.
- **Techo de 300 s.** La corrida en frío del modelo llegó al límite de 180 s. Se agregó `--timeout-modelo` y la demo usa 300 s de techo; el modelo caliente resolvió en 41,9 s y 57,9 s. El `num_predict` sigue en 512 y el modelo no cambió.
- **Túnel SSH.** El alias `fie-server-ts` usa Tailscale y funciona fuera de la red de la FIE. El túnel de la consola se abre con `ControlMaster=no` para que no lo absorba la conexión maestra y el servidor no quede huérfano.

## Corridas

### Plan A: cuenta de servicio sobre la hoja v2

```bash
.venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08
```

Resultado:

```json
{"ambiente": "D2", "correlation_id": "585afd71-3e90-4e59-a72e-5d8e559091a3", "modo": "live_read_only", "resultado": "lectura_confirmada"}
```

Corrida completa con la cuenta de servicio:

```bash
.venv/bin/python scripts/corrida_unica.py --live --modelo gemma4:e4b \
  --id-solicitud FIE-DIF-08 --timeout-modelo 300
```

Resultado: **6/6**. La gacetilla dio `PENDIENTE_VALIDACION` en 64,2 s (`correlation_id 4974bc3b-b3dd-4be4-b52c-99b796db3c31`); HU-014 emitió 2 certificados y HU-012 encoló 3 correos simulados. No se publicó nada.

La consola visual con cuenta de servicio se abrió por `http://127.0.0.1:8080` y se envió el formulario con la actividad real. Generó `BORRADOR — Fie informa 21-10 Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional` y mostró el texto en la vista previa. El `run_id` fue `73cfea1057`.

### Plan B: OAuth

```bash
.venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08
```

Resultado:

```json
{"ambiente": "D2", "correlation_id": "bc14a5e3-1b78-4dc1-8e55-5bf754c3fc2b", "modo": "live_read_only", "resultado": "lectura_confirmada"}
```

### E2E real con `gemma4:e4b` (Plan B OAuth)

```bash
.venv/bin/python scripts/workspace_e2e.py \
  --live --confirm-write-workspace \
  --tipo gacetilla --id-solicitud FIE-DIF-08 \
  --salida /tmp/demo-e2e-fie-dif-08-thinkfalse \
  --modelo gemma4:e4b --timeout-modelo 300
```

Resultado:

```json
{"correlation_id": "f27501d9-7d75-42c4-a2b4-d9d4ee0d9fcc", "duplicada": false, "estado": "PENDIENTE_VALIDACION", "modo": "live_write_opt_in", "reconciliation_required": false}
```

El registro de la corrida dejó `latencia_s: 57.9`, `output_hash: df8e9be983e098af0fd5f4f12958eaa4373ececc0a02c0d6dd11b865d3953a56`, `destination_type: google_drive_template` y `resultado: borrador_generado`.

### Consola visual con el modelo real

La consola se abrió desde la laptop por `http://127.0.0.1:8080`, con túnel a `labredesfie`. El formulario se envió con la actividad real y una fila nueva `DEMO-20261020-235318-7dd1`. El agente generó el borrador:

```json
{"correlation_id": "dfd9e049-a905-4b17-8777-5e8a5c8a5e5d", "estado": "PENDIENTE_VALIDACION", "id_solicitud": "DEMO-20261020-235318-7dd1", "latencia_s": 41.9, "modelo": "gemma4:e4b"}
```

La consola mostró los cuatro pasos: formulario enviado, planilla actualizada, agente generando y borrador listo. El botón «Ver gacetilla» exportó el documento desde el servidor y mostró el texto. No se publicó, compartió ni envió nada.

### Documento creado

En la carpeta `Agentes` quedó `BORRADOR — Fie informa 20-10 Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional`. La exportación a texto verificó:

- encabezado `BORRADOR — NO PUBLICAR`;
- asunto, bajada y cuerpo con la actividad real;
- fecha, finalización, hora, modalidad, organiza y contacto tomados de la fila;
- pie institucional y aviso de plantilla provisional D2.

No se compartió, publicó ni envió nada.

### Prueba previa con stub

Antes de usar el modelo real se corrió la misma consola con un stub de Ollama en loopback. Sirvió para verificar el formulario, la planilla, la generación del documento y la vista previa sin depender del tiempo de carga del modelo. Esa corrida no acredita calidad de prosa; la corrida que sí la acredita es la de `gemma4:e4b`.

## Límites

- **La hoja no es la de producción.** Es una hoja v2 sintética con una actividad real del corpus; la hoja de producción real de la SEU sigue en #99.
- **Plan A funciona; Plan B es respaldo.** La cuenta de servicio leyó y escribió la hoja v2; el par y la clave no se tocaron. OAuth queda como contingencia declarada (ADR 0011), no como identidad objetivo.
- **No hay validación SEU.** El documento queda en `PENDIENTE_VALIDACION` y con la marca de borrador.
- **No se probó la revocación** ni el traspaso de credenciales.
- **El modelo real se probó en caliente.** La primera corrida en frío necesitó el techo de 300 s y `think=false`; la configuración de la demo usa esos valores. La corrida con cuenta de servicio dio 64,2 s y la de OAuth 57,9 s.

## Reproducir

1. Plan A: el `workspace-d2.env` del servidor ya apunta a la hoja v2 y tiene el par de la cuenta de servicio. En la laptop, con Tailscale activo:

```bash
./run-demo-plan-a.sh
```

El script verifica `fie-server-ts`, actualiza el repo, corre el preflight y el smoke con la cuenta de servicio, levanta la consola y abre el navegador. `Ctrl-C` corta el túnel y la consola.

2. Plan B, si la cuenta de servicio falla:

```bash
./run-demo-planb.sh
```

El script copia el overlay OAuth, actualiza el repo, corre el `--check` y levanta la consola OAuth. No toca la cuenta de servicio.

Sin consola, el camino headless del Plan A es:

```bash
.venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08
.venv/bin/python scripts/corrida_unica.py --live --modelo gemma4:e4b --id-solicitud FIE-DIF-08 --timeout-modelo 300
```

El primer comando no escribe; el segundo corre la demo completa con `gemma4:e4b`. Si el modelo no cumple el contrato, el gate rechaza y no se publica.
