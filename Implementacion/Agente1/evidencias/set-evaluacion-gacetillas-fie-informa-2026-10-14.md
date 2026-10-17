# Set de evaluación de gacetillas — corpus FIE INFORMA (difusiones de actividad)

- **Ticket:** #111 (implementa la decisión #104, resuelta el 2026-10-14).
- **Fecha:** 2026-10-14.
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
suite. La **rúbrica humana queda sujeta a la aprobación de Juani antes de
medir**: hasta esa aprobación, el set no produjo ningún puntaje humano y no se
declara conformidad institucional.

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

Se excluyen y se declaran las piezas que **no cumplen** el criterio. Ninguna
es un caso cargado:

| Pieza | Por qué queda afuera |
|---|---|
| Experiencia académica en el Instituto Balseiro (28-5) | El flyer es una foto del expositor, no un afiche con datos; la fecha, el horario y el lugar viajan en el **cuerpo**, no en el flyer. Además nombra al expositor (dato personal). |
| Becas Progresar (24-6) | Aviso de un trámite administrativo («Plataforma Oficial»), no una actividad por realizarse. |
| Nueva ART (4-6) | Aviso de servicio, no una actividad. |
| Suspensión de Actividad Académica (26-5) | Aviso de una suspensión, no una invitación. |
| Inicio de inscripción a exámenes (26-6) | Aviso académico con la fecha en el cuerpo; no hay flyer con datos. |
| Convocatoria Tutores 2027 (9-6) | Convocatoria interna con datos en el cuerpo, sin flyer. Cae en el tipo «convocatoria interna», hoy sin pipeline. |
| Saludo del Director (9-7) | Saludo/efeméride, no una actividad por realizarse (tipo sin pipeline). |
| Crónicas («Noticias FIE», recorridas, ceremonias, capacitaciones) | Hecho ya ocurrido; tipo sin pipeline. |
| PRODE y FE DE ERRATAS | Recreativo con enlaces; tipo sin pipeline y con enlaces internos de casilla. |
| Newsletter, fallecimiento, avisos de estacionamiento / misa / vacuna | Tipos sin pipeline. |

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

El set se diseña **capability-gated**: declara los tipos de FIE INFORMA de
#106 con slots vacíos documentados. Un slot se llena cuando #106 prioriza el
tipo **y** existe su pipeline. Hoy sólo «difusión de actividad» tiene pipeline
(HU-010) y casos cargados.

| Tipo (#106) | Casos | Pipeline | Motivo del slot vacío |
|---|---|---|---|
| difusión de actividad | 8 | sí (HU-010) | tipo cargado |
| crónica | 0 | no | no existe código; #104 §2 verificó que no hay pipeline |
| aviso/comunicado | 0 | no | no existe código |
| saludo/efeméride | 0 | no | no existe código |
| convocatoria interna | 0 | no | no existe código |
| fallecimiento | 0 | no | no existe código |

Los posts de redes (HU-011) quedan como slot aparte, con la B2 de la SEU
todavía abierta (#105). **No se cargan casos de tipos sin pipeline.**

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

Puntúa una persona (Juani) **1 a 4 por caso y por dimensión**, con estas anclas
escritas. **La rúbrica queda sujeta a la aprobación de Juani antes de medir**:
las anclas son una propuesta del equipo, no un instrumento aprobado.

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

**Protocolo de corrida (decisión #104 §6).** **n = 3** por caso con la config
congelada de #51. Un caso pasa el automático **sólo si las tres corridas
pasan**; el puntaje humano es la **mediana**. El modelo es un parámetro, no una
decisión de este ticket.

**Umbral de aceptación (decisión #104 §8).** «Conforme» sólo si el automático da
**100 %** de los casos en verde **y** la mediana humana es **≥ 3** en cada
dimensión sin ningún caso < 2. Si no se alcanza, se declara el nivel real y la
brecha, sin maquillar.

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

- Los chequeos son de **contrato**, no de calidad institucional: no puntúan
  parecido a un FIE INFORMA ni verdad semántica.
- **No hay puntaje humano** ni aprobación de la rúbrica todavía.
- El set **no acredita** validación de la SEU, Gate G2 ni TRL 3.
- Los originales del corpus **no** están en el repo; el manifest cita su
  `sha256` sin copiar contenido.
