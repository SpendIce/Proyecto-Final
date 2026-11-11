---
status: accepted
---

# El certificado de aprobación es una composición reproducible del diseño SEU; el símbolo y las firmas quedan en custodia fuera de Git

La SEU entregó el 19/10/2026 un DOCX editable con la plantilla del certificado de **aprobación** ([issue #126](https://github.com/SpendIce/Proyecto-Final/issues/126)). El archivo contiene las imágenes de las dos firmas y vive bajo custodia fuera del repositorio (`.local-recovery/`, modo 700, SHA-256 registrado en la ficha de la visita): se conserva sin cambios, no se versiona ni se publica.

Decidimos integrarlo como una **composición de PDF reproducible en código** (`certificados_plantilla_seu.py`), no como una transformación del DOCX:

1. **La plantilla se describe como código, no como archivo binario.** El renderer compone la página A4 horizontal observada —borde doble, símbolo FIE centrado arriba, denominación de facultad y universidad, título de la actividad, texto de aprobación, lugar/fecha y dos bloques visibles de firma— y parametriza nombre, apellido, DNI, actividad, horas y fecha. Los datos del ejemplo recibido (Gestión Documental, 12 horas, octubre de 2026) no quedan en el código: cada certificado sale de los datos validados de su actividad.
2. **El símbolo y las firmas son insumos del entorno, nunca del repo.** El renderer pide recursos por nombre (`simbolo-fie`, `firma-secretario`, `firma-decano`) a un puerto de custodia (`RecursosFirma`); el runner los resuelve de una carpeta restringida configurada por `AGENTE1_CERTIFICADOS_RECURSOS_DIR` en live o `--recursos` en offline. Los tests versionan imágenes sintéticas generadas por código en `tests/fixtures/recursos-firma/`, y un recurso faltante deja su espacio marcado «insumo restringido no provisto»: ningún PDF puede parecer firmado sin estarlo.
3. **Sólo se componen los dos firmantes visibles.** El XML del DOCX arrastra un textbox heredado con un tercer nombre y cargo (Director de la FIE) que el render no muestra: la plantilla declara únicamente al Secretario de Extensión Universitaria y al Decano, tal como la SEU los presenta.
4. **La composición es determinista y sin dependencias.** El PDF se arma con la biblioteca estándar (mismo bytes para los mismos datos y recursos) para que el hash del adjunto auditable sea estable, y el render acepta PNG y JPEG del directorio restringido con validación fail-closed.

## Considered Options

- **Convertir el DOCX a PDF en cada emisión** (LibreOffice, `docx`+fill). Se descartó porque exigiría versionar el binario con las firmas, o descomponerlo y recomponerlo a mano, y porque el render de LibreOffice del archivo mostraba espaciado irregular en el encabezado que habría que corregir igualmente. La composición en código reproduce el diseño aprobado sin depender del binario ni de una suite instalada.
- **Extraer las firmas a imágenes versionadas.** Se descartó de plano: el repo es público y las imágenes de firma quedan en el original restringido por acuerdo de custodia (JOS-P2 avala su uso en pruebas, no su publicación).
- **Renderizar sin marca cuando hay recursos reales.** Se descartó: la marca `DOCUMENTO DE PRUEBA — SIN VALIDEZ` es permanente mientras rija la lista de prueba, aun con las firmas reales montadas.
- **Completar el tercer bloque heredado del XML.** Se descartó porque no aparece en el render que la SEU valida: copiar texto invisible del XML habría fabricado un firmante que la plantilla recibida no muestra.
- **Unificar asistencia en la misma plantilla cambiando el verbo.** Se descartó: la SEU no entregó ni avaló la variante de asistencia, así que `asistencia` sigue con la composición provisional declarada hasta la entrega o aval SEU.

## Consequences

- `aprobacion` compone `certificado_seu_aprobacion_v1` y `asistencia` sigue con `certificado_base_provisional_v1`; el evento de cada entrega deja la plantilla usada.
- El circuito no cambia: mismo parseo de lista, mismas dos aprobaciones de la línea descriptiva, mismo `apruebo_lote` atado al hash de la lista, misma entrega cercada por la lista de prueba. La aprobación del lote la define #125 (la aprueba quien la genera, definición del 11/11); esta plantilla no toca `revisar_aprobacion_lote`.
- La auditoría y el registro de entregas siguen guardando sólo hashes: las rutas y los bytes de los recursos restringidos nunca entran al registro ni al correo.
- Una corrida sin `…_RECURSOS_DIR` sale igual, con los espacios de símbolo y firma marcados: la custodia puede montar los recursos reales en D2 sin tocar el código.
- La variante de asistencia queda explícitamente pendiente, junto con la firma digital y la emisión institucional real.
