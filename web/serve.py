"""Статика web/ без кэша: правки в app.js/css видны сразу после обновления страницы."""

from __future__ import annotations

import http.server
import socket
import socketserver
import sys
from functools import partial
from pathlib import Path

PORT = 8765
ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 - имя параметра задано базовым классом
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def lan_ip() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        probe.close()
        return address
    except OSError:
        return "—"


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    handler = partial(Handler, directory=str(ROOT))
    with Server(("", PORT), handler) as httpd:
        print(f"ActPilot web: http://127.0.0.1:{PORT}")
        print(f"с телефона:  http://{lan_ip()}:{PORT}")
        print("Ctrl+C — остановить")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nостановлено")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
