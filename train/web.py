# -*- coding: utf-8 -*-
"""Local web table: start a four-robot game and review records."""
import argparse
import json
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote

from train.play import list_games, load_game, play_game, result_text, save_game
from train.view import public_payload

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
INDEX = WEB / "index.html"


def pack_game(game):
    view = public_payload(game.get("events") or [])
    return {
        "id": game.get("id"),
        "created": game.get("created"),
        "seed": game.get("seed"),
        "result": game.get("result"),
        "result_text": result_text(game),
        "winner": game.get("winner"),
        "winners": game.get("winners") or [],
        "settle": game.get("settle"),
        "fans": game.get("fans") or {},
        "n_discard": game.get("n_discard"),
        "header": view.get("header"),
        "frames": view.get("frames") or [],
        "log": view.get("log") or [],
        "wall_left": view.get("wall_left"),
    }


class TableServer(ThreadingHTTPServer):
    allow_reuse_address = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body, content_type, cache=False):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store" if not cache else "public, max-age=60")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in ("/", "/index.html"):
            html = INDEX.read_text(encoding="utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/api/games":
            self._json(200, {"games": list_games()})
            return
        if path.startswith("/api/games/"):
            gid = path.split("/api/games/", 1)[1].strip("/")
            game = load_game(gid)
            if game is None:
                self._json(404, {"error": "not found"})
                return
            self._json(200, pack_game(game))
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/play":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}
        seed = body.get("seed") if isinstance(body, dict) else None
        table = body.get("table") if isinstance(body, dict) else None
        try:
            game = play_game(seed=seed, table=table or "mix")
            save_game(game)
            self._json(200, pack_game(game))
        except Exception as exc:
            self._json(500, {"error": str(exc)})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Four-robot mahjong web table")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    server = TableServer((args.host, args.port), Handler)
    url = "http://%s:%s/" % (args.host, args.port)
    sys.stdout.write("open %s\n" % url)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
