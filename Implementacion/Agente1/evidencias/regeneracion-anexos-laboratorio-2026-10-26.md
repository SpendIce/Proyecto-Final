# Regeneración de los anexos de laboratorio, 26/10 (#147)

- **Estado:** anexos 1, 2 y 3 regenerados después de una revisión de referencias viejas. Listos para la revisión de Juani y el envío (fecha límite: fin de la cursada, 25/11).
- **Foto declarada:** corte del 26/10/2026, versión del agente **0.5.6** (tag `agente1-v0.5.6`). Reemplaza la foto 0.5.5 del mismo día.
- **Entrega:** `Documentos/Laboratorio/Entrega/` (`Anexo1-Presentacion.docx`, `Anexo2-Calidad.docx`, `Anexo3-Seguridad.docx`), sobre las plantillas oficiales 2025.
- **Verificación:** suite 2444 verdes y 8 saltados; ruff limpio. En los tres Word no queda ninguna versión anterior salvo la frase que cuenta lo desplegado (0.5.0 a 0.5.5), ni «apagado», «laptop», «PENDIENTE #51» o «4 %».

## Referencias viejas corregidas

**Perfil de calidad** (anexos 1 y 2):
- **Encabezado:** decía corte del 23/10 y versión 0.5.4, mientras los anexos ya declaraban el 26/10. Ahora dice 26/10 y 0.5.6, con el scheduler encendido.
- **Capacidad:** citaba la medición del 26/08 con `llama3.2:3b` y «PENDIENTE #51», pero #51 está cerrado. Ahora es una cota con las latencias de `gemma4:e4b` medidas desde el contenedor el 23/10: 36 posts × 78 s ≈ 47 min al mes, menos del 10 % de una jornada. Sigue en `B` porque es una cota, no una corrida del volumen mensual. La fila de escalabilidad cambia «4 %» por «10 %».
- **Ausencia de fallos:** citaba DEF-A1-021 como «corregido en esta foto» (era del 12/10). Ahora cita el registro hasta DEF-A1-029 y los dos defectos del paso a contenedores (028 y 029), cerrados.
- **Instalabilidad:** decía «cuatro versiones (0.5.0 a 0.5.3)». Ahora: seis versiones (0.5.0 a 0.5.5) del 23/10 al 26/10, y la 0.5.5 se desplegó sola con el scheduler corriendo.
- **Interoperabilidad del canal:** suma que el Form de pedidos no está definido y que está previsto que el scheduler lo atienda (#149).

**Perfil de seguridad** (Anexo 3):
- **Encabezado y cierre:** de 23/10 y 0.5.4 a 26/10 y 0.5.6.
- **Propiedad de los recursos (eje 5):** de `A` a `B`. Declaraba una unidad compartida por ambiente, pero los recursos de D2 (planilla, carpeta de borradores y carpeta de respaldos) son de la cuenta técnica. Mover los recursos es #100. La fila no está en la selección del Anexo 3.
- **Límite de tasa:** «4 %» pasa a «10 %», con la misma cota.

**Anexo 1** (`scripts/anexo1_presentacion.py`, archivo controlado, por eso hay versión nueva):
- **SLO:** decía «no tienen medición a la fecha (issue #88)», pero #88 está cerrado. Ahora dice que el instrumento existe, que el scheduler registra cada corrida desde el 26/10 y que todavía no hay ventana de operación para medir.
- **Forms:** suma que está previsto que el scheduler atienda el Form de pedidos (#149).

**Fuera de los anexos:**
- **ADR 0013:** nota de que la marcha en paralelo terminó (#143) y el scheduler del contenedor corre desde el 26/10.
- **Runbook del scheduler:** el estado apunta al contenedor. Las unidades `systemd` quedan como alternativa fuera de Docker.
- **Inventario:** la fila de las unidades del scheduler decía «perfil apagado». Ahora dice encendido desde el 26/10.
- **Guion de la prueba presencial:** el chequeo previo incluye `agente1-scheduler-1`. La plantilla del ensayo ya no ofrece la OAuth (#99 está cerrado) y nombra el modelo `gemma4:e4b`.

## Segunda pasada: encabezado y textos de las plantillas (versión 0.5.7)

En la revisión, Juani vio «Ciclo Lectivo 2025» en el encabezado del Anexo 1. El año viene de las plantillas 2025 y estaba en los tres Word.

- **Encabezado:** los tres anexos dicen «Ciclo Lectivo 2026» (`CICLO_LECTIVO` en `scripts/plantilla_laboratorio.py`).
- **Anexos 2 y 3:** sale la aclaración de la plantilla «(Se incluyen datos puntuales a modo de ejemplo)». La instrucción «El Equipo de Proyecto completará esta tabla…» se reemplaza por las referencias: ISO/IEC 25010, 25059 y 25012 en el Anexo 2, y NIST CSF 2.0, OWASP Top 10, OWASP Top 10 for LLM y MITRE ATT&CK en el Anexo 3. El ejemplo aprobado de 2025 hizo lo mismo en su Anexo 3.
- **Columnas de nivel y comentarios: siguen vacías a propósito.** Maiorano lo pidió por escrito el 14/10: «eso es lo que completamos nosotros al evaluar». El alumno de 2025 se había autoevaluado ahí y el laboratorio lo reescribió. Seguimos la instrucción del laboratorio.
- **Verificación:** dos tests nuevos en `tests/test_anexos_plantilla_oficial.py` (ciclo lectivo vigente en los tres; sin texto de ejemplo y con referencias en el 2 y el 3). Suite con python-docx: 2451 verdes. Ruff limpio.

## Tercera pasada: la seguridad se declara en el Anexo 1 (versión 0.5.8, publicada como 0.5.9)

Hasta la 0.5.7, cada componente del Anexo 1 tenía una fila «Seguridad · Remite» que mandaba al Anexo 3. Pero el Word del Anexo 3 sólo lleva `Componente` e `Ítem`, así que el laboratorio no veía qué estado ni qué motivo declaraba el autor para la seguridad. El ejemplo aprobado de 2025 declaraba la seguridad dentro del Anexo 1. Juani aprobó hacer lo mismo.

- **Anexo 1:** cada componente lleva los mismos ítems que lista el Anexo 3 (32, con la selección de `anexos_seleccion.py`), cada uno con su estado y su motivo tomados del perfil de seguridad. Las filas se rotulan «Seguridad (factor)». `Google Workspace` entra como componente propio después de Integraciones, sólo con sus ítems de seguridad. Ya no queda ningún «Remite».
- **El Anexo 3 no cambia:** sigue con componente e ítem. Las columnas de nivel y el comentario los completa el laboratorio.
- **Verificación:** dos tests nuevos en `tests/test_anexo1_presentacion.py`. Uno comprueba que los ítems y los estados de seguridad del Anexo 1 son exactamente los del Anexo 3; el otro, que el generador falla si un componente queda sin ítems. Suite: 2453 verdes con python-docx y 2446 sin. Ruff limpio. El Anexo 1 queda en 11 tablas y 13 páginas.
