# Forma declarada y modo de producción por tipo (#121)

- **Estado:** implementado y verificado offline; la forma y los tipos siguen sin
  aprobación institucional de la SEU
- **Alcance:** el tipo como enum cerrado, la forma declarada por tipo, el modo
  de producción, el contrato de entrada por tipo, el gate con núcleo común más
  reglas propias y el refactor del renderer para los siete tipos del corpus
- **Relacionados:** decisión #120 y su adendo del 17/10, ADR 0012, ADR 0001,
  ADR 0010, `CONTEXT.md` (Gacetilla, Tipo de gacetilla, Modo de producción,
  Forma declarada), issue #122 (canal) e issue #123 (anexos)

## 1. Qué se construyó

La gacetilla **declara su tipo**, y el tipo declara su **modo** y su **forma**.
El conjunto de tipos es cerrado y vive en
`src/agente1/contracts/tipos_gacetilla_v1.json`. El tipo selecciona la forma
declarada, el contrato de entrada, las reglas de gate propias y el modo de
producción; no se infiere ni se aproxima a la clase más parecida.

### El tipo en el lenguaje del contrato

- `generar_newsletter` y `generar_mail` salieron del catálogo de intenciones
  (`intenciones_v4`). Un newsletter es un **tipo** de gacetilla y un mail es el
  **canal**. `generar_gacetilla` declara `tipo_gacetilla` como parámetro de
  enum cerrado.
- El fallback de interpretación pasó a `interpretacion_fallback_v4`, con el
  mismo enum que el catálogo, y su prompt a `interpretacion_fallback_v4.txt`.
- La versión del agente sube por cambio **Mayor**: de `0.1.0` a `0.2.0`.

### La forma declarada, un archivo por tipo

Cada tipo tiene su archivo en `src/agente1/contracts/formas/` con su
`schema_version` y las partes institucionales fijas: encabezado, pie,
firmante, fórmulas y etiquetas, además del plan de armado de la pieza.

| Tipo | Modo | Prompt |
|---|---|---|
| Difusión de actividad | Genera | `gacetilla_v8` |
| Saludo o efeméride | Genera | `saludo_o_efemeride_v1` |
| Crónica de evento | Extrae y confirma | No tiene |
| Aviso de otra área | Extrae y confirma | No tiene |
| Convocatoria interna | Extrae y confirma | No tiene |
| Fallecimiento | Extrae y confirma | No tiene |
| Newsletter | Extrae y confirma | No tiene |

La **frase fija de invitación** salió del renderer. Antes,
`_renderizar_mail` agregaba siempre «La Facultad de Ingeniería del Ejército
invita a {público} a participar de la siguiente actividad». No está en el
corpus y hacía que un aviso pareciera una invitación y que una crónica de un
hecho pasado pareciera una invitación a futuro. Ahora la introducción la
aporta la prosa del modelo en los tipos que generan, y en los que extraen y
confirman no hay introducción que generar.

### El contrato de entrada por tipo

Cada tipo tiene `src/agente1/contracts/entradas/<tipo>_v1.json` con sus
`required` y sus `no_aplican`. `gacetilla_input_v2` queda como el contrato de
la planilla de actividades y sólo lo reusa difusión: `modalidad`,
`duracion_horas` y `enlace_inscripcion` no existen para las otras clases.

### El gate

`gacetillas.validar_pieza` tiene un núcleo común para los siete tipos:
- largo máximo de la pieza;
- sin marcadores de plantilla sin resolver;
- sin vocabulario de proceso interno;
- cada hecho que la forma imprime tiene que estar en la pieza.

Y reglas propias del tipo:
- `aviso_de_otra_area`: no puede afirmar una invitación
  (`aviso_afirma_invitacion`);
- `fallecimiento`: no puede quedar sin el nombre confirmado
  (`fallecimiento_sin_nombre_confirmado`);
- `convocatoria_interna` y `newsletter`: no pueden inventar el área emisora
  (`emisor_area_no_confirmada`).

En los tipos que extraen y confirman, el gate compara la pieza contra **lo
confirmado** y `interpretacion_fallback` no interviene: no hay prosa que
extraer. La garantía es doble: `generar_pieza` levanta `TipoNoGeneraError` para
esos tipos y su contrato de entrada declara `x-interpretacion_fallback: false`.

### El renderer

Hay **un** renderer (`gacetillas.renderizar`), no uno por tipo.
`_renderizar_mail` de `procesamiento.py` delega en él y ya no contiene ninguna
frase institucional literal. Difusión de actividad es la primera forma
declarada y las otras seis usan la misma maquinaria.

### Conformidad de forma

Cada uno de los siete tipos renderiza su pieza desde un caso con la forma del
corpus y la compara byte a byte contra `golden/formas/<tipo>.md`. El golden
`SYN-001.md` se regeneró sin la línea fija de invitación y la matriz
`matriz_hu010.py` hashea también la forma y el contrato de entrada de difusión.

## 2. Verificación ejecutada

Desde `Implementacion/Agente1`:

```
$ uv run pytest -q
2245 passed, 8 skipped in 55.10s

$ uv run ruff check .
All checks passed!

$ uv run python scripts/manifest_version.py --salida manifest-version.json
manifest de versión 0.2.0: 181 archivos controlados
```

El manifest se regeneró al cortar la versión, como pide
`PROCEDIMIENTO-CORTE-DE-VERSION.md`. Incluye las siete formas, los siete
contratos de entrada, `tipos_gacetilla_v1.json` y los prompts nuevos.

## 3. Límites

- **La forma no está aprobada por la SEU.** Todos los archivos están marcados
  `PROVISIONAL_NO_INSTITUCIONAL`.
- **Convocatoria interna no tiene esqueleto propio en el anexo del corpus.** Su
  forma se deriva del bloque «Aviso de otra área», adaptado a la clase
  convocatoria, y así queda declarado en el campo `x-fuente` del archivo.
- **La crónica no genera desde Historia Viva en este ciclo.** Su modo es extrae
  y confirma, con «genera desde Historia Viva» como destino declarado (adendo
  del 17/10 en #120).
- **El manifiesto del set de evaluación (#111) no se tocó.** Es una evidencia
  congelada por hash y su `slots_por_tipo` todavía dice que los tipos distintos
  de difusión no tienen pipeline. Regenerar los anexos es #123.
- **El campo de tipo en el canal del Form es #122.** Acá el tipo viaja
  declarado en la solicitud y en el contrato; el canal todavía no lo pregunta.
