# Recorrido — plantilla SEU del certificado de aprobación (#126)

## Qué demuestra

- Que la emisión de `aprobacion` compone el diseño recibido de la SEU —
  A4 horizontal, doble borde, símbolo FIE centrado arriba, encabezado
  institucional en una línea, título de la actividad, cuerpo de aprobación
  en oblicua con el destinatario en negrita oblicua, lugar/fecha y los dos
  bloques visibles de firma (Secretario de Extensión Universitaria y
  Decano)— como composición reproducible de
  `certificados_plantilla_seu.py` (`certificado_seu_aprobacion_v2`), no
  como transformación del DOCX.
- Que la composición se ajustó al PDF institucional del 17/11/2026: caja de
  firma de 90×65 pt apoyada en y=62, encabezado en una línea (facultad 17
  pt, universidad 13 pt), título achicado de 17 a 13 pt para entrar en una
  línea, cuerpo completo en Helvetica-Oblique de 15 pt con el destinatario
  en Helvetica-BoldOblique, sustantivo del cuerpo según la primera palabra
  del título y DNI con separador de miles.
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
- Que la firma se solapa sobre el texto del firmante (pedido SEU del
  17/11/2026): la imagen va en una caja de 90×65 pt con borde inferior en
  62 pt, alineada al fondo y centrada en el firmante; queda casi entera
  sobre el nombre, sólo sus trazos inferiores lo cruzan y el texto se
  emite después para quedar legible encima. El espacio reservado de un
  recurso ausente no pisa nombre ni cargo.
- Que el PDF es determinista byte a byte para los mismos datos y
  recursos, así que `pdf_hash` en la auditoría es estable.
- Que el circuito no cambia: mismo parseo estricto de la lista, misma
  aprobación única de contenido de la línea descriptiva (#74, #125), mismo
  `apruebo_lote`
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
`--recursos tests/fixtures/recursos-firma`. El circuito exigió la
aprobación única de contenido de la línea y el `apruebo_lote` del rol de
contenido por el correo de quien generó el lote sobre el objeto
`c4a9e194…72df` (#125):

```bash
uv run --no-sync env PYTHONPATH=src python scripts/emitir_certificados.py \
  --actividad EJEMPLO-NOTEBOOKLM-N2 \
  --csv data/actividades_notebooklm_n2_sinteticas.csv \
  --lista-csv /tmp/demo-seu/lista.csv \
  --linea /tmp/demo-seu/linea.txt \
  --solicitante aprobador@example.invalid \
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

## Muestra del ajuste al PDF de la SEU (v2)

La composición `certificado_seu_aprobacion_v2` se generó fuera del repo con
los recursos sintéticos de `tests/fixtures/recursos-firma/` para la
revisión visual. Datos de la muestra: nombre «Ana María», apellido
«Prueba», DNI «30222333», el título del taller del PDF de la SEU y 14 horas
reloj.

- `/dev/shm/firma-muestra-v2.pdf` — A4 horizontal, 7513 bytes, sha256
  `f66323123900bceece139875d11aeaa719e07783e248999c7ddcbaea9ca43449`.
- `/dev/shm/firma-muestra-v2.png` — la misma página rasterizada a 80 dpi
  con `pdftoppm -r 80 -png`, 936×662 px.

Se reproduce con `generar_pdf_certificado_seu` y
`RecursosFirmaDirectorio("tests/fixtures/recursos-firma")`. La geometría y
la tipografía las cubren
`test_firma_se_solapa_sobre_el_nombre_y_se_dibuja_antes`,
`test_encabezado_institucional_en_una_sola_linea`,
`test_titulo_largo_en_una_linea_achicado_hasta_quince`,
`test_titulo_que_no_entra_a_trece_se_envuelve` y
`test_cuerpo_en_oblicua_y_destinatario_en_negrita_oblicua`, entre otros.

La corrida auditada de arriba queda como evidencia de v1; con v2 el evento
`entrega` asienta `certificado_seu_aprobacion_v2` y el `pdf_hash` del
adjunto cambia con la composición.

## Pendientes

- Variante de **asistencia**: plantilla SEU entregada o adaptación
  avalada de la de aprobación (verbo y texto); hoy sigue la provisional.
- Firma digital y emisión institucional real (`PENDIENTE_SEU`).
- Revisión SEU de la fidelidad visual del render: encabezado en una
  línea, título achicado, cuerpo oblicuo y solapado de la firma sobre el
  nombre.
- Compatibilidad con el manual visual 2026 (Encode Sans/Roboto), sin
  rediseño automático por esa diferencia.
