# Interfaz web del Agente 1: alcance y validación con la SEU

**Autor:** Juan Ignacio Goñe. **Fecha:** 03/11/2026. **Estado:** recorrido de diseño confirmado por Juan Ignacio Goñe; implementación y validación con la SEU pendientes. Responde a la orientación de Juani de reemplazar el recorrido fragmentado por una web propia con acceso mediante cuenta Google.

**Acuerdos de la entrevista:** Juani confirmó primera entrega de gacetillas, edición manual además de ajustes por el agente y bandeja compartida con permisos. La revisión y la decisión se ubican en la misma web. La primera prueba guiada de usabilidad/contenido puede realizarse con un prototipo; la verificación funcional de login y controles requiere implementación real. Juani eligió edición manual en Google Docs abierto aparte y cierre del recorrido de difusión al aprobar el borrador, sin pedir registro posterior de publicación. Juani también confirmó señales automáticas con comentarios opcionales y aporte manual a Historia Viva por el personal mientras se difiere el aporte automático de este primer recorrido. Los apartados siguientes se leen con estas precisiones.

## Recorrido acordado con Juani

`Ingresar → bandeja compartida SEU → pedido guiado → borrador → editar en Docs o pedir ajuste → revisar → aprobar o descartar`.

El pedido precarga datos disponibles y exige actividad sólo cuando el tipo la necesita. Al pedir un ajuste se usa la última revisión, incluidas las correcciones humanas, y se crea otra sin sobrescribirla. La aprobación de difusión cierra el recorrido en A1. No se pide registrar publicación; el personal registra en Historia Viva por ahora. Las señales de revisión se capturan automáticamente y el comentario es opcional. La primera prueba guiada puede usar un prototipo. Juani confirmó globalmente el entendimiento después de revisar el resumen visual. Se cierra la entrevista de producto; implementación, permisos institucionales y validación SEU siguen pendientes.

## 1. Decisión de diseño de trabajo

Se propone una **web interna del Agente 1**, con inicio de sesión de Google, una bandeja de pedidos y una vista de revisión. Los formularios serán propios de la aplicación; Google aporta la autenticación. El correo queda como aviso opcional con enlace al pedido. El usuario podrá continuar un pedido sin volver a cargar los datos comunes ni buscar sus borradores en sucesivos correos.

Esta solución se encuadra en HU-013 y en la validación humana de las piezas existentes, dentro del Proceso 4. No incorpora historias funcionales nuevas ni un chatbot. Su primera entrega para validar será el recorrido completo de gacetillas/FIE INFORMA. El resto de las funciones vigentes de A1 se incorporará de manera progresiva, conservando sus circuitos actuales hasta verificar cada migración.

La **interfaz común para los cinco agentes** se propone como continuidad del P100 y debe acordarse con Ignacio y los responsables de los otros agentes. La web de A1 deja una separación clara entre acceso humano y lógica del agente, sin comprometer ahora un portal general, identidad compartida o contratos de los cinco agentes.

## 2. Qué verá la persona usuaria

| Pantalla | Comportamiento de la primera entrega |
|---|---|
| Acceso | «Ingresar con Google». Sólo una identidad institucional admitida y autorizada en el padrón accede al trabajo. Si falta permiso, recibe un mensaje claro sin ver pedidos. |
| Bandeja | Pedidos del equipo SEU visibles según permisos y tareas asignadas al rol autorizado. Se puede continuar trabajo de otra persona autorizada; se muestran estado, actividad, tipo de pieza y última versión. |
| Nuevo pedido | Formulario propio guiado: tipo, actividad condicional y área emisora desde catálogos existentes, con datos precargados e indicaciones adicionales. No exige redactar un pedido completo desde cero. Se conserva la clasificación y validación del núcleo. |
| Revisión | Borrador visible en la aplicación, actividad y versión identificadas; acciones disponibles según rol. El enlace al Doc es complementario. |
| Solicitar ajuste | Parte de la última revisión recuperada, incluidas las correcciones humanas, y conserva pedido, actividad y datos comunes. La persona indica el cambio; se produce otra revisión sin sobrescribir la anterior y debe revisarse de nuevo. No se presenta como chat abierto. |
| Edición manual | «Editar en Google Docs» abre el editor oficial aparte. Al volver, A1 actualiza el contenido y vincula una revisión identificada antes de permitir la decisión. El acceso al Doc requiere sus propios permisos. |
| Decisión | Para gacetillas permite aprobar el borrador vigente o descartarlo. El recorrido de difusión termina ahí; no se pide registrar después su publicación ni se publica por API. |

Para certificados y notificaciones, una futura vista de decisión deberá respetar aprobación de plantilla/lote y destinatarios del circuito existente. No se reutilizará un botón genérico de «aprobar» como autorización indistinta de todas las salidas.

Una corrección no modifica por sí sola la actividad institucional de origen ni el texto fuente del catálogo. Si el problema está en esos datos, se informa qué responsable debe corregirlos y se vuelve a leer la fuente autorizada. Juani confirmó edición manual además de nueva generación; se realiza mediante el editor de Google Docs abierto aparte. Se conserva el pedido en A1 y se actualiza la vista al regresar. No se construye un editor propio ni se depende de un editor privado embebido. El login de A1 no concede permisos sobre el documento ni garantiza qué cuenta Google queda activa en Docs.

## 3. Autenticación, autorización y acceso técnico

**Autenticación humana.** Se propone Google Identity Services y un botón explícito de inicio de sesión. El servidor verifica el ID token: firma, emisor, audiencia y vencimiento; para restringir a Workspace comprueba `hd`, sin confiar sólo en el sufijo del correo. `sub` identifica de forma estable a la cuenta. La recepción de credenciales debe protegerse contra CSRF; no basta decodificar un token en JavaScript. Se utilizará una biblioteca mantenida. [Verificación oficial de ID tokens](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

**Autorización local.** Una identidad válida se resuelve contra el padrón institucional y sus permisos por operación y pedido. Cada lectura y decisión vuelve a comprobar autorización en el servidor. El correo del token sirve para resolver la compatibilidad con el padrón actual; no se acepta uno escrito por la persona ni un rol enviado por el navegador. No hay registro público de usuarios ni alta automática de permisos por pertenecer al dominio. El responsable de mantener el padrón y el sentido de «aprueba SEU+Dir Proy» siguen pendientes de precisión; no se agrega al director como aprobador de cada pieza por inferencia.

**Sesión de aplicación.** Después del login, la web establece una sesión de servidor con cookie `HttpOnly`, `Secure` y política `SameSite` compatible con el flujo. Se proponen vencimiento por inactividad, cierre de sesión y protección CSRF en operaciones que modifican estado. Los tokens no van a logs, enlaces, almacenamiento persistente del navegador ni al LLM. El alcance y la duración de sesión deben configurarse y probarse, sin inventar una política institucional vigente.

**Identidad técnica del agente.** El login humano no entrega al agente acceso a Drive o Gmail personales. Las integraciones conservan la cuenta de servicio de DSI y la cuenta técnica del ADR 0011. El navegador nunca recibe esas credenciales. Esta autenticación no reactiva la antigua credencial OAuth usada para operar Workspace en nombre del autor.

**Configuración externa necesaria.** Google requiere un cliente de aplicación web y configuración de acceso, orígenes y, según el modo, URL de recepción autorizada. Para este diseño se propone un único origen HTTPS institucional accesible desde los equipos de validación. Los permisos de inicio de sesión no requieren scopes sensibles de Drive/Gmail del usuario. DSI debe confirmar proyecto institucional, cliente, dominio admitido y condiciones de acceso; no se solicitan contraseñas a los usuarios. No se presume que esas configuraciones ya estén entregadas. [Preparación de Sign in with Google](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid), [OpenID Connect de Google](https://developers.google.com/identity/openid-connect/openid-connect).

## 4. Ubicación en la arquitectura

```text
Persona SEU ── navegador ── Google: identidad
                    │
                    ▼
          Web interna de A1 + sesión
                    │
        permisos por persona, pedido y acción
                    │
                    ▼
        canal web / registro de decisiones
                    │
        núcleo existente + ejecución acotada
                    │
          borradores, estado y auditoría
                    │
          Workspace con identidad técnica
```

La web es un canal del Agente 1. No conecta el navegador directamente a Ollama ni le permite decidir qué herramientas ejecuta el agente. Los otros agentes conservan sus contratos de integración; un usuario no obtiene acceso a ellos por iniciar sesión en A1.

Se recomienda un módulo web Python que sirva páginas y operaciones del mismo origen. **FastAPI pasa a tener una necesidad concreta**: recibir y verificar identidad, consultar estado y aceptar acciones humanas. Se propone para esta capa, sin incorporarlo todavía a las dependencias ni declarar su adopción institucional cerrada. No se suma una SPA independiente, un broker, Redis ni otro runtime de agentes para este recorrido.

El código ya separa el canal mediante `CanalInteraccion`/`PedidoCanal` en `canal.py`; el Form actual adapta filas a ese puerto. La lectura de decisiones en `decisiones_form.py` está ligada a Forms: debe extraerse o reutilizarse su lógica de negocio mediante una interfaz común antes de agregar el adapter web. **No alcanza con cambiar el HTML**. La autenticación real, el seguimiento por pedido y la revisión de versiones son trabajo de implementación pendiente.

El módulo propuesto expone operaciones pequeñas: crear pedido, consultar los autorizados, obtener su resultado, solicitar ajuste y registrar decisión. Encapsula verificación de identidad, padrón, idempotencia y auditoría. El núcleo de interpretación y generación conserva su única responsabilidad y sus controles.

## 5. Estado, versiones y ejecución

La aplicación conserva un identificador raíz de pedido, identificadores de revisiones y la referencia a la pieza/versiones producidas. Los estados visibles son una proyección de los estados reales, sin llamar «aprobado» a un resultado que sólo pasó controles automáticos.

Las generaciones largas se atienden fuera de la respuesta HTTP, con aceptación trazable y consulta de estado desde la misma vista. No se espera que la conexión del navegador permanezca abierta durante la inferencia. El adapter web necesita una entrada durable e idempotente integrada con el ejecutor; el sondeo de Forms no cubre automáticamente esa función. Se conserva el modelo de ejecución local, con concurrencia acotada al host, sin crear una segunda cola de envíos.

Antes de implementar debe concretarse el almacenamiento del nuevo canal: qué dato transitorio necesita el ejecutor, quién puede leerlo, cuándo se purga y cómo se respalda. Este detalle no queda resuelto por elegir una interfaz ni justifica conservar conversaciones. La sesión y la cola no pueden ampliar silenciosamente la retención vigente. Los borradores mantienen su repositorio autorizado; los registros de auditoría conservan referencias y hashes según los contratos existentes, sin tokens ni prosa de pedidos.

La consulta del borrador se restringe a la pieza autorizada por el pedido, con tamaño y formato acotados; el servidor no acepta un ID de Drive arbitrario del navegador. El texto generado se representa como texto seguro, no como HTML ejecutable.

Antes de un ajuste generativo se recupera el texto vigente de la revisión elegida. Se usa como base de edición, no como fuente de hechos ni como instrucción privilegiada; los datos institucionales siguen procediendo de sus fuentes autorizadas. Si esa recuperación falla o hay conflicto de revisión, no se regenera silenciosamente desde una copia anterior: se informa y se pide actualizar la vista. La salida se registra como revisión nueva.

Cada decisión identifica la versión revisada. Si ya existe otra revisión, la aplicación rechaza la decisión obsoleta y muestra la vigente. Un nuevo borrador no hereda aprobaciones de una versión anterior. La aprobación se vincula al contenido capturado y revisado, no sólo al enlace mutable de Docs; ediciones posteriores no quedan aprobadas por esa decisión. La importación, captura y detección de cambios están pendientes de implementación. Un doble clic no duplica pedidos ni efectos. Ante una operación de envío o emisión de resultado indeterminado, la interfaz conserva ese estado y no ofrece un reintento que pueda duplicarla.

## Aporte a Historia Viva en el primer recorrido

Juani decidió diferir el aporte automático de estas piezas desde el nuevo canal. Por ahora el personal puede registrarlas manualmente en Historia Viva, por su propio circuito. El agente no exige una confirmación de ese registro ni trata una aprobación como evidencia de publicación. Se conserva la consulta a A2 cuando corresponda. El contrato y el código previos basados en `publique` no se reinterpretan; su adaptación eventual queda fuera de este primer recorrido y requiere coordinación con Historia Viva.

## Señales de revisión sin carga adicional

La web registra aprobación o descarte, pedido/revisión y versión del agente. Si hubo edición en Docs, compara el texto generado conservado para el ciclo de revisión con el texto reimportado al volver o aprobar y deriva señales de cambio; distingue aceptación sin cambios y aceptación después de intervención humana. Es una comparación entre capturas, no un registro completo de cada pulsación o autor de edición en Google Docs.

Los motivos y observaciones son opcionales. No se pide un cuestionario para cerrar cada pieza. La evaluación guiada de usabilidad/contenido es una instancia distinta y sí usa su instrumento de prueba. La aprobación no se utiliza por sí sola como evidencia de que el texto original del modelo fue correcto.

Las métricas derivadas y referencias/hashes pueden alimentar el análisis de mejoras; el texto completo necesario para comparar se usa durante el ciclo y no se agrega a logs ni se archiva indefinidamente para aprendizaje. Deben concretarse retención y purga del dato transitorio antes de implementar. Esto no habilita autoaplicación de cambios ni decide entre las alternativas de autoaprendizaje que revisará César.

## 6. Corte del trabajo y continuidad

| Etapa | Incluido | Condición de salida |
|---|---|---|
| Diseño para revisar | Este alcance, pantallas, identidad, frontera y prueba guiada | Juani revisa; SEU confirma recorrido y permisos necesarios; se registran observaciones |
| Primer recorrido implementado | Login real, bandeja restringida y gacetilla: pedido → borrador → ajuste → decisión | DSI habilita acceso; controles técnicos pasan; SEU prueba el mismo recorrido con contenido generado |
| Migración restante de A1 | Vistas para las historias vigentes, según sus aprobaciones y destinos | Cada función demuestra equivalencia con su circuito anterior; Forms deja de ser necesario para esa función |
| Continuidad P100 | Portal compartido, navegación A1–A5, eventual inicio de sesión común y bandejas entre agentes | Acuerdo con Ignacio y responsables; contratos, permisos, operación y costos definidos |

Para A1, la entrada web reemplaza al Form en el flujo migrado; no se embebe ni se escribe una fila fingiendo que Google Forms verificó al usuario. Durante la transición, cada pedido declara su canal de origen y comparte reglas de autorización y decisiones. El retiro del canal viejo requiere evidencia de funcionamiento del nuevo; no se deshabilita con este documento.

## 7. Validación conjunta de interfaz y contenido

Se distinguen dos instancias: una **prueba guiada de interfaz**, que Juani permite hacer sobre un prototipo para iterar con la SEU, y la **verificación funcional del canal real**, que demuestra login, permisos, persistencia y recuperación. La primera no debe esperar necesariamente a la segunda; se declara qué mecanismos son reales o simulados. La sesión de acceso de la web es un concepto diferente de ambas instancias.

La SEU realiza las tareas sobre borradores generados por el agente, conservando dos resultados separados: utilidad de la interfaz y calidad de la pieza. Poder completar el recorrido no demuestra que la gacetilla sea aceptable; aceptar un texto tampoco acredita control de acceso.

| Caso | Evidencia y criterio de cierre |
|---|---|
| Persona autorizada hace un pedido | Acceso real, actividad y área elegidas correctamente; identificador y estado recuperables |
| Generación en curso | La vista informa avance o espera sin exigir repetir el pedido ni mantener una conexión larga |
| Revisión de gacetilla | Texto y versión visibles; la persona puntúa contenido con la rúbrica vigente y registra observaciones |
| Ajuste | Se conservan datos comunes; se parte de la última revisión humana o generada, sin perder cambios previos; nueva revisión vinculada, anterior conservada y nueva evaluación del texto |
| Decisión vigente | Sólo rol habilitado, sobre la versión actual, con registro de identidad y fecha; sin publicación automática |
| Acceso indebido | Cuenta externa, persona fuera del padrón o acceso a pedido ajeno rechazados también por petición directa al servidor |
| Sesión y concurrencia | Sesión vencida no admite acciones; doble clic no duplica; decisión sobre versión obsoleta rechazada |
| Caída y recuperación | Pedido aceptado no desaparece; estado real recuperable; no se repite un efecto indeterminado |

Se registra por tarea: resultado, ayuda requerida, errores, cantidad de cambios de contexto y observación del usuario; los tiempos se miden sin fijar aquí una meta no acordada. Para contenido se usan los criterios y escala SEU vigentes. La aceptación incluye persona participante, fecha, actividad, versión del sistema y de la pieza, puntajes, observaciones y decisión. El instrumento no contiene credenciales ni datos innecesarios de participantes de cursos.

**Trazabilidad:** P4; HU-013 como canal, HU-010 como primer recorrido y validación humana transversal. DoD: autenticación y autorización comprobadas, generación con controles existentes, estados recuperables, corrección por revisión, decisiones auditadas y sesión de uso registrada. Responsable técnico: Juani; validación funcional: SEU; acceso institucional: DSI; portal P100: acuerdo futuro con Ignacio y responsables. Este diseño no acredita TRL; la evidencia interna de uso e integración alimentará la evaluación correspondiente.

## 8. Qué queda cerrado y qué falta

Queda definida la dirección de trabajo: web propia de A1 con login Google y revisión en un lugar; primer recorrido con gacetillas; portal de cinco agentes para continuidad. Juani confirmó el recorrido completo después de la entrevista y su resumen visual. El respaldo de César a simplificar y esta confirmación de diseño no equivalen a aceptación institucional de una implementación por parte de la SEU.

Antes de una prueba funcional faltan cliente de login, URL HTTPS y conectividad, cuentas y padrón autorizados, diseño durable del canal con retención explícita e implementación/verificación de la sesión y las acciones. La SEU debe confirmar el recorrido y los permisos; el alcance ambiguo de «aprueba SEU+Dir Proy» sigue abierto. No hace falta resolver el portal completo para avanzar con esas condiciones de A1.

Fuentes: respuestas de Dirección y WhatsApp aportado por Juani, sintetizadas en [Reunión con la Dirección de carrera](https://github.com/SpendIce/Proyecto-Final/issues/69), con respaldo local en `Documentos/Reuniones/Direccion-2026-11-03/`; ADR 0005/0011/0013; `canal.py`, `canal_form.py`, `decisiones_form.py`; [arquitectura P100 en tres capas](Arquitectura-Multiagente-P100-Tres-Capas-2026-10-21.md). La documentación de Google fue consultada el 03/11/2026. Los controles y el corte propuestos aquí son decisiones de diseño del PPS, no requisitos atribuidos a Google o a la SEU sin confirmación.
