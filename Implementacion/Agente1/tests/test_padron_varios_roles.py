"""Una persona puede tener varios roles en el padrón (17/11/2026).

La SEU designó a la misma persona para aprobar contenido y pagos. El CSV
lleva una fila por rol; cada chequeo pide el rol que lo habilita y la
persona actúa con ese. Con un solo rol nada cambia.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agente1.canal_form import PadronRoles, cargar_padron_roles_csv
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO, ROL_APROBADOR_PAGOS
from agente1.workspace_config import ConfiguracionWorkspaceError

CORREO = "persona@example.invalid"


def _csv(tmp_path: Path, texto: str) -> Path:
    ruta = tmp_path / "padron.csv"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_el_csv_acepta_una_fila_por_rol_y_conserva_el_orden(tmp_path: Path) -> None:
    padron = cargar_padron_roles_csv(
        _csv(
            tmp_path,
            f"correo,rol\n{CORREO},{ROL_APROBADOR_PAGOS}\n"
            f"{CORREO.upper()},{ROL_APROBADOR_CONTENIDO}\n",
        )
    )
    assert padron.roles_para(CORREO) == (ROL_APROBADOR_PAGOS, ROL_APROBADOR_CONTENIDO)
    assert padron.rol_para(CORREO) == ROL_APROBADOR_PAGOS
    assert (
        padron.rol_para(CORREO, (ROL_APROBADOR_CONTENIDO,))
        == ROL_APROBADOR_CONTENIDO
    )
    assert padron.tiene_rol(CORREO, ROL_APROBADOR_CONTENIDO)
    assert padron.tiene_rol(CORREO, ROL_APROBADOR_PAGOS)


def test_sin_el_rol_preferido_devuelve_el_principal() -> None:
    padron = PadronRoles({CORREO: ROL_APROBADOR_PAGOS})
    assert padron.rol_para(CORREO, (ROL_APROBADOR_CONTENIDO,)) == ROL_APROBADOR_PAGOS
    assert not padron.tiene_rol(CORREO, ROL_APROBADOR_CONTENIDO)
    assert padron.roles_para("otra@example.invalid") == ()
    assert padron.rol_para("otra@example.invalid") is None


def test_la_misma_fila_repetida_invalida_el_padron(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_padron_roles_csv(
            _csv(
                tmp_path,
                f"correo,rol\n{CORREO},{ROL_APROBADOR_PAGOS}\n"
                f"{CORREO},{ROL_APROBADOR_PAGOS}\n",
            )
        )
    assert exc.value.code == "padron_roles_invalid"


def test_un_rol_desconocido_en_cualquier_fila_frena_el_padron(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_padron_roles_csv(
            _csv(
                tmp_path,
                f"correo,rol\n{CORREO},{ROL_APROBADOR_CONTENIDO}\n"
                f"{CORREO},rol_inventado\n",
            )
        )
    assert exc.value.code == "padron_rol_desconocido"
