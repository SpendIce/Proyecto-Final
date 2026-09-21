# Consulta sobre el cierre de G2 y el alcance del Agente 1

Para: César Cicerchia, Director de Carrera y del Proyecto Centenario  
De: Juan Ignacio Goñe, PPS Agente 1 (Extensión Bot)  
Fecha: 9 de septiembre de 2026  
Asunto: Agente 1: consultas sobre el Gate G2 y el alcance del proyecto

Hola César, ¿cómo estás?

Te escribo para consultarte la evidencia del Gate G2 y tres puntos de alcance del documento de Procesos y Agentes. Me gustaría dejar estas definiciones alineadas para ordenar el trabajo que sigue.

## Estado del prototipo

Al 8 de septiembre tengo una versión reproducible desde Git, con 588 pruebas aprobadas. HU-010 genera gacetillas con el modelo local: seis de seis casos conformes, con resultados idénticos entre corridas. HU-011 también alcanza seis de seis con el contrato de catálogo cerrado. HU-012 funciona offline y conserva el control de duplicados ante una caída del proceso, aunque todavía no permite envíos reales. Todas las salidas quedan como borradores pendientes de validación.

Para completar el panorama, todavía hay cinco puntos que dependen de definiciones o recursos institucionales: la revisión editorial de la SEU, la identidad y los permisos para Google Workspace, la plantilla institucional, los criterios de contenido por canal y los orígenes de inscripción. Los detallo en la consulta sobre G2.

## 1. Criterio para G2

Para dejar documentado el criterio del gate, necesito confirmar estos cinco puntos:

1. ¿Qué evidencia mínima tengo que presentar? El anteproyecto pide gacetilla y post generados, logs, checklist de la SEU, mediciones de tiempo e informe de avance.

2. ¿La revisión de la SEU es obligatoria para aprobar G2? El documento de procesos define TRL 3 como "funciona en entorno controlado, caso simple validado, sin necesidad de robustez total". El anteproyecto incluye el checklist de la SEU como evidencia mínima de G2. ¿Ese checklist es condición para el gate o corresponde incorporarlo en una instancia posterior?

3. ¿Los cinco puntos institucionales bloquean G2 o pueden quedar como riesgos aceptados, con responsable y fecha comprometida? Son: acceso a Workspace, plantilla institucional, validación editorial, criterios de contenido por canal y definición de orígenes de inscripción. Ninguno está clasificado como crítico; su resolución requiere accesos o definiciones institucionales.

4. ¿Quién debe aprobar y firmar el cierre de G2?

5. ¿Alcanza con un acta breve y el paquete de evidencia adjunto? Si ese formato sirve, preparo el acta para la firma de quien corresponda.

Mi propuesta, sujeta a tu aprobación, es cerrar G2 con la evidencia del prototipo en entorno controlado y dejar la validación de la SEU como condición de entrada de G4. El acta dejaría explícito que ese cierre no acredita aceptación institucional. La validación humana antes de publicar o enviar contenido seguiría siendo obligatoria.

## 2. Definiciones del documento de Procesos y Agentes

Al convertir el documento a texto para poder consultarlo, encontré estos tres puntos en la versión vigente. Necesito confirmar cómo interpretarlos antes de avanzar:

1. ¿Qué canal corresponde implementar para HU-013? El Backlog técnico pide "interfaz simple, prompt en Sheet o Doc". Supervisión humana indica que la comunicación "deberá ser mediante un email que dispara el agente al humano, quien recibe una invitación a chatear". El bloque de Diseño de Sistemas Informáticos 2 describe una interfaz web con inicio de sesión, listado de borradores, corrección y aprobación, y un prototipo en Figma. ¿Cuál de estas definiciones rige para HU-013? Si corresponden a etapas o funciones distintas, necesitaría saber qué se espera en cada una. Por ahora dejé el canal separado de la lógica mediante una interfaz común, para poder adaptarlo cuando se defina. La elección también cambia la infraestructura necesaria.

2. ¿HU-013 debe incluir la aprobación de los contenidos de las demás historias? El documento indica que la validación humana usa ese mismo canal. Si eso forma parte de HU-013, su alcance excedería la interacción interna estimada en tres puntos. Mi interpretación fue mantener ambas funciones separadas, porque el caso de uso transversal de validación enumera los casos que lo incluyen y el de interacción interna no figura entre ellos. ¿Es correcta esa lectura?

3. ¿FastAPI y Celery son obligatorios o son una referencia de implementación en EP04? El escenario de prueba los menciona como parte de la arquitectura. Para el prototipo decidí diferirlos, porque no eran necesarios para el gate y agregaban infraestructura sin una necesidad validada. ¿Podemos mantener esa decisión o deben incorporarse para cumplir con la evaluación?

También quería pedirte, para las próximas versiones, una nota breve de cambios. El documento indica que las modificaciones se resaltan en amarillo, pero ese resaltado no aparece en las copias exportadas a Markdown y PDF con las que estamos trabajando. Una nota de dos líneas nos permitiría ubicar los cambios sin releer todo.

Podemos resolver las cinco preguntas de G2 en una reunión de 30 minutos y las de alcance por escrito, si te resulta más cómodo. También me sirve que respondas directamente sobre los puntos numerados.

Quedo atento a tus comentarios. Mientras tanto, continúo con el diseño desacoplado que ya tengo.

Gracias, César.

Juan Ignacio Goñe
