# Checklist consolidado HU-010 / HU-011

Completar una copia por fila de `muestra-validacion.csv`. Estado inicial:
`PENDIENTE`. No completar identidades ni resultados antes de una sesión real.

## Identificación

| Campo | Valor |
|---|---|
| ID de muestra | |
| ID de actividad | |
| Historia / canal | |
| Correlation ID | |
| Hash del borrador | |
| Persona revisora | |
| Rol / área | |
| Fecha y hora | |

## Escala común

| Puntaje | Interpretación |
|---:|---|
| 1 | Inaceptable: impide utilizar el borrador como base |
| 2 | Insuficiente: requiere correcciones sustanciales |
| 3 | Adecuado con observaciones: requiere ajustes menores |
| 4 | Adecuado: cumple el criterio en esta instancia |

Un puntaje menor que 3 requiere una observación concreta. Para
`alucinaciones`, 4 significa que no se detectaron afirmaciones sin respaldo;
no sustituye el contraste humano con la fuente.

Para `APROBADO_COMO_BORRADOR`, los seis puntajes deben ser 3 o 4 y todos los
controles obligatorios deben estar marcados. No se promedian puntajes: un 1 o 2
impide aprobar esa muestra.

## Evaluación

| Criterio | Control | Puntaje 1–4 | Observación / evidencia |
|---|---|---:|---|
| Precisión | Hechos, fecha, organización, contacto y lugar coinciden con la fuente | | |
| Tono | Registro adecuado para comunicación institucional | | |
| Ajuste de canal | Formato pertinente para gacetilla, Instagram o LinkedIn | | |
| Gramática | Ortografía, puntuación y claridad correctas | | |
| Longitud | Extensión legible y compatible con la política provisional | | |
| Alucinaciones | No agrega hechos, enlaces, contactos, lugares ni aprobaciones | | |

## Controles obligatorios

- [ ] Contrasté todos los hechos con el insumo autorizado.
- [ ] El texto no afirma estar aprobado, validado, enviado ni publicado.
- [ ] No contiene datos personales o sensibles innecesarios.
- [ ] Registré los defectos y correcciones de forma reproducible.
- [ ] El borrador conserva su condición de `BORRADOR — NO PUBLICAR`.

## Decisión sobre el borrador

- [ ] `APROBADO_COMO_BORRADOR`
- [ ] `REQUIERE_AJUSTES`
- [ ] `RECHAZADO`
- [x] `PENDIENTE`

La primera opción sólo permite avanzar al siguiente control humano; no autoriza
publicar, compartir ni enviar.
