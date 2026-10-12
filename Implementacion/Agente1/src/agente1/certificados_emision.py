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
   `linea_descriptiva.objeto_id_linea_descriptiva`: una decisión semántica
   (`apruebo_semantica`) del `responsable_gestion_conocimiento` y una
   utilitaria (`apruebo_utilitaria`) del `coordinador_extension`,
   registradas bajo el tipo `linea_descriptiva` por el mismo Form de
   decisiones. El texto llega por parámetro inyectable; nunca se lee del
   pedido ni se hardcodea.
4. **El lote lo aprueba el rol utilitario.** La aprobación vale por el
   hash de la lista: el objeto del Form de decisiones es
   `sha256("lote_cierre_certificados|<id_actividad>|<hash_lista>")`, así
   que editar la lista después de aprobar cambia el objeto y la aprobación
   anterior no aplica (hay que aprobar de nuevo). El que cargó la lista no
   puede ser su aprobador: si la única aprobación registrada viene de su
   correo, no habilita. Mientras falta la aprobación se declara el objeto
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

La plantilla es la base provisional acordada con campos confirmados por la
SEU el 22/09: encabezado, organización, titular con tratamiento y
documento, actividad con carga horaria, modalidad y fecha, línea
descriptiva aprobada, bloque de firmas del Secretario de Extensión y del
Decano con el espacio de imagen marcado como insumo provisional, y la
declaración de documento provisional sin firma digital. La plantilla
institucional final queda `PENDIENTE_SEU`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .certificados import generar_pdf_certificado
from .confirmaciones import (
    MARCADOR_BORRADOR as MARCADOR_BORRADOR_CORREO,
)
from .confirmaciones import (
    ROL_APROBACION_UTILITARIA,
    _hash,
)
from .decisiones_form import (
    EnlacesDecisiones,
    RegistroDecisiones,
)
from .fuentes import FuenteSolicitudes, FuenteSolicitudesError
from .linea_descriptiva import (
    linea_descriptiva_aprobada,
    objeto_id_linea_descriptiva,
)

HU = "HU-014"
CONTRACT_VERSION = "certificado_emision_lote_v1"
TEMPLATE_VERSION = "certificado_base_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
LOG_NAME = "emisiones-certificados-hu014.jsonl"

MARCA_PRUEBA = "DOCUMENTO DE PRUEBA — SIN VALIDEZ"

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
class RevisionLote:
    """Resultado de revisar el registro de decisiones contra el lote."""

    aprobada: bool
    correo_hash_aprobador: str | None
    descalificaciones: tuple[str, ...]


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


def revisar_aprobacion_lote(
    registro_decisiones: RegistroDecisiones,
    *,
    objeto_lote: str,
    cargada_por_correo_hash: str,
) -> RevisionLote:
    """Busca un `apruebo_lote` válido sobre el objeto del lote de cierre.

    Vale sólo una decisión `registrada`, de `tipo` `lote`, con
    `decision` `apruebo_lote`, hecha por el rol utilitario y por un correo
    que no sea el de quien cargó la lista. Las aprobaciones que fallan
    esas condiciones se cuentan en `descalificaciones` para la auditoría:
    existen, pero no habilitan.
    """

    aprobada = False
    correo_hash_aprobador = None
    descalificaciones: list[str] = []
    for entrada in registro_decisiones.procesadas():
        if (
            entrada.get("tipo") != "lote"
            or entrada.get("objeto_id") != objeto_lote
            or entrada.get("decision") != "apruebo_lote"
            or entrada.get("resultado") != "registrada"
        ):
            continue
        if entrada.get("rol") != ROL_APROBACION_UTILITARIA:
            descalificaciones.append("aprobador_rol_no_utilitario")
            continue
        if entrada.get("correo_hash") == cargada_por_correo_hash:
            descalificaciones.append("aprobador_es_cargador")
            continue
        aprobada = True
        correo_hash_aprobador = entrada.get("correo_hash")
    return RevisionLote(
        aprobada=aprobada,
        correo_hash_aprobador=correo_hash_aprobador,
        descalificaciones=tuple(descalificaciones),
    )


_TEXTO_POR_CONDICION = {
    "asistencia": ("CERTIFICADO DE ASISTENCIA", "asistió a"),
    "aprobacion": ("CERTIFICADO DE APROBACIÓN", "aprobó"),
}


def renderizar_certificado_lote(
    *,
    persona: PersonaCierre,
    actividad: dict[str, str],
    linea_descriptiva: str,
    id_certificado: str,
    firmantes: tuple[Firmante, ...] = FIRMANTES_DECLARADOS,
) -> tuple[str, str]:
    """Arma (título, cuerpo) del certificado con la plantilla base fija.

    Determinista y sin modelo: un certificado es un documento
    administrativo, el texto lo dan los datos de la fila y de la actividad.
    La primera línea del cuerpo es la marca de prueba permanente; el PDF
    de muestra agrega además `BORRADOR — NO EMITIR` por arriba.
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
    correo_aprobador: str,
    solicitante_correo: str,
    directorio_salida: Path | str,
    firmantes: tuple[Firmante, ...] = FIRMANTES_DECLARADOS,
    correlation_id: str | None = None,
) -> ResultadoEmisionCertificados:
    """Corre el circuito de emisión del lote de cierre de una actividad.

    `destino` es el puerto de correo con firma
    `entregar(*, idempotency_key, destinatario, asunto, cuerpo, adjunto=None)`:
    en vivo es `GmailDestinoConfirmaciones` (la lista de prueba se valida
    adentro, antes de la red) y offline un destino de archivo.
    `correo_aprobador` es el correo del rol utilitario que aprueba el lote.
    `solicitante_correo` es la identidad verificada del canal: la de quien
    disparó el pedido y cargó la lista de cierre. Sirve para dos cosas: su
    hash queda en la auditoría como `solicitante_hash`, y una aprobación del
    lote que venga de ese mismo correo no habilita (quien carga la lista no
    puede aprobarla).
    """

    cid = correlation_id or _hash(f"emision|{id_actividad}")[:16]
    salida = Path(directorio_salida)
    salida.mkdir(parents=True, exist_ok=True)
    log_path = salida / LOG_NAME
    solicitante_hash = _hash(
        solicitante_correo.lower().strip()
        if isinstance(solicitante_correo, str)
        else ""
    )
    cargada_por_hash = solicitante_hash

    def evento(nombre: str, **campos) -> None:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "schema": CONTRACT_VERSION,
                        "hu": HU,
                        "correlation_id": cid,
                        "evento": nombre,
                        **campos,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
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
        correo_aprobador if isinstance(correo_aprobador, str) else ""
    ) is None or _MAIL_RE.fullmatch(
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
    if not linea_descriptiva_aprobada(
        registro_decisiones,
        id_actividad=id_actividad.strip(),
        linea=texto_linea,
    ):
        evento(
            "linea_descriptiva_no_aprobada",
            objeto_linea=objeto_id_linea_descriptiva(
                id_actividad.strip(), texto_linea
            ),
        )
        return resultado(
            "PENDIENTE_APROBACION",
            "la línea descriptiva no tiene las dos aprobaciones",
            "linea_descriptiva_no_aprobada",
        )
    evento("linea_descriptiva_aprobada")

    # 4. El lote lo aprueba el rol utilitario, atado al hash de la lista.
    revision = revisar_aprobacion_lote(
        registro_decisiones,
        objeto_lote=objeto_lote,
        cargada_por_correo_hash=cargada_por_hash,
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
        _titulo, cuerpo_muestra = renderizar_certificado_lote(
            persona=personas[0],
            actividad=actividad,
            linea_descriptiva=texto_linea,
            id_certificado=f"cert-{id_actividad.strip()}-{personas[0].dni}",
            firmantes=firmantes,
        )
        pdf_muestra = generar_pdf_certificado(cuerpo_muestra, borrador=True)
        enlace = enlaces.enlace(
            tipo="lote", objeto_id=objeto_lote, decision="apruebo_lote"
        )
        cuerpo_aviso = (
            MARCADOR_BORRADOR_CORREO
            + "\n\n"
            + "Se pidió la emisión de los certificados de una actividad y el "
            "lote de cierre quedó pendiente de su aprobación.\n\n"
            f"Actividad: {actividad['titulo']} ({id_actividad.strip()})\n"
            f"Personas en la lista de cierre: {len(personas)}\n"
            "Adjunto: un certificado de muestra marcado como borrador "
            "(documento de prueba, sin validez).\n\n"
            "Para aprobar el lote responda `apruebo_lote` en el Form de "
            "decisiones desde este enlace:\n"
            f"{enlace}\n"
        )
        try:
            destino.entregar(
                idempotency_key=_hash(f"aviso_lote|{objeto_lote}"),
                destinatario=correo_aprobador,
                asunto=(
                    "[Agente 1] Aprobación pendiente — lote de certificados "
                    f"{id_actividad.strip()}"
                ),
                cuerpo=cuerpo_aviso,
                adjunto=_adjunto_pdf("certificado-muestra.pdf", pdf_muestra),
            )
        except Exception as exc:
            code = getattr(exc, "code", "aviso_aprobacion_fallido")
            evento("aviso_aprobacion", resultado="fallido", code=str(code))
            return resultado(
                "FALLIDA",
                "no se pudo enviar el correo de aprobación del lote",
                str(code),
            )
        evento("aviso_aprobacion", resultado="enviado")
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
        titulo, cuerpo = renderizar_certificado_lote(
            persona=persona,
            actividad=actividad,
            linea_descriptiva=texto_linea,
            id_certificado=id_certificado,
            firmantes=firmantes,
        )
        pdf = generar_pdf_certificado(cuerpo, borrador=False)
        destinatario_hash = _hash(persona.mail.lower())
        certificado_ref_hash = _hash(id_certificado)
        holder_hash = _hash(
            f"{persona.nombre}|{persona.apellido}|{persona.dni}"
        )
        try:
            destino.entregar(
                idempotency_key=_hash(
                    f"entrega_cert|{objeto_lote}|{id_certificado}"
                ),
                destinatario=persona.mail,
                asunto=f"[Agente 1] Certificado — {actividad['titulo']}",
                cuerpo=(
                    MARCADOR_BORRADOR_CORREO
                    + "\n\n"
                    + f"{persona.tratamiento} {persona.apellido}:\n\n"
                    "Se adjunta el certificado correspondiente a la "
                    f"actividad {actividad['titulo']}.\n"
                    "Es un documento de prueba: no tiene validez "
                    "institucional.\n"
                ),
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


def construir_emisor_certificados(**config):
    """Adapta `procesar_emision_certificados` al callable del seam.

    `interpretar_solicitud` despacha la intención `emitir_certificados` con
    dos argumentos (`id_actividad` y `solicitante`); esta fábrica captura el
    resto de la configuración —fuente, lector de lista, línea, registro y
    enlaces de decisiones, destino, correo del aprobador, directorio— y
    devuelve el callable listo para `emisor_certificados=...`.
    `solicitante` es la `IdentidadSolicitante` del canal: su identificador
    verificado se usa como `solicitante_correo`, la identidad que dispara
    el pedido y que quedó registrada como cargadora de la lista.
    """

    def emisor(
        *, id_actividad: str, solicitante
    ) -> ResultadoEmisionCertificados:
        return procesar_emision_certificados(
            id_actividad=id_actividad,
            solicitante_correo=getattr(solicitante, "identificador", ""),
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
        with self._path.open("a", encoding="utf-8") as archivo:
            archivo.write(
                json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n"
            )


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
    "renderizar_certificado_lote",
    "revisar_aprobacion_lote",
]
