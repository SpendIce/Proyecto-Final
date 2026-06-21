# Guion de Video — Agente 1 (Extensión Bot)

**Uso:** pieza rápida para enviar a la SEU / Secretario de Extensión (teaser asíncrono).
**No reemplaza** la defensa oral en vivo ante el profesor de PPS — la complementa.
**Duración objetivo:** ~1 min 45 s (105 s).
**Track visual:** el mismo deck `pitch-agente1.html` en modo autoplay (15 escenas, sincronizadas).
**Track de audio:** la narración de abajo, una línea por escena.

> Lineamientos idénticos a la presentación: arco dolor → solución → control humano → viabilidad → pedido.
> Registro de la narración: institucional, claro, ritmo ágil. Frases cortas. Una idea por escena.

---

## Tabla de escenas (narración 1:1 con las slides)

| # | Slide | Dur | Narración (voz en off) |
|---|-------|-----|------------------------|
| 1 | Portada | 5 s | "Agente 1, Extensión Bot: el agente de comunicación institucional de la Secretaría de Extensión de la FIE." |
| 2 | El Centenario | 6 s | "La FIE llega a sus cien años con nueve procesos de extensión gestionados, todavía, a mano." |
| 3 | El problema | 7 s | "Hoy cada gacetilla, cada post, cada correo se escribe desde cero. Sin plantillas, sin integración, sin registro." |
| 4 | El costo | 7 s | "Más de treinta minutos por pieza. Cuellos de botella, mensaje inconsistente y sin trazabilidad para CONEAU." |
| 5 | La solución | 7 s | "Extensión Bot genera ese contenido automáticamente. Y siempre con validación humana antes de publicar." |
| 6 | Qué hace | 8 s | "Gacetillas, posts adaptados a cada red, newsletters, mails, confirmaciones de inscripción y certificados." |
| 7 | Qué NO hace | 7 s | "No es chatbot público, no hace scraping ni analítica. Un alcance acotado es un proyecto que se entrega." |
| 8 | Cómo funciona | 8 s | "Entra un dato, el agente genera un borrador, un responsable lo aprueba, recién ahí se publica. El humano, siempre en el centro." |
| 9 | Demo | 9 s | "De datos sueltos en una planilla, a una gacetilla institucional lista para revisar. De media hora, a segundos." |
| 10 | Stack | 7 s | "Todo software libre, modelos que corren localmente. Costo de licencias cero, y los datos nunca salen de la FIE." |
| 11 | Alcance y TRL | 7 s | "Maduración por niveles: de un prototipo funcional a la integración total con los cinco agentes del Proyecto Centenario." |
| 12 | Backlog | 6 s | "No es una idea suelta: es un backlog priorizado, con metodología Scrum." |
| 13 | Riesgos | 6 s | "Los riesgos están previstos: validación humana obligatoria, ajuste de modelos y participación temprana del personal." |
| 14 | Métricas | 7 s | "Y se mide: menos de treinta segundos por pieza, noventa y nueve por ciento de disponibilidad, trazabilidad completa." |
| 15 | Cierre | 8 s | "Extensión Bot: la comunicación de la Secretaría de Extensión, automatizada y bajo control humano." |

**Total: 105 s (~1:45).**

---

## Versión ultra-corta (60 s · si necesitás un teaser de redes)

Fusionar y recortar a 8 escenas. Narración:

1. (Portada) "Agente 1, Extensión Bot — la comunicación de la SEU, automatizada."
2. (Problema + costo) "Hoy, más de media hora por cada gacetilla, post o correo. A mano, sin registro."
3. (Solución) "Extensión Bot lo genera automáticamente, siempre con validación humana."
4. (Qué hace) "Gacetillas, posts, newsletters, confirmaciones, certificados."
5. (Control humano) "El agente propone; el responsable de la SEU aprueba. Nunca publica solo."
6. (Soberanía) "Software libre, modelos locales: costo cero y los datos no salen de la FIE."
7. (Métricas) "Menos de treinta segundos por pieza, con trazabilidad para CONEAU."
8. (Cierre) "Extensión Bot. Comunicación institucional, bajo control humano."

---

## Cómo producir el video (camino recomendado)

### Opción A — Grabar el deck en autoplay + voz (recomendada)
La más rápida, gratis y coherente con la soberanía de datos del proyecto. Reusa el deck que ya existe.

1. Grabá primero la **narración** sola (audio) leyendo la tabla de escenas. Cronometro: respetá los segundos por escena. Herramienta: cualquier grabador (Audacity, o el grabador del celular).
2. Abrí el deck en pantalla completa y dispará el autoplay:
   ```
   # abrir directamente en modo reproducción
   xdg-open "pitch-agente1.html?play"
   ```
   - O abrir normal y apretar **F** (pantalla completa) y luego **P** (play).
   - En modo play el deck oculta toda la interfaz (flechas, puntos, contador) y avanza solo con los tiempos de la tabla. Esc o un clic lo cortan.
3. Grabá la pantalla con **OBS Studio** (gratis, multiplataforma) mientras corre el autoplay.
4. Uní video + audio en cualquier editor (CapCut, DaVinci Resolve, Kdenlive). Ajustá si alguna escena necesita medio segundo más.
5. Música de fondo opcional: instrumental sobrio, volumen bajo (-20 dB respecto a la voz).

> Si los tiempos no te cierran con tu ritmo de lectura, editá el array `durations` en `pitch-agente1.html` (está comentado al final del `<script>`).

### Opción B — Voz sintética (sin grabar tu voz)
Si no querés poner la voz: generá el audio con TTS (ElevenLabs, o Edge/Google TTS) a partir de la narración, y seguí desde el paso 3 de la Opción A.

### Opción C — Avatar / video con IA
Herramientas tipo HeyGen o Synthesia: pegás la narración, generan video con avatar y voz. Más "producido", pero sale de la infraestructura local (los datos van a un servicio externo — ojo con el mensaje de soberanía si lo mostrás a la SEU).

### Opción D — Export nativo de Gamma
Si además armás el deck en Gamma (ver `guion-pitch-agente1.md`), Gamma permite presentar/exportar con narración. Menos control fino que OBS, pero todo en un lugar.

---

## Tips de producción

- **Primeros 5 segundos = todo.** Si no enganchás en la portada + problema, el cliente cierra. Arrancá fuerte.
- **Voz > imagen.** El deck ya es sobrio; que la narración tenga energía contenida, no monótona.
- **No leas la pantalla.** La voz aporta lo que el texto NO dice. Redundancia = aburrimiento.
- **Subtítulos:** agregalos. Mucha gente mira sin audio (celular, oficina). CapCut los autogenera.
- **Cierre con CTA claro:** que el último frame invite a una reunión o respuesta. El video abre la puerta; vos cerrás el trato.
- **Formato de salida:** 1920×1080, MP4 H.264, para mandar por mail o WhatsApp sin que pese de más.
