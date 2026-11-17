"""Emisión durable del lote de certificados aprobado en la web (#168).

El lote aprobado queda como snapshot en `lotes_certificados` (actividad,
lista de cierre y línea descriptiva). Esta cola sólo guarda el trabajo:
puntero al lote, estado, reserva y contadores. No copia DNI, correos,
nombres ni PDFs; la descarga ZIP se compone al vuelo desde ese snapshot
mientras la retención lo permita.

El motor es el de siempre: `procesar_emision_certificados` recibe una
fuente y un lector que devuelven exactamente el snapshot aprobado, no las
planillas vivas. Así una edición posterior de la Sheet no cambia lo que se
emite ni lo que se descarga.

Decisiones que no se ven en el código:

- **La reserva es un lock real de PostgreSQL.** `FOR UPDATE SKIP LOCKED`
  entrega un trabajo a un solo worker; el token de reserva evita que un
  worker vencido cierre el trabajo de otro. La reserva vencida sin envío
  vuelve a `PENDIENTE`; la que ya estaba `ENVIANDO` pasa a
  `INDETERMINADA` y no se reintenta.
- **No hay reintento de un envío indeterminado.** La cabecera de
  idempotencia de Gmail no deduplica: un worker que cayó después de
  empezar a mandar no puede saber qué correos salieron. El estado queda
  visible para intervención humana, no se vuelve a encolar.
- **La aprobación se repara desde la base.** Si el proceso cayó entre la
  decisión y el asiento JSONL que lee el motor, el worker vuelve a asentar
  el `apruebo_lote` con la identidad y el rol que quedaron en la fila del
  lote. No inventa una aprobación: proyecta una decisión ya registrada.
- **El rol se revalida al ejecutar.** El padrón se consulta de nuevo por
  el hash del generador; si ya no tiene `APROBADOR_CONTENIDO`, el trabajo
  cierra `FALLIDA` sin llamar al motor.
- **El ZIP demo comparte el render real.** Se compone con
  `generar_pdf_certificado_lote`, la misma función que usa la emisión, con
  las marcas permanentes de prueba y borrador. No registra aprobaciones ni
  manda correos.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import secrets
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import psycopg

from .canal_form import PadronRoles
from .certificados_emision import (
    FIRMANTES_DECLARADOS,
    PersonaCierre,
    ResultadoEmisionCertificados,
    generar_pdf_certificado_lote,
    procesar_emision_certificados,
    recursos_firma_opcional,
)
from .certificados_plantilla_seu import RecursosFirma
from .confirmaciones import ROL_APROBADOR_CONTENIDO, EntregaRechazadaError
from .decisiones_form import (
    DECISION_APRUEBO_LOTE,
    RESULTADO_REGISTRADA,
    ROL_ORIGEN_PADRON,
    TIPO_LOTE,
    RegistroDecisiones,
    ResultadoDecision,
)
from .linea_descriptiva import revisar_aprobacion_lote
from .plantillas_aprobadas import PlantillaCorreo
from .workspace_config import ConfiguracionWorkspaceError

MODO_REAL = "real"
MODO_DEMO = "demo"
MODOS = frozenset({MODO_REAL, MODO_DEMO})

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_RESERVADA = "RESERVADA"
ESTADO_ENVIANDO = "ENVIANDO"
ESTADO_EMITIDA = "EMITIDA"
ESTADO_EMITIDA_PARCIAL = "EMITIDA_PARCIAL"
ESTADO_FALLIDA = "FALLIDA"
ESTADO_INDETERMINADA = "INDETERMINADA"
ESTADO_GENERADA_DEMO = "GENERADA_DEMO"
ESTADO_EXPIRADA = "EXPIRADA"

ESTADOS_ACTIVOS = frozenset(
    {ESTADO_PENDIENTE, ESTADO_RESERVADA, ESTADO_ENVIANDO}
)
ESTADOS_TERMINALES = frozenset(
    {
        ESTADO_EMITIDA,
        ESTADO_EMITIDA_PARCIAL,
        ESTADO_FALLIDA,
        ESTADO_INDETERMINADA,
        ESTADO_GENERADA_DEMO,
        ESTADO_EXPIRADA,
    }
)

# Ventana para que un lote aprobado se emita; pasado ese plazo el snapshot
# deja de ser necesario para emitir y la purga puede retirarlo.
VIGENCIA_HORAS = 72
LEASE_SEGUNDOS = 15 * 60
RETENCION_REAL_DIAS = 30
RETENCION_DEMO_DIAS = 2

CODIGO_LOTE_INEXISTENTE = "lote_inexistente"
CODIGO_LOTE_NO_APROBADO = "lote_no_aprobado"
CODIGO_SNAPSHOT_NO_DISPONIBLE = "snapshot_no_disponible"
CODIGO_IDENTIDAD_NO_DISPONIBLE = "identidad_no_disponible"
CODIGO_ROL_REVOCADO = "rol_revocado"
CODIGO_REGISTRO_NO_DISPONIBLE = "registro_decisiones_no_disponible"
CODIGO_PLANTILLAS_CAMBIADAS = "plantillas_cambiadas"
CODIGO_ENTREGA_AMBIGUA = "entrega_ambigua"
CODIGO_ENTREGAS_FALLIDAS = "entregas_fallidas"
CODIGO_DEMO_FUERA_DE_MODO = "demo_fuera_de_modo"
CODIGO_RENDER_DEMO_FALLIDO = "render_demo_fallido"
CODIGO_RESERVA_PERDIDA = "reserva_perdida"
CODIGO_ERROR_MOTOR = "error_motor"
CODIGO_DESTINO_NO_DISPONIBLE = "destino_no_disponible"
CODIGO_LOTE_DEMO_NO_ENVIA = "lote_demo_no_envia"
CODIGO_MODO_DEMO_NO_ENVIA = "modo_demo_no_envia"


class EmisionCertificadosError(RuntimeError):
    """Contrato de la cola roto. `code` es el código auditable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReservaPerdida(RuntimeError):
    code = CODIGO_RESERVA_PERDIDA


@dataclass(frozen=True)
class EmisionCertificados:
    id_emision: str
    id_lote: str
    modo: str
    estado: str
    intentos: int
    reservada_por: str | None
    token_reserva: str | None
    reservada_hasta: datetime | None
    iniciada_en: datetime | None
    terminada_en: datetime | None
    expira_en: datetime
    retencion_hasta: datetime | None
    total: int
    enviadas: int
    fallidas: int
    error_codigo: str | None
    modo_envio: str | None
    plantillas_hash: str | None
    creada_en: datetime
    actualizada_en: datetime


@dataclass(frozen=True)
class ResultadoTrabajoEmision:
    estado: str
    codigo: str | None = None
    enviadas: int = 0
    fallidas: int = 0
    total: int = 0


class RepositorioLotesPuerto(Protocol):
    def obtener(self, id_lote: str) -> Any | None: ...


class RepositorioEmisiones:
    """Cola PostgreSQL de emisión: reserva, cierre y reconciliación."""

    def __init__(
        self, conexion_factory: Callable[[], psycopg.Connection]
    ) -> None:
        self._conexion_factory = conexion_factory

    def encolar(
        self,
        *,
        id_lote: str,
        modo: str = MODO_REAL,
        plantillas_hash: str | None = None,
        ahora: datetime | None = None,
        expira_en: datetime | None = None,
        retencion_hasta: datetime | None = None,
    ) -> EmisionCertificados:
        if modo not in MODOS:
            raise EmisionCertificadosError("modo_invalido")
        id_lote = (id_lote or "").strip()
        if not id_lote:
            raise EmisionCertificadosError("lote_id_invalido")
        if plantillas_hash is not None and (
            not isinstance(plantillas_hash, str)
            or len(plantillas_hash) != 64
            or any(c not in "0123456789abcdef" for c in plantillas_hash)
        ):
            raise EmisionCertificadosError("plantillas_hash_invalido")
        ahora = ahora or datetime.now(timezone.utc)
        expira = expira_en or (
            ahora + timedelta(hours=VIGENCIA_HORAS)
            if modo == MODO_REAL
            else ahora + timedelta(days=RETENCION_DEMO_DIAS)
        )
        if expira < ahora:
            raise EmisionCertificadosError("expira_en_invalida")
        id_emision = "emi-" + hashlib.sha256(
            id_lote.encode("utf-8")
        ).hexdigest()[:16]
        with self._conexion_factory() as conn:
            with conn.transaction():
                # Todo trabajo entra PENDIENTE, real o demo: el ZIP demo se
                # compone en el worker con el render real y recién ahí la
                # fila pasa a GENERADA_DEMO. Encolar no genera ni envía.
                conn.execute(
                    "INSERT INTO emisiones_certificados ("
                    " id_emision, id_lote, modo, estado, expira_en,"
                    " retencion_hasta, plantillas_hash, terminada_en,"
                    " creada_en, actualizada_en) VALUES"
                    " (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    " ON CONFLICT (id_lote) DO NOTHING",
                    (
                        id_emision,
                        id_lote,
                        modo,
                        ESTADO_PENDIENTE,
                        expira,
                        retencion_hasta,
                        plantillas_hash,
                        None,
                        ahora,
                        ahora,
                    ),
                )
        emision = self.obtener_por_lote(id_lote)
        if emision is None:
            raise EmisionCertificadosError("emision_no_persistida")
        return emision

    def obtener_por_lote(self, id_lote: str) -> EmisionCertificados | None:
        with self._conexion_factory() as conn:
            fila = conn.execute(
                f"{_SELECT} WHERE id_lote = %s", (id_lote,)
            ).fetchone()
        return _emision_desde_fila(fila) if fila is not None else None

    def listar(self) -> list[EmisionCertificados]:
        with self._conexion_factory() as conn:
            filas = conn.execute(
                f"{_SELECT} ORDER BY creada_en DESC"
            ).fetchall()
        return [_emision_desde_fila(fila) for fila in filas]

    def reclamar(
        self,
        *,
        worker_id: str,
        lease_segundos: int = LEASE_SEGUNDOS,
        ahora: datetime | None = None,
    ) -> EmisionCertificados | None:
        ahora = ahora or datetime.now(timezone.utc)
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise EmisionCertificadosError("worker_id_invalido")
        self.reconciliar(ahora=ahora)
        token = secrets.token_hex(32)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "WITH candidato AS ("
                    " SELECT id_emision FROM emisiones_certificados"
                    " WHERE estado = %s AND expira_en > %s"
                    " ORDER BY creada_en"
                    " FOR UPDATE SKIP LOCKED LIMIT 1"
                    ") UPDATE emisiones_certificados e SET"
                    " estado = %s, reservada_por = %s,"
                    " token_reserva = %s, reservada_hasta = %s,"
                    " intentos = e.intentos + 1, actualizada_en = %s"
                    " FROM candidato c WHERE e.id_emision = c.id_emision"
                    f" RETURNING {_COLUMNAS_ALIAS}",
                    (
                        ESTADO_PENDIENTE,
                        ahora,
                        ESTADO_RESERVADA,
                        worker_id.strip(),
                        token,
                        ahora + timedelta(seconds=lease_segundos),
                        ahora,
                    ),
                ).fetchone()
        return _emision_desde_fila(fila) if fila is not None else None

    def marcar_indeterminadas(
        self, *, ahora: datetime | None = None
    ) -> int:
        """Marca como indeterminadas las reservas que un restore dejó vivas.

        La restauración de un respaldo puede volver a un estado anterior a
        un envío ya hecho. No hay forma de saber qué correos salieron: el
        trabajo no se reintenta. Este método existe para que el worker de
        respaldo cierre esas filas sin tocar `reconciliar` ni inventar un
        estado nuevo.
        """
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                return conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " terminada_en = %s, reservada_por = NULL,"
                    " token_reserva = NULL, reservada_hasta = NULL,"
                    " retencion_hasta = NULL, actualizada_en = %s"
                    " WHERE estado IN (%s, %s)",
                    (
                        ESTADO_INDETERMINADA,
                        ahora,
                        ahora,
                        ESTADO_RESERVADA,
                        ESTADO_ENVIANDO,
                    ),
                ).rowcount

    def reconciliar(self, *, ahora: datetime | None = None) -> int:
        ahora = ahora or datetime.now(timezone.utc)
        total = 0
        with self._conexion_factory() as conn:
            with conn.transaction():
                total += conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " terminada_en = %s, reservada_por = NULL,"
                    " token_reserva = NULL, reservada_hasta = NULL,"
                    " retencion_hasta = NULL, actualizada_en = %s"
                    " WHERE estado = %s AND reservada_hasta <= %s",
                    (
                        ESTADO_INDETERMINADA,
                        ahora,
                        ahora,
                        ESTADO_ENVIANDO,
                        ahora,
                    ),
                ).rowcount
                total += conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " reservada_por = NULL, token_reserva = NULL,"
                    " reservada_hasta = NULL, actualizada_en = %s"
                    " WHERE estado = %s AND reservada_hasta <= %s",
                    (
                        ESTADO_PENDIENTE,
                        ahora,
                        ESTADO_RESERVADA,
                        ahora,
                    ),
                ).rowcount
                total += conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " terminada_en = %s, retencion_hasta = %s,"
                    " actualizada_en = %s"
                    " WHERE estado = %s AND expira_en <= %s",
                    (
                        ESTADO_EXPIRADA,
                        ahora,
                        ahora,
                        ahora,
                        ESTADO_PENDIENTE,
                        ahora,
                    ),
                ).rowcount
        return total

    def marcar_enviando(
        self,
        *,
        id_emision: str,
        token: str,
        lease_segundos: int = LEASE_SEGUNDOS,
        ahora: datetime | None = None,
    ) -> bool:
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " iniciada_en = %s, reservada_hasta = %s,"
                    " actualizada_en = %s"
                    " WHERE id_emision = %s AND estado = %s"
                    "   AND token_reserva = %s RETURNING id_emision",
                    (
                        ESTADO_ENVIANDO,
                        ahora,
                        ahora + timedelta(seconds=lease_segundos),
                        ahora,
                        id_emision,
                        ESTADO_RESERVADA,
                        token,
                    ),
                ).fetchone()
        return fila is not None

    def renovar_reserva(
        self,
        *,
        id_emision: str,
        token: str,
        lease_segundos: int = LEASE_SEGUNDOS,
        ahora: datetime | None = None,
    ) -> bool:
        ahora = ahora or datetime.now(timezone.utc)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "UPDATE emisiones_certificados SET reservada_hasta = %s,"
                    " actualizada_en = %s"
                    " WHERE id_emision = %s AND estado = %s"
                    "   AND token_reserva = %s AND reservada_hasta > %s"
                    " RETURNING id_emision",
                    (
                        ahora + timedelta(seconds=lease_segundos),
                        ahora,
                        id_emision,
                        ESTADO_ENVIANDO,
                        token,
                        ahora,
                    ),
                ).fetchone()
        return fila is not None

    def finalizar(
        self,
        *,
        id_emision: str,
        token: str,
        estado: str,
        total: int = 0,
        enviadas: int = 0,
        fallidas: int = 0,
        error_codigo: str | None = None,
        modo_envio: str | None = None,
        ahora: datetime | None = None,
    ) -> bool:
        if estado not in ESTADOS_TERMINALES:
            raise EmisionCertificadosError("estado_terminal_invalido")
        ahora = ahora or datetime.now(timezone.utc)
        retencion = None
        if estado != ESTADO_INDETERMINADA:
            retencion = ahora + timedelta(days=RETENCION_REAL_DIAS)
        with self._conexion_factory() as conn:
            with conn.transaction():
                fila = conn.execute(
                    "UPDATE emisiones_certificados SET estado = %s,"
                    " terminada_en = %s, reservada_por = NULL,"
                    " token_reserva = NULL, reservada_hasta = NULL,"
                    " retencion_hasta = CASE WHEN modo = %s THEN %s"
                    "   ELSE %s END, total = %s, enviadas = %s,"
                    " fallidas = %s, error_codigo = %s,"
                    " modo_envio = %s, actualizada_en = %s"
                    " WHERE id_emision = %s AND token_reserva = %s"
                    "   AND estado IN (%s, %s) RETURNING id_emision",
                    (
                        estado,
                        ahora,
                        MODO_DEMO,
                        ahora + timedelta(days=RETENCION_DEMO_DIAS),
                        retencion,
                        total,
                        enviadas,
                        fallidas,
                        error_codigo,
                        modo_envio,
                        ahora,
                        id_emision,
                        token,
                        ESTADO_RESERVADA,
                        ESTADO_ENVIANDO,
                    ),
                ).fetchone()
        return fila is not None


_COLUMNAS_LISTA = (
    "id_emision", "id_lote", "modo", "estado", "intentos", "reservada_por",
    "token_reserva", "reservada_hasta", "iniciada_en", "terminada_en",
    "expira_en", "retencion_hasta", "total", "enviadas", "fallidas",
    "error_codigo", "modo_envio", "plantillas_hash", "creada_en",
    "actualizada_en",
)
_SELECT = (
    "SELECT " + ", ".join(_COLUMNAS_LISTA) + " FROM emisiones_certificados"
)
# En el `UPDATE ... FROM candidato` las columnas sin alias son ambiguas con
# la CTE: el RETURNING siempre va calificado con la tabla objetivo.
_COLUMNAS_ALIAS = ", ".join(f"e.{c}" for c in _COLUMNAS_LISTA)


def _emision_desde_fila(fila) -> EmisionCertificados:
    return EmisionCertificados(
        id_emision=fila[0],
        id_lote=fila[1],
        modo=fila[2],
        estado=fila[3],
        intentos=fila[4],
        reservada_por=fila[5],
        token_reserva=fila[6],
        reservada_hasta=fila[7],
        iniciada_en=fila[8],
        terminada_en=fila[9],
        expira_en=fila[10],
        retencion_hasta=fila[11],
        total=fila[12],
        enviadas=fila[13],
        fallidas=fila[14],
        error_codigo=fila[15],
        modo_envio=fila[16],
        plantillas_hash=fila[17],
        creada_en=fila[18],
        actualizada_en=fila[19],
    )


class FuenteActividadSnapshot:
    """Fuente de actividades que devuelve la ficha congelada del lote."""

    def __init__(self, actividad: Mapping[str, str]) -> None:
        self._actividad = {
            str(clave): str(valor)
            for clave, valor in dict(actividad).items()
        }

    def obtener(self, id_actividad: str) -> dict[str, str]:
        return dict(self._actividad)


class LectorListaSnapshot:
    """Lector de lista de cierre que devuelve las filas congeladas."""

    def __init__(self, personas: tuple[PersonaCierre, ...]) -> None:
        self._filas = [
            [
                p.nombre,
                p.apellido,
                p.dni,
                p.mail,
                p.tratamiento,
                p.condicion,
            ]
            for p in personas
        ]

    def leer_valores(self) -> list[object]:
        return [list(fila) for fila in self._filas]


def hash_plantillas_aprobadas(
    plantillas: Mapping[str, PlantillaCorreo] | None,
) -> str | None:
    """Hash estable de las redacciones aprobadas que puede usar el lote."""
    if not plantillas:
        return None
    documento = {
        str(tipo): {
            "asunto": plantilla.asunto,
            "cuerpo": plantilla.cuerpo,
        }
        for tipo, plantilla in sorted(plantillas.items())
    }
    return hashlib.sha256(
        json.dumps(
            documento, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def nombre_zip(id_lote: str) -> str:
    """Nombre genérico del ZIP: sólo el id opaco del lote."""
    seguro = "".join(
        c if c.isalnum() or c in "-_." else "-" for c in str(id_lote)
    ).strip("-") or "lote"
    return f"certificados-{seguro}.zip"


def construir_zip_certificados(
    *,
    lote: Any,
    demo: bool,
    modo_envio: str | None = None,
    recursos_firma: RecursosFirma | None = None,
    plantillas_aprobadas: Mapping[str, PlantillaCorreo] | None = None,
    firmantes=FIRMANTES_DECLARADOS,
) -> bytes:
    """Compone el ZIP determinista desde el snapshot autorizado.

    Los PDFs salen del mismo render que la emisión. Un lote demo siempre
    lleva las dos marcas permanentes —prueba y borrador—; el real usa el
    modo de envío declarado para no inventar marcas en producción.
    """
    if not lote.personas or lote.linea_descriptiva is None:
        raise EmisionCertificadosError(CODIGO_SNAPSHOT_NO_DISPONIBLE)
    produccion = modo_envio == "produccion"
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED
    ) as archivo:
        for indice, persona in enumerate(lote.personas, start=1):
            pdf, _plantilla = generar_pdf_certificado_lote(
                persona=persona,
                actividad=dict(lote.actividad),
                linea_descriptiva=lote.linea_descriptiva,
                id_certificado=f"cert-{lote.id_actividad}-{persona.dni}",
                firmantes=firmantes,
                recursos_firma=recursos_firma,
                borrador=demo,
                marcar_prueba=demo or not produccion,
                plantilla_asistencia=(
                    (plantillas_aprobadas or {}).get("certificado_asistencia")
                    if produccion and not demo
                    else None
                ),
            )
            info = zipfile.ZipInfo(
                f"certificado-{indice:03d}.pdf", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0
            archivo.writestr(info, pdf)
    return buffer.getvalue()


def bloqueos_envio(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Códigos que impiden un envío real, sin tocar red ni romper la web."""
    from .gmail_envio import (
        cargar_destinatarios_aprobados,
        cargar_destinatarios_prueba,
        cargar_modo_envio,
    )

    bloqueos: list[str] = []
    try:
        modo = cargar_modo_envio(environ)
    except ConfiguracionWorkspaceError as error:
        bloqueos.append(error.code)
        return tuple(bloqueos)
    try:
        if modo == "produccion":
            cargar_destinatarios_aprobados(environ)
        else:
            cargar_destinatarios_prueba(environ)
    except ConfiguracionWorkspaceError as error:
        bloqueos.append(error.code)
    return tuple(bloqueos)


def crear_destino_gmail(
    environ: Mapping[str, str] | None = None,
    *,
    directorio_auditoria: Path | None = None,
):
    """Construye el destino Gmail real; no hace red hasta `entregar`."""
    from .gmail_envio import GmailDestinoConfirmaciones
    from .workspace_auth import construir_token_provider
    from .workspace_config import cargar_configuracion_workspace

    config = cargar_configuracion_workspace(environ)
    token_provider = construir_token_provider(
        environ,
        timeout_s=config.timeout_s,
        directorio_auditoria=directorio_auditoria,
    )
    return GmailDestinoConfirmaciones.desde_entorno(
        environ,
        token_provider=token_provider,
        timeout_s=config.timeout_s,
    )


class EnvioAmbiguo(RuntimeError):
    """Una entrega pudo haber salido: el resto del lote no se manda."""

    code = "entrega_ambigua"


class _DestinoConReserva:
    """Destino que renueva la reserva antes de cada envío y la vigila.

    Dos salidas no reintentables:

    - ``perdida``: el lock venció (u otro worker se lo quedó). Ni una
      entrega más sale por esta instancia.
    - ``ambigua``: el transporte lanzó después de recibir el pedido, así
      que no se puede afirmar que el correo no salió. Todas las entregas
      siguientes se bloquean y el trabajo cierra ``INDETERMINADA`` aunque
      no se haya confirmado ninguna. Sólo `EntregaRechazadaError`, el
      rechazo de política por destinatario, pasa como falla limpia.
    """

    def __init__(
        self,
        destino,
        *,
        repositorio: RepositorioEmisiones,
        trabajo: EmisionCertificados,
        lease_segundos: int,
        ahora: Callable[[], datetime],
    ) -> None:
        self._destino = destino
        self._repositorio = repositorio
        self._trabajo = trabajo
        self._lease_segundos = lease_segundos
        self._ahora = ahora
        self.enviadas = 0
        self.perdida = False
        self.ambigua = False

    @property
    def modo(self) -> str | None:
        return getattr(self._destino, "modo", None)

    def entregar(self, **kwargs) -> None:
        if self.perdida:
            raise ReservaPerdida()
        if self.ambigua:
            raise EnvioAmbiguo()
        if not self._repositorio.renovar_reserva(
            id_emision=self._trabajo.id_emision,
            token=self._trabajo.token_reserva or "",
            lease_segundos=self._lease_segundos,
            ahora=self._ahora(),
        ):
            self.perdida = True
            raise ReservaPerdida()
        try:
            self._destino.entregar(**kwargs)
        except EntregaRechazadaError:
            raise
        except Exception:
            self.ambigua = True
            raise
        self.enviadas += 1


def _finalizar_fallo(
    repositorio: RepositorioEmisiones,
    trabajo: EmisionCertificados,
    *,
    codigo: str,
    ahora: datetime,
) -> ResultadoTrabajoEmision:
    repositorio.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva or "",
        estado=ESTADO_FALLIDA,
        error_codigo=codigo,
        ahora=ahora,
    )
    return ResultadoTrabajoEmision(estado=ESTADO_FALLIDA, codigo=codigo)


# `error_codigo` entra en un CHECK `[A-Za-z0-9_.-]{1,64}`: la prosa del
# motor ("N entregas fallidas") nunca se persiste tal cual.
_FORMATO_CODIGO = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def _codigo_error(valor: str | None, por_defecto: str) -> str:
    if valor and _FORMATO_CODIGO.fullmatch(valor):
        return valor
    return por_defecto


def _reparar_aprobacion(
    registro: RegistroDecisiones,
    lote: Any,
    *,
    ahora: datetime,
) -> bool:
    if (
        lote.estado != "APROBADA"
        or lote.origen_identidad != "google"
        or getattr(lote, "origen_creacion", None) == "demo"
        or lote.decidida_por_hash != lote.generada_por_hash
        or lote.rol_decision != ROL_APROBADOR_CONTENIDO
    ):
        return False
    revision = revisar_aprobacion_lote(
        registro,
        objeto_lote=lote.objeto_lote,
        generada_por_correo_hash=lote.generada_por_hash,
    )
    if revision.aprobada:
        return True
    if not lote.decidida_por_hash or not lote.rol_decision:
        return False
    # Sólo se re-proyecta el `apruebo_lote` que la fila del lote ya
    # comprobó con FOR UPDATE: identidad, rol y objeto salen de la base,
    # no de una decisión nueva. La línea descriptiva no se toca acá: si
    # falta, el lote queda bloqueado hasta que una persona la confirme en
    # la web; el worker nunca la fabrica.
    marca = ahora.isoformat()
    registro.registrar(
        ResultadoDecision(
            id_respuesta=hashlib.sha256(
                "web_lote|{o}|{h}|{m}".format(
                    o=lote.objeto_lote,
                    h=lote.decidida_por_hash,
                    m=marca,
                ).encode("utf-8")
            ).hexdigest(),
            correo_hash=lote.decidida_por_hash,
            rol=lote.rol_decision,
            rol_origen=ROL_ORIGEN_PADRON,
            tipo=TIPO_LOTE,
            objeto_id=lote.objeto_lote,
            decision=DECISION_APRUEBO_LOTE,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=marca,
            timestamp=marca,
        )
    )
    return revisar_aprobacion_lote(
        registro,
        objeto_lote=lote.objeto_lote,
        generada_por_correo_hash=lote.generada_por_hash,
    ).aprobada


def ejecutar_trabajo_emision(
    trabajo: EmisionCertificados,
    *,
    repositorio: RepositorioEmisiones,
    lotes: RepositorioLotesPuerto,
    padron: PadronRoles,
    registro_decisiones: RegistroDecisiones | None,
    directorio_salida: Path,
    fabrica_destino: Callable[[], object],
    recursos_firma: RecursosFirma | None = None,
    plantillas_aprobadas: Mapping[str, PlantillaCorreo] | None = None,
    motor: Callable[..., ResultadoEmisionCertificados] = (
        procesar_emision_certificados
    ),
    ahora: datetime | None = None,
    lease_segundos: int = LEASE_SEGUNDOS,
    modo_demo: bool = False,
) -> ResultadoTrabajoEmision:
    """Ejecuta un trabajo reservado con el snapshot aprobado.

    El orden de las barreras importa: el lote existe y está aprobado, el
    snapshot sigue retenido, el generador conserva el rol y el registro
    tiene (o puede reparar) el `apruebo_lote`. Sólo después se marca
    `ENVIANDO` y se llama al motor.
    """
    momento = ahora or datetime.now(timezone.utc)
    if trabajo.estado != ESTADO_RESERVADA or not trabajo.token_reserva:
        return ResultadoTrabajoEmision(
            estado=trabajo.estado, codigo="trabajo_no_reservado"
        )
    lote = lotes.obtener(trabajo.id_lote)
    if lote is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_INEXISTENTE,
            ahora=momento,
        )
    if lote.estado != "APROBADA":
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_NO_APROBADO,
            ahora=momento,
        )
    if modo_demo:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_MODO_DEMO_NO_ENVIA,
            ahora=momento,
        )
    from .lote_demo import es_lote_demo

    # El origen demo es permanente: ni un cambio de modo ni el paso del
    # tiempo habilitan Gmail para este lote. La semilla histórica, que
    # tiene `origen_creacion` NULL, se reconoce por el predicado.
    if (
        getattr(lote, "origen_creacion", None) == "demo"
        or es_lote_demo(lote)
    ):
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_DEMO_NO_ENVIA,
            ahora=momento,
        )
    if not lote.personas or lote.linea_descriptiva is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_SNAPSHOT_NO_DISPONIBLE,
            ahora=momento,
        )
    if lote.origen_identidad != "google":
        return _finalizar_fallo(
            repositorio, trabajo, codigo="identidad_no_verificada", ahora=momento
        )
    if registro_decisiones is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_REGISTRO_NO_DISPONIBLE,
            ahora=momento,
        )
    if padron is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_IDENTIDAD_NO_DISPONIBLE,
            ahora=momento,
        )
    correo = padron.correo_para_hash(lote.generada_por_hash)
    if not correo:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_IDENTIDAD_NO_DISPONIBLE,
            ahora=momento,
        )
    if padron.rol_para(correo) != ROL_APROBADOR_CONTENIDO:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_ROL_REVOCADO,
            ahora=momento,
        )
    try:
        aprobado = _reparar_aprobacion(
            registro_decisiones, lote, ahora=momento
        )
    except Exception:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_REGISTRO_NO_DISPONIBLE,
            ahora=momento,
        )
    if not aprobado:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_NO_APROBADO,
            ahora=momento,
        )
    actual = hash_plantillas_aprobadas(plantillas_aprobadas)
    if trabajo.plantillas_hash is not None and actual != trabajo.plantillas_hash:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_PLANTILLAS_CAMBIADAS,
            ahora=momento,
        )
    if not repositorio.marcar_enviando(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        lease_segundos=lease_segundos,
        ahora=momento,
    ):
        return ResultadoTrabajoEmision(
            estado=trabajo.estado, codigo=CODIGO_RESERVA_PERDIDA
        )
    try:
        destino = fabrica_destino()
    except Exception:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_DESTINO_NO_DISPONIBLE,
            ahora=momento,
        )
    envuelto = _DestinoConReserva(
        destino,
        repositorio=repositorio,
        trabajo=trabajo,
        lease_segundos=lease_segundos,
        ahora=lambda: ahora or datetime.now(timezone.utc),
    )
    try:
        resultado = motor(
            id_actividad=lote.id_actividad,
            fuente=FuenteActividadSnapshot(lote.actividad),
            lector_lista=LectorListaSnapshot(lote.personas),
            linea_descriptiva=lote.linea_descriptiva,
            registro_decisiones=registro_decisiones,
            enlaces=_EnlacesSinCorreo(),
            destino=envuelto,
            solicitante_correo=correo,
            solicitante_rol=ROL_APROBADOR_CONTENIDO,
            directorio_salida=directorio_salida,
            firmantes=FIRMANTES_DECLARADOS,
            recursos_firma=recursos_firma,
            plantillas_aprobadas=plantillas_aprobadas,
            correlation_id=f"emision-{trabajo.id_emision}",
        )
    except Exception:
        estado = (
            ESTADO_INDETERMINADA
            if envuelto.enviadas or envuelto.perdida or envuelto.ambigua
            else ESTADO_FALLIDA
        )
        codigo = (
            CODIGO_RESERVA_PERDIDA
            if envuelto.perdida
            else CODIGO_ENTREGA_AMBIGUA
            if envuelto.ambigua
            else CODIGO_ERROR_MOTOR
        )
        repositorio.finalizar(
            id_emision=trabajo.id_emision,
            token=trabajo.token_reserva,
            estado=estado,
            total=len(lote.personas),
            enviadas=envuelto.enviadas,
            fallidas=max(0, len(lote.personas) - envuelto.enviadas),
            error_codigo=codigo,
            modo_envio=envuelto.modo,
            ahora=momento,
        )
        return ResultadoTrabajoEmision(
            estado=estado,
            codigo=codigo,
            enviadas=envuelto.enviadas,
            fallidas=max(0, len(lote.personas) - envuelto.enviadas),
            total=len(lote.personas),
        )
    if envuelto.perdida or envuelto.ambigua:
        estado = ESTADO_INDETERMINADA
        codigo = (
            CODIGO_RESERVA_PERDIDA
            if envuelto.perdida
            else CODIGO_ENTREGA_AMBIGUA
        )
    elif resultado.estado == "EMITIDA":
        estado, codigo = ESTADO_EMITIDA, None
    elif resultado.estado == "EMITIDA_PARCIAL":
        estado, codigo = (
            ESTADO_EMITIDA_PARCIAL,
            _codigo_error(resultado.error, CODIGO_ENTREGAS_FALLIDAS),
        )
    elif resultado.estado == "PENDIENTE_APROBACION":
        estado, codigo = (
            ESTADO_FALLIDA,
            _codigo_error(resultado.error, CODIGO_LOTE_NO_APROBADO),
        )
    else:
        estado, codigo = (
            ESTADO_FALLIDA,
            _codigo_error(resultado.error, CODIGO_ENTREGAS_FALLIDAS),
        )
    total = len(lote.personas)
    repositorio.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        estado=estado,
        total=total,
        enviadas=resultado.emitidas,
        fallidas=resultado.entregas_fallidas,
        error_codigo=codigo,
        modo_envio=envuelto.modo,
        ahora=momento,
    )
    return ResultadoTrabajoEmision(
        estado=estado,
        codigo=codigo,
        enviadas=resultado.emitidas,
        fallidas=resultado.entregas_fallidas,
        total=total,
    )


def ejecutar_trabajo_demo(
    trabajo: EmisionCertificados,
    *,
    repositorio: RepositorioEmisiones,
    lotes: RepositorioLotesPuerto,
    padron: PadronRoles | None = None,
    recursos_firma: RecursosFirma | None = None,
    plantillas_aprobadas: Mapping[str, PlantillaCorreo] | None = None,
    modo_demo: bool = False,
    ahora: datetime | None = None,
) -> ResultadoTrabajoEmision:
    """Compone el render demo reservado y lo marca `GENERADA_DEMO`.

    El trabajo demo compone el mismo PDF por persona que la emisión real
    (con las marcas permanentes de prueba) para validar que el snapshot
    rinde. El ZIP no se guarda en la base: la descarga lo vuelve a
    componer al vuelo, sin tocar la fila. Un fallo de render cierra
    `FALLIDA`, no una descarga rota.

    No hay envío ni reserva externa: una caída a mitad del render deja
    la reserva vencer y el trabajo vuelve a `PENDIENTE`. No necesita
    registro ni padrón, pero si hay padrón revalida el rol vigente del
    generador, igual que el camino real.
    """
    momento = ahora or datetime.now(timezone.utc)
    if trabajo.estado != ESTADO_RESERVADA or not trabajo.token_reserva:
        return ResultadoTrabajoEmision(
            estado=trabajo.estado, codigo="trabajo_no_reservado"
        )
    lote = lotes.obtener(trabajo.id_lote)
    if lote is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_INEXISTENTE,
            ahora=momento,
        )
    if not modo_demo:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_DEMO_FUERA_DE_MODO,
            ahora=momento,
        )
    if lote.estado != "APROBADA":
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_LOTE_NO_APROBADO,
            ahora=momento,
        )
    if not lote.personas or lote.linea_descriptiva is None:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_SNAPSHOT_NO_DISPONIBLE,
            ahora=momento,
        )
    if padron is not None:
        correo = padron.correo_para_hash(lote.generada_por_hash)
        if not correo:
            return _finalizar_fallo(
                repositorio,
                trabajo,
                codigo=CODIGO_IDENTIDAD_NO_DISPONIBLE,
                ahora=momento,
            )
        if padron.rol_para(correo) != ROL_APROBADOR_CONTENIDO:
            return _finalizar_fallo(
                repositorio,
                trabajo,
                codigo=CODIGO_ROL_REVOCADO,
                ahora=momento,
            )
    try:
        construir_zip_certificados(
            lote=lote,
            demo=True,
            recursos_firma=recursos_firma,
            plantillas_aprobadas=plantillas_aprobadas,
        )
    except EmisionCertificadosError as exc:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=_codigo_error(exc.code, CODIGO_RENDER_DEMO_FALLIDO),
            ahora=momento,
        )
    except Exception:
        return _finalizar_fallo(
            repositorio,
            trabajo,
            codigo=CODIGO_RENDER_DEMO_FALLIDO,
            ahora=momento,
        )
    total = len(lote.personas)
    repositorio.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        estado=ESTADO_GENERADA_DEMO,
        total=total,
        ahora=momento,
    )
    return ResultadoTrabajoEmision(
        estado=ESTADO_GENERADA_DEMO,
        codigo=None,
        enviadas=0,
        fallidas=0,
        total=total,
    )


class _EnlacesSinCorreo:
    """Los enlaces del Form no se usan en la emisión durable."""

    def declarar_y_enlaces(self, **_kwargs) -> None:
        return None

    def enlace(self, **_kwargs) -> str:
        return ""


__all__ = [
    "CODIGO_DEMO_FUERA_DE_MODO",
    "CODIGO_DESTINO_NO_DISPONIBLE",
    "CODIGO_ENTREGAS_FALLIDAS",
    "CODIGO_ENTREGA_AMBIGUA",
    "CODIGO_ERROR_MOTOR",
    "CODIGO_IDENTIDAD_NO_DISPONIBLE",
    "CODIGO_LOTE_DEMO_NO_ENVIA",
    "CODIGO_LOTE_INEXISTENTE",
    "CODIGO_LOTE_NO_APROBADO",
    "CODIGO_MODO_DEMO_NO_ENVIA",
    "CODIGO_PLANTILLAS_CAMBIADAS",
    "CODIGO_REGISTRO_NO_DISPONIBLE",
    "CODIGO_RENDER_DEMO_FALLIDO",
    "CODIGO_RESERVA_PERDIDA",
    "CODIGO_ROL_REVOCADO",
    "CODIGO_SNAPSHOT_NO_DISPONIBLE",
    "ESTADOS_ACTIVOS",
    "ESTADOS_TERMINALES",
    "ESTADO_EMITIDA",
    "ESTADO_EMITIDA_PARCIAL",
    "ESTADO_ENVIANDO",
    "ESTADO_EXPIRADA",
    "ESTADO_FALLIDA",
    "ESTADO_GENERADA_DEMO",
    "ESTADO_INDETERMINADA",
    "ESTADO_PENDIENTE",
    "ESTADO_RESERVADA",
    "EmisionCertificados",
    "EmisionCertificadosError",
    "EnvioAmbiguo",
    "FuenteActividadSnapshot",
    "LectorListaSnapshot",
    "MODO_DEMO",
    "MODO_REAL",
    "MODOS",
    "RepositorioEmisiones",
    "ResultadoTrabajoEmision",
    "VIGENCIA_HORAS",
    "bloqueos_envio",
    "construir_zip_certificados",
    "crear_destino_gmail",
    "ejecutar_trabajo_demo",
    "ejecutar_trabajo_emision",
    "hash_plantillas_aprobadas",
    "nombre_zip",
    "recursos_firma_opcional",
]
