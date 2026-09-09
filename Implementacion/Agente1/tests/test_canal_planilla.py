"""HU-013 (#24): adapter de planilla offline para el canal de interacción.

`CanalPlanillaOffline` es un seam delgado: lee pedidos pendientes de un CSV y
escribe la respuesta en otro, contra un directorio temporal. Es la spec la
que pide no sobre-testearlo ("Testing Decisions" de #18: "Se prueba sólo por
lectura y escritura contra un directorio temporal"), así que estas pruebas se
limitan a eso — nunca a lógica de interpretación, que no vive acá.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from agente1.canal import CanalInteraccionFake, PedidoCanal, atender_canal
from agente1.canal_planilla import CanalPlanillaOffline
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.interpretacion import IdentidadSolicitante, ROLES_HABILITADOS
from agente1 import FakeGenerator


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


def _escribir_pedidos(directorio: Path, filas: list[dict[str, str]]) -> None:
    path = directorio / "pedidos.csv"
    with path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo, fieldnames=["id_pedido", "identificador", "rol", "texto"]
        )
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)


def test_lee_un_pedido_pendiente_desde_el_csv(tmp_path: Path) -> None:
    _escribir_pedidos(
        tmp_path,
        [
            {
                "id_pedido": "p-1",
                "identificador": "persona-seu-01",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            }
        ],
    )
    canal = CanalPlanillaOffline(tmp_path)

    pendientes = canal.leer_pendientes()

    assert pendientes == (
        PedidoCanal(
            id_pedido="p-1",
            solicitante=IdentidadSolicitante(identificador="persona-seu-01", rol=ROL_HABILITADO),
            texto="gacetilla SYN-001",
        ),
    )


def test_directorio_sin_planilla_de_pedidos_no_tiene_pendientes(tmp_path: Path) -> None:
    canal = CanalPlanillaOffline(tmp_path)

    assert canal.leer_pendientes() == ()


def test_responder_escribe_una_fila_en_la_planilla_de_respuestas(tmp_path: Path) -> None:
    _escribir_pedidos(
        tmp_path,
        [
            {
                "id_pedido": "p-1",
                "identificador": "persona-seu-01",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            }
        ],
    )
    canal = CanalPlanillaOffline(tmp_path)

    resultados = atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )

    respuestas_path = tmp_path / "respuestas.csv"
    assert respuestas_path.exists()
    with respuestas_path.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 1
    assert filas[0]["id_pedido"] == "p-1"
    assert filas[0]["estado"] == "PENDIENTE_VALIDACION"
    assert filas[0]["referencia_borrador"]
    assert resultados[0].estado == "PENDIENTE_VALIDACION"


def test_un_pedido_ya_respondido_no_vuelve_a_aparecer_como_pendiente(tmp_path: Path) -> None:
    _escribir_pedidos(
        tmp_path,
        [
            {
                "id_pedido": "p-1",
                "identificador": "persona-seu-01",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            }
        ],
    )
    canal = CanalPlanillaOffline(tmp_path)
    atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )

    assert canal.leer_pendientes() == ()


def test_una_fila_de_pedido_con_identidad_incompleta_se_omite(tmp_path: Path) -> None:
    _escribir_pedidos(
        tmp_path,
        [
            {"id_pedido": "p-1", "identificador": "", "rol": "", "texto": "gacetilla SYN-001"},
            {
                "id_pedido": "p-2",
                "identificador": "persona-seu-01",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            },
        ],
    )
    canal = CanalPlanillaOffline(tmp_path)

    pendientes = canal.leer_pendientes()

    assert [p.id_pedido for p in pendientes] == ["p-2"]


def test_dos_pedidos_nuevos_quedan_pendientes_hasta_ser_respondidos(tmp_path: Path) -> None:
    _escribir_pedidos(
        tmp_path,
        [
            {
                "id_pedido": "p-1",
                "identificador": "persona-seu-01",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            },
            {
                "id_pedido": "p-2",
                "identificador": "persona-seu-02",
                "rol": ROL_HABILITADO,
                "texto": "gacetilla SYN-001",
            },
        ],
    )
    canal = CanalPlanillaOffline(tmp_path)

    assert len(canal.leer_pendientes()) == 2

    # Responder únicamente p-1 (a través del bucle real, contra un fake
    # cargado sólo con ese pedido) debe dejar a p-2 como el único pendiente
    # cuando se vuelve a leer la planilla de pedidos.
    pedido_1 = next(p for p in canal.leer_pendientes() if p.id_pedido == "p-1")
    fake_solo_p1 = CanalInteraccionFake(pedidos=(pedido_1,))
    atender_canal(
        fake_solo_p1,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )
    resultado_p1 = fake_solo_p1.respuestas[0][1]
    canal.responder(pedido_1, resultado_p1)

    restantes = canal.leer_pendientes()
    assert [p.id_pedido for p in restantes] == ["p-2"]
