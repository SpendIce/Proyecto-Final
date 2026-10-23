---
status: accepted
---

# El agente corre en contenedores sobre el Docker del servidor, con el aislamiento dentro del contenedor

El Agente 1 corría en `labredesfie` como un checkout con un venv de `uv` y un Ollama de usuario, compartiendo host, loopback y ciclo de vida. Sin root, nada volvía solo después de un reinicio y el modelo no tenía aislamiento. El perfil de seguridad lo declaraba como **previsto y no implementado**. La especificación de la migración ([#143](https://github.com/SpendIce/Proyecto-Final/issues/143)) pedía Docker **rootless** y descartaba el Docker rootful y el grupo `docker`, porque los dos equivalen a darle root al usuario.

El 23/10 DSI le dio a Juani acceso a Docker del servidor por **Portainer**, con rol de administrador ([#146](https://github.com/SpendIce/Proyecto-Final/issues/146)). Es el Docker rootful del mismo host. Rootless habría exigido que DSI configurara `uidmap`, `subuid` y *linger*, cosa que no está pedida ni tiene fecha.

Decidimos ([#124](https://github.com/SpendIce/Proyecto-Final/issues/124)) que **el agente corre en contenedores sobre el Docker rootful del servidor, y el aislamiento se garantiza dentro de los contenedores**:

1. **La credencial de Portainer es de desarrollo y es de Juani.** El agente y sus contenedores nunca la reciben, y tampoco reciben el socket de Docker. Que esa credencial permita actuar como root sobre el host se declara como riesgo aceptado: DSI la entregó sabiéndolo, y después del traspaso el operador recibe su propio usuario.
2. **Los contenedores del agente corren endurecidos:** usuario no root, sistema de archivos de sólo lectura, `cap_drop: ALL`, `no-new-privileges`, sin modo privilegiado ni namespaces del host, con límites de memoria y procesos.
3. **El modelo no tiene salida a internet.** Ollama corre en su propio contenedor, con la versión congelada para el modelo de la demo, en una red interna. El agente llega a él por un relay en `127.0.0.1:11434` dentro de su propio contenedor, así que el adaptador mantiene su control de sólo loopback sin cambios.
4. **Nada sensible entra a la imagen.** La clave de la cuenta de servicio y el env file se montan en sólo lectura y se cargan en tiempo de ejecución. Los modelos se montan desde el host. El estado vive en un directorio del host.
5. **El empaquetado es parte de la versión.** El `Dockerfile` y `docker/` entran a las rutas controladas del manifest (ADR 0010), y el entrypoint verifica la integridad antes de lanzar cualquier comando.
6. **Sólo se despliega una versión cortada.** El CI construye la imagen y corre la suite adentro en cada cambio. Al cortar una versión, publica la imagen en ghcr.io y escribe el compose con el digest en la rama `deploy`. Portainer sigue esa rama por *polling*. GitHub no llega al servidor y no guarda credenciales del servidor.

## Considered Options

- **Esperar el Docker rootless.** Es el aislamiento más fuerte respecto del host. Se descartó porque depende de una configuración de DSI que no está pedida y deja el modelo sin aislar mientras tanto. Queda como mejora si DSI lo habilita: el compose no cambia de forma.
- **Seguir con el venv y el Ollama de usuario.** Es lo que corrió la demo del 21/10. Se descartó como estado final porque no aísla el modelo, no vuelve solo después de un reinicio y no da un artefacto reproducible para el traspaso. Se mantiene en paralelo hasta que el contenedor tenga evidencia.
- **Compartir la red del contenedor de Ollama (`network_mode: service:ollama`).** Es más simple, pero el modelo queda con la salida a internet del agente.
- **Abrir el adaptador a hosts que no sean loopback.** Se descartó porque afloja un control declarado en el Anexo 3 por comodidad de red.
- **Meter los modelos en la imagen.** Hace la imagen determinista, pero pesa decenas de GB y duplica lo que ya está en el host. El modelo se controla por su hash en la evidencia.
- **Desplegar con un runner de GitHub en el servidor, o con la acción conectada a la tailnet personal.** El primero es un riesgo en un repo público, porque un PR de un fork ejecutaría código en el servidor. El segundo no sobrevive al traspaso. Se eligió que el servidor tire de GitHub.

## Consequences

- El reinicio del host ya no deja el sistema caído: el demonio de Docker es un servicio del sistema y los contenedores tienen `restart: unless-stopped`. Eso reemplaza al cron `@reboot` de Ollama y al timer de `systemd --user` sin *linger*.
- El scheduler del contenedor queda **apagado** (perfil `scheduler`) mientras dure la marcha en paralelo con el venv, para que dos runtimes no procesen la misma planilla. Se enciende con el cambio.
- Hay dos Ollama en el host durante la marcha en paralelo. Entran en memoria (31 GB), pero compiten por los 4 núcleos si se usan a la vez.
- El Anexo 3 gana tres filas con evidencia (aislamiento del modelo, modelo sin egreso y runtime endurecido) y una de riesgo aceptado (credencial de Portainer de desarrollo con permisos de root sobre el host).
- La imagen publicada en ghcr.io es pública y contiene lo mismo que el repo público: ni secretos ni modelos.
- Una versión que no pase la suite adentro de la imagen no se publica. Un archivo controlado alterado dentro del contenedor impide arrancar.
