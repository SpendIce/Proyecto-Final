#!/usr/bin/env python3
"""Prototipo descartable de interfaz local para la prueba guiada HU-013.

Pregunta de diseño: ¿puede JM cargar pedidos en una conversación guiada,
ver qué respondió el agente y dejar una señal de comprensión sin editar CSV?
Los pedidos viven sólo en memoria durante la sesión; el núcleo conserva su
auditoría habitual por hash y los borradores en un directorio temporal.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agente1.fuentes import CsvFuenteSolicitudes
from agente1.interpretacion import (
    IdentidadSolicitante,
    RegistroPendientesMemoria,
    interpretar_solicitud,
)
from agente1.ollama import OllamaGenerator
from agente1.procesamiento import PATRON_PROSA_SIN_DATOS

ROOT = Path(__file__).resolve().parents[1]
HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prueba guiada · Agente 1</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#18251f;background:#f3f5f1}*{box-sizing:border-box}body{margin:0}header{background:#173f35;color:white;padding:26px max(24px,calc((100% - 980px)/2))}header small{opacity:.75}main{max-width:980px;margin:28px auto;padding:0 20px}.layout{display:grid;grid-template-columns:280px 1fr;gap:22px}.panel,.turn{background:white;border:1px solid #dce4dd;border-radius:14px;padding:20px}.panel h2,.turn h2{font-size:18px;margin:0 0 12px}.tasks{padding-left:20px}.tasks li{margin:10px 0}.muted{color:#5b6b62;font-size:14px}.badge{display:inline-block;background:#e7f2eb;color:#245541;border-radius:999px;padding:4px 10px;font-size:13px}.badge.fake{background:#fff2d8;color:#734b00}label{display:block;font-weight:650;margin:12px 0 5px}textarea,select,input{font:inherit;width:100%;padding:11px;border:1px solid #bdc9bf;border-radius:8px;background:#fff}textarea{min-height:120px;resize:vertical}button{font:inherit;border:0;border-radius:8px;padding:10px 15px;cursor:pointer;background:#1d5c49;color:#fff;font-weight:650}button.secondary{background:#e9efea;color:#244537}button:disabled{opacity:.55;cursor:wait}.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.turn{margin-top:18px}.answer{white-space:pre-wrap;background:#f4f7f4;border-radius:8px;padding:12px;margin:12px 0}.draft{white-space:pre-wrap;overflow:auto;max-height:330px;background:#faf8ee;border:1px solid #eee5c6;padding:14px;border-radius:8px;font:14px/1.5 ui-monospace,monospace}.feedback{border-top:1px solid #e1e7e2;margin-top:16px;padding-top:12px}.feedback label{display:inline;font-weight:500;margin-right:16px}.turn-num{color:#5b6b62;font-size:13px}.foot{margin-top:22px}.hidden{display:none}.turn{scroll-margin-top:16px}.turn.latest{border:2px solid #1d5c49;box-shadow:0 2px 12px rgba(23,63,53,.14)}details.turn>summary{cursor:pointer;list-style:none}details.turn>summary::-webkit-details-marker{display:none}details.turn>summary::before{content:'\25b8\20';color:#5b6b62}details.turn[open]>summary::before{content:'\25be\20'}@media(max-width:720px){.layout{grid-template-columns:1fr}header{padding:22px}}
</style></head>
<body><header><small>SECRETARÍA DE EXTENSIÓN UNIVERSITARIA · PRUEBA GUIADA</small><h1 style="margin:4px 0">Hablemos con el agente</h1><div>Pedí una pieza con tus palabras. Después revisamos juntos qué entendió.</div></header>
<main><div class="layout"><aside class="panel"><h2>¿Qué podés probar?</h2><ol class="tasks"><li>Pedir una gacetilla mencionando una actividad.</li><li>Pedir un post e indicar Instagram o LinkedIn.</li><li>Responder una pregunta si el agente no sabe cuál actividad elegís.</li><li>Probar un pedido que no corresponda a sus tareas.</li></ol><p class="muted">Son ideas, no frases para copiar. Escribí como lo pedirías normalmente.</p><h2 style="margin-top:20px">Actividades ficticias</h2><ul class="muted"><li>Taller sintético de vinculación</li><li>Jornada sintética</li><li>Seminario sintético remoto</li></ul><div id="mode" class="badge"></div><p class="muted">Usamos actividades sintéticas. No se publica ni se envía nada.</p></aside>
<section><div class="panel"><h2>Tu pedido</h2><div class="muted">Podés pedir una gacetilla o un post. Para el post, mencioná el canal. Si algo no queda claro, el agente puede preguntarte.</div><label for="pedido">¿Qué necesitás?</label><textarea id="pedido" placeholder="Escribí acá tu pedido…"></textarea><div class="row"><button id="send">Enviar pedido</button></div><div class="muted foot">La identidad y el rol son datos de prueba; esta pantalla no verifica quién la usa.</div></div>
<div id="turns"></div><div class="panel foot"><h2>Registro de la sesión</h2><div class="muted">Al terminar cada intercambio, quien conduce anota si la respuesta se entendió y qué haría la persona después. El registro no incluye el texto del pedido.</div><button id="download" class="secondary" style="margin-top:12px">Descargar resumen sin pedidos</button></div></section></div></main>
<script>
const $=s=>document.querySelector(s), turns=[];let busy=false;
async function submit(){if(busy)return;const text=$('#pedido').value.trim();if(!text)return;busy=true;$('#send').disabled=true;$('#send').textContent='Procesando…';try{const r=await fetch('/api/pedido',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:text})});const d=await r.json();if(!r.ok)throw Error(d.error||'No se pudo procesar');turns.push({...d,feedback:null});render();$('#pedido').value='';}catch(e){alert(e.message)}finally{busy=false;$('#send').disabled=false;$('#send').textContent='Enviar pedido';}}
function render(){const root=$('#turns');root.innerHTML='';turns.forEach((t,i)=>{const last=i===turns.length-1;const el=document.createElement(last?'article':'details');el.className='turn'+(last?' latest':'');const title=document.createElement(last?'div':'summary');title.className='turn-num';const pista=(t.resumen||t.error||'').slice(0,70);title.textContent=`RESPUESTA ${i+1} · ${t.estado}${last?' · nueva':pista?' — '+pista:''}`;el.append(title);const body=document.createElement('div');const ans=document.createElement('div');ans.className='answer';ans.textContent=t.resumen||t.error||'El agente no devolvió un detalle.';body.append(ans);if(t.candidatas?.length){const ul=document.createElement('ol');t.candidatas.forEach(c=>{const li=document.createElement('li');li.textContent=`${c.titulo} (${c.fecha||'fecha no informada'})`;ul.append(li)});body.append(ul)}if(t.borrador){const b=document.createElement('details');const s=document.createElement('summary');s.textContent='Ver borrador generado';const pre=document.createElement('pre');pre.className='draft';pre.textContent=t.borrador;b.append(s,pre);body.append(b)}const f=document.createElement('div');f.className='feedback';f.innerHTML='<strong>Antes de seguir: ¿se entendió esta respuesta?</strong><div class="row"><label><input type="radio" name="understood-'+i+'" value="si"> Sí</label><label><input type="radio" name="understood-'+i+'" value="no"> No / con dudas</label></div><label for="next-'+i+'">¿Qué harías ahora?</label><input id="next-'+i+'" placeholder="Anotá la respuesta en forma resumida, sin copiar el pedido">';f.querySelectorAll('input[type=radio]').forEach(x=>{if(t.feedback?.entendida===x.value)x.checked=true;x.addEventListener('change',()=>{t.feedback={entendida:f.querySelector('input[type=radio]:checked')?.value||null,siguiente:$('#next-'+i).value};})});const nxt=f.querySelector('input:not([type=radio])');nxt.value=t.feedback?.siguiente||'';nxt.addEventListener('input',e=>{t.feedback={entendida:f.querySelector('input[type=radio]:checked')?.value||null,siguiente:e.target.value};});body.append(f);el.append(body);root.append(el)});if(turns.length)root.lastElementChild.scrollIntoView({behavior:'smooth',block:'start'});$('#mode').textContent=window.MODE;$('#mode').classList.toggle('fake',window.MODE.startsWith('SIMULADO'));}
$('#send').onclick=submit;$('#pedido').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();submit()}});$('#download').onclick=()=>{const rows=turns.map((t,i)=>({interaccion:i+1,estado:t.estado,intencion:t.intencion,entendida:t.feedback?.entendida||'sin_respuesta',siguiente_parafraseado:t.feedback?.siguiente||''}));const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({prototipo:true,modo:window.MODE,interacciones:rows},null,2)],{type:'application/json'}));a.download='resumen-sesion-hu013.json';a.click();URL.revokeObjectURL(a.href)};render();
</script></body></html>'''


class GeneradorDemo:
    """Salidas deterministas válidas para ensayar la interfaz sin Ollama.

    La gacetilla se arma desde el bloque DATOS FUENTE del propio prompt: el
    gate de hechos compara título/fecha/organiza/lugar/contacto contra la
    fila, así que un texto fijo sólo pasaría para SYN-001.
    """

    modelo = "demo-determinista"
    num_predict = None

    def __init__(self) -> None:
        # La ficha golden es la salida del modelo que el pipeline valida; el
        # golden `SYN-001.md` es el artefacto durable (el mail renderizado).
        self.gacetilla = (
            ROOT / "golden" / "SYN-001.ficha.md"
        ).read_text(encoding="utf-8").strip()

    def generar(self, prompt: str) -> str:
        if '"gancho"' in prompt or "gancho" in prompt.lower():
            canal = "linkedin" if "linkedin" in prompt.lower() else "instagram"
            if canal == "linkedin":
                return json.dumps({"gancho":"Nueva propuesta de extensión abierta a la comunidad.","prosa":"Te invitamos a una experiencia de intercambio junto a docentes, estudiantes y graduados.","cta":"Toda la información está en el enlace de esta publicación.","hashtags":["#FIE","#UNDEF","#Ingenieria"]},ensure_ascii=False)
            return json.dumps({"gancho":"¡La FIE te espera con una nueva propuesta!","prosa":"Te esperamos para compartir una propuesta que acerca la ingeniería a tu futuro. ¡Si es ingeniería, la FIE te espera!","cta":"La FIE te espera. El enlace está en nuestro perfil.","hashtags":["#FIE","#UNDEF","#inscripciones"]},ensure_ascii=False)
        datos = self._datos_fuente(prompt)
        if not datos:
            return self.gacetilla
        lineas = [f"Fecha: {datos.get('fecha_inicio', '')}", f"Organiza: {datos.get('organiza', '')}"]
        if datos.get("lugar"):
            lineas.append(f"Lugar: {datos['lugar']}")
        # La prosa no puede llevar datos concretos (números, correos, enlaces,
        # montos): esos los pone el renderer desde la fila. La descripción se
        # usa como bajada cuando no trae datos concretos y entra en el tope.
        bajada = datos.get("descripcion", "")
        if len(bajada.split()) > 40 or PATRON_PROSA_SIN_DATOS.search(bajada):
            bajada = ""
        if not bajada:
            bajada = "Nueva propuesta de extensión universitaria."
        if datos.get("organiza") and datos.get("publico"):
            cuerpo = (
                f"{datos['organiza']} la propone como una instancia abierta "
                "para acercarse, participar y hacer consultas sobre la "
                "oferta de extensión de la facultad."
            )
        else:
            cuerpo = f"Propuesta organizada por {datos.get('organiza', '')}."
        if len(cuerpo.split()) > 120 or PATRON_PROSA_SIN_DATOS.search(cuerpo):
            cuerpo = "Propuesta de extensión abierta a la comunidad."
        return "\n\n".join([
            "## TÍTULO\n" + datos.get("titulo", ""),
            "## DATOS DE LA ACTIVIDAD\n" + "\n".join(lineas),
            "## CONTACTO\n" + datos.get("contacto", ""),
            "## BAJADA\n" + bajada,
            "## CUERPO\n" + cuerpo,
        ])

    @staticmethod
    def _datos_fuente(prompt: str) -> dict[str, str]:
        if "--- DATOS FUENTE ---" not in prompt:
            return {}
        bloque = prompt.split("--- DATOS FUENTE ---")[-1].split("--- FIN DATOS FUENTE ---")[0]
        datos = {}
        for linea in bloque.strip().splitlines():
            campo, _, valor = linea.partition(":")
            if campo.strip():
                datos[campo.strip()] = valor.strip()
        return datos


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            contenido = HTML.replace("window.MODE", json.dumps(self.server.modo))
            data = contenido.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/pedido":
            self.send_error(404); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        texto = body.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            self._json(400, {"error":"Escribí un pedido para continuar."}); return
        resultado = interpretar_solicitud(texto=texto,solicitante=self.server.identidad,fuente=self.server.fuente,directorio_salida=self.server.salida,generator=self.server.generator,registro_pendientes=self.server.pendientes,interprete=self.server.interprete)
        borrador = None
        if resultado.borrador_path and resultado.borrador_path.exists():
            borrador = resultado.borrador_path.read_text(encoding="utf-8")
        self._json(200,{"estado":resultado.estado,"intencion":resultado.intencion,"resumen":resultado.resumen,"error":resultado.error,"candidatas":[{"titulo":c.titulo,"fecha":c.fecha_inicio} for c in resultado.candidatas],"borrador":borrador})

    def _json(self, estado: int, objeto: dict) -> None:
        data = json.dumps(objeto,ensure_ascii=False).encode(); self.send_response(estado); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, *_: object) -> None:
        pass


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modo",choices=("simulado","ollama"),default="simulado",help="simulado es determinista; ollama usa el modelo local indicado.")
    parser.add_argument("--modelo",default="llama3.1:8b")
    parser.add_argument("--puerto",type=int,default=8765)
    args=parser.parse_args()
    salida=Path(tempfile.mkdtemp(prefix="prototipo-hu013-"))
    if args.modo=="ollama":
        generator=OllamaGenerator(modelo=args.modelo)
        interprete=generator
        modo=f"Ollama local · {args.modelo}"
    else:
        generator=GeneradorDemo()
        interprete=None
        modo="SIMULADO · resultados deterministas, sin LLM"
    server=ThreadingHTTPServer(("127.0.0.1",args.puerto),Handler)
    server.modo=modo
    server.identidad=IdentidadSolicitante(identificador="juan-manuel",rol="coordinador_seu")
    server.fuente=CsvFuenteSolicitudes(ROOT/"data"/"actividades_sinteticas.csv")
    server.salida=salida
    server.generator=generator
    server.interprete=interprete
    server.pendientes=RegistroPendientesMemoria()
    print(f"Prototipo HU-013: http://127.0.0.1:{args.puerto} ({modo})")
    print(f"Borradores y auditoría local: {salida}")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nSesión finalizada.")
    finally: server.server_close()


if __name__=="__main__":
    main()
