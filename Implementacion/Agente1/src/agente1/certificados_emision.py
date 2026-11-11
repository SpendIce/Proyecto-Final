"""HU-014 (#75) — Emisión en vivo de certificados con lista de cierre.

El circuito de `certificados.py` (#29, #53) es el ciclo de vida por
documento sobre el fake: un certificado, sus aprobaciones y una emisión
simulada. Este módulo agrega la otra mitad de la HU: la emisión real
acotada de un lote completo sobre la lista de cierre de una actividad, con
la autorización organizada por el Form de decisiones de #72 y la entrega
por `gmail.send` con la lista de prueba de #40.

El disparo es un pedido del canal («emití los certificados de
<actividad>», intención `emitir_certificados` del catálogo
`intenciones_v2`). No hay ningún trigger por cambio de estado: el disparo
automático al cerrar la actividad es HU-015 y queda fuera de este ticket.

El circuito, en orden:

1. **La actividad da los datos institucionales.** El título, la carga
   horaria, la modalidad, la fecha y la organización salen del registro de
   actividades (`FuenteSolicitudes`), nunca del texto del pedido ni de la
   lista.
2. **La lista de cierre se lee cruda.** Es una Sheet D2 cargada por el
   Auxiliar de Curso (fuera del repo, declarada por configuración) con
   columnas posicionales `nombre|apellido|dni|mail|tratamiento|condicion`.
   `condicion` sólo admite `asistencia` o `aprobacion`, exactas: el agente
   no infiere la condición, y una fila vacía o inválida bloquea el lote
   entero, no salta.
3. **La línea descriptiva tiene que estar aprobada.** Ningún PDF sale sin
   la aprobación de #74 sobre el objeto
   `linea_descriptiva-<id_actividad>-<sha256>` que define
   `linea_descriptiva.objeto_id_linea_descriptiva`: una sola decisión
   (`apruebo_contenido`) de la persona autorizada (`APROBADOR_CONTENIDO`),
   registrada bajo el tipo `linea_descriptiva` por el mismo Form de
   decisiones. El texto llega por parámetro inyectable; nunca se lee del
   pedido ni se hardcodea.
4. **El lote lo aprueba quien lo genera.** Por la designación vigente
   (#125) no hay «aprobador final de certificados»: la única aprobación
   que habilita es la `apruebo_lote` registrada por la misma persona
   autorizada que disparó la emisión y cargó la lista, con rol
   `APROBADOR_CONTENIDO`. La aprobación vale por el
   hash de la lista: el objeto del Form de decisiones es
   `sha256("lote_cierre_certificados|<id_actividad>|<hash_lista>")`, así
   que editar la lista después de aprobar cambia el objeto y la aprobación
   anterior no aplica (hay que aprobar de nuevo). Una aprobación que viene
   de otro correo o de alguien sin el rol no habilita. Mientras falta la
   aprobación se declara el objeto
   pendiente y se manda el correo de aprobación con el enlace al Form y un
   PDF de muestra marcado `BORRADOR — NO EMITIR`.
5. **La entrega va por Gmail con lista de prueba.** Un correo por
   titular, con el PDF adjunto, desde la cuenta técnica. Un destinatario
   fuera de la lista rechaza antes de la red y no reintenta: esa entrega
   queda `FALLIDA` y el lote informa `EMITIDA_PARCIAL`.
6. **Marca de prueba permanente.** Todo PDF emitido lleva
   `DOCUMENTO DE PRUEBA — SIN VALIDEZ` como primera línea mientras rija la
   lista sintética. La muestra previa a la aprobación lleva además
   `BORRADOR — NO EMITIR`, así el documento que ve el aprobador no se
   confunde con el que recibe el titular.
7. **Retención mínima.** La auditoría guarda sólo hashes: del
   solicitante, de la lista, de cada titular (identidad, destinatario y
   PDF). Los PDFs viven en memoria el tiempo que tarda el `messages/send`
   y la lista no se persiste: la fuente queda en la Sheet D2 del Aux. Las
   imágenes de firma, cuando la SEU las entregue, viven en una carpeta D2
   restringida fuera del repo; ninguna imagen de firma entra a Git, y la
   marca de prueba se mantiene igual.

La plantilla depende de la condición declarada en la lista (#126): la de
**aprobación** compone el diseño institucional recibido de la SEU el
19/10/2026 —A4 horizontal, doble borde, símbolo FIE, bloques de Secretario
y Decano— en `certificados_plantilla_seu.py`, con símbolo y firmas leídos
de la carpeta restringida por `recursos_firma` (fuera de Git; el recurso
ausente deja su espacio marcado, nunca una firma inventada). La de
**asistencia** sigue siendo la base provisional acordada con campos
confirmados por la SEU el 22/09 —encabezado, organización, titular con
tratamiento y documento, actividad con carga horaria, modalidad y fecha,
línea descriptiva aprobada, bloque de firmas del Secretario de Extensión
y del Decano con el espacio de imagen marcado como insumo provisional, y
la declaración de documento provisional sin firma digital— porque la
variante institucional de asistencia no fue recibida y queda pendiente
de definición SEU. La auditoría de cada entrega deja la plantilla usada.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from .certificados import MARCA_PRUEBA, generar_pdf_certificado
from .certificados_plantilla_seu import (
    FIRMANTES_SEU,
    RECURSOS_IMAGEN,
    TEMPLATE_VERSION_SEU,
    DatosCertificadoSeu,
    RecursosFirma,
    RecursosFirmaDirectorio,
    fecha_lugar_texto,
    generar_pdf_certificado_seu,
    horas_reloj_texto,
)
from .confirmaciones import (
    MARCADOR_BORRADOR as MARCADOR_BORRADOR_CORREO,
)
from .confirmaciones import (
    ROL_APROBADOR_CONTENIDO,
    _hash,
)
from .decisiones_form import (
    EnlacesDecisiones,
    RegistroDecisiones,
)
from .fuentes import FuenteSolicitudes, FuenteSolicitudesError
from .linea_descriptiva import (
    RevisionLote,
    objeto_id_linea_descriptiva,
    revisar_aprobacion_lote,
    revisar_linea_descriptiva,
)
from .plantillas_aprobadas import (
    PLANTILLA_TIPO_MISSING,
    PLANTILLA_VERSION_NO_APROBADA,
    PlantillaCorreo,
    id_version_plantilla,
    plantilla_version_registrada,
    renderizar_plantilla,
    validar_forma_plantilla,
)
from .registro_auditoria import escribir_registro

HU = "HU-014"
CONTRACT_VERSION = "certificado_emision_lote_v1"
TEMPLATE_VERSION = "certificado_base_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
LOG_NAME = "emisiones-certificados-hu014.jsonl"

CONDICIONES_CIERRE = frozenset({"asistencia", "aprobacion"})
COLUMNAS_LISTA_CIERRE = (
    "nombre",
    "apellido",
    "dni",
    "mail",
    "tratamiento",
    "condicion",
)

_MAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\Z")


@dataclass(frozen=True)
class PersonaCierre:
    """Una fila válida de la lista de cierre: los seis campos, sin más."""

    nombre: str
    apellido: str
    dni: str
    mail: str
    tratamiento: str
    condicion: str


@dataclass(frozen=True)
class Firmante:
    """Nombre y cargo de un bloque de firma del certificado."""

    nombre: str
    cargo: str


# Firmantes declarados con fuente: la bible (convenio FIE–SEU) nombra como
# representante legal de la SEU al Secretario de Extensión Universitaria
# My. Ing. Sebastián Ernesto Moreira y como representante legal de la FIE
# al Col. Ing. David Fiorito. El llamador puede inyectar otros; el bloque
# sigue marcado provisional hasta la plantilla institucional.
FIRMANTES_DECLARADOS = (
    Firmante(
        nombre="Sebastián Ernesto Moreira",
        cargo="Secretario de Extensión Universitaria",
    ),
    Firmante(
        nombre="David Fiorito",
        cargo="Decano — Facultad de Ingeniería del Ejército",
    ),
)


class ListaCierreError(RuntimeError):
    """La lista de cierre no cumple el contrato. Bloquea el lote entero.

    `code` es la etiqueta auditable; `fila` es el índice 1-based de la
    fila que disparó el bloqueo (un número, no un dato personal).
    """

    def __init__(self, code: str, fila: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.fila = fila


class LectorListaCierre(Protocol):
    """Puerto de lectura cruda de la lista de cierre.

    Lo implementan `GoogleSheetsLectorValores` (Sheet D2, `values.get`) y
    `LectorValoresCsv` de `canal_form` (réplica offline para la demo): las
    dos devuelven filas posicionales de celdas de texto, sin escritura.
    """

    def leer_valores(self) -> list[object]: ...


@dataclass(frozen=True)
class ResultadoEmisionCertificados:
    """Lo que el emisor devuelve al despacho del canal.

    `estado` es `PENDIENTE_APROBACION` (falta línea o lote, quizá con el
    aviso ya enviado), `EMITIDA` (todas las entregas ok), `EMITIDA_PARCIAL`
    (alguna entrega rechazada o fallida), `INVALIDA` (contrato del pedido
    o de la lista roto) o `FALLIDA` (falla del medio o de configuración).
    """

    estado: str
    correlation_id: str
    log_path: str
    resumen: str
    error: str | None = None
    emitidas: int = 0
    entregas_fallidas: int = 0


def parsear_lista_cierre(filas: list[object]) -> tuple[PersonaCierre, ...]:
    """Valida la lista de cierre entera. Una fila mala bloquea el lote.

    Reglas: fila con las seis columnas no vacías, mail con forma válida y
    `condicion` exacta (`asistencia` o `aprobacion`, sin inferencias).
    La fila de encabezado se salta sólo si coincide literal con los
    nombres de columna. Duplicados por dni o por mail bloquean también:
    un dni o un correo repetido significa lista mal armada, no dos
    certificados.
    """

    personas: list[PersonaCierre] = []
    dnis: set[str] = set()
    mails: set[str] = set()
    for indice, fila in enumerate(filas, start=1):
        if not isinstance(fila, (list, tuple)):
            raise ListaCierreError("lista_cierre_fila_invalida", fila=indice)
        celdas = [_limpiar_celda(c) for c in fila[: len(COLUMNAS_LISTA_CIERRE)]]
        if all(not c for c in celdas):
            continue  # fila vacía de la planilla, no un dato
        if celdas == list(COLUMNAS_LISTA_CIERRE):
            continue  # encabezado declarado por el Aux
        if len(fila) < len(COLUMNAS_LISTA_CIERRE):
            raise ListaCierreError("lista_cierre_fila_invalida", fila=indice)
        nombre, apellido, dni, mail, tratamiento, condicion = celdas
        if not all((nombre, apellido, dni, mail, tratamiento)):
            raise ListaCierreError("lista_cierre_fila_invalida", fila=indice)
        if not condicion:
            raise ListaCierreError("lista_cierre_condicion_vacia", fila=indice)
        if condicion not in CONDICIONES_CIERRE:
            raise ListaCierreError(
                "lista_cierre_condicion_invalida", fila=indice
            )
        if _MAIL_RE.fullmatch(mail) is None:
            raise ListaCierreError("lista_cierre_fila_invalida", fila=indice)
        if dni in dnis or mail in mails:
            raise ListaCierreError("lista_cierre_duplicada", fila=indice)
        dnis.add(dni)
        mails.add(mail)
        personas.append(
            PersonaCierre(
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                mail=mail,
                tratamiento=tratamiento,
                condicion=condicion,
            )
        )
    if not personas:
        raise ListaCierreError("lista_cierre_vacia")
    return tuple(personas)


def hash_lista_cierre(personas: tuple[PersonaCierre, ...]) -> str:
    """Hash canónico de la lista completa, en el orden de la planilla.

    Es el ancla de la aprobación del lote: cualquier edición (alta, baja,
    cambio de condición, reorden) cambia el hash y por lo tanto el objeto
    que hay que aprobar.
    """

    filas = [
        [p.nombre, p.apellido, p.dni, p.mail, p.tratamiento, p.condicion]
        for p in personas
    ]
    return _hash(
        CONTRACT_VERSION
        + "|"
        + json.dumps(filas, ensure_ascii=False, separators=(",", ":"))
    )


def objeto_lote_cierre(id_actividad: str, hash_lista: str) -> str:
    """El objeto del Form de decisiones para el lote de cierre.

    Un hash puro de 64 hex: siempre entra en el `ID_RE` de pendientes y el
    binding con actividad + lista es exacto. El log de la emisión guarda
    `id_actividad` y `hash_lista` junto al objeto para poder cruzarlos.
    """

    return _hash(
        f"lote_cierre_certificados|{id_actividad.strip()}|{hash_lista}"
    )


_TEXTO_POR_CONDICION = {
    "asistencia": ("CERTIFICADO DE ASISTENCIA", "asistió a"),
    "aprobacion": ("CERTIFICADO DE APROBACIÓN", "aprobó"),
}

# La SEU entregó plantilla sólo para `aprobacion` (#126): esa condición se
# compone con el diseño recibido; `asistencia` sigue con la provisional y
# queda declarada pendiente de la variante institucional o su adaptación
# avalada. El evento de cada entrega deja la plantilla usada.
_PLANTILLA_POR_CONDICION = {
    "aprobacion": TEMPLATE_VERSION_SEU,
    "asistencia": TEMPLATE_VERSION,
}


def _pdf_para_persona(
    *,
    persona: PersonaCierre,
    actividad: dict[str, str],
    linea_descriptiva: str,
    id_certificado: str,
    firmantes: tuple[Firmante, ...],
    recursos_firma: RecursosFirma | None,
    borrador: bool,
    marcar_prueba: bool = True,
    plantilla_asistencia: PlantillaCorreo | None = None,
) -> tuple[bytes, str]:
    """El PDF de una persona con la plantilla que dicta su condición.

    `aprobacion` compone el diseño SEU recibido (#126) con los recursos
    de firma de la custodia; `asistencia` queda en la plantilla
    provisional hasta que la SEU entregue o avale su variante — el
    `plantilla` devuelto es la traza de cuál salió.

    `marcar_prueba` (#142) se apaga sólo en la emisión de modo
    producción, donde el diseño SEU sale como pieza real sin la línea
    «DOCUMENTO DE PRUEBA». `plantilla_asistencia` (#142) sólo llega en
    modo producción para la condición `asistencia`: el cuerpo sale de la
    redacción aprobada en vez de la provisional, sin la marca de prueba,
    y la traza `plantilla` de la auditoría nombra la versión registrada
    de esa plantilla, no la provisional que no se usó.
    """

    if persona.condicion == "aprobacion":
        datos = DatosCertificadoSeu(
            nombre=persona.nombre,
            apellido=persona.apellido,
            dni=persona.dni,
            actividad=actividad["titulo"],
            horas=horas_reloj_texto(actividad["duracion_horas"]),
            fecha=fecha_lugar_texto(
                actividad.get("fecha_fin") or actividad["fecha_inicio"]
            ),
            linea_descriptiva=linea_descriptiva,
        )
        pdf = generar_pdf_certificado_seu(
            datos,
            recursos=recursos_firma,
            borrador=borrador,
            marcar_prueba=marcar_prueba,
        )
        return pdf, _PLANTILLA_POR_CONDICION[persona.condicion]
    _titulo, cuerpo = renderizar_certificado_lote(
        persona=persona,
        actividad=actividad,
        linea_descriptiva=linea_descriptiva,
        id_certificado=id_certificado,
        firmantes=firmantes,
        plantilla=plantilla_asistencia,
    )
    # La traza nombra la plantilla efectivamente usada: en producción, la
    # versión registrada de `certificado_asistencia` — el id que el
    # registro de decisiones autorizó —; en prueba, la provisional.
    traza = (
        id_version_plantilla("certificado_asistencia", plantilla_asistencia)
        if plantilla_asistencia is not None
        else _PLANTILLA_POR_CONDICION[persona.condicion]
    )
    return generar_pdf_certificado(cuerpo, borrador=borrador), traza


# Variables que la plantilla aprobada de un certificado puede nombrar
# (#142): el conjunto cierra el dato que el circuito completa, así que una
# plantilla que declare otra cosa se rechaza al cargar la corrida.
VARIABLES_CERTIFICADO = frozenset(
    {
        "encabezado",
        "verbo",
        "titulo",
        "organiza",
        "tratamiento",
        "nombre",
        "apellido",
        "dni",
        "duracion_horas",
        "modalidad",
        "fechas",
        "linea_descriptiva",
        "referencia",
        "bloque_firmas",
    }
)

# Las del correo que lleva el PDF al titular: cubre el asunto y el cuerpo.
VARIABLES_CORREO_CERTIFICADO = frozenset(
    {"tratamiento", "nombre", "apellido", "titulo", "id_actividad"}
)


def _modo_envio_destino(destino: object) -> str:
    """El modo de envío que declara el destino; ausente es `prueba`.

    El destino de archivo y los dobles de test no conocen modos: conservan
    el comportamiento de siempre, que es el de prueba. `DestinoCorreoArchivo`
    se declara acá mismo porque vive en este módulo.
    """

    from .gmail_envio import MODO_ENVIO_PRODUCCION, MODO_ENVIO_PRUEBA

    return (
        MODO_ENVIO_PRODUCCION
        if getattr(destino, "modo", None) == MODO_ENVIO_PRODUCCION
        else MODO_ENVIO_PRUEBA
    )


def _modo_entrega(destino: object) -> str:
    """Identificador del destino que entregó, para la línea de auditoría.

    Mismo vocabulario que `confirmaciones.modo_entrega` más
    `archivo_offline` para el destino de archivo de este módulo: es lo que
    distingue en `delivery_mode` un envío por lista de prueba de uno por la
    lista aprobada.
    """

    if type(destino) is DestinoCorreoArchivo:
        return "archivo_offline"
    from .confirmaciones import modo_entrega

    return modo_entrega(destino)


def renderizar_certificado_lote(
    *,
    persona: PersonaCierre,
    actividad: dict[str, str],
    linea_descriptiva: str,
    id_certificado: str,
    firmantes: tuple[Firmante, ...] = FIRMANTES_DECLARADOS,
    plantilla: PlantillaCorreo | None = None,
) -> tuple[str, str]:
    """Arma (título, cuerpo) del certificado con la plantilla base fija.

    Determinista y sin modelo: un certificado es un documento
    administrativo, el texto lo dan los datos de la fila y de la actividad.
    La primera línea del cuerpo es la marca de prueba permanente; el PDF
    de muestra agrega además `BORRADOR — NO EMITIR` por arriba.

    `plantilla` (#142) sólo llega en modo producción: el cuerpo sale de la
    redacción aprobada por condición con las mismas variables, sin la
    marca de prueba ni la declaración provisional. Las variables que el
    texto aprobado puede nombrar son las de `VARIABLES_CERTIFICADO`.
    """

    encabezado, verbo = _TEXTO_POR_CONDICION[persona.condicion]
    titulo = f"{encabezado} — {actividad['titulo'].strip()}"
    fechas = actividad["fecha_inicio"].strip()
    fecha_fin = (actividad.get("fecha_fin") or "").strip()
    if fecha_fin and fecha_fin != fechas:
        fechas = f"{fechas} al {fecha_fin}"
    bloque_firmas = "\n".join(
        f"________________________________\n{f.nombre.strip()}\n{f.cargo.strip()}"
        for f in firmantes
    )
    if plantilla is not None:
        valores = {
            "encabezado": encabezado,
            "verbo": verbo,
            "titulo": actividad["titulo"].strip(),
            "organiza": actividad["organiza"].strip(),
            "tratamiento": persona.tratamiento,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "dni": persona.dni,
            "duracion_horas": actividad["duracion_horas"].strip(),
            "modalidad": actividad["modalidad"].strip(),
            "fechas": fechas,
            "linea_descriptiva": linea_descriptiva.strip(),
            "referencia": id_certificado,
            "bloque_firmas": bloque_firmas,
        }
        return titulo, renderizar_plantilla(plantilla.cuerpo, valores)
    cuerpo = (
        f"{MARCA_PRUEBA}\n\n"
        f"{encabezado}\n\n"
        f"{actividad['organiza'].strip()} certifica que\n"
        f"{persona.tratamiento} {persona.nombre} {persona.apellido} "
        f"(documento {persona.dni})\n"
        f"{verbo} la actividad: {actividad['titulo'].strip()}.\n"
        f"Carga horaria: {actividad['duracion_horas'].strip()} horas. "
        f"Modalidad: {actividad['modalidad'].strip()}.\n"
        f"Fecha: {fechas}\n"
        f"{linea_descriptiva.strip()}\n"
        f"Referencia: {id_certificado}\n\n"
        f"{bloque_firmas}\n\n"
        "[espacio reservado para la imagen de firma: insumo provisional "
        "PENDIENTE_SEU]\n\n"
        "Documento provisional sin firma digital ni validez institucional.\n"
    )
    return titulo, cuerpo


def procesar_emision_certificados(
    *,
    id_actividad: str,
    fuente: FuenteSolicitudes,
    lector_lista: LectorListaCierre,
    linea_descriptiva: str | None,
    registro_decisiones: RegistroDecisiones,
    enlaces: EnlacesDecisiones,
    destino,
    solicitante_correo: str,
    solicitante_rol: str | None = None,
    directorio_salida: Path | str,
    firmantes: tuple[Firmante, ...] = FIRMANTES_DECLARADOS,
    recursos_firma: RecursosFirma | None = None,
    plantillas_aprobadas: Mapping[str, PlantillaCorreo] | None = None,
    correlation_id: str | None = None,
) -> ResultadoEmisionCertificados:
    """Corre el circuito de emisión del lote de cierre de una actividad.

    `destino` es el puerto de correo con firma
    `entregar(*, idempotency_key, destinatario, asunto, cuerpo, adjunto=None)`:
    en vivo es `GmailDestinoConfirmaciones` (la lista de prueba se valida
    adentro, antes de la red) y offline un destino de archivo.
    `solicitante_correo` es la identidad verificada del canal: la de quien
    disparó el pedido y cargó la lista de cierre, es decir quien genera el
    lote. Sirve para tres cosas: su hash queda en la auditoría como
    `solicitante_hash`, es el correo que tiene que registrar la
    `apruebo_lote` — quien genera el lote lo aprueba (#125) — y es el
    destinatario del aviso de aprobación pendiente.
    `solicitante_rol` es el rol del padrón de quien dispara: la designación
    vigente exige `APROBADOR_CONTENIDO` para pedir o generar el lote, así
    «lo aprueba quien lo genera» siempre tiene a alguien habilitado; un
    rol operativo recibe `solicitante_rol_no_autorizado` en vez de un lote
    que nadie puede aprobar. Sin el dato la barrera no corre (los runners
    viejos la documentan pendiente); el despacho por canal siempre la trae.
    `recursos_firma` es el puerto de custodia del símbolo y las firmas de
    la plantilla SEU de aprobación (#126): resuelve imágenes desde la
    carpeta restringida configurada fuera del repo; sin él, los espacios
    de firma salen marcados como insumo no provisto.

    El modo lo declara el destino (#142): con `modo="produccion"` el
    certificado de `aprobacion` sale del diseño SEU ya recibido (#126), el
    de `asistencia` —aún pendiente— exige la plantilla aprobada
    `certificado_asistencia` de `plantillas_aprobadas` y el correo del
    titular sale de `correo_certificado` del mismo archivo, sin la marca
    de prueba ni la de borrador. La aprueba la SEU, por la definición del
    11/11: aprueba quien genera la pieza. Sin las plantillas que el lote
    necesita la corrida es `INVALIDA` con `approved_template_missing`
    antes de mandar nada.
    """

    cid = correlation_id or _hash(f"emision|{id_actividad}")[:16]
    salida = Path(directorio_salida)
    salida.mkdir(parents=True, exist_ok=True)
    log_path = salida / LOG_NAME
    from .gmail_envio import MODO_ENVIO_PRODUCCION

    en_produccion = _modo_envio_destino(destino) == MODO_ENVIO_PRODUCCION
    delivery_mode = _modo_entrega(destino)
    solicitante_hash = _hash(
        solicitante_correo.lower().strip()
        if isinstance(solicitante_correo, str)
        else ""
    )
    generada_por_hash = solicitante_hash

    def evento(nombre: str, **campos) -> None:
        escribir_registro(
            log_path,
            {
                "schema": CONTRACT_VERSION,
                "hu": HU,
                "correlation_id": cid,
                "evento": nombre,
                **campos,
            },
        )

    def resultado(
        estado: str,
        resumen: str,
        error: str | None = None,
        emitidas: int = 0,
        entregas_fallidas: int = 0,
    ) -> ResultadoEmisionCertificados:
        return ResultadoEmisionCertificados(
            estado=estado,
            correlation_id=cid,
            log_path=str(log_path),
            resumen=resumen,
            error=error,
            emitidas=emitidas,
            entregas_fallidas=entregas_fallidas,
        )

    evento(
        "solicitud_emision",
        id_actividad=id_actividad,
        solicitante_hash=solicitante_hash,
    )

    # 0. Pedir o generar el lote exige el rol de contenido (#125, ADR 0018):
    # quien lo aprueba es quien lo genera, así que un rol operativo nunca
    # puede habilitar su propio lote.
    if (
        solicitante_rol is not None
        and solicitante_rol != ROL_APROBADOR_CONTENIDO
    ):
        evento("solicitante_rol_no_autorizado", rol=solicitante_rol)
        return resultado(
            "RECHAZADA",
            "pedir el lote de certificados exige el rol de contenido",
            "solicitante_rol_no_autorizado",
        )

    # 1. La actividad aporta los datos institucionales.
    if not isinstance(id_actividad, str) or not id_actividad.strip():
        evento("actividad_invalida")
        return resultado("INVALIDA", "el pedido no trae actividad", "actividad_invalida")
    try:
        fila_actividad = fuente.obtener(id_actividad.strip())
    except FuenteSolicitudesError as exc:
        evento("actividad_no_disponible", code=exc.code)
        estado = (
            "INVALIDA"
            if exc.code in {"source_request_not_found", "source_duplicate_id"}
            else "FALLIDA"
        )
        return resultado(
            estado, f"la actividad no está disponible ({exc.code})", exc.code
        )
    except Exception:
        evento("actividad_no_disponible", code="fuente_error")
        return resultado(
            "FALLIDA", "la fuente de actividades falló", "fuente_error"
        )

    actividad = {
        "titulo": (fila_actividad.get("titulo") or "").strip(),
        "duracion_horas": (fila_actividad.get("duracion_horas") or "").strip(),
        "modalidad": (fila_actividad.get("modalidad") or "").strip(),
        "fecha_inicio": (fila_actividad.get("fecha_inicio") or "").strip(),
        "fecha_fin": (fila_actividad.get("fecha_fin") or "").strip(),
        "organiza": (fila_actividad.get("organiza") or "").strip(),
    }
    if not all(
        (
            actividad["titulo"],
            actividad["duracion_horas"],
            actividad["modalidad"],
            actividad["fecha_inicio"],
            actividad["organiza"],
        )
    ):
        evento("actividad_datos_incompletos")
        return resultado(
            "INVALIDA",
            "a la actividad le faltan datos para certificar",
            "actividad_datos_incompletos",
        )

    if _MAIL_RE.fullmatch(
        solicitante_correo if isinstance(solicitante_correo, str) else ""
    ) is None:
        evento("config_correo_invalido")
        return resultado(
            "INVALIDA",
            "la configuración de correos del circuito es inválida",
            "config_correo_invalido",
        )

    # 2. La lista de cierre, cruda y entera.
    try:
        filas = lector_lista.leer_valores()
    except FuenteSolicitudesError as exc:
        evento("lista_no_disponible", code=exc.code)
        return resultado(
            "FALLIDA", f"la lista de cierre no está disponible ({exc.code})", exc.code
        )
    except Exception:
        evento("lista_no_disponible", code="lista_cierre_unavailable")
        return resultado(
            "FALLIDA", "la lista de cierre no está disponible", "lista_cierre_unavailable"
        )
    try:
        personas = parsear_lista_cierre(filas)
    except ListaCierreError as exc:
        evento("lista_invalida", code=exc.code, fila=exc.fila)
        return resultado(
            "INVALIDA",
            f"la lista de cierre no habilita el lote ({exc.code})",
            exc.code,
        )
    hash_lista = hash_lista_cierre(personas)
    objeto_lote = objeto_lote_cierre(id_actividad.strip(), hash_lista)
    evento(
        "lista_validada",
        cantidad=len(personas),
        hash_lista=hash_lista,
        objeto_lote=objeto_lote,
    )

    # 2b. En producción el correo del titular sale de la plantilla aprobada
    # `correo_certificado` (#142) y, si el lote tiene `asistencia` —aún sin
    # diseño institucional—, de `certificado_asistencia`; `aprobacion` ya
    # compone el diseño SEU recibido (#126) y no exige entrada. Que el
    # archivo las declare no alcanza: cada versión tiene que tener la
    # `apruebo_contenido` registrada en `registro_decisiones` (definición
    # del 11/11, #125). Y para el diseño SEU la custodia tiene que
    # resolver el símbolo y todas las firmas: un PDF real no puede salir
    # con «[firma: insumo restringido no provisto]». Cualquier falta es
    # INVALIDA antes de entregar al primer titular.
    plantillas = dict(plantillas_aprobadas or {})
    if en_produccion:
        requeridas = {"correo_certificado"}
        if any(p.condicion == "asistencia" for p in personas):
            requeridas.add("certificado_asistencia")
        if not requeridas <= set(plantillas):
            evento("plantillas_aprobadas_incompletas")
            return resultado(
                "INVALIDA",
                "faltan plantillas aprobadas para el modo producción",
                PLANTILLA_TIPO_MISSING,
            )
        for tipo in sorted(requeridas):
            invalida = validar_forma_plantilla(
                plantillas[tipo],
                asunto_requerido=tipo == "correo_certificado",
                variables_permitidas=(
                    VARIABLES_CERTIFICADO
                    if tipo == "certificado_asistencia"
                    else VARIABLES_CORREO_CERTIFICADO
                ),
            )
            if invalida is not None:
                evento("plantillas_aprobadas_invalidas")
                return resultado(
                    "INVALIDA",
                    "una plantilla aprobada no cumple la forma declarada",
                    invalida,
                )
        for tipo in sorted(requeridas):
            if not plantilla_version_registrada(
                registro_decisiones,
                tipo=tipo,
                plantilla=plantillas[tipo],
            ):
                evento("plantilla_version_no_aprobada", tipo=tipo)
                return resultado(
                    "INVALIDA",
                    "la plantilla no tiene la aprobación registrada "
                    "sobre su versión",
                    PLANTILLA_VERSION_NO_APROBADA,
                )
        correo_certificado = plantillas["correo_certificado"]
        if any(p.condicion == "aprobacion" for p in personas):
            requeridos = set(RECURSOS_IMAGEN) | {
                f.recurso for f in FIRMANTES_SEU if f.recurso is not None
            }
            faltantes = [
                nombre
                for nombre in sorted(requeridos)
                if recursos_firma is None
                or recursos_firma.leer(nombre) is None
            ]
            if faltantes:
                evento(
                    "recursos_firma_incompletos",
                    cantidad_faltantes=len(faltantes),
                )
                return resultado(
                    "INVALIDA",
                    "faltan recursos de firma para emitir en producción",
                    "signature_resources_missing",
                )

    # 3. La línea descriptiva: sin su aprobación no hay PDF.
    texto_linea = (
        linea_descriptiva.strip()
        if isinstance(linea_descriptiva, str)
        else ""
    )
    if not texto_linea:
        evento("linea_descriptiva_ausente")
        return resultado(
            "PENDIENTE_APROBACION",
            "falta la línea descriptiva de la actividad (#74)",
            "linea_descriptiva_ausente",
        )
    revision_linea = revisar_linea_descriptiva(
        registro_decisiones,
        id_actividad=id_actividad.strip(),
        linea=texto_linea,
    )
    if not revision_linea.aprobada:
        evento(
            "linea_descriptiva_no_aprobada",
            objeto_linea=objeto_id_linea_descriptiva(
                id_actividad.strip(), texto_linea
            ),
            descalificaciones=revision_linea.descalificaciones,
        )
        return resultado(
            "PENDIENTE_APROBACION",
            "la línea descriptiva no tiene la aprobación registrada",
            "linea_descriptiva_no_aprobada",
        )
    evento("linea_descriptiva_aprobada")

    # 4. El lote lo aprueba quien lo genera, atado al hash de la lista.
    revision = revisar_aprobacion_lote(
        registro_decisiones,
        objeto_lote=objeto_lote,
        generada_por_correo_hash=generada_por_hash,
    )
    evento(
        "autorizacion_lote",
        aprobada=revision.aprobada,
        correo_hash_aprobador=revision.correo_hash_aprobador,
        descalificaciones=list(revision.descalificaciones),
    )
    if not revision.aprobada:
        # El objeto queda declarado pendiente y el correo de aprobación sale
        # con el enlace al Form y un PDF de muestra marcado borrador. El
        # detalle del pendiente registra de qué lote se trata (actividad +
        # cantidad de personas; el hash ya está adentro del objeto).
        enlaces.declarar_y_enlaces(
            tipo="lote",
            objeto_id=objeto_lote,
            detalle={
                "pieza": "certificados_lote_cierre",
                "id_actividad": id_actividad.strip(),
                "personas": str(len(personas)),
            },
        )
        try:
            pdf_muestra, plantilla_muestra = _pdf_para_persona(
                persona=personas[0],
                actividad=actividad,
                linea_descriptiva=texto_linea,
                id_certificado=(
                    f"cert-{id_actividad.strip()}-{personas[0].dni}"
                ),
                firmantes=firmantes,
                recursos_firma=recursos_firma,
                borrador=True,
                plantilla_asistencia=(
                    plantillas.get("certificado_asistencia")
                    if en_produccion
                    else None
                ),
            )
        except Exception as exc:
            # Un render que falla —una `{{variable}}` sin dato en la
            # plantilla aprobada— no puede dejar el aviso a medio camino:
            # queda su línea de auditoría y la corrida cierra como FALLIDA.
            code = getattr(exc, "code", "render_muestra_fallido")
            evento(
                "aviso_aprobacion",
                resultado="fallido",
                code=str(code),
                delivery_mode=delivery_mode,
            )
            return resultado(
                "FALLIDA",
                "no se pudo componer el certificado de muestra",
                str(code),
            )
        enlace = enlaces.enlace(
            tipo="lote", objeto_id=objeto_lote, decision="apruebo_lote"
        )
        # El aviso al aprobador es operativo, no una pieza institucional:
        # en producción sólo pierde la marca de borrador del correo; el PDF
        # de muestra sigue marcado borrador porque es eso, una muestra.
        cuerpo_aviso = (
            ("" if en_produccion else MARCADOR_BORRADOR_CORREO + "\n\n")
            + "Se pidió la emisión de los certificados de una actividad y el "
            "lote de cierre quedó pendiente de su aprobación.\n\n"
            f"Actividad: {actividad['titulo']} ({id_actividad.strip()})\n"
            f"Personas en la lista de cierre: {len(personas)}\n"
            "Adjunto: un certificado de muestra marcado como borrador "
            "(documento de prueba, sin validez).\n\n"
            "El lote lo aprueba quien lo genera. Para aprobarlo responda "
            "`apruebo_lote` en el Form de "
            "decisiones desde este enlace:\n"
            f"{enlace}\n"
        )
        try:
            destino.entregar(
                idempotency_key=_hash(f"aviso_lote|{objeto_lote}"),
                destinatario=solicitante_correo,
                asunto=(
                    "[Agente 1] Aprobación pendiente — lote de certificados "
                    f"{id_actividad.strip()}"
                ),
                cuerpo=cuerpo_aviso,
                adjunto=_adjunto_pdf("certificado-muestra.pdf", pdf_muestra),
            )
        except Exception as exc:
            code = getattr(exc, "code", "aviso_aprobacion_fallido")
            evento(
                "aviso_aprobacion",
                resultado="fallido",
                code=str(code),
                delivery_mode=delivery_mode,
            )
            return resultado(
                "FALLIDA",
                "no se pudo enviar el correo de aprobación del lote",
                str(code),
            )
        evento(
            "aviso_aprobacion",
            resultado="enviado",
            plantilla_muestra=plantilla_muestra,
            delivery_mode=delivery_mode,
        )
        resumen = (
            "el lote quedó pendiente y se envió el correo de aprobación "
            "con el certificado de muestra"
        )
        if revision.descalificaciones:
            resumen += (
                " (había aprobaciones que no habilitan: "
                + ", ".join(revision.descalificaciones)
                + ")"
            )
        return resultado("PENDIENTE_APROBACION", resumen, "lote_no_aprobado")

    # 5. Emisión: un correo con PDF por titular. Sin persistir el PDF ni la
    # fila; la auditoría guarda sólo hashes.
    emitidas = 0
    fallidas = 0
    for persona in personas:
        id_certificado = f"cert-{id_actividad.strip()}-{persona.dni}"
        destinatario_hash = _hash(persona.mail.lower())
        certificado_ref_hash = _hash(id_certificado)
        holder_hash = _hash(
            f"{persona.nombre}|{persona.apellido}|{persona.dni}"
        )
        # El render va adentro del mismo try que la entrega: un error de
        # plantilla —una `{{variable}}` sin dato— no puede cortar el lote a
        # mitad sin su línea `entrega` ni el `cierre` final de auditoría.
        plantilla = _PLANTILLA_POR_CONDICION.get(
            persona.condicion, "desconocida"
        )
        try:
            pdf, plantilla = _pdf_para_persona(
                persona=persona,
                actividad=actividad,
                linea_descriptiva=texto_linea,
                id_certificado=id_certificado,
                firmantes=firmantes,
                recursos_firma=recursos_firma,
                borrador=False,
                marcar_prueba=not en_produccion,
                plantilla_asistencia=(
                    plantillas.get("certificado_asistencia")
                    if en_produccion
                    else None
                ),
            )
            if en_produccion:
                valores_correo = {
                    "tratamiento": persona.tratamiento,
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "titulo": actividad["titulo"],
                    "id_actividad": id_actividad.strip(),
                }
                asunto_correo = renderizar_plantilla(
                    correo_certificado.asunto or "", valores_correo
                )
                cuerpo_correo = renderizar_plantilla(
                    correo_certificado.cuerpo, valores_correo
                )
            else:
                asunto_correo = (
                    f"[Agente 1] Certificado — {actividad['titulo']}"
                )
                cuerpo_correo = (
                    MARCADOR_BORRADOR_CORREO
                    + "\n\n"
                    + f"{persona.tratamiento} {persona.apellido}:\n\n"
                    "Se adjunta el certificado correspondiente a la "
                    f"actividad {actividad['titulo']}.\n"
                    "Es un documento de prueba: no tiene validez "
                    "institucional.\n"
                )
            destino.entregar(
                idempotency_key=_hash(
                    f"entrega_cert|{objeto_lote}|{id_certificado}"
                ),
                destinatario=persona.mail,
                asunto=asunto_correo,
                cuerpo=cuerpo_correo,
                adjunto=_adjunto_pdf(f"{id_certificado}.pdf", pdf),
            )
        except Exception as exc:
            code = getattr(exc, "code", "entrega_failed")
            fallidas += 1
            evento(
                "entrega",
                resultado="fallida",
                code=str(code),
                destinatario_hash=destinatario_hash,
                holder_hash=holder_hash,
                certificado_ref_hash=certificado_ref_hash,
                plantilla=plantilla,
                delivery_mode=delivery_mode,
            )
            continue  # rechazo de política o falla del medio: no reintenta
        emitidas += 1
        evento(
            "entrega",
            resultado="enviada",
            destinatario_hash=destinatario_hash,
            holder_hash=holder_hash,
            certificado_ref_hash=certificado_ref_hash,
            pdf_hash=_hash_bytes(pdf),
            plantilla=plantilla,
            delivery_mode=delivery_mode,
        )
    estado = (
        "EMITIDA"
        if fallidas == 0
        else "EMITIDA_PARCIAL" if emitidas else "FALLIDA"
    )
    evento(
        "cierre",
        emitidas=emitidas,
        entregas_fallidas=fallidas,
        estado=estado,
    )
    return resultado(
        estado,
        f"{emitidas} certificados entregados de {len(personas)} "
        f"({actividad['titulo']})",
        None if fallidas == 0 else f"{fallidas} entregas fallidas",
        emitidas=emitidas,
        entregas_fallidas=fallidas,
    )


def recursos_firma_opcional(directorio: Path | str | None) -> RecursosFirma | None:
    """El puerto de custodia de #126, declarado por configuración.

    En vivo el directorio sale de `AGENTE1_CERTIFICADOS_RECURSOS_DIR` y en
    los runners offline del flag `--recursos`; sin valor declarado el
    circuito corre igual y las firmas salen como insumo no provisto.
    """

    if directorio is None:
        return None
    texto = str(directorio).strip()
    return RecursosFirmaDirectorio(texto) if texto else None


def construir_emisor_certificados(**config):
    """Adapta `procesar_emision_certificados` al callable del seam.

    `interpretar_solicitud` despacha la intención `emitir_certificados` con
    dos argumentos (`id_actividad` y `solicitante`); esta fábrica captura el
    resto de la configuración —fuente, lector de lista, línea, registro y
    enlaces de decisiones, destino, directorio— y
    devuelve el callable listo para `emisor_certificados=...`.
    `solicitante` es la `IdentidadSolicitante` del canal: su identificador
    verificado se usa como `solicitante_correo`, la identidad que dispara
    el pedido y genera el lote — y por eso es quien lo aprueba (#125).
    """

    def emisor(
        *, id_actividad: str, solicitante
    ) -> ResultadoEmisionCertificados:
        return procesar_emision_certificados(
            id_actividad=id_actividad,
            solicitante_correo=getattr(solicitante, "identificador", ""),
            solicitante_rol=getattr(solicitante, "rol", None),
            **config,
        )

    return emisor


def _limpiar_celda(valor: object) -> str:
    """Una celda es texto plano o nada: sin saltos ni tabulaciones."""

    if not isinstance(valor, str):
        return ""
    return re.sub(r"[\r\n\t]+", " ", valor).strip()


class DestinoCorreoArchivo:
    """Destino de correo offline: cada entrega es una línea JSONL.

    Implementa el puerto del emisor —`entregar` con `adjunto` opcional— sin
    red: lo que en vivo sale por `gmail.send` queda escrito en
    `entregas-certificados-offline.jsonl` con destinatario, asunto, cuerpo y,
    del adjunto, sólo nombre, tamaño y sha256. El PDF no se persiste: es la
    misma regla de retención que rige la emisión real.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def modo(self) -> str:
        # El archivo offline es un destino del modo prueba: nunca sale a
        # la red ni a una lista aprobada.
        from .gmail_envio import MODO_ENVIO_PRUEBA

        return MODO_ENVIO_PRUEBA

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        adjunto=None,
    ) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        registro = {
            "idempotency_key": idempotency_key,
            "destinatario": destinatario,
            "asunto": asunto,
            "cuerpo": cuerpo,
        }
        if adjunto is not None:
            registro["adjunto"] = {
                "nombre": adjunto.nombre,
                "tipo_mime": adjunto.tipo_mime,
                "bytes": len(adjunto.contenido),
                "sha256": _hash_bytes(adjunto.contenido),
            }
        escribir_registro(self._path, registro)


def _adjunto_pdf(nombre: str, pdf: bytes):
    """Importa perezoso para no tocar gmail_envio en corridas que no envían."""

    from .gmail_envio import AdjuntoCorreo

    return AdjuntoCorreo(nombre=nombre, contenido=pdf)


def _hash_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


__all__ = [
    "COLUMNAS_LISTA_CIERRE",
    "CONDICIONES_CIERRE",
    "CONTRACT_VERSION",
    "DestinoCorreoArchivo",
    "FIRMANTES_DECLARADOS",
    "Firmante",
    "LectorListaCierre",
    "ListaCierreError",
    "MARCA_PRUEBA",
    "PersonaCierre",
    "POLICY_STATUS",
    "ResultadoEmisionCertificados",
    "RevisionLote",
    "TEMPLATE_VERSION",
    "construir_emisor_certificados",
    "hash_lista_cierre",
    "objeto_lote_cierre",
    "parsear_lista_cierre",
    "procesar_emision_certificados",
    "recursos_firma_opcional",
    "renderizar_certificado_lote",
    "revisar_aprobacion_lote",
]
