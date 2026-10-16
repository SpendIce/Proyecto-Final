# Evaluación del Proyecto: Presentación

Anexo 1 de la revisión de laboratorio (iLab/rLab). Documento generado por `Implementacion/Agente1/scripts/anexo1_presentacion.py`.

Vista de trabajo del anexo: declara una **selección** de hasta 3 atributos por componente (`scripts/anexos_seleccion.py`). El perfil completo, con todo lo evaluado, queda en `Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`.

## Título del Proyecto

Proyecto Centenario, Agente 1: Extensión Bot para la Secretaría de Extensión Universitaria de la FIE (Facultad de Ingeniería del Ejército, Universidad de la Defensa Nacional)

## Concepto General del Proyecto

*(abstract)*

El Agente 1 (Extensión Bot) es el agente de comunicación institucional del Proyecto Centenario (P100) de la Facultad de Ingeniería del Ejército (FIE), Universidad de la Defensa Nacional. Prepara piezas comunicacionales para la Secretaría de Extensión Universitaria (SEU) dentro del Proceso 4: gacetillas, publicaciones para redes sociales, correos y confirmaciones, y certificados. Su producto es siempre un borrador: el agente no publica, no difunde ni decide; toda pieza que llega a un destinatario o a una publicación pasó por una validación humana registrada, y cada salida queda marcada como pendiente de validación.

El proyecto se desarrolla a lo largo de un año académico (dos semestres de 2026) con maduración progresiva por niveles TRL: el objetivo del primer semestre es TRL 3 y el del segundo, TRL 4, en ambos casos sujeto a la decisión del gate correspondiente. Se ejecuta sobre tecnologías de código abierto y sobre la suite institucional Google Workspace; los modelos de lenguaje corren localmente (Ollama) como medida de diseño para preservar la soberanía de los datos institucionales. La estimación de costos del año de alcance se ubica en el rango de USD 0 a USD 1.400, según se utilicen o no componentes opcionales de infraestructura, respaldo o contingencia.

Este documento es el Anexo 1 de la revisión de laboratorio: presenta el sistema de demostración (el Agente 1 en todo su alcance declarado, funcionando de punta a punta en vivo) y su perfil de calidad por estrato. El detalle por atributo, en el orden del estándar, está en el Anexo 2; el perfil de seguridad, en el Anexo 3.

## Enfoque del proyecto

- **Enfoque iterativo-incremental con gates por semestre.** El proyecto sigue los cinco pasos metodológicos del Director del Proyecto (relevamiento, diseño, prototipado, validación y documentación) y se gestiona con un tablero Kanban. Cada semestre cierra en un gate de evaluación TRL con su paquete de evidencia; ningún gate se declara cerrado sólo por documentación narrativa ni por demostración informal.
- **Validación humana obligatoria.** El mecanismo es estructural y no puede deshabilitarse sin modificar el código: las piezas de difusión (gacetillas y posts) requieren la decisión de publicación registrada por quien publica o descarta el borrador; las piezas que el agente envía o emite (confirmaciones y certificados) requieren la plantilla aprobada más la aprobación de lote previa al envío.
- **Ejecución local y fail-closed.** Los modelos corren en infraestructura propia y el agente falla cerrado en cada frontera: lo que no cumple se rechaza antes de generar, escribir o tocar el registro. La auditoría guarda códigos, conteos y hashes, nunca contenido ni datos personales en claro.
- **Sistema de demostración sin capacidades detenidas.** El sistema corre en la laptop del autor con modelo local y sobre Google Workspace D2 con la cuenta técnica. Lo que depende de un tercero (plantillas, firmas, política de redes, identidad del personal, host D3) corre contra un destino de prueba o un insumo provisional declarado, por el mismo mecanismo productivo y nunca contra un fake, con la meta de conseguir el original.
- **Alcance acotado y excluido.** El agente se limita a la comunicación institucional del Proceso 4 y a las historias HU-010 a HU-014. Queda fuera el reemplazo de personal, la publicación o el envío sin validación humana, la analítica y el scraping, la atención masiva al público, la infraestructura de alto costo y toda integración externa compleja no definida.

## Estado de las capacidades contra el gate TRL 4

Este anexo declara el estado de las capacidades contra el **gate TRL 4**. Las cifras y los estados de las tablas por estrato son los de la foto declarada (commit de base `98be859`, 12/10/2026). La nota sobre fechas y estado verificado del anteproyecto conserva el corte del 21/09/2026; cuando uno y otro citan un número, corresponde a su propia fecha, y la revisión de laboratorio evalúa la foto de este anexo.

**Demostrado sobre el sistema de demostración.** La corrida live del 28/09/2026 quedó verificada con smoke de lectura, casos negativos y un extremo a extremo de gacetilla cuyo borrador real quedó en la carpeta autorizada, sin modificar nada existente. HU-010 a HU-014 están implementadas dentro del alcance declarado (gacetilla, post, plantilla de correo por actividad y certificado con línea descriptiva y circuito de lote), la suite y las matrices por historia las ejercitan, y cada fila A o B de las tablas por estrato cita su evidencia versionada y su paso en vivo.

**No demostrado.**

- La validación de calidad por referentes de la SEU: la operabilidad, la reconocibilidad de la adecuación y la prueba guiada de HU-013 están previstas y su validación registrada sigue pendiente (issue #56; la prueba guiada con una persona real de la SEU no se concretó).
- La ejecución live de los canales y del registro de decisiones como paso de la revisión: la evidencia versionada es offline y las corridas live se declaran como paso.
- La operación sobre el host D3: no hay ejecución live porque el host todavía no llegó (DEF-A1-001 parcial).
- Los niveles verificados de los SLO (disponibilidad, latencia por pieza, utilización de recursos, tiempo de atención y aprobación a envío) no tienen medición a la fecha (issues #50, #51 y #88); el perfil declara la ausencia en lugar de un número.
- El criterio formal del gate: la Dirección de carrera no fijó un criterio formal, la evidencia se presenta contra el TRL 4 de la documentación del P100 y el go/no-go lo fija el informe del laboratorio.

**Brecha técnica abierta de HU-011.** El contrato creativo de redacción libre para los posts todavía no supera el control de contenido: el gate detecta hechos de la fuente filtrados al texto creativo y registro lingüístico no rioplatense, de modo que la variedad comunicacional depende de criterios editoriales que la SEU aún no definió. El nivel medido de conformidad al gate en redacción libre es de 1/6 con `llama3.2:3b` y 4/6 con `llama3.1:8b` (23/09/2026); el incumplimiento residual es de obediencia del modelo, lo contienen el gate fail-closed y la validación humana obligatoria, y la medición se refresca con el modelo definitivo (issue #51).

**El gate no está cerrado.** Este anexo declara estados por atributo, no el cierre del gate. El gate TRL 4 se acredita con el informe de la revisión de laboratorio, que habilita, habilita con condiciones o no habilita la presentación de cursada del 18 de noviembre de 2026. Hasta ese informe, este anexo no declara TRL 4 alcanzado.

## Esquema general de los componentes del sistema y perfil de calidad de cada uno de ellos

El perfil se declara por **estrato**, la capa del inventario de componentes sobre la que se lee el perfil de calidad. `Sistema` agrupa los atributos transversales que ninguna capa ejerce sola. El orden de los estratos es el del inventario:

- **Canal:** Transporta pedidos de la SEU hacia el agente y resultados hacia la persona. No es una conversación abierta y no verifica identidad: la identidad llega afirmada por el canal y el rol sale de un padrón externo.
- **Interpretación:** Clasifica la solicitud a una intención de un catálogo cerrado (o la rechaza) y resuelve la actividad por identificador, por búsqueda difusa determinística o por repregunta; nunca aproxima a la intención más parecida.
- **Generación:** Produce las piezas como borrador (gacetilla, post, plantilla de correo por actividad y certificado con línea descriptiva) con gate mecánico de salida antes de escribir.
- **Gates:** Controles fail-closed que deciden antes de generar, escribir o tocar el registro: política de redes, catálogo cerrado de tipos de notificación y matriz de orígenes de inscripción.
- **Control de pagos:** Deriva la situación de pago de cada preinscripto desde las fuentes en cada corrida, como función pura sin estado propio, y planifica el lote de recordatorios y los candidatos a confirmación de inscripción.
- **Aprobación:** Registra la validación humana: aprobaciones semántica y utilitaria por actividad, aprobación de lote y decisión de publicación, con identidad verificada por Google y rol tomado de un padrón.
- **Cola y envío:** Encola y entrega lo aprobado con idempotencia durable, reconciliación de reservas colgadas a envío indeterminado y retención acotada del registro; el único envío automático es la confirmación de inscripción.
- **Persistencia y auditoría:** Audita y opera las evidencias del sistema: invariantes de seguridad sobre manifiestos sanitizados, contratos operativos fail-closed y medición del nivel verificado de los SLO. Expone códigos, conteos y hashes, nunca contenido ni destinatarios.
- **Integraciones:** Fuentes, destinos y servicios externos detrás de puertos: planilla de actividades, Docs y Drive, Gmail (envío y buzón propio), Google Forms, Ollama local y los insumos de los agentes A3 a A5.
- **Sistema (atributos transversales):** Atributos transversales que ninguna capa ejerce sola: ausencia de fallos, disponibilidad, operabilidad, mantenibilidad, instalabilidad y los atributos de calidad de datos que dependen del dueño funcional.

## Detalle de atributos de calidad por componente

Las tablas de este anexo se derivan de la tabla fuente del perfil de calidad del sistema de demostración (`Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`), la misma que alimenta el Anexo 2: foto del inventario de componentes en el commit de base `98be859` (12/10/2026). El perfil de seguridad no se declara acá: cada estrato remite al Anexo 3.

Atributos tenidos en cuenta en cada componente, con el estado de implementación declarado por el autor y su motivo. La escala de estados es la de la revisión de laboratorio: A implementado satisfactoriamente, B implementado con observaciones, C tenido en cuenta sin implementar y D desconocido o ignorado expresamente (D lo asigna el laboratorio). Los factores de (ciber)seguridad de cada estrato se declaran en el Anexo 3.

### Canal

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Capacidad de interacción | Protección contra errores del usuario | A | El canal nunca decide por la persona: identificador inexistente o ambiguo produce repregunta con candidatas e identificadores, nunca una elección silenciosa; pedido vacío o fuera de catálogo se rechaza; una fila con identidad incompleta se omite; rol no habilitado queda rechazado y registrado |
| Capacidad de interacción | Transparencia (25059) | A | La prosa del pedido no se persiste en claro: ni en el registro de atendidos, ni en el aviso, ni en el link de repregunta |
| Fiabilidad | Robustez (25059) | A | La prosa externa es dato, nunca instrucción: un intento de inyección produce una intención válida o un rechazo y no llega al prompt del generador; un registro corrupto frena la lectura |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Interpretación

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Adecuación funcional | Pertinencia funcional | A | El catálogo declara exactamente las operaciones del alcance (gacetilla, post, plantilla por actividad, emisión de certificados, ajuste, newsletter, mail); cualquier otra solicitud termina `INVALIDA` o `RECHAZADA` |
| Fiabilidad | Robustez (25059) | A | La salida del modelo en el fallback es un contrato acotado: una salida manipulada no puede producir una intención inexistente; la que no cumple el contrato se descarta; una falla del intérprete no propaga excepción |
| Capacidad de interacción | Transparencia (25059) | A | El registro de interacciones conserva sólo el derivado estructurado; la interacción pendiente guarda lo que produjo el agente, nunca prosa del pedido |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Generación

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Adecuación funcional | Completitud funcional | A | HU-010 a HU-014 implementadas dentro del alcance declarado: gacetilla, post (v2 y v3), plantilla de correo por actividad y certificado con línea descriptiva y circuito de lote; los insumos provisionales se declaran y no bajan el estado |
| Adecuación funcional | Corrección del contenido generado (25059) | B | Nivel verificado de conformidad al gate: HU-010 con 6/6 borradores conformes (corte del 08/09); HU-011 v3 con redacción libre: 1/6 con `llama3.2:3b` y 4/6 con `llama3.1:8b` (23/09). El incumplimiento residual es de obediencia del modelo y lo contiene el gate fail-closed más la validación humana obligatoria. PENDIENTE #51: el modelo definitivo refresca la medición |
| Fiabilidad | Robustez (25059) | A | El gate descarta la salida entera ante cualquier incumplimiento verificable: variable faltante, desconocida o renombrada, dígito, fecha, importe, correo o enlace escritos por el modelo, hecho copiado de la fuente, dato personal, eco de prompting, promesa prohibida, salida truncada o registro no rioplatense |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Gates

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Adecuación funcional | Corrección del sistema | A | Integridad del gate (SLO del 100 %): ninguna pieza no conforme se presenta como conforme; cada regla tiene código y caso negativo; el catálogo de tipos de notificación es cerrado; un origen `DESCONOCIDO` bloquea el envío |
| Capacidad de interacción | Controlabilidad (25059) | A | Nada habilita a ciegas: un tipo fuera del catálogo es `INVALIDA`, un origen no permitido bloquea el envío y una regla `NO_MECANIZABLE` no se aplica ni se declara cumplida |
| Fiabilidad | Robustez (25059) | A | Una política con regla inválida o desconocida se rechaza al cargar; el estado `NO_MECANIZABLE` no puede marcarse como conforme |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Control de pagos

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Adecuación funcional | Corrección del sistema | A | La situación de pago se deriva de las fuentes en cada corrida, como función pura sin estado propio (ADR 0003); un comprobante presentado nunca cuenta como pago confirmado (D1/D9); una respuesta de baja no asociada se informa sin interpretar su contenido |
| Fiabilidad | Tolerancia a fallos | A | Una fuente inválida (encabezado distinto, columna faltante, fila desalineada) se rechaza entera; un buzón inexistente termina con código controlado; los adjuntos se hashean en memoria |
| Calidad de datos (25012) | Exactitud sintáctica | A | Contratos versionados con encabezado exacto (`plan_pagos_actividad_v1`, `novedades_pago_v1`, `tipos_notificacion_v2`, `matriz_origenes_inscripcion_v1`); la lista de cierre usa seis columnas posicionales con `condicion` de catálogo cerrado |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Aprobación

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Capacidad de interacción | Controlabilidad (25059) | A | Doble aprobación obligatoria (semántica más utilitaria) por catálogo cerrado de tipo y decisión por rol; un objeto de decisión sólo vale si fue declarado pendiente; registrar una decisión no dispara ninguna acción |
| Capacidad de interacción | Intervenibilidad (25059) | A | La persona puede aprobar, descartar o dejar pendiente; editar la lista de cierre o la plantilla cambia el `sha256` del objeto y la aprobación previa deja de aplicar; `manual_only` ante una ejecución cortada exige decisión humana |
| Capacidad de interacción | Transparencia (25059) | A | Las decisiones quedan en el append-only `decisiones-procesadas.jsonl` con identidad hasheada y fecha con zona horaria; el correo verificado no queda en claro |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Cola y envío

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Fiabilidad | Tolerancia a fallos | A | Reserva intermedia con reconciliación: una reserva colgada pasa a `ENVIO_INDETERMINADO` sin reenviar; la idempotencia por clave absorbe re-corridas (`DUPLICADA`); un destinatario fuera de la lista de prueba se rechaza sin reintento |
| Fiabilidad | Recuperabilidad | B | Idempotencia durable verificada: el registro archivo-por-clave sobrevive reinicio y una reserva colgada se reconcilia sin reenviar. Los SLO de RPO (menor o igual a un día hábil) y RTO (una jornada siguiendo el manual) quedan previstos del respaldo diario (ADR 0009, implementación #86) sin nivel verificado a la fecha: la medición es #88. PENDIENTE #86, #88 |
| Adecuación funcional | Corrección del sistema | A | La doble aprobación es requisito de la máquina de estados (DEF-A1-016): sin las dos decisiones no hay encolado; `ENVIO_INDETERMINADO` nunca reenvía sin cruzar con Enviados |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Persistencia y auditoría

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Capacidad de interacción | Transparencia (25059) | A | Manifest sanitizado por ejecución; auditorías y reportes exponen sólo códigos, conteos y hashes; la auditoría no copia destinatarios ni cuerpos |
| Calidad de datos (25012) | Trazabilidad | A | Cada ejecución lleva correlation id; la lista de cierre y los objetos de decisión se anclan por `sha256`; el plan de pago declara procedencia por dato; los logs no guardan contenido ni correos en claro |
| Fiabilidad | Tolerancia a fallos | A | Un registro corrupto se trata como ausente y no habilita entrega; un JSONL corrupto interrumpe la lectura en fail-closed; una clave que no es un hash no elige dónde se escribe |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Integraciones

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Compatibilidad | Interoperabilidad | A/B/C | Workspace D2 verificado live el 28/09 (parte `A`): smoke de lectura, negativos y E2E de gacetilla con Doc real `BORRADOR — NO PUBLICAR` en la carpeta autorizada, sin tocar nada existente. Insumos de A3 por productor provisional declarado (parte `B`). Seam de A2 offline sin transporte ni contrato cerrado y A4/A5 con sólo contrato candidato (parte `C`, previstas). La provisión D3 sigue abierta |
| Fiabilidad | Robustez (25059) | A | Un token inválido o con inyección en encabezado se rechaza sin tocar la red; respuestas inválidas o sobredimensionadas se rechazan; los errores HTTP se mapean sin filtrar token ni cuerpo; los adjuntos se hashean en memoria |
| Calidad de datos (25012) | Consistencia | A | La misma interpretación posicional en CSV y Sheets produce estructuras de dominio idénticas: plan, padrón y novedades coinciden entre las dos fuentes |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

### Sistema (atributos transversales)

| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |
|---|---|---|---|
| Mantenibilidad | Modularidad | A | Puertos y adapters en cada frontera (canal, fuente, destino, buzón, generador, registro, decisiones); el seam de interpretación es independiente del transporte |
| Mantenibilidad | Analizabilidad | B | Docstrings de decisión por módulo y la tabla de decisiones del README permiten localizar cada regla; falta linter y análisis estático: esa parte queda prevista y requerida, la cubre #90. PENDIENTE #90 |
| Flexibilidad | Instalabilidad | B | Paquete con `pyproject.toml` y `uv.lock` que instala y corre en la laptop del autor vía `uv`; la instalación por un tercero (responsable de operación tras el traspaso) está prevista para diciembre-febrero |
| Seguridad | Factores de (ciber)seguridad del estrato | Remite | El perfil de seguridad de este estrato se declara en el Anexo 3 del laboratorio (perfil de seguridad del sistema de demostración, issues #58 y #108); este anexo lo remite y no lo reescribe. |

## Lista de Control

*(Versión inicial prevista; se podrán agregar los puntos a considerar que el laboratorio estime convenientes.)*

- Correr la suite completa (`uv run pytest -q`) y ver las matrices reproducibles por historia de usuario (`scripts/matriz_hu010.py`, `scripts/matriz_hu011_v2.py`, `scripts/matriz_hu012.py`, `scripts/matriz_hu014.py`). Evidencia: `tests/` y `evidencias/` del Agente 1.
- Recorrer el canal con un pedido ambiguo y ver la repregunta con candidatas sin persistir la prosa del pedido. Evidencia: `src/agente1/canal_form.py`, `src/agente1/interpretacion.py`; `tests/test_canal_form.py`, `tests/test_interpretacion.py`.
- Verificar el gate de generación sobre los casos adversariales: variable fuera de catálogo, dígito, fecha, importe, correo, enlace o hecho escritos por el modelo, eco de prompting y salida truncada. Evidencia: `src/agente1/procesamiento.py`, `src/agente1/politica_redes.py`; `tests/test_plantillas_actividad.py`, `tests/test_posts.py`, `tests/test_linea_descriptiva.py`, `tests/test_procesar_gacetilla.py`.
- Verificar la doble aprobación (semántica y utilitaria) y la aprobación de lote: sin las dos decisiones no hay encolado ni emisión, y editar la lista de cierre o la plantilla cambia el objeto y la aprobación previa deja de aplicar. Evidencia: `src/agente1/confirmaciones.py`, `src/agente1/linea_descriptiva.py`; `tests/test_confirmaciones.py`, `tests/test_linea_descriptiva.py`.
- Verificar la idempotencia durable y la reconciliación: una reserva colgada pasa a envío indeterminado sin reenviar y una re-corrida termina duplicada. Evidencia: `src/agente1/confirmaciones.py`; `tests/test_confirmaciones_durables.py`; `evidencias/recuperacion-hu012-idempotencia-durable-2026-09-08.md`.
- Verificar que la auditoría y los reportes exponen sólo códigos, conteos y hashes, sin destinatarios ni cuerpos. Evidencia: `src/agente1/auditoria_d2.py`, `src/agente1/operaciones_seguras.py`; `tests/test_auditoria_seguridad_d2.py`, `tests/test_operaciones_seguras.py`.
- Verificar los límites de escritura: escribir es siempre crear nuevo y el envío por Gmail opera cercado por la lista de prueba, con rechazo antes de tocar token o red. Evidencia: `src/agente1/destinos.py`, `src/agente1/gmail_envio.py`; `tests/test_destinos.py`, `tests/test_gmail_envio.py`.
- Verificar los insumos provisionales declarados: el sistema corre con ellos por el mecanismo productivo y ninguno queda como fake ni como capacidad detenida. Evidencia: el inventario de componentes del sistema de demostración (issue #67) y la columna Estado de los dos perfiles.
- Contrastar los estados declarados por estrato en este anexo con la proyección del Anexo 2 y con la del Anexo 3, de las que salen los ítems que evalúa el laboratorio. Evidencia: `Documentos/Laboratorio/Anexo2-Calidad-Proyeccion-v1.md`, `Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`.
