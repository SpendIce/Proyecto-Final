# Changelog — Agente 1

Historial de las **versiones del agente** que se instalan en el host. Cada
versión lleva un tag `agente1-vX.Y.Z` sobre `main` y una entrada acá con los
cambios controlados que la componen, su clase y la referencia del issue o rama
que los introdujo.

La versión sale de un solo lugar, `pyproject.toml` (`[project].version`); el
manifest de versión, la auditoría de cada pieza y esta entrada la citan, no la
repiten. El procedimiento para cortar una versión está en
[`PROCEDIMIENTO-CORTE-DE-VERSION.md`](PROCEDIMIENTO-CORTE-DE-VERSION.md).

**Clases** (resolución del issue #66):

- **Mayor** — cambia un contrato de interfaz.
- **Menor** — capacidad nueva, prompt o política.
- **Parche** — corrección.

> La referencia identifica el cambio controlado. Este repositorio integra por
> ramas `ticket/NN` con merge local; todavía no hay números de PR de GitHub, así
> que se cita el issue o la rama.

## [0.5.3] - 2026-10-23

- **Parche — el camino del scheduler pide el modelo sin razonamiento (#143).**
  `cli_insumos` (insumos de agentes y scheduler) construía el generador sin
  `think=False`, a diferencia del E2E. Con `gemma4:e4b`, el insumo de A3
  quedaba `evento_generacion_fallida` a los 183 s. Lo encontró el ensayo del
  scheduler en el contenedor del servidor. El compose le da al scheduler 300 s
  de techo, igual que la demo.

## [0.5.2] - 2026-10-23

- **Parche — la imagen lleva `golden/` (#143).** El canal de pedidos offline
  (HU-012/HU-013) lee la ficha de `golden/`. Sin ese directorio, la corrida
  única fallaba en el contenedor con `runner_unavailable`. Un test fija qué
  directorios tiene que llevar el runtime.

## [0.5.1] - 2026-10-23

- **Parche — la corrida única corre dentro del contenedor (#143).** Sin `.git`
  en la imagen, `corrida_unica.py` toma el commit de `AGENTE1_REVISION`, que
  el `Dockerfile` hornea desde el tag. Con `AGENTE1_ESTADO` definido, el
  registro estable del E2E va a `<estado>/workspace-e2e` porque el código es
  de sólo lectura.
- **Parche — directorios por defecto escribibles en el contenedor.** `tmp/` y
  `salida/` del agente se montan como `tmpfs`, para que un script corrido sin
  `--directorio` no falle por sistema de archivos de sólo lectura. Lo durable
  sigue en `/state`.

## [0.5.0] - 2026-10-23

Versión que corre en contenedores en el servidor de la facultad y junta los
cambios controlados que se instalaron en `labredesfie` desde la 0.4.0 sin corte
propio (la presentación de avance del 21/10 corrió sobre `dbcbcde`).

- **Menor — empaquetado en contenedores (#143, ADR 0013).** `Dockerfile`
  multi-etapa (`test` corre la suite adentro, `runtime` sin tests, no root, base
  fijada por digest), `docker/compose.yaml` con Ollama 0.40.6 en una red interna
  sin egreso y modelos montados en sólo lectura, y
  `scripts/contenedor_entrypoint.py`: carga el env file en tiempo de ejecución,
  verifica la integridad al arrancar y reenvía loopback a Ollama sin tocar el
  control del adaptador. `Dockerfile` y `docker/` entran a `RUTAS_CONTROLADAS`.
  `pyyaml` entra sólo como dependencia de desarrollo.
- **Menor — modelo de la demo (#51).** Prompts v3/v4 de HU-012 y HU-014, v5 de
  LinkedIn e Instagram, v6 de posts con versión de prompt por canal,
  `linea_descriptiva_v2`, `think` opcional en Ollama y medidores con
  `--guardar-respuestas`. Timeout de Ollama derivado del peor caso del servidor
  (#50).
- **Menor — plantilla de HU-012 (#140).** El modelo escribe sólo la prosa y el
  código compone el cuerpo con las variables.
- **Menor — modo producción del envío Gmail (#141)** con lista aprobada; el
  modo prueba sigue siendo el único habilitado.
- **Menor — corrida única y consola de la demo (#132).** Script de corrida en
  el servidor, consola visual con la cuenta de servicio y hoja v2, `think=false`
  en la gacetilla live y E2E de posts con el contrato creativo v3. Los wrappers
  del plan B por OAuth siguen en `scripts/` sin credencial que los alimente
  (OAuth dada de baja en #99).
- **Parche — gates.** La regla del título rechaza la copia, no la mención del
  tema (#139); el gate de registro no confunde la tercera persona con el tuteo;
  una región amplia después de «en» es tema, no sede; el techo de extensión del
  post es el de cada plataforma (#51).
- **Parche — E2E offline de la gacetilla (#138):** el fake devuelve la ficha.

## [0.4.0] - 2026-10-17

El aporte a Historia Viva manda el vocabulario exacto de la `1.1.0-rc2` de la
`/v1` (#117): `TIPOS_CONTENIDO_APORTE` pasa a `{"gacetilla", "post",
"comunicado", "newsletter"}`: se quita `mail` (un mail es el canal `correo`,
no un tipo de contenido) y entra `comunicado`. El espejo
`contracts/historia_viva_v1.schema.json` y `CONTRACT_VERSION` pasan a
`historia_viva_v1_1.1.0-rc2`, con la huella del paquete rc2
(`a0082324…52a7f0ea`, resolución del issue #101).

Es un cambio **Mayor**: cambia un contrato de interfaz, el contrato de
Historia Viva. El número, 0.4.0, sigue el precedente de este repositorio: en
el corte del #121 un cambio de clase Mayor bajó de `0.1.0` a `0.2.0`, y el
procedimiento marca «sube X» pero con `X=0` y el contrato de la `/v1`
todavía en borrador (rc2, congelado el 30/10) una `1.0.0` declararía una
estabilidad que no existe. Declaro la desviación acá, como pide el
procedimiento.

### Mayor — contratos de interfaz

- `TIPOS_CONTENIDO_APORTE` = `{"gacetilla", "post", "comunicado",
  "newsletter"}`; `mail` se rechaza con `ValueError` en el gate del cliente
  (#117).
- Espejo del contrato `historia_viva_v1.schema.json`: `$id` y
  `x-contract-version` en `historia_viva_v1_1.1.0-rc2`, huella rc2 en
  `description`, `.TipoContenido.enum` con las cuatro formas y `.Canal.enum`
  con `["instagram", "linkedin", "web", "correo", null]` (#117).
- `CONTRACT_VERSION` = `historia_viva_v1_1.1.0-rc2` (#117).

## [0.3.0] - 2026-10-17

El canal del Form declara el tipo de gacetilla, pide la actividad sólo para
los tipos que la llevan y resuelve el área emisora por un padrón cerrado
(#122). Es un cambio **Menor**: la forma v1 de la hoja sigue siendo el
default y ningún contrato vivo cambia su comportamiento; la forma v2 del
canal es opt-in por `AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO` y las listas
cerradas son contratos nuevos versionados, no reescrituras de contratos
vigentes. La forma v1 se versiona retroactivamente, tal como ya se leía.

### Menor — capacidades, prompts y políticas

- Contratos versionados de la hoja de respuestas del Form: `canal_form_respuestas_v1`
  (la forma de una sola pregunta abierta, retroactiva) y
  `canal_form_respuestas_v2` (tipo de gacetilla como primera pregunta, 
  actividad condicional, área emisora y pedido libre) (#122).
- Padrón cerrado de áreas emisoras (`contracts/areas_emisoras_v1.json`,
  provisional, con las firmas de área observadas en el corpus): la firma del
  área que la pieza imprime sale del padrón, por el placeholder
  `{area_emisora}` de la forma declarada del tipo, sin editar formas (#122).
- El canal v2 valida el tipo contra la lista cerrada de
  `tipos_gacetilla_v1` y la actividad es condicional: «No es una actividad /
  no figura» no registra ninguna actividad, y una fila que no cumple las
  listas cerradas termina en un desenlace acotado del canal (aviso con
  mensaje fijo, registro con código, sin núcleo y sin generación) (#122).
- El pedido estructurado despacha por el mismo clasificador determinístico
  de #115 (`gacetilla actividad <id>`); el registro de atendidos de la
  forma v2 declara el contrato de hoja leído, los campos estructurados que
  trajo la fila y el origen de los hechos de la pieza (fuente institucional
  o declaración de la solicitud) (#122).
- La sincronización automática del desplegable de actividades (Apps Script)
  queda declarada como destino del canal, no construida: el desplegable se
  carga a mano como insumo provisional con identificadores de la planilla
  (#122).

## [0.2.0] - 2026-10-17

La gacetilla declara su tipo y el tipo declara su modo y su forma (ADR 0012).
Es un cambio **Mayor** porque cambian contratos de interfaz: el catálogo de
intenciones, el contrato de entrada y el renderer.

### Mayor — contratos de interfaz

- Contrato cerrado de tipos de gacetilla (`tipos_gacetilla_v1.json`) con los
  siete tipos del corpus, su modo de producción y si necesitan actividad
  (#120).
- Catálogo de intenciones v4: `generar_newsletter` y `generar_mail` dejan de
  ser intenciones porque un newsletter es un tipo de gacetilla y un mail es el
  canal; `generar_gacetilla` declara `tipo_gacetilla` como parámetro cerrado
  (#121). El fallback de interpretación pasa a v4 con el mismo enum.
- Contrato de entrada por tipo (`contracts/entradas/<tipo>_v1.json`), con sus
  `required` y sus campos que no aplican. `gacetilla_input_v2` queda como el
  contrato de actividad que sólo reusa difusión (#121).
- Forma declarada por tipo (`contracts/formas/<tipo>_v1.json`), con
  `schema_version` propia. La frase fija de invitación sale del renderer: el
  marco se copia de la forma y la introducción la aporta la prosa del modelo
  en los tipos que generan (#121).

### Menor — capacidades, prompts y políticas

- Renderer único y gate único para los siete tipos (`gacetillas.py`): núcleo
  común más reglas por tipo; en los tipos que extraen y confirman el gate
  compara contra lo confirmado y no interviene el fallback de interpretación
  (#121).
- Prompt `gacetilla_v8` (difusión) y prompt corto `saludo_o_efemeride_v1`; los
  cinco tipos que extraen y confirman no tienen prompt ni llaman al modelo
  (#121).
- Casos de conformidad de forma con golden por tipo en `golden/formas/`, y
  actualización del golden `SYN-001` y de la matriz `matriz_hu010.py` (#121).

## [0.1.0] - 2026-10-14

Primera versión etiquetada. Es el sistema de demostración completo del Agente 1
antes de la revisión de laboratorio y de la mesa final del 18/11/2026. Consolida
los cambios controlados incorporados a `main` hasta esta fecha.

### Mayor — contratos de interfaz

- Contrato v2 de la planilla de actividades, consumido por HU-010 (gacetilla),
  HU-011 (posts) y HU-013 (interpretación) (#77).
- Contrato creativo estructurado de HU-011 y su renderer determinista (#85).
- Contrato `/v1` de consulta a Historia Viva: cliente y transporte HTTP
  (#12, #13, #17).

### Menor — capacidades, prompts y políticas

- Pipeline HU-010: gacetilla desde un evento A3 (#83).
- Pipeline HU-011: posts y post de efeméride desde Historia Viva (#85).
- Confirmaciones HU-012 y su circuito de doble aprobación por rol (#28).
- Recordatorios de pago, pagos desde la planilla e instrucciones de pago
  (#44, #45, #46).
- Corrida de pagos, novedades de pago y envío por Gmail de lista de prueba
  (#39, #40, #42).
- Plantilla de correo por actividad HU-012 (#73).
- Certificados HU-014: línea descriptiva, lote de cierre y emisión (#74, #75).
- Canal de pedidos por Form, registro de decisiones y canal de planilla
  (#71, #72).
- Scheduler local de las corridas programadas (#84).
- Respaldo diario del estado local en Drive (#86).
- Purga de datos personales del registro al cerrar el ciclo (#87).
- Medición del nivel verificado de los SLO (#88).
- Corrida de insumos de agentes A2-A5 sobre la pestaña «Insumos de agentes»
  (#82).
- Buzón Gmail de sólo lectura (#43).
- Manifest de versión y verificación de integridad al arrancar (#92).
- Versión del agente en la auditoría, tag y este changelog (#93).

### Parche — correcciones

- Gacetillas sin lugar: el gate y el render acuerdan el campo (#6).
- Reintento con feedback de regla en HU-011 ante salida no conforme.
- Idempotencia de HU-012 ante una caída (#9).
- Presupuesto de decodificación dimensionado por el contrato (#4).

### Infraestructura

- Suite, cobertura y linter del Agente 1 en GitHub Actions (#90).

## Configuración

Cambios que el responsable técnico o el operador le piden a **DSI** en la consola
de Google (Workspace y credenciales): IDs de planillas y Forms, scopes, cuenta
técnica, unidad compartida. **No generan versión del agente** —no cambian el
código, los prompts ni las políticas— y se anotan **al pedir el cambio**, con
fecha, motivo y quién lo aprobó (issue #66, adenda del 13/10). El log de la
consola de Google los guarda 6 meses; esta tabla es el registro que sobrevive.

| Fecha | Cambio pedido | Motivo | Aprobó |
|---|---|---|---|
| — | _Sin cambios pedidos a DSI todavía._ | — | — |
