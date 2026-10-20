# -*- coding: utf-8 -*-
"""
Servidor local del panel XKT Savage.

Sirve el sitio (como python -m http.server) y ademas permite que el panel
admin.html GUARDE config.json en disco de forma persistente:

  GET  /api/ping          -> confirma que el guardado local esta disponible
  POST /api/save-config   -> guarda el body JSON en config.json (con backup)

Uso:  python server.py [puerto]     (por defecto 8000)
"""
import json
import os
import shutil
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
BACKUP_PATH = os.path.join(ROOT, "config.backup.json")


class XKTHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # --- utilidades ---
    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    # --- API ---
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":
            body = json.dumps({"ok": True, "save": True}).encode("utf-8")
            return self._send(200, body)
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/save-config":
            return self._send(404, b'{"ok":false,"error":"endpoint desconocido"}')
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0:
                return self._send(400, b'{"ok":false,"error":"body vacio"}')
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))  # valida que sea JSON
            pretty = json.dumps(data, ensure_ascii=False, indent=2)

            # backup del anterior (si existe y era distinto)
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        old = f.read()
                    if old.strip() != pretty.strip():
                        shutil.copyfile(CONFIG_PATH, BACKUP_PATH)
                except Exception:
                    pass

            # escritura atomica: temp -> replace
            tmp = CONFIG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(pretty)
            os.replace(tmp, CONFIG_PATH)
            return self._send(200, json.dumps({"ok": True, "saved": time.strftime("%H:%M:%S")}).encode("utf-8"))
        except ValueError:
            return self._send(400, b'{"ok":false,"error":"JSON invalido"}')
        except PermissionError:
            return self._send(500, b'{"ok":false,"error":"sin permiso de escritura (cierra el archivo config.json si esta abierto)"}')
        except Exception as e:
            msg = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
            return self._send(500, msg)

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s\n" % (fmt % args))
        sys.stdout.flush()


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    httpd = ThreadingHTTPServer(("0.0.0.0", port), XKTHandler)
    print()
    print("  ============================================")
    print("   PANEL XKT SAVAGE (local con guardado)")
    print("   Los cambios SI se guardan en config.json")
    print("   NO cerrar esta ventana mientras editas.")
    print("  ============================================")
    print()
    print("  Servidor: http://localhost:%d  ->  Panel: http://localhost:%d/admin.html" % (port, port))
    print("  Panel abierto en el navegador. Usa Ctrl+C para salir.")
    print()
    try:
        webbrowser.open("http://localhost:%d/admin.html" % port)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor detenido.\n")


if __name__ == "__main__":
    main()
