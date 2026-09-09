"""HU-013 (#24, #25): el canal de interacción como puerto, por encima del seam.

Ejercita `agente1.canal`: el puerto `CanalInteraccion`, el bucle
`atender_canal` y el fake `CanalInteraccionFake`. El adapter de planilla
offline (`CanalPlanillaOffline`) se prueba aparte, en
`test_canal_planilla.py`, sólo por lectura y escritura contra un directorio
temporal.

El bucle no tiene lógica de interpretación propia: por eso estas pruebas lo
ejercitan con el núcleo real (`interpretar_solicitud`), nunca con un doble del
núcleo. Lo único que se verifica del lado del bucle es que lee, despacha y
responde — no que clasifique ni resuelva nada, porque eso ya lo prueba
`test_interpretacion.py`. Lo mismo vale para el estado entre turnos (#25):
la única cobertura que corresponde acá es que dos llamadas independientes de
`atender_canal` con la misma instancia de `registro_pendientes` alcanzan para
que el segundo turno resuelva la repregunta que dejó el primero — la
resolución por orden, por rasgo y el vencimiento ya se prueban a fondo contra
el seam en `test_interpretacion.py`, sección 11.
"""

from __future__ import annotations

import json
from pathlib import Path

from agente1 import FakeGenerator
from agente1.canal import (
    CanalInteraccionFake,
    PedidoCanal,
    atender_canal,
)
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.interpretacion import (
    ROLES_HABILITADOS,
    IdentidadSolicitante,
    RegistroPendientesMemoria,
)


ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"
ROL_HABILITADO = next(iter(ROLES_HABILITADOS))

_BORRADOR_CONFORME = (
    "## TÍTULO\n"
    "Taller sintético de vinculación\n\n"
    "## DATOS DE LA ACTIVIDAD\n"
    "Fecha: 2026-08-05\n"
    "Organiza: Equipo de prueba\n"
    "Lugar: Aula de prueba\n\n"
    "## CONTACTO\n"
    "pruebas@example.invalid\n\n"
    "## BAJADA\n"
    "Bajada breve de prueba.\n\n"
    "## CUERPO\n"
    "Cuerpo breve de prueba."
)


def _identidad(rol: str = ROL_HABILITADO, identificador: str = "persona-seu-01") -> IdentidadSolicitante:
    return IdentidadSolicitante(identificador=identificador, rol=rol)


def test_fake_devuelve_los_pedidos_pendientes_cargados() -> None:
    pedido = PedidoCanal(id_pedido="p-1", solicitante=_identidad(), texto="gacetilla SYN-001")
    canal = CanalInteraccionFake(pedidos=(pedido,))

    assert canal.leer_pendientes() == (pedido,)


def test_fake_deja_de_listar_un_pedido_una_vez_respondido(tmp_path: Path) -> None:
    pedido = PedidoCanal(id_pedido="p-1", solicitante=_identidad(), texto="gacetilla SYN-001")
    canal = CanalInteraccionFake(pedidos=(pedido,))

    resultados = atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )

    assert canal.leer_pendientes() == ()
    assert len(resultados) == 1
    assert resultados[0].estado == "PENDIENTE_VALIDACION"


def test_el_bucle_registra_la_respuesta_junto_al_pedido_en_el_fake(tmp_path: Path) -> None:
    pedido = PedidoCanal(id_pedido="p-1", solicitante=_identidad(), texto="gacetilla SYN-001")
    canal = CanalInteraccionFake(pedidos=(pedido,))

    atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )

    assert len(canal.respuestas) == 1
    pedido_respondido, resultado = canal.respuestas[0]
    assert pedido_respondido == pedido
    assert resultado.borrador_path is not None


def test_el_bucle_atiende_varios_pedidos_en_orden_y_no_mezcla_identidades(
    tmp_path: Path,
) -> None:
    pedido_valido = PedidoCanal(
        id_pedido="p-1", solicitante=_identidad(), texto="gacetilla SYN-001"
    )
    pedido_sin_rol = PedidoCanal(
        id_pedido="p-2",
        solicitante=_identidad(rol="rol_inexistente"),
        texto="gacetilla SYN-001",
    )
    canal = CanalInteraccionFake(pedidos=(pedido_valido, pedido_sin_rol))

    resultados = atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )

    assert [r.estado for r in resultados] == ["PENDIENTE_VALIDACION", "RECHAZADA"]
    assert canal.respuestas[1][1].error is not None


class _FuenteConActividadesAmbiguas:
    """Dos actividades con título, fecha y organización idénticos: cualquier
    consulta sobre ellas empata exactamente, para forzar una repregunta
    (#25) sin depender de márgenes delicados del dataset sintético real. Ver
    el mismo fixture en `test_interpretacion.py`, sección 11."""

    _FILA_BASE = {
        "descripcion": "",
        "publico": "",
        "contacto": "",
        "fuente": "",
        "lugar": "",
        "titulo": "Taller de robótica educativa",
        "fecha": "2026-09-01",
        "organiza": "Equipo ambiguo",
    }

    def obtener(self, id_solicitud: str) -> dict[str, str]:
        for fila in self.enumerar():
            if fila["id_solicitud"] == id_solicitud:
                return fila
        raise AssertionError("no debería pedirse una actividad ambigua por id")

    def enumerar(self) -> list[dict[str, str]]:
        return [
            {**self._FILA_BASE, "id_solicitud": "AMB-001"},
            {**self._FILA_BASE, "id_solicitud": "AMB-002"},
        ]


def test_atender_canal_resuelve_una_repregunta_en_el_turno_siguiente(
    tmp_path: Path,
) -> None:
    """La pendiente vive en el puerto `registro_pendientes`, no en el bucle:
    pasar la misma instancia a dos llamadas independientes de `atender_canal`
    alcanza para que el segundo pedido de la misma persona resuelva la
    repregunta que dejó el primero — exactamente el recorrido que hace
    `atender_canal` en producción, turno a turno (#24, #25)."""
    registro_pendientes = RegistroPendientesMemoria()
    identidad = _identidad(identificador="persona-canal-pendiente")

    primer_turno = CanalInteraccionFake(
        pedidos=(
            PedidoCanal(
                id_pedido="p-1",
                solicitante=identidad,
                texto="Quiero la gacetilla del taller de robotica educativa",
            ),
        )
    )
    resultados_primer_turno = atender_canal(
        primer_turno,
        fuente=_FuenteConActividadesAmbiguas(),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
        registro_pendientes=registro_pendientes,
    )
    assert resultados_primer_turno[0].estado == "PENDIENTE_DESAMBIGUACION"
    assert registro_pendientes.obtener(identidad.identificador) is not None

    segundo_turno = CanalInteraccionFake(
        pedidos=(
            PedidoCanal(id_pedido="p-2", solicitante=identidad, texto="El segundo"),
        )
    )
    resultados_segundo_turno = atender_canal(
        segundo_turno,
        fuente=_FuenteConActividadesAmbiguas(),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
        registro_pendientes=registro_pendientes,
    )

    resultado_segundo = resultados_segundo_turno[0]
    assert resultado_segundo.intencion == "generar_gacetilla"
    registro = _ultima_linea(resultado_segundo.log_path)
    assert registro["id_actividad"] == "AMB-002"
    assert registro_pendientes.obtener(identidad.identificador) is None


def _ultima_linea(log_path: Path) -> dict[str, object]:
    return json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
