# Paquete ejecutable de validación SEU — Agente 1

## Estado

- **Estado documental:** `PENDIENTE`
- **Personas revisoras comunicadas por SEU:** A/c Juan Manuel Gonzalez
  Chipont; suplente: VS “ec” Tomás de Vergara. La participación efectiva se
  registra recién en el acta.
- **Validación SEU registrada:** no
- **Gate G2 / TRL 3 acreditado:** no
- **Publicación o envío habilitado:** no

Este paquete prepara una sesión humana sobre borradores de HU-010 y HU-011.
No atribuye criterios, puntajes ni decisiones a la Secretaría de Extensión y no
autoriza publicar, compartir o enviar contenido.

## Contenido

| Archivo | Propósito |
|---|---|
| `protocolo-sesion.md` | Secuencia operativa y límites de la sesión |
| `muestra-validacion.csv` | Muestra sintética de tres actividades con gacetilla y ambos canales sociales |
| `checklist-consolidado.md` | Escala 1–4 y controles que se completan por borrador |
| `plantilla-acta-decision.md` | Formulario humano de cierre, inicialmente vacío |
| `acta-validacion.json` | Acta estructurada que consume el validador automático |
| `registro-defectos.csv` | Registro vacío para defectos observados durante la sesión |
| `referencias.json` | Catálogo versionable de artefactos que deben hashearse |
| `manifest-referencias.json` | Manifest reproducible generado sin copiar el contenido |

## Preparar o verificar el manifest

Desde la raíz del repositorio:

```bash
python Implementacion/Agente1/scripts/preparar_validacion_seu.py
```

El comando:

1. valida que un acta no declare una aprobación sin identidad, rol, fecha,
   evidencia, las nueve muestras, puntajes y controles mínimos;
2. calcula `sha256` y tamaño de cada referencia;
3. escribe solamente identificadores opacos, hashes, tamaños y estados; las
   rutas permanecen en el catálogo local y no pasan al manifest;
4. no imprime ni copia borradores, contactos o identidad de la persona
   revisora;
5. no posee ninguna operación de publicación, envío o integración externa.

Para verificar el script:

```bash
cd Implementacion/Agente1
python -m pytest -q tests/test_preparar_validacion_seu.py
```

## Regla de cierre

`APROBADO_COMO_BORRADOR` significa exclusivamente que el texto puede avanzar
al siguiente control humano. **Nunca significa autorizado para publicación.**
La evidencia de esta carpeta tampoco acredita por sí sola el DoD institucional,
el Gate G2 ni TRL 3.

El umbral para aprobar cada borrador es: seis puntajes enteros entre 3 y 4 y
todos los controles obligatorios exactamente en `true`. Para cualquier cierre,
un puntaje 1 o 2 exige observación; `REQUIERE_AJUSTES` y `RECHAZADO` exigen
además motivo global y observación en cada muestra afectada. La fecha de cierre
debe usar ISO 8601 con zona horaria.
