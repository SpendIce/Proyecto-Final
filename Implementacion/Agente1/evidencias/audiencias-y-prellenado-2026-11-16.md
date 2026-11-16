# Audiencias institucionales y prellenado de correo — 2026-11-16

## Qué se hizo

Se agregó el paso posterior a la aprobación de un borrador de gacetilla: armar
una **URL de composición de Gmail** con asunto, cuerpo y destinatarios en Cco,
**sin enviar nada**. El envío lo hace la persona desde su cliente de correo.

Este camino **no es `gmail.send`**: no hay llamado de red, no se crea un
borrador por API, no se pide el scope `gmail.compose` y no queda rastro de
envío. El sistema no puede saber si la persona lo mandó; el documento de
interfaz ya aceptó no pedirlo.

## Fuente

- Archivo: `Listado Grupos.pdf` (2 páginas), aportado por el autor del PPS.
- Extracción: `pdftotext -raw "Listado Grupos.pdf" -`.
- Fecha de extracción: 2026-11-16.
- Resultado: **18 grupos**, todos del dominio institucional.
- Las direcciones **no** se versionan: viven en
  `~/.config/agente1/audiencias-institucionales.json` con `chmod 600`. El repo
  versiona el loader y el esquema
  `src/agente1/contracts/audiencias_institucionales_v1.schema.json`.

## Catálogo externo

Ruta: `~/.config/agente1/audiencias-institucionales.json` (`-rw-------`).

Versión `audiencias_institucionales_v1`, `estado_general:
PENDIENTE_APROBACION_SEU`, 18 audiencias. Todas con
`estado_aprobacion: "PENDIENTE_SEU"`.

| id | nombre | categoría | alcance | usos candidatos | origen del uso |
|---|---|---|---|---|---|
| `alumnos_geomatica` | Alumnos Geomática | alumnos | segmentado | — | PENDIENTE_SEU |
| `alumnos_ingenieria` | Alumnos Ingeniería | alumnos | segmentado | — | PENDIENTE_SEU |
| `alumnos_posgrados` | Alumnos Posgrados | alumnos | segmentado | `newsletter` | PENDIENTE_SEU |
| `alumnos_hys` | Alumnos Tec Higiene y Seguridad | alumnos | segmentado | — | PENDIENTE_SEU |
| `alumnos_tec_utn` | Alumnos Tec UTN | alumnos | segmentado | — | PENDIENTE_SEU |
| `cfoim` | CFOIM | institucional | desconocido | — (vacío) | PENDIENTE_SEU |
| `comunidad` | Comunidad FIE | comunidad | masivo | `fallecimiento` | PENDIENTE_SEU |
| `docentes_ingenieria` | Docentes Ingeniería | docentes | segmentado | `convocatoria_interna` | PENDIENTE_SEU |
| `docentes_tecnicatura` | Docentes Tecnicatura | docentes | segmentado | `convocatoria_interna` | PENDIENTE_SEU |
| `fieinforma` | FIE Informa | institucional | masivo | `difusion_de_actividad`, `cronica_de_evento`, `aviso_de_otra_area`, `saludo_o_efemeride` | **DECISION_USUARIO** |
| `graduados_civiles` | Graduados Civiles | graduados | segmentado | `newsletter` | PENDIENTE_SEU |
| `graduados_oim` | Graduados OIM | graduados | desconocido | — (vacío) | PENDIENTE_SEU |
| `oim_actividad` | Graduados OIM en Actividad | graduados | desconocido | — (vacío) | PENDIENTE_SEU |
| `personal_gestion` | Personal de Gestión | personal | interno | `convocatoria_interna` | PENDIENTE_SEU |
| `plana_mayor` | Plana Mayor | conducción | interno | — | PENDIENTE_SEU |
| `secretaria_academica` | Secretaria Académica | institucional | interno | `difusion_de_actividad` | **DECISION_USUARIO** |
| `suboficiales` | Suboficiales | personal | interno | — | PENDIENTE_SEU |
| `soldados` | Soldados | personal | interno | — | PENDIENTE_SEU |

`cfoim`, `graduados_oim` y `oim_actividad` quedaron con
`usos_candidatos: []` y una observación porque sus siglas no están
documentadas en el repo; no se infiere su alcance.

## Procedencia (no inflar)

- `fieinforma` para gacetillas de difusión y `secretaria_academica` para
  actividades de carrera: **decisión del autor del PPS**, registrada como
  `DECISION_USUARIO`, no aprobación SEU.
- «La lista son los correos más importantes y representativos»: dicho al autor
  por un tercero, sin acta. Registrado como `SUPUESTO` en el catálogo.
- El resto de los mapeos: propuesta técnica `PENDIENTE_SEU`.
- Los tipos de gacetilla siguen `PROVISIONAL_NO_INSTITUCIONAL` en
  `contracts/tipos_gacetilla_v1.json`; este trabajo no los promueve.

## Módulo y comportamiento

`Implementacion/Agente1/src/agente1/audiencias.py`:

- `cargar_audiencias(path)` — loader fail-closed: versión, fuente,
  `total_grupos` coherente, ids únicos, direcciones válidas con `email_valido`,
  sin duplicados, campos obligatorios y estados cerrados. Un archivo inválido
  no produce catálogo; el error sólo lleva un código, sin direcciones.
- `audiencias_para(tipo, catalogo, es_de_carrera=False)` — ids del mapeo.
- `construir_prellenado(tipo, asunto, cuerpo, catalogo, seleccion=None)` —
  `Prellenado(url, destinatarios, cuerpo_portapapeles, audiencias_pendientes)`.
  No filtra por aprobación; devuelve pendientes para que la interfaz lo
  muestre.
- `url_compose(destinatarios, asunto, cuerpo=None)` — base
  `https://mail.google.com/mail/?view=cm&fs=1&tf=1`, `urlencode(...,
  quote_via=quote)`, destinatarios en `bcc`, nunca en `to`.
- `MAX_URL_COMPOSE = 1800`. Si el cuerpo no entra, no viaja en la URL y vuelve
  en `cuerpo_portapapeles`. La interfaz lo copia y lo indica.
- El cuerpo debe ser el de la **revisión aprobada** (su texto y su hash), no
  uno regenerado.
- Sin imports de HTTP ni de `gmail_envio`; no hay envío, borrador por API ni
  scope `gmail.compose`.

## Verificación ejecutada

Catálogo real y validador real de `gmail_envio` (18/18, sin imprimir
direcciones):

```bash
cd /home/spendice/Documents/Archivos_Facu/Proyecto-Final/Implementacion/Agente1
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from agente1.audiencias import cargar_audiencias
from agente1.gmail_envio import _validar_destinatarios

catalogo = cargar_audiencias(
    Path.home() / ".config/agente1/audiencias-institucionales.json"
)
validas = _validar_destinatarios(
    [a.direccion for a in catalogo.audiencias], maximo=1000
)
print(len(catalogo.audiencias), len(validas))
PY
# -> 18 18
```

Resultado observado: `18 18`; las 18 quedaron `PENDIENTE_SEU` y sólo
`fieinforma` y `secretaria_academica` con `origen_uso: DECISION_USUARIO`.

Pruebas y linter:

```bash
cd /home/spendice/Documents/Archivos_Facu/Proyecto-Final/Implementacion/Agente1
uv run pytest -q tests/test_audiencias.py   # 35 passed
uv run pytest -q                            # 2484 passed, 11 skipped
uv run ruff check .                         # All checks passed!
```

Cobertura de `tests/test_audiencias.py`: los 18 grupos cargan y validan; URL
con 18 destinatarios ≤ 1800 y sin `body`; cuerpo corto en la URL y cuerpo
largo en `cuerpo_portapapeles`; duplicados exactos colapsan; estado inválido y
campos ausentes fallan cerrado; ningún archivo de `src/` contiene el dominio
institucional; el módulo no importa `gmail_envio` ni abre sockets.

## Env operativo

`~/.config/agente1/gmail-destinatarios.env` (`-rw-------`):

```text
AGENTE1_GMAIL_MODO=prueba
AGENTE1_GMAIL_DESTINATARIOS_APROBADOS=
```

La lista aprobada queda vacía a propósito. Las 18 audiencias no se cargan en
`AGENTE1_GMAIL_DESTINATARIOS_APROBADOS` ni en
`AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`. Este env no habilita envíos.

## Fuera de alcance (no se hizo)

- No se envía correo, no se crean borradores en Gmail y no se activa el modo
  producción.
- No se llenó la lista aprobada ni se aprobó ninguna audiencia.
- No se hardcodearon direcciones reales en `.py`, tests ni documentación
  versionada.
- No se reemplazó el circuito de aprobación ni el botón de decisión. En `main`
  no está la interfaz web definitiva: vive en la rama `feat/149-canal-web`
  (`src/agente1/web/`), donde este trabajo se integró con la decisión de
  contenido y el prellenado; la evidencia de esa rama amplía este registro.
- No se tocó `gmail_envio.py`, la auditoría D2 ni los contratos de
  HU-012/HU-014.
- No se cortó versión ni se regeneró `manifest-version.json`: el archivo nuevo
  bajo `src/` es controlado y el próximo corte debe subir la versión y
  regenerar el manifest antes de instalar (ADR 0010). Tampoco se commiteó.
