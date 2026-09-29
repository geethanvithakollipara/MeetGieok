"""Core business logic: contacts, meetings, commitments, relationship stats."""
import hashlib
import json
import secrets
from datetime import datetime, timezone

from .extract import RuleBasedExtractor


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class Unauthorized(Exception):
    pass


class Clock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> datetime:
    try:
        dt = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        raise BadRequest(f"invalid datetime: {s!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def norm_due(s):
    """Date-only due dates mean end of that day."""
    if not s:
        return None
    return iso(parse(s + "T23:59:59Z" if len(s) == 10 else s))


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


class Service:
    def __init__(self, conn, clock=None, extractor=None):
        self.conn = conn
        self.clock = clock or Clock()
        self.extractor = extractor or RuleBasedExtractor()
        self.learning = None  # set by app wiring (avoids circular import)

    # ---------- users ----------
    def create_user(self, name, email=None):
        if not name:
            raise BadRequest("name required")
        key = "mpa_" + secrets.token_urlsafe(24)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO users(name,email,api_key_hash,created_at) VALUES(?,?,?,?)",
                (name, email, _hash(key), iso(self.clock.now())))
        return {"id": cur.lastrowid, "name": name, "email": email, "api_key": key}

    def authenticate(self, api_key):
        r = self.conn.execute("SELECT id FROM users WHERE api_key_hash=?",
                              (_hash(api_key or ""),)).fetchone()
        if not r:
            raise Unauthorized("invalid API key")
        return r["id"]

    # ---------- contacts ----------
    def add_contact(self, uid, name, email=None, company=None, role=None, notes=None):
        if not name:
            raise BadRequest("name required")
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO contacts(user_id,name,email,company,role,notes,created_at) "
                    "VALUES(?,?,?,?,?,?,?)", (uid, name, email, company, role, notes, iso(self.clock.now())))
        except Exception as e:
            if "UNIQUE" in str(e):
                raise BadRequest("contact with this email already exists")
            raise
        return self.get_contact(uid, cur.lastrowid)

    def get_contact(self, uid, cid):
        r = self.conn.execute("SELECT * FROM contacts WHERE id=? AND user_id=?", (cid, uid)).fetchone()
        if not r:
            raise NotFound(f"contact {cid}")
        c = dict(r)
        c["facts"] = rows(self.conn.execute(
            "SELECT id,category,fact,created_at FROM contact_facts WHERE contact_id=? ORDER BY id", (cid,)))
        return c

    def list_contacts(self, uid, q=None):
        sql, args = "SELECT * FROM contacts WHERE user_id=?", [uid]
        if q:
            sql += " AND (name LIKE ? OR company LIKE ? OR email LIKE ?)"
            args += [f"%{q}%"] * 3
        return rows(self.conn.execute(sql + " ORDER BY name", args))

    def update_contact(self, uid, cid, **fields):
        self.get_contact(uid, cid)
        allowed = {k: v for k, v in fields.items() if k in ("name", "email", "company", "role", "notes")}
        if allowed:
            sets = ",".join(f"{k}=?" for k in allowed)
            with self.conn:
                self.conn.execute(f"UPDATE contacts SET {sets} WHERE id=?", (*allowed.values(), cid))
        return self.get_contact(uid, cid)

    def add_fact(self, uid, cid, fact, category="general"):
        self.get_contact(uid, cid)
        if not fact:
            raise BadRequest("fact required")
        with self.conn:
            self.conn.execute("INSERT INTO contact_facts(contact_id,category,fact,created_at) VALUES(?,?,?,?)",
                              (cid, category, fact, iso(self.clock.now())))
        return self.get_contact(uid, cid)

    # ---------- meetings ----------
    def create_meeting(self, uid, title, scheduled_at, attendee_ids, duration_min=30,
                       meeting_type="general", location=None, agenda=None):
        if not title or not attendee_ids:
            raise BadRequest("title and at least one attendee required")
        for cid in attendee_ids:
            self.get_contact(uid, cid)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO meetings(user_id,title,scheduled_at,duration_min,meeting_type,location,agenda,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (uid, title, iso(parse(scheduled_at)), int(duration_min), meeting_type, location, agenda,
                 iso(self.clock.now())))
            self.conn.executemany("INSERT INTO meeting_attendees VALUES(?,?)",
                                  [(cur.lastrowid, c) for c in set(attendee_ids)])
        return self.get_meeting(uid, cur.lastrowid)

    def get_meeting(self, uid, mid):
        r = self.conn.execute("SELECT * FROM meetings WHERE id=? AND user_id=?", (mid, uid)).fetchone()
        if not r:
            raise NotFound(f"meeting {mid}")
        m = dict(r)
        m["attendees"] = rows(self.conn.execute(
            "SELECT c.id,c.name,c.email,c.company,c.role FROM contacts c "
            "JOIN meeting_attendees a ON a.contact_id=c.id WHERE a.meeting_id=? ORDER BY c.name", (mid,)))
        m["topics"] = [t["topic"] for t in self.conn.execute(
            "SELECT topic FROM meeting_topics WHERE meeting_id=? ORDER BY topic", (mid,))]
        m["commitments"] = rows(self.conn.execute(
            "SELECT * FROM commitments WHERE meeting_id=? ORDER BY id", (mid,)))
        return m

    def list_meetings(self, uid, upcoming=False, contact_id=None, limit=50):
        sql = "SELECT m.id FROM meetings m"
        where, args = ["m.user_id=?"], [uid]
        if contact_id:
            sql += " JOIN meeting_attendees a ON a.meeting_id=m.id"
            where.append("a.contact_id=?"); args.append(contact_id)
        if upcoming:
            where.append("m.status='scheduled' AND m.scheduled_at>=?"); args.append(iso(self.clock.now()))
        order = "ASC" if upcoming else "DESC"
        ids = [r["id"] for r in self.conn.execute(
            f"{sql} WHERE {' AND '.join(where)} ORDER BY m.scheduled_at {order} LIMIT ?", (*args, limit))]
        return [self.get_meeting(uid, i) for i in ids]

    def past_meetings(self, uid, contact_id, before=None, limit=10):
        return [self.get_meeting(uid, r["id"]) for r in self.conn.execute(
            "SELECT m.id FROM meetings m JOIN meeting_attendees a ON a.meeting_id=m.id "
            "WHERE m.user_id=? AND a.contact_id=? AND m.status='completed' AND m.scheduled_at<? "
            "ORDER BY m.scheduled_at DESC LIMIT ?",
            (uid, contact_id, before or iso(self.clock.now()), limit))]

    def cancel_meeting(self, uid, mid):
        self.get_meeting(uid, mid)
        with self.conn:
            self.conn.execute("UPDATE meetings SET status='cancelled' WHERE id=?", (mid,))
        return self.get_meeting(uid, mid)

    def complete_meeting(self, uid, mid, summary=None, notes=None, topics=None, commitments=None,
                         sentiment=None, actual_duration_min=None, extract=True):
        """Close out a meeting: store what was discussed, record promises (explicit + extracted),
        and feed the learning loop."""
        m = self.get_meeting(uid, mid)
        if m["status"] != "scheduled":
            raise BadRequest(f"meeting is {m['status']}")
        if sentiment is not None and not -2 <= int(sentiment) <= 2:
            raise BadRequest("sentiment must be between -2 and 2")
        text = "\n".join(x for x in (summary, notes) if x)
        topics = [t.lower().strip() for t in (topics or self.extractor.topics(text)) if t.strip()]
        items = list(commitments or [])
        if extract and notes:
            seen = {i["description"].lower() for i in items}
            for c in self.extractor.commitments(notes, [a["name"] for a in m["attendees"]], self.clock.now()):
                if c["description"].lower() not in seen:
                    items.append(c)
        created = []
        with self.conn:
            self.conn.execute(
                "UPDATE meetings SET status='completed',summary=?,notes=?,sentiment=?,completed_at=?,duration_min=? "
                "WHERE id=?", (summary, notes, sentiment, iso(self.clock.now()),
                               actual_duration_min or m["duration_min"], mid))
            self.conn.executemany("INSERT OR IGNORE INTO meeting_topics VALUES(?,?)", [(mid, t) for t in topics])
        for c in items:
            created.append(self._add_commitment(uid, m, c))
        if self.learning:
            self.learning.record_meeting_style(uid, self.get_meeting(uid, mid))
        out = self.get_meeting(uid, mid)
        out["extracted_commitments"] = created
        return out

    # ---------- commitments ----------
    def _add_commitment(self, uid, meeting, c):
        if c.get("owner") not in ("me", "them") or not c.get("description"):
            raise BadRequest("commitment needs owner ('me'|'them') and description")
        cid = c.get("contact_id")
        if not cid:
            person = (c.get("person") or "").lower()
            match = [a for a in meeting["attendees"] if person and a["name"].lower().split()[0] in person]
            cid = (match or meeting["attendees"])[0]["id"]
        self.get_contact(uid, cid)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO commitments(user_id,meeting_id,contact_id,owner,description,due_date,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (uid, meeting["id"], cid, c["owner"], c["description"], norm_due(c.get("due_date")),
                 iso(self.clock.now())))
        return self.get_commitment(uid, cur.lastrowid)

    def add_commitment(self, uid, contact_id, owner, description, due_date=None, meeting_id=None):
        meeting = {"id": meeting_id, "attendees": [{"id": contact_id, "name": ""}]}
        return self._add_commitment(uid, meeting, {"owner": owner, "description": description,
                                                   "due_date": due_date, "contact_id": contact_id})

    def get_commitment(self, uid, cid):
        r = self.conn.execute("SELECT * FROM commitments WHERE id=? AND user_id=?", (cid, uid)).fetchone()
        if not r:
            raise NotFound(f"commitment {cid}")
        return dict(r)

    def list_commitments(self, uid, status=None, contact_id=None, owner=None):
        sql, args = "SELECT * FROM commitments WHERE user_id=?", [uid]
        for col, v in (("status", status), ("contact_id", contact_id), ("owner", owner)):
            if v:
                sql += f" AND {col}=?"; args.append(v)
        return rows(self.conn.execute(sql + " ORDER BY COALESCE(due_date,'9999'), id", args))

    def complete_commitment(self, uid, cid):
        c = self.get_commitment(uid, cid)
        if c["status"] in ("done", "cancelled"):
            raise BadRequest(f"commitment already {c['status']}")
        now = self.clock.now()
        late = 1 if c["status"] == "missed" or (c["due_date"] and parse(c["due_date"]) < now) else 0
        with self.conn:
            self.conn.execute("UPDATE commitments SET status='done',completed_at=?,completed_late=? WHERE id=?",
                              (iso(now), late, cid))
        return self.get_commitment(uid, cid)

    def cancel_commitment(self, uid, cid):
        self.get_commitment(uid, cid)
        with self.conn:
            self.conn.execute("UPDATE commitments SET status='cancelled' WHERE id=?", (cid,))
        return self.get_commitment(uid, cid)

    def sweep_overdue(self, uid=None):
        """Business rule: an open commitment past its due date becomes 'missed'."""
        now = iso(self.clock.now())
        sql = "UPDATE commitments SET status='missed',missed_at=? WHERE status='open' AND due_date IS NOT NULL AND due_date<?"
        args = [now, now]
        if uid:
            sql += " AND user_id=?"; args.append(uid)
        with self.conn:
            return self.conn.execute(sql, args).rowcount

    # ---------- relationship intelligence ----------
    def contact_stats(self, uid, cid):
        self.get_contact(uid, cid)
        ms = rows(self.conn.execute(
            "SELECT m.scheduled_at,m.sentiment FROM meetings m JOIN meeting_attendees a ON a.meeting_id=m.id "
            "WHERE m.user_id=? AND a.contact_id=? AND m.status='completed' ORDER BY m.scheduled_at", (uid, cid)))
        now = self.clock.now()
        stats = {"meetings_count": len(ms), "first_met": None, "last_met": None, "days_since_last": None,
                 "cadence_days": None, "recent_sentiment": [m["sentiment"] for m in ms[-3:] if m["sentiment"] is not None]}
        if ms:
            dts = [parse(m["scheduled_at"]) for m in ms]
            stats.update(first_met=ms[0]["scheduled_at"], last_met=ms[-1]["scheduled_at"],
                         days_since_last=(now - dts[-1]).days)
            if len(dts) >= 3:
                gaps = [(b - a).days for a, b in zip(dts, dts[1:])]
                stats["cadence_days"] = round(sum(gaps) / len(gaps), 1)
        for owner in ("me", "them"):
            r = self.conn.execute(
                "SELECT SUM(status='done' AND completed_late=0) ontime, SUM(status IN ('done','missed')) total "
                "FROM commitments WHERE user_id=? AND contact_id=? AND owner=?", (uid, cid, owner)).fetchone()
            total = r["total"] or 0
            stats[f"reliability_{owner}"] = {
                "on_time_rate": round((r["ontime"] or 0) / total, 2) if total >= 3 else None, "sample": total}
        return stats

    def timeline(self, uid, cid):
        self.get_contact(uid, cid)
        events = [{"type": "meeting", "at": m["scheduled_at"], "title": m["title"], "status": m["status"],
                   "summary": m["summary"], "topics": m["topics"]}
                  for m in self.list_meetings(uid, contact_id=cid, limit=200)]
        events += [{"type": "commitment", "at": c["due_date"] or c["created_at"], "owner": c["owner"],
                    "text": c["description"], "status": c["status"]}
                   for c in self.list_commitments(uid, contact_id=cid)]
        return sorted(events, key=lambda e: e["at"], reverse=True)

    def search(self, uid, q):
        if not q or len(q) < 2:
            raise BadRequest("query too short")
        like = "%" + q.replace("%", r"\%").replace("_", r"\_") + "%"
        out = []
        for r in self.conn.execute(
                "SELECT DISTINCT m.id,m.title,m.scheduled_at,m.summary FROM meetings m WHERE m.user_id=? AND "
                "(m.title LIKE ? ESCAPE '\\' OR m.summary LIKE ? ESCAPE '\\' OR m.notes LIKE ? ESCAPE '\\') "
                "ORDER BY m.scheduled_at DESC LIMIT 25", (uid, like, like, like)):
            out.append({"type": "meeting", **dict(r)})
        for r in self.conn.execute(
                "SELECT c.id,c.name,f.fact FROM contact_facts f JOIN contacts c ON c.id=f.contact_id "
                "WHERE c.user_id=? AND f.fact LIKE ? ESCAPE '\\' LIMIT 25", (uid, like)):
            out.append({"type": "fact", **dict(r)})
        for r in self.conn.execute(
                "SELECT id,contact_id,description,status,owner FROM commitments WHERE user_id=? "
                "AND description LIKE ? ESCAPE '\\' LIMIT 25", (uid, like)):
            out.append({"type": "commitment", **dict(r)})
        return out
