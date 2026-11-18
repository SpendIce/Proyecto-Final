// Fuente de verdad del AVANCE del cronograma de implementacion (Agente 1).
// La fuente de verdad del PLAN (fechas, tareas, hitos) sigue siendo
// diagrama-gantt-implementacion-semanal.mmd. Este archivo solo registra que
// tareas estan hechas.
//
// Formato: un objeto por tarea/hito, indexado por el ID que usa el .mmd
// (s0a, s0b, ..., m0, s1a, ..., m8). Cada entrada:
//   {
//     done: true,              // obligatorio si la tarea esta hecha
//     at:   "YYYY-MM-DD",      // fecha en que se completo
//     nota: "texto opcional"   // evidencia, link, comentario corto
//   }
//
// Se puede marcar una tarea como completada editando este archivo
// directamente (a mano o delegado a un agente): agregar/actualizar la
// entrada correspondiente al ID de la tarea con done:true y la fecha.
// No hace falta tocar el HTML ni el .mmd para esto.
//
// El visor (visor-gantt-implementacion-semanal.html) carga este archivo al
// abrir la pagina. Los cambios hechos desde el navegador (tildar checkboxes)
// se guardan en localStorage al toque; para que se reflejen en otro
// navegador o para un agente que lea el repo hay que usar el boton
// "Guardar progreso" del visor, que reescribe este mismo archivo.

window.GANTT_PROGRESS = {
  // Corte 18/11 (día de la presentación de cursada). Contrastado contra
  // origin/main (agente1-v0.11.1, a27cfdf), CHANGELOG 0.6.0-0.11.1, issues
  // #57, #125, #126, #149, #151, #153, #168, #177 y #193, la evidencia del
  // servidor en PR #178 y el despliegue de 0.11.1 verificado en labredesfie.
  // No se marca ninguna tarea nueva: el canal web y los certificados en la web
  // avanzan m5 y m6, pero ninguno cumple su DoD completo (ver notas).
  "m5": {"done": false, "nota": "17/11: canal web de A1 implementado y desplegado en labredesfie (0.6.0-0.9.0, Tailscale): bandeja, pedido guiado de 7 tipos de pieza, Doc real en Drive, «Traer cambios», ajuste generativo sobre la última revisión, aprobar/descartar atado al hash y «Preparar correo» en Gmail sin envío. Persistencia en PostgreSQL con worker y auditoría (#151, ADR 0016). E2E en el servidor el 17/11: generación 43,8 s y ajuste 57,7 s (PR #178). Usabilidad del prototipo aceptada por la SEU el 04/11 (s5d). Falta para el DoD: login Google institucional (DSI, #62/#149; hoy modo demostración sin verificar identidad, vence el 20/11) y padrón real de la SEU (provisorio; desde 0.10.4 admite varios roles por persona, #125). 18/11: interfaz pulida en 0.11.1 (resumen y pestañas en la bandeja, estados con color, detalles técnicos plegados) y «Pedir certificados» en la barra principal."},
  // 04/11: aceptación cualitativa SEU del prototipo y gacetillas; sin puntajes inferidos.
  "s1e": {"done": true, "at": "2026-11-04", "nota": "Validación cualitativa de gacetillas aceptada por SEU en recorrido guiado por Juani con Juan Manuel y Leandro. Acta: Documentos/Reuniones/SEU-2026-11-04/Acta-Validacion-Interfaz-y-Gacetillas-A1.md. No se infieren puntajes 1-4 ni conformidad del set formal; su medición sigue en #112. No incluye posts."},
  "s5d": {"done": true, "at": "2026-11-04", "nota": "Regresión técnica existente y recorrido guiado del prototipo con Juan Manuel y Leandro, facilitado por Juani. SEU eligió interfaz A (bandeja y pieza) y aceptó la generación mostrada. Acta: Documentos/Reuniones/SEU-2026-11-04/Acta-Validacion-Interfaz-y-Gacetillas-A1.md. No acredita login Google, permisos Docs ni persistencia reales."},
  "m1": {"done": true, "at": "2026-11-04", "nota": "HU-010 operativa con DoD: s1a-s1e completas; validación humana registrada por la aceptación cualitativa SEU del 04/11 (Documentos/Reuniones/SEU-2026-11-04/Acta-Validacion-Interfaz-y-Gacetillas-A1.md), cerrada por decisión de Juani. Siguen aparte, sin bloquear el hito: la medición puntuada del set (#112) y la carpeta institucional en la unidad compartida (#100)."},
  "m2": {"done": true, "at": "2026-11-04", "nota": "MVP de cursada redefinido el 03/11 con Dirección (B14): Instagram pasa a la presentación Final y LinkedIn a continuidad, así que HU-011 deja de ser condición. HU-010 operativa y validada (m1). Cerrado por decisión de Juani; el criterio formal del Gate (B19, DEF-A1-006) se sigue en #69 y no se declara un TRL por este cierre."},
  "c1": {"done": false, "nota": "Evento cualitativo SEU realizado y aceptado el 04/11 con Juan Manuel y Leandro; trazabilidad en Documentos/Reuniones/SEU-2026-11-04/Acta-Validacion-Interfaz-y-Gacetillas-A1.md. No se informaron puntajes del checklist 1-4; no se fabrica un ≥3/4. Medición formal en #112 y revisión de posts para Final en #14."},

  // Corte de revision: 2026-10-19 (noche), ampliado el 2026-10-21 con el E2E
  // del Plan B. El plan (.mmd) no se toca: no hay rebaseline ni estados
  // nuevos. Contrastado contra: git log desde 2026-09-20; los issues abiertos
  // y cerrados del repo; Implementacion/Agente1/evidencias/ (medicion del
  // servidor 2026-10-19 y 2026-10-21, contrato Historia Viva rc2, anexos
  // 2026-10-17, SLO 2026-10-12, cuenta de servicio 2026-10-14); la suite y el
  // CI del Agente 1 (2411 passed / 8 skipped; CI de main verde); el Registro
  // de Defectos; y la visita a la SEU del 2026-10-19 (actas y cierre en
  // Documentos/Reuniones/SEU-2026-10-19/, todavia fuera de Git al corte). El
  // 20/10 se suman s1c, s3b y s5a con la evidencia de la forma FIE INFORMA,
  // los roles/criterios del 22/09 y el canal Form con correo verificado. El
  // 21/10 se suma s7c con el E2E live de gemma4:e4b y OAuth. Quedan 19 tareas
  // abiertas, explicadas abajo y en Revision-Avance-2026-10-19.md.

  "s0a": { done: true, at: "2026-07-06", nota: "Ollama user-local restaurado, llama3.2:3b descargado (.claude/persistence.md)" },
  "s0b": { done: true, at: "2026-09-28", nota: "Cuenta tecnica dedicada del Agente 1 (institucional DSI/FIE) con OAuth2 verificado en vivo: scopes drive/documents/spreadsheets concedidos y lectura de la carpeta autorizada confirmada. Credencial de hoy: token efimero. El mecanismo definitivo (cuenta de servicio con delegacion, #98) esta implementado offline desde el 14/10; su instalacion en el host y la baja de la OAuth siguen en #99. Evidencia live: notas/workspace-live-d2-2026-09-28.md" },
  "s0c": { done: true, at: "2026-07-10", nota: "Esqueleto del proyecto y logging basico verificados por la suite de pruebas" },
  "m0":  { done: true, at: "2026-07-10", nota: "Entorno offline suficiente para construir el MVP. Conexion Workspace live sigue BLOQUEADO_EXTERNO (DEF-A1-001)" },

  "s1a": { done: true, at: "2026-07-15", nota: "Pipeline de gacetilla offline funcional. Reforzado el 2026-09-08 con la plantilla gacetilla_v3, que decide la linea de lugar por caso y cierra DEF-A1-014" },
  "s1b": { done: true, at: "2026-09-28", nota: "Adapter de Sheets verificado live: lectura real de la planilla sintetica D2 por API (lectura_confirmada) y consumo dentro del E2E. Negativos live: source_request_not_found y workspace_auth_unavailable sin tocar red. Evidencia: notas/workspace-live-d2-2026-09-28.md" },
  "s1d": { done: true, at: "2026-09-08", nota: "Cinco casos sinteticos ejecutados: tres completos generan borrador y dos incompletos se rechazan sin invocar al modelo (matriz-conformidad-hu010-2026-07-20.md). Reverificado live tras DEF-A1-014: 6/6 borradores en dos intentos, identicos byte a byte, mas cuatro casos negativos de lugar. Regresion en test_matriz_hu010.py. No incluye la validacion SEU (s1e)" },
  "s1c": { done: true, at: "2026-10-19", nota: "Forma FIE INFORMA aprobada como referencia de formato y estructura (Brief SEU 19/10); la salida a Docs corrio live el 28/09. El archivo de plantilla en Docs usado en esa corrida es sintetico; la revision de las muestras generadas es s1e" },

  "s2a": { done: true, at: "2026-08-07", nota: "Contrato/politicas de canal offline resueltas en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2b": { done: true, at: "2026-08-12", nota: "Prototipo de post offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2c": { done: true, at: "2026-08-14", nota: "Control de longitud/limpieza offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },

  "s3c": { done: true, at: "2026-08-26", nota: "Spike PostgreSQL cerrado tecnicamente: migraciones 0001-0003, timestamps futuros rechazados, rollback a cero tablas y forward final en PostgreSQL 16 efimero. Medicion registrada el 26/08; la regresion integral vigente al corte 2026-09-08 es de 588 pruebas verdes. No hay adapter ni integracion operativa" },
  "s3d": { done: true, at: "2026-08-26", nota: "Logging seguro con correlation ID, hashes, versiones y controles D2/D3 verificado en la regresion local; no incluye secretos ni acceso Workspace live" },
  "s3b": { done: true, at: "2026-09-22", nota: "Roles nominales y criterios por canal confirmados en el acta del 22/09 (semantica: Juan Manuel; utilitaria y firma final: Sebastian Moreira, luego delegacion a Juan Manuel o Josefina, #125). La revision de las muestras es s1e/s2d" },

  "s4a": { done: true, at: "2026-08-26", nota: "Contrato, modelo de datos y puerto local de confirmacion implementados en HU-012; no hay endpoint ni trigger institucional live" },
  "s4b": { done: true, at: "2026-09-08", nota: "Idempotencia y transiciones atomicas verificadas primero en memoria (26/08) y luego de forma durable (issue #9): RegistroConfirmacionesArchivo conserva estado en disco y reconciliar_envios_reservados cierra reservas colgadas hacia ENVIO_INDETERMINADO sin volver a entregar. 18 pruebas nuevas, dos de concurrencia" },
  "s4c": { done: true, at: "2026-08-26", nota: "Plantilla provisional y puerto de entrega fake verificados. Gmail quedo habilitado con lista de prueba (#40/#41); el modo produccion existe desde #141 pero no esta habilitado. La plantilla institucional sigue BLOQUEADO_EXTERNO (DEF-A1-002)" },

  "s5b": { done: true, at: "2026-09-09", nota: "Modulo agente1/interpretacion.py: clasificacion deterministica contra catalogo cerrado (intenciones_v1), resolucion difusa de actividad sobre el indice de enumerar(), repregunta con candidatas y estado entre turnos, y fallback con LLM local cuyo presupuesto se deriva del contrato y se aplica fail-closed. Sin LangGraph y sin dependencias de runtime. Ocho tickets (#19-#26), suite 588 -> 749. No incluye la validacion SEU" },
  "s5c": { done: true, at: "2026-09-09", nota: "Tarea reformulada el 2026-09-21: el plan original decia 'persistir transcript' y contradecia la spec de HU-013 (#18), que prohibe conservar la prosa escrita por las personas. Lo implementado es el fallback fuera de alcance (#26) mas la persistencia del solo derivado estructurado: la pendiente de repregunta guarda orden, id, titulo y fecha de cada candidata, la intencion y el vencimiento (#25), con una prueba que falla si aparece prosa. Hecho en el mismo corte que s5b" },
  "s5a": { done: true, at: "2026-10-20", nota: "El canal es el Form de pedidos con correo verificado por Google y rol por padron externo (ADR 0005), no un chat. El .mmd conserva el nombre legado 'Chat interno'; el anteproyecto y CONTEXT.md declaran que el Agente 1 no es un chatbot. El padron queda provisional hasta confirmacion de la SEU" },

  "s4d": { done: true, at: "2026-09-21", nota: "Cola de envio propia sin Celery/Redis (merge feature/s4d-envio-asincrono): estado ENVIO_ENCOLADO tras la doble aprobacion, ColaEnviosMemoria y ColaEnviosArchivo con encolado idempotente y orden FIFO, worker drenar_envios con un intento por item por corrida y presupuesto de reintentos (3) hacia FALLIDA. Sigue sin broker; el destino de prueba es el fake y el adapter Gmail existe con lista de prueba. Desde #141 tiene modo produccion opt-in. 28 pruebas nuevas" },

  "s6a": { done: true, at: "2026-09-21", nota: "Slice offline de HU-014 (issue #29, merge feature/hu014-certificados): plantilla provisional de certificado y maquina de estados HITL con el mismo circuito de doble aprobacion de HU-012 (semantica + utilitaria). La plantilla institucional de aprobacion llego el 19/10 y quedo integrada sin versionar firmas (#126, cerrado 11/11); la variante institucional de asistencia no se recibio y sigue la provisional" },
  "s6b": { done: true, at: "2026-09-21", nota: "PDF determinista generado con stdlib pura (sin dependencias nuevas): el borrador lleva la marca BORRADOR - NO EMITIR y el emitido no; bytes reproducibles verificados en regresion" },
  "s6c": { done: true, at: "2026-09-21", nota: "Emision bloqueada sin las dos aprobaciones registradas (mismo circuito que HU-012); el destino es DestinoCertificadosFake y la emision real sigue pendiente de SEU/DSI" },
  "s6d": { done: true, at: "2026-09-21", nota: "62 pruebas nuevas cubren datos faltantes, rechazo, rol invalido, duplicados, recuperacion durable y emision simulada controlada (matriz_conformidad_hu014_v1, 12 casos)" },
  "s6e": { done: true, at: "2026-09-21", nota: "Log de emision con hashes (pdf_hash) sin datos personales en claro, reconciliacion de EMISION_RESERVADA hacia EMISION_INDETERMINADA y doc de limites en evidencias/limites-hu014-offline.md" },
  "m7":  { done: true, at: "2026-10-20", nota: "Suite local 2377 passed / 8 skipped; cobertura 90% registrada. CI de main verde en el run 39455797467 (f2dfbf6). Regresion al 17/11 (0.9.0): 2935 passed / 8 skipped con PostgreSQL, Ruff y CI verdes (PR #178)" },
  "s7c": { done: true, at: "2026-10-21", nota: "E2E live en labredesfie con gemma4:e4b y una actividad real del corpus (FIE-DIF-08), con la cuenta de servicio. 21/10: gacetilla PENDIENTE_VALIDACION en 64,2 s, HU-014 y HU-012, y la consola visual en la presentacion de avance. 23/10, ya en contenedores (runtime oficial, ADR 0013, version 0.5.3): corrida unica completa (gacetilla, HU-014 con 2 certificados EMITIDA, HU-012/HU-013 con lote ENVIO_ENCOLADO), posts de Instagram y LinkedIn en vivo, modelo en HU-014 6/6, HU-012 4/4 y canal 8/8, scheduler con el insumo de A3, respaldo y restauracion, vuelta atras de version y recuperacion ante caida. Gmail y Forms reales de HU-012/HU-014 siguen sin configurar (destinos de prueba). Suite 2444 passed / 8 skipped y CI verde, tambien dentro de la imagen. Evidencia: Implementacion/Agente1/evidencias/contenedores-servidor-2026-10-23.md" },
  "s7d": { done: true, at: "2026-10-30", nota: "Revision de seguridad del laboratorio aprobada en la prueba presencial del 30/10 (agente1 0.5.9 en contenedores en labredesfie). Base: suite de inyeccion en canal y fallback, auditoria D2, aislamiento de contenedores verificado el 23/10 y Anexo 3. La revision de laboratorio iLab/rLab quedo aprobada y #57 se cerro el 11/11." },

  // Sin marcar a proposito. Cada linea dice que falta exactamente, para no
  // arrastrar tareas bloqueadas junto con otras que si estan hechas.
  //
  // s1e  - completada el 04/11 por aceptación cualitativa de gacetillas; ver acta. La medición puntuada no se presume.
  // m1   - completada el 04/11 por decisión de Juani; ver la entrada arriba.
  // s2d  - DIFERIDA (Dirección 03/11, B14): Instagram para la presentación Final,
  //        LinkedIn para continuidad. No bloquea el MVP de cursada. Historial:
  //        validacion SEU de posts y criterios definitivos por canal: la mitad
  //        tecnica se hizo el 22/09 — la SEU confirmo los criterios por canal
  //        (acta) y se implementaron el mismo dia (politica v1 con 17 reglas
  //        activas, prompts v4, catalogo v3, paquete regenerado). La mitad
  //        humana sigue BLOQUEADO_EXTERNO: revision asincronica del paquete
  //        en curso (DEF-A1-005). DEF-A1-007 quedo EN_CORRECCION.
  //        Medicion live del 22/09: 1/6 conforme con y sin reintento
  //        (issue #37 mergeado): la brecha residual es obediencia del
  //        modelo 3B, no del gate ni del pipeline. El 23/09 se midio una
  //        variante de prompt con solo instrucciones positivas: mismo 1/6
  //        con fallas dispersas en 7 codigos (evidencia
  //        medicion-hu011-v3-positivo-2026-09-23.md). Misma noche,
  //        comparacion de modelos (evidencia
  //        medicion-hu011-v3-modelos-2026-09-23.md): llama3.1:8b da 4/6
  //        y mistral:7b da 0/6 - el modelo concreto importa, no solo el
  //        tamano. El 19/10 no hubo revision de muestras (JOS-P5 pendiente);
  //        los criterios por canal del 22/09 siguen vigentes.
  // m2   - completado el 04/11 por decisión de Juani (MVP sin HU-011); criterio del Gate sigue en #69.
  // s3a  - D2 provisionado y verificado live el 28/09. Desde el 21/10 la
  //        identidad definitiva (cuenta de servicio de DSI, #99) opera en el
  //        servidor y la OAuth se dio de baja el 23/10. Desde el 23/10 el host
  //        es el servidor de la facultad con el agente en contenedores
  //        (runtime oficial, ADR 0013, #119 cerrado). Falta solamente la
  //        unidad compartida institucional de D3 con los recursos migrados
  //        (#100, de DSI); por eso no se marca.
  // m3   - depende de s3a; s3b esta completo desde el 22/09.
  // s7d  - seguridad, permisos y prompt injection: la suite cubre la
  //        inyeccion en el canal y el fallback, y el 23/10 se verifico en el
  //        servidor el aislamiento de los contenedores (Ollama sin egreso,
  //        agente sin root ni capacidades, arranque fail-closed). El 30/10
  //        la revision de laboratorio aprobo la seguridad: se marca.
  // m6   - "HU-014 operativa con DoD": el slice offline esta hecho (s6a-s6e).
  //        Al 18/11: plantilla SEU de aprobacion integrada (#126); el lote lo
  //        aprueba quien lo genera (Juani 11/11, ADR 0018); el lote se aprueba
  //        en la web atado al hash con muestra BORRADOR (0.8.0). Desde 0.10.0
  //        el lote se pide desde una actividad del catalogo y se emite desde
  //        la web en segundo plano (#168); desde 0.11.0 el pedido acepta
  //        directamente el Excel de aprobados de la SEU (#193), probado en el
  //        servidor con una lista real. En modo demostracion el lote queda
  //        marcado de prueba, con BORRADOR, y no se envia. Falta para el DoD
  //        (#142): las imagenes de firma de la SEU (sin ellas no se emite
  //        institucionalmente, R2), la variante institucional de asistencia,
  //        el login institucional (m5) y el envio Gmail fuera de la lista de
  //        prueba. No se declara emision institucional.
  // s4e  - duplicados y destinatario invalido probados, y desde el 2026-09-21
  //        el envio exige las dos aprobaciones del circuito (semantica RGC +
  //        utilitaria Coordinador, DEF-A1-016 cerrado como RESUELTO_TECNICO,
  //        issue #28, suite 757). Falta la validacion SEU del mismo item.
  //        El 22/09 la bible amplio HU-012 a notificaciones de participacion,
  //        situacion de pagos y aprobacion: extension implementada y mergeada
  //        el mismo 22/09 (issue #33, catalogo tipos_notificacion_v1) con
  //        situacion_pagos bloqueada fail-closed; la fuente de datos de pagos
  //        sigue DESCONOCIDO hasta respuesta SEU. El 19/10 no hubo validacion
  //        SEU del item; #125 cambia la aprobacion a una sola persona y
  //        requiere adaptacion.
  // m4   - el adapter Gmail existe con lista de prueba y modo produccion
  //        (#141); lo que falta es que los renderers compongan el cuerpo de
  //        la plantilla aprobada por tipo y la lista real de la SEU.
  //
  // Sprint 5 (HU-013) arranca el 2026-09-15. El diseno esta cerrado y
  // especificado (issue #18 con ocho tickets, #19 a #26). Al corte del
  // 2026-10-19 estan marcadas s5a, s5b y s5c; s5d y m5 siguen sin marca.
  // Avance por ticket al 2026-09-09:
  //
  //   #19 CERRADO  - enumerar actividades desde el puerto de fuente. Prefactor
  //                  de s5b: habilita construir el indice de busqueda. Ambos
  //                  adapters (CSV, Sheets) enumeran sin agregar superficie de
  //                  escritura. Suite 588 -> 605.
  //   #21 CERRADO  - brecha de aprobacion unica de HU-012 registrada como
  //                  DEF-A1-016. No corresponde a ninguna tarea del cronograma:
  //                  es registro de defecto, y la correccion pertenece a su
  //                  propio incremento, no a HU-013.
  //   #20 CERRADO  - seam de interpretacion `interpretar_solicitud`: entra
  //                  prosa con un id explicito, sale un puntero a borrador de
  //                  gacetilla. Catalogo cerrado en intenciones_v1, despacho
  //                  decidido por codigo y no por el JSON, prosa fuera del
  //                  prompt y fuera del registro. Suite 605 -> 643.
  //                  Es el nucleo de s5b, pero s5b pide ademas el LLM local:
  //                  eso llega recien con #26.
  //   #22 CERRADO  - despacho de `generar_post` al pipeline de HU-011. El
  //                  canal de red (Instagram/LinkedIn) se resuelve con codigo
  //                  deterministico; sin canal, o con los dos a la vez, el
  //                  resultado es INCOMPLETA sin default silencioso. Los gates
  //                  de contenido y de politica de redes no se debilitaron.
  //   #24 CERRADO  - puerto de canal `CanalInteraccion` + bucle `atender_canal`
  //                  + fake + adapter de planilla offline, todo por encima del
  //                  seam: `interpretacion.py` quedo con cero lineas tocadas.
  //                  Incluye recorrido documentado para la prueba guiada con
  //                  una persona de la SEU sin credenciales, en
  //                  evidencias/recorrido-prueba-guiada-canal-planilla.md.
  //                  Suite 643 -> 663.
  //   #23 CERRADO  - resolucion difusa de actividad sin identificador, sobre
  //                  el indice de enumerar() de #19. Puntaje deterministico
  //                  con difflib, sin dependencias nuevas; solo resuelve la
  //                  coincidencia unica y clara. Corpus versionado de frases
  //                  en data/frases_resolucion_actividad.csv. El contenido de
  //                  la planilla no llega a ningun prompt. Suite 663 -> 686
  //                  (incluye dos pruebas de la composicion #22+#23, un post
  //                  sin identificador explicito, que ningun ticket cubria
  //                  por separado y aparecio al mergear).
  //   #25 CERRADO  - repregunta con candidatas y estado entre turnos. Puerto
  //                  RegistroPendientes con fake en memoria y sin durabilidad,
  //                  por decision explicita de la spec. La pendiente guarda
  //                  solo orden, id, titulo y fecha de cada candidata, mas la
  //                  intencion y el vencimiento: nunca prosa, y hay una prueba
  //                  que afirma sobre el conjunto exacto de campos. Reloj
  //                  inyectado para el vencimiento de 15 minutos. Verificado
  //                  tambien a traves del bucle atender_canal de #24.
  //                  Suite 686 -> 702.
  //   #26 CERRADO  - fallback con modelo local. Unica salida admitida del
  //                  modelo validada contra el catalogo cerrado; presupuesto
  //                  derivado del contrato Y aplicado fail-closed; el modelo
  //                  nunca ve la planilla ni recibe la prosa como instruccion.
  //                  Con este ticket s5b queda completa y se marca arriba.
  //                  Suite 702 -> 749.
  //
  // Con #26 cerrado existe la regresión técnica de HU-013. El 04/11 se
  // realizó el recorrido guiado SEU con Juan Manuel y Leandro: s5d completa.
  // m5 sigue sin completar por los controles del canal web real pendientes.
  //
  // Sprint 7 y cierre: m7 desde el 20/10, s7c desde el 21/10 y s7d desde el
  // 30/10; el cierre sigue abierto.
  //
  // s7a  - contratos y mocks con A3-A5 y puerto A2 con fakes; el contrato
  //        con Historia Viva (#17) sigue abierto, asi que no cubre A2-A5
  //        completo. Evidencia: Contrato-Candidato-Insumos-A2-A5-Agente-1.md,
  //        contracts/insumos/a3_evento_gacetilla_v1.schema.json, ADR 0008.
  // s7b  - integracion progresiva: depende de s7a y del contrato #17.
  // c1   - aceptación cualitativa realizada el 04/11; el checklist 1-4 no tiene puntajes informados. La ausencia prevista para el 18/11 no cancela este evento.
  //        La presentación de cursada del 18/11 (con la SEU presente) es una demo, no la medición del checklist.
  // c2   - al 18/11 regresion completa verde con 0.11.1 (3164 passed /
  //        8 skipped, Ruff y CI verdes, PR #196). Segun el registro al 17/11
  //        no hay defectos CRITICA abiertos; siguen ALTA bloqueados externamente: DEF-A1-002
  //        (plantilla de gacetilla), DEF-A1-006 (criterio del Gate, Cesar) y
  //        DEF-A1-007 (revision editorial de posts).
  // c3   - agente1-v0.11.1 desplegado y verificado en el servidor el 18/11
  //        (servicios sin reinicios), sobre la evidencia de 0.9.0 en PR #178
  //        y el respaldo de vuelta atras (demo-respaldo-2026-11-17). No es
  //        una release candidata con paquete de evidencias cerrado.
  // c4   - depende de c1-c3.
  // m8   - depende de c1-c4, del DoD de la bible para TRL 3-4 y del OK de
  //        Cesar (criterio en #69, DEF-A1-006).
  //
  // Nota de alcance: cerrar los ocho tickets NO acredita validacion
  // institucional ni nivel TRL, como dice #18 explicitamente. La evidencia es
  // tecnica y reproducible; la aceptacion sigue dependiendo de definiciones de
  // la SEU que continuan abiertas.
  //
  // Issue #27 (ready-for-human): decidir si el modelo puede recuperar un
  // pedido cuya clasificacion deterministica fallo. Hoy no puede, por ADR
  // 0001. Mueve el limite de confianza del modelo, asi que es decision
  // institucional.
  //
  // Nota de alcance bible 22/09: la nueva version de Procesos y Agentes agrega
  // HU-016 (BD de consultas, 13 SP) y HU-017 (Disposiciones Decanales) dentro
  // de Epica E2 = Agente 1. Decision confirmada el 2026-09-30: fuera del PPS,
  // delegadas a los alumnos de 4to ano que continuan el P100 (issue #34), igual
  // que la lectura A1 de HU-015 y cualquier HU posterior a HU-014. Las
  // expansiones de HU-010..HU-014 (ej.: situacion de pagos en HU-012) si son
  // alcance del PPS. El .mmd no se rebaselinea: conserva las
  // fechas de plan y este archivo registra el avance real — Sprint 6 (HU-014)
  // quedo completo una semana antes de su inicio planificado.
  //
  // Ninguno de estos tickets acredita s5a: esa tarea pide autenticacion de
  // personal SEU y la identidad institucional sigue BLOQUEADO_EXTERNO. El
  // canal de #24 es un adapter de planilla offline con identidad afirmada y
  // no verificada (ADR 0002), que no sustituye ese requisito.
};
