#!/usr/bin/env python3
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
        pass

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

    def fetch_with_redirects(self, url, token=None, data=None, method='GET', max_redirects=10):
        """Sigue redirecciones manualmente incluyendo las de Google"""
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        
        for _ in range(max_redirects):
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json, text/plain, */*')
            if token:
                req.add_header('access_token', token)
            if data:
                req.add_header('Content-Type', 'application/json')
            
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read(), resp.status
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    url = e.headers.get('Location', url)
                    if method in ('POST',) and e.code in (301, 302, 303):
                        method = 'GET'
                        data = None
                    continue
                raise
        raise Exception('Demasiadas redirecciones')

    def handle_proxy_get(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_url = params.get('url', [''])[0]
        token = params.get('token', [''])[0]

        if not target_url:
            self.send_error(400, 'Falta url')
            return

        try:
            data, status = self.fetch_with_redirects(target_url, token=token or None)
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
            data, status = self.fetch_with_redirects(target_url, data=body, method='POST')
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
        if not full_path.startswith(base_dir):
            self.send_error(403)
            return
        if not os.path.exists(full_path):
            self.send_error(404)
            return
        ext = path.rsplit('.', 1)[-1].lower()
        types = {'html': 'text/html; charset=utf-8', 'js': 'application/javascript',
                 'css': 'text/css', 'ico': 'image/x-icon'}
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
