# Ejemplo aprobado 2025 — juego completo de anexos

Material de referencia: el juego de anexos de un proyecto que **pasó la revisión de
laboratorio** en el ciclo 2025. Sirve como vara de comparación para calibrar el
nivel de detalle, no como plantilla a copiar.

- **Origen:** archivo `seguridad-20261015T192808Z-1-001.zip`, aportado por Juani el
  15/10/2026 (ejemplo de un alumno del año anterior).
- **Anonimizado:** el nombre del alumno se reemplazó por `[alumno]` en todos los
  archivos, incluidos los metadatos. El resto quedó tal cual.
- **No se versiona** `3.0 - Procedimiento 2025.docx`: es byte a byte el mismo que ya
  está en `Revision-Laboratorio-2025/` (mismo md5).

## Archivos

| Archivo | Qué es |
|---|---|
| `3.1 - Anexo 1 - Presentación 2025.docx` | La presentación, como la envió el alumno (04/11/2025). |
| `3.2 - Anexo 2 - Calidad 2025.docx` | La lista de control de calidad, como la envió el alumno (15/11/2025). |
| `3.2 - … -Postreunion.docx` | La misma, **completada por el laboratorio** después de la reunión (18/11/2025). |
| `3.3 - Anexo 3 - Seguridad 2025.docx` | La lista de control de seguridad, como la envió el alumno (15/11/2025). |
| `3.3 - … -Postreunion.docx` | La misma, **completada por el laboratorio** (18/11/2025). |

Las versiones *Postreunion* son las más útiles: muestran qué agrega y qué corrige el
laboratorio sobre lo que uno entrega.

## Qué enseña

**Escala real de lo que se aprueba.** Medido convirtiendo los `.docx` a PDF:

| | Ejemplo aprobado | Anexo propio (referencia, oct-2026) |
|---|---|---|
| Anexo 1 | 2 páginas, 7 filas, **una sola tabla** | 13 páginas, 77 filas, 10 tablas |
| Anexo 2 | 2 páginas, 12 atributos | 3 páginas, 43 atributos |
| Anexo 3 | 1 página, **7 ítems** | 5 páginas, 74 ítems |

**El Anexo 1 es una sola tabla con cuatro columnas:** `Componente | Atributo | Estado |
Motivo`, con el componente repetido en cada fila. No una tabla por componente.

**El `Estado` se escribe con la frase completa:** `A - Implementado satisfactoriamente`,
`B - Implementado con observaciones`. Lo llena el equipo de proyecto.

**La seguridad se declara en cada componente** dentro del Anexo 1, además del Anexo 3.

**Qué completa el laboratorio** (comparando pre y post reunión):

- Los datos de cabecera: `Fecha de Evaluación`, `Laboratorio`, `Equipo de Evaluación`,
  `Alumno`, y una columna `Alumno` propia.
- Reescribe la escala: el alumno se autoevaluó con `Implementado satisfactoriamente` y
  el laboratorio lo pasó a `Muy satisfactorio` / `Satisfactorio` en `Nivel de
  Competencia` y `Nivel de Competencia Global`.
- Llena `Comentarios` (quedan vacíos en la entrega del alumno).
- En el Anexo 3 borra las marcas que el alumno había puesto en `Previsto` y deja las de
  `Implementado`.
- Agrega una tabla de firma (`Fecha | Responsable(s) | Firma(s)`) y un recuadro de
  `Observaciones`.

**Criterio de referencia:** cada ítem declarado es un ítem que el laboratorio puede
pedir ver funcionando. El ejemplo declaró 7 ítems de seguridad y la reunión giró sobre
esos 7.
