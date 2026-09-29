import json
import os
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timezone

from meeting_prep import db
from meeting_prep.api import build, make_server


class FakeClock:
    def __init__(self, s):
        self.t = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

    def now(self):
        return self.t

    def set(self, s):
        self.t = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.conn = db.connect(os.path.join(self.tmp, "t.db"))
        db.init(self.conn)
        self.clock = FakeClock("2026-08-01T09:00:00")
        self.svc, self.learning, self.engine = build(self.conn, self.clock)
        self.u = self.svc.create_user("Alex", "alex@x.com")["id"]
        self.priya = self.svc.add_contact(self.u, "Priya Nair", "priya@acme.com", "Acme", "CTO")["id"]

    def _past_meeting(self, when, title, **complete):
        m = self.svc.create_meeting(self.u, title, when, [self.priya], 45, "sales")
        return self.svc.complete_meeting(self.u, m["id"], **complete)

    def test_commitment_extraction_and_missed_followups(self):
        done = self._past_meeting(
            "2026-08-01T10:00:00Z", "Acme kickoff", summary="Discussed pricing and rollout.",
            notes="I'll send the revised proposal by 2026-08-08. Priya will share the security questionnaire by 2026-08-15.",
            sentiment=1)
        owners = {c["owner"]: c for c in done["extracted_commitments"]}
        self.assertEqual(set(owners), {"me", "them"})
        self.assertTrue(owners["them"]["due_date"].startswith("2026-08-15"))

        # I deliver late; they never deliver
        self.clock.set("2026-08-12T09:00:00")
        late = self.svc.complete_commitment(self.u, owners["me"]["id"])
        self.assertEqual((late["status"], late["completed_late"]), ("done", 1))
        self.clock.set("2026-09-28T09:00:00")
        self.assertEqual(self.svc.sweep_overdue(self.u), 1)
        self.assertEqual(self.svc.list_commitments(self.u, status="missed")[0]["owner"], "them")

        upcoming = self.svc.create_meeting(self.u, "Acme check-in", "2026-09-30T10:00:00Z", [self.priya], 30)
        brief = self.engine.generate(self.u, upcoming["id"])
        sections = {s["key"]: s for s in brief["contacts"][0]["sections"]}
        self.assertIn("security questionnaire", sections["missed"]["items"][0]["text"].lower())
        self.assertIn("43 days overdue", sections["missed"]["items"][0]["text"])
        self.assertIn("pricing", " ".join(i["text"] for i in sections["last_time"]["items"]).lower())
        self.assertEqual(list(sections)[0], "missed")  # protected sections lead
        self.assertFalse(any("Close the loop" in i["text"] for i in sections["agenda"]["items"]))  # they owe me, not vice versa
        self.assertTrue(sections["agenda"]["items"][0]["text"].startswith("[10 min]") or "min]" in sections["agenda"]["items"][0]["text"])

    def test_learning_hides_useless_sections_and_adapts_length(self):
        self._past_meeting("2026-08-01T10:00:00Z", "Kickoff", topics=["pricing"], summary="s")
        up = self.svc.create_meeting(self.u, "Next", "2026-09-30T10:00:00Z", [self.priya])
        for _ in range(4):
            b = self.engine.generate(self.u, up["id"])
            self.learning.record_feedback(self.u, b["id"], "history", useful=False)
        keys = [s["key"] for s in self.engine.generate(self.u, up["id"])["contacts"][0]["sections"]]
        self.assertNotIn("history", keys)
        b = self.engine.generate(self.u, up["id"])
        self.assertEqual(self.learning.record_feedback(self.u, b["id"], "_", length="too_long")["max_items"], 4)
        with self.assertRaises(Exception):
            self.learning.set_prefs(self.u, {"hidden_sections": ["missed"]})  # accountability stays visible

    def test_meeting_style_learning_and_isolation(self):
        self._past_meeting("2026-08-01T10:00:00Z", "A", topics=["x"])
        self._past_meeting("2026-08-08T10:00:00Z", "B", topics=["x"])
        style = self.learning.get_prefs(self.u)["style"]
        self.assertEqual((style["meetings"], style["typical_meeting_type"], style["typical_hour_utc"]), (2, "sales", 10))
        other = self.svc.create_user("Eve")["id"]
        from meeting_prep.services import NotFound
        with self.assertRaises(NotFound):
            self.svc.get_contact(other, self.priya)


class HttpTests(unittest.TestCase):
    def test_end_to_end(self):
        path = os.path.join(tempfile.mkdtemp(), "h.db")
        srv = make_server(path, port=0, admin_token="adm")
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def call(method, p, body=None, key=None, admin=None, raw=False):
            req = urllib.request.Request(base + p, method=method, data=json.dumps(body).encode() if body is not None else None)
            if key: req.add_header("X-API-Key", key)
            if admin: req.add_header("X-Admin-Token", admin)
            try:
                with urllib.request.urlopen(req) as r:
                    data = r.read().decode()
                    return r.status, (data if raw else json.loads(data))
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        self.assertEqual(call("POST", "/users", {"name": "A"})[0], 401)
        _, user = call("POST", "/users", {"name": "Alex"}, admin="adm")
        k = user["api_key"]
        self.assertEqual(call("GET", "/contacts")[0], 401)
        _, c = call("POST", "/contacts", {"name": "Sam Lee", "company": "Globex"}, key=k)
        _, m = call("POST", "/meetings", {"title": "Intro", "scheduled_at": "2030-01-01T10:00:00Z",
                                          "attendee_ids": [c["id"]]}, key=k)
        s, done = call("POST", f"/meetings/{m['id']}/complete", {"notes": "I'll send the deck by 2030-01-05."}, key=k)
        self.assertEqual((s, len(done["extracted_commitments"])), (200, 1))
        m2 = call("POST", "/meetings", {"title": "Follow-up", "scheduled_at": "2030-02-01T10:00:00Z",
                                        "attendee_ids": [c["id"]]}, key=k)[1]
        self.assertEqual(call("POST", f"/meetings/{m2['id']}/brief", key=k)[0], 201)
        s, md = call("GET", f"/meetings/{m2['id']}/brief?format=markdown", key=k, raw=True)
        self.assertIn("What you owe them", md)
        self.assertEqual(call("POST", "/meetings", {"title": "x"}, key=k)[0], 400)
        self.assertEqual(call("GET", "/meetings/999", key=k)[0], 404)
        srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
