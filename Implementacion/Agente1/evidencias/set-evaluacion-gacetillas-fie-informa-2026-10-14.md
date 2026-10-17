# Set de evaluación de gacetillas — corpus FIE INFORMA (dos ejes)

- **Ticket:** #111 (implementa la decisión #104, resuelta el 2026-10-14; los
  dos ejes implementan el adendo del 17/10 de #120 y las formas de #121).
- **Fecha:** 2026-10-14; re-congelado el 2026-10-17.
- **Artefactos del set:**
  - `data/corpus-fie-informa-difusiones.csv` — filas reconstruidas, con el
    encabezado exacto de `COLUMNAS_ACTIVIDADES_V2` (15 columnas).
  - `data/corpus-fie-informa-difusiones.procedencia.csv` — procedencia por
    campo (flyer / provisional declarado / no informado / sintético).
  - `evidencias/manifest-set-evaluacion-gacetillas-fie-informa-2026-10-14.json`
    — manifest del set, `schema_version` propio, congelado por hash.
  - `tests/test_set_evaluacion_fie_informa.py` — chequeos automáticos.
- **Naturaleza:** artefacto de datos + rúbrica. **No** es un pipeline nuevo:
  reutiliza el pipeline HU-010 y su gate de validación.

**Estado de aprobación.** Los chequeos automáticos corren y pasan en la
suite. La **rúbrica humana quedó aprobada por Juani el 16/10**: las anclas 1 a
4 de las tres dimensiones son el instrumento del eje 1. El set todavía no
produjo ningún puntaje humano (las corridas de medición no se ejecutaron) y no
se declara conformidad institucional.

## Los dos ejes

La ampliación del 17/10 (#120 con #121) parte el set en dos ejes: el set deja
de cubrir sólo difusión de actividad y pasa a cubrir **los siete tipos de
gacetilla del contrato** (`src/agente1/contracts/tipos_gacetilla_v1.json`),
cada uno con el eje que le corresponde.

| Eje | Qué mide | Cómo | A qué tipos aplica |
|---|---|---|---|
| **Eje 1: calidad de la prosa generada** | La rúbrica 1 a 4 por dimensión, con el umbral vigente (automático 100 %, mediana humana ≥ 3, ningún caso < 2) | Humano | Sólo los tipos que **generan**: difusión de actividad y saludo o efeméride |
| **Eje 2: conformidad de forma** | Binario y automático: ¿la pieza es un FIE INFORMA reconocible de su tipo, con su encabezado, su firmante, su pie, sus fórmulas y sus etiquetas, y contiene exactamente lo confirmado? | Automático (chequeo determinista, sin rúbrica) | **Los siete tipos, sin excepción** |

Dos reglas que el manifest declara con todas las letras y que este documento
repite:

1. **Declarar conformidad de forma no declara conformidad de calidad.** El eje
   2 es un chequeo determinista de forma; puntuar 1 a 4 algo determinista no
   diría nada. Es la vía por la que entran las misas, la vacunación, la
   convocatoria de tutores y el fallecimiento.
2. **El umbral vigente aplica sólo al eje 1.** Automático 100 % en verde y
   mediana humana ≥ 3 en cada dimensión sin ningún caso < 2 es el umbral del
   eje 1; el eje 2 no tiene rúbrica ni umbral humano.

La rúbrica no se rehace: **la rúbrica vigente es el instrumento del eje 1 y no
cambia porque el set crezca**; sólo cambia qué tipos la usan. Lo único que se
declara por caso es **contra qué se mide la fidelidad de sentido** cuando el
tipo genera, porque la fuente cambia: en difusión es la fila de la actividad;
en un saludo son la ocasión y la fecha. Eso vive en cada caso, no en la
rúbrica.

## Criterio de inclusión

Entra un caso si la pieza del corpus es una **difusión de actividad de
extensión** (tipo con pipeline: HU-010) y cumple las tres condiciones:

1. **Invitación a una actividad por realizarse** (curso, diplomatura,
   conferencia, charla o jornada), no un hecho ya ocurrido ni un aviso de
   servicio.
2. **El texto del borrador es mínimo** (a veces sólo el título): el contenido
   informativo viaja en el **flyer** (imagen embebida del `.docx`).
3. **Los datos del flyer se pueden transcribir** a los 15 campos del contrato
   v2 sin traer datos personales, teléfonos, enlaces internos ni metadatos de
   autor.

Este criterio arma las filas del dataset del eje 1 para difusión. La
ampliación del 17/10 mantiene el criterio para las filas del CSV y agrega dos
vías de entrada nuevas, fuera de este criterio: el caso Balseiro (pendiente,
ver más abajo) y los casos de forma del eje 2 (ver «Slots por tipo»).

Piezas incluidas (8 filas, 6 piezas lógicas; la pieza «Diplomaturas segundo
semestre» aporta dos actividades):

| id | Pieza del corpus | Actividad |
|---|---|---|
| `FIE-DIF-01` | Fie informa 26-5 (revisiones 4-6 y 30-6) | Diplomatura Universitaria en Formación Integral para Instructores de Tiro |
| `FIE-DIF-02` | Fie informa 8-6 | Curso IA Aplicada a la Gestión Documental I — 3ª Edición |
| `FIE-DIF-03` | Fie informa 29-6 | Conferencia «Los desafíos de la conquista del espacio» |
| `FIE-DIF-04` | Fie informa 15-5 | Día de la Escarapela |
| `FIE-DIF-05` | Fie informa 2-6 | 2º Jornada CTID+I 2026 |
| `FIE-DIF-06` | Fie informa 1-6 | Semana de la Ingeniería — FIUBA |
| `FIE-DIF-07` | Fie informa 30-6 | Diplomatura Universitaria en Infraestructuras Antárticas |
| `FIE-DIF-08` | Fie informa 30-6 | Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional |

La pieza 26-5 tiene tres revisiones del flyer (inicio 10/06, 24/06 y 15/07).
Se carga **una** actividad (la del flyer original, inicio 10/06) y se
documentan las revisiones: no son piezas nuevas, son re-fechados de la misma
actividad.

## Piezas dudosas excluidas

Se excluyen del criterio del **eje 1** (filas del CSV de difusión) y se
declaran las piezas que **no cumplen** el criterio. La ampliación del 17/10 no
las vuelve difusión: las re-clasifica al tipo que les corresponde del
contrato, y entran por ahí (eje 2) o quedan fuera de alcance. Ninguna es un
caso cargado del CSV:

| Pieza | Por qué queda afuera del eje 1 | Destino según el 17/10 |
|---|---|---|
| Becas Progresar (24-6) | Aviso de un trámite administrativo («Plataforma Oficial»), no una actividad por realizarse. | Aviso de otra área (eje 2, no representante del tipo) |
| Nueva ART (4-6) | Aviso de servicio, no una actividad. | Aviso de otra área (eje 2, no representante del tipo) |
| Suspensión de Actividad Académica (26-5) | Aviso de una suspensión, no una invitación. | Aviso de otra área (eje 2, no representante del tipo) |
| Inicio de inscripción a exámenes (26-6) | Aviso académico con la fecha en el cuerpo; no hay flyer con datos. | Aviso de otra área (eje 2, no representante del tipo) |
| Saludo del Director (9-7) | Saludo/efeméride, no una actividad por realizarse. | Saludo o efeméride (eje 1 y 2); el representante del tipo es el Día del Ingeniero (16-6), que entra como FIE-SAL-01 |
| Newsletter (18-6) | Boletín con adjunto, no es difusión. | Newsletter: entra como FIE-NEW-01 (eje 2) |
| Comunicados de fallecimiento | Fórmula fija, no es difusión. | Fallecimiento: entra como FIE-FAL-01 (eje 2), con la plantilla con huecos como representante |
| Misa (2-7) y aviso de vacunación | Avisos de otra área con datos en el cuerpo. | Aviso de otra área: la misa entra como FIE-AVI-01 y la vacunación como FIE-AVI-02 (eje 2) |
| Convocatoria Tutores 2027 (9-6) | Convocatoria interna con datos en el cuerpo, sin flyer. | Convocatoria interna: entra como FIE-CON-01 (eje 2) |
| Crónicas («Noticias FIE», recorridas, ceremonias, capacitaciones) | Hecho ya ocurrido; no hay prosa que puntuar. | Crónica de evento: el representante del tipo es la recorrida institucional (12-5), que entra como FIE-CRO-01 |
| PRODE y FE DE ERRATAS | Recreativo con enlaces internos de casilla. | Fuera de los dos ejes, salvo que la SEU lo priorice en #106 |

El caso Balseiro ya no está en esta tabla: deja de ser dudoso y pasa a ser un
caso declarado del eje 1 que espera su fuente de datos.

### El caso Balseiro (28-5): pendiente de transcripción

La pieza «Experiencia académica en el Instituto Balseiro» (28-5) es la única
difusión del corpus con los datos **en el cuerpo** y no en el flyer, y nombra
al expositor (dato personal; el repo es público y el set prohíbe datos
personales). La decisión del 17/10 la suma al eje 1, **transcrita al contrato
igual que las otras y con el nombre del expositor anonimizado**.

Estado del caso `FIE-DIF-09` en el manifest: **PENDIENTE_SEU**.

- La transcripción exige leer el cuerpo del `.docx` original, que está en
  custodia local fuera del repo (el análisis #103 no transcribe ese cuerpo) y
  no hay fila en `data/`: **no se inventan fecha, horario, lugar, organiza ni
  contacto**.
- La fuente de fidelidad del caso (la fila de la actividad) queda declarada
  pendiente de ese dato. El caso **no corre por el pipeline** hasta que la SEU
  habilite la transcripción.
- Al transcribir: el expositor entra anonimizado y la fila declara su
  procedencia por campo en el sidecar, con las mismas convenciones que las
  otras filas (`flyer` cuando aplique, `provisional` para lo declarado,
  `PENDIENTE_SEU` para lo que la SEU tenga que confirmar).

**Diferencia con el conteo «9» de #103.** El análisis del corpus (#103, §3)
estima «unas 9» difusiones. El criterio explícito del issue —texto mínimo y
datos en el flyer— fija **6 piezas lógicas / 8 actividades**. La diferencia se
debe a que #103 contó de forma gruesa y a que la revisión de la pieza de
Diplomaturas suma actividades. Se asienta el número reproducible del set y no
se fuerza el «9». (*Supuesto documentado.*)

## Procedencia por campo

Cada uno de los 15 campos de las 8 filas declara su origen en
`data/corpus-fie-informa-difusiones.procedencia.csv`:

- `flyer` — el dato está en la imagen del flyer.
- `provisional` — el flyer no lo trae y se declara un valor para completar el
  `required` del contrato o para fijar un hecho del correo.
- `no_informado` — campo opcional del contrato v2 que la pieza no informa;
  queda vacío para que el renderer lo omita.
- `sintetico` — campo de procedencia armado para el set (`id_actividad`,
  `fuente`); no sale del flyer.

Reglas de transcripción aplicadas:

- Los datos del flyer **cualitativos** («arancelada», «gratuito», «acceso
  libre») van a `descripcion`.
- Los datos del flyer **con números** (créditos INAP, descuentos porcentuales,
  montos) **no** se transcriben a la prosa: `descripcion` se redacta sin
  dígitos para que la prosa del pipeline no arrastre hechos no autorizados
  (`PATRON_PROSA_SIN_DATOS`).
- No se transcriben enlaces reales de inscripción (formularios/paneles
  públicos): `enlace_inscripcion` queda `no_informado`.
- No se transcriben nombres de expositores ni datos personales.

## Slots por tipo

Desde #121 los siete tipos del contrato (`tipos_gacetilla_v1`) tienen forma
declarada, renderer único y gate por tipo, así que **ningún slot queda vacío
por falta de pipeline**: los tipos que extraen y confirman se cubren con el
chequeo mecánico de forma del eje 2 (un caso representativo por tipo), y los
que generan se cubren además con la rúbrica del eje 1.

| Tipo (contrato) | Modo | Eje 1 (rúbrica) | Eje 2 (forma) | Caso del eje 2 | Fuente declarada |
|---|---|---|---|---|---|
| difusion_de_actividad | genera | 8 casos + 1 pendiente | 1 | FIE-DIF-01 (pieza 26-5) | la fila de la actividad del dataset |
| cronica_de_evento | extrae y confirma | 0 (no genera) | 1 | FIE-CRO-01 (recorrida, 12-5) | lo confirmado |
| aviso_de_otra_area | extrae y confirma | 0 (no genera) | 2 | FIE-AVI-01 (misa, 2-7) + FIE-AVI-02 (vacunación) | lo confirmado |
| convocatoria_interna | extrae y confirma | 0 (no genera) | 1 | FIE-CON-01 (tutores 2027, 9-6) | lo confirmado |
| saludo_o_efemeride | genera | 1 | 1 | FIE-SAL-01 (Día del Ingeniero, 16-6) | la ocasión y la fecha de la pieza |
| fallecimiento | extrae y confirma | 0 (no genera) | 1 | FIE-FAL-01 (plantilla con huecos) | lo confirmado |
| newsletter | extrae y confirma | 0 (no genera) | 1 | FIE-NEW-01 (newsletter, 18-6) | lo confirmado |

Lo que dispara cada caso:

- **Difusión (eje 1):** las 8 filas de `data/corpus-fie-informa-difusiones.csv`
  corren por HU-010; FIE-DIF-09 (Balseiro, 28-5) queda declarado PENDIENTE_SEU
  sin fila hasta tener la transcripción.
- **Difusión (eje 2):** el representante es la pieza del 26-5, la misma que
  FIE-DIF-01.
- **Saludo o efeméride (eje 1):** el prompt `saludo_o_efemeride_v1` existe en
  `src/agente1/prompts/`, así que el tipo se sienta en el eje con su caso
  FIE-SAL-01; su fuente de fidelidad declarada es la ocasión y la fecha, no una
  fila del CSV.
- **Misa y vacunación (eje 2):** van al slot `aviso_de_otra_area`, no a
  difusión: son avisos de otra área en el corpus (#103 §3).
- **Convocatoria de tutores (eje 2):** slot `convocatoria_interna` (la pieza
  del 9-6).
- **Fallecimiento (eje 2):** slot `fallecimiento`; el representante es la
  plantilla con huecos, que no trae datos de personas.

**Fuera de los dos ejes:** el PRODE y las piezas recreativas (4tos de final,
16avos) y el afiche-programa sin cuerpo, salvo que la SEU los priorice en
#106.

Los posts de redes (HU-011) siguen como slot aparte, con la B2 de la SEU
todavía abierta (#105).

## Campos provisionales

Valores declarados por no venir del flyer (lista completa en el sidecar):

- `publico` — **provisional en las 8 filas**: ningún flyer lo informa.
- `modalidad` — **provisional en `FIE-DIF-03`, `04`, `05`, `06`, `08`**:
  inferida del lugar o de «clases sincrónicas»; el flyer no la declara.
- `contacto` — **provisional en `FIE-DIF-04`, `05`, `06`**: se declara el
  contacto de área de la SEU; el flyer no lo informa.

Todo campo `provisional` es un valor de andamiaje del set, **no un dato
institucional validado**. Si la SEU confirma el valor real, se reemplaza y se
re-congela el manifest.

## Rúbrica humana

Puntúa una persona (Juani) **1 a 4 por caso y por dimensión**. La rúbrica fue
aprobada: **la aprobación de Juani quedó registrada el 16/10** y las anclas 1 a
4 de las tres dimensiones son el instrumento vigente del eje 1. El instrumento
**no cambia** con la ampliación a los dos ejes: sólo cambia qué tipos la usan
(sólo los que generan). Las corridas de medición siguen sin ejecutarse: la
aprobación de la rúbrica no produce puntajes.

Dimensiones: (a) **parecido a un FIE INFORMA**, (b) **fidelidad de sentido**,
(c) **claridad y uso**.

| Puntaje | (a) parecido a un FIE INFORMA | (b) fidelidad de sentido | (c) claridad y uso |
|---|---|---|---|
| 1 — no publicable | El registro no es el de un FIE INFORMA: tono ajeno, tuteo peninsular, lenguaje de marketing o de proceso interno. | Inventa, altera o contradice hechos del flyer (fechas, lugar, organiza, contacto) o agrega datos que no están. | No se entiende qué se ofrece, a quién o cómo participar; la pieza no se puede usar. |
| 2 — publicable con reescritura mayor | Se reconocen el asunto, los hechos y el pie, pero la prosa suena artificial o genérica; habría que reescribir buena parte. | Todos los hechos están, pero uno o más están mal jerarquizados o reformulados de un modo que puede confundir. | Se entiende la propuesta, pero faltan datos de uso (a quién, cuándo, cómo inscribirse) o hay ruido que obliga a releer. |
| 3 — publicable con retoque menor | La pieza se parece a un FIE INFORMA real; el registro es rioplatense y sobrio; admite un retoque de estilo antes de enviar. | Fiel: coincide con el flyer en título, fechas, lugar, organiza y contacto; no agrega hechos. | Clara y usable: se entiende la propuesta y el circuito de participación sin relecturas. |
| 4 — publicable tal cual | Idéntica en registro, estructura y tono a un FIE INFORMA del corpus; no requiere cambios. | Fiel en todos los hechos y en el sentido; nada de más ni de menos. | Lista para difundir sin cambios: invita, informa y orienta la inscripción. |

## Chequeos automáticos

Se reutiliza el gate existente (`procesar_fila_csv` y sus validaciones). Los
chequeos binarios, por caso (todos deben dar verde):

1. **Estructura del borrador** — las cinco secciones del contrato, en orden.
2. **Todos los campos v2 presentes** — `renderer_fact_missing` = 0.
3. **Nombre del Doc** — `BORRADOR — Fie informa D-M <título>`.
4. **Pie fijo + firma institucional** — «Departamento de Cursos
   Complementarios / Secretaría de Extensión Universitaria» y la firma de la
   facultad.
5. **`Consultas:` = contacto** de la fila.
6. **Largos** — dentro de `MAX_BORRADOR_CHARS`, bajada y cuerpo dentro de sus
   límites de palabras.
7. **Registro rioplatense sin tuteo** — `PATRON_TUTEO` (reutilizado de posts).
8. **Prosa sin datos** — `PATRON_PROSA_SIN_DATOS` sobre bajada y cuerpo.
9. **Sin proceso interno (DEF-A1-017)** — nada de «revisión», «validación»,
   «aprobación», «borrador» ni «pendiente» en la prosa de lectura pública.
10. **Regresión nueva: no reproduce las erratas del corpus** — ni el set ni la
    salida contienen las erratas tipificadas en #103 §5 («visitaros»,
    «FRACIA», «NOTIFICAS», «elpe», «Secretaria», «activiad»). Es la regresión
    que **#105** necesita para no enseñar los errores del corpus vía few-shot.
    Esta lista es el conjunto de chequeos del **eje 1**: estructura, hechos y
    registro de la prosa generada de difusión.

### Chequeos automáticos del eje 2 (conformidad de forma)

Por tipo, los siete, binario y automático, sin rúbrica:

1. **Forma declarada por tipo** — cada tipo tiene su archivo versionado en
   `src/agente1/contracts/formas/<tipo>_v1.json` (#121, congelado en el
   manifest de versión).
2. **Render contra la forma** — la pieza representativa del tipo se arma con
   el renderer único de #121 y se compara byte a byte contra
   `golden/formas/<tipo>.md`.
3. **Gate por tipo** — núcleo común (largo, sin marcadores sin resolver, sin
   vocabulario de proceso interno, cada hecho impreso contra lo confirmado)
   más las reglas propias del tipo (un aviso no afirma una invitación, un
   fallecimiento no inventa un nombre, un comunicado no inventa el área
   emisora).
4. **Sin datos que la forma no imprima** — la pieza contiene exactamente lo
   confirmado: en extrae y confirma, los datos los carga quien pide.

El caso representativo por tipo es declarativo (qué pieza del corpus
representa al tipo); el chequeo mecánico es el mismo para todos los casos del
tipo, porque la conformidad es de la forma. Estas verificaciones corren en
`tests/test_gacetillas_formas.py` (#121) y el set las declara en su manifest
con el mapeo tipo-caso-forma-golden.

**Protocolo de corrida (decisión #104 §6).** **n = 3** por caso con la config
congelada de #51. Un caso pasa el automático **sólo si las tres corridas
pasan**; el puntaje humano es la **mediana**. El modelo es un parámetro, no una
decisión de este ticket.

**Umbral de aceptación (decisión #104 §8).** «Conforme» sólo si el automático da
**100 %** de los casos en verde **y** la mediana humana es **≥ 3** en cada
dimensión sin ningún caso < 2. Si no se alcanza, se declara el nivel real y la
brecha, sin maquillar. **Este umbral aplica sólo al eje 1**: declarar
conformidad de forma (eje 2) no declara conformidad de calidad.

**Interfaz con #105 (decisión #104 §9).** El set registra por caso: resultado
automático, puntaje humano por dimensión, versiones (prompt / contrato /
renderer / modelo) y hashes. #105 corre los dos brazos con el mismo protocolo
(n = 3) y adopta el few-shot **sólo si sube la mediana humana sin degradar
ningún automático**.

## Supuestos (opción conservadora)

1. **Número de piezas.** Se fija el número reproducible del criterio (6 piezas
   / 8 filas) y no el «9» grueso de #103.
2. **Diplomaturas segundo semestre = dos filas.** La pieza anuncia tres
   flyers; el de Instructores de Tiro es un re-fechado de `FIE-DIF-01`, así que
   sólo se cargan las dos actividades nuevas (Antárticas y Geomática).
3. **Semana de la Ingeniería incluida.** Es una invitación a actividades por
   realizarse con datos en el flyer, aunque la organiza otra universidad y el
   cuerpo traiga texto. Se marca como borde del criterio.
4. **Contactos de área.** Se usan correos institucionales de área que ya están
   publicados en los flyers y en el propio repo; no se usan correos personales.
   Cuando el flyer no informa contacto, se declara uno de área como
   provisional.
5. **Sin enlaces reales.** No se transcriben formularios ni paneles públicos:
   `enlace_inscripcion` queda vacío.
6. **Sin datos personales.** No se transcriben nombres de expositores aunque el
   flyer sea público; ante la duda, no se incluye el dato.
7. **`fecha_inicio` del ciclo.** Para la Semana de la Ingeniería se usa el
   primer día del ciclo (lunes 1 de junio), no el día destacado en el borrador.

## Límites y lo que no acredita

- Los chequeos del eje 1 son de **contrato**, no de calidad institucional: no
  puntúan parecido a un FIE INFORMA ni verdad semántica.
- **Rúbrica aprobada (16/10), corridas de medición no ejecutadas**: el set
  todavía no produjo ningún puntaje humano.
- **Declarar conformidad de forma no declara conformidad de calidad.** El eje
  2 verifica forma; la calidad se evalúa con la rúbrica del eje 1, sólo en los
  tipos que generan.
- Las formas declaradas y el catálogo de tipos siguen
  **PROVISIONAL_NO_INSTITUCIONAL**: sin aprobación de la SEU.
- El set **no acredita** validación de la SEU, Gate G2 ni TRL 3.
- Los originales del corpus **no** están en el repo; el manifest cita su
  `sha256` sin copiar contenido. Los casos representativos del eje 2 se citan
  por nombre de pieza, sin hash propio (el hash va con la custodia local);
  FIE-DIF-09 (Balseiro) queda PENDIENTE_SEU sin transcribir.
