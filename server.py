#!/usr/bin/env python3
"""
Bsale Farmacia - Servidor completo con almacenamiento propio
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = '/tmp/bsale_data.json'

# ---- Helpers de datos ----
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {'am': [], 'precios': [], 'config': {'descuento_am': '10'}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, access_token')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, access_token')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # --- Proxy para Bsale ---
        if path == '/bsale':
            url = params.get('url', [''])[0]
            token = params.get('token', [''])[0]
            if not url:
                self.send_json({'error': 'Falta url'}, 400)
                return
            try:
                req = urllib.request.Request(url)
                req.add_header('access_token', token)
                req.add_header('User-Agent', 'Mozilla/5.0')
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                self.send_json(data)
            except urllib.error.HTTPError as e:
                self.send_json({'error': f'Bsale HTTP {e.code}'}, e.code)
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
            return

        # --- API datos locales ---
        if path == '/api/am':
            d = load_data()
            self.send_json({'items': d.get('am', [])})
            return

        if path == '/api/precios':
            d = load_data()
            self.send_json({'items': d.get('precios', [])})
            return

        if path == '/api/config':
            d = load_data()
            self.send_json({'config': d.get('config', {'descuento_am': '10'})})
            return

        # --- Servir archivos estáticos ---
        self.serve_file(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        d = load_data()

        if path == '/api/am/add':
            import time
            item = {
                'id': str(int(time.time() * 1000)),
                'name': body.get('name', ''),
                'rut': body.get('rut', ''),
                'phone': body.get('phone', ''),
                'fecha': body.get('fecha', '')
            }
            d['am'].append(item)
            save_data(d)
            self.send_json({'ok': True, 'id': item['id']})
            return

        if path == '/api/am/delete':
            id_ = str(body.get('id', ''))
            d['am'] = [x for x in d['am'] if str(x.get('id')) != id_]
            save_data(d)
            self.send_json({'ok': True})
            return

        if path == '/api/precios/save':
            d['precios'] = body.get('items', [])
            save_data(d)
            self.send_json({'ok': True, 'count': len(d['precios'])})
            return

        if path == '/api/config/save':
            d['config'].update(body)
            save_data(d)
            self.send_json({'ok': True})
            return

        self.send_json({'error': 'Ruta no encontrada'}, 404)

    def serve_file(self, path):
        path = path.lstrip('/')
        if not path:
            path = 'bsale_farmacia.html'
        base = os.path.dirname(os.path.abspath(__file__))
        full = os.path.join(base, path)
        if not full.startswith(base) or not os.path.exists(full):
            self.send_response(404)
            self.end_headers()
            return
        ext = path.rsplit('.', 1)[-1].lower()
        ct = {'html': 'text/html; charset=utf-8', 'js': 'application/javascript',
              'css': 'text/css'}.get(ext, 'application/octet-stream')
        with open(full, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

socketserver.TCPServer.allow_reuse_address = True
print(f"Bsale Farmacia corriendo en puerto {PORT}")
with socketserver.TCPServer(('0.0.0.0', PORT), Handler) as httpd:
    httpd.serve_forever()
