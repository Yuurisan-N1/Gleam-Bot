import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading

from gleam_mcp import browser as br
from gleam_mcp import cookies as ck

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

PORT = 8099
SECRET = "SECRET123"


class Server(socketserver.TCPServer):
    allow_reuse_address = True


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        raw = self.headers.get("Cookie") or ""
        jar = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                jar[k.strip()] = v.strip()
        if self.path.startswith("/login"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>LOGIN PAGE</h1>")
            return
        if jar.get("sid") == SECRET:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>MEMBER AREA</h1><p>Santoso Permana</p>")
            return
        self.send_response(302)
        self.send_header("Location", "/login")
        self.end_headers()


srv = Server(("127.0.0.1", 0), Handler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

out = {"engine": br.engine(), "server": "http://127.0.0.1:%d/" % PORT}

with tempfile.TemporaryDirectory() as tmp:
    good = os.path.join(tmp, "good.json")
    bad = os.path.join(tmp, "bad.json")
    with open(good, "w") as fh:
        fh.write(json.dumps([{"name": "sid", "value": SECRET}]))
    with open(bad, "w") as fh:
        fh.write(json.dumps([{"name": "sid", "value": "SALAH"}]))

    os.environ["COOKIE_DIR"] = tmp
    os.environ["CUSTOM_COOKIE_URL"] = "http://127.0.0.1:%d/" % PORT
    os.environ["CUSTOM_COOKIE_DOMAINS"] = "127.0.0.1"
    os.environ["CUSTOM_COOKIE_SESSION"] = "sid"
    os.environ["BROWSER_PROXY"] = ""
    os.environ["GLEAM_PROXY_FILE"] = "/tmp/does-not-exist.txt"
    os.environ.pop("CUSTOM_COOKIE_FILE", None)

    os.environ["CUSTOM_COOKIE_FILE"] = good
    pos = br.connect("custom", screenshot="/tmp/cookie_e2e_ok.png")

    os.environ["CUSTOM_COOKIE_FILE"] = bad
    neg = br.connect("custom")

    os.environ.pop("CUSTOM_COOKIE_FILE", None)
    os.environ["COOKIE_DIR"] = "/tmp/empty-cookie"
    none = br.connect("x")

out["kontrol_positif"] = {
    "ok": pos.get("ok"), "logged_in": pos.get("logged_in"),
    "final_url": pos.get("final_url"), "title": pos.get("title"),
    "injected": pos.get("injected"), "session_cookie": pos.get("session_cookie"),
    "elapsed": pos.get("elapsed"), "error": pos.get("error"),
}
out["kontrol_negatif"] = {
    "ok": neg.get("ok"), "logged_in": neg.get("logged_in"),
    "final_url": neg.get("final_url"), "redirected_to_login": neg.get("redirected_to_login"),
    "error": neg.get("error"),
}
out["tanpa_cookie_x"] = {"ok": none.get("ok"), "reason": none.get("reason"),
                         "error": none.get("error")}

srv.shutdown()
print(json.dumps(out, ensure_ascii=False, indent=2))
