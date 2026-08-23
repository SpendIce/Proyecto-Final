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
  // Ejemplo (comentado): "s0a": { done: true, at: "2026-07-06", nota: "Ollama local + script Python OK" },

  "s0a": { done: true, at: "2026-07-06", nota: "Ollama user-local restaurado, llama3.2:3b descargado (.claude/persistence.md)" },
  "s0c": { done: true, at: "2026-07-10", nota: "Esqueleto del proyecto y logging basico verificados por la suite de pruebas" },
  "m0":  { done: true, at: "2026-07-10", nota: "Entorno offline suficiente para construir el MVP. Conexion Workspace live sigue BLOQUEADO_EXTERNO (DEF-A1-001)" },

  "s1a": { done: true, at: "2026-07-15", nota: "Pipeline de gacetilla offline funcional (persistence.md: borradores offline y con Ollama local)" },

  "s2a": { done: true, at: "2026-08-07", nota: "Contrato/politicas de canal offline resueltas en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2b": { done: true, at: "2026-08-12", nota: "Prototipo de post offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },
  "s2c": { done: true, at: "2026-08-14", nota: "Control de longitud/limpieza offline resuelto en 537402a (DEF-A1-004 RESUELTO_TECNICO)" },

  // Sin marcar a proposito (evidencia no alcanza para done:true):
  // s0b  - Workspace/OAuth2 institucional: BLOQUEADO_EXTERNO (DEF-A1-001).
  // s1b-s1e, m1 - HU-010 sigue PARCIAL segun Plan-Recuperacion-MVP-Agente-1-2026-08-17.md.
  // s2d, m2 - Validacion SEU y Gate TRL 3 siguen PENDIENTE/BLOQUEADO_EXTERNO (DEF-A1-005, DEF-A1-006).
};
