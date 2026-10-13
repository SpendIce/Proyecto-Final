# RESULTADO del contrato /v1

| Campo | Valor |
| --- | --- |
| Veredicto | PASA |
| Versión | 1.1.0-rc1 |
| Huella | `2af852e591ede5701adf7599be69d992fe6112d55fc44459e71feab9f8c60d7b` (coincide con CONGELADO.sha256) |
| Mock | Prism 5.16.0 con docker en http://127.0.0.1:4010 |
| Escenarios | 57/57 OK (22 pendientes de C48) |
| Cliente del Agente 1 | OK, código de salida 0 en 1.0 s |
| Fecha | 2026-10-13T13:59:01.364Z |
| Equipo | linux x64, Node v26.7.0 |

## Escenarios

| # | Ruta | Ejemplo | C48 | Esperado | Obtenido | Resultado | Detalle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GET /v1/fragmentos | conResultados |  | 200 | 200 | OK |  |
| 2 | GET /v1/fragmentos | precisionDecada |  | 200 | 200 | OK |  |
| 3 | GET /v1/fragmentos | precisionRango |  | 200 | 200 | OK |  |
| 4 | GET /v1/fragmentos | planillaConSeccion |  | 200 | 200 | OK |  |
| 5 | GET /v1/fragmentos | videoDescrito |  | 200 | 200 | OK |  |
| 6 | GET /v1/fragmentos | sinResultados |  | 200 | 200 | OK |  |
| 7 | GET /v1/fragmentos | sinCriterio |  | 400 | 400 | OK |  |
| 8 | GET /v1/fragmentos | parametroDesconocido |  | 400 | 400 | OK |  |
| 9 | GET /v1/fragmentos | rutaInexistente |  | 404 | 404 | OK |  |
| 10 | GET /v1/fragmentos | tokenInvalido |  | 401 | 401 | OK |  |
| 11 | GET /v1/fragmentos | sinAlcance |  | 403 | 403 | OK |  |
| 12 | GET /v1/fragmentos | limite |  | 429 | 429 | OK |  |
| 13 | GET /v1/fragmentos | pausado |  | 503 | 503 | OK |  |
| 14 | GET /v1/fragmentos | motorCaido |  | 503 | 503 | OK |  |
| 15 | GET /v1/piezas/{pieza_id} | convenio |  | 200 | 200 | OK |  |
| 16 | GET /v1/piezas/{pieza_id} | videoAnalizadoPorPersona |  | 200 | 200 | OK |  |
| 17 | GET /v1/piezas/{pieza_id} | aporteValidado | sí | 200 | 200 | OK |  |
| 18 | GET /v1/piezas/{pieza_id} | idMalFormado |  | 400 | 400 | OK |  |
| 19 | GET /v1/piezas/{pieza_id} | noDisponible |  | 404 | 404 | OK |  |
| 20 | GET /v1/piezas/{pieza_id} | tokenInvalido |  | 401 | 401 | OK |  |
| 21 | GET /v1/piezas/{pieza_id} | sinAlcance |  | 403 | 403 | OK |  |
| 22 | GET /v1/piezas/{pieza_id} | limite |  | 429 | 429 | OK |  |
| 23 | GET /v1/piezas/{pieza_id} | pausado |  | 503 | 503 | OK |  |
| 24 | GET /v1/piezas/{pieza_id} | motorCaido |  | 503 | 503 | OK |  |
| 25 | GET /v1/efemerides | conResultados | sí | 200 | 200 | OK |  |
| 26 | GET /v1/efemerides | sinResultados | sí | 200 | 200 | OK |  |
| 27 | GET /v1/efemerides | sinPeriodo | sí | 400 | 400 | OK |  |
| 28 | GET /v1/efemerides | periodoLargo | sí | 400 | 400 | OK |  |
| 29 | GET /v1/efemerides | rutaInexistente | sí | 404 | 404 | OK |  |
| 30 | GET /v1/efemerides | tokenInvalido | sí | 401 | 401 | OK |  |
| 31 | GET /v1/efemerides | sinAlcance | sí | 403 | 403 | OK |  |
| 32 | GET /v1/efemerides | limite | sí | 429 | 429 | OK |  |
| 33 | GET /v1/efemerides | pausado | sí | 503 | 503 | OK |  |
| 34 | GET /v1/efemerides | motorCaido | sí | 503 | 503 | OK |  |
| 35 | GET /v1/relatos | conResultados | sí | 200 | 200 | OK |  |
| 36 | GET /v1/relatos | sinResultados | sí | 200 | 200 | OK |  |
| 37 | GET /v1/relatos | sinPeriodo | sí | 400 | 400 | OK |  |
| 38 | GET /v1/relatos | periodoLargo | sí | 400 | 400 | OK |  |
| 39 | GET /v1/relatos | rutaInexistente | sí | 404 | 404 | OK |  |
| 40 | GET /v1/relatos | tokenInvalido | sí | 401 | 401 | OK |  |
| 41 | GET /v1/relatos | sinAlcance | sí | 403 | 403 | OK |  |
| 42 | GET /v1/relatos | limite | sí | 429 | 429 | OK |  |
| 43 | GET /v1/relatos | pausado | sí | 503 | 503 | OK |  |
| 44 | GET /v1/relatos | motorCaido | sí | 503 | 503 | OK |  |
| 45 | POST /v1/aportes | creado |  | 201 | 201 | OK |  |
| 46 | POST /v1/aportes | repetido |  | 200 | 200 | OK |  |
| 47 | POST /v1/aportes | claveReutilizada |  | 400 | 400 | OK |  |
| 48 | POST /v1/aportes | claveAusente |  | 400 | 400 | OK |  |
| 49 | POST /v1/aportes | cuerpoGrande |  | 400 | 400 | OK |  |
| 50 | POST /v1/aportes | fuenteInexistente |  | 400 | 400 | OK |  |
| 51 | POST /v1/aportes | rutaInexistente |  | 404 | 404 | OK |  |
| 52 | POST /v1/aportes | aporteRechazado | sí | 422 | 422 | OK |  |
| 53 | POST /v1/aportes | tokenInvalido |  | 401 | 401 | OK |  |
| 54 | POST /v1/aportes | sinAlcance |  | 403 | 403 | OK |  |
| 55 | POST /v1/aportes | limite |  | 429 | 429 | OK |  |
| 56 | POST /v1/aportes | pausado |  | 503 | 503 | OK |  |
| 57 | POST /v1/aportes | motorCaido |  | 503 | 503 | OK |  |

## Cliente del Agente 1

Comando: `cd ../Proyecto-Final/Implementacion/Agente1 && .venv/bin/python -m pytest -v -p no:cacheprovider contrato/test_contrato_hv_v1.py`

Código de salida: 0 · Duración: 1.0 s

Últimas 200 líneas de la salida:

```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- /home/spendice/Documents/Archivos_Facu/Proyecto-Final/Implementacion/Agente1/.venv/bin/python
rootdir: /home/spendice/Documents/Archivos_Facu/Proyecto-Final/Implementacion/Agente1
configfile: pyproject.toml
plugins: cov-7.1.0
collecting ... collected 39 items

contrato/test_contrato_hv_v1.py::test_fragmentos_conResultados_cita_pagina_seccion_y_precision PASSED [  2%]
contrato/test_contrato_hv_v1.py::test_fragmentos_precisionDecada_no_es_fecha_exacta PASSED [  5%]
contrato/test_contrato_hv_v1.py::test_fragmentos_precisionRango_se_redacta_entre_x_y_y PASSED [  7%]
contrato/test_contrato_hv_v1.py::test_fragmentos_planillaConSeccion_usa_la_hoja_como_ubicacion PASSED [ 10%]
contrato/test_contrato_hv_v1.py::test_fragmentos_videoDescrito_usa_la_marca_de_tiempo_como_ubicacion PASSED [ 12%]
contrato/test_contrato_hv_v1.py::test_fragmentos_sinResultados_no_da_material_para_afirmar PASSED [ 15%]
contrato/test_contrato_hv_v1.py::test_fragmentos_4xx_es_definitivo[400-sinCriterio] PASSED [ 17%]
contrato/test_contrato_hv_v1.py::test_fragmentos_4xx_es_definitivo[400-parametroDesconocido] PASSED [ 20%]
contrato/test_contrato_hv_v1.py::test_fragmentos_4xx_es_definitivo[404-rutaInexistente] PASSED [ 23%]
contrato/test_contrato_hv_v1.py::test_piezas_convenio_devuelve_la_pieza_completa PASSED [ 25%]
contrato/test_contrato_hv_v1.py::test_piezas_videoAnalizadoPorPersona_acepta_el_tipo_nuevo PASSED [ 28%]
contrato/test_contrato_hv_v1.py::test_piezas_noDisponible_es_ausencia_no_error PASSED [ 30%]
contrato/test_contrato_hv_v1.py::test_piezas_idMalFormado_es_definitivo PASSED [ 33%]
contrato/test_contrato_hv_v1.py::test_aportes_creado_queda_pendiente PASSED [ 35%]
contrato/test_contrato_hv_v1.py::test_aportes_repetido_devuelve_el_acuse_original PASSED [ 38%]
contrato/test_contrato_hv_v1.py::test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado[400-claveReutilizada] PASSED [ 41%]
contrato/test_contrato_hv_v1.py::test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado[400-claveAusente] PASSED [ 43%]
contrato/test_contrato_hv_v1.py::test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado[400-cuerpoGrande] PASSED [ 46%]
contrato/test_contrato_hv_v1.py::test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado[400-fuenteInexistente] PASSED [ 48%]
contrato/test_contrato_hv_v1.py::test_aportes_4xx_no_se_reintenta_ni_con_reintento_habilitado[404-rutaInexistente] PASSED [ 51%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[401-tokenInvalido-historia_viva_unauthorized-fragmentos] PASSED [ 53%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[401-tokenInvalido-historia_viva_unauthorized-piezas] PASSED [ 56%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[401-tokenInvalido-historia_viva_unauthorized-aportes] PASSED [ 58%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[403-sinAlcance-historia_viva_forbidden-fragmentos] PASSED [ 61%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[403-sinAlcance-historia_viva_forbidden-piezas] PASSED [ 64%]
contrato/test_contrato_hv_v1.py::test_comun_4xx_de_credencial_es_definitivo[403-sinAlcance-historia_viva_forbidden-aportes] PASSED [ 66%]
contrato/test_contrato_hv_v1.py::test_comun_limite_espera_retry_after_y_no_reintenta_en_rafaga[fragmentos] PASSED [ 69%]
contrato/test_contrato_hv_v1.py::test_comun_limite_espera_retry_after_y_no_reintenta_en_rafaga[piezas] PASSED [ 71%]
contrato/test_contrato_hv_v1.py::test_comun_limite_espera_retry_after_y_no_reintenta_en_rafaga[aportes] PASSED [ 74%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[pausado-fragmentos] PASSED [ 76%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[pausado-piezas] PASSED [ 79%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[pausado-aportes] PASSED [ 82%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[motorCaido-fragmentos] PASSED [ 84%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[motorCaido-piezas] PASSED [ 87%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_largo_no_bloquea_el_flujo[motorCaido-aportes] PASSED [ 89%]
contrato/test_contrato_hv_v1.py::test_comun_503_con_retry_after_corto_se_reintenta_esperando PASSED [ 92%]
contrato/test_contrato_hv_v1.py::test_comun_el_token_se_lee_en_cada_pedido PASSED [ 94%]
contrato/test_contrato_hv_v1.py::test_c48_aporteValidado_vuelve_como_cualquier_pieza PASSED [ 97%]
contrato/test_contrato_hv_v1.py::test_c48_aporteRechazado_es_definitivo_y_no_reusa_la_clave PASSED [100%]

============================== 39 passed in 0.45s ==============================

```
