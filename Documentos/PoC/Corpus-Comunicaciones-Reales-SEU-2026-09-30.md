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

1. **La repregunta no conservaba el canal del pedido original — corregido
   el 05/10.** «Post de linkedin para la jornada» → repregunta por
   actividad → responder «la 1» resolvía la actividad pero el pipeline
   re-leía el canal del texto del turno nuevo → `INCOMPLETA`. Ahora
   `InteraccionPendiente` conserva además el `canal` ya resuelto (sigue sin
   guardar prosa): el canal nombrado en el turno de respuesta gana si está
   («la 1, para linkedin» corrige un pedido de instagram); si el pedido
   original nunca resolvió canal, el despacho sigue dando `INCOMPLETA` —
   no hay default silencioso. Verificado end-to-end en el prototipo:
   repregunta → «la 1» → `PENDIENTE_VALIDACION` con el post linkedin de la
   actividad elegida.
2. **Responder la repregunta era más frágil de lo documentado — corregido
   el 30/09.** `_referencia_por_rasgo` exigía un rasgo presente en una sola
   candidata: cualquier token compartido («sintética», «agosto», «2026»)
   envenenaba la resolución aunque otro token fuera perfectamente
   discriminatorio. Fallaban el título («la jornada sintética»), la fecha
   ISO («2026-08-07») y la fecha en letras («la del 7 de agosto») — tres
   respuestas naturales, incluida la que la repregunta sugiere. Reescrita
   como intersección con dominancia estricta: gana la candidata con más
   rasgos en común sólo si la ventaja es única; el empate sigue sin
   resolver.
3. El demo anterior devolvía siempre el golden SYN-001 → **toda gacetilla
   de otra actividad salía `FALLIDA`** (los hechos no coinciden con la
   fuente). Corregido: `GeneradorDemo` arma la ficha desde el bloque
   `DATOS FUENTE` del prompt.
4. El contrato creativo vigente del pipeline (`post_creative_output_v2` +
   catálogo) usa **catálogo cerrado** por campo: el modelo elige entre
   opciones fijas de gancho/prosa/cta por canal. Esa es la causa profunda
   de la «simplicidad» del demo — no es el LLM, es el catálogo. Resuelto
   el mismo día: catálogo enriquecido a `post_creative_catalog_v4` (ver §4).
5. Gates que sí se comportaron como se esperaba: rechazo fuera de alcance
   (newsletter), `INCOMPLETA` por canal ausente en el pedido inicial,
   `INCOMPLETA` por contacto faltante (SYN-002), id explícito SYN-001.
6. **«En la FIE» dispara el gate de lugares.** El eslogan literal «Si es
   ingeniería, es en la FIE» fue rechazado por `unauthorized_place`
   (`PATRON_LUGAR_PROPIO` lee «en la + NombrePropio» como lugar inventado).
   Solución adoptada sin tocar el gate: variante «¡Si es ingeniería, la FIE
   te espera!» que conserva el cierre real sin el patrón. Si la SEU quiere
   el eslogan literal, habría que revisar el gate — decisión institucional.

## 4. Uso del corpus — estado

- **Catálogo creativo (implementado 30/09):** `post_creative_catalog_v4` en
  `post_creative_output_v2.schema.json` agrega opciones inspiradas en el
  corpus real — ganchos «¡La FIE te espera con una nueva propuesta!» /
  «Se acerca una nueva propuesta para la comunidad.», prosa con
  «…proyectar tu futuro junto a docentes y estudiantes» y la variante del
  eslogan «¡Si es ingeniería, la FIE te espera!», CTAs «La FIE te espera.
  El enlace está en nuestro perfil.». Diseño: los `!` quedaron sólo en
  gancho/prosa (ningún cta) para que ninguna combinación supere el tope
  interno de 2 exclamaciones. Verificación exhaustiva: las 80+48
  combinaciones posibles pasan todos los gates del pipeline.
- **Borrador mail durable (implementado 30/09, reemplaza a la vista
  ilustrativa):** el pipeline de gacetilla adoptó el mismo patrón que los
  posts — el modelo produce una ficha validada (título, hechos, contacto,
  bajada, cuerpo) y un renderer determinista
  (`gacetilla_mail_renderer_v1`, `PROMPT_VERSION = gacetilla_v5`) arma el
  correo en forma FIE Informa: `Asunto:`, línea de invitación institucional
  con el público, bajada y cuerpo del modelo, `📅` con la fecha en formato
  largo, `🕒` opcional, `Organiza:`/`Lugar:`/`Inscripción:`/`Consultas:`
  desde la fila, y la firma institucional completa del corpus. **El
  artefacto durable auditado es el mail**, no la ficha; el control
  posterior (`_validar_render_mail`) verifica que ningún hecho de la fila
  se haya perdido en el render. Los topes de prosa quedaron calibrados
  contra este corpus (bajada ≤ 40 palabras, cuerpo ≤ 120, varias oraciones
  permitidas) en lugar del techo arbitrario de 12; y la prosa no puede
  contener números, correos, enlaces ni montos — esos datos los pone el
  renderer desde la fuente (`unauthorized_fact_in_prose`). `hora` y
  `enlace` se renderizan sólo si la fuente los trae: agregarlos al CSV es
  una decisión institucional pendiente (`COLUMNAS_GACETILLA` es el contrato
  de entrada vigente).
- **Descripción de la actividad en el post (implementado 30/09, renderer
  `post_deterministic_renderer_v4`):** observación de ensayo — el post IG
  «no decía nada de la actividad» porque los campos creativos son genéricos
  por contrato y la `descripcion` nunca llegaba a la pieza. El renderer
  ahora inserta la descripción de la fuente como párrafo entre la prosa
  creativa y el bloque de hechos, colapsada a una línea para no inyectar
  saltos en la estructura. No es prosa del modelo: es el dato institucional
  copiado, como `Título:`/`Fecha:`. Pendiente editorial: si la SEU quiere
  prosa creativa que describa la actividad (como I1: «podrás conocer la
  oferta académica, explorar los laboratorios y participar en charlas»), el
  contrato creativo tendría que admitir un campo de prosa anclada a la
  fuente — hoy los campos creativos no pueden mencionar la actividad.
- **Casos del instrumento (actualizado 30/09):** las consignas C1–C4 del
  instrumento de prueba guiada se reformularon con prosa natural del
  dominio («Necesito avisar de la actividad…», «Tenemos que avisar… en
  LinkedIn») y la nota de C3 documenta las dos limitaciones observadas.
- **Pendiente:** las preguntas para SEU siguen abiertas: ¿hashtags
  temáticos libres o set cerrado? ¿CTA puede decir «inscripción»? ¿el dato
  va dentro de la prosa o adjunto por sistema? ¿eslogan literal («en la
  FIE») permitido o la variante alcanza? ¿agregar `hora` y `enlace` al
  contrato de entrada? ¿prosa creativa anclada a la descripción de la
  actividad, o alcanza con el párrafo literal del renderer?
