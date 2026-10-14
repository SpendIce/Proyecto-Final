# Corpus FIE INFORMA histórico — análisis sin datos personales

- **Fecha de análisis:** 2026-10-13
- **Ticket de origen:** #103 (ticket #102 fijó qué cierra el corpus; alimenta #104 y #107)
- **Estatus del corpus:** ejemplo aprobado de **formato y estructura** (no de
  ortografía). Fija B1, B3 y B4 de «Visita a la SEU» (#14); B2 (posts) sigue
  abierta.
- **Custodia:** los originales **no** viven en el repo. Copia canónica local
  fuera de todo repo git: `/home/spendice/Documents/P100-Corpus-FIE-Informa/`
  (zip + 64 `.docx` + `MANIFEST-2026-10-13.txt`). Cuando se migre la unidad
  compartida del agente (#100, ADR 0007), pasan ahí.

> **Qué NO contiene este documento.** Nombres de personas, teléfonos, correos
> personales, enlaces internos/privados ni metadatos de autor. Cuando hace
> falta señalar un dato, se describe **la clase** de dato, no el dato. Única
> excepción autorizada por el ticket: los datos de los **flyers de avisos
> públicos** (cursos, diplomaturas, conferencias), que ya se difundieron
> (§6). Aun así se omitieron los nombres de expositores.

## 1. Procedencia y huella

- **Origen:** zip «Histórico - FIE INFORMA-20261013T201901Z-1-001.zip»,
  descargado por el autor desde Drive el 2026-10-13. Contiene una carpeta
  plana con **64 archivos `.docx`** (los borradores Word de cada FIE INFORMA).
- **Huella (sha256) del zip:**
  `aa8c64fa1ef79dbfa8e91be484b85a2cfebd18d5979b5cb4b4c63471a80fac46`
  (prefijo `aa8c64fa`, sufijo `fac46`; coincide con la esperada). El sha256 por
  archivo vive en el `MANIFEST-2026-10-13.txt` de la carpeta local.
- **Naturaleza del material:** son **borradores de trabajo**, no las piezas
  publicadas. Los `.docx` traen el cuerpo del mensaje; la firma institucional y
  el ensamblado final los agrega el canal de correo (§4). 43 de los 64 archivos
  embeben al menos una imagen (flyer) — ver §4.

## 2. Deduplicación 64 → 44

Método reproducible: se extrae `word/document.xml` de cada `.docx`, se
normaliza el texto (se colapsan espacios y saltos) y se calcula su sha256.

| Medida | Valor |
|---|---|
| Archivos `.docx` entregados | **64** |
| Pares de cuerpo **idéntico** (sólo cambia el nombre del archivo) | 21 |
| Textos únicos por hash exacto (64 − 21) | **43** |
| Variantes casi idénticas (misma pieza, otra revisión) | 2 pares |
| **Piezas lógicas** | **41** |

**Los 21 pares de cuerpo idéntico.** En cada uno conviven dos nombres: una
versión «descriptiva» (tema) y otra «fecha a secas», con el mismo cuerpo. La
dupla es (fecha, tema): 2-6 · CTID+I; 5-6 · capacitación de bomberos;
2-7 · misa; 12-5 · recorrida institucional; 13-7 · semifinales; 15-5 · entrega
de escarapelas; 16-6 · día del ingeniero; 16-7 · ceremonia 9 de julio;
18-6 · newsletter; 19-6 · noticias; 24-6 · becas; 26-5 · diplomatura;
28-5 · conmemoración; 28-6 · 16avos; 30-6 · diplomaturas; 7-5 · estacionamiento
motos; 7-7 · 4tos de final; 8-5 · estacionamiento; 8-6 · curso IA;
8-7 · estacionamiento; 9-7 · saludo del Director. Los 22 archivos restantes no
tienen par exacto.

**Las 2 variantes casi idénticas (misma pieza, otra revisión):**

1. La pieza «visita al Instituto Nacional del Profesorado Técnico» aparece dos
   veces; la única diferencia es una tilde en un topónimo («TECNOLOGICA» /
   «TECNOLÓGICA»). Son la misma pieza.
2. El aviso «inicio de inscripción a exámenes…» aparece dos veces; el segundo
   arrastra el título repetido en el cuerpo. Es la misma pieza, otra revisión.

**Reconciliación con el «44» de #102 (supuesto).** El ticket #102 registra
**44 piezas únicas**; el conteo por hash exacto da **43 grupos** (64 − 21) y
**41 piezas lógicas** tras unificar los dos pares casi idénticos. La diferencia
de ±1 con el «44» es consistente con que en #102 no se haya colapsado uno de
los 21 pares de cuerpo idéntico (probablemente un par cuyo nombre sugiere dos
piezas distintas). No se fuerza el número: queda asentado para que el **set de
evaluación (#104) fije el denominador**. (*Supuesto documentado.*)

## 3. Tipología con conteo

Sobre las **41 piezas lógicas**:

| Tipo | Piezas | Qué es |
|---|---|---|
| Difusión de actividad de extensión | 9 | curso, diplomatura, conferencia o charla por realizarse; el texto es mínimo y los datos viajan en el flyer |
| Crónica de evento («Noticias FIE») | 9 | hecho ya ocurrido (ceremonias, visitas, capacitaciones, reuniones) |
| Aviso de otra área (oficina) | 12 | estacionamiento, misa, vacuna, mesas de examen, ART, becas, suspensión |
| Pronóstico PRODE (recreativo) | 5 | pronósticos del Mundial 2026 + el aviso de mantenimiento del sistema |
| Saludo / efeméride | 2 | día del ingeniero; saludo del Director por el 9 de julio |
| Comunicado de fallecimiento | 2 | uno con datos y uno con huecos (plantilla) |
| Newsletter | 1 | boletín de un observatorio, con enlace a un adjunto |
| Programa / otro | 1 | afiche-programa de una jornada, sin cuerpo |

Los conteos gruesos de #102 («unas 9 difusiones, unas 8 crónicas, unos 12
avisos, Prode, saludos y una plantilla de fallecimiento») son consistentes con
esta clasificación.

## 4. Rasgos de formato por tipo

### Dónde viaja el contenido (regla transversal)

Hay **dos portadores** del contenido, y esto cambia según el tipo:

- **Cuerpo de texto:** avisos de otras áreas, crónicas, PRODE y saludos. Fechas,
  horarios, enlaces y contactos van como texto.
- **Flyer / imagen embebida:** en las **difusiones de cursos y conferencias** el
  `.docx` casi no tiene texto (a veces sólo el título) y **los datos viajan en
  la imagen del flyer**. 43 de los 64 archivos embeben al menos una imagen; al
  enviarse, la SEU adjunta el flyer. Es la causa de que el texto del correo
  (una línea de invitación + «inscripción» + Consultas) sea tan corto.

### Encabezado

Tres estilos observados, más el caso «sin encabezado»:

- `FIE INFORMA D-M` en mayúsculas y con guion (p. ej. 27-4, 30-4).
- `Fie informa D-M` con barra (`1/7`, `29/6`, `2/7`, `7/7`, `8/7`) o guion
  (`24/6`, `30/6`); la fecha es la de generación.
- Rótulo **`NOTIFICAS FIE`** en las crónicas (mal escrito, §5).
- Muchas piezas arrancan directo con el título, sin línea de encabezado.

El glosario (`CONTEXT.md`, «FIE Informa») fija que el documento se llama
«Fie informa D-M \<título\>» y que **el cuerpo no lleva esa línea**. En los
borradores esa línea del nombre queda pegada al inicio del cuerpo: candidato a
descartar en el renderer. El título suele figurar **dos veces** seguido
(borrador).

### Pie (firma)

El **pie no está en el `.docx`**: ningún archivo trae texto en encabezado ni
pie (sólo 1 de 64 tiene un XML de `header/footer`, y vacío). La firma
**institucional** (Facultad de Ingeniería del
Ejército + lema histórico de la unidad + UNDEF + teléfono y dirección
institucionales + sitio) y la firma **del área** las agrega el canal de correo,
no el borrador. Firmas de área observadas por tipo: «Departamento de Cursos
Complementarios / Secretaría de Extensión Universitaria» (cursos), «Secretaría
Académica» (exámenes), «Secretaría de Extensión Universitaria» (avisos de la
SEU), «DOE» (tutorías). Es coherente con la decisión de #102: **pie fijo**.

### Enlaces

Presentes **en el cuerpo** de 20 de 64 archivos (no en el flyer). Clases de
destino: formularios (`forms.gle`, `docs.google.com`), hojas/paneles de datos
(`datastudio.google.com`), documentos y adjuntos de Drive
(`drive.google.com` — algunos son **enlaces internos de la casilla**, con
identificador de usuario: nunca reproducir), sitios institucionales
(`fie.undef.edu.ar`, `argentina.gob.ar`) y un video (`youtu.be`).

### Por tipo

| Tipo | Cuerpo | Datos en el flyer | Enlaces | Pie |
|---|---|---|---|---|
| Difusión de actividad | mínimo (invitación + «inscripción» + Consultas) | casi todos los datos | sí (inscripción) | Departamento de Cursos Complementarios / SEU |
| Crónica | texto corrido (1–3 párrafos) | no | a veces | institucional |
| Aviso de otra área | texto corto y directo | no | a veces | área emisora (Académica, SEU, etc.) |
| PRODE | texto + enlaces | no | sí (pronóstico + tabla) | SEU |
| Saludo / efeméride | 1–2 frases | no | no | institucional |
| Fallecimiento | fórmula fija con huecos | no | no | institucional |
| Newsletter | 1 línea + adjunto | no | adjunto | área emisora |

## 5. Erratas como clase (sin citar personas)

El corpus tiene errores **reales y variados**. Se listan como clases, sin
identificar a nadie:

- **Tipeo en verbo:** «visitaros» por «visitaron».
- **Nombre propio mal escrito:** «FRACIA» por «FRANCIA».
- **Rótulo mal escrito:** «NOTIFICAS FIE» por «NOTICIAS FIE».
- **Palabra cortada/pegada:** «elpe encontrará» por «el Prode… encontrará»
  (un aviso posterior, «FE DE ERRATAS», corrige ese texto).
- **Tilde faltante en topónimo:** «TECNOLOGICA» / «TECNOLÓGICA» en dos copias
  de una misma pieza.
- **Tilde faltante en cargo:** «Secretaria» por «Secretaría».
- **Palabra mal escrita:** «activiad» por «actividad».
- **Título duplicado** dentro del mismo borrador.
- **Concordancia en el cierre:** «Agradecemos sepan disculpar las molestias».
- **Piezas incompletas** que quedaron en el histórico: sólo el título, cuerpo
  vacío (p. ej. avisos de una línea).
- **Mecanismo de corrección:** existe al menos una pieza **«FE DE ERRATAS»**
  que enmienda un aviso previo. El canal admite emitir correcciones; como
  mínimo, el agente no debe perpetuar el error.

**Regla:** el corpus es referencia de **formato y estructura**, no de
ortografía. El agente copia el registro, no los errores.

## 6. Datos de flyers de avisos públicos (transcripción)

Flyers verificados (material ya difundido). Se transcriben los datos; se omite
el nombre de expositores por criterio de datos personales. La transcripción
completa del resto queda para #104.

| Pieza | Datos del flyer |
|---|---|
| Diplomatura Universitaria en Formación Integral para **Instructores de Tiro** | Inicio 10/06; finalización 29/10; cursada **híbrida** (presencial y virtual) 18:30–22:00; requisitos: conocimientos previos de armas de fuego y práctica en tiro; inscripción previa por **SIU**; actividad **arancelada**; consultas `cursos@fie.undef.edu.ar` |
| Curso **IA Aplicada a la Gestión Documental I — 3ª Edición** | cursada 25/06 al 06/08; inscripción por SIU 08/06 al 19/06; modalidad **online y autogestionado**; **gratuito**; reconocimiento **INAP (12 créditos)**; consultas `cursos@fie.undef.edu.ar` |
| Conferencia **«Los desafíos de la conquista del espacio»** | acceso libre y gratuito; 1 de julio 18:00; lugar: Centro Educativo de las Fuerzas Armadas, Av. Luis María Campos 480, Aula Magna; inscripción `redes.seyc@fmc.undef.edu.ar`; organiza Facultad Militar Conjunta / Universidad Austral – Escuela de Gobierno |
| **Día de la Escarapela** | lunes 18 de mayo; Hall de Banderas; invitación a retirar la escarapela |
| **Diplomaturas segundo semestre** | afiche con varios «Más información» (flyers múltiples, sin texto propio) |

**Patrón confirmado:** en estas piezas el borrador `.docx` es casi vacío y todo
el contenido informativo está en el flyer. El correo aporta sólo la invitación,
la palabra «inscripción»/«Más información» y el contacto.

## 7. Datos personales presentes en el corpus (clase, sin reproducir)

Motivo por el que los originales quedan **fuera** del repo:

- **Nombres de personas** en las crónicas (autoridades, docentes, expositores,
  y el nombre de una persona fallecida + su familia).
- **Un teléfono móvil personal** en el flyer de una jornada recreativa (clase:
  teléfono personal dentro de material de difusión).
- **Enlaces internos de casilla** (adjunto de Drive con identificador de
  usuario) en una pieza.
- **Correos institucionales de área** (cursos@, comunicacion@, sanidad@, doe@):
  de área, no personales.
- **Metadatos de autor:** los **64** `.docx` declaran el **mismo nombre de
  autor** en `docProps/core.xml` (`dc:creator` y `lastModifiedBy`) — clase:
  nombre de la persona redactora. No se reproduce.
- **Firmas institucionales** (no personales).

## 8. Revisión del corpus del 30/09 versionado en `Adjuntos/imagenes-flat-finch/`

Criterio: mismo que §7 (repo público; ante la duda, no exponer el dato). El
directorio contiene 9 archivos, todos dentro del repo y de su historia.

| Archivo | Qué es | Veredicto |
|---|---|---|
| `node133-backup.json` (11,9 MB) | **dump crudo de una sesión del asistente**: `message_id`, metadatos de la petición, el texto del mensaje y las 7 imágenes en base64. Reproduce un **teléfono móvil personal** y un enlace de casilla | **Sacar del repo (y de la historia).** No tiene valor analítico — duplica las 7 imágenes — y filtra metadatos de la sesión |
| `mensaje-original.md` (5,8 KB) | el mismo texto del mensaje, con **teléfono móvil personal** y enlace de adjunto de la casilla | **Sacar del repo, o sanear** (quitar teléfono y enlace). Si se conserva el mapeo imagen→pieza, sin esos datos |
| `img-1790777571539674121.png` (flyer «Día del estudiante») | flyer público con un **teléfono móvil personal** impreso | **Sacar o recortar** (el teléfono es dato personal) |
| `img-1790777939890855976.png` (foto «Día del Estudiante», IG) | **fotografía de personas identificables** (alumnos) | **Sacar.** Derecho de imagen de terceros; posibles menores |
| `img-1790777382703146694.png` y `img-1790777393756023762.png` (flyer IA NotebookLM N2), `img-1790777464537990578.png` (flyer mesas de exámenes), `img-1790777909619840211.png` (IG puertas abiertas), `img-1790778116369244602.png` (IG Episodio 13) | flyers / material institucional **público**, sin datos personales sensibles | No exponen PII; pero son **~11 MB de binarios** en un repo de documentos y su contenido ya está descrito en `Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md`. Recomendado: **moverlos a la carpeta local** fuera de git; si se conservan, sin cambios |

**Historia.** Todo el directorio entró a `main` en el merge **`2d991c8`**
(2026-10-12) y sigue en el historial de `main` (y en las ramas que lo
contienen). Sacarlo del *working tree* **no** purga la historia: el dump de
sesión, el teléfono y la foto de alumnos quedan en los commits de esa línea.
Quitarlos de la historia exige `git filter-repo` + force-push → **HITL**,
fuera del alcance de esta tarea AFK.

**Acción tomada en esta tarea.** Sólo el **veredicto escrito** (esta §8). No se
borró, movió ni reescribió nada del directorio.

**Purga ejecutada (2026-10-14, decisión de Juani).** Con `git filter-repo
--invert-paths` sobre todo el repositorio se sacaron de la historia los cuatro
archivos marcados arriba: `node133-backup.json`, `mensaje-original.md`,
`img-1790777571539674121.png` e `img-1790777939890855976.png`. Los cinco
flyers institucionales públicos quedaron. La purga reescribió los SHA de toda
la línea de `main` y **también borró las copias del working tree**: los cuatro
archivos ya no existen ni en el repo ni en el disco. La PII **nunca se había
publicado**: el `main` del remoto estaba 194 commits atrás y no contenía el
merge `2d991c8`. Queda pendiente el `force-push` para publicar la historia ya
limpia, y el guardado de los SHA nuevos en el log de estado.

**Revisión del documento vecino.** `Documentos/PoC/Corpus-Comunicaciones-Reales-SEU-2026-09-30.md`
se revisó con el mismo criterio: **no** incluye el teléfono móvil personal y
sólo cita correos institucionales de área. Veredicto: apto como está.

## 9. Uso y límites

- Este análisis **alimenta** el set de evaluación (#104) y el renderer (#107).
  No reemplaza la transcripción de cada flyer: eso es trabajo de #104.
- No reproduce datos personales; los originales están fuera del repo.
- Toda decisión de custodia sigue ADR 0007 (no depender del autor): los
  originales migran a la unidad compartida del agente cuando exista (#100).

### Supuestos (elegidos por ser la opción más conservadora)

1. **Denominador del corpus.** El «44» de #102 no se reprodujo por hash exacto
   (43) ni por pieza lógica (41). Se documentan los tres números y se deja que
   #104 fije el denominador.
2. **Ruta local.** Se propone y se crea (por **copia**, sin mover el original)
   `/home/spendice/Documents/P100-Corpus-FIE-Informa/`, fuera de todo repo git.
3. **Transcripción de flyers parcial:** sólo los flyers verificados; el resto,
   para #104.
4. **Nombres de expositores omitidos** en las transcripciones, aun cuando el
   flyer es público, por el criterio «ante la duda, no incluir el dato».
5. **Historial del 30/09:** se deja el veredicto; la purga de historia queda
   como tarea HITL separada (requiere force-push, no permitido acá).

### Bloqueantes

- Ninguno técnico. La purga de historia (§8) y la migración a la unidad
  compartida (#100) dependen de terceros y son HITL.

## Anexo — Esqueletos por tipo (extractos, sin datos personales)

Plantillas del **esqueleto real** de cada tipo, con los datos reemplazados por
marcadores. No incluyen nombres, teléfonos, enlaces ni metadatos. Sirven de
andamiaje para el set de evaluación (#104) y el renderer (#107).

**Difusión de curso/diplomatura** (cuerpo mínimo; datos en el flyer):

```
<Título del curso o diplomatura>

[flyer adjunto]

Ins/Inscripción

Consultas
<cursos@fie.undef.edu.ar>

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria
```

**Aviso de otra área:**

```
Se informa a la comunidad <educativa|...> que <hecho>, a partir del <fecha>,
<condición>.

Muchas gracias
<Área emisora>
```

**Crónica de evento («Noticias FIE»):**

```
<NOTICIAS FIE>
<Título>

<Párrafo(s) corrido(s): qué se hizo, dónde, cuándo y quiénes participaron — con
los nombres y cargos como datos variables.>
```

**Pronóstico PRODE:**

```
<Título de la instancia>

Ingresá al enlace y pronosticá <...>.
<enlace al formulario>

IMPORTANTE: <condición, p. ej. usar el correo institucional (dato variable)>
```

**Saludo / efeméride:**

```
<Título>

<1–2 frases de saludo institucional>
```

**Fallecimiento** (la propia pieza existe como plantilla con huecos en el
corpus):

```
Informar fallecimiento
Con profundo pesar informamos el fallecimiento de <nombre>, quien fuera <rol>.

El <día> se realizará un responso a las <hora> en <lugar>.

Acompañamos a su familia en este doloroso momento y elevamos nuestras plegarias
por su eterno descanso.
```

**Newsletter:**

```
<Título del boletín>

Link archivo adjunto:
<enlace al adjunto — enlace interno de casilla: no reproducir; se reemplaza por
el destino declarado>
```
