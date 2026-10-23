# Runbook — el Agente 1 en contenedores

Cómo se instala, se actualiza, se vuelve atrás y se diagnostica el Agente 1 en contenedores en el servidor de la facultad (`labredesfie`). La decisión y sus motivos están en el ADR 0013 y en [#124](https://github.com/SpendIce/Proyecto-Final/issues/124). El trabajo se sigue en [#143](https://github.com/SpendIce/Proyecto-Final/issues/143).

## Qué corre

| Servicio | Imagen | Red | Qué hace |
|---|---|---|---|
| `ollama` | `ollama/ollama:0.40.6` (por digest) | `modelo` (interna, sin internet) | Sirve el modelo. Los modelos se montan en sólo lectura desde `~/.ollama/models` |
| `consola` | `ghcr.io/spendice/agente1` (por digest) | `modelo` + `salida` | Consola de la demo. Se publica en `127.0.0.1:8090` del host |
| `scheduler` | la misma | `modelo` + `salida` | Corridas programadas. **Apagado** salvo el perfil `scheduler` |

Los contenedores del agente:
- corren como el uid del dueño de la clave (`1003`), con el sistema de archivos de sólo lectura y sin capacidades;
- montan `~/.config/agente1/` en sólo lectura y `~/p100/estado-contenedor/` como estado;
- llegan a Ollama por un relay en `127.0.0.1:11434` dentro del contenedor.

## Cómo llega una versión al servidor

1. Se corta la versión según `Implementacion/Agente1/PROCEDIMIENTO-CORTE-DE-VERSION.md` y se pushea el tag `agente1-vX.Y.Z`.
2. El workflow `agente1-imagen` corre la suite dentro de la imagen, publica `ghcr.io/spendice/agente1:X.Y.Z` y escribe `compose.yaml` con el digest en la rama `deploy`.
3. Portainer sigue la rama `deploy` y redespliega solo cuando cambia.

GitHub no llega al servidor, que tiene IP privada: es el servidor el que consulta a GitHub. Nadie despliega a mano lo que no tiene tag.

## Instalación inicial (una vez)

1. En el servidor, crear el directorio de estado con el dueño correcto:
   ```bash
   mkdir -p ~/p100/estado-contenedor && chmod 700 ~/p100/estado-contenedor
   ```
2. En Portainer: *Stacks → Add stack → Repository*.
   - Repositorio: `https://github.com/SpendIce/Proyecto-Final`
   - Referencia: `refs/heads/deploy`
   - Compose: `compose.yaml`
   - Actualizaciones automáticas: polling cada 5 minutos, con *re-pull image*.
3. Si las rutas del host no son las de `jgone`, definir en el stack `AGENTE1_HOST_CONFIG`, `AGENTE1_HOST_ESTADO`, `OLLAMA_HOST_MODELOS`, `AGENTE1_UID` y `AGENTE1_GID`.

## Operación

- **Abrir la consola:** desde la laptop, `ssh -L 8090:127.0.0.1:8090 fie-server-ts` y abrir `http://127.0.0.1:8090`.
- **Smoke en vivo desde el contenedor:** en Portainer, *consola → Console*, o por API. El comando es `python scripts/contenedor_entrypoint.py smoke --live --id-solicitud <fila>`.
- **Encender el scheduler (sólo al hacer el cambio):** agregar el perfil `scheduler` al stack y, en el mismo paso, apagar el scheduler del runtime venv. No pueden correr los dos.
- **Logs:** la auditoría queda en `~/p100/estado-contenedor/logs/`, incluida `integridad-arranque.jsonl`. La salida estándar va al driver de Docker con rotación (10 MB × 5).

## Volver atrás

- **A la versión anterior:** volver a correr el workflow `agente1-imagen` sobre el tag anterior (*Actions → agente1-imagen → Run workflow* con ese tag), o mover la rama `deploy` a su commit anterior. Portainer redespliega solo.
- **Al runtime venv:** detener el stack en Portainer. El checkout `~/p100/Agente1` y el Ollama de usuario siguen intactos mientras dure la marcha en paralelo.

## Diagnóstico

| Síntoma | Qué mirar |
|---|---|
| `consola` reinicia en bucle y sale con código 2 | `integridad-arranque.jsonl`: un archivo controlado no coincide con el manifest. La imagen no se toca a mano: se corta una versión nueva |
| `consola` sale con código 64 | Configuración: falta el env file montado o `AGENTE1_OLLAMA_UPSTREAM` es inválida |
| `ollama` no queda *healthy* | Que `~/.ollama/models` exista y sea legible por el uid 1003 |
| La generación falla por tiempo | El primer pedido carga el modelo en frío: la consola lo calienta al arrancar |
| El smoke da `workspace_auth_denied` | La clave o las APIs del proyecto de DSI (ver `Runbook-Workspace-D2-D3-Agente-1.md`) |

## Seguridad

- **Credencial de Portainer:** es la de desarrollo de Juani y vive sólo en su laptop (`~/.config/agente1/portainer.env`, 600). Ni el agente ni los contenedores la reciben. Después del traspaso, el operador usa su propio usuario de Portainer que le da DSI.
- **Riesgo aceptado:** un admin de Portainer puede actuar como root sobre el host. El agente no usa ese poder: sus contenedores no son privilegiados y no montan el socket de Docker.
