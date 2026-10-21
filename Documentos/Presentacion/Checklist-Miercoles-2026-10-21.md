# Checklist: miércoles 21/10/2026, 7:00 a 9:00, servidor `labredesfie`

Objetivo de la mañana: dejar el Agente 1 **corriendo en el servidor** y con la
evidencia guardada, para que a las 9:00 la presentación sea *correr y mirar*,
no depurar. El servidor se alcanza por Tailscale con el alias `fie-server-ts`; la demo no corre en localhost. Si `ssh fie-server-ts` da timeout, revisá Tailscale. El alias `fie-server` es para la red de la facultad.

Regla de oro: si un paso falla, **no se depura en clase**. Se anota el código,
se muestra la evidencia parcial y se sigue con lo que esté sano.

## Antes de salir de casa (lunes/martes)

- [ ] La rama de #132 está mergeada en `main` y `scripts/corrida_unica.py`
      existe en el remoto. Sin eso, el servidor no tiene el runner.
- [ ] La clave JSON de la cuenta de servicio está en el servidor, **fuera del
      repo**, con `chmod 600`. No se copia por Git, ni por chat, ni por correo.
- [ ] El `workspace-d2.env` del servidor apunta a la hoja v2 (`Actividades!A1:O100`) y tiene el par de la cuenta de servicio. El backup del 21/10 es `workspace-d2.env.bak-20261021`.
- [ ] Están a mano los IDs confirmados por DSI/SEU para la planilla D2
      (planilla, rango, carpeta, plantilla) y la cuenta por la que se hace
      pasar el agente. No se inventan.

## 1. 7:00 a 7:15: red, SSH y copia de la clave

Si #99 ya dejó la clave instalada en el servidor y el preflight del dry-run la
encuentra con permisos 600, **no la pises**: verificá y seguí. Si no está,
copiala una sola vez:

```bash
ssh fie-server-ts 'hostname; whoami; mkdir -p ~/.config/agente1; chmod 700 ~/.config/agente1'
scp -p <ruta-local-de-la-clave>.json fie-server-ts:~/.config/agente1/cuenta-servicio.json
ssh fie-server-ts 'chmod 600 ~/.config/agente1/cuenta-servicio.json; stat -c "%a %n" ~/.config/agente1/cuenta-servicio.json'
```

Tiene que imprimir `600`. Si imprime `644` u otro valor, `chmod 600` y repetir.

La clave **nunca** se agrega al repo, ni siquiera a `tmp/`. Si `git status` la
muestra, se borra del índice y se avisa.

## 2. 7:15 a 7:30: variables de Workspace

El entorno vive fuera del repo, en `~/.config/agente1/workspace-d2.env`, con
`chmod 600`. Si ya existe, se verifica que apunte a la v2 y que el par de la cuenta de servicio esté completo. El backup del 21/10 es `workspace-d2.env.bak-20261021`.

```bash
ssh fie-server-ts 'test -f ~/.config/agente1/workspace-d2.env && chmod 600 ~/.config/agente1/workspace-d2.env && grep -E "^AGENTE1_WORKSPACE_(SPREADSHEET_ID|RANGO_A1)=" ~/.config/agente1/workspace-d2.env && grep -o "^AGENTE1_WORKSPACE_[A-Z0-9_]*" ~/.config/agente1/workspace-d2.env | sort -u || echo "FALTA workspace-d2.env"'
```

Tienen que estar, como mínimo:

```text
AGENTE1_WORKSPACE_AMBIENTE
AGENTE1_WORKSPACE_SPREADSHEET_ID
AGENTE1_WORKSPACE_RANGO_A1
AGENTE1_WORKSPACE_FOLDER_ID
AGENTE1_WORKSPACE_TEMPLATE_ID
AGENTE1_WORKSPACE_TIMEOUT_S
AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES
AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY
AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT
```

La hoja configurada es la **v2**: `Actividades!A1:O100`, con la actividad real `FIE-DIF-08`. El 21/10 se actualizó el entorno y quedó un backup `workspace-d2.env.bak-20261021`; la vieja hoja v1 `Solicitudes` no se tocó. La cuenta de servicio ya leyó y escribió la v2: el 21/10 corrió **6/6** con `gemma4:e4b`.

**Plan A (principal):** no se copia la clave. Se usa el `workspace-d2.env` del servidor, que ya tiene el par de la cuenta de servicio y la hoja v2. El script `run-demo-plan-a.sh` hace el chequeo y la consola visual. **Plan B (respaldo):** el wrapper `scripts/corrida_plan_b_oauth.sh` carga un entorno separado, `~/.config/agente1/workspace-d2-planb.env` (fuera del repo, chmod 600), con el trío OAuth, la hoja v2, la carpeta y la plantilla. El wrapper **quita del proceso** el par de la cuenta de servicio con `unset`; no borra ni modifica `workspace-d2.env` ni `cuenta-servicio.json`.

Si el archivo no existe, crealo con `umask 077` y esas nueve variables; los
IDs son los confirmados por DSI/SEU, no se inventan. Si falta el par de la
cuenta de servicio, se agrega **sólo la ruta y la
cuenta**, nunca el contenido del JSON:

```bash
umask 077
cat >> ~/.config/agente1/workspace-d2.env <<'EOF'
AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY=/home/jgone/.config/agente1/cuenta-servicio.json
AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT=<cuenta-confirmada-por-DSI>
EOF
chmod 600 ~/.config/agente1/workspace-d2.env
```

Cargar el entorno en la sesión de trabajo y comprobar **sólo presencia**, sin
imprimir valores:

```bash
set -a; . ~/.config/agente1/workspace-d2.env; set +a
python3 - <<'PY'
import os
nombres = [n for n in os.environ if n.startswith("AGENTE1_WORKSPACE_")]
print("variables AGENTE1_WORKSPACE_*:", len(nombres))
print("par de cuenta de servicio:", bool(os.environ.get("AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY")) and bool(os.environ.get("AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT")))
PY
```

Si el par está a medias, el runner falla cerrado en el preflight. No hay
fallback silencioso a la OAuth.

## 3. 7:30 a 7:45: código y dependencias

```bash
cd ~/p100/Agente1
git fetch origin
git switch main
git pull --ff-only
git rev-parse --short HEAD
test -f Implementacion/Agente1/scripts/corrida_unica.py || echo "FALTA corrida_unica.py: #132 no está mergeado"
cd Implementacion/Agente1
uv sync
uv run python -c 'import agente1; print("agente1 importa")'
```

Anotar el commit corto: va a quedar en la evidencia. Si `git pull` no es
fast-forward, **no mergear ni rebasear en el servidor**: avisar y seguir con el
commit que ya estaba, anotándolo.

No se corta versión ni se regenera `manifest-version.json`. El manifest queda
viejo entre cortes a propósito.

## 4. 7:45 a 8:00: Ollama 0.40.6 y modelo precargado

El servidor no tiene sudo. Ollama corre como proceso de `jgone` en loopback
`:11434`.

```bash
export OLLAMA_HOST=127.0.0.1:11434
curl -s http://127.0.0.1:11434/api/version
```

- Si responde `{"version":"0.40.6"}`, ya está levantado: no se toca.
- Si no responde, levantar el binario de 0.40.6 que vive en `~/ollama` (el de
  la medición de #50). Si `~/ollama/bin/ollama` no existe, ubicarlo:

```bash
find ~/ollama -maxdepth 3 -type f -name ollama
```

Y arrancarlo en una sesión de tmux para que no se muera al cerrar la terminal:

```bash
tmux new -s ollama 'export OLLAMA_HOST=127.0.0.1:11434; <binario-de-0406> serve'
```

No se actualiza Ollama. La versión se congela con el modelo: 0.40.6 es la de
la medición y la que el runner espera por defecto.

Precargar el modelo de la gacetilla (sin sudo, sin descargar nada si ya está).
#51 decidió `gemma4:e4b` como modelo único del sistema de demostración
(validación del 20/10: 44/48 medido en gacetillas y posts, 48/48 re-validado
con DEF-A1-026; HU-014 y HU-012 18/18). Pesa 6,6 GB y la carga en frío es lenta:
se precarga con `keep_alive` largo para que no se descargue antes de la demo
(el valor por defecto de Ollama son 5 minutos):

```bash
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"gemma4:e4b","keep_alive":"3h"}'
<binario-de-0406> ps
```

`gemma4:e4b` tiene que aparecer cargado. El runner usa `llama3.2:3b` por
defecto y no elige por su cuenta: **en los pasos 5 y 6 se pasa
`--modelo gemma4:e4b`**, que queda anotado en `host.txt`. Configuración
congelada de la medición: sin razonamiento (`gemma4:e4b` no razona si no se
le pide), temperatura 0, `num_predict` 512, timeout 180 s en la medición y 300 s de techo en la demo por el arranque en frío. Gacetilla medida:
mediana 45 s, máximo 67 s.

## 5. 8:00 a 8:10: dry-run (no toca red ni Workspace)

```bash
cd ~/p100/Agente1/Implementacion/Agente1
uv run python scripts/corrida_unica.py --id-solicitud <id-de-la-fila> --modelo gemma4:e4b
```

El dry-run valida raíz, commit, host, Python, variables, clave (archivo, 600,
JSON), scripts y CSV sintéticos. Imprime el plan de los seis pasos y deja
evidencia en `evidencias/corrida-AAAA-MM-DD-HHMM/` con `host.txt`,
`corrida.json` y `transcripcion.log`.

Si el preflight falla, **no se pasa a `--live`**: se corrige lo que dice el
mensaje y se repite. Los códigos de salida están en la tabla de abajo.

## 6. 8:10 a 8:55: corrida live, en el orden de la demo

```bash
uv run python scripts/corrida_unica.py --live --id-solicitud <id-de-la-fila> --presupuesto-min 45 --modelo gemma4:e4b
```

Orden interno, que es el de la presentación:

1. Ollama 0.40.6 y modelo descargado.
2. Smoke de Workspace: una lectura de sólo lectura.
3. Gacetilla E2E: crea un borrador en Drive, pendiente de validación humana.
4. HU-014: certificados con lista sintética, dos aprobaciones de línea y
   aprobación del lote, todo offline.
5. HU-012: pedido de plantilla por el canal del Form y lote completo con los
   CSV sintéticos, todo offline.

El corte de 45 minutos se evalúa **antes de cada paso**. Si se agota, el
runner corta con `CORTE_PRESUPUESTO` (código 7) y dice qué quedó sin correr.
Si la clase empieza y hay poco tiempo, usar un presupuesto menor (por ejemplo
`--presupuesto-min 20`) para que sólo entre la gacetilla.

Si el ensayo de la mañana ya creó el borrador con ese `--id-solicitud`, la
corrida de la clase devuelve `DUPLICADA`: es correcto, no se crea otro
documento en Drive. Para **mostrar la creación** en vivo, usar otra fila de la
planilla (otro id). No borrar `tmp/workspace-e2e` para forzar una creación:
el registro de idempotencia es lo que evita duplicar el documento.

## 7. 8:55 a 9:00: evidencia y cierre

La corrida deja:

```text
Implementacion/Agente1/evidencias/corrida-AAAA-MM-DD-HHMM/
├── host.txt              host, commit, Python, modo, modelo, resultado
├── corrida.json          pasos, estados, duración, exit code, sanitizado
├── transcripcion.log     salida completa, sanitizada
├── workspace-e2e/        manifiestos nuevos del E2E (si los hubo)
├── hu014/                lista, línea, decisiones y log de emisión
└── hu012/                pedido, borradores y entregas simuladas
```

La auditoría de tokens del E2E queda en el registro estable
`tmp/workspace-e2e/logs/cuenta-suplantada.jsonl`; no se copia a la evidencia
de la corrida para no mezclar emisiones de días distintos.

Para traerla a la laptop:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1/Implementacion/Agente1 && ls -d evidencias/corrida-*'
scp -r fie-server-ts:~/p100/Agente1/Implementacion/Agente1/evidencias/corrida-<sello> .
rg -n --glob '!*.pdf' 'BEGIN [A-Z ]*PRIVATE KEY|ya29\.' corrida-<sello> || echo "sin secretos aparentes"
```

La evidencia no lleva la ruta de la clave ni el contenido del `.env`; aun así,
se revisa antes de compartirla. No se commitea en `main` sin pedido.

## Tabla de fallas: qué mirar y qué decir

| Paso | Código | Qué se ve | Qué hacer | Qué decir |
|---|---:|---|---|---|
| Preflight | 1 | `PREFLIGHT: ...` con la variable, el permiso o el JSON que falla | Corregir entorno/clave y repetir el dry-run. No seguir a live. | «La configuración del host no está completa; lo arreglo y vuelvo a correr.» |
| Ollama | 2 | Versión distinta de 0.40.6 o modelo ausente | Levantar el binario de 0.40.6 de `~/ollama`; `ollama pull` sólo si falta el modelo. No actualizar. | «El servidor tiene que usar la versión congelada de la medición; no la cambio en vivo.» |
| Smoke | 3 | `workspace_auth_unavailable` (puede ser el par, la lista cerrada o la clave) | Revisar el par, los permisos 600 y que la cuenta esté en la lista cerrada. Si Google deniega, no reintentar en caliente. | «La lectura de la planilla no está autorizada; el circuito live queda bloqueado y sigo con lo offline.» |
| Gacetilla | 4 | `FALLIDA`, `BLOQUEADA_RECONCILIACION` o timeout | No repetir si está bloqueada: reconciliar. Si fue generación (el gate rechazó la salida), **no cambiar de modelo en vivo** (#51, Q5): se muestra el rechazo y después la evidencia de la mañana. El runner sugiere probar `llama3.2:3b`: no aplica a esta demo. | «No se creó otro documento; miro el manifiesto y muestro la evidencia de la mañana.» |
| HU-014 | 5 | `PENDIENTE_APROBACION` inesperado o decisión rechazada | Verificar el rol del padrón y el catálogo; el circuito no emite parcial. | «El gate de aprobación es el que tiene que frenar; el certificado es de prueba y sin validez.» |
| HU-012 | 6 | El canal no clasifica o el lote no encola | Revisar el CSV sintético y el padrón; el lote es idempotente. | «Los correos son simulados y llevan `BORRADOR — NO ENVIAR`; no sale correo real.» |
| Presupuesto | 7 | `CORTE_PRESUPUESTO` con la lista de pasos pendientes | Nada: es el corte previsto. | «Cortamos acá para no comernos la clase; lo que sigue queda para la próxima.» |
| Uso | 64 | `error: argumentos inválidos` | Revisar el comando; no se imprimen argumentos por seguridad. | (no aplica) |

### Si sólo entra la gacetilla

Es un resultado válido, no una falla. Se muestra la gacetilla y se dice:

> «La gacetilla es el flujo completo de comunicación: lee la planilla, genera
> con el modelo local y deja un borrador en Drive para validación humana. Los
> certificados y las confirmaciones usan el mismo pipeline con otros gates;
> quedan para la próxima corrida.»

No se inventa una corrida ni se muestra una salida vieja como si fuera de hoy.

## Demo visual (camino recomendado)

El script del Plan A hace todo el camino: verifica Tailscale, actualiza el repo, corre el preflight y el smoke con la cuenta de servicio, levanta la consola y abre el navegador. No copia la clave.

```bash
./run-demo-plan-a.sh
```

La consola queda en `http://127.0.0.1:8080`, con un formulario precargado con la actividad real `FIE-DIF-08` del corpus. Al enviar, se ve el paso por la planilla, la generación con `gemma4:e4b` y el borrador en Drive, todo con la cuenta de servicio. `Ctrl-C` corta el túnel y la consola.

Si el puerto 8080 está ocupado: `PORT=8081 ./run-demo-plan-a.sh`.

Si la cuenta de servicio falla, el respaldo es el Plan B OAuth: `./run-demo-planb.sh` (copia el overlay y usa la consola OAuth).

### Plan A sin consola

Smoke de sólo lectura con la cuenta de servicio y la hoja v2:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1/Implementacion/Agente1 && set -a; . ~/.config/agente1/workspace-d2.env; set +a; .venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08'
```

Corrida completa, con gacetilla live y HU-014/HU-012 offline:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1/Implementacion/Agente1 && set -a; . ~/.config/agente1/workspace-d2.env; set +a; .venv/bin/python scripts/corrida_unica.py --live --modelo gemma4:e4b --id-solicitud FIE-DIF-08 --timeout-modelo 300'
```

El smoke tiene que dar `lectura_confirmada`; la corrida completa deja el borrador en `Agentes` y no publica.

### Plan B: OAuth de respaldo

**Plan B1: OAuth + hoja v2 + actividad real.** Ya está armado y probado con el modelo real. El Plan A con cuenta de servicio es el camino principal; este queda si la credencial de servicio falla. El wrapper hace el cambio de credencial sin tocar el entorno de la cuenta de servicio; la cuenta de servicio y su clave siguen en el servidor.

1. Copiar el entorno Plan B desde la máquina del autor, con la red de la FIE:

```bash
ssh fie-server-ts 'mkdir -p ~/.config/agente1 && chmod 700 ~/.config/agente1'
scp ~/.config/agente1/workspace-d2-planb.env fie-server-ts:~/.config/agente1/workspace-d2-planb.env
ssh fie-server-ts 'chmod 600 ~/.config/agente1/workspace-d2-planb.env'
```

El archivo trae el trío OAuth, la hoja v2 sintética (`Actividades!A1:O100`), la carpeta y la plantilla. Nunca se versiona.

2. En el servidor, actualizar el repo a `main` para tener el wrapper y el preflight OAuth:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1 && git switch main && git pull --ff-only'
```

3. En el servidor, desde el repo, verificar sin escribir:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1 && bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh --check'
```

Hace el dry-run del preflight y un smoke live de sólo lectura con `FIE-DIF-08`. Tiene que terminar con `lectura_confirmada`.

4. Si el check pasa, correr la demo completa:

```bash
ssh fie-server-ts 'cd ~/p100/Agente1 && bash Implementacion/Agente1/scripts/corrida_plan_b_oauth.sh'
```

Corre Ollama con `gemma4:e4b`, el smoke, la gacetilla live y HU-014/HU-012 offline. El E2E deja un `BORRADOR — NO PUBLICAR` en la carpeta `Agentes`.

La corrida completa con cuenta de servicio dio 6/6 en el servidor con `gemma4:e4b` y `FIE-DIF-08`; el E2E OAuth también dio `PENDIENTE_VALIDACION`. No hace falta el stub.

5. Si el modelo no cumple el contrato, el gate rechaza y se muestra el rechazo. No se cambia de modelo ni se publica.

6. La hoja v2 sintética es la garantía del camino. La hoja de producción y la cuenta de servicio siguen en #99. Si la hoja de producción ya es v2 y el OAuth tiene acceso, se puede apuntar el overlay a esa hoja; no es necesario para la demo.

Es una **contingencia declarada**: la identidad objetivo sigue siendo la cuenta de servicio (#99), no el OAuth que se retira. No versionar el overlay.

**Plan B2: offline.** Si el OAuth tampoco sirve:

1. Correr HU-014 y HU-012 offline en el servidor, en ese orden.
2. Mostrar la evidencia de la gacetilla: `corrida.json` y el borrador de la mañana.
3. Decir que el E2E live quedó pendiente por acceso a Sheets/Docs, no por el agente ni por el modelo.
4. No mostrar una salida vieja como si fuera de hoy.

La gacetilla offline en el servidor sirve para mostrar el pipeline, pero no acredita Workspace live.

### Si la gacetilla live falla

1. No depurar frente a la clase.
2. Mostrar `corrida.json` y el manifiesto de la mañana.
3. Si hace falta mostrar el pipeline, correr el E2E offline **en el servidor**
   (fuente y destino en memoria) y aclarar que no acredita Workspace:

```bash
uv run python scripts/workspace_e2e.py --tipo gacetilla --salida /tmp/demo-offline-$(date +%H%M)
```

4. Decir que el bloqueo es de credencial o de red y que el circuito live queda
   pendiente de #118. No se promete lo que no corrió.

## Lo que NO se hace

- No se versiona la clave JSON, ni el `.env`, ni `tmp/`.
- No se usa `sudo`: Ollama y el agente corren en espacio de usuario.
- No se actualiza Ollama ni se cambia el modelo por cuenta propia.
- No se corta versión ni se regenera `manifest-version.json`.
- No se publica, comparte ni envía nada: el E2E deja borradores y las
  confirmaciones son simuladas.
- No se borra `tmp/workspace-e2e`: es el registro de idempotencia del E2E.
- No se borra `~/.config/agente1/`.
- No se rebaselinea el Gantt ni se agregan estados nuevos.
- No se corre la demo desde la laptop como host.
