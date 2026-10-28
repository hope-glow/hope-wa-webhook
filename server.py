from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request, os

MAESTRO = "https://maestro.adapta.one/webhooks/generic/48eb493143f04a53733d5162cd74a3464b6a8e48d525ed0fee159aadec196f40"
SECRET  = "7a8f691566c70e4776141fa51c9760a2a9be4cf5522bf3e2929966c41b37a5cd"
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "hope2026verify")

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if 'hub.challenge=' in self.path:
            ch = self.path.split('hub.challenge=')[1].split('&')[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(ch.encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hope webhook OK')
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        req = urllib.request.Request(MAESTRO + '?secret=' + SECRET, data=body,
              headers={'Content-Type': self.headers.get('Content-Type','application/json'),
                       'X-Webhook-Secret': SECRET})
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'EVENT_RECEIVED')
    def log_message(self, *a):
        pass

HTTPServer(('0.0.0.0', int(os.environ.get('PORT', 8080))), H).serve_forever()
