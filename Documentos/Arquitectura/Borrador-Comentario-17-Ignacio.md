Hola Ignacio:

Para la presentación de avance del miércoles 21/10 armé una propuesta de arquitectura multiagente P100 en tres capas. La idea no es reemplazar la definición conjunta ni la bible, sino llegar a una vista común para mostrar lo mismo.

- **Capa 1, lo compartido hoy con evidencia:** la pestaña de insumos de agentes en D2 como punto de entrada (ADR 0008), el contrato `/v1` con Historia Viva (rc2, probado contra el mock 57/57), la identidad Workspace por cuenta de servicio de DSI (ADR 0011), el servidor de la facultad con Ollama como host de la demo y el control de cambios con manifest fail-closed (ADR 0010).
- **Capa 2, lo proyectado por la bible con condición de entrada:** Apps Script, Celery + Redis, FastAPI, LangChain/LlamaIndex y Docker. LangGraph no está en la bible: entra por la cursada y el anteproyecto, y lo presento como runtime futuro, no en uso.
- **Capa 3, la frontera de A1:** consume insumos de A3-A5, Historia Viva y la planilla D2; produce borradores, decisiones por Form y aportes a Historia Viva; no orquesta a los otros agentes.

El documento completo y el diagrama están en `Documentos/Arquitectura/` (los subo al repo en el próximo push). Dos puntos donde me interesa tu devolución: el contrato `/v1` quedó en rc2 y la instancia real la probamos el 27/10; y si tu vista de la capa 2 difiere, mejor mostrar la tuya o consensuar una.

¿Llegás a mirarlo antes del miércoles a la mañana? Si no, mostramos esta versión y después la ajustamos con lo que me marques.

Gracias,
Juani
