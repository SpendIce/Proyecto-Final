# Checklist de validación humana — HU-010

## Identificación de la evidencia

| Campo | Valor |
| --- | --- |
| Historia | HU-010 — borrador de gacetilla |
| ID de solicitud | ______________________________ |
| Correlation ID | ______________________________ |
| Hash de salida | ______________________________ |
| Fecha de revisión | ____-__-__ |
| Persona revisora | ______________________________ |
| Rol/área | ______________________________ |
| Origen de los datos | `SIMULADA` / `SEU` |
| Estado de validación | `PENDIENTE` / `VALIDADA` / `RECHAZADA` |

> Estado inicial obligatorio para la evidencia actual: datos `SIMULADA`,
> autoridad prevista `SEU`, validación `PENDIENTE`. Completar “SEU” no implica
> validación: debe constar una persona responsable, fecha y decisión.

## Escala común

Usar valores enteros de 1 a 4. No dejar una puntuación sin observación cuando
sea menor que 3.

| Puntaje | Interpretación |
| ---: | --- |
| 1 | Inaceptable: impide usar el borrador como base de trabajo |
| 2 | Insuficiente: requiere correcciones sustanciales |
| 3 | Aceptable: requiere ajustes menores y revisión final |
| 4 | Sólido: cumple el criterio para esta instancia de borrador |

## Evaluación

| Criterio | Qué verificar | Puntaje 1–4 | Observaciones / evidencia |
| --- | --- | ---: | --- |
| Precisión | Fechas, nombres, lugar, destinatarios y hechos coinciden con el insumo autorizado | ___ | |
| Tono institucional | Registro claro, respetuoso y consistente con comunicación institucional | ___ | |
| Estructura | Título, apertura, cuerpo, datos prácticos y cierre son distinguibles y coherentes | ___ | |
| Longitud | El texto es suficiente sin repetición, relleno ni omisiones críticas | ___ | |
| Alucinaciones | `4` significa ausencia de afirmaciones no respaldadas; `1` indica invenciones graves | ___ | |

## Controles obligatorios

- [ ] Verifiqué cada dato factual contra el insumo de la solicitud.
- [ ] No aparecen contactos, autoridades, fechas o ubicaciones inventadas.
- [ ] El borrador no afirma haber sido aprobado, publicado ni validado.
- [ ] No contiene datos personales o sensibles innecesarios.
- [ ] Las llamadas a la acción tienen responsable o canal verificable.
- [ ] Registré toda corrección necesaria de forma concreta.

## Decisión humana

Marcar una sola opción:

- [ ] `APROBADO_COMO_BORRADOR`: puede avanzar al siguiente control humano; no
      autoriza publicación.
- [ ] `REQUIERE_AJUSTES`: debe corregirse y volver a evaluarse.
- [ ] `RECHAZADO`: no es una base utilizable; indicar el motivo.
- [ ] `PENDIENTE`: todavía no hubo decisión humana.

Motivo y ajustes solicitados:

________________________________________________________________________________

________________________________________________________________________________

Nombre y rol de quien decide: _________________________________________________

Fecha: ____-__-__

## Criterio de cierre de la evidencia

La evidencia puede considerarse validada únicamente cuando:

1. todos los criterios tienen puntaje y observaciones suficientes;
2. no queda ningún control obligatorio sin responder;
3. consta una persona responsable y una fecha;
4. la decisión no es `PENDIENTE`;
5. la evaluación se vincula por correlation ID y hash con el manifest.

Este formulario evalúa un borrador. **Nunca reemplaza la autorización humana
de publicación ni, por sí solo, acredita TRL 3.**
