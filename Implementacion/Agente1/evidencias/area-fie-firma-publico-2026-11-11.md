# Área FIE, firma de área opcional y públicos destinatarios — evidencia de implementación

- **Ticket:** #154 (definición de la SEU con el autor del PPS, 11/11/2026).
- **Fecha:** 2026-11-11.
- **Rama:** `feat/154-area-fie-firma-publico`, seis commits (`197b9ef` a
  `af703dd`), sin push en el momento de esta evidencia.
- **Decisión registrada:** ADR 0015
  (`docs/adr/0015-area-emisora-y-firma-opcional-publico-como-catalogo-de-grupos.md`).

## Qué cambió

1. **Área FIE.** `areas_emisoras_v2.json` agrega el área `fie` con la firma
   exacta «Facultad de Ingeniería del Ejército» para las comunicaciones
   generales que no son de un área en particular. La `v1` queda versionada
   para trazabilidad; el código (`canal_form.py`) lee la `v2`.
2. **Firma de área opcional.** El pedido elige el área y, por separado, si la
   pieza lleva firma de área. Las formas `v2` de `aviso_de_otra_area`,
   `convocatoria_interna` y `newsletter` ganan `pie_condicion`: con la firma
   desactivada el pie omite el área y el bloque `firmante` institucional va
   siempre. Las entradas `v2` declaran `firma_de_area` como opción `sí`/`no`
   con default «sí», que conserva el comportamiento anterior. El gate deja
   de exigir el área impresa sólo cuando la firma está apagada; el área se
   confirma en el pedido igual.
3. **Públicos destinatarios.** `publicos_destinatarios_v1.json` es el
   catálogo cerrado nuevo: cada público es un grupo de correo de Workspace,
   sólo `id` y `nombre` —las direcciones de los grupos no se versionan en un
   repo público—, y arranca con `alumnos_ingenieria` («Alumnos de
   ingeniería»), el único confirmado. `canal_form_respuestas_v3.json` suma
   las columnas `firma_de_area` y `publicos`; el canal las valida fail-closed
   (firma fuera de las opciones, público vacío, fuera del catálogo o
   repetido, público en un tipo que no lo lleva). El público queda declarado
   en la estructura del pedido, en el registro de atendidos y en el aviso de
   revisión (`Públicos: <nombre del catálogo>`), y una barrera explícita
   (`CAMPOS_DEL_PEDIDO_NO_DE_LA_PIEZA`, aplicada en `construir_prompt` y en
   `_construir_prompt`) lo excluye de cualquier prompt.

## Contratos con versión nueva

| Contrato | Versión | Qué lleva |
|---|---|---|
| `areas_emisoras` | `v2` | área `fie`; la `v1` queda como histórico |
| `tipos_gacetilla` | `v2` | versión de forma y entrada por tipo, `requiere_publicos` |
| `formas/aviso_de_otra_area`, `convocatoria_interna`, `newsletter` | `v2` | `pie_condicion` sobre `firma_de_area` |
| `entradas/aviso_de_otra_area`, `convocatoria_interna`, `newsletter` | `v2` | `firma_de_area` opcional, default «sí» |
| `publicos_destinatarios` | `v1` (nuevo) | `alumnos_ingenieria`, sólo id y nombre |
| `canal_form_respuestas` | `v3` | columnas `firma_de_area` y `publicos` |
| Renderer | `gacetilla_forma_declarada_v5` | condición del pie |

Las lecturas de `canal_form_respuestas_v1`/`v2` quedan iguales: sus filas no
traen las columnas nuevas y la validación no aplica (hay regresión
versionada de ambas).

## Resultado de la suite

- `uv run --no-sync pytest -q`: **2476 tests pasados, 11 salteados**
  (los salteados son los que requieren `Documentos/` o condiciones live que
  la suite marca como skip, igual que antes del cambio).
- `uv run --no-sync ruff check .`: sin hallazgos.
- `manifest-version.json` regenerado (paso 3 del procedimiento), versión del
  proyecto sin cambio: `0.5.10`. No se cortó versión ni se crearon tags.

Cobertura nueva: contrato v3 y catálogo (columnas, sólo `id`/`nombre`, sin
correos), `fie` en el padrón y su firma exacta, firma de área por default y
por opción en las tres formas, firma fuera de la lista, firma ignorada en
tipos sin área, bloque institucional siempre presente, público requerido /
fuera del catálogo / repetido, despacho con un público declarado en el
registro y visible en el aviso, **el prompt del modelo sin el público** (ni
el id ni el nombre, sobre el prompt real del pipeline), **el borrador
idéntico con y sin la columna de públicos** (v3 vs v2), y regresión de la
lectura v1/v2 de la hoja.

## Decisiones tomadas por mi cuenta

- **Numeración del ADR.** El primer número que elegí (0014) ya estaba
  tomado por la ADR de la web de A1 en las ramas `planning/`; lo renumeré a
  0015.
- **La difusión conserva su forma `v1`.** Su pie es una firma institucional
  fija, no un área del pedido, así que `pie_condicion` no le aplica; sólo
  los tres tipos que imprimen `{area_emisora}` subieron a `v2`.
- **`publicos_no_aplica` queda como guarda.** Hoy los siete tipos declaran
  `requiere_publicos`, así que el bloqueo por «público en un tipo que no lo
  lleva» no puede dispararse con el contrato vigente; queda para el tipo
  futuro que no viaje por FIE Informa.
- **La frase de público de las piezas no se toca.** Los campos `publico` /
  `destinatarios` que algunas entradas usan para redactar («a la comunidad
  educativa») son prosa de la pieza, no destinatarios de envío: el público
  de envío es el campo cerrado nuevo, y ambos conviven porque deciden cosas
  distintas (ADR 0015).
- **El id del pedido firma las columnas nuevas sólo en v3.** Una fila v2
  produce el mismo `id_pedido` que antes: la deduplicación entre formas de
  hoja no se mezcla.
