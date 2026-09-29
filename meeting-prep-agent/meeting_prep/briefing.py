"""Builds the pre-meeting brief from everything remembered about each attendee."""

import json
from collections import Counter

from .learning import PROTECTED
from .services import iso, parse

import sys

AI_PATH = r"C:\Users\Dell\Desktop\MeetGieok\MeetGieok\meeting_prep_ai"

MEMORY_PATH = r"C:\Users\Dell\Desktop\MeetGieok\MeetGieok\hindsight_memory"

if AI_PATH not in sys.path:
    sys.path.insert(0, AI_PATH)

if MEMORY_PATH not in sys.path:
    sys.path.insert(0, MEMORY_PATH)

from brief import generate_brief
from memory import Contact, MeetingRecord, recall_memory


DEFAULT_ORDER = [
    "flags",
    "ai_previous_context",
    "ai_personalization",
    "ai_questions",
    "ai_talking_points",
    "ai_followups",
    "missed",
    "open_mine",
    "open_theirs",
    "last_time",
    "agenda",
    "recurring_topics",
    "personal",
    "history",
]
TITLES = {
    "flags": "Heads-up", "missed": "Missed follow-ups", "open_mine": "What you owe them",
    "open_theirs": "What they owe you", "last_time": "Last time", "agenda": "Suggested agenda",
    "recurring_topics": "Recurring topics", "personal": "Personal notes", "history": "Meeting history",
    "ai_previous_context": "AI Previous Context",
    "ai_personalization": "AI Personalization",
    "ai_questions": "AI Suggested Questions",
    "ai_talking_points": "AI Talking Points",
    "ai_followups": "AI Follow-ups",
}


def _day(s):
    return s[:10] if s else "no due date"


class BriefingEngine:
    def __init__(self, svc, learning):
        self.svc, self.learning = svc, learning

    def generate(self, uid, meeting_id):
        self.svc.sweep_overdue(uid)
        m = self.svc.get_meeting(uid, meeting_id)
        if m["status"] == "cancelled":
            from .services import BadRequest
            raise BadRequest("meeting is cancelled")
        prefs = self.learning.get_prefs(uid)
        content = {
            "meeting": {k: m[k] for k in ("id", "title", "scheduled_at", "duration_min", "meeting_type",
                                          "location", "agenda")},
            "generated_at": iso(self.svc.clock.now()),
            "contacts": [self._contact_brief(uid, m, c) for c in m["attendees"]],
            "applied_preferences": {"max_items": prefs["max_items"], "pinned": prefs["pinned_sections"]},
        }
        with self.svc.conn:
            cur = self.svc.conn.execute(
                "INSERT INTO briefs(user_id,meeting_id,generated_at,content) VALUES(?,?,?,?)",
                (uid, meeting_id, content["generated_at"], json.dumps(content)))
        content["id"] = cur.lastrowid
        return content

    def latest(self, uid, meeting_id):
        from .services import NotFound
        r = self.svc.conn.execute(
            "SELECT id,content FROM briefs WHERE user_id=? AND meeting_id=? ORDER BY id DESC LIMIT 1",
            (uid, meeting_id)).fetchone()
        if not r:
            raise NotFound("no brief generated yet for this meeting")
        return {**json.loads(r["content"]), "id": r["id"]}

    # ---------- per contact ----------
    def _contact_brief(self, uid, m, c):
        svc, now = self.svc, self.svc.clock.now()
        contact = svc.get_contact(uid, c["id"])
        stats = svc.contact_stats(uid, c["id"])
        hist = svc.past_meetings(uid, c["id"], before=m["scheduled_at"], limit=10)
        missed = svc.list_commitments(uid, status="missed", contact_id=c["id"])
        open_ = svc.list_commitments(uid, status="open", contact_id=c["id"])
        mine = [x for x in open_ if x["owner"] == "me"]
        theirs = [x for x in open_ if x["owner"] == "them"]
        S = {}
                # AI-powered personalized brief
                # Hindsight-powered personalized brief
        try:
            ai_contact = Contact(
                name=contact["name"],
                role=contact.get("role") or "",
                company=contact.get("company") or "",
            )

            memory_groups = recall_memory(
                ai_contact,
                top_k=6
            )

            memories = []
            for category, items in memory_groups.items():
                for item in items:
                    memories.append(f"{category}: {item}")

            ai_meeting = {
                "title": m["title"],
                "date": m["scheduled_at"][:10],
                "agenda": m.get("agenda") or "",
            }

            ai_contact_data = {
                "name": contact["name"],
                "role": contact.get("role") or "",
                "company": contact.get("company") or "",
                "background": contact.get("notes") or "",
            }

            ai_brief = generate_brief(
                ai_contact_data,
                ai_meeting,
                memories
            )

            S["ai_previous_context"] = [
                {"text": x}
                for x in ai_brief.get("previous_context", [])
            ]

            S["ai_questions"] = [
                {"text": x}
                for x in ai_brief.get("suggested_questions", [])
            ]

            S["ai_talking_points"] = [
                {"text": x}
                for x in ai_brief.get("talking_points", [])
            ]

            S["ai_followups"] = [
                {"text": x}
                for x in ai_brief.get("potential_followups", [])
            ]

            if ai_brief.get("personalization_note"):
                S["ai_personalization"] = [
                    {"text": ai_brief["personalization_note"]}
                ]

        except Exception as e:
            print(
                f"[AI/Hindsight] brief generation unavailable: "
                f"{type(e).__name__}: {e}"
            )

        # flags: relationship alerts
        flags = []
        if not hist:
            flags.append("First recorded meeting with this contact - no prior context.")
        if stats["cadence_days"] and stats["days_since_last"] > 1.5 * stats["cadence_days"]:
            flags.append(f"{stats['days_since_last']} days since you last met "
                         f"(you usually meet about every {stats['cadence_days']:.0f} days).")
        for owner, who in (("them", "They have"), ("me", "You have")):
            r = stats[f"reliability_{owner}"]
            if r["on_time_rate"] is not None and r["on_time_rate"] < 0.6:
                flags.append(f"{who} delivered only {round(r['on_time_rate'] * 100)}% of commitments "
                             f"on time ({r['sample']} tracked).")
        if len(stats["recent_sentiment"]) >= 2 and all(s <= -1 for s in stats["recent_sentiment"][-2:]):
            flags.append("The last two meetings ended on a negative note.")
        S["flags"] = [{"text": t} for t in flags]

        def commit_item(x, prefix):
            due = f"due {_day(x['due_date'])}"
            if x["status"] == "missed":
                due += f", {(now - parse(x['due_date'])).days} days overdue"
            return {"id": x["id"], "text": f"{prefix}{x['description']} ({due})"}

        S["missed"] = [commit_item(x, "You promised: " if x["owner"] == "me" else "They promised: ")
                       for x in missed]
        S["open_mine"] = [commit_item(x, "") for x in mine]
        S["open_theirs"] = [commit_item(x, "") for x in theirs]

        if hist:
            last = hist[0]
            tone = {-2: "very negative", -1: "negative", 0: "neutral", 1: "positive", 2: "very positive"}
            line = f"{last['scheduled_at'][:10]} - {last['title']}"
            items = [{"text": line}]
            if last["summary"]:
                items.append({"text": last["summary"]})
            if last["topics"]:
                items.append({"text": "Topics: " + ", ".join(last["topics"])})
            if last["sentiment"] is not None:
                items.append({"text": f"Ended on a {tone[last['sentiment']]} note."})
            S["last_time"] = items
            S["history"] = [{"text": f"{h['scheduled_at'][:10]} - {h['title']}"
                             + (f" ({', '.join(h['topics'][:3])})" if h["topics"] else "")} for h in hist]
            counts = Counter(t for h in hist for t in h["topics"])
            S["recurring_topics"] = [{"text": f"{t} ({n} meetings)"} for t, n in counts.most_common() if n >= 2]

        S["personal"] = [{"text": f"{f['category']}: {f['fact']}" if f["category"] != "general" else f["fact"]}
                         for f in contact["facts"]]
        S["agenda"] = self._agenda(uid, m, hist, missed, mine, theirs)

        order, prefs = self.learning.arrange_sections(uid, [k for k in DEFAULT_ORDER if S.get(k)])
        cap = prefs["max_items"]
        sections = []
        for k in order:
            items = S[k]
            if len(items) > cap:
                items = items[:cap] + [{"text": f"...and {len(S[k]) - cap} more"}]
            sections.append({"key": k, "title": TITLES[k], "protected": k in PROTECTED, "items": items})
        return {"contact": {k: contact[k] for k in ("id", "name", "email", "company", "role")},
                "stats": stats, "sections": sections}

    def _agenda(self, uid, m, hist, missed, mine, theirs):
        steps = []
        owed = [x for x in missed if x["owner"] == "me"] + mine
        if owed:
            steps.append("Close the loop on what you owe: " + "; ".join(x["description"] for x in owed[:2]))
        if hist and hist[0]["topics"]:
            steps.append("Follow up on last time: " + ", ".join(hist[0]["topics"][:3]))
        if theirs or [x for x in missed if x["owner"] == "them"]:
            waiting = [x["description"] for x in theirs + [x for x in missed if x["owner"] == "them"]][:2]
            steps.append("Ask about their open items: " + "; ".join(waiting))
        if not hist:
            steps.insert(0, "Introductions and goals for the relationship")
        if m.get("agenda"):
            steps.insert(0, "Planned agenda: " + m["agenda"])
        steps.append("Agree on next steps, owners and dates")
        duration = m["duration_min"] or (self.learning.get_prefs(uid)["style"]["avg_duration"] or 30)
        per = max(5, int(duration) // len(steps))
        return [{"text": f"[{per} min] {s}"} for s in steps]


def render_markdown(brief):
    mt = brief["meeting"]
    lines = [f"# Prep: {mt['title']}", f"*{mt['scheduled_at']} - {mt['duration_min']} min*", ""]
    for cb in brief["contacts"]:
        c = cb["contact"]
        who = c["name"] + (f" ({c['role']}, {c['company']})" if c["role"] and c["company"] else
                           f" ({c['company']})" if c["company"] else "")
        n = cb['stats']['meetings_count']
        lines += [f"## {who}", f"Met {n} time{'' if n == 1 else 's'}", ""]
        for s in cb["sections"]:
            lines.append(f"### {s['title']}")
            lines += [f"- {i['text']}" for i in s["items"]]
            lines.append("")
    return "\n".join(lines)
