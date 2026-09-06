# Domain docs

Reglas para que las engineering skills consuman la documentacion de dominio de este repositorio.

## Antes de explorar

Leer, cuando existan:

- `CONTEXT.md` en la raiz.
- `docs/adr/`, seleccionando los ADR relacionados con el area de trabajo.

Si estos archivos no existen, continuar sin advertirlo ni proponer su creacion anticipada. `/domain-modeling`, normalmente mediante `/grill-with-docs` o `/improve-codebase-architecture`, los crea cuando se resuelven terminos o decisiones que justifican conservarlos.

Ademas, siguen vigentes las fuentes de verdad y el orden de lectura definidos en `AGENTS.md` y `CLAUDE.md`.

## Estructura

Este repositorio usa un esquema single-context:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── Implementacion/
```

`CONTEXT.md` contiene el glosario y el modelo de dominio compartido. `docs/adr/` contiene decisiones arquitectonicas dificiles de revertir.

## Vocabulario

Al nombrar conceptos del dominio en issues, especificaciones, pruebas o propuestas, usar los terminos definidos en `CONTEXT.md`. No reemplazarlos por sinonimos que el glosario descarte.

Si falta un concepto, revisar primero las fuentes institucionales del repositorio. Si sigue siendo una brecha real, registrarla para `/domain-modeling`; no inventar terminologia institucional.

## Conflictos con ADR

Si una propuesta contradice un ADR existente, indicarlo expresamente en lugar de reemplazar silenciosamente la decision.
