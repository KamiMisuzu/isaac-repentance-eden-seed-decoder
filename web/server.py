from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.eden_display import build_display
from tools.eden_predict import EdenPredictOptions, predict_eden
from tools.eden_reverse import iter_reverse_search_from_raw, reverse_search
from tools.profile_store import profile_status, run_memory_extract
from tools.seed_codec import suggest_canonical_seed

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".ico": "image/x-icon",
}


class EdenHandler(BaseHTTPRequestHandler):
    server_version = "EdenPredict/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_error(self, code, message=None, explain=None):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._send_json(code, {"ok": False, "error": message or explain or str(code)})
            return
        super().send_error(code, message, explain)

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_ndjson_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _stream_line(self, obj: dict) -> None:
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        self.wfile.write(line.encode("utf-8"))
        self.wfile.flush()

    def _read_json_body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        return json.loads(raw.decode("utf-8"))

    def _predict_error_payload(self, seed: str, exc: Exception) -> dict:
        payload: dict = {"ok": False, "error": str(exc)}
        if seed:
            sug = suggest_canonical_seed(seed)
            if sug and sug.upper() != seed.strip().upper():
                payload["suggested_seed"] = sug
        return payload

    def _predict_from_params(self, params: dict) -> dict:
        seed = (params.get("seed") or [""])[0].strip()
        p3ec = params.get("p3ec", [None])[0]
        ach = params.get("ach_159", ["0"])[0]

        def _int(v):
            if v is None or v == "":
                return None
            return int(v) & 0xFFFFFFFF

        opts = EdenPredictOptions(
            seed_label=seed,
            p3ec=_int(p3ec),
            achievement_159=str(ach).lower() in ("1", "true", "yes"),
        )
        from tools.profile_store import resolve_proc_table_path, resolve_trinket_pool_path

        tri = resolve_trinket_pool_path(None)
        proc = resolve_proc_table_path(None)
        if tri:
            opts.trinket_pool = tri
        if proc:
            opts.proc_table = proc

        result = predict_eden(opts)
        return {
            "ok": True,
            "data": result.to_json_dict(),
            "display": build_display(result),
            "profile": profile_status(),
        }

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path)
        if path.path == "/api/profile":
            self._send_json(200, {"ok": True, **profile_status()})
            return
        if path.path == "/api/predict":
            qs = parse_qs(path.query)
            seed = (qs.get("seed") or [""])[0].strip()
            try:
                data = self._predict_from_params(qs)
                self._send_json(200, data)
            except Exception as e:
                self._send_json(400, self._predict_error_payload(seed, e))
            return
        if path.path in ("/", "/index.html"):
            self._serve_file(WEB_DIR / "index.html")
            return
        if path.path.startswith("/static/"):
            rel = path.path[len("/static/") :]
            target = (WEB_DIR / "static" / rel).resolve()
            if not str(target).startswith(str((WEB_DIR / "static").resolve())):
                self.send_error(403)
                return
            if target.is_file():
                self._serve_file(target)
                return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path)
        if path.path == "/api/extract":
            try:
                body = self._read_json_body()
                profile = (body.get("profile") or "").strip() or None
                result = run_memory_extract(profile=profile)
                result["profile_status"] = profile_status()
                self._send_json(200, result)
            except Exception as e:
                try:
                    self._send_json(400, {"ok": False, "error": str(e)})
                except (ConnectionAbortedError, BrokenPipeError):
                    pass
            return
        if path.path == "/api/predict":
            body = self._read_json_body()
            seed = str(body.get("seed") or "").strip()
            try:
                params = {k: [str(v)] for k, v in body.items()}
                data = self._predict_from_params(params)
                self._send_json(200, data)
            except Exception as e:
                try:
                    self._send_json(400, self._predict_error_payload(seed, e))
                except (ConnectionAbortedError, BrokenPipeError):
                    pass
            return
        if path.path == "/api/reverse":
            body: dict = {}
            try:
                body = self._read_json_body()
                if body.get("stream"):
                    self._send_ndjson_stream()
                    for event in iter_reverse_search_from_raw(
                        body, log_terminal=True, log_source="web"
                    ):
                        self._stream_line(event)
                    self._stream_line({"type": "profile", "profile": profile_status()})
                else:
                    data = reverse_search(body, log_terminal=True, log_source="web")
                    data["profile"] = profile_status()
                    self._send_json(200, data)
            except (ConnectionAbortedError, BrokenPipeError):
                pass
            except Exception as e:
                try:
                    if body.get("stream"):
                        self._stream_line({"type": "error", "ok": False, "error": str(e)})
                    else:
                        self._send_json(400, {"ok": False, "error": str(e)})
                except (ConnectionAbortedError, BrokenPipeError):
                    pass
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def _serve_file(self, path: Path) -> None:
        data = path.read_bytes()
        ext = path.suffix.lower()
        ctype = MIME.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), EdenHandler)
    url = f"http://{host}:{port}/"
    print(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
