"""Small, restricted Horizons retrieval service and local GUI server.

The static GUI can live on GitHub Pages. Only ephemeris retrieval is served
here; uploaded files, screening results and run history stay in the browser.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from .bodies import validate_body_names
from .browser import trajectory_bundle
from .trajectories import get_trajectories
from .validation import parse_datetime

STEPS = {"1h": 3600, "6h": 21600, "1d": 86400}
MAX_SAMPLES = 5000
MAX_TOTAL_SAMPLES = 50000
# One request at a time to respect the Horizons fair-use policy.
_QUERY_LOCK = threading.Lock()
_CACHE = OrderedDict()
_CACHE_BYTES = 0
_BACKOFF_UNTIL = 0.0
CACHE_MAX_BYTES = 64 * 1024 * 1024
CACHE_TTL = 86400


def validate_request(payload):
    if not isinstance(payload, dict) or set(payload) != {"bodies", "start", "end", "step"}:
        raise ValueError("Provide bodies, start, end and step only.")
    if not isinstance(payload["bodies"], list) or not all(isinstance(b, str) for b in payload["bodies"]):
        raise ValueError("Bodies must be a list of supported names.")
    bodies = validate_body_names(payload["bodies"])
    if len(bodies) < 2 or bodies == ["Sun"]:
        raise ValueError("Select at least two bodies.")
    if payload["step"] not in STEPS:
        raise ValueError("Choose a sample spacing of 1h, 6h or 1d.")
    start = parse_datetime(payload["start"], "start")
    end = parse_datetime(payload["end"], "end")
    if not 1900 <= start.year <= end.year <= 2100 or start >= end:
        raise ValueError("Choose an increasing interval between 1900 and 2100.")
    seconds = (end - start).total_seconds()
    samples = int(seconds / STEPS[payload["step"]]) + 1
    if seconds % STEPS[payload["step"]] != 0:
        raise ValueError("The interval must be a whole number of sample steps.")
    if samples > MAX_SAMPLES or samples * len(bodies) > MAX_TOTAL_SAMPLES:
        raise ValueError("Use a shorter period or wider spacing (5,000 samples per body; 50,000 total per period).")
    return {"bodies": bodies, "start": start.isoformat(), "end": end.isoformat(), "step": payload["step"]}


class ServiceBusy(Exception):
    pass


def retrieve(payload):
    global _CACHE_BYTES, _BACKOFF_UNTIL
    request = validate_request(payload)
    key = json.dumps({**request, "bodies": sorted(request["bodies"])}, sort_keys=True)
    if not _QUERY_LOCK.acquire(blocking=False):
        raise ServiceBusy("Another Horizons request is in progress. Please try again shortly.")
    try:
        now = time.monotonic()
        if key in _CACHE:
            saved, encoded = _CACHE[key]
            if now - saved < CACHE_TTL:
                _CACHE.move_to_end(key)
                return encoded
            _CACHE_BYTES -= len(encoded)
            del _CACHE[key]
        if now < _BACKOFF_UNTIL:
            raise ServiceBusy("Horizons is temporarily unavailable. Please try again in a minute.")
        # Sun is the origin of HCI; Horizons rejects a target equal to its center.
        names = [b for b in request["bodies"] if b != "Sun"]
        try:
            trajectories = get_trajectories(names, request["start"], request["end"], request["step"])
        except Exception as exc:
            _BACKOFF_UNTIL = time.monotonic() + 60
            raise RuntimeError(f"{exc} Check mission coverage for the selected dates; Horizons may also be temporarily unavailable.") from exc
        bundle = trajectory_bundle(trajectories, request["start"], request["end"], request["step"])
        if "Sun" in request["bodies"]:
            samples = next(iter(bundle["trajectories"].values()))
            bundle["trajectories"]["Sun"] = [{"time": p["time"], "lon_deg": 0.0, "lat_deg": 0.0, "radius_km": 0.0} for p in samples]
        bundle["retrieval_method"] = "SolarConflux retrieval service / SunPy get_horizons_coord"
        bundle["sun_convention"] = "Sun is the HCI origin, not an independent longitude measurement."
        from .browser import load_bundle
        load_bundle(bundle)
        encoded = json.dumps(bundle, allow_nan=False).encode()
        while _CACHE and (_CACHE_BYTES + len(encoded) > CACHE_MAX_BYTES or len(_CACHE) >= 32):
            _, (_, old) = _CACHE.popitem(last=False)
            _CACHE_BYTES -= len(old)
        if len(encoded) <= CACHE_MAX_BYTES:
            _CACHE[key] = (time.monotonic(), encoded)
            _CACHE_BYTES += len(encoded)
        return encoded
    finally:
        _QUERY_LOCK.release()


class Handler(SimpleHTTPRequestHandler):
    # Only the built public directory is exposed; never serve the checkout.
    def allowed_origin(self):
        origin = self.headers.get("Origin")
        return not origin or origin in self.server.allowed_origins

    def respond(self, status, payload):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin and self.allowed_origin():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if status in (429, 503):
            self.send_header("Retry-After", "60")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.respond(200 if self.allowed_origin() else 403, {})

    def do_GET(self):
        if urlsplit(self.path).path == "/api/health":
            self.respond(200, {"service": "SolarConflux Horizons", "status": "ready"})
        elif urlsplit(self.path).path.startswith("/api/"):
            self.respond(404, {"error": "Unknown endpoint."})
        else:
            super().do_GET()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_POST(self):
        if urlsplit(self.path).path != "/api/trajectories":
            return self.respond(404, {"error": "Unknown endpoint."})
        if not self.allowed_origin():
            return self.respond(403, {"error": "This website is not an allowed origin."})
        if self.headers.get_content_type() != "application/json":
            return self.respond(415, {"error": "Send application/json."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                return self.respond(413, {"error": "Invalid request size."})
            self.connection.settimeout(30)
            payload = json.loads(self.rfile.read(length))
            response = retrieve(payload)
            self.respond(200, response)
        except ServiceBusy as exc:
            self.respond(429, {"error": str(exc)})
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(400, {"error": str(exc)[:500]})
        except RuntimeError as exc:
            self.respond(502, {"error": str(exc)[:500]})
        except Exception:
            self.respond(503, {"error": "The retrieval service is temporarily unavailable. Try again later."})


def create_server(host, port, directory, allowed_origins=()):
    server = ThreadingHTTPServer((host, port), partial(Handler, directory=str(directory)))
    server.daemon_threads = True
    actual_port = server.server_address[1]
    server.allowed_origins = set(allowed_origins) | {f"http://127.0.0.1:{actual_port}", f"http://localhost:{actual_port}"}
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--directory", default="dist")
    args = parser.parse_args()
    origins = [o.strip() for o in os.environ.get("SOLARCONFLUX_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    server = create_server(args.host, args.port, Path(args.directory).resolve(), origins)
    print(f"SolarConflux GUI and retrieval service: http://{args.host}:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
