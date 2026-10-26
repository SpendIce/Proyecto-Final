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
