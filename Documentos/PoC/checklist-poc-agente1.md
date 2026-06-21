# Checklist PoC — Agente 1 (Extensión Bot) · 1 semana

**Objetivo:** probar la función crítica (fila de datos → LLM local → borrador → validación humana → evidencia)
y dejar evidencia que sostenga **TRL 3**. Es el primer tajo hacia el MVP de julio (HU-010 + HU-011).

**Scope (cementado por el veredicto):** SOLO gacetillas (HU-010) y posts (HU-011), con Sheets/CSV, Docs,
Ollama local, prompts versionados, logs mínimos y validación humana.

**Fuera esta semana (no tocar):** FastAPI, LangGraph, automatizaciones, publicación, analítica,
certificados (HU-014), confirmaciones (HU-012), lenguaje natural (HU-013), integración A2–A5.
> Primero el camino de valor. La arquitectura linda viene después.

---

## Día 1 — Entorno local (que el modelo corra)
- [ ] Instalar Ollama en el servidor/máquina local.
- [ ] Bajar los dos modelos candidatos: `ollama pull llama3:8b` y `ollama pull mistral:7b`.
- [ ] Verificar que corre **sin GPU**: `ollama run llama3:8b` con un prompt manual cualquiera.
- [ ] Medir latencia de UNA generación (referencia objetivo del proyecto: < 30 s por pieza).
- [ ] Python 3.x + entorno virtual (`venv`). Instalar cliente (`ollama` o `requests`).
- **Listo cuando:** el modelo responde localmente a un prompt tuyo, sin nube.

## Día 2 — Datos de prueba + estructura de salida
- [ ] Crear Sheet (o CSV) con **3–5 filas** de eventos de extensión ficticios pero plausibles.
      Columnas: `titulo, fecha, lugar, descripcion, publico, organiza, contacto`.
- [ ] Definir la **estructura fija de la gacetilla** (campos, longitud, tono institucional).
- [ ] Definir la **estructura del post por canal** (Instagram y LinkedIn: tono y longitud distintos).
- [ ] Escribir **a mano** 1 golden output de gacetilla + 1 post por canal → es tu vara de calidad.
- **Listo cuando:** tenés dataset + golden outputs de referencia.

## Día 3 — Prompts versionados
- [ ] `prompts/gacetilla_v1.txt` con placeholders de las columnas.
- [ ] `prompts/post_instagram_v1.txt` y `prompts/post_linkedin_v1.txt`.
- [ ] Probar a mano con 1 fila; iterar el prompt hasta acercarte al golden (v2, v3… versionado real).
- [ ] Guardar los prompts en archivos (control de versión = evidencia de refinamiento).
- **Listo cuando:** los prompts producen salida con la estructura correcta.

## Día 4 — Script thin slice (end-to-end)
- [ ] Script Python lineal: lee 1 fila → arma prompt desde template → llama a Ollama → recibe borrador → lo guarda (archivo o Google Doc).
- [ ] **Sin FastAPI, sin LangGraph.** Script pelado.
- [ ] Log mínimo por corrida: `timestamp, id_fila, modelo, version_prompt, latencia_s, longitud_salida`.
- [ ] Correrlo sobre las 3–5 filas.
- **Listo cuando:** el script genera borradores de todas las filas de punta a punta.

## Día 5 — Validación humana + paquete de evidencia
- [ ] Checklist de validación (escala 1–4): precisión de datos, tono institucional, sin alucinaciones, longitud por canal.
- [ ] Pasar cada borrador por el checklist (hacés de revisor SEU) y registrar puntaje.
- [ ] Comparar generado vs golden output.
- [ ] Si la calidad falla: ajuste de prompt (few-shot) o cambiar de modelo (plan B, **siempre local**).
- [ ] Armar paquete de evidencia: dataset, prompts versionados, salidas generadas, logs, checklist completado, capturas.
- **Listo cuando:** la evidencia sostiene "función crítica viable = TRL 3".

## Día 6–7 — Colchón + decisión
- [ ] Buffer para lo que se atrasó (siempre se atrasa algo).
- [ ] Decidir modelo: LLaMA 3 8B vs Mistral 7B (cuál dio mejor con TUS prompts y datos).
- [ ] Escribir el **go/no-go**: ¿el MVP de julio es viable sobre esta base? ¿Qué recortarías más si no?

---

## Definición de listo (DoD) del PoC
- El script genera gacetilla + posts desde una fila real de datos, en local.
- Hay golden outputs y una comparación documentada contra lo generado.
- Hay logs mínimos y un checklist de validación humana aplicado.
- Hay un paquete de evidencia reproducible (datos, prompts, salidas, logs).
- Hay un veredicto escrito de factibilidad del MVP de julio.

## Qué NO hacer esta semana
- Nada de framework (FastAPI/LangGraph) hasta que el camino de valor esté cementado.
- Nada de publicar a redes reales ni tocar datos reales de la SEU.
- Nada de HU-012/013/014 (son S2).
- No perseguir la salida perfecta: buscás "usable + validable por humano", no producción final.
```
