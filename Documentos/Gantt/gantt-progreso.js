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
  // Corte de revision: 2026-09-09. Contrastado contra la suite vigente (749
  // pruebas verdes), el Registro de Defectos y la matriz HU-DoD.

  "s0a": { done: true, at: "2026-07-06", nota: "Ollama user-local restaurado, llama3.2:3b descargado (.claude/persistence.md)" },
  "s0c": { done: true, at: "2026-07-10", nota: "Esqueleto del proyecto y logging basico verificados por la suite de pruebas" },
  "m0":  { done: true, at: "2026-07-10", nota: "Entorno offline suficiente para construir el MVP. Conexion Workspace live sigue BLOQUEADO_EXTERNO (DEF-A1-001)" },

  "s1a": { done: true, at: "2026-07-15", nota: "Pipeline de gacetilla offline funcional. Reforzado el 2026-09-08 con la plantilla gacetilla_v3, que decide la linea de lugar por caso y cierra DEF-A1-014" },
  "s1d": { done: true, at: "2026-09-08", nota: "Cinco casos sinteticos ejecutados: tres completos generan borrador y dos incompletos se rechazan sin invocar al modelo (matriz-conformidad-hu010-2026-07-20.md). Reverificado live tras DEF-A1-014: 6/6 borradores en dos intentos, identicos byte a byte, mas cuatro casos negativos de lugar. Regresion en test_matriz_hu010.py. No incluye validacion SEU (s1e) ni Workspace live (s1b, s1c)" },

  "s2a": { done: true, at: "2026-08-07", nota: "Contrato/politicas de canal offline resueltas en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2b": { done: true, at: "2026-08-12", nota: "Prototipo de post offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2c": { done: true, at: "2026-08-14", nota: "Control de longitud/limpieza offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },

  "s3c": { done: true, at: "2026-08-26", nota: "Spike PostgreSQL cerrado tecnicamente: migraciones 0001-0003, timestamps futuros rechazados, rollback a cero tablas y forward final en PostgreSQL 16 efimero. Medicion registrada el 26/08; la regresion integral vigente al corte 2026-09-08 es de 588 pruebas verdes. No hay adapter ni integracion operativa" },
  "s3d": { done: true, at: "2026-08-26", nota: "Logging seguro con correlation ID, hashes, versiones y controles D2/D3 verificado en la regresion local; no incluye secretos ni acceso Workspace live" },

  "s4a": { done: true, at: "2026-08-26", nota: "Contrato, modelo de datos y puerto local de confirmacion implementados en HU-012; no hay endpoint ni trigger institucional live" },
  "s4b": { done: true, at: "2026-09-08", nota: "Idempotencia y transiciones atomicas verificadas primero en memoria (26/08) y luego de forma durable (issue #9): RegistroConfirmacionesArchivo conserva estado en disco y reconciliar_envios_reservados cierra reservas colgadas hacia ENVIO_INDETERMINADO sin volver a entregar. 18 pruebas nuevas, dos de concurrencia" },
  "s4c": { done: true, at: "2026-08-26", nota: "Plantilla provisional y puerto de entrega fake verificados; Gmail/Workspace y plantilla institucional continuan BLOQUEADO_EXTERNO (DEF-A1-001, DEF-A1-002)" },

  "s5b": { done: true, at: "2026-09-09", nota: "Modulo agente1/interpretacion.py: clasificacion deterministica contra catalogo cerrado (intenciones_v1), resolucion difusa de actividad sobre el indice de enumerar(), repregunta con candidatas y estado entre turnos, y fallback con LLM local cuyo presupuesto se deriva del contrato y se aplica fail-closed. Sin LangGraph y sin dependencias de runtime. Ocho tickets (#19-#26), suite 588 -> 749. No incluye s5a (autenticacion) ni la validacion SEU" },

  // Sin marcar a proposito. Cada linea dice que falta exactamente, para no
  // arrastrar tareas bloqueadas junto con otras que si estan hechas.
  //
  // s0b  - Workspace/OAuth2 institucional: BLOQUEADO_EXTERNO (DEF-A1-001).
  // s1b  - adapter de Sheets verificado offline; falta OAuth y corrida live.
  // s1c  - adapter de Docs/Drive verificado offline; falta plantilla institucional aprobada (DEF-A1-002) y corrida live.
  // s1e  - validacion SEU de gacetillas: BLOQUEADO_EXTERNO (DEF-A1-005). Paquete de nueve muestras listo, acta pendiente.
  // m1   - el DoD de HU-010 incluye Sheets, Docs, plantilla y validacion humana: tres de esos cuatro siguen abiertos.
  // s2d  - validacion SEU de posts y criterios definitivos por canal: BLOQUEADO_EXTERNO (DEF-A1-005, DEF-A1-007).
  // m2   - Gate TRL 3 PENDIENTE: falta criterio formal (DEF-A1-006) y validacion SEU.
  // s3a  - paquete de gestion DSI redactado (issue #15), pero identidad, permisos y recursos siguen sin otorgarse.
  // s3b  - SEU designo revisor titular/suplente y se documento el circuito; faltan criterios por canal y acta de sesion.
  // m3   - depende de s3a y s3b.
  // s4d  - no existe tarea de envio asincrona ni persistencia operativa en base: la persistencia vigente es en archivo y PostgreSQL sigue siendo spike.
  // s4e  - duplicados y destinatario invalido estan probados (test_confirmaciones.py, matriz HU-012); falta la validacion SEU del mismo item.
  // m4   - depende de s4d y s4e, y de un adapter de correo que no existe.
  //
  // Sprint 5 (HU-013) arranca el 2026-09-15. El diseno esta cerrado y
  // especificado (issue #18 con ocho tickets, #19 a #26) y la implementacion
  // empezo, pero ninguna tarea del cronograma esta completa todavia: s5a-s5d
  // y m5 no llevan marca. Avance por ticket al 2026-09-09:
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
  // Con #26 cerrado, HU-013 tiene sus ocho tickets integrados. De las cuatro
  // tareas del sprint 5 solo s5b se marca. Las otras tres NO, y conviene que
  // conste por que, porque dos de ellas no se completan con mas codigo:
  //
  // s5a  - "Chat interno con autenticacion de personal SEU". El canal existe
  //        (#24: puerto, fake y adapter de planilla offline) pero la identidad
  //        es AFIRMADA por el canal y no verificada (ADR 0002): cada linea de
  //        auditoria lleva identidad_verificada: false. La autenticacion
  //        institucional sigue BLOQUEADO_EXTERNO (DEF-A1-001, issue #15). La
  //        evidencia de #24 no acredita control de acceso y no hay que leerla
  //        asi.
  // s5c  - "Fallback fuera de alcance y persistir transcript". La primera
  //        mitad esta hecha; la segunda **se decidio no hacer** y esta en
  //        conflicto con el plan: la spec de HU-013 exige que el registro no
  //        conserve la prosa escrita por las personas (#18, historia 19 del
  //        auditor), para que la trazabilidad no cree un deposito de datos
  //        personales. Se persiste solo el derivado estructurado, y hay
  //        pruebas que fallan si aparece prosa. La tarea del cronograma
  //        deberia reformularse en lugar de marcarse.
  // s5d  - "Probar solicitudes validas, fuera de alcance y usabilidad". Las
  //        dos primeras estan cubiertas por la regresion. La usabilidad no:
  //        exige la prueba guiada con una persona de la SEU, cuyo recorrido
  //        quedo documentado en #24
  //        (evidencias/recorrido-prueba-guiada-canal-planilla.md) pero todavia
  //        no se ejecuto con nadie.
  // m5   - "HU-013 operativa con DoD": depende de s5a, s5c y s5d.
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
  // Ninguno de estos tickets acredita s5a: esa tarea pide autenticacion de
  // personal SEU y la identidad institucional sigue BLOQUEADO_EXTERNO. El
  // canal de #24 es un adapter de planilla offline con identidad afirmada y
  // no verificada (ADR 0002), que no sustituye ese requisito.
};
