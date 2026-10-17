"""Post de efeméride HU-011 desde Historia Viva (#85).

Flujo: A1 consulta a Historia Viva (A2) por el puerto `HistoriaViva`, compone
la efeméride con `componer_material_efemeride` y genera un borrador de post
con las citas de los fragmentos, por el mismo carril estructurado de
`posts.py`. Todo queda en `PENDIENTE_VALIDACION` y la pieza pasa por la misma
decisión de publicación del circuito humano.

Decisiones que no se ven en el código:

- **La fuente es el puerto, nunca un adapter.** El parámetro `historia_viva`
  recibe cualquier implementación de `HistoriaViva`: el fake en pruebas, o el
  `ClienteHistoriaViva` sobre `TransporteHistoriaVivaHttp` (#12). Nada de
  este módulo sabe si el material vino por red o de memoria.
- **Historia Viva no redacta y el modelo tampoco escribe hechos.** El
  `datos_fuente` del prompt lleva los textos citados y sus citas como datos
  no confiables; el modelo sólo escribe `gancho`, `prosa`, `cta` y hashtags
  del contrato `post_creative_efemeride_v1`. El renderer intercala los
  fragmentos literalmente, con su cita, igual que `posts.py` intercala los
  datos de la actividad.
- **Los mismos gates, sin duplicarlos.** La salida del modelo pasa por
  `_parsear_creatividad_estructurada` de `posts.py` con los mismos códigos y
  el mismo reintento acotado; `hechos_extra` declara los hechos que acá no
  viajan en una fila de planilla (textos citados, citas, expresión temporal y
  el mes de la efeméride), así `source_fact_in_creative_field` cubre también
  la copia del material en la zona creativa.
- **La cita conserva pieza, fragmento y precisión.** `Fragmento.cita()`
  identifica el pasaje (`pieza_id`, ubicación, expresión temporal) pero no el
  fragmento; el post necesita la identidad completa para que la afirmación
  sea verificable contra la fuente, así que `_cita_publicable` la arma con
  `pieza_id / fragmento_id (, ubicacion) (expresion_temporal)`. La expresión
  sale siempre de `RangoHistorico.expresion_temporal`, nunca de formatear la
  fecha: una pieza con precisión `mes` no se presenta como día exacto.
- **El texto citado no pasa el gate de "estado".** `PATRON_ACCION_NO_AUTORIZADA`
  existe para que un borrador no afirme que algo fue aprobado, publicado o
  confirmado. Un fragmento histórico que narra una aprobación la afirma como
  *cita* atribuida a su fuente, no como estado del borrador: aplicarle ese
  gate haría imposible citar la historia institucional. Lo que sí se rechaza
  de la fuente son los caracteres de control (`source_rendering_unsafe`),
  porque romperían la estructura del documento. El gate de acciones sigue
  pleno sobre la zona creativa del modelo.
- **Sin material no hay post.** Una consulta vacía termina `INCOMPLETA` /
  `material_insuficiente` sin invocar al generador: no hay hueco que el
  modelo pueda rellenar con una afirmación inventada.
- **Un fragmento por post, filtrado por fecha antes de generar.** De los
  fragmentos que devuelve Historia Viva se descartan los que no sustentan la
  fecha consultada: la fecha que la fuente sostiene tiene que caer DENTRO del
  período, el solapamiento no alcanza, y la precisión declarada se interpreta
  tal cual, porque los límites de un mes, un año o una década no son fechas
  exactas. Si ninguna sustenta el período se informa material insuficiente
  (causa temporal), sin invocar al generador.
- **Se elige el primero que entra completo, en orden de Historia Viva.** Entre
  los elegibles no hay ranking por precisión ni por cercanía: se conserva el
  orden de respuesta y se toma el primero que entra completo en el canal,
  presupuestando el texto citado, la cita, la expresión temporal, la
  estructura y el espacio que ocupan la creatividad y los hashtags. Si no
  entra, se prueba el siguiente; si ninguno entra se informa material no
  utilizable (causa de extensión), distinto de una falla de generación. El
  gate final de extensión y el reintento acotado siguen vigentes: que la
  fuente quepa no demuestra que el modelo haya cumplido el contrato.
- **Las referencias descartadas quedan a la vista de quien valida.** El
  borrador lleva, fuera del texto publicable y de su cómputo de extensión, una
  lista breve de referencias no utilizadas con su motivo; no se generan posts
  alternativos ni se agrega un circuito de selección humana.
- **Procedencia declarada, no inferida.** `procedencia` es del vocabulario
  `PROCEDENCIAS_EFEMERIDE`: `insumo_a2` para el material del acervo de A2 y
  `synthetic_test` para las corridas con fragmentos sintéticos (el fake y los
  recorridos offline). El pipeline no puede saber cómo está respaldado el
  puerto, así que quien lo invoca declara la procedencia: va a la auditoría
  como `data_origin` y al borrador como línea `_Procedencia: ..._`, visible
  para quien valida y ajena al texto del post.
- **El id deriva del pedido.** `efemeride-<periodo>-<canal>-<hash8>` es
  estable para el mismo pedido y no colisiona entre temas ni precisiones del
  mismo período. Es también el `objeto_id` que quien invoca declara como
  `publicacion` pendiente en el registro de decisiones (#72), igual que el
  correo de «borrador listo» del canal.

No está en este módulo: el despacho desde `interpretacion.py` (el catálogo
`intenciones_v3` no tiene una intención de efeméride y resolver fechas desde
prosa es un cambio de contrato aparte), el `registrar_aporte` de vuelta a A2
(el issue define el flujo consulta→borrador), y el transporte (`historia_viva_http.py`).
"""

from __future__ import annotations

import json
import time
import unicodedata
import uuid
from datetime import date, datetime, timezone
from importlib.resources import files
from pathlib import Path

from .destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
    ReferenciaBorrador,
)
from .historia_viva import (
    CONTRACT_STATUS as HV_CONTRACT_STATUS,
)
from .historia_viva import (
    CONTRACT_VERSION as HV_CONTRACT_VERSION,
)
from .historia_viva import (
    LIMITE_FRAGMENTOS_DEFAULT,
    LIMITE_FRAGMENTOS_MAX,
    MESES,
    PRECISIONES_FECHA,
    Fragmento,
    HistoriaViva,
    HistoriaVivaError,
    MaterialEfemeride,
    componer_material_efemeride,
)
from .politica_redes import (
    POLICY_VERSION,
    POLITICA_DEFAULT,
    POLITICAS_DEFAULT,
    PoliticaPost,
)
from .posts import (
    CANALES,
    CODIGOS_REINTENTABLES,
    DESTINATION_ERROR_CODES,
    INSTRUCCION_REINTENTO_POR_CODIGO,
    MAX_INTENTOS_GENERACION,
    RESULTADO_REINTENTO_PENDIENTE,
    ContratoCreativo,
    _construir_contrato_creativo,
    _hash_texto,
    _limite_declarado,
    _parsear_creatividad_estructurada,
    _prompt_con_feedback_reglas,
    _registrar,
)
from .presupuesto import (
    MENSAJE_PRESUPUESTO_AGOTADO,
    RESULTADO_PRESUPUESTO_AGOTADO,
    PresupuestoAgotadoError,
)
from .procesamiento import Generator, ResultadoProceso

HU = "HU-011"
CONTRACT_VERSION = "post_efemeride_input_v1"
EFEMERIDE_RENDERER_VERSION = "post_efemeride_renderer_v1"

CONTRATO_SALIDA_EFEMERIDE = json.loads(
    files("agente1")
    .joinpath("contracts", "post_creative_efemeride_v1.schema.json")
    .read_text(encoding="utf-8")
)
CONTRATO_CREATIVO_EFEMERIDE_V1 = _construir_contrato_creativo(
    CONTRATO_SALIDA_EFEMERIDE,
    renderer_version=EFEMERIDE_RENDERER_VERSION,
    prompt_suffix="efemeride_v1",
    borrador_suffix="",
)

# Procedencia declarada del material: el acervo de A2 por un lado, las
# corridas con fragmentos sintéticos por el otro. `synthetic_test` reusa el
# literal del contrato candidato de insumos para que la evidencia offline no
# se lea como insumo real.
PROCEDENCIA_INSUMO_A2 = "insumo_a2"
PROCEDENCIA_SINTETICA = "synthetic_test"
PROCEDENCIAS_EFEMERIDE = frozenset(
    {PROCEDENCIA_INSUMO_A2, PROCEDENCIA_SINTETICA}
)

# Motivos por los que una referencia recuperada no llega al post. El código va
# a la auditoría; la frase, al borrador, a la vista de quien valida. Una
# referencia se descarta por fecha (no sustenta el período consultado), por
# extensión (no entra completa en el canal) o porque el post cita una sola y
# ya se eligió otra.
MOTIVO_FUERA_DEL_PERIODO = "fuera_del_periodo_consultado"
MOTIVO_NO_ENTRA_EN_CANAL = "no_entra_completo_en_el_canal"
MOTIVO_NO_UTILIZADA = "no_utilizada_una_referencia_por_post"
MOTIVOS_EXCLUSION = {
    MOTIVO_FUERA_DEL_PERIODO: (
        "la fecha sustentada queda fuera del período consultado"
    ),
    MOTIVO_NO_ENTRA_EN_CANAL: "no entra completa en el canal",
    MOTIVO_NO_UTILIZADA: "no se usa: el post cita una sola referencia",
}

MAX_TEMA_CARACTERES = 300

# Feedback del reintento en el vocabulario de la pieza: los códigos son los
# mismos del gate compartido, pero «la actividad» acá es material citado.
INSTRUCCIONES_REINTENTO_EFEMERIDE = dict(INSTRUCCION_REINTENTO_POR_CODIGO)
INSTRUCCIONES_REINTENTO_EFEMERIDE["source_fact_in_creative_field"] = (
    "no repitas los textos citados, las citas ni la expresión temporal de la "
    "efeméride —fecha, mes, año, identificadores de pieza o de fragmento—: "
    "el sistema los agrega por separado"
)
INSTRUCCIONES_REINTENTO_EFEMERIDE["unauthorized_date"] = (
    "no escribas fechas, meses, años ni ninguna mención temporal concreta: "
    "la fecha de la efeméride la agrega el sistema"
)


def procesar_post_efemeride(
    *,
    historia_viva: HistoriaViva,
    desde: date,
    hasta: date,
    canal: str,
    directorio_salida: Path,
    generator: Generator,
    precision: str = "dia",
    tema: str | None = None,
    limite: int = LIMITE_FRAGMENTOS_DEFAULT,
    procedencia: str = PROCEDENCIA_INSUMO_A2,
    politica: PoliticaPost | None = None,
    destino: DestinoBorradores | None = None,
    contrato: ContratoCreativo | None = None,
) -> ResultadoProceso:
    """Genera el borrador de post de efeméride desde el puerto HistoriaViva.

    Mismo contrato que `procesar_post_estructurado`: no propaga excepciones,
    cada frontera (consulta, generador, destino) se traduce a estado + línea
    de auditoría, y el éxito es `PENDIENTE_VALIDACION` con la marca
    `BORRADOR — NO PUBLICAR`. `desde`/`hasta` acotan el período consultado,
    `precision` declara cuánto puede decir `expresion_temporal` y `tema`
    acota la búsqueda sólo cuando la solicitud lo determina.

    El post cita una sola referencia: se filtran los fragmentos que sustentan
    la fecha consultada antes de generar y, entre los elegibles, se publica el
    primero que entra completo en el canal, en el orden que devuelve el
    puerto. `limite` es el tope de recuperación, no la cantidad de fragmentos
    publicados: se pide más de uno justamente para poder descartar al primero.
    """

    contrato_efectivo = contrato or CONTRATO_CREATIVO_EFEMERIDE_V1
    correlation_id = str(uuid.uuid4())
    inicio = time.perf_counter()
    politica_auditoria = politica or POLITICA_DEFAULT
    log_path = directorio_salida / "logs" / "ejecuciones.jsonl"

    if not _parametros_validos(desde, hasta, precision, tema, limite, procedencia):
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=None,
            hv_consulta=None,
            canal=canal if canal in CANALES else None,
            generator=generator,
            politica=politica_auditoria,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="INVALIDA",
            resultado="consulta_invalida",
            error="Consulta de efeméride inválida",
            validation_errors=["consulta_invalida"],
            contrato=contrato_efectivo,
        )
    tema_efectivo = tema.strip() if tema else None
    hv_consulta = {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "precision": precision,
        "tema_hash": _hash_texto(tema_efectivo) if tema_efectivo else None,
        "limite": limite,
    }
    parte_periodo = (
        desde.isoformat()
        if desde == hasta
        else f"{desde.isoformat()}_{hasta.isoformat()}"
    )
    huella = _hash_texto(
        f"{desde}|{hasta}|{precision}|{tema_efectivo or ''}"
    )[:8]
    id_efemeride = f"efemeride-{parte_periodo}-{huella}"
    if canal not in CANALES:
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=None,
            generator=generator,
            politica=politica_auditoria,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="INVALIDA",
            resultado="channel_invalid",
            error="Canal inválido",
            validation_errors=["channel_not_allowed"],
            contrato=contrato_efectivo,
        )
    politica_efectiva = politica or POLITICAS_DEFAULT[canal]
    # Errores de configuración: se detectan antes de tocar el puerto. Un
    # `ContratoCreativo` de actividad comparte la forma pero apunta al prompt
    # `post_{canal}_…` de otra pieza, y un prompt que falta no se disimula con
    # una excepción a medio pipeline.
    if politica_efectiva.min_hashtags > len(contrato_efectivo.hashtags_seguros):
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="INVALIDA",
            resultado="policy_incompatible",
            error="La política no es compatible con la lista segura provisional",
            validation_errors=["structured_policy_incompatible"],
            contrato=contrato_efectivo,
            material=None,
        )
    try:
        plantilla = files("agente1").joinpath(
            "prompts", f"post_{canal}_{contrato_efectivo.prompt_suffix}.txt"
        ).read_text(encoding="utf-8")
    except Exception:
        plantilla = None
    if plantilla is None or not (
        contrato_efectivo.contract_version.startswith("post_creative_efemeride")
    ):
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="INVALIDA",
            resultado="contract_incompatible",
            error="El contrato creativo no es compatible con la efeméride",
            validation_errors=["efemeride_contract_incompatible"],
            contrato=contrato_efectivo,
            material=None,
        )
    try:
        material = componer_material_efemeride(
            historia_viva,
            desde=desde,
            hasta=hasta,
            precision=precision,
            tema=tema_efectivo,
            limite=limite,
        )
    except HistoriaVivaError as exc:
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="FALLIDA",
            resultado="source_failure",
            error="Falló la consulta a Historia Viva",
            extra_fields={"source_error_code": exc.code},
            contrato=contrato_efectivo,
        )
    except Exception:
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="FALLIDA",
            resultado="source_failure",
            error="Falló la consulta a Historia Viva",
            extra_fields={"source_error_code": "historia_viva_unavailable"},
            contrato=contrato_efectivo,
        )
    if not isinstance(material, MaterialEfemeride) or any(
        not isinstance(fragmento, Fragmento) for fragmento in material.fragmentos
    ):
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="FALLIDA",
            resultado="source_failure",
            error="Falló la consulta a Historia Viva",
            extra_fields={"source_error_code": "historia_viva_response_invalid"},
            contrato=contrato_efectivo,
        )
    # Filtro temporal ANTES de generar: la fecha que la fuente sostiene tiene
    # que caer DENTRO del período consultado. El solapamiento no alcanza (una
    # fuente «entre 2015 y 2019» no sustenta una efeméride de abril de 2016) y
    # la precisión declarada se interpreta tal cual: los límites de un mes, un
    # año o una década no son fechas exactas. Se conserva el orden de Historia
    # Viva y se registran los motivos de lo que se descarta.
    elegibles, excluidos = _filtrar_por_periodo(material)
    if not elegibles:
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="INCOMPLETA",
            resultado="material_insuficiente",
            error=(
                "La consulta no devolvió material histórico"
                if not material.hay_material
                else "Ningún fragmento sustentado por la fuente cae dentro "
                "del período consultado"
            ),
            validation_errors=["material_insuficiente"],
            extra_fields={
                "motivo_material": (
                    "sin_material"
                    if not material.hay_material
                    else "sin_fecha_elegible"
                )
            },
            contrato=contrato_efectivo,
            material=material,
            elegibles=elegibles,
            exclusiones=excluidos,
        )
    material_elegible = MaterialEfemeride(
        rango_consultado=material.rango_consultado,
        fragmentos=elegibles,
    )
    # Controles sobre la fuente previos a generar: el renderer copia estos
    # valores tal cual al post, así que lo que no sea seguro copiar se frena
    # acá. Sólo se controlan los elegibles: lo que se descarta por fecha no se
    # renderiza ni se cita. El gate de acciones institucionales no se aplica al
    # texto citado (es afirmación atribuida a la fuente, no estado del
    # borrador); el del texto creativo corre igual que en `posts.py`.
    valores_renderizados = [
        valor
        for fragmento in elegibles
        for valor in (
            fragmento.texto,
            _cita_publicable(fragmento),
            fragmento.cita(),
        )
    ] + [material.rango_consultado.expresion_temporal()]
    if any(
        unicodedata.category(char).startswith("C")
        for valor in valores_renderizados
        for char in valor
    ):
        return _fallo_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio,
            procedencia=procedencia,
            estado="FALLIDA",
            resultado="source_not_renderable",
            error="La fuente contiene controles incompatibles con el renderer",
            validation_errors=["source_rendering_unsafe"],
            contrato=contrato_efectivo,
            material=material,
            elegibles=elegibles,
            exclusiones=excluidos,
        )

    datos = _material_como_datos(material_elegible)
    prompt = _construir_prompt_efemeride(
        plantilla, datos, canal, politica_efectiva, contrato_efectivo
    )
    hechos_fuente = _hechos_fuente_efemeride(material_elegible)
    inicio_generacion = time.perf_counter()
    prompt_efectivo = prompt
    intento = 0
    contenido = ""
    publicado: Fragmento | None = None
    exclusiones: tuple[tuple[Fragmento, str], ...] = excluidos
    while True:
        intento += 1
        try:
            salida_cruda = generator.generar(prompt_efectivo)
        except PresupuestoAgotadoError:
            return _fallo_efemeride(
                log_path=log_path,
                id_efemeride=id_efemeride,
                hv_consulta=hv_consulta,
                canal=canal,
                generator=generator,
                politica=politica_efectiva,
                correlation_id=correlation_id,
                inicio=inicio_generacion,
                procedencia=procedencia,
                estado="FALLIDA",
                resultado=RESULTADO_PRESUPUESTO_AGOTADO,
                error=MENSAJE_PRESUPUESTO_AGOTADO,
                contrato=contrato_efectivo,
                material=material,
                datos=datos,
                intento=intento,
                elegibles=elegibles,
                exclusiones=excluidos,
                publicado=publicado,
            )
        except Exception:
            return _fallo_efemeride(
                log_path=log_path,
                id_efemeride=id_efemeride,
                hv_consulta=hv_consulta,
                canal=canal,
                generator=generator,
                politica=politica_efectiva,
                correlation_id=correlation_id,
                inicio=inicio_generacion,
                procedencia=procedencia,
                estado="FALLIDA",
                resultado="error_generacion",
                error="Falló la generación del borrador",
                contrato=contrato_efectivo,
                material=material,
                datos=datos,
                intento=intento,
                elegibles=elegibles,
                exclusiones=excluidos,
                publicado=publicado,
            )
        contenido_crudo = (
            unicodedata.normalize("NFC", salida_cruda.strip())
            if isinstance(salida_cruda, str)
            else ""
        )
        # La "fila" del gate queda vacía: acá los hechos de fuente no viajan
        # por `CAMPOS_SEMANTICOS_AUTORIZADOS` sino por `hechos_extra`, así el
        # mismo gate y los mismos códigos cubren el material citado.
        creatividad, errores = _parsear_creatividad_estructurada(
            contenido_crudo,
            {},
            canal,
            politica_efectiva,
            contrato_efectivo,
            hechos_extra=hechos_fuente,
        )
        contenido = ""
        publicado = None
        exclusiones_intento = excluidos
        if creatividad is not None and not errores:
            # Selección por extensión: se conserva el orden de Historia Viva y
            # se toma el primer elegible que entra COMPLETO en el canal,
            # presupuestando el texto citado, la cita, la expresión temporal,
            # la estructura y el espacio que ocupan la creatividad y los
            # hashtags de este intento. Los que no entran y los que quedan
            # después del elegido quedan como referencias no utilizadas.
            publicado, descartes = _seleccionar_que_entra(
                material_elegible, canal, creatividad, politica_efectiva
            )
            exclusiones_intento = _exclusiones_en_orden(
                material, publicado, excluidos, descartes
            )
            if publicado is None:
                errores.append("length_out_of_range")
            else:
                material_candidato = MaterialEfemeride(
                    rango_consultado=material.rango_consultado,
                    fragmentos=(publicado,),
                )
                contenido = _renderizar_post_efemeride(
                    material_candidato, canal, creatividad
                )
                errores.extend(
                    _validar_render_efemeride(
                        contenido,
                        material_candidato,
                        canal,
                        creatividad,
                        politica_efectiva,
                    )
                )
        if not errores:
            exclusiones = exclusiones_intento
            break
        if intento >= MAX_INTENTOS_GENERACION or any(
            codigo not in CODIGOS_REINTENTABLES for codigo in errores
        ):
            # «No entra ninguno» no es una falla del modelo sino del material
            # para ese canal: se informa como tal, sin borrador y sin
            # confundirlo con una salida no conforme.
            solo_longitud = set(errores) == {"length_out_of_range"}
            return _fallo_efemeride(
                log_path=log_path,
                id_efemeride=id_efemeride,
                hv_consulta=hv_consulta,
                canal=canal,
                generator=generator,
                politica=politica_efectiva,
                correlation_id=correlation_id,
                inicio=inicio_generacion,
                procedencia=procedencia,
                estado="INCOMPLETA" if solo_longitud else "FALLIDA",
                resultado=(
                    "material_no_utilizable"
                    if solo_longitud
                    else (
                        "salida_no_conforme" if contenido_crudo else "salida_vacia"
                    )
                ),
                error=(
                    "Ningún fragmento elegible entra completo en el canal"
                    if solo_longitud
                    else "La salida generada no cumple el contrato mínimo"
                ),
                validation_errors=list(dict.fromkeys(errores)),
                contrato=contrato_efectivo,
                material=material,
                datos=datos,
                intento=intento,
                elegibles=elegibles,
                exclusiones=exclusiones_intento,
                publicado=publicado,
            )
        _registrar(
            log_path,
            _registro_base_efemeride(
                id_efemeride=id_efemeride,
                hv_consulta=hv_consulta,
                material=material,
                datos=datos,
                canal=canal,
                generator=generator,
                politica=politica_efectiva,
                correlation_id=correlation_id,
                latencia_s=round(time.perf_counter() - inicio_generacion, 6),
                procedencia=procedencia,
                elegibles=elegibles,
                exclusiones=exclusiones_intento,
                publicado=publicado,
            )
            | _campos_auditoria_efemeride(contrato_efectivo, canal, intento)
            | {
                "estado": "FALLIDA",
                "resultado": RESULTADO_REINTENTO_PENDIENTE,
                "error": "La salida generada no cumple el contrato mínimo",
                "output_hash": None,
                "validation_errors": list(dict.fromkeys(errores)),
            },
        )
        prompt_efectivo = _prompt_con_feedback_reglas(
            prompt, errores, instrucciones=INSTRUCCIONES_REINTENTO_EFEMERIDE
        )

    borrador = (
        f"{BORRADOR_MARKER}"
        f"{_linea_procedencia(procedencia, desde, hasta)}\n\n"
        f"{contenido}\n"
        f"{_bloque_referencias_no_utilizadas(exclusiones)}"
    )
    destino_efectivo = destino or MarkdownDestinoBorradores(directorio_salida)
    id_borrador = f"{id_efemeride}-{canal}"
    try:
        referencia = destino_efectivo.guardar(id_borrador, borrador)
        if not isinstance(referencia, ReferenciaBorrador):
            raise DestinoBorradoresError("destination_contract_invalid")
    except DestinoBorradoresError as exc:
        return _fallo_destino_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            material=material,
            datos=datos,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            procedencia=procedencia,
            borrador=borrador,
            code=exc.code,
            reconciliation_ref_hash=exc.reconciliation_ref_hash,
            contrato=contrato_efectivo,
            intento=intento,
            elegibles=elegibles,
            exclusiones=exclusiones,
            publicado=publicado,
        )
    except Exception:
        return _fallo_destino_efemeride(
            log_path=log_path,
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            material=material,
            datos=datos,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            inicio=inicio_generacion,
            procedencia=procedencia,
            borrador=borrador,
            code="destination_unavailable",
            reconciliation_ref_hash=None,
            contrato=contrato_efectivo,
            intento=intento,
            elegibles=elegibles,
            exclusiones=exclusiones,
            publicado=publicado,
        )
    _registrar(
        log_path,
        _registro_base_efemeride(
            id_efemeride=id_efemeride,
            hv_consulta=hv_consulta,
            material=material,
            datos=datos,
            canal=canal,
            generator=generator,
            politica=politica_efectiva,
            correlation_id=correlation_id,
            latencia_s=round(time.perf_counter() - inicio_generacion, 6),
            procedencia=procedencia,
            elegibles=elegibles,
            exclusiones=exclusiones,
            publicado=publicado,
        )
        | _campos_auditoria_efemeride(contrato_efectivo, canal, intento)
        | {
            "estado": "PENDIENTE_VALIDACION",
            "resultado": "borrador_generado",
            "error": None,
            "output_hash": _hash_texto(borrador),
            "destination_type": referencia.tipo,
            "borrador_ref_hash": _hash_texto(referencia.referencia),
        },
    )
    return ResultadoProceso(
        estado="PENDIENTE_VALIDACION",
        borrador_path=referencia.path,
        log_path=log_path,
        correlation_id=correlation_id,
        referencia_borrador=referencia,
    )


# --- Entrada y material --------------------------------------------------------


def _parametros_validos(
    desde: object,
    hasta: object,
    precision: object,
    tema: object,
    limite: object,
    procedencia: object,
) -> bool:
    """Valida la consulta antes de tocar el puerto.

    `datetime` se excluye a propósito: es `date` pero su `isoformat` trae
    hora y `:`, que no pasan la allowlist de identificadores del borrador.
    `tema` es prosa de la solicitud: se acota como cualquier texto que viaja
    hacia un servicio y hacia el prompt.
    """

    if (
        type(desde) is not date
        or type(hasta) is not date
        or hasta < desde
        or precision not in PRECISIONES_FECHA
        or procedencia not in PROCEDENCIAS_EFEMERIDE
        or not isinstance(limite, int)
        or isinstance(limite, bool)
        or not 1 <= limite <= LIMITE_FRAGMENTOS_MAX
    ):
        return False
    if tema is not None:
        if (
            not isinstance(tema, str)
            or not tema.strip()
            or len(tema.strip()) > MAX_TEMA_CARACTERES
            or any(
                unicodedata.category(char).startswith("C") for char in tema
            )
        ):
            return False
    return True


# --- Selección del fragmento ---------------------------------------------------


def _filtrar_por_periodo(
    material: MaterialEfemeride,
) -> tuple[tuple[Fragmento, ...], tuple[tuple[Fragmento, str], ...]]:
    """Separa los fragmentos que sustentan la fecha de los que no.

    La fecha que la fuente sostiene tiene que quedar DENTRO del período
    consultado: el solapamiento no alcanza. La comparación usa los límites del
    rango tal como vienen de la fuente, así que una precisión de mes, año o
    década se respeta sin tratarla como un día exacto. Conserva el orden de
    respuesta de Historia Viva. Devuelve los elegibles y, por separado, los
    descartados con su motivo.
    """

    rango_consultado = material.rango_consultado
    elegibles: list[Fragmento] = []
    excluidos: list[tuple[Fragmento, str]] = []
    for fragmento in material.fragmentos:
        if rango_consultado.contiene(fragmento.rango):
            elegibles.append(fragmento)
        else:
            excluidos.append((fragmento, MOTIVO_FUERA_DEL_PERIODO))
    return tuple(elegibles), tuple(excluidos)


def _seleccionar_que_entra(
    material_elegible: MaterialEfemeride,
    canal: str,
    creatividad: dict[str, object],
    politica: PoliticaPost,
) -> tuple[Fragmento | None, tuple[tuple[Fragmento, str], ...]]:
    """Elige el primer elegible que entra completo y lista los descartes.

    Conserva el orden devuelto por Historia Viva: no hay ranking por precisión
    ni por cercanía. El presupuesto de extensión se mide sobre el post ya
    renderizado con la creatividad de este intento, porque el espacio que
    ocupan gancho, prosa, cta y hashtags sólo se conoce cuando el modelo los
    produjo. Devuelve el fragmento elegido (o `None` si ninguno entra) y los
    motivos de los no usados.
    """

    fragmentos = material_elegible.fragmentos
    for indice, fragmento in enumerate(fragmentos):
        candidato = MaterialEfemeride(
            rango_consultado=material_elegible.rango_consultado,
            fragmentos=(fragmento,),
        )
        longitud = _longitud_publicable(
            _renderizar_post_efemeride(candidato, canal, creatividad)
        )
        if longitud is not None and longitud <= politica.max_chars:
            descartes = tuple(
                (previo, MOTIVO_NO_ENTRA_EN_CANAL)
                for previo in fragmentos[:indice]
            ) + tuple(
                (posterior, MOTIVO_NO_UTILIZADA)
                for posterior in fragmentos[indice + 1 :]
            )
            return fragmento, descartes
    return None, tuple(
        (fragmento, MOTIVO_NO_ENTRA_EN_CANAL) for fragmento in fragmentos
    )


def _longitud_publicable(contenido: str) -> int | None:
    """Caracteres del texto publicable más los hashtags, como el gate.

    Es el mismo cómputo que aplica `_validar_render_efemeride`: la selección y
    el gate no pueden discrepar sobre qué entra. Devuelve `None` si el
    contenido no tiene la estructura del post, porque entonces el problema es
    otro y no la extensión.
    """

    _, separador_texto, cuerpo = contenido.partition("\nTEXTO:\n")
    texto, separador_hashtags, hashtags = cuerpo.rpartition("\nHASHTAGS:\n")
    if not separador_texto or not separador_hashtags:
        return None
    return len(texto) + len(hashtags)


def _exclusiones_en_orden(
    material: MaterialEfemeride,
    publicado: Fragmento | None,
    excluidos: tuple[tuple[Fragmento, str], ...],
    descartes: tuple[tuple[Fragmento, str], ...],
) -> tuple[tuple[Fragmento, str], ...]:
    """Los motivos de exclusión en el orden que devolvió Historia Viva.

    Junta los descartes por fecha y los de extensión (o por citar una sola
    referencia) y los reordena según el material original, para que la lista
    del borrador siga el mismo orden que la respuesta del puerto.
    """

    motivos = dict(excluidos)
    motivos.update(descartes)
    return tuple(
        (fragmento, motivos[fragmento])
        for fragmento in material.fragmentos
        if fragmento is not publicado
    )


def _bloque_referencias_no_utilizadas(
    exclusiones: tuple[tuple[Fragmento, str], ...],
) -> str:
    """Referencias descartadas y su motivo, fuera del texto publicable.

    Va después del bloque que se publicaría y no entra en el cómputo de
    extensión: el gate mide el post, no esta nota para quien valida. Sólo
    lleva identificadores y expresiones temporales, nunca la prosa de la
    fuente.
    """

    if not exclusiones:
        return ""
    lineas = ["", "REFERENCIAS NO UTILIZADAS"]
    for fragmento, motivo in exclusiones:
        lineas.append(
            f"- {fragmento.pieza_id} / {fragmento.fragmento_id} "
            f"({fragmento.rango.expresion_temporal()}): {MOTIVOS_EXCLUSION[motivo]}"
        )
    return "\n".join(lineas) + "\n"


def _material_como_datos(material: MaterialEfemeride) -> dict[str, object]:
    """El material serializado: va al prompt como dato y a `input_hash`."""

    return {
        "efemeride": {
            "expresion_temporal": material.rango_consultado.expresion_temporal(),
            "fragmentos": [
                {"texto": fragmento.texto, "cita": _cita_publicable(fragmento)}
                for fragmento in material.fragmentos
            ],
        }
    }


def _cita_publicable(fragmento: Fragmento) -> str:
    """Cita con identidad de pieza y de fragmento, no sólo del documento."""

    ubicacion = f", {fragmento.ubicacion}" if fragmento.ubicacion else ""
    return (
        f"{fragmento.pieza_id} / {fragmento.fragmento_id}{ubicacion} "
        f"({fragmento.rango.expresion_temporal()})"
    )


def _hechos_fuente_efemeride(material: MaterialEfemeride) -> tuple[str, ...]:
    """Hechos que la zona creativa no puede repetir.

    Los textos citados, las citas en sus dos formas y la expresión temporal
    son los hechos del material; los nombres de mes cubren la forma corta de
    la fecha («en agosto» también es afirmar la fecha de la efeméride).
    """

    hechos: list[str] = []
    for fragmento in material.fragmentos:
        hechos.append(fragmento.texto)
        hechos.append(_cita_publicable(fragmento))
        hechos.append(fragmento.cita())
    rango = material.rango_consultado
    hechos.append(rango.expresion_temporal())
    if rango.precision in {"dia", "mes"}:
        hechos.extend(
            MESES[fecha.month - 1] for fecha in (rango.desde, rango.hasta)
        )
    return tuple(dict.fromkeys(hechos))


def _linea_procedencia(procedencia: str, desde: date, hasta: date) -> str:
    """La marca de procedencia del borrador, fuera del texto del post.

    Va después de `BORRADOR — NO PUBLICAR` y antes de `CANAL:`: la ve quien
    valida el borrador y no se confunde con el cuerpo que se publicaría.
    """

    consulta = f"desde {desde.isoformat()} hasta {hasta.isoformat()}"
    if procedencia == PROCEDENCIA_SINTETICA:
        return (
            "_Procedencia: material sintético de prueba con la forma del "
            f"insumo de A2 (Historia Viva). Consulta: {consulta}._"
        )
    return (
        "_Procedencia: insumo de A2 (Historia Viva, acervo histórico "
        f"validado). Consulta: {consulta}._"
    )


# --- Prompt, render y auditoría -------------------------------------------------


def _construir_prompt_efemeride(
    plantilla: str,
    datos: dict[str, object],
    canal: str,
    politica: PoliticaPost,
    contrato: ContratoCreativo,
) -> str:
    datos_json = json.dumps(
        datos, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (
        plantilla.replace("{max_chars}", str(politica.max_chars))
        .replace("{min_hashtags}", str(politica.min_hashtags))
        .replace(
            "{max_hashtags}",
            str(min(politica.max_hashtags, len(contrato.hashtags_seguros))),
        )
        .replace("{max_emojis}", _limite_declarado(politica.max_emojis))
        .replace("{max_exclamaciones}", _limite_declarado(politica.max_exclamaciones))
        .replace("{datos_fuente}", datos_json)
    )


def _renderizar_post_efemeride(
    material: MaterialEfemeride, canal: str, creatividad: dict[str, object]
) -> str:
    """Arma el post: creatividad del modelo + material citado literalmente.

    Función pura y determinista, sin decisión propia: cada fragmento del
    material que reciba queda en una sola línea seguida de su `Fuente:`, igual
    que `descripcion` en `posts.py`. El flujo le pasa un material de un solo
    fragmento, ya elegido; nada rellena lo que la fuente no trajo.
    """

    lineas = [
        f"CANAL: {canal}",
        "TEXTO:",
        str(creatividad["gancho"]),
        "",
        str(creatividad["prosa"]),
        "",
        f"Efeméride: {material.rango_consultado.expresion_temporal()}",
        "",
    ]
    for fragmento in material.fragmentos:
        lineas += [
            " ".join(fragmento.texto.split()),
            f"Fuente: {_cita_publicable(fragmento)}",
            "",
        ]
    lineas += [
        str(creatividad["cta"]),
        "HASHTAGS:",
        " ".join(creatividad["hashtags"]),
    ]
    return "\n".join(lineas)


def _validar_render_efemeride(
    contenido: str,
    material: MaterialEfemeride,
    canal: str,
    creatividad: dict[str, object],
    politica: PoliticaPost,
) -> list[str]:
    """Re-renderiza y compara; después aplica el límite de extensión."""

    if contenido != _renderizar_post_efemeride(material, canal, creatividad):
        return ["renderer_invariant_violation"]
    longitud = _longitud_publicable(contenido)
    if longitud is None:
        return ["document_structure"]
    if longitud > politica.max_chars:
        return ["length_out_of_range"]
    return []


def _campos_auditoria_efemeride(
    contrato: ContratoCreativo, canal: str | None, intento: int = 0
) -> dict[str, object]:
    return {
        "output_contract_version": contrato.contract_version,
        "renderer_version": contrato.renderer_version,
        "creative_catalog_version": contrato.catalogo_version,
        "prompt_version": (
            f"post_{canal}_{contrato.prompt_suffix}"
            if canal in CANALES
            else None
        ),
        "intento": intento,
    }


def _registro_base_efemeride(
    *,
    id_efemeride: str | None,
    hv_consulta: dict[str, object] | None,
    material: MaterialEfemeride | None,
    datos: dict[str, object] | None,
    canal: str | None,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    latencia_s: float,
    procedencia: str,
    elegibles: tuple[Fragmento, ...] | None = None,
    exclusiones: tuple[tuple[Fragmento, str], ...] | None = None,
    publicado: Fragmento | None = None,
) -> dict[str, object]:
    """Campos comunes de la línea JSONL del pipeline de efeméride.

    Además de los campos compartidos con `posts.py`, registra la procedencia
    declarada (`data_origin`), la versión del contrato de consulta a A2 y el
    material por conteos e identificadores: piezas y fragmentos citables son
    ids de la fuente, nunca su contenido. `tema` viaja como hash, no en claro.

    La recuperación se separa de la publicación: `hv_fragmentos` cuenta lo que
    devolvió el puerto, `hv_fragmentos_elegibles` lo que sustenta el período y
    `hv_fragmentos_publicados` el único fragmento que llegó al post (0 o 1).
    `hv_consulta.limite` conserva el tope pedido, que no se reduce a uno.
    `referencias_excluidas` lista referencias y motivos, nunca prosa.
    """

    registro = {
        "correlation_id": correlation_id,
        "id_solicitud": id_efemeride,
        "id_solicitud_hash": None,
        "HU": HU,
        "canal": canal,
        "contract_version": CONTRACT_VERSION,
        "hv_contract_version": HV_CONTRACT_VERSION,
        "hv_contract_status": HV_CONTRACT_STATUS,
        # La procedencia es un literal del llamador: sólo se registra si está
        # en el vocabulario, porque una cadena arbitraria no es un origen
        # declarado sino texto ajeno entrando al log.
        "data_origin": (
            procedencia if procedencia in PROCEDENCIAS_EFEMERIDE else None
        ),
        "hv_consulta": hv_consulta,
        "hv_fragmentos": (
            len(material.fragmentos) if material is not None else None
        ),
        "hv_fragmentos_elegibles": (
            len(elegibles) if elegibles is not None else None
        ),
        "hv_fragmentos_publicados": (
            1 if publicado is not None else (None if material is None else 0)
        ),
        "hv_piezas_fuente": (
            [publicado.pieza_id]
            if publicado is not None
            else (
                list(material.piezas_fuente()) if material is not None else None
            )
        ),
        "policy_version": politica.version,
        "policy_status": politica.status,
        "policy_document_version": POLICY_VERSION,
        "max_chars": politica.max_chars,
        "min_hashtags": politica.min_hashtags,
        "max_hashtags": politica.max_hashtags,
        "modelo": generator.modelo,
        "num_predict": getattr(generator, "num_predict", None),
        "latencia_s": latencia_s,
        "input_hash": (
            _hash_texto(
                json.dumps(datos, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
            )
            if datos is not None
            else None
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if exclusiones is not None:
        registro["referencias_excluidas"] = [
            {
                "referencia": (
                    f"{fragmento.pieza_id} / {fragmento.fragmento_id}"
                ),
                "motivo": motivo,
            }
            for fragmento, motivo in exclusiones
        ]
    format_mode = getattr(generator, "format_mode", None)
    format_schema_hash = getattr(generator, "format_schema_hash", None)
    if format_mode is not None and format_schema_hash is not None:
        registro["generation_format"] = format_mode
        registro["format_schema_hash"] = format_schema_hash
    return registro


def _fallo_efemeride(
    *,
    log_path: Path,
    id_efemeride: str | None,
    hv_consulta: dict[str, object] | None,
    canal: str | None,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    inicio: float,
    procedencia: str,
    estado: str,
    resultado: str,
    error: str,
    validation_errors: list[str] | None = None,
    extra_fields: dict[str, object] | None = None,
    contrato: ContratoCreativo,
    material: MaterialEfemeride | None = None,
    datos: dict[str, object] | None = None,
    intento: int = 0,
    elegibles: tuple[Fragmento, ...] | None = None,
    exclusiones: tuple[tuple[Fragmento, str], ...] | None = None,
    publicado: Fragmento | None = None,
) -> ResultadoProceso:
    registro = _registro_base_efemeride(
        id_efemeride=id_efemeride,
        hv_consulta=hv_consulta,
        material=material,
        datos=datos,
        canal=canal,
        generator=generator,
        politica=politica,
        correlation_id=correlation_id,
        latencia_s=round(time.perf_counter() - inicio, 6),
        procedencia=procedencia,
        elegibles=elegibles,
        exclusiones=exclusiones,
        publicado=publicado,
    ) | _campos_auditoria_efemeride(contrato, canal, intento) | {
        "estado": estado,
        "resultado": resultado,
        "error": error,
        "output_hash": None,
    }
    if validation_errors is not None:
        registro["validation_errors"] = validation_errors
    if extra_fields is not None:
        registro.update(extra_fields)
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado=estado,
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error=error,
    )


def _fallo_destino_efemeride(
    *,
    log_path: Path,
    id_efemeride: str,
    hv_consulta: dict[str, object],
    material: MaterialEfemeride,
    datos: dict[str, object],
    canal: str,
    generator: Generator,
    politica: PoliticaPost,
    correlation_id: str,
    inicio: float,
    procedencia: str,
    borrador: str,
    code: str,
    reconciliation_ref_hash: str | None,
    contrato: ContratoCreativo,
    intento: int,
    elegibles: tuple[Fragmento, ...] | None = None,
    exclusiones: tuple[tuple[Fragmento, str], ...] | None = None,
    publicado: Fragmento | None = None,
) -> ResultadoProceso:
    code_seguro = (
        code if code in DESTINATION_ERROR_CODES else "destination_unavailable"
    )
    registro = _registro_base_efemeride(
        id_efemeride=id_efemeride,
        hv_consulta=hv_consulta,
        material=material,
        datos=datos,
        canal=canal,
        generator=generator,
        politica=politica,
        correlation_id=correlation_id,
        latencia_s=round(time.perf_counter() - inicio, 6),
        procedencia=procedencia,
        elegibles=elegibles,
        exclusiones=exclusiones,
        publicado=publicado,
    ) | _campos_auditoria_efemeride(contrato, canal, intento) | {
        "estado": "FALLIDA",
        "resultado": "destination_failure",
        "error": "Falló la persistencia del borrador",
        "output_hash": _hash_texto(borrador),
        "destination_error_code": code_seguro,
    }
    if code_seguro == code and reconciliation_ref_hash is not None:
        registro["reconciliation_ref_hash"] = reconciliation_ref_hash
    _registrar(log_path, registro)
    return ResultadoProceso(
        estado="FALLIDA",
        borrador_path=None,
        log_path=log_path,
        correlation_id=correlation_id,
        error="Falló la persistencia del borrador",
    )
