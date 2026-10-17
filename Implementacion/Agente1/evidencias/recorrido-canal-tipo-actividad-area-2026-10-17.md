# Recorrido — el canal del Form declara tipo, actividad condicional y área emisora (#122)

## Qué demuestra

- Que la hoja de respuestas del Form de pedidos tiene una **forma declarada
  y versionada** (`canal_form_respuestas_v2`): seis columnas en este orden,
  marca temporal, correo, tipo de gacetilla, actividad, área emisora y
  pedido. El tipo es la primera pregunta, con lista cerrada de los siete
  identificadores de `tipos_gacetilla_v1`.
- Que la **actividad es condicional**: sólo la llevan los tipos que su
  contrato de entrada declara (hoy `difusion_de_actividad`). La opción
  «No es una actividad / no figura» lleva a `actividad_no_figura`; un id de
  actividad bien formado pero no cargado entra al núcleo igual que por prosa
  y el núcleo responde un desenlace acotado sin generación; un texto sin
  forma de id lleva a `actividad_no_identificada`. El pedido estructurado
  despacha con el mismo vocabulario determinístico de la repregunta:
  `gacetilla actividad <id>`.
- Que el **área emisora entra por padrón cerrado**
  (`areas_emisoras_v1`, doctrina ADR 0005): un valor fuera de la lista lleva
  a `area_fuera_de_padron`, y obligatoria o no obligatoria según el contrato
  de entrada del tipo. La firma institucional de la pieza sale del padrón,
  nunca del texto de la hoja.
- Que la forma de hoja se declara con la misma variable del entorno en los
  dos modos (`AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO`, por defecto
  `canal_form_respuestas_v1`): un valor desconocido falla cerrado con
  `canal_form_config_invalid`, en el runner offline con código propio y en
  live por la validación de `cargar_configuracion_canal_form`.
- Que el registro de atendidos viaja con lo que el canal dijo y nada más:
  `declarado` sólo guarda vocabulario cerrado (tipo del catálogo, id de la
  planilla), porque el texto libre de la hoja sería prosa en claro (ADR
  0001); suma `contrato_hoja` y `origen_hechos` (`fuente_institucional` para
  el despacho, `solicitud` para los bloqueos).
- Que el circuito de prosa libre #115 queda intacto sin la variable
  declarada: con el contrato v1 por defecto, la misma hoja se lee por las
  tres columnas de siempre y los pedidos caen al extractor del núcleo, igual
  que antes de #122.

## Qué NO demuestra

El recorrido offline no acredita la verificación de identidad de Google: el
correo se lee del CSV igual que vendría de la hoja, y el atributo «verificado
por Google» sólo existe cuando el Form real lo recolecta (ADR 0005). La
autorización por rol sí se ensaya: el padrón es un archivo externo en ambos
modos.

Tampoco acredita, y queda **declarado como destino** para iteraciones
siguientes:

- **El despacho de los seis tipos que no es difusión.** Hoy otro tipo
  declarado lleva a `tipo_sin_despacho`: bloqueo acotado, aviso con los datos
  que ese tipo exige los carga quien pide, y registro. El circuito de pedidos
  sigue abierto por Form para lo que el núcleo reconoce.
- **La ingesta de la firma a nivel pieza.** El placeholder `{area_emisora}`
  del pie de las formas (#121) y el wirado `firma_de_area` ya existen, pero
  ninguna pieza generada hoy lo ingesta: el único tipo que despacha
  (`difusion_de_actividad`) declara `area_emisora` en `no_aplican`. El
  ingestión a nivel pieza llega con la iteración de despacho por tipo.
- **La procedencia a nivel pieza.** `ProcedenciaInsumo` (ADR 0008) es
  vocabulario de insumo y `interpretar_solicitud` no tiene parámetro de
  procedencia, así que el origen se declara a nivel registro
  (`origen_hechos`), no a nivel pieza.
- **La sincronización del desplegable de actividades.** La carga a mano con
  identificadores de la planilla es el insumo provisional declarado;
  Apps Script queda como destino, el agente sigue sin escribir el Form.
- **La interfaz con la SEU.** La hoja v2 y el padrón de áreas están marcados
  `PROVISIONAL_NO_INSTITUCIONAL`; la lista de áreas viene del corpus histórico
  y no de una aprobación de la SEU.

## Antes de empezar

- No hace falta cuenta de Google ni credenciales: el modo offline usa un CSV
  como hoja de respuestas y escribe los avisos en un JSONL local.
- Hace falta una terminal en `Implementacion/Agente1` y `uv` disponible.
- El padrón es un CSV `correo,rol` externo al repo; para el ensayo sirven
  correos inventados, con el rol de quien genera dentro de la lista de roles
  habilitados (el circuito de generación lo exige igual que en producción).
- El id de actividad `SYN-001` existe en `data/actividades_sinteticas.csv`.
- El valor de la variable del entorno es el nombre completo del contrato:
  `canal_form_respuestas_v2`. Un atajo tipo `v2` no existe a propósito, para
  no sumar un segundo vocabulario.

## Paso a paso (offline)

### 1. Preparar directorio, padrón y hoja v2

```bash
cd Implementacion/Agente1
mkdir -p /tmp/demo-122
cat > /tmp/demo-122/padron.csv <<'EOF'
correo,rol
maria@example.invalid,TRADUCTOR
solicitante@example.invalid,coordinador_seu
EOF
cat > /tmp/demo-122/pedidos-v2.csv <<'EOF'
Marca temporal,Correo,Tipo de gacetilla,Actividad,Área emisora,Pedido
2026-10-17 09:00:00,solicitante@example.invalid,difusion_de_actividad,SYN-001,,necesito difusión del taller
2026-10-17 09:05:00,solicitante@example.invalid,newsletter,,cursos_complementarios,arregla el newsletter del mes
2026-10-17 09:10:00,maria@example.invalid,difusion_de_actividad,No es una actividad / no figura,,quiero una difusión sin actividad cargada
2026-10-17 09:15:00,maria@example.invalid,aviso_de_otra_area,,biblioteca,
EOF
```

La hoja declara cuatro historias: una difusión completa, un newsletter (tipo
con despliegue pendiente, con área en el padrón), una difusión sin actividad
cargada y un aviso de otra área con el área fuera del padrón.

### 2. Atender la hoja con el contrato v2 declarado

```bash
AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO=canal_form_respuestas_v2 \
PYTHONPATH=src python3 scripts/atender_canal_form.py \
  --directorio /tmp/demo-122 \
  --respuestas-csv /tmp/demo-122/pedidos-v2.csv \
  --padron /tmp/demo-122/padron.csv
```

Salida (el stdout trae sólo el pedido que entró al núcleo):

```text
{"correlation_id": "5fc07865-fdb1-4044-8de7-0d8bfe144a91", "estado": "PENDIENTE_VALIDACION", "intencion": "generar_gacetilla"}
{"atendidos": 1, "config": {"certificados": false, "modo_offline": true, "planes_pago": 0}, "modo": "offline_fake", "registro_atendidos": "atendidos-canal-form.jsonl"}
```

El pedido queda `PENDIENTE_VALIDACION` con intención `generar_gacetilla` y borrador
en `/tmp/demo-122/borradores/SYN-001.md`, marcado
`BORRADOR — NO PUBLICAR`.

### 3. Lo que quedó en el registro de atendidos

```text
{"contrato_hoja": "canal_form_respuestas_v2", "declarado": {"tipo": "newsletter"}, "estado": "INVALIDA", "origen_hechos": "solicitud", "resultado": "tipo_sin_despacho", "rol": "coordinador_seu", "rol_origen": "padron", "version_agente": "0.3.0"}
{"contrato_hoja": "canal_form_respuestas_v2", "declarado": {"tipo": "difusion_de_actividad"}, "estado": "INVALIDA", "origen_hechos": "solicitud", "resultado": "actividad_no_figura", "rol": "TRADUCTOR", "rol_origen": "padron", "version_agente": "0.3.0"}
{"contrato_hoja": "canal_form_respuestas_v2", "declarado": {"tipo": "aviso_de_otra_area"}, "estado": "INVALIDA", "origen_hechos": "solicitud", "resultado": "area_fuera_de_padron", "rol": "TRADUCTOR", "rol_origen": "padron", "version_agente": "0.3.0"}
{"contrato_hoja": "canal_form_respuestas_v2", "declarado": {"actividad": "SYN-001", "tipo": "difusion_de_actividad"}, "estado": "PENDIENTE_VALIDACION", "origen_hechos": "fuente_institucional", "resultado": null, "rol": "coordinador_seu", "rol_origen": "padron", "version_agente": "0.3.0"}
```

Tres bloqueos con su código y aviso, un despacho con lo declarado completo
(tipo y actividad). Nada del texto libre de la columna Pedido entra al
registro.

### 4. Los avisos que recibió quien pidió

Cada bloqueo entrega un aviso con el desenlace en claro. Verbatim, de
`estado-canal-form/avisos-offline.jsonl`:

```text
El tipo declarado todavía no despacha en este canal, así que nada se generó. Los datos que ese tipo exige los carga quien pide y el canal todavía no tiene las columnas para pedirlos; el circuito de pedidos sigue abierto por Form para lo que el núcleo reconoce.
```

```text
«No es una actividad / no figura» no da de alta ninguna actividad y nada se generó. Para una difusión, la actividad tiene que estar cargada en la planilla institucional: cargarla no es tarea de este agente.
```

```text
El área emisora declarada no está en el padrón cerrado del repo, así que nada se generó. Las áreas válidas son las del desplegable.
```

### 5. Sin la variable declarada, el camino de prosa #115 sigue igual

Relanzar la misma hoja **sin** la variable (contrato v1 por defecto) demuestra
que el circuito preexistente no cambió: las tres columnas de v1 se leen igual
y la columna de tipo se vuelve parte del pedido en prosa, que cae al extractor
del núcleo:

```text
{"correlation_id": "7aa17425-cf2d-4625-8d87-8354a239a5c6", "estado": "PENDIENTE_CONFIRMACION", "intencion": "generar_gacetilla"}
{"correlation_id": "8a96ae0b-0331-442c-8861-ee31a86e9365", "estado": "PENDIENTE_CONFIRMACION", "intencion": "generar_gacetilla"}
{"correlation_id": "22dccd72-4d53-4da0-969f-bada12be837b", "estado": "RECHAZADA", "intencion": null}
{"correlation_id": "940120a7-55c3-455b-b1ff-1d2eb964d651", "estado": "RECHAZADA", "intencion": null}
{"atendidos": 4, "config": {"certificados": false, "modo_offline": true, "planes_pago": 0}, "modo": "offline_fake", "registro_atendidos": "atendidos-canal-form.jsonl"}
```

Quien no declara la nueva forma de hoja no ve ninguna diferencia de fondo, y
nadie se sube al contrato v2 sin querer.

### 6. Contrato desconocido, rechazado

```bash
AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO=canal_form_respuestas_v99 \
PYTHONPATH=src python3 scripts/atender_canal_form.py \
  --directorio /tmp/demo-122 --respuestas-csv /tmp/demo-122/pedidos-v2.csv \
  --padron /tmp/demo-122/padron.csv
```

```text
{"estado": "RECHAZADA", "resultado": "canal_form_config_invalid"}
```

Exit code 2, la hoja no se lee. En live el mismo valor falla igual desde
`cargar_configuracion_canal_form`.

## Mecanismo elegido para el área emisora y su firma

- La forma declarada de cada tipo (#121) ya trae el placeholder
  `"pie": "{area_emisora}"` y el gate ya valida el emisor confirmado; el
  bloque `firmante` de la forma queda como membrete institucional fijo.
- El nuevo `contracts/areas_emisoras_v1.json` es el padrón cerrado id →
  firma (cuatro áreas del corpus histórico, `x-status: PROVISIONAL`).
- `firma_de_area(id_area)` es el wirado único: el id viaja declarado en la
  solicitud, la firma que imprime la pieza sale del padrón. Un aviso de otra
  área nunca se firma con el área que la hoja traiga en texto libre.
- Hoy `firma_de_area` en el canal valida y mapea; la ingesta del placeholder
  a nivel pieza queda para la iteración de despacho por tipo, porque el único
  tipo que despacha no lleva área (`no_aplican`).

Se eligió padrón cerrado y no texto libre (ni heurística sobre el texto)
porque el bug observado en el corpus fue justamente una pieza firmada por un
área que no la emitió; lista cerrada + gate le pone techo al problema.

## Verificación ejecutada

Desde `Implementacion/Agente1`:

```text
$ uv run pytest -q
2273 passed, 8 skipped in 54.92s

$ uv run ruff check .
All checks passed!
```

Los 26 tests de `tests/test_canal_form_respuestas_v2.py` cubren el circuito
pero con dobles de prueba; los dos tests nuevos del runner
(`test_runner_hoja_v2_offline_despacha_difusion_declarada` y
`test_runner_hoja_contrato_desconocido_rechaza`, en
`tests/test_plantillas_actividad.py`) amarran el camino offline del script
con el env real. El recorrido de arriba es la corrida manual end to end.

## Mapeo a los criterios del ticket

El mapeo usa el pedido del título (campo de tipo, actividad condicional, área
emisora por padrón) y el comportamiento verificado; la numeración exacta de
los criterios es del issue y este documento no la inventa.

| Criterio | Cómo queda demostrado |
|---|---|
| Campo de tipo como primera pregunta, lista cerrada | Sección 3 del paso a paso con el despacho declarado; contrato `canal_form_respuestas_v2`; el tipo fuera de la lista lleva `tipo_no_declarado` (tests) |
| Actividad condicional | Opción «No es una actividad / no figura» → `actividad_no_figura`; id bien formado no cargado → entra al núcleo y vuelve `INVALIDA` sin generación (AC de desenlace acotado, verbatim en tests `test_difusion_completa_despacha_por_el_clasificador_de_siempre` y `test_una_difusion_con_actividad_no_cargada_no_genera`) |
| Área emisora por padrón | Fuera del padrón → `area_fuera_de_padron`, aviso en claro; firma resuelta por `firma_de_area`, mecanismo arriba |
| Los seis tipos sin despacho acotados | `tipo_sin_despacho` con aviso y registro, sección 3; sin generación ni aproximación por parecido |
| El circuito #115 queda green | Sección 5 del paso a paso y suite completa en 2273 passed |
| Versiones y docs | Contratos versionados, `AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO` documentado en MANUAL 5.9, CHANGELOG 0.3.0 (Menor) |

## Pendientes abiertos

- Los cinco pasos live D2 del Form real (creación de preguntas, hoja y
  corrida con token) quedan pendientes del operador, mismo esquema que el
  recorrido de #72.
- Despacho por tipo de los seis tipos restantes y con ello la ingesta del
  placeholder `{area_emisora}` en la pieza.
- Procedencia a nivel pieza (`ProcedenciaInsumo`, ADR 0008): hoy el origen se
  declara a nivel registro.
- Apps Script para sincronizar el desplegable de actividades: destino
  declarado, no construido.
- Confirmación de la SEU de la lista de áreas y de la interfaz de la hoja
  (ambos contratos marcan `PROVISIONAL_NO_INSTITUCIONAL`).
- Glosario de `CONTEXT.md`: no se agregaron entradas «Área emisora» ni
  «Canal del Form».
