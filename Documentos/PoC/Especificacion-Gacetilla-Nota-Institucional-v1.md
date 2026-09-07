# Especificación candidata — nota institucional de gacetilla v1

- **Proceso BPM:** P4 — Comunicación y Difusión Institucional
- **HU:** HU-010
- **Estado:** `CANDIDATA_PARA_CO_DISENO_SEU`
- **Base:** definición operativa SEU registrada el 2026-08-26.
- **Alcance de publicación:** documento técnico candidato; no es plantilla oficial ni autorización de publicación.

## Propósito

Definir un contenedor de borrador para comunicaciones que, si corresponde elevar a DGE/SGE, se materializa como una nota institucional con logos en la parte superior, texto e imágenes pertinentes. No existe una plantilla oficial confirmada; esta especificación no crea ni suplanta una.

## Entrada mínima y controles

| Dato | Control | Evidencia |
|---|---|---|
| Actividad y, cuando corresponda, aprobación humana | Referencia recuperable; A1 no infiere aprobación por la mera existencia de la actividad | ID o URI controlada, no secretos |
| Información final de difusión | PDF final o referencia a éste | Hash/referencia del material aprobado |
| Texto base | Fuente identificada y sin hechos inventados | `hash_input`, responsable y versión |
| Logos e imágenes | Activos institucionales autorizados y derechos de uso confirmados | Referencia al repositorio/carpeta autorizada |

Si falta una fuente crítica, el resultado es `INCOMPLETA` o `PENDIENTE_VALIDACION`; nunca una pieza publicable.

## Estructura candidata

1. Franja superior: logos institucionales autorizados.
2. Cuerpo: texto de la gacetilla sustentado en el material aprobado.
3. Recursos visuales: imágenes correspondientes, referenciadas sin duplicar datos ni derechos no verificados.
4. Pie de trazabilidad interno: ID de solicitud, versión, hash y estado `BORRADOR — NO PUBLICAR` (no forma parte de la pieza externa).

La tipografía, tamaños, disposición precisa, cantidad de imágenes, metadatos y formato de elevación se mantienen `PENDIENTE_DE_CO_DISENO` hasta recibir activos/reglas y revisar ejemplos aprobados.

## Flujo HITL

`BORRADOR` → revisión editorial del referente designado → corrección/diseño por Departamento de Comunicación → aprobación/corrección institucional por el Oficial de Comunicación Institucional → escalamiento al Decano sólo si corresponde.

La transición a publicación o elevación oficial queda fuera del alcance automático de A1 y exige decisión humana trazable.

## DoD candidato

- Insumo y aprobación de actividad trazables cuando correspondan.
- Logos e imágenes provenientes de activos autorizados.
- Borrador sin invención de hechos y con estado no publicable.
- Revisión editorial registrada.
- Aprobación/corrección institucional registrada si la pieza se tratará como oficial.
- Evidencia recuperable: input, output, versión, hashes, decisión y responsable.
