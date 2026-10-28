from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request, os, json, time

MAESTRO = "https://maestro.adapta.one/webhooks/generic/48eb493143f04a53733d5162cd74a3464b6a8e48d525ed0fee159aadec196f40"
SECRET  = "7a8f691566c70e4776141fa51c9760a2a9be4cf5522bf3e2929966c41b37a5cd"
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "hope2026verify")

# Dedup: Meta reenvia o mesmo evento (mesmo wamid) ate 3x. Guardar ids vistos.
SEEN = {}
SEEN_MAX = 5000
SEEN_TTL = 3600  # 1h

def is_dup(ids):
    now = time.time()
    # limpeza simples
    if len(SEEN) > SEEN_MAX:
        for k in list(SEEN.keys()):
            if now - SEEN[k] > SEEN_TTL:
                del SEEN[k]
    key = "|".join(ids) if ids else None
    if not key:
        return False
    if key in SEEN:
        return True
    SEEN[key] = now
    return False

def extract_ids(payload):
    """Extrai ids estaveis do payload (wamid de messages e ids de statuses)."""
    ids = []
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                for m in val.get("messages", []):
                    if m.get("id"):
                        ids.append("msg:" + m["id"])
                for s in val.get("statuses", []):
                    if s.get("id"):
                        ids.append("st:%s:%s" % (s["id"], s.get("status", "")))
    except Exception:
        pass
    return ids

def forward(body_bytes):
    """Repassa pro Maestro com retry (3 tentativas)."""
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                MAESTRO + "?secret=" + SECRET,
                data=body_bytes,
                headers={"Content-Type": "application/json",
                         "X-Webhook-Secret": SECRET})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            last = e
            time.sleep(2)
    return False

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
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}
        ids = extract_ids(payload)
        if ids and is_dup(ids):
            # ja repassado antes: responde 200 sem repassar de novo
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'DUPLICATE')
            return
        ok = forward(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'EVENT_RECEIVED')

    def log_message(self, *a):
        pass

HTTPServer(('0.0.0.0', int(os.environ.get('PORT', 8080))), H).serve_forever()
