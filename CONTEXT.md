# Proyecto Centenario — Agente 1

Este contexto define el lenguaje compartido para planificar, desarrollar y evaluar la PPS de Juan Ignacio Goñe dentro del Proyecto Centenario de la FIE/UNDEF.

## Lenguaje

**Agente 1**:
Agente de comunicacion institucional de la Secretaria de Extension Universitaria, responsable de preparar piezas comunicacionales dentro del Proceso 4 con validacion humana obligatoria.
_Evitar_: orquestador, chatbot publico, agente de analitica

**Actividad**:
Actividad de extension en una edicion determinada (un curso, un evento, una charla). Es la unidad que comparten las piezas comunicacionales sobre ella, su plan de pago, su plantilla de actividad y su lista de cierre. El Agente 1 lee sus datos; no la crea ni la modifica.
_Evitar_: solicitud, pedido, evento a secas

**Solicitud**:
Pedido de una pieza comunicacional sobre una actividad, que una persona de la SEU le hace al Agente 1 por el canal de interaccion. Una actividad puede tener muchas solicitudes; una solicitud se refiere a una sola actividad.
_Evitar_: actividad, fila de la planilla de actividades

**Pieza comunicacional**:
Contenido institucional preparado para un canal y un publico determinados, como una gacetilla, un post, un correo, un newsletter o un certificado.
_Evitar_: publicacion, cuando todavia no fue validada ni difundida

**Borrador**:
Pieza comunicacional generada que no tiene autorizacion para publicarse, enviarse ni emitirse.
_Evitar_: contenido aprobado, publicacion

**FIE Informa**:
Canal de correo institucional por el que la FIE difunde a su comunidad piezas de la SEU y de otras areas. Cada pieza se redacta como un documento con nombre «Fie informa D-M <titulo>».
_Evitar_: newsletter, gacetilla, cuando se habla del canal y no de la pieza

**Ejemplo aprobado**:
Pieza que la SEU ya publico y que sirve de referencia de formato, estructura y registro para lo que genera el Agente 1. No es referencia de ortografia ni es una plantilla aprobada: el agente no completa variables sobre ella.
_Evitar_: plantilla, modelo, muestra (las muestras son borradores del agente)

**Validacion humana**:
Conjunto de decisiones registradas por personas con rol institucional autorizado que habilita a una pieza a avanzar; no se infiere de la conformidad tecnica. Toma una forma distinta segun quien difunde la pieza: en una pieza que el Agente 1 envia o emite, es la plantilla aprobada mas la aprobacion de lote; en una pieza de difusion, que publica una persona, es la decision de publicacion. Toda validacion humana queda registrada en el sistema.
_Evitar_: validacion automatica, aprobacion del agente, aprobacion al publicar sin registro

**Plantilla aprobada**:
Version de texto o de diseno de una pieza que el Agente 1 envia o emite (confirmacion, recordatorio, certificado), con aprobacion semantica y aprobacion utilitaria. Se aprueba una vez por version, no por pieza. Al enviar o emitir, el agente solo completa sus variables con datos: ningun texto que el modelo escriba llega a un destinatario sin haber pasado por esta aprobacion. Puede ser una plantilla base o una plantilla de actividad.
_Evitar_: plantilla generica, ejemplo, modelo de mail

**Plantilla base**:
Plantilla aprobada que entrega la SEU para un tipo de pieza: estructura, partes fijas y firma. No cambia de una actividad a otra.
_Evitar_: plantilla institucional, a secas

**Plantilla de actividad**:
Plantilla aprobada que el Agente 1 redacta para una actividad concreta a partir de una plantilla base. El modelo escribe solo la prosa descriptiva; montos, cuotas, fechas, horarios, links y datos de la persona quedan como variables. Se aprueba por actividad.
_Evitar_: borrador de confirmacion, mail personalizado

**Aprobacion de lote**:
Decision de una persona autorizada, previa al envio o la emision, que confirma que una actividad, su lista de destinatarios y los datos que van a completar la plantilla aprobada son correctos. Es una por lote, no una por pieza. En las confirmaciones, que salen a medida que llega cada inscripto, el lote es la habilitacion de envios de la actividad.
_Evitar_: aprobacion de envio, aprobacion por destinatario

**Lista de cierre**:
Lista de las personas que terminaron una actividad, con sus datos y su condicion (asistencia o aprobacion), que carga quien gestiona el curso al cerrarla. Es la unica fuente de quien recibe un certificado y de que tipo: el Agente 1 nunca infiere un resultado academico. Su aprobacion de lote la da el Secretario de Extension, que firma; cualquier cambio posterior exige aprobarla de nuevo.
_Evitar_: padron, lista de inscriptos, acta de notas

**Decision de publicacion**:
Registro que deja quien publica o descarta un borrador de difusion (gacetilla, post), con su identidad y su rol. Es la validacion humana de la difusion: el Agente 1 no publica, y la decision no dispara nada en el agente.
_Evitar_: aprobacion semantica, aprobacion utilitaria, cuando se habla de difusion

**Aprobacion semantica**:
Decision del Responsable de Gestion del Conocimiento sobre si el contenido dice lo correcto: hechos, tono y consistencia institucional. Se aplica a una plantilla aprobada, no a cada pieza enviada.
_Evitar_: revision editorial, visto bueno

**Aprobacion utilitaria**:
Decision del Coordinador de Extension sobre si la pieza sirve para el proposito y el canal previstos. Se aplica a una plantilla aprobada, no a cada pieza enviada.
_Evitar_: aprobacion final, aprobacion del coordinador a secas

**Canal de interaccion**:
Medio por el que una persona de la SEU le pide algo al Agente 1 y recibe la respuesta. Transporta pedidos y resultados: no es una conversacion abierta, y el Agente 1 no es un chatbot con el que se charla. Es independiente de la identidad con la que el agente opera contra los sistemas institucionales: recibir un pedido por un buzon no otorga los permisos de ese buzon.
_Evitar_: chat, conversacion, interfaz, frontend, backend

**Solicitud en lenguaje natural**:
Pedido en prosa libre que una persona interna dirige al Agente 1. Es entrada no confiable: nunca llega como instruccion al modelo generador.
_Evitar_: prompt del usuario, comando, consulta

**Intencion**:
Resultado estructurado de interpretar una solicitud en lenguaje natural, tomado de un catalogo cerrado. Una solicitud que no corresponde a ninguna intencion del catalogo se rechaza; no se aproxima a la mas parecida.
_Evitar_: comando, accion, funcion invocada

**Baseline tecnica recuperable**:
Estado versionado del Agente 1 que puede reconstruirse desde Git, supera sus verificaciones tecnicas declaradas y mantiene trazabilidad entre alcance, pruebas y evidencia, sin implicar aceptacion institucional ni un nivel TRL.
_Evitar_: version final, TRL alcanzado, producto aprobado

**Bloqueante externo**:
Decision, recurso, permiso o validacion que debe aportar una contraparte humana o institucional y que el equipo tecnico no puede sustituir de manera valida.
_Evitar_: defecto de software

**Historia Viva**:
Agente 2 del Proyecto Centenario, responsable del acervo historico institucional validado; entrega fuentes recuperables al Agente 1 y recibe aportes pendientes de validacion.
_Evitar_: generador de efemerides, redactor de contenido para el Agente 1

**Insumo de agente**:
Entrada que un agente del P100 (A3, A4 o A5) le entrega al Agente 1 para que produzca una pieza. El Agente 1 le responde al productor con el estado del insumo (borrador generado o rechazado), nunca con la pieza. Historia Viva no entrega insumos: el Agente 1 la consulta.
_Evitar_: pedido de agente, mensaje entre agentes, orden

### Evaluacion del PPS

**Mesa final**:
Instancia de evaluacion de la asignatura del 18/11/2026 en la que el Agente 1 se demuestra funcionando en vivo ante el profesor de la materia, la Direccion de Carrera y la SEU.
_Evitar_: presentacion final, defensa, gate TRL

**Presentacion final**:
Exposicion del PPS con defensa oral en la ventana de febrero de 2027. No suma historias nuevas; solo puede cerrar lo que en la mesa final quedo detenido por un bloqueante externo.
_Evitar_: mesa final, entrega de version

**Revision de laboratorio**:
Evaluacion de calidad y seguridad del sistema funcionando que hacen los laboratorios iLab y rLab sobre los anexos de calidad y seguridad presentados por el autor. Su informe habilita, habilita con condiciones o no habilita la mesa final.
_Evitar_: auditoria, pentest, gate TRL

**Perfil de calidad**:
Conjunto de atributos de calidad que el autor declara para el sistema de demostracion, por estrato, cada uno con su estado de implementacion, su motivo y su evidencia. Lo presenta el Anexo 1 por estrato y el Anexo 2 por atributo, en el orden del estandar; la seguridad tiene su propio perfil en el Anexo 3.
_Evitar_: plan de calidad, metricas de calidad

**Estrato**:
Capa del inventario de componentes del sistema de demostracion (canal, interpretacion, generacion, gates, control de pagos, aprobacion, cola y envio, persistencia y auditoria, integraciones), que es la unidad sobre la que se declara el perfil de calidad. En la tabla fuente del perfil, el valor `Sistema` marca atributos transversales que ninguna capa ejerce sola.
_Evitar_: modulo, componente (cuando se habla de la unidad del perfil)

**Estado de implementacion**:
Categoria que el autor declara para cada atributo del perfil: A implementado satisfactoriamente, B implementado con observaciones, C tenido en cuenta y no implementado (previsto). Un atributo es A o B solo si tiene evidencia versionada y se puede mostrar en vivo. La categoria D (desconocido o ignorado) la asigna el laboratorio, nunca el autor.
_Evitar_: nivel de competencia (lo califica el laboratorio)

**Sistema de demostracion**:
El Agente 1 en todo su alcance declarado (ambiente, flujos y componentes), funcionando de punta a punta en vivo en la revision de laboratorio y en la mesa final. La mesa final puede mostrar una base posterior a la que reviso el laboratorio, sobre el mismo ambiente. No tiene capacidades detenidas: lo que depende de un tercero corre contra un destino de prueba o un insumo provisional declarado, nunca contra un fake.
_Evitar_: demo, maqueta, prototipo, recorte

**Destino de prueba**:
Destino real de una pieza (buzon, carpeta, lista de direcciones) con alcance restringido y declarado, que el mecanismo productivo alcanza igual que alcanzaria al destino definitivo. Se distingue de un fake, que finge el efecto sin ejecutarlo.
_Evitar_: destino simulado, mock, sandbox

**Insumo provisional**:
Entrada que una persona declarada carga en lugar del productor que todavia no la entrega (la SEU, otro agente), con la forma del contrato y por el mismo mecanismo por el que la leeria del productor definitivo. El Agente 1 la procesa igual que a la definitiva; lo provisional es quien la produce, no el camino.
_Evitar_: dato de prueba, fake, mock

**Productor provisional**:
Persona declarada que carga insumos provisionales en nombre de un agente del P100 que todavia no existe o no esta disponible (A3-A5). Ocupa el rol del agente, no lo simula.
_Evitar_: agente simulado, mock de agente

### Traspaso

**Traspaso**:
Entrega del Agente 1, en el estado en que quede despues de la presentacion final, a los responsables que lo sostienen cuando el autor egresa. Se entrega lo que haya: si para entonces opera, se continua; si no, queda listo para que el responsable de operacion lo ponga en marcha.
_Evitar_: handover, pase a produccion, entrega final

**Responsable de operacion**:
La Direccion de la carrera de Ingenieria en Informatica, que responde por que el Agente 1 siga funcionando despues del traspaso y decide en quien delega su ejecucion (por ejemplo, DSI).
_Evitar_: Informatica, DSI (cuando se habla de quien responde)

**Dueno funcional**:
La SEU, que decide sobre el contenido y la autorizacion de lo que el Agente 1 produce: plantillas aprobadas, padron de roles, lista de cierre y quien aprueba cada pieza.
_Evitar_: usuario, cliente

**Responsable de evolucion**:
Los alumnos de Ingenieria en Informatica que continuan el P100 y cambian el codigo y las historias de usuario del Agente 1 despues del traspaso.
_Evitar_: mantenedor, Informatica

### Operacion

**Ventana de operacion**:
Dias y horario en que el Agente 1 se compromete a atender: corre sus corridas programadas, envia lo aprobado y su operador da soporte. Fuera de la ventana no hay compromiso, y lo aprobado se envia en la primera corrida de la ventana siguiente.
_Evitar_: horario de atencion, 24/7, uptime

**Tiempo de atencion**:
Lo que tarda el Agente 1 desde que una persona de la SEU hace un pedido hasta que le llega el aviso con el borrador. Incluye la espera hasta la siguiente corrida, no solo la generacion.
_Evitar_: latencia, tiempo de generacion

**Integridad del gate**:
Garantia de que toda pieza que llega a validacion humana paso el gate, y de que ninguna pieza no conforme se presenta como conforme. Es un compromiso operativo; la tasa de conformidad, en cambio, es una medida de calidad.
_Evitar_: tasa de conformidad, calidad del modelo

**Nivel verificado**:
Valor de un objetivo de servicio efectivamente medido sobre el sistema de demostracion, con su evidencia. Es lo que se presenta al laboratorio; el objetivo es lo que se le compromete al operador despues del traspaso.
_Evitar_: objetivo, meta, SLO (cuando se habla de lo medido)

**Retencion acotada**:
Interpretacion vigente de que «el sistema no retiene datos»: los datos personales se conservan solo durante el ciclo de envio y su ventana de reconciliacion, y los respaldos no los conservan mas tiempo. La auditoria guarda solo hashes.
_Evitar_: sin retencion, borrado, minimizacion (como sinonimos)

**Cambio controlado**:
Modificacion de algo que define como se comporta el Agente 1 (codigo, prompts y parametros de inferencia, criterios de contenido de la SEU, contratos de interfaz, configuracion de Workspace y credenciales) y que solo entra en operacion aprobada por el dueño de su clase. Los criterios de contenido de la SEU siguen su propio circuito de aprobacion; el control de cambios lo reconoce, no lo duplica.
_Evitar_: actualizacion, ajuste, deploy

**Version del agente**:
Estado etiquetado del Agente 1 que se instala en el host, con la huella de todo lo controlado que contiene. Es la unidad que se instala, se revierte y se cita: cada pieza registra con que version salio.
_Evitar_: release, build, baseline (la baseline tecnica recuperable es otra cosa)

**Dato operativo**:
Informacion que mantiene su dueño institucional y que el Agente 1 solo lee para trabajar: padron de roles, lista de cierre, planilla de actividades. Cargarla o corregirla no es un cambio controlado; queda rastreada por la auditoria.
_Evitar_: configuracion, parametro

**Cambio de emergencia**:
Situacion que habilita actuar por fuera del circuito normal: una credencial comprometida o una pieza enviada o emitida por error. La respuesta es suspender el agente, no corregirlo en caliente; la correccion vuelve por el circuito normal.
_Evitar_: hotfix, parche urgente

**Cuenta tecnica**:
Cuenta de Workspace de la FIE en cuyo nombre actua el Agente 1: es la dueña del buzon que lee y desde el que envia, y la que figura como autora de sus archivos en la auditoria de Google. Ninguna persona la usa para trabajar. La credencial con la que el agente obtiene acceso en su nombre es otra cosa, y cambiarla no cambia la cuenta tecnica.
_Evitar_: cuenta de servicio, bot, cuenta del agente (como sinonimos)

### Control de pagos

**Actividad arancelada**:
Actividad de extension que exige el pago de una o mas cuotas a favor de la Fundacion Savio, con eventuales bonificaciones por categoria de inscripto.
_Evitar_: curso pago, actividad con costo

**Preinscripto**:
Persona que registro su interes en una actividad arancelada y todavia no aseguro su vacante pagando la primera cuota.
_Evitar_: inscripto, interesado, alumno

**Inscripto**:
Persona con vacante asegurada en una actividad. En una actividad arancelada lo es cuando la primera cuota tiene pago confirmado o cuando esta bonificada; un comprobante presentado no alcanza.
_Evitar_: preinscripto, alumno

**Plan de pago**:
Condiciones economicas de una actividad arancelada en una edicion: cantidad de cuotas, monto y vencimiento de cada una, medios de pago y categorias bonificadas.
_Evitar_: arancel, a secas, cuando se habla de las cuotas

**Cuota**:
Cada uno de los pagos que integran un plan de pago, identificada por su numero de orden.
_Evitar_: pago, cuando todavia no se pago

**Comprobante presentado**:
Respuesta de un inscripto que adjunta la constancia de un pago. Es una declaracion del inscripto, no prueba que el dinero haya ingresado.
_Evitar_: pago registrado, pagado

**Pago confirmado**:
Cuota cuyo ingreso fue verificado por la Fundacion Savio. El Agente 1 no verifica pagos: solo puede reflejar una confirmacion que la Fundacion haya hecho observable.
_Evitar_: pago aprobado, pago validado por el agente

**Recordatorio de pago**:
Aviso a un inscripto con una cuota sin comprobante presentado, antes de su vencimiento.
_Evitar_: intimacion, aviso de deuda

**Novedad de pago**:
Registro que carga el Departamento sobre un inscripto o preinscripto para dejar asentado lo que no surge de los correos: confirmacion de la Fundacion, comprobante rechazado, comprobante que cubre varias cuotas, direccion alternativa o bonificacion.
_Evitar_: estado de pago, ajuste del agente
