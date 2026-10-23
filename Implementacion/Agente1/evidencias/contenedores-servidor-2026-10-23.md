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

## Corte oficial (23/10, versión 0.5.3)

Después de la primera prueba se hicieron todas las verificaciones que faltaban y el contenedor pasó a ser el runtime oficial. En el camino aparecieron tres problemas, que se corrigieron como versiones nuevas desplegadas por la misma cadena:
- **0.5.1:** la corrida única sin `.git` y con el código de sólo lectura.
- **0.5.2:** faltaba `golden/` en la imagen, y por eso HU-012 fallaba con `runner_unavailable`.
- **0.5.3:** el scheduler pedía el modelo con razonamiento y agotaba el tiempo.

Cada versión la desplegó Portainer solo, por polling, en menos de 5 minutos después de que el CI escribió `deploy`.

| Prueba (dentro del contenedor del servidor) | Versión | Resultado |
|---|---|---|
| Corrida única completa (`corrida_unica.py --live`) | 0.5.2 | Preflight OK; Ollama 0.40.6 con `gemma4:e4b`; smoke `lectura_confirmada`; gacetilla `DUPLICADA` (el registro de idempotencia la tenía, no se creó otro documento); **HU-014** con línea aprobada por los dos roles, lote aprobado y 2 certificados `EMITIDA` (offline); **HU-012/HU-013** con el canal que clasifica `generar_plantilla_actividad`, tres aprobaciones y lote `ENVIO_ENCOLADO` con 3 entregas simuladas |
| **HU-011** post de Instagram en vivo | 0.5.2 | `PENDIENTE_VALIDACION`, 77,6 s, `post_instagram_structured_v6`, segundo intento del reintento acotado |
| **HU-011** post de LinkedIn en vivo | 0.5.2 | Primer intento `source_failure` en 1 s (falla transitoria de lectura de la planilla, el modelo no llegó a correr); al reintentar, `PENDIENTE_VALIDACION`, 72,3 s, `post_linkedin_structured_v6` |
| Modelo en HU-014, HU-012 y canal (`medir_modelos_hu012_hu014_canal.py`, `--sin-thinking`, 1 ciclo, actividades sintéticas) | 0.5.2 | HU-014 **6/6** (p50 5,3 s); HU-012 **4/4** (p50 24,2 s; 2 filas frenadas por el gate de entrada antes del modelo); canal **8/8** con el criterio de #51 (Q8: JSON válido con intención correcta; 7 repreguntas del resolvedor determinístico `actividad_no_resuelta`) |
| Respaldo y restauración (ADR 0009, carpeta local declarada `AGENTE1_RESPALDO_CARPETA_FAKE`) sobre el estado del lote de HU-012 | 0.5.2 | Respaldo de 13 archivos con manifiesto sha256; restauración en limpio de 13 archivos, idénticos byte a byte (decisiones y confirmaciones comparadas con `cmp`); una segunda restauración no pisa nada |
| Scheduler, un disparo (`scheduler --una-corrida --tabla`) con el insumo real de A3 «Ingeniería por un día 2026» y `gemma4:e4b` | 0.5.2 → 0.5.3 | En 0.5.2 el disparo quedó `completada`, pero el insumo `evento_generacion_fallida` a los 183 s (sin `think=False`). En **0.5.3** quedó `borrador_generado` / `PENDIENTE_VALIDACION` en 59,1 s, con la fila de la tabla marcada `borrador generado` |
| Vuelta atrás: revertir el commit de `deploy` | 0.5.3 → 0.5.2 → 0.5.3 | Portainer redesplegó la 0.5.2 en ~3,5 min y volvió a la 0.5.3 en ~4,5 min; `integridad-arranque.jsonl` registró `PASS` con la versión correspondiente en cada arranque |
| Caída del proceso de la consola (`SIGTERM` al PID 1) | 0.5.3 | Docker lo reinició solo (`RestartCount` 0 → 1) y `/health` volvió a responder 200 |

**Retiro del runtime anterior en el servidor:**
- Se bajaron los dos Ollama de usuario y la consola vieja del puerto 8080.
- El cron `arranque-servicios.sh` sólo levanta Tailscale. La versión anterior quedó en `arranque-servicios.sh.bak-20261023`.
- Queda escuchando únicamente la consola del contenedor, en `127.0.0.1:8090`. Ollama no publica puertos.

## Pendiente

- **Scheduler apagado:** el perfil `scheduler` queda apagado. Encenderlo exige configurar la pestaña de insumos (`AGENTE1_INSUMOS_RANGO_A1`) en el env file, que hoy no está. Antes del contenedor el scheduler tampoco corría en vivo, así que es una capacidad nueva por habilitar, no una regresión del corte.
- **Escritura real en Drive y Gmail, sin configurar (igual que antes):**
  - el respaldo diario en Drive (`AGENTE1_RESPALDO_CARPETA_ID`);
  - HU-014 y HU-012 contra los Forms reales y la lista de prueba de Gmail.

  Lo probado es el circuito completo offline más la generación real del modelo.
- **Reinicio del host, sin probar:** el servidor es compartido y no hay root. Lo que se probó es la recuperación ante la caída del proceso. El reinicio lo cubre `restart: unless-stopped` sobre el demonio de Docker, que es un servicio del sistema.
