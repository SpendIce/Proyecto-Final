# Auditoria del worktree — Issue #2

- **Issue:** `SpendIce/Proyecto-Final#2`
- **Fecha de corte:** 2026-09-05
- **HEAD observado:** `39312a1`
- **Rama/remoto observado:** `main`, alineada con `myfork/main` al iniciar la auditoria
- **Estado:** `AUDITADO_CON_RESPALDO_VERIFICADO_PUBLICACION_BLOQUEADA`

## Proposito y limite

Este corte preserva el resultado de la inspeccion previa al saneamiento. No es
un inventario definitivo, no crea una baseline tecnica recuperable y no
autoriza publicar el worktree actual. Durante la auditoria no se revirtieron,
borraron, stagearon ni commitearon cambios.

## Estado observado

El worktree contiene una migracion amplia y todavia no integrada. El recuento
consolidado identifico:

- 481 archivos trackeados con drift `100644` a `100755`;
- 311 con cambio puro de modo;
- 74 con cambio textual y de modo;
- 96 binarios con cambio de modo y contenido conservado respecto de `HEAD`;
- 51 entradas no trackeadas colapsadas en el inventario del respaldo y 55
  miembros en el archivo. El inventario exhaustivo usa expansion por archivo y
  registra 540 paths totales —485 trackeados, de los cuales 481 tienen drift de
  modo, y 55 no trackeados—. Las cifras
  anteriores 49/53 y 50/54 pertenecen a cortes previos a incorporar los propios
  artefactos de auditoria.

Los conteos describen el corte inspeccionado y deben recalcularse antes de
ejecutar la separacion en commits.

## Revision preventiva de publicacion

La inspeccion automatizada de todos los archivos de texto, incluidos los no
trackeados y excluyendo solamente `.git/` y el propio respaldo, obtuvo cero
coincidencias para claves privadas, tokens `sk-`, claves AWS y valores
`Bearer` de veinte o mas caracteres. Se encontraron categorias que requieren revision
manual antes de cualquier push:

- placeholders y fixtures que deben distinguirse de secretos reales;
- correos institucionales presentes en fuentes documentales;
- URLs de Google que pueden contener identificadores de recursos;
- capturas, logs y snapshots bajo `.playwright-mcp/`;
- binarios y artefactos LaTeX que pueden ser deliberados o reproducibles.

La ausencia de coincidencias conocidas no equivale a una auditoria exhaustiva
de secretos ni cubre el contenido interno de PDF o ZIP. El inventario deja los
archivos afectados como `REVISAR`, `NO_PUBLICAR` o `NO_REDISTRIBUIR`; por lo
tanto ninguno queda autorizado para un commit publico masivo. Cada commit del
saneamiento debe usar una allowlist explicita y repetir el control de secretos
sobre sus paths antes del staging.

## Agrupacion preliminar para el saneamiento

1. Adaptacion documental Becerra → Goñe y reglas de agentes.
2. Implementacion y pruebas HU-010/HU-011.
3. Slice offline y definiciones candidatas de HU-012.
4. Persistencia, migraciones y operaciones seguras.
5. Evidencia, benchmarks, manifests y matrices.
6. Solicitudes y paquetes de gestion SEU/DSI/Cicerchia.
7. Contrato e integracion con Historia Viva.
8. Fuentes y entregables academicos LaTeX.
9. Artefactos generados, binarios, permisos y runtime local.

Esta agrupacion es una hipotesis de separacion, no una autorizacion para crear
commits. Cada grupo debe contrastarse con el diff y con las fuentes de verdad
antes de staging.

### Secuencia propuesta de commits

| Orden | Incremento | Dependencia | Riesgo que debe controlar |
| --- | --- | --- | --- |
| 0 | Normalizar modos contra el indice, preservando las tres excepciones historicas | Respaldo verificado | Ocultar cambios semanticos dentro del ruido de permisos |
| 1 | Gobernanza operativa, contexto y artefactos de auditoria | Orden 0 | Publicar metadatos internos o instrucciones inconsistentes |
| 2 | Implementacion, politicas y pruebas HU-010/HU-011 | Orden 0 | Afirmaciones de comportamiento sin evidencia ejecutable |
| 3 | Persistencia y migraciones | Orden 2 si consume sus modelos; en otro caso puede revisarse en paralelo | Inferencias o migraciones incompatibles con datos existentes |
| 4 | Slice offline HU-012 | Ordenes 2 y 3 segun dependencias reales | Envio real de correo o bypass de validacion humana |
| 5 | Seguridad y configuracion del workspace | Orden 1 | Secretos, credenciales o configuracion local versionada |
| 6 | Evidencia, benchmarks y documentacion de baseline | Ordenes 2 a 5 | Conteos, hashes o conclusiones obsoletas |
| 7 | Paquetes SEU, DSI e Historia Viva | Revision humana previa | Datos personales, enlaces institucionales o decisiones aun no firmadas |
| 8 | Fuentes academicas y, por separado, artefactos renderizados indispensables | Evidencia estabilizada | Binarios redundantes, entregables desactualizados o problemas de redistribucion |

Los logs y snapshots de `.playwright-mcp/`, runtime local y artefactos LaTeX
reproducibles no forman parte de esta secuencia salvo justificacion individual.

El inventario exhaustivo del corte esta en
`Documentos/PoC/Inventario-Worktree-Issue-2-2026-09-05.csv`. Registra por path
estado Git, drift de modo y contenido, intencion, owner aparente, categoria,
decision de publicacion y riesgo. Ninguna fila queda con owner o clasificacion
desconocidos. La decision mas frecuente es `NO_STAGEAR_RUIDO_DE_MODO`: el
cambio de permisos no convierte una fuente ya trackeada en contenido nuevo ni
justifica republicarla.

Las decisiones `NO_PUBLICAR`, `NO_REDISTRIBUIR` o `REVISAR` se aplican al
incremento observado, no reescriben el historial remoto. En particular, las
fuentes academicas/institucionales, la correspondencia, los paquetes de
validacion, los logs de navegador y los metadatos internos requieren una
decision humana antes de incorporarse a un nuevo commit publico.

## Bloqueo vigente

Una rama apuntando solamente a `HEAD` no preserva los cambios no commiteados y
daria una falsa sensacion de respaldo. Por eso la referencia de recuperacion
debe incluir el diff binario de archivos trackeados, los archivos no trackeados
y checksums, bajo un directorio local explicitamente excluido de Git.

El respaldo se creo en `.local-recovery/pre-saneamiento-2026-09-05/`, con
permisos locales restrictivos y exclusion explicita en `.gitignore`. Contiene:

- `tracked.patch`: diff binario completo respecto de `39312a1`;
- `untracked.tar.gz`: 55 miembros que cubren los paths no trackeados al momento
  del corte; la diferencia con las 51 entradas de estado corresponde al
  colapso de directorios;
- `status-porcelain-v2.txt`: inventario machine-readable del estado;
- `tracked-name-status.txt`: nombres y estados de archivos trackeados;
- `SHA256SUMS`: hashes de los cuatro artefactos anteriores.

El patch fue parseado con `git apply --numstat`, el archivo fue listado con
`tar -tzf` y todos los hashes finalizaron `OK`. El respaldo es deliberadamente
local: puede contener material no publicable y no debe agregarse a Git.

Para recuperar en un checkout limpio del commit observado, primero se debe
verificar `SHA256SUMS`, aplicar `tracked.patch` y recien despues extraer
`untracked.tar.gz` sobre la raiz. Esa operacion es destructiva si se ejecuta
sobre un worktree con cambios y requiere una decision humana previa; este
documento no la ejecuta automaticamente.

El ticket siguiente debe normalizar modos segun el indice, conservar las tres
excepciones ejecutables historicas y separar los commits tematicos segun la
agrupacion precedente.

## Decision

El inventario y el respaldo exigidos por el issue #2 estan completos. Esto no
constituye aprobacion de publicacion: la revision manual del contenido elegido
debe ocurrir por allowlist en el issue #3 antes de cada commit, porque revisar
en bloque PDFs, ZIP y material institucional que no se va a publicar agregaria
riesgo sin aportar evidencia al incremento. Hasta entonces, la publicacion del
worktree permanece explicitamente bloqueada.
La revision manual de contenido no forma parte del cierre de este issue; queda
como condicion obligatoria del saneamiento y de cada commit del issue #3.

El saneamiento posterior debe restaurar los modos declarados en el indice archivo
por archivo; no debe usar `chmod -R`, `reset`, `checkout` ni `clean`. Los tres
scripts ya trackeados como `100755` se conservan como excepciones historicas.
