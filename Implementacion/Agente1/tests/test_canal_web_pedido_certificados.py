"""Pedido web del lote de certificados (#168, ADR 0018/0019).

Dos niveles, como el resto del canal web:

- El **parser del CSV** se prueba en unitario contra el puerto real
  (`parsear_csv_lista_cierre` + `parsear_lista_cierre` del circuito):
  delimitadores, cabecera, límites, números de fila y toda-o-nada.
- El **camino HTTP** se prueba contra la app real con el repositorio en
  memoria: puertas de sesión/rol/CSRF, snapshot del catálogo, errores por
  campo, idempotencia por objeto del lote y conflictos explícitos.
  `origen_creacion` se declara como en el contrato: la columna nueva la
  aporta el backend; el fake la aplica sobre el lote igual que la fila.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import (
    ListaCierreError,
    PersonaCierre,
    hash_lista_cierre,
    objeto_lote_cierre,
)
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.lote_demo import es_lote_demo
from agente1.web import pedido_certificados
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.certificados_web import (
    ESTADO_APROBADA,
    ESTADO_DESCARTADA,
    ESTADO_PENDIENTE,
    LoteCertificados,
    ResultadoDecisionLote,
)
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.pedido_certificados import (
    parsear_csv_lista_cierre,
)
from agente1.web.sesiones import SesionesMemoria

CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_OTRO_APROBADOR = "otra.persona@example.invalid"
CORREO_COORDINADOR = "coordinador@example.invalid"
TOKEN_APROBADOR = "tok-aprobador"
TOKEN_COORDINADOR = "tok-coordinador"
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)

ACTIVIDAD_ROW = {
    "id_actividad": "FIE-DIF-02",
    "titulo": "Curso Inteligencia Artificial Aplicada a la Gestión Documental",
    "duracion_horas": "24",
    "modalidad": "online y autogestionado",
    "fecha_inicio": "2026-06-25",
    "fecha_fin": "2026-08-06",
    "organiza": "Facultad de Ingeniería del Ejército",
}
DATOS_ACTIVIDAD = {
    "fecha_fin": "2026-08-06",
    "titulo": ACTIVIDAD_ROW["titulo"],
    "duracion_horas": "24",
    "modalidad": "online y autogestionado",
    "fecha_inicio": "2026-06-25",
    "organiza": "Facultad de Ingeniería del Ejército",
}
LINEA = "Curso introductorio sobre herramientas de análisis documental."

CSV_OK = (
    "nombre;apellido;dni;mail;tratamiento;condicion\n"
    "Ana;Prueba;11111111;ana.prueba@example.invalid;Sra.;aprobacion\n"
    "Luis;Ejemplo;22222222;luis.ejemplo@example.invalid;Sr.;asistencia\n"
)

CSV_COMA = (
    "nombre,apellido,dni,mail,tratamiento,condicion\n"
    "Ana,Prueba,11111111,ana.prueba@example.invalid,Sra.,aprobacion\n"
)


def _personas_csv() -> tuple[PersonaCierre, ...]:
    return (
        PersonaCierre(
            nombre="Ana",
            apellido="Prueba",
            dni="11111111",
            mail="ana.prueba@example.invalid",
            tratamiento="Sra.",
            condicion="aprobacion",
        ),
        PersonaCierre(
            nombre="Luis",
            apellido="Ejemplo",
            dni="22222222",
            mail="luis.ejemplo@example.invalid",
            tratamiento="Sr.",
            condicion="asistencia",
        ),
    )


class RepositorioLotesMemoria:
    """El puerto del repo de lotes en memoria, con `origen_creacion`.

    El fake declara la misma columna nueva que el backend: el lote queda
    con `origen_creacion` cuando el alta la trae (sesión), y sin el
    atributo cuando se siembra directo como los lotes legacy.
    """

    def __init__(self, lotes: tuple[LoteCertificados, ...] | None = None) -> None:
        self._lotes = {lote.id_lote: lote for lote in (lotes or ())}
        self.llamadas_crear: list[dict[str, Any]] = []
        self.llamadas_decidir: list[dict[str, Any]] = []

    def listar(self) -> list[LoteCertificados]:
        return list(self._lotes.values())

    def obtener(self, id_lote: str) -> LoteCertificados | None:
        return self._lotes.get(id_lote)

    def crear(
        self,
        *,
        id_actividad: str,
        actividad: dict[str, str],
        personas: tuple[PersonaCierre, ...],
        linea_descriptiva: str,
        generada_por_hash: str,
        origen_creacion: str | None = None,
        ahora: datetime | None = None,
    ) -> LoteCertificados:
        self.llamadas_crear.append(
            {
                "id_actividad": id_actividad,
                "actividad": dict(actividad),
                "personas": personas,
                "linea_descriptiva": linea_descriptiva,
                "generada_por_hash": generada_por_hash,
                "origen_creacion": origen_creacion,
            }
        )
        objeto = objeto_lote_cierre(
            id_actividad, hash_lista_cierre(personas)
        )
        for lote in self._lotes.values():
            if lote.objeto_lote == objeto:
                return lote
        id_lote = f"lote-{objeto[:16]}"
        lote = LoteCertificados(
            id_lote=id_lote,
            id_actividad=id_actividad,
            objeto_lote=objeto,
            hash_lista=hash_lista_cierre(personas),
            actividad=dict(actividad),
            personas=personas,
            cantidad_personas=len(personas),
            linea_descriptiva=linea_descriptiva,
            linea_descriptiva_hash=hashlib.sha256(
                linea_descriptiva.encode("utf-8")
            ).hexdigest(),
            plantilla_muestra="certificado_seu_aprobacion_v1",
            estado=ESTADO_PENDIENTE,
            generada_por_hash=generada_por_hash,
            creada_en=ahora or AHORA,
        )
        if origen_creacion is not None:
            object.__setattr__(lote, "origen_creacion", origen_creacion)
        self._lotes[id_lote] = lote
        return lote

    def sembrar(self, **cambios) -> LoteCertificados:
        """Lote directo, como las altas del circuito anterior."""
        lote = self.crear(
            id_actividad="FIE-DIF-02",
            actividad=dict(DATOS_ACTIVIDAD),
            personas=_personas_csv(),
            linea_descriptiva=LINEA,
            generada_por_hash=hash_correo(CORREO_APROBADOR),
            **cambios,
        )
        self.llamadas_crear.clear()
        return lote

    def decidir(
        self,
        *,
        id_lote: str,
        hash_lote: str,
        accion: str,
        validador_hash: str,
        rol: str,
        origen_identidad: str,
        version_agente: str,
        ahora: datetime | None = None,
    ) -> ResultadoDecisionLote:
        self.llamadas_decidir.append(
            {"id_lote": id_lote, "accion": accion}
        )
        lote = self._lotes.get(id_lote)
        if lote is None:
            return ResultadoDecisionLote("inexistente")
        if lote.estado != ESTADO_PENDIENTE:
            return ResultadoDecisionLote("duplicada")
        if rol != ROL_APROBADOR_CONTENIDO:
            return ResultadoDecisionLote("aprobador_rol_no_autorizado")
        if hash_lote != lote.objeto_lote:
            return ResultadoDecisionLote("lote_obsoleto")
        if accion == "aprobar" and validador_hash != lote.generada_por_hash:
            return ResultadoDecisionLote("aprobador_no_es_generador")
        nuevo = replace(
            lote,
            estado=(
                ESTADO_APROBADA if accion == "aprobar" else ESTADO_DESCARTADA
            ),
            decidida_en=ahora or AHORA,
            decidida_por_hash=validador_hash,
            rol_decision=rol,
            origen_identidad=origen_identidad,
            version_agente=version_agente,
        )
        # `origen_creacion` es columna en el backend: sobrevive a la
        # decisión igual que el objeto y el generador. Como acá no es un
        # campo del dataclass, la reponemos igual que la lectura real.
        origen = getattr(lote, "origen_creacion", None)
        if origen is not None:
            object.__setattr__(nuevo, "origen_creacion", origen)
        self._lotes[id_lote] = nuevo
        return ResultadoDecisionLote(
            "aprobada" if accion == "aprobar" else "descartada",
            id_lote=id_lote,
        )


class _RepositorioWebVacio:
    def bandeja(self) -> list:
        return []

    def obtener(self, id_solicitud: str):
        return None


@dataclass
class Mundo:
    client: TestClient
    lotes: RepositorioLotesMemoria
    sesiones: SesionesMemoria


def _mundo(
    *,
    actividades: list[dict[str, str]] | None = None,
    lotes: tuple[LoteCertificados, ...] | None = None,
    registro_decisiones=None,
    emision_certificados=None,
) -> Mundo:
    padron = PadronRoles(
        {
            CORREO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_OTRO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_COORDINADOR: "coordinador_seu",
        }
    )
    sesiones = SesionesMemoria(ahora=lambda: AHORA)
    repo_lotes = RepositorioLotesMemoria(lotes)
    app = crear_app(
        config=ConfiguracionWeb(
            google_client_id=CLIENT_ID_PRUEBA,
            modo_prueba=True,
            cookie_secure=False,
        ),
        verificador=VerificadorFake(
            {
                TOKEN_APROBADOR: IdentidadVerificada(
                    "sub-aprobador", CORREO_APROBADOR, "x.invalid"
                ),
                TOKEN_COORDINADOR: IdentidadVerificada(
                    "sub-coordinador", CORREO_COORDINADOR, "x.invalid"
                ),
            }
        ),
        padron=padron,
        repositorio=_RepositorioWebVacio(),
        sesiones=sesiones,
        actividades=(
            [dict(ACTIVIDAD_ROW)] if actividades is None else actividades
        ),
        lotes=repo_lotes,
        version_agente="0.9.0",
        registro_decisiones=registro_decisiones,
        emision_certificados=emision_certificados,
    )
    return Mundo(TestClient(app), repo_lotes, sesiones)


def _ingresar(client: TestClient, token: str = TOKEN_APROBADOR) -> None:
    formulario = client.get("/ingresar")
    csrf = formulario.text.split('name="csrf" value="', 1)[1].split('"', 1)[0]
    respuesta = client.post(
        "/ingresar",
        data={"credential": token, "csrf": csrf},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _csrf(mundo: Mundo) -> str:
    return next(iter(mundo.sesiones._sesiones.values())).csrf_token


def _post_pedir(
    mundo: Mundo,
    *,
    actividad: str = "FIE-DIF-02",
    linea: str = LINEA,
    csv_bytes: bytes | None = None,
    nombre_archivo: str = "cierre.csv",
    **extra: str,
):
    datos = {"csrf": _csrf(mundo), "actividad": actividad, "linea_descriptiva": linea}
    datos.update(extra)
    archivos = (
        {"lista": (nombre_archivo, csv_bytes, "text/csv")}
        if csv_bytes is not None
        else None
    )
    return mundo.client.post(
        "/certificados/pedir",
        data=datos,
        files=archivos,
        follow_redirects=False,
    )


# --- parser del CSV --------------------------------------------------------


def test_parsea_semicolon_y_coma() -> None:
    assert len(parsear_csv_lista_cierre(CSV_OK.encode())) == 2
    assert len(parsear_csv_lista_cierre(CSV_COMA.encode())) == 1


def test_parsea_utf8_con_bom() -> None:
    personas = parsear_csv_lista_cierre(b"\xef\xbb\xbf" + CSV_OK.encode())
    assert personas[0].nombre == "Ana"


def test_rechaza_archivo_vacio() -> None:
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(b"")
    assert error.value.code == "lista_cierre_csv_vacia"


def test_rechaza_no_utf8() -> None:
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre("Aña;B\n".encode("latin-1"))
    assert error.value.code == "lista_cierre_csv_codificacion"


def test_rechaza_sin_cabecera_o_otro_delimitador() -> None:
    for malo in (
        b"Ana;Prueba;11111111;ana@example.invalid;Sra.;aprobacion\n",
        b"nombre|apellido|dni|mail|tratamiento|condicion\n",
    ):
        with pytest.raises(ListaCierreError) as error:
            parsear_csv_lista_cierre(malo)
        assert error.value.code == "lista_cierre_csv_cabecera"


def test_rechaza_bytes_por_encima_del_limite(monkeypatch) -> None:
    monkeypatch.setattr(pedido_certificados, "MAX_CSV_BYTES", 100)
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(CSV_OK.encode())
    assert error.value.code == "lista_cierre_csv_grande"


def test_rechaza_filas_por_encima_del_limite(monkeypatch) -> None:
    monkeypatch.setattr(pedido_certificados, "MAX_CSV_FILAS", 1)
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(CSV_OK.encode())
    assert error.value.code == "lista_cierre_csv_filas"


def test_rechaza_fila_con_columnas_de_mas_o_menos() -> None:
    extra = (
        "nombre;apellido;dni;mail;tratamiento;condicion\n"
        "Ana;Prueba;11111111;ana@example.invalid;Sra.;aprobacion;extra\n"
    )
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(extra.encode())
    assert error.value.code == "lista_cierre_fila_invalida"
    assert error.value.fila == 2
    corta = (
        "nombre;apellido;dni;mail;tratamiento;condicion\n"
        "Ana;Prueba;11111111;ana@example.invalid;Sra.\n"
    )
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(corta.encode())
    assert error.value.fila == 2


def test_error_lleva_el_numero_de_fila_del_archivo() -> None:
    malo = (
        CSV_OK
        + "Mala;Condicion;33333333;mala@example.invalid;Sr.;diploma\n"
    )
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(malo.encode())
    assert error.value.code == "lista_cierre_condicion_invalida"
    # La fila es la del archivo: cabecera en 1, la tercera persona en 4.
    assert error.value.fila == 4


def test_rechaza_duplicados_y_lista_sin_personas() -> None:
    duplicado = (
        "nombre;apellido;dni;mail;tratamiento;condicion\n"
        "Ana;Prueba;11111111;ana@example.invalid;Sra.;aprobacion\n"
        "Otra;Persona;11111111;otra@example.invalid;Sr.;aprobacion\n"
    )
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(duplicado.encode())
    assert error.value.code == "lista_cierre_duplicada"
    assert error.value.fila == 3
    solo_cabecera = "nombre;apellido;dni;mail;tratamiento;condicion\n"
    with pytest.raises(ListaCierreError) as error:
        parsear_csv_lista_cierre(solo_cabecera.encode())
    assert error.value.code == "lista_cierre_vacia"


# --- puertas del pedido -----------------------------------------------------


def test_pedir_sin_sesion_redirige_al_ingreso() -> None:
    mundo = _mundo()
    respuesta = mundo.client.get("/certificados/pedir", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_pedir_exige_rol_aprobador() -> None:
    mundo = _mundo()
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    assert mundo.client.get("/certificados/pedir").status_code == 403
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas_crear == []


def test_pedir_exige_csrf() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/pedir",
        data={
            "actividad": "FIE-DIF-02",
            "linea_descriptiva": LINEA,
        },
        files={"lista": ("cierre.csv", CSV_OK.encode(), "text/csv")},
    )
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas_crear == []


def test_el_formulario_muestra_actividades_del_catalogo() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/certificados/pedir")
    assert respuesta.status_code == 200
    assert "FIE-DIF-02" in respuesta.text
    assert ACTIVIDAD_ROW["titulo"] in respuesta.text
    assert 'name="lista"' in respuesta.text
    assert "linea_descriptiva" in respuesta.text


def test_la_plantilla_csv_es_sintetica_y_sin_correos_reales() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/certificados/plantilla-lista.csv")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert "attachment" in respuesta.headers["content-disposition"]
    assert "nombre;apellido;dni;mail;tratamiento;condicion" in respuesta.text
    assert "@example.invalid" in respuesta.text
    # La plantilla sigue la misma puerta de rol que el pedido.
    mundo2 = _mundo()
    _ingresar(mundo2.client, TOKEN_COORDINADOR)
    assert (
        mundo2.client.get("/certificados/plantilla-lista.csv").status_code
        == 403
    )


# --- alta del lote ----------------------------------------------------------


def test_pedir_valido_crea_el_lote_y_redirige() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 303
    id_lote = respuesta.headers["location"].rsplit("/", 1)[-1]
    assert id_lote.startswith("lote-")

    llamada = mundo.lotes.llamadas_crear[-1]
    assert llamada["actividad"] == DATOS_ACTIVIDAD
    assert llamada["generada_por_hash"] == hash_correo(CORREO_APROBADOR)
    assert llamada["origen_creacion"] == "google"
    assert len(llamada["personas"]) == 2

    lote = mundo.lotes.obtener(id_lote)
    assert lote is not None
    assert lote.estado == ESTADO_PENDIENTE
    assert lote.origen_creacion == "google"
    # El origen declarado lo reconoce la marca: un pedido web de sesión
    # real no es demo, uno de sesión demo sí.
    assert es_lote_demo(lote) is False

    pagina = mundo.client.get(respuesta.headers["location"])
    assert pagina.status_code == 200
    assert "Ana Prueba" in pagina.text
    assert LINEA in pagina.text
    assert "Apruebo la línea descriptiva y la lista del lote" in pagina.text


def test_repetir_el_pedido_devuelve_el_mismo_lote() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    primero = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    segundo = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert primero.status_code == 303 and segundo.status_code == 303
    assert primero.headers["location"] == segundo.headers["location"]
    assert len(mundo.lotes.listar()) == 1


def test_pedir_con_otra_linea_no_reescribe_la_aprobada() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    respuesta = _post_pedir(
        mundo, csv_bytes=CSV_OK.encode(), linea="Otra línea descriptiva."
    )
    assert respuesta.status_code == 409
    assert "otra línea descriptiva" in respuesta.text
    assert len(mundo.lotes.listar()) == 1


def test_pedir_con_otra_ficha_de_actividad_es_conflicto() -> None:
    # El lote quedó sembrado con la ficha original y la fuente cambió el
    # título: repetir el pedido no pisa ni ignora el snapshot viejo.
    mundo = _mundo(actividades=[dict(ACTIVIDAD_ROW)])
    lote = mundo.lotes.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(DATOS_ACTIVIDAD),
        personas=_personas_csv(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
        origen_creacion="google",
    )
    # La fuente ahora expone otro título para la misma actividad.
    mundo2 = _mundo(
        actividades=[
            {**ACTIVIDAD_ROW, "titulo": "Curso renombrado en la fuente"}
        ],
        lotes=(lote,),
    )
    _ingresar(mundo2.client)
    respuesta = _post_pedir(mundo2, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 409
    assert "otra ficha de actividad" in respuesta.text
    assert mundo2.lotes.obtener(lote.id_lote).actividad["titulo"] == (
        ACTIVIDAD_ROW["titulo"]
    )


def test_pedir_la_misma_lista_que_sembró_otro_es_conflicto() -> None:
    mundo = _mundo()
    lote = mundo.lotes.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(DATOS_ACTIVIDAD),
        personas=_personas_csv(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_OTRO_APROBADOR),
        origen_creacion="google",
    )
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 409
    assert "otra identidad" in respuesta.text
    assert mundo.lotes.obtener(lote.id_lote).estado == ESTADO_PENDIENTE


# --- errores por campo ------------------------------------------------------


def test_actividad_inexistente_rechaza() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = _post_pedir(
        mundo, actividad="FIE-INEXISTENTE", csv_bytes=CSV_OK.encode()
    )
    assert respuesta.status_code == 400
    assert "Elegí una actividad de la lista" in respuesta.text
    assert mundo.lotes.llamadas_crear == []


def test_actividad_sin_horas_rechaza_sin_inventar() -> None:
    incompleta = dict(ACTIVIDAD_ROW)
    incompleta["duracion_horas"] = ""
    mundo = _mundo(actividades=[incompleta])
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 400
    assert "le faltan datos en la fuente" in respuesta.text
    assert "duracion_horas" in respuesta.text
    assert mundo.lotes.llamadas_crear == []


def test_sin_archivo_rechaza() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo)
    assert respuesta.status_code == 400
    assert "Subí la lista de cierre" in respuesta.text
    assert mundo.lotes.llamadas_crear == []


def test_csv_mal_formado_rechaza_con_numero_de_fila() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    malo = (
        "nombre;apellido;dni;mail;tratamiento;condicion\n"
        "Ana;Prueba;11111111;ana@example.invalid;Sra.;diploma\n"
    )
    respuesta = _post_pedir(mundo, csv_bytes=malo.encode())
    assert respuesta.status_code == 400
    assert "fila 2" in respuesta.text
    # El mensaje no vuelca el contenido de la fila: dice la fila y la
    # regla, nunca el dato rechazado.
    assert "mala@example" not in respuesta.text
    assert mundo.lotes.llamadas_crear == []


def test_linea_ausente_o_invalida_rechaza() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, linea="   ", csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 400
    assert "Escribí la línea descriptiva" in respuesta.text
    con_cifra = _post_pedir(
        mundo, linea="Curso de 24 horas para el área.", csv_bytes=CSV_OK.encode()
    )
    assert con_cifra.status_code == 400
    assert "cifras" in con_cifra.text
    assert mundo.lotes.llamadas_crear == []


def test_crear_no_envia_ni_registra_nada(tmp_path) -> None:
    from agente1.decisiones_form import RegistroDecisiones

    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(registro_decisiones=registro)
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())
    assert respuesta.status_code == 303
    assert registro.procesadas() == ()


# --- bandeja ----------------------------------------------------------------


def test_bandeja_ofrece_pedir_lote_al_aprobador() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    bandeja = mundo.client.get("/bandeja")
    assert "Pedir lote de certificados" in bandeja.text
    assert "/certificados/pedir" in bandeja.text


def test_bandeja_no_ofrece_pedir_a_otro_rol() -> None:
    mundo = _mundo()
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    bandeja = mundo.client.get("/bandeja")
    assert "Pedir lote de certificados" not in bandeja.text


# --- es_lote_demo con origen declarado --------------------------------------


def test_es_lote_demo_reconoce_origen_creacion_demo() -> None:
    mundo = _mundo()
    lote = mundo.lotes.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(DATOS_ACTIVIDAD),
        personas=_personas_csv(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
        origen_creacion="demo",
    )
    assert es_lote_demo(lote) is True


def test_es_lote_demo_no_marca_origen_google_ni_ausente() -> None:
    mundo = _mundo()
    lote_google = mundo.lotes.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(DATOS_ACTIVIDAD),
        personas=_personas_csv(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
        origen_creacion="google",
    )
    assert es_lote_demo(lote_google) is False
    lote_legacy = mundo.lotes.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(DATOS_ACTIVIDAD),
        personas=_personas_csv()[:1],
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
    )
    assert es_lote_demo(lote_legacy) is False


def test_csv_rechaza_mail_duplicado_sin_distinguir_mayusculas() -> None:
    contenido = CSV_OK.replace("luis.ejemplo@example.invalid", "ANA.PRUEBA@EXAMPLE.INVALID")
    with pytest.raises(ListaCierreError) as exc:
        parsear_csv_lista_cierre(contenido.encode())
    assert exc.value.code == "lista_cierre_duplicada"
    assert exc.value.fila == 3


def test_upload_chunked_se_limita_antes_del_parser(monkeypatch) -> None:
    import asyncio

    from starlette.requests import Request

    parser_llamado = False

    async def parser_prohibido(*args, **kwargs):
        nonlocal parser_llamado
        parser_llamado = True
        raise AssertionError("El multipart no debe procesar un cuerpo excedido")

    monkeypatch.setattr(Request, "form", parser_prohibido)
    monkeypatch.setattr(pedido_certificados, "MAX_FORM_BYTES", 100)
    fragmentos = iter((b"x" * 60, b"y" * 60))

    async def recibir():
        return {"type": "http.request", "body": next(fragmentos), "more_body": True}

    request = Request({"type": "http", "headers": []}, receive=recibir)
    with pytest.raises(ListaCierreError) as exc:
        asyncio.run(pedido_certificados._formulario_acotado(request))
    assert exc.value.code == "lista_cierre_csv_grande"
    assert not parser_llamado


def test_pedido_rechaza_linea_con_dos_renglones() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode(), linea="Introducción a herramientas.\nAnálisis documental.")
    assert respuesta.status_code == 400
    assert mundo.lotes.llamadas_crear == []
    assert "una sola línea" in respuesta.text


# --- pedido con Excel de la SEU (#193) ------------------------------------

MIME_XLSX = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _libro_xlsx(hojas: dict[str, list[list[object]]]) -> bytes:
    libro = Workbook()
    libro.remove(libro.active)
    for nombre, filas in hojas.items():
        hoja = libro.create_sheet(nombre)
        for fila in filas:
            hoja.append(fila)
    destino = io.BytesIO()
    libro.save(destino)
    return destino.getvalue()


def _xlsx_seu_pedido() -> bytes:
    aprobados = [
        [None, None, None, None],
        [
            "DE LA FUENTE Ana",
            "DE LA FUENTE Ana",
            "DNI 30.123.456",
            "ANA.PRUEBA@EXAMPLE.INVALID",
        ],
    ]
    inscripcion = [
        [None, "De la Fuente, Ana", "DNI 30.123.456", None, "ana.prueba@example.invalid"],
    ]
    return _libro_xlsx({"Hoja 1": aprobados, "Worksheet": inscripcion})


def _xlsx_plantilla_pedido() -> bytes:
    return _libro_xlsx(
        {
            "Hoja 1": [
                [
                    "nombre",
                    "apellido",
                    "dni",
                    "mail",
                    "tratamiento",
                    "condicion",
                ],
                [
                    "Ana",
                    "Prueba",
                    "11111111",
                    "ana.prueba@example.invalid",
                    "Sra.",
                    "aprobacion",
                ],
                [
                    "Luis",
                    "Ejemplo",
                    "22222222",
                    "luis.ejemplo@example.invalid",
                    "Sr.",
                    "asistencia",
                ],
            ]
        }
    )


def _post_pedir_xlsx(
    mundo: Mundo,
    contenido: bytes,
    *,
    nombre_archivo: str = "aprobados.xlsx",
    **extra: str,
):
    datos = {
        "csrf": _csrf(mundo),
        "actividad": "FIE-DIF-02",
        "linea_descriptiva": LINEA,
    }
    datos.update(extra)
    return mundo.client.post(
        "/certificados/pedir",
        data=datos,
        files={"lista": (nombre_archivo, contenido, MIME_XLSX)},
        follow_redirects=False,
    )


def test_pedir_xlsx_de_la_seu_crea_el_lote_pendiente() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    respuesta = _post_pedir_xlsx(
        mundo,
        _xlsx_seu_pedido(),
        tratamiento="Sra.",
        condicion="asistencia",
    )

    assert respuesta.status_code == 303
    llamada = mundo.lotes.llamadas_crear[-1]
    assert llamada["personas"] == (
        PersonaCierre(
            nombre="Ana",
            apellido="DE LA FUENTE",
            dni="30123456",
            mail="ana.prueba@example.invalid",
            tratamiento="Sra.",
            condicion="asistencia",
        ),
    )
    lote = mundo.lotes.obtener(
        respuesta.headers["location"].rsplit("/", 1)[-1]
    )
    assert lote is not None
    assert lote.estado == ESTADO_PENDIENTE


def test_pedir_xlsx_plantilla_ignora_los_campos_del_formulario() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    respuesta = _post_pedir_xlsx(
        mundo,
        _xlsx_plantilla_pedido(),
        tratamiento="Dr.",
        condicion="asistencia",
    )

    assert respuesta.status_code == 303
    assert mundo.lotes.llamadas_crear[-1]["personas"] == _personas_csv()


def test_pedir_xlsx_sin_inscripcion_no_crea_lote() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)
    solo_aprobados = _libro_xlsx(
        {
            "Hoja 1": [
                [
                    "PEREZ Ana",
                    "PEREZ Ana",
                    "DNI 30123456",
                    "ana.perez@example.invalid",
                ]
            ]
        }
    )

    respuesta = _post_pedir_xlsx(
        mundo,
        solo_aprobados,
        tratamiento="Sra.",
        condicion="aprobacion",
    )

    assert respuesta.status_code == 400
    assert "no tiene hoja de inscripción" in respuesta.text
    assert mundo.lotes.llamadas_crear == []


def test_el_csv_existente_sigue_creando_el_lote() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    respuesta = _post_pedir(mundo, csv_bytes=CSV_OK.encode())

    assert respuesta.status_code == 303
    assert len(mundo.lotes.listar()) == 1


# --- navegación principal --------------------------------------------------


def test_nav_pedir_certificados_visible_para_el_aprobador() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    bandeja = mundo.client.get("/bandeja")
    assert bandeja.status_code == 200
    assert "Pedir certificados" in bandeja.text
    assert 'href="/certificados/pedir"' in bandeja.text

    otra_pagina = mundo.client.get("/nuevo-pedido")
    assert otra_pagina.status_code == 200
    assert "Pedir certificados" in otra_pagina.text

    formulario = mundo.client.get("/certificados/pedir")
    assert re.search(
        r'href="/certificados/pedir"\s+aria-current="page"',
        formulario.text,
    )


def test_nav_pedir_certificados_no_visible_para_otro_rol() -> None:
    mundo = _mundo()
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    bandeja = mundo.client.get("/bandeja")
    assert bandeja.status_code == 200
    assert "Pedir certificados" not in bandeja.text
    assert 'href="/certificados/pedir"' not in bandeja.text

    otra_pagina = mundo.client.get("/nuevo-pedido")
    assert otra_pagina.status_code == 200
    assert "Pedir certificados" not in otra_pagina.text


# --- volver y logo -----------------------------------------------------------


def test_el_logo_lleva_al_inicio_en_todas_las_pantallas() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    for ruta in ("/bandeja", "/nuevo-pedido", "/certificados/pedir"):
        pagina = mundo.client.get(ruta)
        assert pagina.status_code == 200
        assert re.search(r'<a class="cabecera-marca" href="/"', pagina.text)


def test_volver_aparece_fuera_de_la_bandeja() -> None:
    mundo = _mundo()
    _ingresar(mundo.client)

    bandeja = mundo.client.get("/bandeja")
    assert 'class="volver"' not in bandeja.text

    formulario = mundo.client.get("/certificados/pedir")
    assert re.search(
        r'<a class="volver" href="/bandeja#certificados">', formulario.text
    )
    assert "Volver a la bandeja" in formulario.text

    pedido = mundo.client.get("/nuevo-pedido")
    assert re.search(r'<a class="volver" href="/bandeja">', pedido.text)
