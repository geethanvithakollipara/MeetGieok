"""Turns raw meeting notes into topics + commitments.

The default RuleBasedExtractor needs no external services. ClaudeExtractor is an
optional drop-in (same interface) that falls back to the rules on any failure.
"""
import json
import re
from collections import Counter
from datetime import datetime, timedelta

STOP = set("""the and for with that this from have will about into your our their they them there what
when where which would could should been being were was are but not you all can had has his her its also
just more some then than very over out any get got let like need want going gonna talk talked discuss
discussed meeting call next last week month today tomorrow yesterday send sent share shared""".split())
WORD = re.compile(r"[a-zA-Z][a-zA-Z\-']{3,}")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ME_RE = re.compile(r"\b(i'll|i will|i promised to|i agreed to|i'm going to|we'll|we will)\b", re.I)
THEM_RE = re.compile(r"\b(they'll|they will|she'll|she will|he'll|he will)\b", re.I)
EXPLICIT_RE = re.compile(r"^(?:action|todo|to-do)\s*\((me|them)\)\s*[:\-]\s*(.+)$", re.I)


def extract_topics(text: str, k: int = 5) -> list:
    counts = Counter(w.lower().strip("'-") for w in WORD.findall(text or ""))
    ranked = sorted(((w, c) for w, c in counts.items() if w not in STOP and c >= 2),
                    key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:k]]


def parse_due(text: str, now: datetime):
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    t = text.lower()
    if "tomorrow" in t:
        return (now + timedelta(days=1)).date().isoformat()
    if "next week" in t:
        return (now + timedelta(days=7)).date().isoformat()
    m = re.search(r"\b(?:by|on|before)\s+(?:next\s+)?(" + "|".join(WEEKDAYS) + r")\b", t)
    if m:
        delta = (WEEKDAYS.index(m.group(1)) - now.weekday()) % 7 or 7
        return (now + timedelta(days=delta)).date().isoformat()
    return None


def _clean(s: str) -> str:
    s = s.strip(" -•*\t").rstrip(".!")
    return s[:1].upper() + s[1:]


class RuleBasedExtractor:
    def topics(self, text: str) -> list:
        return extract_topics(text)

    def commitments(self, text: str, attendee_names: list, now: datetime) -> list:
        """Heuristic: 'I'll ...' -> me, '<Name>/they will ...' -> them,
        'ACTION (me|them): ...' -> explicit. Returns [{owner, description, due_date, person}]."""
        out = []
        for sent in re.split(r"(?<=[.!?])\s+|\n+|;", text or ""):
            s = sent.strip(" -•*\t")
            if len(s) < 8:
                continue
            m = EXPLICIT_RE.match(s)
            if m:
                out.append({"owner": m.group(1).lower(), "description": _clean(m.group(2)),
                            "due_date": parse_due(s, now), "person": None})
                continue
            if ME_RE.search(s):
                out.append({"owner": "me", "description": _clean(s),
                            "due_date": parse_due(s, now), "person": None})
                continue
            person = next((n for n in attendee_names if re.search(
                r"\b" + re.escape(n.split()[0]) + r"\b.*\b(will|'ll|promised to|agreed to|is going to)\b",
                s, re.I)), None)
            if person or THEM_RE.search(s):
                out.append({"owner": "them", "description": _clean(s),
                            "due_date": parse_due(s, now), "person": person})
        return out


class ClaudeExtractor(RuleBasedExtractor):
    """Optional: higher-quality extraction via the Anthropic API (pip install anthropic,
    ANTHROPIC_API_KEY set). Any error -> falls back to rule-based extraction."""

    def __init__(self, model: str = "claude-sonnet-5"):
        self.model = model

    def _ask(self, prompt: str):
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=self.model, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}])
        return json.loads(msg.content[0].text)

    def commitments(self, text, attendee_names, now):
        try:
            data = self._ask(
                "Extract commitments from these meeting notes. Return ONLY a JSON array of "
                '{"owner":"me|them","description":str,"due_date":"YYYY-MM-DD or null","person":str or null}. '
                f"'me' is the note-taker. Attendees: {attendee_names}. Today: {now.date()}.\n\n{text}")
            return [d for d in data if d.get("owner") in ("me", "them") and d.get("description")]
        except Exception:
            return super().commitments(text, attendee_names, now)
