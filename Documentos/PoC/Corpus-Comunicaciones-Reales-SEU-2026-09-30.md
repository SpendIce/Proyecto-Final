# Corpus de comunicaciones reales SEU — gacetillas FIE Informa y posts IG

- **Fecha de relevamiento:** 2026-09-30
- **Proveniencia:** aportadas por J. I. Goñe, copiadas desde la casilla real
  `notificaciones@fie.undef.edu.ar` (FIE Informa, bcc `alumnosingenieria`) y
  del Instagram institucional de la FIE. Texto + 7 capturas en
  `Adjuntos/imagenes-flat-finch/` (mapeo imagen→pieza en
  `mensaje-original.md` de esa carpeta).
- **Estatus:** corpus de trabajo **informal**. No son los «ejemplos
  aprobados» que la SEU tiene pendientes desde el acta del 22/09; sí son
  evidencia real del formato vigente y alcanzan para calibrar la base de
  generación. Si la SEU los valida, pueden promover a ese rol.

## 1. Piezas relevadas

### Gacetillas (correo FIE Informa)

| # | Asunto | Forma | Rasgos |
|---|--------|-------|--------|
| G1 | «Últimos días de inscripción - Inteligencia Artificial aplicada a la educación y gestión NotebookLM - Nivel 2» | Cuerpo = 2 flyers adjuntos (PNG) + una línea («inscripción») + consultas | Asunto con gancho temporal + título completo del curso; la info viaja en la imagen; firma del Departamento de Cursos Complementarios + SEU antes de la firma institucional |
| G2 | «RECORDATORIO: Pedido de MESAS DE EXÁMENES» | Cuerpo = 1 imagen documento (instructivo SIU-Guaraní) | Prefijo «RECORDATORIO:» en asunto; sin texto propio; firma institucional duplicada en el reenvío |
| G3 | «VISITA AL NUEVO MUSEO DE GRANADEROS» | Texto completo sin imagen | Bajada emocional → invitación institucional → fecha/hora con emojis (📅 🕒) → descripción → «¿QUERÉS PARTICIPAR?» + «INSCRIBITE COMPLETANDO EL GOOGLE FORM» + URL → cupos/duración → nota de conducta → firma |
| G4 | «Día del estudiante FIE» | Flyer adjunto + texto completo | «Cuando:/Hora:/Dónde:/Menú:» + link de inscripción + link de pago ($5.000) + «Podés traer…» + «¡¡Habrá premios!!» + Consultas con mail y teléfono |

**Firma institucional constante en las 4:**
`Facultad de Ingeniería del Ejército / "Grl Div Manuel N Savio" / UNDEF /
Tel: (011) 4779-3300 / Av. Cabildo 15 – CABA / www.fie.undef.edu.ar`

**Canal de consulta observado:** `cursos@fie.undef.edu.ar` (cursos),
`comunicacion@fie.undef.edu.ar` (+ teléfono) (comunicación general).

### Posts de Instagram

| # | Pieza | Rasgos |
|---|-------|--------|
| I1 | Auspicio CPIC en Jornada de puertas abiertas («Ingeniería por un día 2026») | Gancho de agradecimiento + mención `@cpicorg` → fecha/hora/lugar **dentro de la prosa** → propuesta de valor → eslogan «¡SI ES INGENIERÍA, ES EN LA FIE!» → CTA «Link de inscripción en la Bio "Actividades de Extensión"» → «Consultas comunicacion@fie.undef.edu.ar» → cierre «¡La FIE te espera!». Sin hashtags en el texto |
| I2 | «¡La FIE les desea un felíz día del estudiante!» | Sólo gancho + imagen. Mínimo viable |
| I3 | Episodio 13 de «Con Voz Propia» (radio, camino a los 100 años) | Emoji de gancho 🎬 → «Reviví… ahora mismo» → «Link de canal en nuestro perfil» → 📢 grilla de horarios de FM → 🔔 «¡Suscribite al canal, activa la campanita!» → hashtags temáticos `#radio #FIE #vozpropia #protagonistas` |

**Notas de estilo observadas (para no idealizar el corpus):** los reales
tienen errores («felíz», «16:00h,en», mezcla de tuteo «activa la
campanita»). El registro base es voseo entusiasta con MAYÚSCULAS en los
llamados; el agente debe copiar el registro, no los errores.

## 2. Brechas contra los contratos vigentes del Agente 1

| Rasgo real observado | Contrato/política vigente | Brecha |
|---|---|---|
| Fecha/hora/lugar **dentro de la prosa** del post (I1, I3) | `post_creative_output_*` prohíbe datos en `gancho/prosa/cta`; el renderer los agrega aparte como líneas `Título:/Fecha:` | El formato real integra hechos; el contrato los separa a propósito (exactitud garantizada por el sistema). Diseño deliberado: **decisión a confirmar con SEU** |
| Hashtags temáticos libres (`#radio`, `#vozpropia`, `#protagonistas`) | Allowlist cerrada provisional: `#FIE #UNDEF #Ingenieria #Cursos #inscripciones` | La política provisional no admite hashtags de contenido. **Pregunta abierta SEU** |
| Eslogan fijo «¡SI ES INGENIERÍA, ES EN LA FIE!» y cierre «¡La FIE te espera!» | No contemplados en contrato ni política | Candidato a elemento fijo del renderer (determinístico, sin LLM) |
| CTA real: «Link de inscripción en la Bio "Actividades de Extensión"» | CTA vigente remite al «enlace del perfil»; la palabra **inscripción** está prohibida en campos creativos (`unauthorized_fact_claim`) | Mismo sentido, otra literalidad: SEU escribe «inscripción» en el CTA real. **Pregunta abierta SEU** |
| Emojis en posts: I3 usa 3 (🎬📢🔔); I1/I2 usan 0 | Tope interno 2 («emojis casi nunca» confirmado 22/09) | Consistente en promedio; el caso rico supera el tope. Suficiente como está |
| Gacetilla = mail con asunto-gancho, invitación, CTA de inscripción, consultas y firma institucional completa | `gacetilla_v4` produce ficha técnica de 5 secciones (`## TÍTULO` … `## CUERPO`), bajada ≤ 12 palabras, cuerpo 1 oración | El artefacto PoC es la **ficha**, no el mail. La forma mail real requeriría una plantilla v5 o un paso de **ensamblado determinista** (ficha → mail con firma/consultas/CTA) que hoy no existe |
| Remitente `FIE Informa`, bcc `alumnosingenieria` | Fuera del alcance del PoC (no se envía nada) | Registrar para la etapa de integración |

## 3. Hallazgos del ensayo del prototipo (2026-09-30, modo simulado)

Hechos verificados contra `Implementacion/Agente1/scripts/prototipo_hu013.py`
y el núcleo `interpretacion.py`:

1. **La repregunta no conserva el canal del pedido original.** «Post de
   linkedin para la jornada» → repregunta por actividad (correcto) →
   responder «la 1» resuelve la actividad pero el pipeline re-lee el canal
   del texto del turno nuevo → `INCOMPLETA «No se reconoció un canal»`.
   `InteraccionPendiente` guarda intención + candidatas, no los parámetros ya
   resueltos. Impacta directamente los casos C3+C4 del instrumento de
   prueba guiada. **Defecto candidato** (registrar en
   `Registro-Defectos-Agente-1.md` si se confirma que la spec espera
   conservarlo).
2. **Responder la repregunta con el título completo puede no resolver.**
   «la jornada sintética» no resolvió: `_referencia_por_rasgo` exige rasgo
   que aparezca en una sola candidata, y «sintética» está en todas las
   actividades del dataset → 5 coincidencias → `RECHAZADA`. Con «la
   jornada» sí resuelve. Limitación amplificada por el dataset sintético
   (todas comparten el apellido «sintética»); con títulos reales el rasgo
   funciona. Conviene aclararlo en el instrumento o quien conduce lo va a
   leer como rechazo arbitrario.
3. El demo anterior devolvía siempre el golden SYN-001 → **toda gacetilla
   de otra actividad salía `FALLIDA`** (los hechos no coinciden con la
   fuente). Corregido: `GeneradorDemo` arma la ficha desde el bloque
   `DATOS FUENTE` del prompt.
4. El contrato creativo vigente del pipeline (`post_creative_output_v2` +
   catálogo v3) usa **catálogo cerrado** por campo: el modelo elige entre 2
   opciones fijas de gancho/prosa/cta por canal. Esa es la causa profunda
   de la «simplicidad» del demo — no es el LLM, es el catálogo.
5. Gates que sí se comportaron como se esperaba: rechazo fuera de alcance
   (newsletter), `INCOMPLETA` por canal ausente en el pedido inicial,
   `INCOMPLETA` por contacto faltante (SYN-002), id explícito SYN-001.

## 4. Uso propuesto del corpus

- **Corto plazo (esta semana):** enriquecer el catálogo creativo v3 con
  opciones inspiradas en el corpus real (eslogan FIE, cierre «¡La FIE te
  espera!», ganchos con mención/auspicio) — es data del contrato, no código
  nuevo. Requiere decisión: el catálogo es `x-provisional-*`, diseñado para
  esto.
- **Mediano:** evaluar `gacetilla_v5` con forma mail real (asunto + bajada
  emocional + invitación + fecha destacada + CTA inscripción + consultas +
  firma) o, más seguro, un **renderer mail determinista** que envuelva la
  ficha v4 con firma/consultas/CTA — mantiene el gate de hechos intacto y
  produce la pieza que SEU reconoce.
- **Preguntas para SEU** (cuando haya canal): ¿hashtags temáticos libres o
  set cerrado? ¿CTA puede decir «inscripción»? ¿el dato va dentro de la
  prosa o adjunto por sistema? ¿eslogan y firma fijos oficiales?
