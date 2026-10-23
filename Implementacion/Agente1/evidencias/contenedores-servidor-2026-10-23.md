# El Agente 1 en contenedores en el servidor de la facultad

**Fecha:** 2026-10-23. **Host:** `labredesfie` (Docker 29.9.1 vía Portainer CE 2.19.4). **Versión:** 0.5.0 (`agente1-v0.5.0`, manifest `eaf7db5f…bb936`, 204 archivos controlados). **Tickets:** #143, decisión en #124, ADR 0013.

## Resultado

El Agente 1 corre en el servidor como un stack de Portainer que sigue la rama `deploy`. La imagen la publicó el CI al cortar la versión. Desde el contenedor pasan la verificación de integridad, el smoke en vivo y una E2E de gacetilla en vivo con `gemma4:e4b` y la cuenta de servicio. Ollama corre en su propio contenedor, sin salida a internet. El runtime venv sigue intacto en paralelo y el scheduler del contenedor está apagado.

## Cadena de despliegue

| Paso | Evidencia |
|---|---|
| CI en `main` (`agente1-imagen`) | Suite y linter dentro de la imagen y contrato del runtime: verde |
| CI completo (`agente1-ci`) | Verde sobre el merge `7c0d5a4` |
| Tag `agente1-v0.5.0` | Publicó `ghcr.io/spendice/agente1@sha256:f003507c665ffa2a77b6bcdfaa66865705e79fff0b2e16dbd57811c777286c2d` (pull anónimo OK) y escribió `compose.yaml` en `deploy` |
| Portainer | Stack `agente1` desde `refs/heads/deploy`, polling cada 5 minutos con *re-pull image* (job 1) |

Antes del push se validó todo en la laptop:
- **Suite:** en la imagen, 2429 pasan y 19 se saltean; los salteados extra son los que necesitan git o `Documentos/`, que corren en `agente1-ci`. En el host, 2440 pasan.
- **Imagen:** 179 MB, uid 10001.
- **Integridad:** si se altera un archivo controlado, el contenedor no arranca (salida 2) y queda una línea `FAIL` en `integridad-arranque.jsonl`.
- **Relay:** llega a Ollama 0.40.6.
- **Egreso:** Ollama no tiene salida a internet y la consola sí llega a Google.
- **Secretos:** `docker inspect` muestra sólo la ruta del env file, ningún valor.

## Contenedores en el servidor

| Servicio | Estado | Aislamiento |
|---|---|---|
| `agente1-ollama-1` | `healthy` | `ollama/ollama:0.40.6` por digest; red `modelo` interna; modelos montados en sólo lectura desde `~/.ollama/models` |
| `agente1-consola-1` | `running` | Imagen por digest; uid 1003; `read_only`, `cap_drop: ALL`, `no-new-privileges`; config en sólo lectura; publicada sólo en `127.0.0.1:8090` |
| `scheduler` | no creado | Perfil `scheduler`, apagado durante la marcha en paralelo |

## Corridas desde el contenedor (23/10)

Se ejecutaron con `exec` en `agente1-consola-1`, por la API de Portainer.

**Integridad al arrancar:** `PASS`, versión 0.5.0, 204 archivos, manifest `eaf7db5f4c6cfab6cb1792adc1f9c2f14a6ebaf7cada65d72c42ace5d1bfb936`.

**Smoke en vivo:**

```
python scripts/contenedor_entrypoint.py smoke --live --id-solicitud FIE-DIF-08
{"ambiente": "D2", "correlation_id": "e4c4b1f8-7c23-490a-819b-f7e4f63939c3", "modo": "live_read_only", "resultado": "lectura_confirmada"}
```

**E2E de gacetilla en vivo:**

```
python scripts/contenedor_entrypoint.py e2e --live --confirm-write-workspace --tipo gacetilla \
  --id-solicitud FIE-DIF-08 --salida /state/evidencia/e2e-gacetilla-2026-10-23 \
  --modelo gemma4:e4b --timeout-modelo 300
{"correlation_id": "b8622f79-3c97-4806-8e7a-705122e2058d", "duplicada": false, "estado": "PENDIENTE_VALIDACION", "modo": "live_write_opt_in", "reconciliation_required": false}
```

Auditoría de la corrida: `resultado: borrador_generado`, `modelo: gemma4:e4b`, `latencia_s: 57.4` (primer pedido al Ollama del contenedor), `destination_type: google_drive_template`, `version_agente: 0.5.0`. Los tokens se emitieron con la cuenta de servicio: tres registros `emitido` en `cuenta-suplantada.jsonl`, con la cuenta por hash. No se publicó, compartió ni envió nada.

**Modelo:** `gemma4:e4b`, digest `dc35e8d9c6061baa…`, servido por Ollama 0.40.6.

**Ollama sin egreso, en el servidor:**

```
bash -c 'echo > /dev/tcp/1.1.1.1/443'   →  Network is unreachable
getent hosts ollama.com                 →  sin resolución
```

Los logs y el borrador local quedan en `~/p100/estado-contenedor/` del servidor. No se versionan porque tienen ids de recursos.

## Pendiente

- **Volver atrás:** probar el retorno a una imagen anterior. Falta una segunda versión cortada para hacerlo.
- **Respaldo y restauración desde el contenedor (ADR 0009):** sin probar.
- **Scheduler:** el cambio de runtime y el encendido del perfil `scheduler` se deciden con esta evidencia. Hasta entonces el venv sigue siendo el camino de la demo.
- **Dos Ollama en el host durante la marcha en paralelo:** entran en memoria, pero compiten por CPU si se usan a la vez.
