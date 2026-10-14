# Runbook de protección de la rama `main` — Agente 1

- **Estado:** preparado y **no ejecutado**. La protección de `main` **no está
  activa** al escribir este documento (verificado el 2026-10-14, sección 2). Los
  comandos de la sección 4 los corre Juani cuando termina la ola de merges en
  curso; activarlos antes traba las ramas de los otros tickets.
- **Alcance:** dejar activo el circuito por PR para los cambios controlados del
  Agente 1: PR obligatorio, sin push directo a `main` y `agente1-ci` como check
  requerido. No incluye la revisión obligatoria de un segundo humano, que llega
  con el traspaso (sección 6).
- **Relacionados:** decisión #66 (control de cambios y de configuración),
  issue #90 (CI del Agente 1), issue #96 (este circuito), issue #80 (extracción
  del repositorio del Agente 1), ADR 0007 (traspaso),
  `Implementacion/Agente1/PROCEDIMIENTO-CORTE-DE-VERSION.md`.

## 1. Qué resuelve y qué no

Deja `main` con el circuito mínimo de un cambio controlado (`CONTEXT.md`,
*Cambio controlado*): todo lo que define cómo se comporta el Agente 1 entra por
PR, con la CI del Agente 1 en verde. Es la parte de la decisión #66 que toca
GitHub; el resto del control (aprobación por clase, changelog, corte de versión)
vive en el procedimiento y en el `CHANGELOG.md`.

Este documento **no**:

- activa la protección (la activa Juani con los comandos de la sección 4);
- agrega revisión obligatoria de un segundo humano: hasta el traspaso el autor
  es único y su estado se declara «B: con observaciones», que admite que el
  autor integre su propio cambio con la CI verde (sección 6);
- hace push, merge ni toca la configuración del repositorio desde este entorno.

## 2. Estado actual verificado (2026-10-14)

`main` **no está protegida**. Comprobación y resultado real:

```console
$ gh api repos/SpendIce/Proyecto-Final/branches/main/protection
{"message":"Branch not protected","documentation_url":"https://docs.github.com/rest/branches/branch-protection#get-branch-protection","status":"404"}
```

```console
$ gh api repos/SpendIce/Proyecto-Final/branches/main \
    --jq '{protected, hoja: .protection.enabled, nivel: .protection.required_status_checks.enforcement_level}'
{"protected":false,"hoja":false,"nivel":"off"}

$ gh api repos/SpendIce/Proyecto-Final/rulesets --jq 'length'
0
```

Consecuencia: **hoy `main` acepta push directo.** No hay branch protection ni
ruleset que lo impida. El repositorio es público, la rama por defecto es `main`
y la credencial de `gh` de este entorno tiene rol `admin`, así que alcanza con
los comandos de la sección 4 para activarla.

## 3. Por qué el check requerido es un job que siempre corre

La trampa está descrita en el issue #96: `agente1-ci` filtraba por `paths` en el
evento y solo corría si cambiaba `Implementacion/Agente1/**`. Un workflow
salteado por un filtro de `paths` **no genera el check**, y la protección deja
al PR en «Expected — Waiting for status to be reported» para siempre: un PR que
solo toca documentación queda trabado. Lo documenta GitHub en *Troubleshooting
required status checks* («Handling skipped but required checks»).

**Resuelto con un job que siempre reporta** (`.github/workflows/agente1-ci.yml`):

- se quitaron los filtros `paths` del evento; el workflow corre en todo PR y
  push a `main`;
- el job `cambios` siempre corre, compara contra la base e informa si el cambio
  toca rutas del Agente 1;
- el job `suite` corre solo si hay cambios del Agente 1;
- el job **`agente1-ci`** usa `if: always()`, evalúa a mano el resultado de
  `suite` y **siempre reporta**. Es el único check que la protección exige.

Un job salteado por un `if:` reporta «Success» igual que uno verde; el job
`agente1-ci` no se apoya en esa sutileza: corre siempre y falla si la detección
no completó o si la suite no pasó.

**Alternativa descartada (ruleset acotado a esas rutas).** Un ruleset no tiene
forma de acotar *el check requerido* por archivo cambiado: las reglas que
aceptan patrones de archivos son «Restrict file paths» (bloquea pushes a rutas,
no acota checks) y «Required reviewers» (revisores por equipo, solo en repos de
organización; este repo es de usuario). Acotar el check por rutas además
debilitaría el requisito: los cambios de documentación a `main` dejarían de
pasar por PR. La opción elegida cubre **todos** los PR a `main` con un único
check estable, y el workflow viaja por `git` con el repo (a diferencia de la
configuración de la protección, que no viaja: sección 7).

Nombre del check requerido: **`agente1-ci`** (es el `name:` del job, que es lo
que la protección exige).

## 4. Activación (la corre Juani)

**Antes de activar**, dos requisitos de orden:

1. Este cambio (workflow + plantilla + este runbook) ya tiene que estar en
   `main`, para que el job `agente1-ci` exista en el workflow de la rama.
2. Abrir un PR trivial a `main` y confirmar que el check `agente1-ci` aparece y
   pasa. Sirve para verificar el nombre exacto del check y que el workflow
   reporta. Si el nombre difiere, ajustar `contexts` en el comando de abajo.

Comando exacto (una sola llamada: activa PR obligatorio, sin push directo y con
`agente1-ci` como check requerido, y sin revisor obligatorio):

```bash
gh api -X PUT repos/SpendIce/Proyecto-Final/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["agente1-ci"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false
}
JSON
```

Qué hace cada campo, y por qué:

| Campo | Valor | Por qué |
| --- | --- | --- |
| `required_status_checks.contexts` | `["agente1-ci"]` | El job que siempre reporta (sección 3). |
| `required_status_checks.strict` | `true` | Exige la rama al día con `main` antes de mergear. Es el valor por defecto y el conservador; si en la ola de merges resulta molesto, se cambia a `false` (menos builds, pero permite mergear sin re-probar contra el último `main`). |
| `enforce_admins` | `true` | **Sin push directo de verdad.** Con `false`, el rol `admin` de Juani queda exento y podría seguir pusheando a `main` a mano, que es justo lo que se quiere evitar. Si necesita una excepción puntual puede desactivar la protección (sección 8); no es un bloqueo sin salida. |
| `required_pull_request_reviews` no nulo (con `required_approving_review_count: 0`) | | Hace obligatorio el PR **sin** exigir aprobación de otro. Necesario hasta el traspaso: el autor es único y GitHub no permite autoaprobarse. |
| `restrictions: null` | | No se restringe quién pushea (repo de usuario; la restricción por usuario/equipo es de organización). |
| `allow_force_pushes` / `allow_deletions` | `false` | Sin force push ni borrado de `main`. |
| `required_conversation_resolution` | `false` | No se exige resolver todos los comentarios: no hay revisor hasta el traspaso. |

Alternativa al `contexts` por nombre: `checks` con el `app_id` fijo de GitHub
Actions (`15368`) ata el check a esa app; es más estricto pero más rígido si
GitHub cambia el id. Se deja `contexts` por simplicidad, igual que el resto de
la documentación del proyecto.

## 5. Verificación después de activar

```bash
# La rama queda protegida y con el check requerido:
gh api repos/SpendIce/Proyecto-Final/branches/main/protection \
  --jq '{check: .required_status_checks.contexts, estricto: .required_status_checks.strict,
         admins: .enforce_admins.enabled, pr_obligatorio: (.required_pull_request_reviews != null),
         aprobaciones: .required_pull_request_reviews.required_approving_review_count}'
```

Esperado: `check: ["agente1-ci"]`, `estricto: true`, `admins: true`,
`pr_obligatorio: true`, `aprobaciones: 0`.

Prueba de un cambio controlado y de un PR de solo documentación:

```bash
# 1. PR que solo toca documentación: el check agente1-ci debe pasar y permitir el merge.
# 2. Push directo a main: debe rechazarse.
git push origin main
#    remote: error: GH006: Protected branch update failed for refs/heads/main.
```

## 6. Qué cambia después del traspaso

El traspaso entrega el Agente 1 a los responsables que lo sostienen cuando el
autor egresa (`CONTEXT.md`, *Traspaso*; ADR 0007; repositorio extraído #80):
**Responsable de operación** (Dirección de la carrera de Ingeniería en
Informática, que puede delegar en DSI) y **Responsable de evolución** (alumnos
de 4to año que continúan el P100). Con más de un actor, la revisión deja de ser
opcional:

| Punto | Ahora (autor único) | Después del traspaso (repo extraído #80) |
| --- | --- | --- |
| Aprobaciones | `required_approving_review_count: 0` — el autor integra con la CI verde | `required_approving_review_count: 1` (o más), aprobación de otro con permiso de escritura |
| Code owners | `require_code_owner_reviews: false` | `require_code_owner_reviews: true` + `CODEOWNERS` que mapea las rutas controladas a los owners |
| Quién pushea | sin restricción (repo de usuario) | si el repo queda en una organización, `restrictions` limita el push a equipos/usuarios de los owners |
| Check requerido | `agente1-ci` | sigue siendo `agente1-ci`, pero el filtro de rutas del job `cambios` cambia: en el repo extraído el código está en la raíz (`src/`, `tests/`), no en `Implementacion/Agente1/` |
| Administradores | `enforce_admins: true` | se mantiene; los bypass se otorgan a los owners si hace falta, vía ruleset |

Comando de la transición (a correr **en el repo extraído**, no acá):

```bash
gh api -X PATCH repos/<owner>/<repo-extraido>/branches/main/protection/required_pull_request_reviews \
  -H "Accept: application/vnd.github+json" \
  -f required_approving_review_count=1 \
  -F require_code_owner_reviews=true
```

`CODEOWNERS` y la restricción por equipo solo se pueden poblar después de
definir los owners en el repo extraído; hoy no existen como usuarios/equipos.

## 7. La configuración tiene que viajar al repo extraído (#80)

La protección de rama **es configuración del repositorio, no archivos**: no
viaja con `git filter-repo`, ni con un `git clone`, ni con el `agente1-ci.yml`.
Al extraer el repositorio (#80) hay que **volver a activarla** allí. Dos vías:

1. **Repetir este runbook** contra el repo extraído: mismo comando de la
   sección 4 con `--repo` cambiado y el `contexts` verificado. Simple y
   suficiente; por eso este documento entra en el inventario de documentación
   que #80 se lleva.
2. **Exportar/importar por rulesets** (`gh api repos/.../rulesets`), útil si el
   repo extraído queda en una organización y se prefieren rulesets a la
   protección clásica. No se usa hoy porque la protección clásica alcanza para
   un repo de usuario.

Anotado para #80: el inventario del repo extraído debe llevar este runbook, y el
procedimiento de extracción debe incluir un paso de «activar la protección en el
repo nuevo» con la sección 4 de acá.

## 8. Repetir o revertir

```bash
# Quitar la protección (por ejemplo, para una emergencia puntual):
gh api -X DELETE repos/SpendIce/Proyecto-Final/branches/main/protection

# Volver a activarla:
#   repetir el comando de la sección 4.
```

El cambio de emergencia del Agente 1 (`CONTEXT.md`) no es una excepción a este
circuito: la respuesta es suspender el agente y volver por el circuito normal,
no pushear a `main` por afuera.
