# Solicitud de activos y reglas de formato para la nota institucional de gacetilla

- **Fecha:** 2026-08-26
- **Proceso BPM:** P4 — Comunicación y Difusión Institucional
- **HU:** HU-010
- **Defecto asociado:** `DEF-A1-002` (`BLOQUEADO_EXTERNO`)
- **Anexo de:** `Nota-Solicitud-SEU-Agente-1-PPS-Juan-Ignacio-Gone.md`, punto 4.2
- **Dirigido a:** Departamento de Comunicación de la SEU, con conocimiento del Oficial de Comunicación Institucional
- **Estado del pedido:** `PENDIENTE_DE_RESPUESTA`

## 1. Objeto

La SEU informó que **no existe una plantilla oficial de gacetilla** y que, para
una publicación elevada a DGE/SGE, se prepara una nota institucional con logos
institucionales en la parte superior, texto e imágenes correspondientes,
respetando las características de la gacetilla.

Con esa definición se versionó una especificación candidata
(`Especificacion-Gacetilla-Nota-Institucional-v1.md`). Esa especificación
describe un contenedor y su circuito de validación, pero **no puede producir una
pieza utilizable**: le faltan los activos autorizados y las reglas de uso. Este
anexo pide exactamente eso, desagregado, para que la respuesta pueda ser parcial
y aun así útil.

El punto 4.2 de la nota pedía «la plantilla oficial». Como la SEU ya respondió
que no existe, este anexo lo reemplaza por un pedido de insumos para
construirla.

## 2. Qué se pide

### 2.1 Bloque A — Activos gráficos autorizados

| # | Activo o dato | Por qué es necesario |
|---|---|---|
| A.1 | Archivos de los logos institucionales autorizados para este uso, preferentemente vectoriales (`.svg` o `.pdf`) y, en su defecto, `PNG` con fondo transparente en alta resolución | Sin el archivo autorizado, cualquier logo que se use es una reproducción no verificada |
| A.2 | Qué logos corresponden y en qué orden cuando aparece más de uno (por ejemplo Facultad, UNDEF, Ejército, coorganizadores) | El orden y la jerarquía institucional no se pueden inferir sin riesgo |
| A.3 | Versiones admitidas: color, monocromo, positivo y negativo | Determina qué se puede usar sobre fondos claros u oscuros |
| A.4 | Área de resguardo, tamaño mínimo y proporciones que deben respetarse | Es la regla que hace verificable la franja superior de la pieza |
| A.5 | Usos prohibidos: deformación, recorte, cambio de color, aplicación sobre imagen | Permite convertir la prohibición en control automático |
| A.6 | Quién autoriza el uso de estos activos y con qué alcance | Es la referencia de aprobación que la pieza debe poder citar |
| A.7 | Manual de identidad visual, si existe, aunque sea parcial o interno | Si existe, reemplaza a A.2–A.5 con una fuente única |

### 2.2 Bloque B — Dos ejemplos sanitizados

Se solicitan **dos notas institucionales realmente elevadas a DGE/SGE**, con los
datos personales y toda información sensible removidos o reemplazados por
valores ficticios.

| # | Característica pedida | Motivo |
|---|---|---|
| B.1 | Dos ejemplos, no uno | Con un solo ejemplo no se puede distinguir qué es estructura fija y qué es particular de esa actividad |
| B.2 | Preferentemente de tipos de actividad distintos (por ejemplo un curso y un evento) | Permite detectar si hace falta más de una plantilla |
| B.3 | En su formato original (`.docx`, `.odt` o `.pdf`), no una captura de pantalla | El formato original conserva estilos, márgenes y orden de campos |
| B.4 | Sin datos personales reales | El proyecto trabaja íntegramente con datos sintéticos y no incorpora datos reales a su evidencia |

Si por algún motivo no fuera posible entregar ejemplos, alcanza con un
instructivo o descripción escrita de la estructura: es menos preciso, pero
permite avanzar.

### 2.3 Bloque C — Reglas de formato

| # | Regla | Estado actual en la especificación |
|---|---|---|
| C.1 | Tipografía y cuerpos para título, subtítulo y texto | `PENDIENTE_DE_CO_DISENO` |
| C.2 | Márgenes, interlineado y disposición general | `PENDIENTE_DE_CO_DISENO` |
| C.3 | Contenido y ubicación del encabezado y del pie | `PENDIENTE_DE_CO_DISENO` |
| C.4 | Orden de los campos del cuerpo y cuáles son obligatorios | Definido sólo de forma provisional por el equipo técnico |
| C.5 | Cantidad, ubicación y tamaño de las imágenes, y quién provee esas imágenes | `PENDIENTE_DE_CO_DISENO` |
| C.6 | Firma, cargo y datos de contacto que deben figurar | Sin definición |
| C.7 | Formato y vía de elevación a DGE/SGE (archivo, papel, correo, sistema) | Sin definición |
| C.8 | Si existe más de una plantilla según el tipo de actividad | Sin definición (también consultado en el punto 4.2 de la nota) |

## 3. Uso previsto y límites que se mantienen

Sobre lo que se reciba, A1 hará únicamente esto:

- Derivar reglas de formato verificables y una plantilla de borrador.
- Referenciar los activos de forma controlada, por identificador y hash.
- Producir piezas que conserven `BORRADOR — NO PUBLICAR` y
  `PENDIENTE_VALIDACION` hasta que exista decisión humana registrada.

Y explícitamente **no** hará esto:

- No publicará ni elevará ninguna pieza por sí mismo.
- No versionará los activos gráficos ni los ejemplos dentro del repositorio del
  proyecto: quedarán en el recurso institucional que la SEU indique, referidos
  por identificador.
- No reproducirá identidad institucional en material de prueba: las nueve
  muestras de validación seguirán siendo sintéticas y sin marca.

## 4. Modalidad de entrega sugerida

Se propone una carpeta institucional en el Workspace de la Facultad con permiso
de lectura para el responsable técnico del PPS, o bien envío por correo
institucional. La elección corresponde a la SEU y a la DSI; en ambos casos el
proyecto registrará únicamente la referencia y el hash del material, no una
copia.

## 5. Criterio de aceptación

La especificación pasa de `CANDIDATA_PARA_CO_DISENO_SEU` a plantilla
implementable cuando se cuente, como mínimo, con:

1. Los archivos de logos autorizados (A.1) y quién autoriza su uso (A.6).
2. Un ejemplo sanitizado (B.1 parcial) o, en su defecto, el instructivo del
   punto 2.2.
3. El orden de campos obligatorios (C.4) y el contenido de encabezado y pie
   (C.3).

Con eso `DEF-A1-002` puede pasar de `BLOQUEADO_EXTERNO` a `EN_CORRECCION`. Aun
así permanecerá abierto hasta contar con la prueba recuperable de la pieza
generada sobre el recurso institucional configurado, que además depende de
`DEF-A1-001` (Workspace y OAuth).

## 6. Plazo y efecto sobre el cronograma

Se solicita respuesta, aun parcial, antes del **11 de septiembre de 2026**, de
modo de no comprometer el hito **m4** del 14 de septiembre. Se deja constancia
de que la fecha constituye una solicitud y no una fecha acordada.

Si al vencimiento no hubiera respuesta, HU-010 continuará operando con la
especificación candidata y sin activos institucionales, y esa limitación se
informará como tal en la evidencia del gate: no se sustituirán los activos
faltantes por aproximaciones propias.
