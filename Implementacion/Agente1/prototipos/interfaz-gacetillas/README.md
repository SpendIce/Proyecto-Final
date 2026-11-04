# Prototipo del recorrido de gacetillas de A1

Construido el 03/11/2026. Actualizado el 04/11 por pedido de Juani: actividades reales, ajuste en texto libre y generación real en el servidor. Responsable técnico: Juan Ignacio Goñe.

Pregunta: ¿qué disposición facilita pedir, revisar, corregir y decidir sobre una gacetilla, y qué calidad tiene el contenido producido por el LLM?

## Dos formas de abrirlo

**Servicio interno en la facultad:** usar la URL comunicada en la sesión. El host y su dirección se consultan por la configuración operativa fuera del repositorio; no se versionan aquí. El puerto del prototipo es 8092. La interfaz y su API corren juntas en un contenedor separado del stack oficial; el navegador llama a su mismo origen y el backend accede a Ollama por loopback mediante el relay existente. No se expone Ollama a la red de usuarios.

**Archivo local:** abrir `prototipo.html`. Permite recorrer la interfaz con datos precargados, sin LLM. No confundir este modo con la URL HTTP del servicio real.

```bash
xdg-open Implementacion/Agente1/prototipos/interfaz-gacetillas/prototipo.html
```

Las variantes se eligen con la barra inferior, las flechas del teclado fuera de los campos o `?variant=A`, `?variant=B`, `?variant=C`:

- **A — Bandeja y pieza:** lista compartida junto al documento.
- **B — Recorrido por pasos:** bandeja en filas, documento centrado y etapas visibles.
- **C — Documento y acciones:** bandeja en tarjetas, documento amplio y acciones al costado.

Cambiar de variante conserva el estado en memoria; recargar reinicia el estado del navegador. La rama descartable `prototype/interfaz-a1-gacetillas-2026-11-03` captura el experimento. No es el adapter web productivo ni se promueve directamente a main.

## Actividades y procedencia

La bandeja y el selector de difusión contienen las ocho actividades de `data/corpus-fie-informa-difusiones.csv` y NotebookLM Nivel 2. Geomática aparece primero porque fue el caso de la demostración y del ensayo del laboratorio. Los asuntos, datos visibles y textos precargados cambian con la actividad seleccionada.

El corpus corresponde al set usado en las mediciones: las procedencias por campo de `data/corpus-fie-informa-difusiones.procedencia.csv` distinguen flyer, provisional y no informado. Los datos provisionales se identifican en la interfaz; las fechas son las de las fuentes de prueba de 2026, no una agenda actualizada. Ningún campo ausente se completa por inferencia.

NotebookLM se transcribe desde `Adjuntos/Actividades-Extension/NotebookLM-Nivel-2/registro-actividad-candidato.json`, aplicando las precisiones documentadas de la visita SEU del 19/10 en `Documentos/PoC/Registro-Actividades-Fuentes-Documentales-v1.md`: año 2026, modalidad virtual tutorada asincrónica y 24 horas. Se conserva el organizador sin informar. **El contrato vigente bloquea su generación mientras falte ese dato**, en lugar de inventarlo. No se reutiliza para ese caso el contacto ficticio ni la descripción de `actividades_notebooklm_n2_sinteticas.csv`.

Los datos del backend viven en `datos-prototipo.json`; los snapshots del HTML y este JSON parten de las mismas fuentes y hashes. La API recibe el identificador de actividad y vuelve a resolver los datos de su catálogo: no acepta una fila institucional arbitraria enviada por el navegador.

Los otros seis tipos conservan casos estáticos de `golden/formas/<tipo>.md`; no se los presenta como llamadas al LLM. Tipos y áreas provienen de los contratos provisionales existentes. La difusión real usa el pie fijo declarado para su tipo; no puede generarse con una firma de otra área elegida por error.

## Generación, edición y ajuste

En la URL del servicio, **Generar con LLM** o un nuevo pedido de difusión llama a `gemma4:e4b` en el Ollama existente. Se mantienen temperatura 0, `think=false`, presupuesto de 512 tokens y timeout de 300 segundos. Se reutilizan el prompt `gacetilla_v8`, los controles de ficha y el renderer del núcleo desplegado. El adapter y la extensión de prompt para indicaciones/ajustes son experimentales.

La aceptación HTTP devuelve un identificador de trabajo; la interfaz consulta el estado en segundo plano. El ejecutor admite una generación a la vez y hasta ocho trabajos activos/en espera. Se identifica cada pedido HTTP para no duplicarlo al repetir una misma solicitud. Una consulta interrumpida puede continuarse sobre el mismo trabajo. Este mecanismo en memoria no satisface persistencia ni recuperación del canal real.

El texto precargado se identifica como composición local de datos, no como salida del LLM. Una generación conforme crea otra revisión y registra modelo, prompt, latencia, configuración, hashes y resultado mecánico. Una salida no conforme queda diagnosticable y no se incorpora como borrador aprobable. Un fallo de conexión no se sustituye por un ejemplo estático.

**Pedir ajuste** ofrece un campo de texto libre. El backend recibe la solicitud y la captura de la última revisión, incluidas las correcciones humanas, junto con los datos autorizados. La revisión funciona como base editorial, sin reemplazar a la fuente institucional. El resultado se valida y crea otra revisión; se conservan las anteriores. La segunda versión del ensayo pide no trasladar oraciones del cuerpo a la bajada. Cuando el pedido indica acortar la bajada, compara su cantidad de palabras con la captura base y rechaza un resultado que no sea más breve; es un control experimental de cumplimiento de ese pedido, no una nueva regla institucional de extensión. La extensión de prompt se identifica como `prototipo_ajuste_v2`; no implica que el núcleo oficial ya implemente ajustes.

La edición manual sigue abriendo un **editor local simulado en otra pestaña**. No es Google Docs. Guardar y volver incorpora una captura humana nueva. El ajuste real se prueba sobre esa captura. Mientras se edita o se genera, el pedido bloquea acciones incompatibles; una revisión anterior tampoco admite decisión.

En modo de archivo local, el ajuste libre queda pendiente. Quien guía puede incorporar una respuesta de prueba desde el panel de estado; ese control no aparece como respuesta real del agente.

## Calidad de contenido y evidencia

Los controles automáticos verifican el contrato y hechos mecanizables. **Un resultado CONFORME no demuestra calidad editorial ni validación institucional.** La vista ofrece **Evaluar contenido** de manera separada de aprobar/descartar, con la escala y las tres dimensiones del instrumento vigente:

- parecido a FIE INFORMA;
- fidelidad de sentido frente a la fuente;
- claridad y uso.

Se puede dejar cada dimensión sin puntuar; no se precargan notas. La evaluación se vincula a la revisión concreta y admite observaciones. El instrumento completo y sus anclas están en `evidencias/set-evaluacion-gacetillas-fie-informa-2026-10-14.md`. Corresponde al eje 1 en tipos que generan; no se aplica una puntuación de prosa a la composición determinista de otros tipos.

**Descargar evidencia** exporta las revisiones, resultados del LLM, configuración, fuentes y evaluación introducida por la persona. Es un archivo de prueba, con identidad institucional no verificada. No produce una aceptación SEU ni reemplaza su acta. Se conserva separado el resultado de usabilidad del juicio sobre contenido.

El trabajo transitorio vive en memoria del servidor y del navegador, sin escribir prosa en logs. Los trabajos terminados de más de una hora se eliminan al admitir un pedido posterior; un reinicio pierde esos trabajos. Sólo una descarga explícita conserva la evidencia para quien revisa. La retención del canal productivo sigue pendiente de su decisión técnica.

## Despliegue del ensayo

El contenedor `agente1-prototipo-interfaz-20261104` usa la misma imagen fijada por digest que la consola oficial. Ejecuta el entrypoint existente para verificar integridad y abrir el relay, seguido de `python /prototype/servidor.py --host 0.0.0.0 --port 8080`. Monta sólo esta carpeta en lectura, sin env file de Workspace ni credenciales de Drive/Gmail. Usa uid sin privilegios, raíz de sólo lectura, capacidades eliminadas y estado efímero en `/tmp`.

Comparte la red interna del modelo y publica el puerto 8080 del contenedor como 8092 en la interfaz privada del host. El acceso está limitado por la red disponible de la facultad. No se configuró DNS, HTTPS ni login Google para esta demostración; la pantalla identifica el acceso institucional como simulado. La configuración de IP y los accesos administrativos quedan fuera del repo.

El archivo `servidor.py` puede ejecutarse localmente con Python del proyecto y un Ollama ya accesible en loopback. En el despliegue de este ensayo el relay corre dentro del contenedor; el host no expone ese puerto:

```bash
python Implementacion/Agente1/prototipos/interfaz-gacetillas/servidor.py --port 8092
```

La operación oficial de consola/scheduler y su mecanismo de corte y despliegue por tags mantienen su circuito. Este contenedor está identificado expresamente como ensayo descartable; no es una nueva versión oficial de A1. Para detenerlo se usa su contenedor específico en Portainer, sin detener los servicios del stack oficial.

## Reacción humana y continuidad

El 04/11 Juani pidió actividades reales, corrigió la limitación artificial del ajuste a opciones predefinidas y solicitó probar la generación/calidad con el LLM del servidor y una URL interna. Esos pedidos se incorporan a este ensayo. **Elección o combinación de variantes: pendiente. Evaluación humana de los textos nuevos: pendiente. Prueba SEU: pendiente.**

La prueba guiada debe observar: continuar un pedido ajeno, elegir actividad, reconocer datos provisionales/faltantes, generar, editar aparte, pedir un ajuste libre, reconocer la revisión nueva, consultar historial y aprobar/descartar. Por tarea se registran resultado, ayuda, errores, cambios de contexto, tiempo observado y comentario, sin metas nuevas. La calidad se registra con su instrumento separado.

Diseño: `Documentos/Arquitectura/Interfaz-Web-Agente-1-PPS-Juan-Ignacio-Gone.md`, ADR 0014 y `CONTEXT.md`. Trazabilidad: P4, HU-013 como canal, HU-010 como primer recorrido. Responsable técnico: Juani; validación institucional: SEU. El experimento no acredita DoD del canal real, login, permisos, recuperación, publicación ni avance TRL.

Seguimiento: [Prototipar el recorrido de gacetillas de A1 para revisar interfaz y contenido con SEU](https://github.com/SpendIce/Proyecto-Final/issues/152); implementación posterior en los tickets existentes de base web y revisión/Docs/aprobación. El resultado y las piezas de las comprobaciones live se documentan en esta carpeta al completar la corrida; no se asignan puntajes humanos automáticamente.
