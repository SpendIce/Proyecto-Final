# Recorrido — plantilla SEU del certificado de aprobación (#126)

## Qué demuestra

- Que la emisión de `aprobacion` compone el diseño recibido de la SEU —
  A4 horizontal, doble borde, símbolo FIE centrado arriba, denominación de
  facultad y universidad, título de la actividad, texto de aprobación con
  el destinatario en negrita, lugar/fecha y los dos bloques visibles de
  firma (Secretario de Extensión Universitaria y Decano)— como composición
  reproducible de `certificados_plantilla_seu.py`
  (`certificado_seu_aprobacion_v1`), no como transformación del DOCX.
- Que el tercer firmante heredado del XML del DOCX —un textbox anclado
  fuera de página que el render de la SEU no muestra— no se compone: la
  plantilla declara únicamente los dos bloques visibles.
- Que nombre, apellido, DNI, actividad, horas y fecha salen de los datos
  validados de la actividad y de la lista, nunca del ejemplo recibido:
  el caso `EJEMPLO-NOTEBOOKLM-N2` compone su título propio y
  `VEINTICUATRO` horas, sin heredar las `DOCE` de Gestión Documental.
- Que el símbolo y las firmas se leen de la carpeta restringida
  (`--recursos` en offline, `AGENTE1_CERTIFICADOS_RECURSOS_DIR` en live):
  ningún PDF parece firmado sin estarlo, porque un recurso faltante deja
  su espacio marcado «insumo restringido no provisto».
- Que el PDF es determinista byte a byte para los mismos datos y
  recursos, así que `pdf_hash` en la auditoría es estable.
- Que el circuito no cambia: mismo parseo estricto de la lista, mismas
  dos aprobaciones de la línea descriptiva (#74), mismo `apruebo_lote`
  atado al hash de la lista (#72), mismo correo de muestra con
  `BORRADOR — NO EMITIR` y misma marca `DOCUMENTO DE PRUEBA — SIN VALIDEZ`
  en el emitido.
- Que cada evento `entrega` del log deja la `plantilla` usada junto a
  `pdf_hash`: la traza de cuál composición salió queda en la auditoría.
- Que `asistencia` sigue saliendo con `certificado_base_provisional_v1`:
  la SEU no entregó ni avaló la variante de asistencia y queda
  explícitamente pendiente (ADR 0017).

## Qué NO demuestra

- La revisión visual de la SEU: el layout reproduce la composición
  observada y quedó ajustado por inspección local, pero la fidelidad
  tipográfica fina y el espaciado irregular del render original son
  criterio de la SEU, no algo que este documento pueda dirimir.
- La firma digital ni la emisión institucional real: toda la corrida es
  offline con lista y recursos sintéticos, y la marca de prueba es
  permanente mientras rija la lista de prueba.
- La variante de asistencia, la integración con el manual visual 2026 y
  el aval SEU de cualquier ajuste residual de espaciado.

## Custodia del original

El DOCX recibido se conserva sin cambios en `.local-recovery/` del
checkout principal, modo 700, con SHA-256
`773bf517fd101cf2c1fae7e12be90f7d14e60525e3c74eb02b3fa48b5b668cd4`
registrado en la ficha de la visita (`Documentos/Reuniones/SEU-2026-10-19/`).
Contiene las imágenes de las dos firmas: no se versiona, no se copia al
worktree y ninguna de sus imágenes se extrajo a archivos del repo. Los
recursos de la demo son PNG sintéticos versionados en
`tests/fixtures/recursos-firma/`, dibujados por código; los nombres de
archivo (`simbolo-fie`, `firma-secretario`, `firma-decano`) son el
contrato que la custodia rellena en D2 con los insumos reales.

## Corrida offline con la plantilla

Se corrió `scripts/emitir_certificados.py` sobre
`data/actividades_notebooklm_n2_sinteticas.csv` (`EJEMPLO-NOTEBOOKLM-N2`,
24 horas declaradas en la planilla sintética), con una lista de dos
personas sintéticas —una `asistencia`, una `aprobacion`— y
`--recursos tests/fixtures/recursos-firma`. El circuito exigió las dos
aprobaciones de la línea y el `apruebo_lote` del rol utilitario sobre el
objeto `c4a9e194…72df` (definición del 11/11 de quién aprueba el lote la
implementa #125; este ticket no toca `revisar_aprobacion_lote`):

```bash
uv run --no-sync env PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad EJEMPLO-NOTEBOOKLM-N2 \
  --csv data/actividades_notebooklm_n2_sinteticas.csv \
  --lista-csv /tmp/demo-seu/lista.csv \
  --linea /tmp/demo-seu/linea.txt \
  --aprobador coord@example.invalid \
  --solicitante aux@example.invalid \
  --recursos tests/fixtures/recursos-firma \
  --directorio /tmp/demo-seu/run
```

```text
{"correlation_id": "ffba89881898b7c7", "emitidas": 2, "entregas_fallidas": 0,
 "estado": "EMITIDA", "modo": "offline_fake",
 "resumen": "2 certificados entregados de 2 (INTELIGENCIA ARTIFICIAL APLICADA
 A LA EDUCACIÓN Y GESTIÓN: NOTEBOOKLM - NIVEL 2)"}
```

Las dos entregas quedaron auditadas con su plantilla y el sha256 del
adjunto (nombres, correos, DNI y PDFs no se persisten):

```text
{"evento": "entrega", "plantilla": "certificado_base_provisional_v1",
 "pdf_hash": "9f98fe0fbd683b20bcc4503a7adb7a04c5844bc5bc174bd03752043d954bfaa0", …}
{"evento": "entrega", "plantilla": "certificado_seu_aprobacion_v1",
 "pdf_hash": "2da1021cf256fb96b6eb16975f3afbad5885a4238a0ac0c706f97b798d11ca88", …}
```

La muestra del correo de aprobación salió con `BORRADOR — NO EMITIR`
(adjunto `certificado-muestra.pdf`, 1667 bytes, sólo su hash en el
registro) y el certificado de aprobación emitido —7453 bytes con los tres
recursos sintéticos embebidos— fue revisado visualmente: composición A4
horizontal con doble borde, símbolo centrado, encabezado institucional,
título en dos líneas sin desborde, destinatario en negrita dentro de la
frase de aprobación, línea descriptiva en oblicua, lugar/fecha a la
derecha y los dos bloques de firma con su imagen.

## Pendientes

- Variante de **asistencia**: plantilla SEU entregada o adaptación
  avalada de la de aprobación (verbo y texto); hoy sigue la provisional.
- Firma digital y emisión institucional real (`PENDIENTE_SEU`).
- Revisión SEU de la fidelidad visual del render, incluido el espaciado
  del encabezado observado como irregular en el render del original.
- Compatibilidad con el manual visual 2026 (Encode Sans/Roboto), sin
  rediseño automático por esa diferencia.
