"""Loopback-only HTTP server. Offline computations and static assets only."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, urlsplit

from .engine import compare, policy_from_dict, replay
from .fixtures import SCENARIOS, START, fixture, iso
from .schema import InputError, keys, load_json, timestamp, validate_dataset

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY = 2 * 1024 * 1024


def portless_origin():
    """Accept one explicit local proxy origin, never a wildcard request host."""
    value = os.environ.get("PORTLESS_URL")
    if value is None:
        return None
    parsed = urlsplit(value)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme not in ("http", "https")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.geturl() != value
        or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+localhost", hostname)
        or any(len(label) > 63 for label in hostname.split("."))
        or len(hostname) > 253
        or (parsed.port is not None and not 1 <= parsed.port <= 65535)
    ):
        raise ValueError("PORTLESS_URL must be an exact HTTP(S) .localhost origin without a path")
    return value


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send(self, code, data, content_type="application/json"):
        body = json.dumps(data, allow_nan=False).encode() if content_type == "application/json" else data
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        public_origin = getattr(self.server, "public_origin", None)
        if public_origin:
            expected.add(urlsplit(public_origin).netloc)
        return self.headers.get("Host") in expected

    def do_GET(self):
        if not self.valid_host():
            self.send(403, {"error": "loopback host required"})
            return
        path = urlparse(self.path).path
        if path == "/api/scenarios":
            self.send(200, {"scenarios": [{"id": key, "label": value[0]} for key, value in SCENARIOS.items()], "paper_only": True})
        elif path.startswith("/api/fixture/"):
            name = path.removeprefix("/api/fixture/")
            if name not in SCENARIOS:
                self.send(404, {"error": "unknown scenario"})
            else:
                self.send(200, fixture(name))
        elif path == "/api/health":
            self.send(200, {"status": "ok", "paper_only": True, "execution": "absent"})
        elif path == "/research.md":
            self.send(200, (ROOT / "docs/research.md").read_bytes(), "text/plain; charset=utf-8")
        else:
            root = (ROOT / "web/dist").resolve()
            file = (root / (path.lstrip("/") or "index.html")).resolve()
            if not file.is_relative_to(root) or not file.is_file():
                self.send(404, {"error": "asset not found; run npm run build in web"})
                return
            types = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
            self.send(200, file.read_bytes(), types.get(file.suffix, "application/octet-stream"))

    def do_POST(self):
        origin = self.headers.get("Origin")
        expected = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        public_origin = getattr(self.server, "public_origin", None)
        if public_origin:
            expected.add(public_origin)
        if not self.valid_host() or (origin is not None and origin not in expected):
            self.send(403, {"error": "same-origin loopback requests only"})
            return
        if self.path != "/api/analyze":
            self.send(404, {"error": "no such local computation endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self.send(413, {"error": "request must be 1 byte to 2 MiB"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send(415, {"error": "application/json required"})
                return
            request = load_json(self.rfile.read(length))
            keys(request, ("dataset", "at", "quantity", "policy"), (), "request")
            data = validate_dataset(request["dataset"])
            policy = policy_from_dict(request["policy"])
            timestamp(request["at"])
            result = {"comparison": compare(data, request["at"], policy, request["quantity"]), "replay": replay(data, policy)}
            self.send(200, result)
        except (InputError, ValueError, TypeError, OverflowError) as exc:
            self.send(400, {"error": str(exc)})


def serve(port=8792):
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    public_origin = portless_origin()
    server = HTTPServer(("127.0.0.1", port), Handler)  # single worker, bounded CPU; no QuantLib shared globals
    server.public_origin = public_origin
    print(f"Paper-only local dashboard: {public_origin or f'http://127.0.0.1:{port}'}", flush=True)
    server.timeout = 10
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
