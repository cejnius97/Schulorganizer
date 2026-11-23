"""Schulorganizer als Programm.

Startet einen kleinen lokalen Server (nur auf diesem PC erreichbar), zeigt die
Oberfläche in einem eigenen App-Fenster (ohne Browserleiste) und speichert alle
Daten in einer Datei:  %APPDATA%\\Schulorganizer\\daten.json
Beendet sich selbst, wenn das Fenster geschlossen wird.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}/"
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
INDEX = BASE / "index.html"
if not INDEX.exists():  # beim Testen direkt aus dem Projektordner
    INDEX = Path(__file__).parent.parent / "index.html"
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Schulorganizer"
DATA_FILE = DATA_DIR / "daten.json"
TIMEOUT = 120  # Sekunden ohne Lebenszeichen der Seite -> Programm beenden

last_ping = time.time()
seen_ping = False
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global last_ping, seen_ping
        if self.path.startswith("/api/ping"):
            last_ping, seen_ping = time.time(), True
            self._send(200, b"{}")
        elif self.path.startswith("/api/data"):
            body = DATA_FILE.read_bytes() if DATA_FILE.exists() else b"{}"
            self._send(200, body)
        elif self.path in ("/", "/index.html"):
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404)

    def do_POST(self):
        if not self.path.startswith("/api/data"):
            return self._send(404)
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            json.loads(raw.decode("utf-8"))  # nur gültiges JSON speichern
        except Exception:
            return self._send(400)
        with lock:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp = DATA_FILE.with_suffix(".tmp")
            tmp.write_bytes(raw)
            if DATA_FILE.exists():
                shutil.copyfile(DATA_FILE, DATA_FILE.with_suffix(".bak"))
            os.replace(tmp, DATA_FILE)
        self._send(200, b"{}")


def find_browser():
    candidates = []
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        root = os.environ.get(env)
        if root:
            candidates += [
                Path(root) / "Microsoft/Edge/Application/msedge.exe",
                Path(root) / "Google/Chrome/Application/chrome.exe",
            ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def open_window():
    browser = find_browser()
    if browser:
        subprocess.Popen([browser, f"--app={URL}", "--window-size=1280,860"])
    else:
        webbrowser.open(URL)


def already_running():
    try:
        urllib.request.urlopen(URL + "api/ping", timeout=1)
        return True
    except Exception:
        return False


def watchdog(server):
    start = time.time()
    while True:
        time.sleep(3)
        idle = time.time() - (last_ping if seen_ping else start)
        if idle > (TIMEOUT if seen_ping else 300):
            server.shutdown()
            return


def main():
    if already_running():  # Programm läuft schon -> nur Fenster öffnen
        open_window()
        return
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        open_window()
        return
    threading.Thread(target=watchdog, args=(server,), daemon=True).start()
    open_window()
    server.serve_forever()


if __name__ == "__main__":
    main()
