"""Learns how the user likes to prepare: which brief sections they value, how long they
want briefs, and their typical meeting style."""
import json

from .services import iso, parse

PROTECTED = ("flags", "missed", "open_mine")   # never hidden or demoted: these are accountability items
DEFAULTS = {"max_items": 5, "hidden_sections": [], "pinned_sections": []}
EMA_ALPHA = 0.3
HIDE_BELOW, HIDE_MIN_SAMPLES = 0.25, 4


class Learning:
    def __init__(self, conn, clock):
        self.conn, self.clock = conn, clock

    def _get(self, uid, key, default=None):
        r = self.conn.execute("SELECT value FROM preferences WHERE user_id=? AND key=?", (uid, key)).fetchone()
        return json.loads(r["value"]) if r else default

    def _put(self, uid, key, value):
        with self.conn:
            self.conn.execute(
                "INSERT INTO preferences(user_id,key,value,updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (uid, key, json.dumps(value), iso(self.clock.now())))

    # ---- explicit + learned preferences ----
    def get_prefs(self, uid):
        prefs = {k: self._get(uid, k, d) for k, d in DEFAULTS.items()}
        style = self._get(uid, "style", {"meetings": 0, "avg_duration": None, "types": {}, "hours": {}})
        prefs["style"] = {
            **style,
            "typical_meeting_type": max(style["types"], key=style["types"].get) if style["types"] else None,
            "typical_hour_utc": int(max(style["hours"], key=style["hours"].get)) if style["hours"] else None}
        prefs["section_scores"] = {r["section"]: {"score": round(r["score"], 2), "samples": r["samples"]}
                                   for r in self.conn.execute("SELECT * FROM section_stats WHERE user_id=?", (uid,))}
        return prefs

    def set_prefs(self, uid, updates):
        from .services import BadRequest
        for k, v in updates.items():
            if k == "max_items":
                if not isinstance(v, int) or not 2 <= v <= 10:
                    raise BadRequest("max_items must be an integer 2-10")
            elif k in ("hidden_sections", "pinned_sections"):
                if not isinstance(v, list):
                    raise BadRequest(f"{k} must be a list")
                if k == "hidden_sections" and set(v) & set(PROTECTED):
                    raise BadRequest(f"cannot hide protected sections: {', '.join(PROTECTED)}")
            else:
                raise BadRequest(f"unknown preference: {k}")
            self._put(uid, k, v)
        return self.get_prefs(uid)

    # ---- learning from feedback ----
    def record_feedback(self, uid, brief_id, section, useful=None, length=None, comment=None):
        from .services import BadRequest, NotFound
        if not self.conn.execute("SELECT 1 FROM briefs WHERE id=? AND user_id=?", (brief_id, uid)).fetchone():
            raise NotFound(f"brief {brief_id}")
        if useful is None and length is None:
            raise BadRequest("provide useful (bool) and/or length ('too_long'|'too_short')")
        with self.conn:
            self.conn.execute(
                "INSERT INTO brief_feedback(brief_id,section,useful,comment,created_at) VALUES(?,?,?,?,?)",
                (brief_id, section if useful is not None else "_length",
                 None if useful is None else int(bool(useful)), comment or length, iso(self.clock.now())))
            if useful is not None:
                target = 1.0 if useful else 0.0
                self.conn.execute("INSERT OR IGNORE INTO section_stats(user_id,section) VALUES(?,?)", (uid, section))
                self.conn.execute(
                    "UPDATE section_stats SET score=score+?*(?-score), samples=samples+1 WHERE user_id=? AND section=?",
                    (EMA_ALPHA, target, uid, section))
        if length:
            if length not in ("too_long", "too_short"):
                raise BadRequest("length must be 'too_long' or 'too_short'")
            cur = self._get(uid, "max_items", DEFAULTS["max_items"])
            self._put(uid, "max_items", max(2, cur - 1) if length == "too_long" else min(10, cur + 1))
        return self.get_prefs(uid)

    # ---- learning from meetings ----
    def record_meeting_style(self, uid, meeting):
        s = self._get(uid, "style", {"meetings": 0, "avg_duration": None, "types": {}, "hours": {}})
        n = s["meetings"]
        s["avg_duration"] = round(((s["avg_duration"] or 0) * n + meeting["duration_min"]) / (n + 1), 1)
        s["meetings"] = n + 1
        s["types"][meeting["meeting_type"]] = s["types"].get(meeting["meeting_type"], 0) + 1
        h = str(parse(meeting["scheduled_at"]).hour)
        s["hours"][h] = s["hours"].get(h, 0) + 1
        self._put(uid, "style", s)

    # ---- applying what was learned ----
    def arrange_sections(self, uid, keys):
        """Order and filter section keys: protected first, then pinned, then by learned score."""
        prefs = self.get_prefs(uid)
        scores = prefs["section_scores"]
        hidden = set(prefs["hidden_sections"])
        for k, v in scores.items():
            if k not in PROTECTED and v["samples"] >= HIDE_MIN_SAMPLES and v["score"] < HIDE_BELOW:
                hidden.add(k)
        keep = [k for k in keys if k in PROTECTED or k not in hidden]
        base = {k: i for i, k in enumerate(keep)}

        def rank(k):
            if k in PROTECTED:
                return (0, base[k])
            if k in prefs["pinned_sections"]:
                return (1, base[k])
            return (2, -scores.get(k, {"score": 0.5})["score"], base[k])
        return sorted(keep, key=rank), prefs
