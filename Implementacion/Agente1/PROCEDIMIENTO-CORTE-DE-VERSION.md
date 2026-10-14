# Procedimiento — cortar una versión del Agente 1

Cómo se publica una **versión del agente**: el estado etiquetado que se instala
en el host, con la huella de todo lo controlado que contiene (`CONTEXT.md`,
*Versión del agente*). Está escrito para que lo siga alguien que no escribió el
código: no hace falta entender la arquitectura, sólo ejecutar los pasos en
orden.

Relacionados: ADR 0010 (fail-closed al arrancar), issue #92 (manifest de
versión), issue #93 (tag, changelog y versión en la auditoría), issue #66
(control de cambios). El manual de operación (#81) cuenta otra cosa: cómo se
opera el agente día a día.

## 1. Qué es una versión y cuándo se corta

Una versión se corta **cada vez que cambia algo controlado y el cambio se
instala en el host**. Se instala cuando el operador pone en el host el checkout
de `main` de ese tag. Entre versiones, el host no se toca.

Las clases de cambio y quién las aprueba están en la resolución del issue #66.
Para el número de versión (`X.Y.Z`, tag `agente1-vX.Y.Z` sobre `main`):

| Clase | Qué es | Número |
|---|---|---|
| **Mayor** | cambia un contrato de interfaz (schema, contrato de planilla o de insumos, contrato de Historia Viva) | sube `X`, `Y=Z=0` |
| **Menor** | capacidad nueva, prompt o política | sube `Y`, `Z=0` |
| **Parche** | corrección | sube `Z` |

La versión **sale de un solo lugar**: `pyproject.toml`, `[project].version`. No
se repite a mano en ningún otro archivo. El manifest de versión, la auditoría de
cada pieza y el `CHANGELOG.md` la citan; el procedimiento la escribe una sola
vez, en `pyproject.toml`.

## 2. Pasos

Todos los comandos se corren desde `Implementacion/Agente1/`.

### Paso 1 — Decidir la clase y el número

Mirar los cambios controlados desde la última versión. Elegir la clase más alta
que corresponda y calcular el número nuevo. Anotarlo: es el número que se usa en
los tres lugares siguientes (no debe repetirse a mano, pero tiene que ser el
mismo).

### Paso 2 — Subir la versión en `pyproject.toml`

Editar `[project].version` con el número decidido. Es la única fuente.

```bash
# ejemplo: de 0.1.0 a 0.2.0 (Menor)
sed -i 's/^version = "0.1.0"/version = "0.2.0"/' pyproject.toml
```

### Paso 3 — Regenerar el manifest de versión

El manifest fija el sha256 de todo lo controlado (código, prompts, políticas,
contratos, migraciones, `uv.lock`, `pyproject.toml`, `scripts/`, `systemd/`,
ADR 0010) y lleva la versión. Se regenera **después** de cualquier cambio bajo
esas rutas:

```bash
uv run python scripts/manifest_version.py --salida manifest-version.json
```

Es determinista: el mismo árbol produce el mismo archivo byte a byte.
`manifest-version.json` vive en la raíz del Agente 1, fuera de las rutas que
recorre, así que no se controla a sí mismo.

### Paso 4 — Agregar la entrada al `CHANGELOG.md`

Una entrada por versión, con los cambios controlados que la componen, su clase
y la referencia del issue o rama que los introdujo. Ver la sección 4 más abajo.

### Paso 5 — Verificar y commitear

```bash
uv run pytest -q          # la suite entera, verde
uv run ruff check .       # sin hallazgos
```

Commitear con el número de versión en el mensaje. Si el repo ya tiene `main`
protegida con PR obligatorio (#96), el camino es una rama y un PR con la CI
verde; hoy el autor integra por ramas `ticket/NN` con merge local.

### Paso 6 — Etiquetar `main`

Con el merge ya en `main`:

```bash
git -C <checkout> fetch origin
git -C <checkout> tag -a agente1-v0.2.0 -m "Agente 1 0.2.0"
git -C <checkout> push origin agente1-v0.2.0
```

El tag va **sobre `main`**, no sobre la rama de trabajo: es el estado que se
instala. La versión instalada en el sistema de demostración para el laboratorio
tiene que quedar etiquetada así.

### Paso 7 — Instalar en el host

El operador pone en el host el checkout del tag y su `manifest-version.json`
(viaja con la versión: se regenera acá, no en el host). El arranque en modo
operación verifica la integridad y no arranca si algo no coincide (ADR 0010).

## 3. El manifest viejo entre versiones (importante)

**Después de mergear cualquier cambio controlado, el `manifest-version.json`
versionado queda viejo y el gate fail-closed rechaza el arranque en modo
operación.** Un archivo del repo cambió y el manifest todavía tiene su hash
anterior: el agente no arranca y la auditoría (`logs/integridad-arranque.jsonl`)
muestra el archivo y los dos hashes.

**Eso es por diseño.** El manifest se genera al cortar la versión, no en cada
cambio: si se regenerara en cada merge, el manifest dejaría de ser «la huella de
lo que se instaló» y sería «la huella de lo último que se tocó», que no dice
nada. Entre versiones, el host corre la versión etiquetada anterior; nadie
arranca la `main` sin cortar.

La salida del estado viejo es el **Paso 3**: regenerar el manifest al cortar.

**No agregar una verificación en CI que exija el manifest siempre fresco.** Un
check así mataría el flujo entre versiones (todo merge lo rompería) y forzaría a
regenerar el manifest sin cortar versión, que es exactamente lo que el ADR 0010
quiere evitar. Lo que prueba la CI es la suite y el linter; la frescura del
manifest es parte del corte, no del merge.

## 4. El `CHANGELOG.md`

`CHANGELOG.md` tiene dos secciones:

- **Versiones.** Una entrada por versión etiquetada (`## [X.Y.Z] - AAAA-MM-DD`),
  con los cambios controlados agrupados por clase (Mayor / Menor / Parche). Cada
  cambio se referencia por el issue o la rama que lo introdujo. La versión sale
  de `pyproject.toml`; el changelog sólo la cita.
- **Configuración.** Ver la sección 5.

## 5. La sección *Configuración* (cambios pedidos a DSI)

Hay cambios que **no generan versión del agente**: los que se le piden a DSI en
la consola de Google (Workspace y credenciales), porque cambian la configuración
que Google guarda —IDs, scopes, cuenta técnica, unidad compartida— y no el
código, los prompts ni las políticas.

Cada pedido se anota en la sección *Configuración* de `CHANGELOG.md` con
**fecha, motivo y quién lo aprobó**. Se completa **al pedir el cambio**, no
después. No abren un issue ni un PR: dependen de que DSI use GitHub, y DSI no
lleva registro propio (issue #66, adenda del 13/10). La huella sin secretos de
esa configuración se compara con la de la corrida anterior y, si cambió, se
registra y se avisa al operador (issue #94); el registro durable para el
laboratorio es esta tabla, porque el log de Google se pierde a los 6 meses.

## 6. El manifest de corte y el dataset sintético

`scripts/manifest_corte.py` emite la evidencia de un corte (el laboratorio la
revisa): **con qué versión del agente y con qué configuración** se produjo esa
evidencia. Referencia `version` y `manifest_version_sha256`; no mantiene su
propia lista de archivos controlados.

Además hashea el dataset que alimenta el corte (`data/actividades_sinteticas.csv`)
en `datos_sinteticos_sha256`. El dataset **no es un archivo controlado** —es un
dato operativo, lo mantiene su dueño (`CONTEXT.md`)—, por eso queda fuera del
manifest de versión; pero sin su hash la evidencia del corte no se puede
reproducir, así que el manifest de corte lo ata al corte concreto. Es un dato de
entrada del corte, no una segunda lista de fuentes.
