# Cambios en la configuración por entorno: registro y aviso (#94, ADR 0010)

- **Estado:** implementado y verificado offline; el paso en el host queda para
  el operador designado y para la mesa final
- **Alcance:** huella de la configuración de Workspace por entorno, comparación
  con la corrida anterior, asiento en la auditoría y aviso al operador sin
  frenar el arranque
- **Relacionados:** ADR 0010, issues #66 y #94, `CONTEXT.md` (*Cambio
  controlado*, *Dato operativo*), `src/agente1/config_entorno.py`,
  `src/agente1/cli_insumos.py`

## 1. Qué se construyó

Al arrancar en **modo operación** (corrida `--live`, el camino de las unidades
`systemd/` y del scheduler), el agente calcula la **huella de la configuración
por entorno** a partir de `resumen_seguro()` de `ConfiguracionWorkspace` y la
compara con la de la corrida anterior:

- **Primera corrida, sin huella previa:** asienta la base, sin avisar
  (`resultado=BASE`).
- **Huella igual:** deja constancia de que se comparó (`resultado=SIN_CAMBIO`).
- **Huella distinta:** asienta **qué claves** cambiaron, sin sus valores
  (`resultado=CAMBIO`), y avisa por correo al operador.

El registro vive en `logs/config-entorno.jsonl`, un JSONL append-only escrito
por `registro_auditoria.escribir_registro` (#93), así que **cada línea lleva
`version_agente` y `manifest_version_sha256`**. Cada línea guarda además el
resumen seguro vigente, de modo que la corrida anterior es la última línea
válida: no hay un archivo de estado aparte que pueda divergir del asiento.

**Por qué la rotación de credenciales no dispara el aviso.** La huella sale del
`resumen_seguro()` —hashes de los identificadores, ambiente, endpoints y
límites—, y ni el access token ni el refresh token entran ahí: el token vive en
su propia variable y los providers de credencial los leen directo del entorno.
Rotar una credencial no cambia la huella.

**Por qué no frena el arranque.** Ni el aviso ni la escritura del registro
levantan hacia el llamador: si el correo falla, queda `aviso=fallido` con el
código del error y la corrida sigue (ADR 0010). El fail-closed es del árbol de
archivos (`manifest_version.py`, #92), no de la configuración por entorno. El
aviso sale por `gmail.send` con la lista de prueba de D12 y, en el cuerpo,
viajan sólo los **nombres de las claves** y las dos huellas, nunca los
identificadores.

La dirección que recibe el aviso se declara con
`AGENTE1_CONFIG_ENTORNO_AVISO_DESTINATARIO` y tiene que estar en
`AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`. Sin dirección declarada el cambio igual
se asienta (`aviso=no_configurado`) y no sale correo: el aviso no puede ser la
razón por la que una corrida no arranca.

## 2. Reproducción offline ejecutada (2026-10-14)

Se corrieron cuatro arranques de punta a punta con el módulo real
(`agente1.config_entorno`) y el camino real de `gmail.send`
(`GmailDestinoConfirmaciones`) con un **transporte fake declarado** (se registra
la solicitud y se devuelve una respuesta fija; no hay red). Salida real:

```
== 1. primera corrida (base, sin aviso) ==
resultado: BASE
claves_cambiadas: []
aviso: None (error=None)
solicitudes HTTP del aviso: []

== 2. sin cambio ==
resultado: SIN_CAMBIO
claves_cambiadas: []
aviso: None (error=None)
solicitudes HTTP del aviso: []

== 3. cambia el id de la planilla ==
resultado: CAMBIO
claves_cambiadas: ['spreadsheet_ref_hash']
aviso: enviado (error=None)
solicitudes HTTP del aviso: ['POST gmail.googleapis.com/gmail/v1/users/me/messages/send']

== 4. cambia la carpeta con el aviso caído ==
resultado: CAMBIO
claves_cambiadas: ['folder_ref_hash']
aviso: fallido (error=gmail_unavailable)
solicitudes HTTP del aviso: ['POST gmail.googleapis.com/gmail/v1/users/me/messages/send']

== auditoría (logs/config-entorno.jsonl) ==
{"aviso": null, "aviso_error": null, "claves_cambiadas": [], "huella": "4588c6791133d86492082daab70060500723a6787abd72ffc7d568f7b59f27c4", "huella_anterior": null, "resultado": "BASE", "version_agente": "0.1.0"}
{"aviso": null, "aviso_error": null, "claves_cambiadas": [], "huella": "4588c6791133d86492082daab70060500723a6787abd72ffc7d568f7b59f27c4", "huella_anterior": "4588c6791133d86492082daab70060500723a6787abd72ffc7d568f7b59f27c4", "resultado": "SIN_CAMBIO", "version_agente": "0.1.0"}
{"aviso": "enviado", "aviso_error": null, "claves_cambiadas": ["spreadsheet_ref_hash"], "huella": "2504e293e499bfbc50d5bbb447513bf488b89675967ef724bd64f0578e7dcd04", "huella_anterior": "4588c6791133d86492082daab70060500723a6787abd72ffc7d568f7b59f27c4", "resultado": "CAMBIO", "version_agente": "0.1.0"}
{"aviso": "fallido", "aviso_error": "gmail_unavailable", "claves_cambiadas": ["folder_ref_hash"], "huella": "8fda01b4a99922703c5c0d7619cfaeba544d04631878318017a43fe670904a13", "huella_anterior": "2504e293e499bfbc50d5bbb447513bf488b89675967ef724bd64f0578e7dcd04", "resultado": "CAMBIO", "version_agente": "0.1.0"}

¿aparecen los identificadores en la auditoría?: False
```

Los cuatro casos —sin cambio, cambio de una clave, primera corrida y aviso
caído— están cubiertos por la suite en `tests/test_config_entorno.py`, que
además prueba que el identificador **no** viaja ni a la auditoría ni al cuerpo
del correo, y el cableado en `tests/test_integridad_arranque.py` (una corrida
`--live` deja `BASE` y, al cambiar el id, `CAMBIO`).

Marcas de alcance: esta reproducción es **offline y declarada** —no acredita una
corrida contra Workspace real ni la entrega de un correo por Google—. No es un
fake: es el mismo módulo, el mismo `gmail.send` y la misma auditoría que el modo
operación.

## 3. Paso en vivo declarado (para el laboratorio y la mesa)

Precondición: el host tiene el checkout de la versión, su `manifest-version.json`
y las `AGENTE1_WORKSPACE_*` con la configuración vigente; el operador ya arrancó
una vez para dejar la base. Estimado: **menos de 2 minutos**.

1. **Arranca con la configuración de siempre.** Correr el disparo programado
   documentado (`--live` + `--confirm-write-workspace` + `--ollama-model`). En la
   auditoría:

   ```bash
   tail -n 1 "$DIRECTORIO_SALIDA/logs/config-entorno.jsonl"
   # resultado=SIN_CAMBIO (o BASE la primera vez), claves_cambiadas=[]
   ```

2. **Se cambia un identificador de la configuración por entorno** (el paso que
   la mesa muestra; equivale a un cambio pedido a DSI). Por ejemplo, apuntar la
   planilla a otro id:

   ```bash
   # en el env file del host (~/.config/agente1/scheduler.env)
   AGENTE1_WORKSPACE_SPREADSHEET_ID=<otro-id>
   ```

3. **Arranca igual, pero queda asentado y avisa.** Repetir el disparo: la
   corrida sigue (no frena) y la auditoría muestra la clave afectada, sin el
   valor:

   ```bash
   tail -n 1 "$DIRECTORIO_SALIDA/logs/config-entorno.jsonl"
   # resultado=CAMBIO, claves_cambiadas=["spreadsheet_ref_hash"],
   # aviso=enviado, aviso_error=null
   ```

   El operador recibe el correo «Agente 1: cambió la configuración por
   entorno», con la clave afectada y las dos huellas, sin los identificadores.
   Si el correo no sale, la línea queda con `aviso=fallido` y el código del
   error, y la corrida sigue.

4. **Se restaura.** Volver el id anterior en el env file y repetir el disparo:
   `resultado=CAMBIO` otra vez (cambió respecto de la corrida 3) y la corrida
   sigue. La huella vuelve a coincidir con la de la corrida 1.

El paso no modifica la configuración real de Google: cambia lo que el agente
**lee** del entorno. El control de fondo del lado de Google son las alertas del
modelo de seguridad de la cuenta (#64).

## 4. Límites

- No acredita la corrida live contra Workspace ni la entrega real del correo:
  es la reproducción offline del mismo código, más el procedimiento para el
  host. Desde este entorno no hay credenciales ni host de operación para
  ejecutar el paso 2 en vivo.
- Cubre la configuración de **Workspace** (`resumen_seguro()` de
  `ConfiguracionWorkspace`), que es la clase nombrada por el issue. La
  configuración de los Forms (`AGENTE1_FORM_*`) tiene su propio
  `resumen_seguro()`; extender la huella a esa familia es un cambio de alcance,
  no una corrección de este issue.
- El registro durable para el laboratorio sigue siendo la sección
  *Configuración* de `CHANGELOG.md`: cada cambio pedido a DSI se anota **al
  pedirlo**, con fecha, motivo y quién lo aprobó (issue #66, adenda). Este
  issue agrega la detección automática, no reemplaza esa tabla.
- La dirección del operador (`AGENTE1_CONFIG_ENTORNO_AVISO_DESTINATARIO`) es un
  supuesto de este issue: el issue pide «avisar por correo al operador» y no
  fijaba la variable. Queda declarada en el env file del host (`systemd/`), que
  es tarea de la instalación.
- El `manifest-version.json` versionado queda viejo tras este cambio controlado,
  **por diseño** (procedimiento de corte, §3): el paso en vivo se corre sobre una
  versión instalada —con su manifest regenerado al cortar—, no sobre esta rama.
