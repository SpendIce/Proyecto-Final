# Protocolo de sesión de validación humana — SEU

## 1. Objetivo y alcance

Evaluar si los borradores técnicos de HU-010 y HU-011 pueden servir como base
de trabajo institucional. La sesión usa datos `SIMULADA` y artefactos
versionados. No valida un flujo de publicación ni reemplaza la autorización
humana posterior.

## 2. Prerrequisitos

- La SEU comunicó quiénes están formalmente designados para revisar.
- Cada persona revisora conoce que la decisión se limita al borrador.
- El manifest fue regenerado y sus referencias existen.
- Los borradores conservan `BORRADOR — NO PUBLICAR`.
- La muestra no contiene datos personales reales ni credenciales.

Si falta cualquiera de estos puntos, la sesión permanece `PENDIENTE`.

## 3. Muestra

Se seleccionan tres actividades sintéticas existentes: `SYN-001`, `SYN-003`
y `SYN-005`. Por cada una se revisan:

1. una gacetilla HU-010;
2. un post HU-011 para Instagram;
3. un post HU-011 para LinkedIn.

Son nueve borradores. No se agregan casos institucionales ni identidades que no
estén autorizados.

## 4. Secuencia de la sesión

1. La persona coordinadora verifica los hashes del manifest.
2. La persona revisora contrasta cada borrador con el insumo sintético.
3. Completa todos los criterios 1–4 y los controles obligatorios.
4. Registra observaciones concretas para puntajes menores que 3.
5. Elige por muestra: `APROBADO_COMO_BORRADOR`, `REQUIERE_AJUSTES` o
   `RECHAZADO`.
6. Registra defectos reproducibles en `registro-defectos.csv`.
7. Completa nombre o identificación verificable, rol/área, fecha, referencia de
   evidencia y decisión global. La fecha usa ISO 8601 con zona horaria, por
   ejemplo `2026-08-20T14:00:00-03:00`.
8. Actualiza `acta-validacion.json` y regenera el manifest.

## 5. Regla de decisión

- `APROBADO_COMO_BORRADOR`: los seis criterios tienen puntaje entero entre 3 y
  4, todos los controles son exactamente `true` y las nueve muestras tienen
  esa decisión. Sólo permite avanzar a otro control.
- `REQUIERE_AJUSTES`: existe al menos una corrección necesaria y debe repetirse
  la evaluación afectada.
- `RECHAZADO`: el material no constituye una base utilizable; debe registrarse
  el motivo.
- `PENDIENTE`: valor inicial o sesión incompleta.

El script bloquea una aprobación incompleta, pero no decide por la persona.
Todo puntaje 1 o 2 requiere una observación. Una muestra marcada
`REQUIERE_AJUSTES` o `RECHAZADO` y su decisión global requieren un motivo no
vacío.

## 6. Registro seguro

- No copiar el contenido del borrador ni contactos al registro técnico.
- Referenciar mediante ID, ruta, correlation ID y hash.
- No incluir tokens, IDs de recursos Workspace ni credenciales.
- El resumen de ejecución sólo informa estado, cantidad de referencias y ruta
  del manifest.

## 7. Cierre y escalamiento

El acta sólo puede cerrarse con identidad verificable, rol, fecha, evidencia y
decisión. Una aprobación del borrador no habilita publicación/envío y no permite
declarar Gate G2 o TRL 3 sin el criterio institucional correspondiente.
