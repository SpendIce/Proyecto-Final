#!/usr/bin/env python3
"""Consola visual de la demo: pedido de borradores sobre la planilla D2.

Se sirve desde el servidor y se abre por un túnel SSH. No publica nada: cada
pieza queda en Drive con la marca `BORRADOR — NO PUBLICAR` y el estado
`PENDIENTE_VALIDACION`.

El pedido elige una actividad que ya está en la planilla y las piezas a
generar: gacetilla (HU-010) y posts de Instagram y LinkedIn (HU-011). Los datos
de la actividad los lee el agente de la planilla; la consola no los pide. Cada
pieza corre el mismo `workspace_e2e.py` que usa la demo headless. Aparte, la
consola permite cargar una actividad nueva en la planilla.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.fuentes import COLUMNAS_ACTIVIDADES_V2  # noqa: E402
from agente1.google_workspace import (  # noqa: E402
    DRIVE_HOST,
    SHEETS_HOST,
    HttpsWorkspaceTransport,
)
from agente1.workspace_auth import construir_token_provider  # noqa: E402
from agente1.workspace_config import cargar_configuracion_workspace  # noqa: E402

ACTIVIDAD_INICIAL = "FIE-DIF-08"
MODELO = "gemma4:e4b"
TIMEOUT_MODELO = 300.0
# Pieza → argumentos de `workspace_e2e.py` y nombre visible.
PIEZAS = {
    "gacetilla": (["--tipo", "gacetilla"], "Gacetilla", "HU-010"),
    "post_instagram": (["--tipo", "post", "--canal", "instagram"], "Post de Instagram", "HU-011"),
    "post_linkedin": (["--tipo", "post", "--canal", "linkedin"], "Post de LinkedIn", "HU-011"),
}
# Filas de prueba que la planilla arrastra de corridas anteriores.
PREFIJOS_OCULTOS = ("DEMO-", "SYN-")
FUENTE_CARGA_MANUAL = "Carga manual en la consola de la demo"
MODALIDADES = ("presencial", "virtual", "híbrida", "online y autogestionado")
RUNS: dict[str, dict[str, object]] = {}
RUNS_LOCK = threading.Lock()
WARMUP = {"estado": "calentando"}
WARMUP_LOCK = threading.Lock()


def _modo_auth() -> str:
    """Elige el modo de credencial de la demo sin exponerlo en la UI."""
    pedido = os.environ.get("AGENTE1_DEMO_AUTH", "").strip().lower()
    if pedido in {"service_account", "oauth"}:
        return pedido
    if (
        os.environ.get("AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY")
        and os.environ.get("AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT")
    ):
        return "service_account"
    return "oauth"


AUTH_MODE = _modo_auth()


def _texto(valor: object) -> str:
    return valor if isinstance(valor, str) else ""


def _token() -> str:
    return construir_token_provider().obtener_access_token()


def _pedir(
    metodo: str,
    host: str,
    target: str,
    *,
    cuerpo: bytes | None = None,
    timeout_s: float = 30.0,
) -> tuple[int, bytes]:
    transporte = HttpsWorkspaceTransport()
    respuesta = transporte.request(
        method=metodo,
        host=host,
        target=target,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        body=cuerpo,
        deadline=time.monotonic() + timeout_s,
        max_response_bytes=4_000_000,
    )
    return respuesta.status, respuesta.body


def _pestaña(config) -> str:
    return config.rango_a1.split("!", 1)[0]


def _leer_actividades() -> list[dict[str, str]]:
    config = cargar_configuracion_workspace()
    rango = quote(_pestaña(config), safe="")
    estado, cuerpo = _pedir(
        "GET", SHEETS_HOST, f"/v4/spreadsheets/{config.spreadsheet_id}/values/{rango}"
    )
    if estado != 200:
        raise RuntimeError(f"sheets_read_http_{estado}")
    valores = json.loads(cuerpo.decode("utf-8")).get("values", [])
    if not valores:
        return []
    cabecera = valores[0]
    return [
        {campo: _texto(dict(zip(cabecera, fila)).get(campo)) for campo in COLUMNAS_ACTIVIDADES_V2}
        for fila in valores[1:]
        if fila
    ]


def _actividades_visibles(actividades: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        actividad
        for actividad in actividades
        if actividad["id_actividad"] and not actividad["id_actividad"].startswith(PREFIJOS_OCULTOS)
    ]


def _agregar_fila(fila: dict[str, str]) -> None:
    config = cargar_configuracion_workspace()
    rango = quote(f"{_pestaña(config)}!A1:O1", safe="")
    objetivo = (
        f"/v4/spreadsheets/{config.spreadsheet_id}/values/{rango}:append"
        "?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    valores = [[fila[campo] for campo in COLUMNAS_ACTIVIDADES_V2]]
    estado, _ = _pedir(
        "POST",
        SHEETS_HOST,
        objetivo,
        cuerpo=json.dumps({"values": valores}).encode("utf-8"),
    )
    if estado != 200:
        raise RuntimeError(f"sheets_append_http_{estado}")


def _documento_mas_nuevo(desde: float) -> dict[str, str] | None:
    objetivo = (
        "/drive/v3/files?pageSize=20&orderBy=createdTime%20desc"
        "&fields=files(id,name,mimeType,createdTime,webViewLink)"
    )
    estado, cuerpo = _pedir("GET", DRIVE_HOST, objetivo, timeout_s=20)
    if estado != 200:
        return None
    try:
        archivos = json.loads(cuerpo.decode("utf-8")).get("files", [])
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    for archivo in archivos:
        if archivo.get("mimeType") != "application/vnd.google-apps.document":
            continue
        creado = _texto(archivo.get("createdTime"))
        try:
            marca = datetime.fromisoformat(creado.replace("Z", "+00:00")).timestamp()
        except ValueError:
            marca = 0
        if marca + 5 < desde:
            continue
        return {
            "id": _texto(archivo.get("id")),
            "name": _texto(archivo.get("name")),
            "url": _texto(archivo.get("webViewLink")),
        }
    return None


def _exportar_documento(doc_id: str) -> str:
    objetivo = f"/drive/v3/files/{doc_id}/export?mimeType=text%2Fplain"
    estado, cuerpo = _pedir("GET", DRIVE_HOST, objetivo, timeout_s=20)
    if estado != 200:
        raise RuntimeError(f"docs_export_http_{estado}")
    return cuerpo.decode("utf-8", errors="replace")


def _detalle_fallo(run_dir: Path) -> str:
    ruta = run_dir / "logs" / "ejecuciones.jsonl"
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "no se pudo leer el registro de la corrida"
    if not lineas:
        return "la corrida no dejó registro"
    try:
        ultimo = json.loads(lineas[-1])
    except json.JSONDecodeError:
        return "el registro de la corrida no es JSON"
    errores = ultimo.get("validation_errors") or []
    partes = [ultimo.get("resultado"), ", ".join(errores) if errores else ultimo.get("error")]
    return " · ".join(str(p) for p in partes if p) or "falló sin detalle"


def _entorno_agente() -> dict[str, str]:
    entorno = dict(os.environ)
    if AUTH_MODE == "oauth":
        for clave in (
            "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY",
            "AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT",
            "AGENTE1_WORKSPACE_ACCESS_TOKEN",
        ):
            entorno.pop(clave, None)
    return entorno


def _generar_pieza(run_id: str, indice: int, id_actividad: str, pieza: str) -> None:
    # Cada pedido es una solicitud nueva: lleva su propio registro de
    # idempotencia, así pedir otra vez la misma actividad genera otro borrador.
    run_dir = Path("/tmp/demo-visual-planb") / run_id / pieza
    run_dir.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    with RUNS_LOCK:
        RUNS[run_id]["piezas"][indice].update({"estado": "generando", "inicio": inicio})
    comando = [
        sys.executable,
        str(ROOT / "scripts" / "workspace_e2e.py"),
        "--live",
        "--confirm-write-workspace",
        *PIEZAS[pieza][0],
        "--id-solicitud",
        id_actividad,
        "--salida",
        str(run_dir),
        "--modelo",
        MODELO,
        "--timeout-modelo",
        f"{TIMEOUT_MODELO:g}",
    ]
    detalle = ""
    documento = None
    try:
        proceso = subprocess.run(
            comando,
            cwd=ROOT,
            env=_entorno_agente(),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_MODELO + 120,
            check=False,
        )
        payload = {}
        for linea in reversed(proceso.stdout.splitlines()):
            try:
                payload = json.loads(linea)
                break
            except json.JSONDecodeError:
                continue
        estado_cli = payload.get("estado")
        if estado_cli in {"PENDIENTE_VALIDACION", "DUPLICADA"}:
            estado = "listo"
            documento = _documento_mas_nuevo(inicio)
            if estado_cli == "DUPLICADA":
                detalle = "ya existía un borrador para esta solicitud; no se creó otro"
        else:
            estado = "rechazado"
            detalle = _detalle_fallo(run_dir)
    except subprocess.TimeoutExpired:
        estado = "error"
        detalle = "la corrida excedió el tiempo máximo"
    except Exception:
        estado = "error"
        detalle = "no se pudo ejecutar el agente"
    with RUNS_LOCK:
        RUNS[run_id]["piezas"][indice].update(
            {
                "estado": estado,
                "segundos": round(time.time() - inicio),
                "detalle": detalle,
                "doc_id": documento["id"] if documento else "",
                "doc_name": documento["name"] if documento else "",
                "doc_url": documento["url"] if documento else "",
            }
        )


def _correr(run_id: str, id_actividad: str, piezas: list[str]) -> None:
    # Una pieza por vez: el servidor no tiene GPU y dos generaciones en paralelo
    # se reparten los cuatro núcleos.
    for indice, pieza in enumerate(piezas):
        _generar_pieza(run_id, indice, id_actividad, pieza)
    with RUNS_LOCK:
        RUNS[run_id]["terminado"] = True


def _calentar_modelo() -> None:
    datos = json.dumps(
        {
            "model": MODELO,
            "prompt": "Responde sólo OK.",
            "stream": False,
            "keep_alive": "4h",
            "options": {"num_predict": 1, "temperature": 0},
        }
    ).encode("utf-8")
    try:
        import urllib.request

        pedido = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=datos,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_MODELO) as respuesta:
            respuesta.read()
        with WARMUP_LOCK:
            WARMUP["estado"] = "listo"
    except Exception:
        with WARMUP_LOCK:
            WARMUP["estado"] = "error"


def _estado_modelo() -> str:
    with WARMUP_LOCK:
        return str(WARMUP["estado"])


def _pagina() -> str:
    modalidades = "".join(f'<option value="{m}">{m}</option>' for m in MODALIDADES)
    piezas = "".join(
        f'<label class="pieza"><input type="checkbox" name="piezas" value="{clave}"'
        f'{" checked" if clave != "post_linkedin" else ""}>'
        f"<span>{html.escape(nombre)}</span><small>{hu}</small></label>"
        for clave, (_, nombre, hu) in PIEZAS.items()
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente 1 · Extensión Bot</title>
<style>
:root {{
  --tinta: #0b2545;
  --gris: #4f5d70;
  --suave: #7b8798;
  --oro: #c8a24a;
  --fondo: #f5f3ee;
  --blanco: #ffffff;
  --linea: #dcd6c8;
  --ok: #1f6f4a;
  --mal: #9a3b2f;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--fondo); color: var(--tinta); font: 15px/1.45 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }}
header {{ background: var(--tinta); color: var(--blanco); padding: 16px 32px; border-bottom: 3px solid var(--oro); display: flex; justify-content: space-between; align-items: baseline; gap: 16px; flex-wrap: wrap; }}
header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
header .meta {{ color: #c9d2e0; font-size: 13px; }}
main {{ max-width: 1280px; margin: 22px auto 40px; padding: 0 20px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; }}
.card {{ background: var(--blanco); border: 1px solid var(--linea); border-radius: 12px; padding: 20px; }}
h2 {{ margin: 0 0 14px; font-size: 17px; }}
label {{ display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 600; color: var(--gris); }}
input, textarea, select {{ border: 1px solid #cdd3dc; border-radius: 8px; padding: 8px 10px; font: inherit; font-size: 14px; color: var(--tinta); background: #fbfbfc; }}
select {{ font-size: 15px; }}
textarea {{ resize: vertical; }}
.ficha {{ margin-top: 14px; border: 1px solid #e6e1d6; border-radius: 10px; background: #fcfbf8; padding: 14px 16px; }}
.ficha h3 {{ margin: 0 0 6px; font-size: 15px; }}
.ficha p {{ margin: 0 0 10px; color: var(--gris); font-size: 13.5px; }}
.ficha dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 3px 14px; margin: 0; font-size: 13px; }}
.ficha dt {{ color: var(--suave); }}
.ficha dd {{ margin: 0; }}
.piezas {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }}
.pieza {{ flex-direction: row; align-items: center; gap: 8px; padding: 9px 12px; border: 1px solid #d6dce5; border-radius: 9px; font-size: 14px; color: var(--tinta); cursor: pointer; }}
.pieza small {{ color: var(--suave); font-weight: 500; }}
button {{ border: 0; border-radius: 8px; padding: 11px 16px; font: inherit; font-weight: 700; cursor: pointer; }}
.primario {{ background: var(--tinta); color: var(--blanco); width: 100%; margin-top: 16px; }}
.primario:disabled {{ opacity: .5; cursor: wait; }}
.secundario {{ background: #edf0f5; color: var(--tinta); font-size: 13px; padding: 7px 11px; text-decoration: none; display: inline-block; }}
details {{ margin-top: 18px; border-top: 1px solid var(--linea); padding-top: 14px; }}
summary {{ cursor: pointer; font-weight: 700; font-size: 14px; color: var(--gris); }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; margin-top: 12px; }}
.grid .ancho {{ grid-column: 1 / -1; }}
.badge {{ display: inline-block; padding: 3px 8px; border-radius: 999px; background: #e9edf3; color: var(--gris); font-size: 12px; font-weight: 700; }}
.badge.ok {{ background: #e3f2e9; color: var(--ok); }}
.badge.mal {{ background: #f7e5e1; color: var(--mal); }}
.vacio {{ color: var(--suave); font-size: 14px; }}
.fila {{ border: 1px solid #e3e7ee; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }}
.fila .cab {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
.fila .nombre {{ font-weight: 700; }}
.fila .detalle {{ margin-top: 6px; font-size: 13px; color: var(--gris); word-break: break-word; }}
.fila .acciones {{ display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }}
.fila.generando {{ border-color: var(--oro); background: #fffcf3; }}
.fila.listo {{ border-color: #b9dcc7; }}
.fila.mal {{ border-color: #e7c2bb; background: #fdf6f4; }}
pre {{ margin: 10px 0 0; padding: 14px; background: #fbfaf6; border: 1px solid var(--linea); border-radius: 8px; white-space: pre-wrap; line-height: 1.5; font: 12.5px/1.5 ui-monospace, "SFMono-Regular", Menlo, monospace; max-height: 440px; overflow: auto; }}
.nota {{ margin: 14px 0 0; font-size: 12px; color: var(--suave); }}
.aviso {{ margin-top: 10px; font-size: 13px; }}
.aviso.mal {{ color: var(--mal); }}
.aviso.ok {{ color: var(--ok); }}
@media (max-width: 960px) {{ main {{ grid-template-columns: 1fr; }} .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>Agente 1 · Extensión Bot</h1>
  <span class="meta">Planilla D2 · servidor de la facultad · <span id="modelo">{MODELO}</span></span>
</header>
<main>
  <section class="card">
    <h2>Pedido de borradores</h2>
    <form id="pedido" autocomplete="off">
      <label>Actividad
        <select name="id_actividad" id="actividad"><option>Cargando la planilla…</option></select>
      </label>
      <div class="ficha" id="ficha" hidden></div>
      <div class="piezas">{piezas}</div>
      <button class="primario" type="submit" id="enviar">Generar borradores</button>
      <div class="aviso" id="aviso-pedido"></div>
    </form>

    <details id="nueva">
      <summary>Cargar una actividad nueva en la planilla</summary>
      <form id="form-actividad" autocomplete="off">
        <div class="grid">
          <label class="ancho">Título<input name="titulo" required></label>
          <label class="ancho">Descripción<textarea name="descripcion" rows="3" required></textarea></label>
          <label>Fecha de inicio<input type="date" name="fecha_inicio" required></label>
          <label>Fecha de fin<input type="date" name="fecha_fin"></label>
          <label>Límite de inscripción<input type="date" name="fecha_limite_inscripcion"></label>
          <label>Hora<input name="hora" placeholder="18:30 a 20:30"></label>
          <label>Modalidad<select name="modalidad"><option value=""></option>{modalidades}</select></label>
          <label>Duración en horas<input type="number" name="duracion_horas" min="1"></label>
          <label class="ancho">Público<input name="publico" required></label>
          <label>Organiza<input name="organiza" value="Facultad de Ingeniería del Ejército" required></label>
          <label>Contacto<input type="email" name="contacto" required></label>
          <label>Enlace de inscripción<input name="enlace_inscripcion"></label>
          <label>Lugar<input name="lugar"></label>
          <label class="ancho">Fuente<select name="fuente" id="fuente"></select></label>
        </div>
        <button class="primario" type="submit" id="guardar">Agregar a la planilla</button>
        <div class="aviso" id="aviso-actividad"></div>
      </form>
    </details>
  </section>

  <section class="card">
    <h2>Borradores</h2>
    <div id="lista"><p class="vacio">Todavía no se pidió ningún borrador.</p></div>
    <p class="nota">Cada pieza queda en Drive como borrador pendiente de validación humana. No se publica ni se envía nada.</p>
  </section>
</main>
<script>
const CAMPOS_FICHA = ['fecha_inicio', 'fecha_fin', 'hora', 'modalidad', 'publico', 'organiza', 'contacto'];
const ETIQUETAS = {{fecha_inicio: 'Inicio', fecha_fin: 'Fin', hora: 'Hora', modalidad: 'Modalidad', publico: 'Público', organiza: 'Organiza', contacto: 'Contacto'}};
const sel = document.getElementById('actividad');
const ficha = document.getElementById('ficha');
const lista = document.getElementById('lista');
const enviar = document.getElementById('enviar');
const avisoPedido = document.getElementById('aviso-pedido');
let actividades = [];

function esc(t) {{ const d = document.createElement('div'); d.textContent = t || ''; return d.innerHTML; }}
function aviso(el, texto, clase) {{ el.textContent = texto; el.className = 'aviso' + (clase ? ' ' + clase : ''); }}

function mostrarFicha() {{
  const a = actividades.find((x) => x.id_actividad === sel.value);
  if (!a) {{ ficha.hidden = true; return; }}
  const filas = CAMPOS_FICHA.filter((c) => a[c]).map((c) => '<dt>' + ETIQUETAS[c] + '</dt><dd>' + esc(a[c]) + '</dd>').join('');
  ficha.innerHTML = '<h3>' + esc(a.titulo) + '</h3><p>' + esc(a.descripcion) + '</p><dl>' + filas + '</dl>';
  ficha.hidden = false;
}}

async function cargarActividades(seleccion) {{
  const r = await fetch('/actividades');
  const d = await r.json();
  if (!r.ok) {{ sel.innerHTML = '<option>No se pudo leer la planilla</option>'; return; }}
  actividades = d.actividades;
  sel.innerHTML = actividades.map((a) => '<option value="' + esc(a.id_actividad) + '">' + esc(a.titulo) + ' (' + esc(a.id_actividad) + ')</option>').join('');
  sel.value = seleccion || d.inicial || (actividades[0] && actividades[0].id_actividad) || '';
  document.getElementById('fuente').innerHTML = d.fuentes.map((f) => '<option>' + esc(f) + '</option>').join('');
  mostrarFicha();
}}

async function salud() {{
  try {{
    const d = await (await fetch('/health')).json();
    document.getElementById('modelo').textContent = d.modelo + (d.warmup === 'listo' ? ' · cargado' : ' · ' + d.warmup);
  }} catch (e) {{}}
}}

function pintar(run) {{
  lista.innerHTML = run.piezas.map((p, i) => {{
    let estado = 'en espera', clase = '', badge = 'badge';
    if (p.estado === 'generando') {{ estado = 'generando · ' + Math.round(Date.now() / 1000 - p.inicio) + ' s'; clase = 'generando'; }}
    if (p.estado === 'listo') {{ estado = 'pendiente de validación · ' + p.segundos + ' s'; clase = 'listo'; badge += ' ok'; }}
    if (p.estado === 'rechazado') {{ estado = 'rechazado por el gate'; clase = 'mal'; badge += ' mal'; }}
    if (p.estado === 'error') {{ estado = 'error'; clase = 'mal'; badge += ' mal'; }}
    let cuerpo = '';
    if (p.doc_name) cuerpo += '<div class="detalle">' + esc(p.doc_name) + '</div>';
    if (p.detalle) cuerpo += '<div class="detalle">' + esc(p.detalle) + '</div>';
    if (p.doc_url) cuerpo += '<div class="acciones"><a class="secundario" target="_blank" rel="noopener" href="' + esc(p.doc_url) + '">Abrir en Drive</a><button class="secundario" type="button" data-texto="' + i + '">Ver texto</button></div><pre id="texto-' + i + '" hidden></pre>';
    return '<div class="fila ' + clase + '"><div class="cab"><span class="nombre">' + esc(p.nombre) + '</span><span class="' + badge + '">' + estado + '</span></div>' + cuerpo + '</div>';
  }}).join('');
}}

let runActual = null;
async function seguir(id) {{
  while (true) {{
    const run = await (await fetch('/estado/' + id)).json();
    runActual = run;
    pintar(run);
    if (run.terminado) return;
    await new Promise((ok) => setTimeout(ok, 1000));
  }}
}}

lista.addEventListener('click', async (e) => {{
  const i = e.target.dataset.texto;
  if (i === undefined || !runActual) return;
  const pre = document.getElementById('texto-' + i);
  if (!pre.hidden) {{ pre.hidden = true; return; }}
  e.target.disabled = true;
  try {{
    const r = await fetch('/documento/' + runActual.run_id + '/' + i);
    const d = await r.json();
    pre.textContent = r.ok ? d.texto : 'No se pudo leer el documento.';
    pre.hidden = false;
  }} finally {{ e.target.disabled = false; }}
}});

sel.addEventListener('change', mostrarFicha);

document.getElementById('pedido').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const datos = new URLSearchParams(new FormData(e.target));
  if (!datos.getAll('piezas').length) {{ aviso(avisoPedido, 'Elegí al menos una pieza.', 'mal'); return; }}
  enviar.disabled = true;
  aviso(avisoPedido, '');
  try {{
    const r = await fetch('/generar', {{method: 'POST', body: datos}});
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'no se pudo iniciar el pedido');
    await seguir(d.run_id);
  }} catch (error) {{
    aviso(avisoPedido, 'Error: ' + error.message, 'mal');
  }} finally {{
    enviar.disabled = false;
  }}
}});

document.getElementById('form-actividad').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const avisoAct = document.getElementById('aviso-actividad');
  try {{
    const r = await fetch('/actividad', {{method: 'POST', body: new URLSearchParams(new FormData(e.target))}});
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'no se pudo guardar');
    aviso(avisoAct, 'Actividad ' + d.id_actividad + ' agregada a la planilla.', 'ok');
    e.target.reset();
    await cargarActividades(d.id_actividad);
  }} catch (error) {{
    aviso(avisoAct, 'Error: ' + error.message, 'mal');
  }}
}});

cargarActividades();
salud();
setInterval(salud, 5000);
</script>
</body>
</html>"""


def _leer_formulario(handler: BaseHTTPRequestHandler) -> dict[str, list[str]]:
    largo = int(handler.headers.get("Content-Length", "0"))
    return parse_qs(handler.rfile.read(largo).decode("utf-8"), keep_blank_values=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "Agente1Demo/2.0"

    def log_message(self, *args) -> None:  # noqa: D401 - silencio para la demo
        return

    def _json(self, datos: object, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _html(self, texto: str) -> None:
        cuerpo = texto.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self) -> None:  # noqa: N802 - API de http.server
        ruta = urlparse(self.path).path
        if ruta == "/":
            self._html(_pagina())
            return
        if ruta == "/health":
            self._json({"modelo": MODELO, "warmup": _estado_modelo()})
            return
        if ruta == "/actividades":
            try:
                todas = _leer_actividades()
            except Exception:
                self._json({"error": "no_se_pudo_leer_la_planilla"}, 502)
                return
            visibles = _actividades_visibles(todas)
            fuentes = sorted({a["fuente"] for a in visibles if a["fuente"]} | {FUENTE_CARGA_MANUAL})
            self._json(
                {
                    "actividades": visibles,
                    "fuentes": fuentes,
                    "inicial": ACTIVIDAD_INICIAL
                    if any(a["id_actividad"] == ACTIVIDAD_INICIAL for a in visibles)
                    else "",
                }
            )
            return
        if ruta.startswith("/estado/"):
            run_id = ruta.split("/", 2)[2]
            with RUNS_LOCK:
                datos = json.loads(json.dumps(RUNS.get(run_id, {})))
            if not datos:
                self._json({"error": "run_not_found"}, 404)
                return
            self._json(datos)
            return
        if ruta.startswith("/documento/"):
            partes = ruta.split("/")
            if len(partes) != 4 or not partes[3].isdigit():
                self._json({"error": "not_found"}, 404)
                return
            with RUNS_LOCK:
                piezas = list(RUNS.get(partes[2], {}).get("piezas", []))
            indice = int(partes[3])
            doc_id = _texto(piezas[indice].get("doc_id")) if indice < len(piezas) else ""
            if not doc_id:
                self._json({"error": "document_not_found"}, 404)
                return
            try:
                self._json({"texto": _exportar_documento(doc_id)})
            except Exception:
                self._json({"error": "document_export_failed"}, 502)
            return
        self._json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - API de http.server
        ruta = urlparse(self.path).path
        try:
            datos = _leer_formulario(self)
        except (UnicodeDecodeError, ValueError):
            self._json({"error": "formulario_invalido"}, 400)
            return
        if ruta == "/generar":
            self._generar(datos)
            return
        if ruta == "/actividad":
            self._nueva_actividad(datos)
            return
        self._json({"error": "not_found"}, 404)

    def _generar(self, datos: dict[str, list[str]]) -> None:
        id_actividad = _texto((datos.get("id_actividad") or [""])[0]).strip()
        piezas = [p for p in PIEZAS if p in datos.get("piezas", [])]
        if not piezas:
            self._json({"error": "elegí al menos una pieza"}, 400)
            return
        try:
            ids = {a["id_actividad"] for a in _leer_actividades()}
        except Exception:
            self._json({"error": "no se pudo leer la planilla"}, 502)
            return
        if id_actividad not in ids:
            self._json({"error": "la actividad no está en la planilla"}, 400)
            return
        run_id = uuid.uuid4().hex[:10]
        with RUNS_LOCK:
            RUNS[run_id] = {
                "run_id": run_id,
                "id_actividad": id_actividad,
                "terminado": False,
                "piezas": [
                    {"pieza": p, "nombre": PIEZAS[p][1], "estado": "en_espera", "inicio": 0,
                     "segundos": 0, "detalle": "", "doc_id": "", "doc_name": "", "doc_url": ""}
                    for p in piezas
                ],
            }
        threading.Thread(target=_correr, args=(run_id, id_actividad, piezas), daemon=True).start()
        self._json({"run_id": run_id})

    def _nueva_actividad(self, datos: dict[str, list[str]]) -> None:
        fila = {campo: _texto((datos.get(campo) or [""])[0]).strip() for campo in COLUMNAS_ACTIVIDADES_V2}
        for campo in ("titulo", "descripcion", "fecha_inicio", "publico", "organiza", "contacto"):
            if not fila[campo]:
                self._json({"error": f"falta {campo}"}, 400)
                return
        fila["fuente"] = fila["fuente"] or FUENTE_CARGA_MANUAL
        fila["id_actividad"] = "ACT-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            _agregar_fila(fila)
        except Exception:
            self._json({"error": "no se pudo actualizar la planilla"}, 502)
            return
        self._json({"id_actividad": fila["id_actividad"]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consola visual de la demo del Agente 1.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    hilo = threading.Thread(target=_calentar_modelo, daemon=True)
    hilo.start()
    servidor = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Consola en http://{args.host}:{args.port}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
