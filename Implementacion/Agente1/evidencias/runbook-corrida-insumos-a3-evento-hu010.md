# Runbook — corrida de insumos A3 `evento` → gacetilla HU-010 sobre D2

## Estado de este documento

**Procedimiento preparado, no ejecutado.** Este runbook deja listo el
ensayo offline y la corrida live del flujo implementado en el issue #83.
Ninguna de las corridas descriptas fue ejecutada sobre la planilla D2: la
corrida live es tarea del operador y requiere credenciales, configuración
del entorno y un modelo de Ollama disponible. La evidencia offline generada
por la suite (`tests/test_insumos_corrida.py`) usa el generador
determinista `fake-determinista`, lo cual queda asentado en el propio log
del pipeline.

## Qué demuestra el flujo (#83)

Un insumo de A3 con `payload.type = "evento"` entregado en la pestaña
`Insumos de agentes` de la planilla D2 se traduce a la entrada del pipeline
de gacetilla HU-010 y produce un borrador `BORRADOR — NO PUBLICAR` en
estado `PENDIENTE_VALIDACION`, que exige la misma validación humana de la
SEU que cualquier gacetilla pedida por el canal propio. El enlace (o el
path local, en offline) vuelve a la columna `detalle` de la fila.

Controles del flujo:

- El `payload.content` tiene contrato declarado
  (`contracts/insumos/a3_evento_gacetilla_v1.schema.json`,
  `CANDIDATO_NO_INSTITUCIONAL`): campos admitidos igual a las columnas de
  la planilla de actividades menos `id_actividad`, y obligatorios igual a
  los de `gacetilla_input_v2` menos el mismo identificador.
- Falta de un obligatorio, campo desconocido o valor no texto: la fila
  queda `rechazado` con código propio (`evento_campos_faltantes`,
  `evento_campos_desconocidos`, `evento_valor_invalido`), sin generar nada
  y sin invocar al modelo.
- El borrador lleva una línea visible `[Procedencia: ...]` entre la marca
  y la pieza: productor, tipo, flag de productor provisional,
  `cargado_por` y `correlation_id` del insumo.
- La línea de `logs/ejecuciones.jsonl` suma el bloque `procedencia` con
  los mismos identificadores opacos; nunca copia el contenido del insumo.
- La idempotencia por `correlation_id` y la escritura acotada
  `C{fila}:D{fila}` son las de la corrida del #82, sin cambios.

## Insumo real utilizado

El insumo de ensayo es el evento real «Ingeniería por un día 2026»
(jornada de puertas abiertas, miércoles 14 de octubre de 2026, 16:00 h,
Av. Cabildo 15, CABA, consultas `comunicacion@fie.undef.edu.ar`), tal como
figura en el corpus de comunicaciones reales de la SEU. El envelope está
versionado como fixture en
`tests/fixtures/insumos_agentes/a3_evento_ingenieria_por_un_dia_2026.json`
con `data_origin = provisional_producer` (lo carga el productor
provisional declarado, no un agente real) y provenance con los SHA-256 de
sus fuentes:

- `Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md`:
  `d4bea92098a4f58f560aedebc5aecf197d1bd0573f678e26c952ceee393bf6ed`
- `Adjuntos/imagenes-flat-finch/mensaje-original.md` (post de Instagram
  de la jornada, ejemplo IG 1):
  `0dd317f3af7528f18a3b39e59eebb34fdba17976f517f1d3d50ab953c407f081`

El CSV `insumos-ensayo-a3-evento-ingenieria-por-un-dia.csv`, en esta misma
carpeta, replica la forma de la pestaña con esa fila (`cargado_por =
ope-jgone`, `estado` y `detalle` vacíos).

## Ensayo offline (ejecutable sin red)

Desde `Implementacion/Agente1`:

```bash
PYTHONPATH=src python -m agente1 insumos-agentes \
  --tabla evidencias/insumos-ensayo-a3-evento-ingenieria-por-un-dia.csv \
  --directorio /tmp/salida-insumos-ensayo \
  --fake-output "$(cat <<'EOF'
## TÍTULO
Ingeniería por un día 2026

## DATOS DE LA ACTIVIDAD
Fecha: 2026-10-14
Organiza: Facultad de Ingeniería del Ejército
Lugar: Av. Cabildo 15, CABA

## CONTACTO
comunicacion@fie.undef.edu.ar

## BAJADA
Jornada de puertas abiertas con laboratorios y charlas.

## CUERPO
La actividad invita a conocer la oferta académica y los laboratorios.
EOF
)"
```

Resultado esperado: la fila queda `borrador generado`, el `detalle` del
CSV recibe el path local del borrador bajo
`/tmp/salida-insumos-ensayo/borradores/` y el documento empieza con la
marca `BORRADOR — NO PUBLICAR`, la línea `[Procedencia: insumo de A3,
tipo evento; productor provisional: sí; cargado_por: ope-jgone;
correlation_id: corr-a3-ingenieria-por-un-dia-2026.]` y la pieza.
`/tmp/salida-insumos-ensayo/logs/ejecuciones.jsonl` registra una línea
`PENDIENTE_VALIDACION` con el bloque `procedencia`.

La corrida escribe el estado en el propio CSV, igual que haría sobre la
pestaña: para repetir el ensayo se usa una copia del CSV o se regenera con
`estado` y `detalle` vacíos (una fila con estado escrito se omite como ya
procesada). El CSV versionado se conserva prístino: la corrida de ensayo
se hace siempre sobre una copia en un directorio de trabajo.

## Precondiciones de la corrida live sobre D2

1. DSI debe asignar identidad y autorización Workspace, igual que para el
   runner e2e (`evidencias/runbook-workspace-e2e.md`).
2. La SEU debe confirmar la planilla D2, el nombre de la pestaña
   `Insumos de agentes`, la carpeta de Drive para borradores y la
   plantilla.
3. La fila del insumo real debe estar cargada en la pestaña por el
   productor provisional declarado, con `estado` vacío. El JSON del
   fixture es el contenido textual de la celda `insumo`.
4. Ollama disponible en loopback con el modelo aprobado para la prueba.
5. El access token efímero se entrega sólo por
   `AGENTE1_WORKSPACE_ACCESS_TOKEN`.

Variables requeridas (las mismas del workspace e2e más el rango de la
pestaña):

```text
AGENTE1_WORKSPACE_AMBIENTE=D2
AGENTE1_WORKSPACE_SPREADSHEET_ID=<asignado-por-DSI-SEU>
AGENTE1_WORKSPACE_RANGO_A1=<hoja-y-rango-de-actividades>
AGENTE1_WORKSPACE_FOLDER_ID=<asignado-por-SEU>
AGENTE1_WORKSPACE_TEMPLATE_ID=<asignado-por-SEU>
AGENTE1_WORKSPACE_TIMEOUT_S=10
AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES=1048576
AGENTE1_WORKSPACE_ACCESS_TOKEN=<token-efimero>
AGENTE1_INSUMOS_RANGO_A1='Insumos de agentes'!A1:D<n>
```

## Ejecución live explícita

El subcomando exige simultáneamente `--live` y `--confirm-write-workspace`,
y en vivo sólo admite un modelo de Ollama real:

```bash
PYTHONPATH=src python -m agente1 insumos-agentes \
  --live --confirm-write-workspace \
  --directorio salida/insumos-d2 \
  --ollama-model <modelo-aprobado>
```

Resultado esperado sobre la fila del insumo real: `estado = "borrador
generado"` y `detalle =` enlace al documento creado en la carpeta de Drive
configurada (el pipeline lo renderiza desde la plantilla y lo deja
pendiente de validación). El informe JSON por stdout muestra la fila con
`desenlace = "escrita"`, `producer = "A3"`, `payload_type = "evento"` y
`data_origin = "provisional_producer"`; nunca muestra el contenido del
insumo.

## Verificación posterior esperada

- En el documento generado: marca `BORRADOR — NO PUBLICAR`, línea
  `[Procedencia: insumo de A3, tipo evento; productor provisional: sí;
  cargado_por: <valor-de-la-celda>; correlation_id:
  corr-a3-ingenieria-por-un-dia-2026.]` y la pieza con los hechos del
  evento (fecha en formato largo, organiza, lugar, contacto).
- En `salida/insumos-d2/logs/ejecuciones.jsonl`: una línea
  `PENDIENTE_VALIDACION` con `procedencia.origen = "insumo_agente"` y los
  identificadores opacos, sin contenido del insumo ni del borrador.
- En `salida/insumos-d2/insumos-procesados.jsonl`: reserva `inicio` y
  `final` del `correlation_id`; una segunda corrida sobre la misma fila
  la omite como ya procesada.
- El borrador no se publica ni se envía: queda a la espera de la
  validación humana de la SEU, igual que cualquier gacetilla del canal
  propio.

## Lo que esta evidencia no afirma

- No se ejecutó la corrida live ni se tocó la planilla D2.
- El ensayo offline usa `fake-determinista`: ejercita la traducción del
  insumo, los gates del pipeline y la procedencia, no la calidad de la
  prosa de un modelo real.
- La generación de un borrador no constituye aprobación: el estado final
  sigue siendo `PENDIENTE_VALIDACION` y la publicación es decisión
  humana de la SEU.
