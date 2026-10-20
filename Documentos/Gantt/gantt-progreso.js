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
  // Corte de revision: 2026-10-19 (noche), previo a la presentacion de avance
  // del 2026-10-21. El plan (.mmd) no se toca: no hay rebaseline ni estados
  // nuevos. Contrastado contra: git log desde 2026-09-20; los issues abiertos
  // y cerrados del repo al 19/10; Implementacion/Agente1/evidencias/ (medicion
  // del servidor 2026-10-19, contrato Historia Viva rc2, anexos 2026-10-17,
  // SLO 2026-10-12, cuenta de servicio 2026-10-14); la suite y el CI del
  // Agente 1 (run 39302694001 del 2026-10-19: 1 failed, 2284 passed, 5
  // skipped, en rojo); el Registro de Defectos; y la visita a la SEU del
  // 2026-10-19 (actas y cierre en Documentos/Reuniones/SEU-2026-10-19/,
  // todavia fuera de Git al corte). Este corte NO agrega tareas nuevas a
  // done: las 24 que siguen abiertas estan explicadas abajo y en
  // Revision-Avance-2026-10-19.md.

  "s0a": { done: true, at: "2026-07-06", nota: "Ollama user-local restaurado, llama3.2:3b descargado (.claude/persistence.md)" },
  "s0b": { done: true, at: "2026-09-28", nota: "Cuenta tecnica dedicada del Agente 1 (institucional DSI/FIE) con OAuth2 verificado en vivo: scopes drive/documents/spreadsheets concedidos y lectura de la carpeta autorizada confirmada. Credencial de hoy: token efimero. El mecanismo definitivo (cuenta de servicio con delegacion, #98) esta implementado offline desde el 14/10; su instalacion en el host y la baja de la OAuth siguen en #99. Evidencia live: notas/workspace-live-d2-2026-09-28.md" },
  "s0c": { done: true, at: "2026-07-10", nota: "Esqueleto del proyecto y logging basico verificados por la suite de pruebas" },
  "m0":  { done: true, at: "2026-07-10", nota: "Entorno offline suficiente para construir el MVP. Conexion Workspace live sigue BLOQUEADO_EXTERNO (DEF-A1-001)" },

  "s1a": { done: true, at: "2026-07-15", nota: "Pipeline de gacetilla offline funcional. Reforzado el 2026-09-08 con la plantilla gacetilla_v3, que decide la linea de lugar por caso y cierra DEF-A1-014" },
  "s1b": { done: true, at: "2026-09-28", nota: "Adapter de Sheets verificado live: lectura real de la planilla sintetica D2 por API (lectura_confirmada) y consumo dentro del E2E. Negativos live: source_request_not_found y workspace_auth_unavailable sin tocar red. Evidencia: notas/workspace-live-d2-2026-09-28.md" },
  "s1d": { done: true, at: "2026-09-08", nota: "Cinco casos sinteticos ejecutados: tres completos generan borrador y dos incompletos se rechazan sin invocar al modelo (matriz-conformidad-hu010-2026-07-20.md). Reverificado live tras DEF-A1-014: 6/6 borradores en dos intentos, identicos byte a byte, mas cuatro casos negativos de lugar. Regresion en test_matriz_hu010.py. No incluye validacion SEU (s1e) ni Workspace live (s1b, s1c)" },

  "s2a": { done: true, at: "2026-08-07", nota: "Contrato/politicas de canal offline resueltas en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2b": { done: true, at: "2026-08-12", nota: "Prototipo de post offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2c": { done: true, at: "2026-08-14", nota: "Control de longitud/limpieza offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },

  "s3c": { done: true, at: "2026-08-26", nota: "Spike PostgreSQL cerrado tecnicamente: migraciones 0001-0003, timestamps futuros rechazados, rollback a cero tablas y forward final en PostgreSQL 16 efimero. Medicion registrada el 26/08; la regresion integral vigente al corte 2026-09-08 es de 588 pruebas verdes. No hay adapter ni integracion operativa" },
  "s3d": { done: true, at: "2026-08-26", nota: "Logging seguro con correlation ID, hashes, versiones y controles D2/D3 verificado en la regresion local; no incluye secretos ni acceso Workspace live" },

  "s4a": { done: true, at: "2026-08-26", nota: "Contrato, modelo de datos y puerto local de confirmacion implementados en HU-012; no hay endpoint ni trigger institucional live" },
  "s4b": { done: true, at: "2026-09-08", nota: "Idempotencia y transiciones atomicas verificadas primero en memoria (26/08) y luego de forma durable (issue #9): RegistroConfirmacionesArchivo conserva estado en disco y reconciliar_envios_reservados cierra reservas colgadas hacia ENVIO_INDETERMINADO sin volver a entregar. 18 pruebas nuevas, dos de concurrencia" },
  "s4c": { done: true, at: "2026-08-26", nota: "Plantilla provisional y puerto de entrega fake verificados. Gmail quedo habilitado con lista de prueba (#40/#41) y sin envio live; la plantilla institucional sigue BLOQUEADO_EXTERNO (DEF-A1-002)" },

  "s5b": { done: true, at: "2026-09-09", nota: "Modulo agente1/interpretacion.py: clasificacion deterministica contra catalogo cerrado (intenciones_v1), resolucion difusa de actividad sobre el indice de enumerar(), repregunta con candidatas y estado entre turnos, y fallback con LLM local cuyo presupuesto se deriva del contrato y se aplica fail-closed. Sin LangGraph y sin dependencias de runtime. Ocho tickets (#19-#26), suite 588 -> 749. No incluye s5a (autenticacion) ni la validacion SEU" },
  "s5c": { done: true, at: "2026-09-09", nota: "Tarea reformulada el 2026-09-21: el plan original decia 'persistir transcript' y contradecia la spec de HU-013 (#18), que prohibe conservar la prosa escrita por las personas. Lo implementado es el fallback fuera de alcance (#26) mas la persistencia del solo derivado estructurado: la pendiente de repregunta guarda orden, id, titulo y fecha de cada candidata, la intencion y el vencimiento (#25), con una prueba que falla si aparece prosa. Hecho en el mismo corte que s5b" },

  "s4d": { done: true, at: "2026-09-21", nota: "Cola de envio propia sin Celery/Redis (merge feature/s4d-envio-asincrono): estado ENVIO_ENCOLADO tras la doble aprobacion, ColaEnviosMemoria y ColaEnviosArchivo con encolado idempotente y orden FIFO, worker drenar_envios con un intento por item por corrida y presupuesto de reintentos (3) hacia FALLIDA. Sigue sin adapter de correo real ni broker: el destino es el fake. 28 pruebas nuevas" },

  "s6a": { done: true, at: "2026-09-21", nota: "Slice offline de HU-014 (issue #29, merge feature/hu014-certificados): plantilla provisional de certificado y maquina de estados HITL con el mismo circuito de doble aprobacion de HU-012 (semantica + utilitaria). El 19/10 llego la plantilla institucional de aprobacion (issue #126), pero no esta integrada; la variante de asistencia sigue pendiente" },
  "s6b": { done: true, at: "2026-09-21", nota: "PDF determinista generado con stdlib pura (sin dependencias nuevas): el borrador lleva la marca BORRADOR - NO EMITIR y el emitido no; bytes reproducibles verificados en regresion" },
  "s6c": { done: true, at: "2026-09-21", nota: "Emision bloqueada sin las dos aprobaciones registradas (mismo circuito que HU-012); el destino es DestinoCertificadosFake y la emision real sigue pendiente de SEU/DSI" },
  "s6d": { done: true, at: "2026-09-21", nota: "62 pruebas nuevas cubren datos faltantes, rechazo, rol invalido, duplicados, recuperacion durable y emision simulada controlada (matriz_conformidad_hu014_v1, 12 casos)" },
  "s6e": { done: true, at: "2026-09-21", nota: "Log de emision con hashes (pdf_hash) sin datos personales en claro, reconciliacion de EMISION_RESERVADA hacia EMISION_INDETERMINADA y doc de limites en evidencias/limites-hu014-offline.md" },

  // Sin marcar a proposito. Cada linea dice que falta exactamente, para no
  // arrastrar tareas bloqueadas junto con otras que si estan hechas.
  //
  // s1c  - la forma de la gacetilla de difusion sale del corpus FIE INFORMA,
  //        que la SEU reconoce como referencia aprobada de formato y
  //        estructura. La copia de plantilla y el volcado en Docs corrieron
  //        live el 28/09, pero el archivo de plantilla en Docs usado en esa
  //        corrida es sintetico y falta la revision de las muestras
  //        generadas (DEF-A1-005).
  // s1e  - validacion SEU de gacetillas: BLOQUEADO_EXTERNO (DEF-A1-005). Paquete de nueve muestras listo, acta pendiente. La visita del 19/10 no reviso muestras ni hubo Juan Manuel; JOS-P5 sigue pendiente.
  // m1   - el DoD de HU-010 incluye Sheets, Docs, plantilla y validacion
  //        humana: Sheets y Docs ya corrieron live el 28/09; al 19/10 quedan
  //        abiertas la plantilla institucional (s1c) y la validacion SEU (s1e).
  // s2d  - validacion SEU de posts y criterios definitivos por canal: la mitad
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
  // m2   - Gate TRL 3 PENDIENTE: falta criterio formal (DEF-A1-006, BLOQUEADO_EXTERNO) y validacion SEU.
  // s3a  - D2 provisionado y verificado live el 28/09: cuenta tecnica
  //        dedicada, carpeta autorizada, planilla y plantilla sinteticas, y
  //        E2E completo con borrador real. El servidor de la facultad corre
  //        como host de computo sobre D2 desde el 19/10. El issue #15 se
  //        cerro el 08/10 con la parte tecnica cumplida. D3 como ambiente
  //        completo (unidad compartida y recursos propios, #100), el aval
  //        formal y el host institucional siguen abiertos (#63/#64, #119).
  // s3b  - SEU designo revisor titular/suplente y se documento el circuito; el
  //        22/09 quedaron confirmados los roles nominales (semantica: Juan
  //        Manuel; utilitaria y firma final: Sebastian Moreira, Secretario de
  //        Extension). Falta la revision de las muestras (asincronica en
  //        curso). El 19/10 no se revisaron muestras; la aprobacion de
  //        contenido paso a una sola persona (Juan Manuel o Josefina, por
  //        delegacion de Moreira), cambio registrado en #125.
  // m3   - depende de s3a y s3b; al 19/10 ninguno de los dos esta completo.
  // m6   - "HU-014 operativa con DoD": el slice offline esta hecho (s6a-s6e),
  //        pero el DoD exige plantilla institucional de la SEU y validacion
  //        humana real. El 19/10 llego la plantilla de aprobacion (ficha de
  //        la SEU, issue #126), pero no esta integrada; la variante de
  //        asistencia y el aprobador final del lote siguen pendientes. No se
  //        declara emision institucional por recibir el archivo.
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
  // m4   - depende de s4d y s4e, y de un adapter de correo real que al 19/10
  //        sigue sin existir.
  //
  // Sprint 5 (HU-013) arranca el 2026-09-15. El diseno esta cerrado y
  // especificado (issue #18 con ocho tickets, #19 a #26). Al corte del
  // 2026-10-19 estan marcadas s5b y s5c; s5a, s5d y m5 siguen sin marca.
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
  // Con #26 cerrado, HU-013 tiene sus ocho tickets integrados. De las cuatro
  // tareas del sprint 5 quedan marcadas s5b y s5c; s5c se reformulo el
  // 2026-09-21 porque el plan original ("persistir transcript") contradecia
  // la spec de HU-013, y la tarea del .mmd quedo reescrita acorde. Las otras
  // dos NO se marcan, porque no se completan con mas codigo:
  //
  // s5a  - "Chat interno con autenticacion de personal SEU". El canal existe
  //        (#24: puerto, fake y adapter de planilla offline) pero la identidad
  //        es AFIRMADA por el canal y no verificada (ADR 0002): cada linea de
  //        auditoria lleva identidad_verificada: false. La autenticacion
  //        institucional sigue BLOQUEADO_EXTERNO (DEF-A1-001, issue #15). La
  //        evidencia de #24 no acredita control de acceso y no hay que leerla
  //        asi. El 19/10 Josefina acepto la lectura directa del buzon, pero
  //        la habilitacion tecnica sigue pendiente; eso no es autenticacion
  //        de personal.
  // s5d  - renombrada el 2026-09-21 a "Regresion de solicitudes y prueba
  //        guiada de usabilidad con SEU". La mitad automatizable ya existe:
  //        las solicitudes validas y las fuera de alcance tienen cobertura de
  //        regresion desde los tickets #19-#26. La mitad humana tenia fecha
  //        para el viernes 25/09 (instrumento de sesion en el issue #32),
  //        pero la prueba no se hizo: JOS-P4 sigue pendiente y no hay fecha
  //        nueva. El recorrido quedo documentado en #24
  //        (evidencias/recorrido-prueba-guiada-canal-planilla.md).
  // m5   - "HU-013 operativa con DoD": depende de s5a y s5d; al 19/10 ambas
  //        siguen abiertas.
  //
  // Sprint 7 y cierre: al 2026-10-19 ninguna tarea esta completa.
  //
  // s7a  - contratos y mocks con A3-A5 y puerto A2 con fakes; el contrato
  //        con Historia Viva (#17) sigue abierto, asi que no cubre A2-A5
  //        completo. Evidencia: Contrato-Candidato-Insumos-A2-A5-Agente-1.md,
  //        contracts/insumos/a3_evento_gacetilla_v1.schema.json, ADR 0008.
  // s7b  - integracion progresiva: depende de s7a y del contrato #17.
  // s7c  - hay suite amplia y E2E D2 del 28/09, pero el CI del 19/10 esta en
  //        rojo (run 39302694001) y la corrida E2E en el servidor de la demo
  //        (#118) todavia no esta versionada. No se acredita "unitarias,
  //        integracion y E2E" completo.
  // s7d  - auditoria de seguridad D2/D3 y pruebas de prompt injection como
  //        dato, offline; permisos y revocacion reales siguen pendientes.
  // m7   - "Suite de pruebas en verde y cobertura registrada": el CI del
  //        19/10 fallo (1 failed, 2284 passed, 5 skipped). No se declara.
  // c1   - validacion con usuarios SEU: sin sesion agendada; JOS-D5 registra
  //        que nadie de la SEU asistira al 18/11.
  // c2   - sin defectos CRITICA abiertos, pero hay ALTA bloqueados y el CI
  //        no esta verde.
  // c3   - el tag agente1-v0.1.0 existe, pero al corte no hay release
  //        candidate con paquete de evidencias cerrado.
  // c4   - depende de c1-c3.
  // m8   - depende de c1-c4 y del Gate TRL 4.
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
