import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_matriz_hu011_v2_es_reproducible_y_no_publica(tmp_path: Path):
    proceso = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "matriz_hu011_v2.py"), "--salida", str(tmp_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proceso.returncode == 0, proceso.stderr
    resumen = json.loads((tmp_path / "matriz.json").read_text(encoding="utf-8"))
    assert resumen["totals"] == {
        "activities": 5,
        "channel_executions": 10,
        "pending_validation": 6,
        "incomplete": 4,
    }
    assert resumen["published"] is False
    assert resumen["trl3_claimed"] is False
    assert resumen["human_review"] == "PENDIENTE"
    completos = [caso for caso in resumen["cases"] if caso["draft_created"]]
    assert len(completos) == 6
    assert all(caso["output_contract_version"] == "post_creative_output_v2" for caso in completos)
    assert all(caso["renderer_version"] == "post_deterministic_renderer_v2" for caso in completos)
