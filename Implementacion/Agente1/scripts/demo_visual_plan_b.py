#!/usr/bin/env python3
"""Consola visual de la demo: formulario, planilla, agente y borrador.

Se sirve desde el servidor y se abre por un túnel SSH. No publica nada: cada
corrida deja un documento con la marca `BORRADOR — NO PUBLICAR` y el estado
`PENDIENTE_VALIDACION`.

El formulario es una pieza de demostración. La actividad precargada sale del
corpus FIE INFORMA (`data/corpus-fie-informa-difusiones.csv`, fila
`FIE-DIF-08`); al enviar se agrega una fila nueva a la hoja v2 sintética y se
corre el mismo `workspace_e2e.py` que usa la demo headless.
"""

from __future__ import annotations

import argparse
import csv
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

ACTIVIDAD_DEMO = "FIE-DIF-08"
MODELO = "gemma4:e4b"
TIMEOUT_MODELO = 300.0
RUNS: dict[str, dict[str, object]] = {}
RUNS_LOCK = threading.Lock()
WARMUP = {"estado": "calentando"}
WARMUP_LOCK = threading.Lock()


def _texto(valor: object) -> str:
    return valor if isinstance(valor, str) else ""


def _actividad_demo() -> dict[str, str]:
    ruta = ROOT / "data" / "corpus-fie-informa-difusiones.csv"
    try:
        with ruta.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if fila.get("id_actividad") == ACTIVIDAD_DEMO:
                    return {campo: _texto(fila.get(campo)) for campo in COLUMNAS_ACTIVIDADES_V2}
    except OSError:
        pass
    return {campo: "" for campo in COLUMNAS_ACTIVIDADES_V2}


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


def _agregar_fila(fila: dict[str, str], config) -> None:
    pestaña = config.rango_a1.split("!", 1)[0]
    rango = quote(f"{pestaña}!A1:O1", safe="")
    objetivo = (
        f"/v4/spreadsheets/{config.spreadsheet_id}/values/{rango}:append"
        "?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    valores = [[fila[campo] for campo in COLUMNAS_ACTIVIDADES_V2]]
    estado, cuerpo = _pedir(
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
    partes = [ultimo.get("resultado"), ultimo.get("error")]
    return " · ".join(str(p) for p in partes if p) or "falló sin detalle"


def _correr(run_id: str, fila: dict[str, str]) -> None:
    run_dir = Path("/tmp/demo-visual-planb") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    comando = [
        sys.executable,
        str(ROOT / "scripts" / "workspace_e2e.py"),
        "--live",
        "--confirm-write-workspace",
        "--tipo",
        "gacetilla",
        "--id-solicitud",
        fila["id_actividad"],
        "--salida",
        str(run_dir),
        "--modelo",
        MODELO,
        "--timeout-modelo",
        f"{TIMEOUT_MODELO:g}",
    ]
    entorno = dict(os.environ)
    for clave in (
        "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY",
        "AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT",
        "AGENTE1_WORKSPACE_ACCESS_TOKEN",
    ):
        entorno.pop(clave, None)
    detalle = ""
    estado = "error"
    documento = None
    try:
        proceso = subprocess.run(
            comando,
            cwd=ROOT,
            env=entorno,
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
            if estado_cli:
                detalle = f"{estado_cli}: {detalle}"
    except subprocess.TimeoutExpired:
        estado = "error"
        detalle = "la corrida excedió el tiempo máximo"
    except Exception:
        estado = "error"
        detalle = "no se pudo ejecutar el agente"
    with RUNS_LOCK:
        RUNS[run_id].update(
            {
                "estado": estado,
                "paso": 4,
                "detalle": detalle,
                "doc_id": documento["id"] if documento else "",
                "doc_name": documento["name"] if documento else "",
                "doc_url": documento["url"] if documento else "",
            }
        )


def _calentar_modelo() -> None:
    datos = json.dumps(
        {
            "model": MODELO,
            "prompt": "Responde sólo OK.",
            "stream": False,
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


def _pagina(prefill: dict[str, str]) -> str:
    def valor(campo: str) -> str:
        return html.escape(prefill.get(campo, ""))

    def campo(nombre: str, etiqueta: str, *, tipo: str = "text", requerido: bool = False) -> str:
        req = " required" if requerido else ""
        return (
            f'<label>{etiqueta}<input type="{tipo}" name="{nombre}" '
            f'value="{valor(nombre)}"{req}></label>'
        )

    def area(nombre: str, etiqueta: str, *, filas: int = 3) -> str:
        return (
            f'<label>{etiqueta}<textarea name="{nombre}" rows="{filas}">'
            f"{valor(nombre)}</textarea></label>"
        )

    modalidad = valor("modalidad")
    opciones = "".join(
        f'<option value="{opcion}"{" selected" if modalidad == opcion else ""}>{opcion}</option>'
        for opcion in ("", "presencial", "virtual", "híbrida", "online y autogestionado")
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente 1 · Demo de gacetilla</title>
<style>
:root {{
  --tinta: #0b2545;
  --tinta-suave: #31445f;
  --oro: #c8a24a;
  --papel: #f4f1ea;
  --blanco: #ffffff;
  --linea: #d9d2c3;
  --ok: #1f6f4a;
  --alerta: #9a3b2f;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--papel); color: var(--tinta);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}}
header {{
  background: var(--tinta); color: var(--blanco);
  padding: 22px 34px; border-bottom: 4px solid var(--oro);
}}
header .kicker {{ color: var(--oro); font-size: 12px; letter-spacing: .16em; text-transform: uppercase; }}
header h1 {{ margin: 4px 0 2px; font-size: 30px; }}
header p {{ margin: 0; color: #d8deea; font-size: 14px; }}
main {{ max-width: 1320px; margin: 24px auto 48px; padding: 0 24px; display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, .9fr); gap: 22px; }}
.card {{ background: var(--blanco); border: 1px solid var(--linea); border-radius: 14px; padding: 22px; box-shadow: 0 10px 30px rgba(11,37,69,.06); }}
.card h2 {{ margin: 0 0 6px; font-size: 21px; }}
.card .sub {{ margin: 0 0 18px; color: var(--tinta-suave); font-size: 13px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px 14px; }}
.grid .ancho {{ grid-column: 1 / -1; }}
label {{ display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--tinta-suave); font-weight: 600; }}
input, textarea, select {{ border: 1px solid #cfd5df; border-radius: 8px; padding: 9px 10px; font: inherit; color: var(--tinta); background: #fbfbfd; }}
input:focus, textarea:focus, select:focus {{ outline: 2px solid #9fb7d8; border-color: #6f8fb8; }}
textarea {{ resize: vertical; }}
button {{ border: 0; border-radius: 9px; padding: 12px 18px; font: inherit; font-weight: 700; cursor: pointer; }}
.primario {{ background: var(--tinta); color: var(--blanco); width: 100%; margin-top: 16px; }}
.primario:disabled {{ opacity: .55; cursor: wait; }}
.secundario {{ background: #eef1f6; color: var(--tinta); }}
.paso {{ display: flex; align-items: center; gap: 9px; padding: 9px 10px; border-radius: 9px; color: #7b8798; font-size: 13px; }}
.paso .n {{ width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; background: #e7ebf1; color: #5b6b80; font-weight: 700; font-size: 12px; }}
.paso.activo {{ background: #f2f6fc; color: var(--tinta); }}
.paso.activo .n {{ background: var(--oro); color: var(--tinta); }}
.paso.hecho .n {{ background: var(--ok); color: var(--blanco); }}
.estado {{ margin-top: 12px; padding: 13px 14px; border-radius: 10px; background: #f7f8fb; border: 1px solid #e1e6ee; color: var(--tinta-suave); font-size: 14px; line-height: 1.5; min-height: 48px; }}
.estado.ok {{ background: #eef7f1; border-color: #b9dcc7; color: #14543a; }}
.estado.mal {{ background: #fbf0ee; border-color: #e7c2bb; color: #7f2f25; }}
.doc {{ margin-top: 14px; border-top: 1px solid var(--linea); padding-top: 14px; }}
.doc h3 {{ margin: 0 0 6px; font-size: 15px; }}
.doc .nombre {{ font-size: 13px; color: var(--tinta-suave); word-break: break-word; }}
.acciones {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
pre {{ margin: 14px 0 0; padding: 16px; background: #fbfaf6; border: 1px solid var(--linea); border-radius: 10px; white-space: pre-wrap; line-height: 1.55; font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: 12.5px; max-height: 520px; overflow: auto; }}
.nota {{ margin-top: 14px; font-size: 12px; color: #6b7687; }}
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 999px; background: #eef1f6; color: #4c5a6e; font-size: 11px; font-weight: 700; }}
.badge.ok {{ background: #e4f3ea; color: #1f6f4a; }}
.badge.mal {{ background: #f8e6e2; color: #9a3b2f; }}
@media (max-width: 980px) {{ main {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <div class="kicker">Agente 1 · Extensión Bot · Demo</div>
  <h1>Del formulario al borrador</h1>
  <p>Formulario de pedido, planilla, agente local y documento listo para validación humana.</p>
</header>
<main>
  <section class="card">
    <h2>Pedido de gacetilla</h2>
    <p class="sub">Actividad real del corpus FIE INFORMA. Podés editar los campos antes de enviar.</p>
    <form id="pedido" autocomplete="off">
      <div class="grid">
        <div class="ancho">{area("titulo", "Título", filas=2)}</div>
        <div class="ancho">{area("descripcion", "Descripción", filas=3)}</div>
        {campo("fecha_inicio", "Fecha de inicio", tipo="date", requerido=True)}
        {campo("fecha_fin", "Fecha de fin", tipo="date")}
        {campo("fecha_limite_inscripcion", "Límite de inscripción", tipo="date")}
        {campo("hora", "Hora")}
        <label>Modalidad<select name="modalidad">{opciones}</select></label>
        {campo("duracion_horas", "Duración en horas", tipo="number")}
        <div class="ancho">{area("publico", "Público destinatario", filas=2)}</div>
        {campo("organiza", "Organiza", requerido=True)}
        {campo("contacto", "Contacto", tipo="email", requerido=True)}
        <div class="ancho">{campo("fuente", "Fuente")}</div>
        {campo("enlace_inscripcion", "Enlace de inscripción")}
        {campo("lugar", "Lugar")}
      </div>
      <button class="primario" type="submit" id="enviar">Enviar pedido</button>
      <p class="nota">El identificador se genera al enviar. El agente no publica: deja un borrador con la marca <b>BORRADOR — NO PUBLICAR</b>.</p>
    </form>
  </section>

  <section class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
      <h2 style="margin:0;">Salida</h2>
      <span class="badge" id="modelo">Modelo: {_estado_modelo()}</span>
    </div>
    <div style="margin-top:14px;">
      <div class="paso" data-paso="1"><span class="n">1</span> Formulario enviado</div>
      <div class="paso" data-paso="2"><span class="n">2</span> Planilla actualizada</div>
      <div class="paso" data-paso="3"><span class="n">3</span> Agente generando</div>
      <div class="paso" data-paso="4"><span class="n">4</span> Borrador listo</div>
    </div>
    <div class="estado" id="estado">Completá el formulario y enviá el pedido. El agente lee la planilla, genera con <b>{MODELO}</b> y deja el borrador en Drive.</div>
    <div class="doc" id="doc" hidden>
      <h3>Documento</h3>
      <div class="nombre" id="doc-nombre"></div>
      <div class="acciones">
        <a id="doc-link" class="secundario" style="text-decoration:none;padding:10px 14px;border-radius:9px;font-size:13px;font-weight:700;" target="_blank" rel="noopener" hidden>Abrir en Drive</a>
        <button class="secundario" type="button" id="ver-texto">Ver gacetilla</button>
      </div>
      <pre id="texto" hidden></pre>
    </div>
    <p class="nota">Demo con datos reales del corpus y una planilla sintética. No se publica, comparte ni envía nada.</p>
  </section>
</main>
<script>
const form = document.getElementById('pedido');
const boton = document.getElementById('enviar');
const estado = document.getElementById('estado');
const doc = document.getElementById('doc');
const docNombre = document.getElementById('doc-nombre');
const docLink = document.getElementById('doc-link');
const texto = document.getElementById('texto');
const verTexto = document.getElementById('ver-texto');
const modeloBadge = document.getElementById('modelo');
const pasos = [...document.querySelectorAll('.paso')];
let runId = null;
let docId = null;

function marcarPaso(n) {{
  pasos.forEach((p) => {{
    const k = Number(p.dataset.paso);
    p.classList.toggle('hecho', k < n);
    p.classList.toggle('activo', k === n);
  }});
}}
function ponerEstado(html, clase) {{
  estado.innerHTML = html;
  estado.className = 'estado' + (clase ? ' ' + clase : '');
}}
async function salud() {{
  try {{
    const r = await fetch('/health');
    const d = await r.json();
    modeloBadge.textContent = 'Modelo: ' + d.modelo + ' · ' + d.warmup;
    modeloBadge.className = 'badge' + (d.warmup === 'listo' ? ' ok' : '');
  }} catch (e) {{}}
}}
async function esperar(id) {{
  let segundos = 0;
  while (true) {{
    const r = await fetch('/estado/' + id);
    const d = await r.json();
    if (d.estado === 'generando') {{
      marcarPaso(3);
      ponerEstado('El agente está generando el borrador con <b>{MODELO}</b>. Tiempo: ' + segundos + ' s.');
    }} else if (d.estado === 'listo') {{
      marcarPaso(4);
      ponerEstado('Borrador listo para validación humana. No se publicó.', 'ok');
      doc.hidden = false;
      docNombre.textContent = d.doc_name || 'Documento sin nombre';
      docId = d.doc_id || null;
      if (d.doc_url) {{
        docLink.href = d.doc_url;
        docLink.hidden = false;
      }}
      if (d.detalle) {{
        ponerEstado('Borrador listo. ' + d.detalle + '. No se publicó.', 'ok');
      }}
      return;
    }} else {{
      marcarPaso(d.estado === 'rechazado' ? 3 : 4);
      ponerEstado('No se generó un borrador publicable. ' + (d.detalle || 'El gate rechazó la salida.') + ' No se publicó.', 'mal');
      return;
    }}
    await new Promise((ok) => setTimeout(ok, 1500));
    segundos += 2;
  }}
}}
form.addEventListener('submit', async (evento) => {{
  evento.preventDefault();
  boton.disabled = true;
  doc.hidden = true;
  texto.hidden = true;
  docLink.hidden = true;
  marcarPaso(1);
  ponerEstado('Enviando el pedido...');
  try {{
    const respuesta = await fetch('/generar', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: new URLSearchParams(new FormData(form)),
    }});
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error || 'No se pudo enviar el pedido.');
    runId = datos.run_id;
    marcarPaso(2);
    ponerEstado('Planilla actualizada con la solicitud <b>' + datos.id_actividad + '</b>. El agente arranca.');
    await esperar(runId);
  }} catch (error) {{
    ponerEstado('Error: ' + error.message, 'mal');
    marcarPaso(1);
  }} finally {{
    boton.disabled = false;
  }}
}});
verTexto.addEventListener('click', async () => {{
  if (!runId) return;
  verTexto.disabled = true;
  try {{
    const r = await fetch('/documento/' + runId);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'No se pudo leer el documento.');
    texto.textContent = d.texto;
    texto.hidden = false;
  }} catch (error) {{
    ponerEstado('No se pudo leer el texto: ' + error.message, 'mal');
  }} finally {{
    verTexto.disabled = false;
  }}
}});
salud();
setInterval(salud, 5000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "Agente1Demo/1.0"

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
            self._html(_pagina(_actividad_demo()))
            return
        if ruta == "/health":
            self._json({"modelo": MODELO, "warmup": _estado_modelo()})
            return
        if ruta.startswith("/estado/"):
            run_id = ruta.split("/", 2)[2]
            with RUNS_LOCK:
                datos = dict(RUNS.get(run_id, {}))
            if not datos:
                self._json({"error": "run_not_found"}, 404)
                return
            self._json(datos)
            return
        if ruta.startswith("/documento/"):
            run_id = ruta.split("/", 2)[2]
            with RUNS_LOCK:
                datos = dict(RUNS.get(run_id, {}))
            doc_id = _texto(datos.get("doc_id"))
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
        if urlparse(self.path).path != "/generar":
            self._json({"error": "not_found"}, 404)
            return
        largo = int(self.headers.get("Content-Length", "0"))
        try:
            datos = parse_qs(self.rfile.read(largo).decode("utf-8"), keep_blank_values=True)
        except (UnicodeDecodeError, ValueError):
            self._json({"error": "formulario_invalido"}, 400)
            return
        fila = {campo: _texto((datos.get(campo) or [""])[0]).strip() for campo in COLUMNAS_ACTIVIDADES_V2}
        for campo in ("titulo", "descripcion", "fecha_inicio", "publico", "organiza", "contacto"):
            if not fila[campo]:
                self._json({"error": f"falta_{campo}"}, 400)
                return
        fila["id_actividad"] = "DEMO-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        try:
            config = cargar_configuracion_workspace()
            _agregar_fila(fila, config)
        except Exception:
            self._json({"error": "no_se_pudo_actualizar_la_planilla"}, 502)
            return
        run_id = uuid.uuid4().hex[:10]
        with RUNS_LOCK:
            RUNS[run_id] = {
                "run_id": run_id,
                "estado": "generando",
                "paso": 3,
                "id_actividad": fila["id_actividad"],
                "detalle": "",
                "doc_id": "",
                "doc_name": "",
                "doc_url": "",
            }
        threading.Thread(target=_correr, args=(run_id, fila), daemon=True).start()
        self._json({"run_id": run_id, "id_actividad": fila["id_actividad"]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consola visual del Plan B OAuth.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    hilo = threading.Thread(target=_calentar_modelo, daemon=True)
    hilo.start()
    servidor = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Demo visual en http://{args.host}:{args.port}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
