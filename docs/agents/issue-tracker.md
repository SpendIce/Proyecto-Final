# Issue tracker: GitHub

Los issues y specs de este repositorio viven en GitHub Issues de
`SpendIce/Proyecto-Final`. Usar `gh` con `--repo SpendIce/Proyecto-Final`
en todas las operaciones para no confundir este fork con el remoto historico
`BecerraIgnacio/Proyecto-Final`.

## Convenciones

- Crear: `gh issue create --repo SpendIce/Proyecto-Final --title "..." --body "..."`
- Leer: `gh issue view <numero> --repo SpendIce/Proyecto-Final --comments`
- Listar: `gh issue list --repo SpendIce/Proyecto-Final --state open`
- Comentar: `gh issue comment <numero> --repo SpendIce/Proyecto-Final --body "..."`
- Etiquetar: `gh issue edit <numero> --repo SpendIce/Proyecto-Final --add-label "..."`
- Quitar etiqueta: `gh issue edit <numero> --repo SpendIce/Proyecto-Final --remove-label "..."`
- Cerrar: `gh issue close <numero> --repo SpendIce/Proyecto-Final --comment "..."`

## Pull requests como superficie de triage

**PRs como superficie de solicitudes: no.**

## Cuando una skill indica publicar en el tracker

Crear un issue en `SpendIce/Proyecto-Final`.

## Cuando una skill indica obtener el ticket relevante

Ejecutar:

`gh issue view <numero> --repo SpendIce/Proyecto-Final --comments`

## Operaciones de wayfinding

- El mapa es un issue con etiqueta `wayfinder:map`.
- Sus tickets hijos deben vincularse como sub-issues de GitHub.
- Las dependencias deben registrarse mediante dependencias nativas de GitHub.
- Si la funcionalidad no esta disponible, usar `Blocked by: #<numero>` en el cuerpo.
- Un ticket esta disponible cuando todos sus bloqueantes estan cerrados y no tiene responsable asignado.
- Al tomarlo, asignarlo mediante `gh issue edit <numero> --repo SpendIce/Proyecto-Final --add-assignee @me`.
