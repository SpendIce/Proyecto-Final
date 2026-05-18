# Corpus Markdown operativo — Campus

> Este directorio contiene conversiones Markdown de los PDFs de `Contenido/Campus/` que no pertenecen a `DSI1/_md` ni `DSI2/_md`.
>
> Usar estos archivos primero para busqueda con `rg` y lectura agentica. Abrir el PDF original solo cuando hagan falta diagramas, tablas, paginacion o evidencia visual exacta.

## Criterio de conversion

- Conversion directa: `pdftotext -layout` cuando el PDF expone texto embebido suficiente.
- OCR local: `pdftoppm -r 150` + `tesseract -l spa+eng --psm 6` cuando el PDF solo exponia numeracion o texto no util.
- Duplicados exactos: no se duplica el contenido; se deja un Markdown de referencia al archivo canonico.

## Mapa PDF -> Markdown

| PDF | Markdown | Metodo | Paginas | Palabras finales |
|---|---|---|---:|---:|
| `2012_019_001_495381.pdf` | `2012-019-001-495381.md` | `pdftotext -layout` | 258 | 123454 |
| `20151002-Plan-transformacion-digital-age-oopp.pdf` | `20151002-plan-transformacion-digital-age-oopp.md` | `pdftotext -layout` | 55 | 12864 |
| `503-G1326.pdf` | `503-g1326.md` | `pdftotext -layout` | 3 | 3322 |
| `65369_bierwirth hoofa antonia.pdf` | `65369-bierwirth-hoofa-antonia.md` | `pdftotext -layout` | 230 | 74851 |
| `ETICT-6.pdf` | `etict-6.md` | `pdftotext -layout` | 9 | 4789 |
| `Escenarios de Defensa/DIEEEM28-2015_Transformacion_Digital_MINISDEF_JesusG.Ruedas.pdf` | `escenarios-de-defensa/dieeem28-2015-transformacion-digital-minisdef-jesusg-ruedas.md` | `pdftotext -layout` | 39 | 12278 |
| `Escenarios de Defensa/DOD-DIGITAL-MODERNIZATION-STRATEGY-2019.PDF` | `escenarios-de-defensa/dod-digital-modernization-strategy-2019.md` | `pdftotext -layout` | 72 | 23000 |
| `Escenarios de Defensa/Manual de la Defensa.pdf` | `escenarios-de-defensa/manual-de-la-defensa.md` | referencia-duplicado | 434 | 0 |
| `Guia-Did├бctica_Modelo-Canvas-1.pdf` | `guia-didactica-modelo-canvas-1.md` | `pdftotext -layout` | 112 | 16122 |
| `Lecturas y Herramientas/2009-06-CharlaPreparaticAgil.pdf` | `lecturas-y-herramientas/2009-06-charlapreparaticagil.md` | `pdftotext -layout` | 54 | 1186 |
| `Lecturas y Herramientas/A Lightweight Incremental Effort Estimation.pdf` | `lecturas-y-herramientas/a-lightweight-incremental-effort-estimation.md` | `pdftotext -layout` | 23 | 1779 |
| `Lecturas y Herramientas/Plan SQM v1.00_ejemplo.pdf` | `lecturas-y-herramientas/plan-sqm-v1-00-ejemplo.md` | `pdftotext -layout` | 16 | 5225 |
| `Lecturas y Herramientas/UN_MODELO_DE_ESTIMACION_DE_PROYECTOS_DE_SOFTWARE.pdf` | `lecturas-y-herramientas/un-modelo-de-estimacion-de-proyectos-de-software.md` | `pdftotext -layout` | 49 | 13842 |
| `Lecturas y Herramientas/kleer-scrum-estimation-planning-es.pdf` | `lecturas-y-herramientas/kleer-scrum-estimation-planning-es.md` | `pdftotext -layout` | 61 | 12223 |
| `Lecturas y Herramientas/mtrigasTFC0612memoria.pdf` | `lecturas-y-herramientas/mtrigastfc0612memoria.md` | `pdftotext -layout` | 56 | 14805 |
| `Lecturas y Herramientas/rgraciapenTFC0613.pdf` | `lecturas-y-herramientas/rgraciapentfc0613.md` | `pdftotext -layout` | 51 | 11176 |
| `Lecturas y Herramientas/scrum_I.pdf` | `lecturas-y-herramientas/scrum-i.md` | `pdftotext -layout` | 58 | 13399 |
| `Lecturas y Herramientas/v15n3a7.pdf` | `lecturas-y-herramientas/v15n3a7.md` | `pdftotext -layout` | 16 | 11132 |
| `Lecturas y Herramientas/w186.pdf` | `lecturas-y-herramientas/w186.md` | `pdftotext -layout` | 29 | 10754 |
| `Marco Conceptual y Buenas Pr├бcticas/Consejos G.Proyectos TI.pdf` | `marco-conceptual-y-buenas-practicas/consejos-g-proyectos-ti.md` | `pdftotext -layout` | 24 | 7239 |
| `Marco Conceptual y Buenas Pr├бcticas/PMBOK-6ta Ed.pdf` | `marco-conceptual-y-buenas-practicas/pmbok-6ta-ed.md` | `pdftotext -layout` | 762 | 256395 |
| `Marco Conceptual y Buenas Pr├бcticas/benefits-focus-during-project-execution.pdf` | `marco-conceptual-y-buenas-practicas/benefits-focus-during-project-execution.md` | `pdftotext -layout` | 28 | 10040 |
| `PPS 2026 - Módulo Propedéutico - 1.pdf` | `pps-2026-modulo-propedeutico-1.md` | OCR local con `pdftoppm -r 150` + `tesseract -l spa+eng --psm 6` | 25 | 1777 |
| `PPS 2026 - Módulo Propedéutico - 2.pdf` | `pps-2026-modulo-propedeutico-2.md` | OCR local con `pdftoppm -r 150` + `tesseract -l spa+eng --psm 6` | 31 | 2745 |
| `Plantilla y Ejemplos/0a_PM_Caso de Negocio est├бndar v1.2_Gu├нa y Ejemplos.pdf` | `plantilla-y-ejemplos/0a-pm-caso-de-negocio-estandar-v1-2-guia-y-ejemplos.md` | `pdftotext -layout` | 19 | 3807 |
| `Plantilla y Ejemplos/0b_PM_Beneficios cuantificados v1.2_Casos de An├бlisis y Plantilla.pdf` | `plantilla-y-ejemplos/0b-pm-beneficios-cuantificados-v1-2-casos-de-analisis-y-plantilla.md` | `pdftotext -layout` | 3 | 458 |
| `Plantilla y Ejemplos/0c_PM_Elementos Anteproyecto v1.2_Casos de An├бlisis.pdf` | `plantilla-y-ejemplos/0c-pm-elementos-anteproyecto-v1-2-casos-de-analisis.md` | `pdftotext -layout` | 1 | 252 |
| `Plantilla y Ejemplos/1a_PM_Acta Constit Proyecto v1.2.pdf` | `plantilla-y-ejemplos/1a-pm-acta-constit-proyecto-v1-2.md` | `pdftotext -layout` | 4 | 205 |
| `Plantilla y Ejemplos/1b_Descripci├│n del Proy Mil como PID v2.1.pdf` | `plantilla-y-ejemplos/1b-descripcion-del-proy-mil-como-pid-v2-1.md` | `pdftotext -layout` | 3 | 443 |
| `Proy_Intro.pdf` | `proy-intro.md` | `pdftotext -layout` | 12 | 184 |
| `Proyecto PyS_1-3.pdf` | `proyecto-pys-1-3.md` | `pdftotext -layout` | 11 | 594 |
| `Proyecto PyS_4a.pdf` | `proyecto-pys-4a.md` | `pdftotext -layout` | 23 | 754 |
| `Proyecto PyS_4b-1.pdf` | `proyecto-pys-4b-1.md` | `pdftotext -layout` | 22 | 693 |
| `Proyecto PyS_4b-2.pdf` | `proyecto-pys-4b-2.md` | `pdftotext -layout` | 41 | 3811 |
| `Proyecto PyS_4c.pdf` | `proyecto-pys-4c.md` | `pdftotext -layout` | 14 | 873 |
| `Proyectos Defensa Nacional/3 Arbol de problemas FINAL v 1-3.pdf` | `proyectos-defensa-nacional/3-arbol-de-problemas-final-v-1-3.md` | `pdftotext -layout` | 1 | 148 |
| `Proyectos Defensa Nacional/4 Arbol de Objetivos FINAL v 1-3.pdf` | `proyectos-defensa-nacional/4-arbol-de-objetivos-final-v-1-3.md` | `pdftotext -layout` | 1 | 223 |
| `Proyectos Defensa Nacional/5 Matriz de Marco L├│gico v 1-4.pdf` | `proyectos-defensa-nacional/5-matriz-de-marco-logico-v-1-4.md` | `pdftotext -layout` | 5 | 601 |
| `Proyectos Defensa Nacional/Descripci├│n del Proy Mil como PID v.2.0.pdf` | `proyectos-defensa-nacional/descripcion-del-proy-mil-como-pid-v-2-0.md` | `pdftotext -layout` | 3 | 407 |
| `Proyectos Defensa Nacional/Manual de la Defensa.pdf` | `proyectos-defensa-nacional/manual-de-la-defensa.md` | `pdftotext -layout` | 434 | 131495 |
| `Trabajo2.5.pdf` | `trabajo2-5.md` | `pdftotext -layout` | 20 | 7879 |
| `babypmi-pgba-spanish-translation-full.pdf` | `babypmi-pgba-spanish-translation-full.md` | `pdftotext -layout` | 26 | 10406 |
| `c├│mo-escribir-un-caso-de-negocio-eficaz---luis-reyes.pdf` | `como-escribir-un-caso-de-negocio-eficaz-luis-reyes.md` | `pdftotext -layout` | 31 | 1900 |
| `nistspecialpublication800-144.pdf` | `nistspecialpublication800-144.md` | `pdftotext -layout` | 80 | 33337 |
| `nistspecialpublication800-145.pdf` | `nistspecialpublication800-145.md` | `pdftotext -layout` | 7 | 1584 |
