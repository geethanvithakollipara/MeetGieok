"""HTTP layer (stdlib only). Every request gets its own DB connection; auth via X-API-Key."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db
from .briefing import BriefingEngine, render_markdown
from .learning import Learning
from .services import BadRequest, Clock, NotFound, Service, Unauthorized


def build(conn, clock=None, extractor=None):
    svc = Service(conn, clock, extractor)
    learning = Learning(conn, svc.clock)
    svc.learning = learning
    return svc, learning, BriefingEngine(svc, learning)


# (method, regex, handler(ctx, uid, match, query, body)) -> (status, payload)
ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


class Ctx:
    def __init__(self, svc, learning, engine):
        self.svc, self.learning, self.engine = svc, learning, engine


def _i(m, n=1):
    return int(m.group(n))


@route("POST", r"/contacts")
def _(c, u, m, q, b): return 201, c.svc.add_contact(u, **{k: b.get(k) for k in ("name", "email", "company", "role", "notes")})

@route("GET", r"/contacts")
def _(c, u, m, q, b): return 200, c.svc.list_contacts(u, q.get("q"))

@route("GET", r"/contacts/(\d+)")
def _(c, u, m, q, b): return 200, {**c.svc.get_contact(u, _i(m)), "stats": c.svc.contact_stats(u, _i(m))}

@route("PATCH", r"/contacts/(\d+)")
def _(c, u, m, q, b): return 200, c.svc.update_contact(u, _i(m), **b)

@route("POST", r"/contacts/(\d+)/facts")
def _(c, u, m, q, b): return 201, c.svc.add_fact(u, _i(m), b.get("fact"), b.get("category", "general"))

@route("GET", r"/contacts/(\d+)/timeline")
def _(c, u, m, q, b): return 200, c.svc.timeline(u, _i(m))

@route("POST", r"/meetings")
def _(c, u, m, q, b):
    return 201, c.svc.create_meeting(u, b.get("title"), b.get("scheduled_at"), b.get("attendee_ids") or [],
                                     b.get("duration_min", 30), b.get("meeting_type", "general"),
                                     b.get("location"), b.get("agenda"))

@route("GET", r"/meetings")
def _(c, u, m, q, b):
    return 200, c.svc.list_meetings(u, upcoming=q.get("upcoming") == "1",
                                    contact_id=int(q["contact_id"]) if q.get("contact_id") else None)

@route("GET", r"/meetings/(\d+)")
def _(c, u, m, q, b): return 200, c.svc.get_meeting(u, _i(m))

@route("POST", r"/meetings/(\d+)/complete")
def _(c, u, m, q, b):
    return 200, c.svc.complete_meeting(u, _i(m), b.get("summary"), b.get("notes"), b.get("topics"),
                                       b.get("commitments"), b.get("sentiment"),
                                       b.get("actual_duration_min"), b.get("extract", True))

@route("POST", r"/meetings/(\d+)/cancel")
def _(c, u, m, q, b): return 200, c.svc.cancel_meeting(u, _i(m))

@route("POST", r"/meetings/(\d+)/brief")
def _(c, u, m, q, b): return 201, c.engine.generate(u, _i(m))

@route("GET", r"/meetings/(\d+)/brief")
def _(c, u, m, q, b):
    brief = c.engine.latest(u, _i(m))
    return (200, ("text/markdown", render_markdown(brief))) if q.get("format") == "markdown" else (200, brief)

@route("POST", r"/briefs/(\d+)/feedback")
def _(c, u, m, q, b):
    return 200, c.learning.record_feedback(u, _i(m), b.get("section"), b.get("useful"), b.get("length"), b.get("comment"))

@route("GET", r"/commitments")
def _(c, u, m, q, b):
    c.svc.sweep_overdue(u)
    return 200, c.svc.list_commitments(u, q.get("status"), int(q["contact_id"]) if q.get("contact_id") else None, q.get("owner"))

@route("POST", r"/commitments")
def _(c, u, m, q, b):
    return 201, c.svc.add_commitment(u, b.get("contact_id"), b.get("owner"), b.get("description"),
                                     b.get("due_date"), b.get("meeting_id"))

@route("POST", r"/commitments/(\d+)/complete")
def _(c, u, m, q, b): return 200, c.svc.complete_commitment(u, _i(m))

@route("POST", r"/commitments/(\d+)/cancel")
def _(c, u, m, q, b): return 200, c.svc.cancel_commitment(u, _i(m))

@route("GET", r"/preferences")
def _(c, u, m, q, b): return 200, c.learning.get_prefs(u)

@route("PUT", r"/preferences")
def _(c, u, m, q, b): return 200, c.learning.set_prefs(u, b)

@route("GET", r"/search")
def _(c, u, m, q, b): return 200, c.svc.search(u, q.get("q"))


def make_server(db_path, host="127.0.0.1", port=8000, admin_token=None, clock=None, extractor=None):
    admin_token = admin_token or os.environ.get("MPA_ADMIN_TOKEN")
    boot = db.connect(db_path)
    db.init(boot)
    boot.close()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, payload):
            ctype = "application/json"
            if isinstance(payload, tuple):
                ctype, payload = payload
                body = payload.encode()
            else:
                body = json.dumps(payload).encode()

            self.send_response(status)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _handle(self, method):
            if method == "OPTIONS":
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
                self.end_headers()
                return

            url = urlparse(self.path)

            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            conn = db.connect(db_path)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"{}") if length else {}
                except json.JSONDecodeError:
                    raise BadRequest("body must be valid JSON")
                svc, learning, engine = build(conn, clock, extractor)
                if method == "POST" and url.path == "/users":
                    if not admin_token or self.headers.get("X-Admin-Token") != admin_token:
                        raise Unauthorized("admin token required")
                    return self._send(201, svc.create_user(body.get("name"), body.get("email")))
                if method == "GET" and url.path == "/health":
                    return self._send(200, {"ok": True})
                uid = svc.authenticate(self.headers.get("X-API-Key"))
                for meth, rx, fn in ROUTES:
                    mt = rx.match(url.path)
                    if meth == method and mt:
                        status, payload = fn(Ctx(svc, learning, engine), uid, mt, query, body)
                        return self._send(status, payload)
                self._send(404, {"error": "route not found"})
            except Unauthorized as e:
                self._send(401, {"error": str(e)})
            except NotFound as e:
                self._send(404, {"error": f"not found: {e}"})
            except (BadRequest, TypeError, ValueError) as e:
                self._send(400, {"error": str(e)})
            finally:
                conn.close()

        do_GET = lambda self: self._handle("GET")
        do_POST = lambda self: self._handle("POST")
        do_PATCH = lambda self: self._handle("PATCH")
        do_PUT = lambda self: self._handle("PUT")
        do_OPTIONS = lambda self: self._handle("OPTIONS")

    return ThreadingHTTPServer((host, port), Handler)
