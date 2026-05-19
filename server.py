#!/usr/bin/env python3
"""
Bsale Farmacia - Servidor web para Railway
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get('PORT', 8080))

class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silenciar logs en produccion

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, access_token')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/proxy'):
            self.handle_proxy_get()
        else:
            self.serve_file()

    def do_POST(self):
        if self.path.startswith('/proxy'):
            self.handle_proxy_post()
        else:
            self.send_error(404)

    def handle_proxy_get(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_url = params.get('url', [''])[0]
        token = params.get('token', [''])[0]
        if not target_url:
            self.send_error(400, 'Falta url')
            return
        try:
            req = urllib.request.Request(target_url)
            if token:
                req.add_header('access_token', token)
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def handle_proxy_post(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_url = params.get('url', [''])[0]
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b'{}'
        if not target_url:
            self.send_error(400, 'Falta url')
            return
        try:
            req = urllib.request.Request(target_url, data=body, method='POST')
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            body_resp = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(body_resp)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def serve_file(self):
        path = self.path.split('?')[0].lstrip('/')
        if path == '' or path == '/':
            path = 'bsale_farmacia.html'
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, path)
        # Seguridad: no salir del directorio
        if not full_path.startswith(base_dir):
            self.send_error(403)
            return
        if not os.path.exists(full_path):
            self.send_error(404)
            return
        ext = path.rsplit('.', 1)[-1].lower()
        types = {
            'html': 'text/html; charset=utf-8',
            'js':   'application/javascript',
            'css':  'text/css',
            'ico':  'image/x-icon',
            'png':  'image/png'
        }
        ct = types.get(ext, 'application/octet-stream')
        with open(full_path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', len(data))
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)

socketserver.TCPServer.allow_reuse_address = True
print(f"Bsale Farmacia corriendo en puerto {PORT}")
with socketserver.TCPServer(('0.0.0.0', PORT), ProxyHandler) as httpd:
    httpd.serve_forever()
