"""Mide cuántos tokens cuesta el documento más grande que admite el contrato.

Reproduce la evidencia de `DEF-A1-013`
(`evidencias/medicion-presupuesto-decodificacion-2026-09-08.md`). Necesita un
Ollama local ya iniciado con el modelo descargado; no descarga ni levanta nada.

Usa `/api/generate` con `raw: true` y `num_predict: 1` porque en esa forma
`prompt_eval_count` devuelve la tokenización exacta del texto enviado, sin
plantilla de chat. Es la única manera de medir el costo de un documento sin
depender de lo que el modelo decida generar.

Los cuatro estilos no son decorativos: el mismo documento, con el mismo largo
en caracteres, cuesta más del doble de tokens escrito en mayúsculas y signos
que en prosa corriente. El presupuesto se dimensiona con ese extremo malo.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.presupuesto import (  # noqa: E402
    CHARS_POR_TOKEN_MENOS_FAVORABLE,
    documento_maximo,
    presupuesto_minimo_num_predict,
)

ESTILOS = {
    "prosa institucional": (
        "La Facultad invita a la comunidad academica a sumarse a esta propuesta "
        "de formacion continua, pensada para compartir experiencias y "
        "fortalecer vinculos. "
    ),
    "prosa con acentuacion densa": (
        "La Ingeniería está también aquí: participación, formación técnica, "
        "investigación aplicada y difusión académica según cada área temática "
        "común. "
    ),
    "palabras de una y dos letras": (
        "y de la el un no se te da vi fe ir ah oh su mi tu es va ha uy ex ok ya "
        "al so id os ni ay pe ce "
    ),
    "mayusculas y signos": (
        "¡ATENCIÓN! ¿QUÉ? —SÍ— «JORNADA» #Área/2026: (Inscripción) [Cupos]; "
        "¡ÚLTIMOS! ¿DÓNDE? —AQUÍ— «SEDE» #Ñandú/2026: (Vacantes) [Límite]; "
    ),
}


def _contrato(version: str) -> dict[str, object]:
    ruta = (
        ROOT / "src" / "agente1" / "contracts" / f"post_creative_output_{version}.schema.json"
    )
    return json.loads(ruta.read_text(encoding="utf-8"))


def _con_estilo(documento: str, muestra: str) -> str:
    """Reemplaza el relleno por texto real conservando el largo de cada campo."""

    campos = json.loads(documento)
    for clave, valor in campos.items():
        if isinstance(valor, str):
            largo = len(valor)
            campos[clave] = (muestra * (largo // len(muestra) + 1))[:largo]
    return json.dumps(campos, ensure_ascii=False, separators=(",", ":"))


def _tokens(base_url: str, modelo: str, texto: str) -> int:
    cuerpo = json.dumps(
        {
            "model": modelo,
            "prompt": texto,
            "raw": True,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 1},
        }
    ).encode("utf-8")
    peticion = urllib.request.Request(
        f"{base_url}/api/generate",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        return json.loads(respuesta.read())["prompt_eval_count"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--modelo", default="llama3.2:3b")
    parser.add_argument("--contrato", default="v3", choices=("v2", "v3"))
    args = parser.parse_args()

    contrato = _contrato(args.contrato)
    documento = documento_maximo(contrato)
    print(f"contrato {args.contrato}: documento maximo de {len(documento)} caracteres")
    print()

    peor = None
    for nombre, muestra in ESTILOS.items():
        texto = _con_estilo(documento, muestra)
        try:
            tokens = _tokens(args.base_url, args.modelo, texto)
        except (urllib.error.URLError, OSError) as exc:
            print(f"no se pudo contactar a Ollama en {args.base_url}: {exc}", file=sys.stderr)
            return 1
        ratio = len(texto) / tokens
        peor = ratio if peor is None else min(peor, ratio)
        print(f"  {nombre:32s} tokens={tokens:4d}  caracteres_por_token={ratio:.2f}")

    print()
    print(f"extremo malo medido ahora:        {peor:.2f} caracteres por token")
    print(f"extremo malo versionado:          {CHARS_POR_TOKEN_MENOS_FAVORABLE:.2f}")
    print(f"presupuesto derivado del contrato: {presupuesto_minimo_num_predict(contrato)} tokens")
    if peor < CHARS_POR_TOKEN_MENOS_FAVORABLE:
        print()
        print(
            "ATENCION: esta corrida midio un extremo peor que el versionado. "
            "El presupuesto derivado quedo corto; hay que actualizar "
            "CHARS_POR_TOKEN_MENOS_FAVORABLE y revisar el default.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
