"""Static file HTTP server for dashboard iframes.

Serves the dashboard/static/ directory over plain HTTP so Streamlit's
st.iframe() can point to a proper ``http://`` origin (not a data: URI),
enabling WebSocket connections from within the iframe.

Uses Python's built-in ``http.server`` — zero additional dependencies.
Runs in a daemon thread alongside the WebSocket server.
"""

import http.server
import socket
import threading
from pathlib import Path
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parents[2] / "dashboard" / "static"


class _DashboardHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Serves files from dashboard/static/ with CORS headers."""

    # Suppress default logging (we use our own logger)
    def log_message(self, format, *args):
        logger.debug(f"HTTP: {args[0]} {args[1]} {args[2]}")

    def do_GET(self):
        # Strip query strings
        path = self.path.split("?")[0].split("#")[0]

        # Normalize path: remove leading /
        if path.startswith("/"):
            path = path[1:]

        # Security: prevent directory traversal
        try:
            filepath = (_STATIC_DIR / path).resolve()
            filepath.relative_to(_STATIC_DIR.resolve())
        except (ValueError, RuntimeError):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        # Only serve allowed extensions
        if not filepath.is_file() or filepath.suffix not in (".html", ".css", ".js", ".png", ".svg", ".ico"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        content_type_map = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        content_type = content_type_map.get(filepath.suffix, "application/octet-stream")

        try:
            body = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Internal Server Error")


class StaticFileServer:
    """Simple HTTP server for dashboard static files.

    Starts on a dedicated port in a daemon thread.

    Usage:
        server = StaticFileServer(port=8767)
        server.start()
        # ... later ...
        server.stop()
    """

    def __init__(self, port: int = 8767):
        self.port = port
        self._server: Optional[http.server.HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the HTTP server in a daemon thread."""
        if self._running:
            return

        # Find an available port (iterate up if port is taken)
        actual_port = self._find_available_port(self.port)
        if actual_port != self.port:
            logger.info(f"Static server port {self.port} in use, using {actual_port} instead")
            self.port = actual_port

        try:
            self._server = http.server.HTTPServer(
                ("0.0.0.0", self.port),
                _DashboardHTTPRequestHandler,
            )
            self._server.timeout = 1.0  # Allow clean shutdown via KeyboardInterrupt
            self._running = True
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="static-http-server",
            )
            self._thread.start()
            logger.info(f"Static HTTP server ready on http://localhost:{self.port}")
        except OSError as e:
            logger.error(f"Failed to start static HTTP server on port {self.port}: {e}")

    def stop(self) -> None:
        """Stop the HTTP server."""
        self._running = False
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        self._thread = None

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> int:
        """Find an available TCP port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                    return port
                except OSError:
                    continue
        return start_port  # fallback, will likely fail on start
