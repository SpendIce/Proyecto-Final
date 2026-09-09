# Proyecto Centenario — Agente 1

Este contexto define el lenguaje compartido para planificar, desarrollar y evaluar la PPS de Juan Ignacio Goñe dentro del Proyecto Centenario de la FIE/UNDEF.

## Lenguaje

**Agente 1**:
Agente de comunicacion institucional de la Secretaria de Extension Universitaria, responsable de preparar piezas comunicacionales dentro del Proceso 4 con validacion humana obligatoria.
_Evitar_: orquestador, chatbot publico, agente de analitica

**Pieza comunicacional**:
Contenido institucional preparado para un canal y un publico determinados, como una gacetilla, un post, un correo, un newsletter o un certificado.
_Evitar_: publicacion, cuando todavia no fue validada ni difundida

**Borrador**:
Pieza comunicacional generada que no tiene autorizacion para publicarse, enviarse ni emitirse.
_Evitar_: contenido aprobado, publicacion

**Validacion humana**:
Conjunto de decisiones registradas por personas con rol institucional autorizado que habilita a una pieza a avanzar; no se infiere de la conformidad tecnica. Una pieza destinada a publicacion requiere aprobacion semantica y aprobacion utilitaria, no una sola firma.
_Evitar_: validacion automatica, aprobacion del agente, aprobacion unica

**Aprobacion semantica**:
Decision del Responsable de Gestion del Conocimiento sobre si el contenido dice lo correcto: hechos, tono y consistencia institucional.
_Evitar_: revision editorial, visto bueno

**Aprobacion utilitaria**:
Decision del Coordinador de Extension sobre si la pieza sirve para el proposito y el canal previstos.
_Evitar_: aprobacion final, aprobacion del coordinador a secas

**Canal de interaccion**:
Medio por el que una persona de la SEU le pide algo al Agente 1 y recibe la respuesta. Es independiente de la identidad con la que el agente opera contra los sistemas institucionales: recibir un pedido por un buzon no otorga los permisos de ese buzon.
_Evitar_: chat, interfaz, frontend, backend

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
