"""HU-013 (#24): el canal de interacción como puerto, por encima del seam.

Ejercita `agente1.canal`: el puerto `CanalInteraccion`, el bucle
`atender_canal` y el fake `CanalInteraccionFake`. El adapter de planilla
offline (`CanalPlanillaOffline`) se prueba aparte, en
`test_canal_planilla.py`, sólo por lectura y escritura contra un directorio
temporal.

El bucle no tiene lógica de interpretación propia: por eso estas pruebas lo
ejercitan con el núcleo real (`interpretar_solicitud`), nunca con un doble del
núcleo. Lo único que se verifica del lado del bucle es que lee, despacha y
responde — no que clasifique ni resuelva nada, porque eso ya lo prueba
`test_interpretacion.py`.
"""

from __future__ import annotations

from pathlib import Path

from agente1 import FakeGenerator
from agente1.canal import (
    CanalInteraccionFake,
    PedidoCanal,
    atender_canal,
)
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.interpretacion import IdentidadSolicitante, ROLES_HABILITADOS


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
