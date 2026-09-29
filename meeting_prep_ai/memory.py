"""Memory layer: Hindsight (primary) with a local JSON fallback.

One Hindsight *memory bank per contact* keeps recall clean and isolated.
Hindsight extracts facts/entities on retain and runs semantic + keyword +
graph + temporal search on recall.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import config


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class HindsightBackend:
    name = "hindsight"

    def __init__(self, prefix: str):
        from hindsight_client import Hindsight

        kwargs = {"base_url": config.HINDSIGHT_BASE_URL}
        if config.HINDSIGHT_API_KEY:
            kwargs["api_key"] = config.HINDSIGHT_API_KEY
        self.client = Hindsight(**kwargs)
        self.prefix = prefix
        # Fails fast if the server is unreachable -> caller falls back to local
        self.client.recall(bank_id=f"{prefix}-healthcheck", query="ping")

    def _bank(self, contact: str) -> str:
        return f"{self.prefix}-{slug(contact)}"

    def retain(self, contact: str, text: str, context: str, date: str):
        kwargs = dict(bank_id=self._bank(contact), content=text, context=context)
        try:
            self.client.retain(timestamp=datetime.fromisoformat(date), **kwargs)
        except TypeError:
            self.client.retain(**kwargs)

    def recall(self, contact: str, query: str, limit: int = 8):
        res = self.client.recall(bank_id=self._bank(contact), query=query)
        return [r.text for r in res.results[:limit]]


class LocalBackend:
    name = "local (JSON fallback)"

    def __init__(self, prefix: str):
        self.path = Path(f".memory_{prefix}.json")
        self.items = json.loads(self.path.read_text()) if self.path.exists() else []

    def retain(self, contact: str, text: str, context: str, date: str):
        self.items.append({"contact": contact, "text": text, "context": context, "date": date})
        self.path.write_text(json.dumps(self.items, indent=1))

    def recall(self, contact: str, query: str, limit: int = 8):
        words = set(re.findall(r"\w{4,}", query.lower()))
        pool = [i for i in self.items if i["contact"] == contact]

        def score(i):
            overlap = len(words & set(re.findall(r"\w{4,}", i["text"].lower())))
            return (overlap, i["date"])

        return [f"[{i['date']}] {i['text']}" for i in sorted(pool, key=score, reverse=True)[:limit]]


RECALL_QUERIES = [
    "What have we discussed in previous meetings and what was decided?",
    "What commitments or promises were made, by whom, and are they still open?",
    "What unresolved issues, objections or concerns does this person have?",
    "What are this person's preferences, communication style and priorities?",
    "What follow-ups were planned or missed?",
]


class MemoryLayer:
    def __init__(self, prefix: str | None = None):
        prefix = prefix or config.BANK_PREFIX
        self.backend = None
        if config.MEMORY_BACKEND == "hindsight":
            try:
                self.backend = HindsightBackend(prefix)
            except Exception as e:
                print(f"[memory] Hindsight unavailable ({type(e).__name__}: {e}). Using local fallback.")
        if self.backend is None:
            self.backend = LocalBackend(prefix)

    @property
    def name(self) -> str:
        return self.backend.name

    def store_analysis(self, contact: str, date: str, title: str, a: dict):
        """Pass the extracted meeting analysis into memory (2 retains/meeting)."""

        def j(key):
            v = a.get(key) or []
            return "; ".join(x if isinstance(x, str) else json.dumps(x) for x in v) or "none"

        commitments = "; ".join(
            f"{c.get('owner', '?')} will {c.get('task', '')} (due {c.get('due') or 'unspecified'})"
            for c in a.get("commitments", [])
        ) or "none"

        record = (
            f"Meeting '{title}' with {contact} on {date}. Summary: {a.get('summary', '')} "
            f"Topics: {j('topics')}. Decisions: {j('decisions')}. "
            f"Commitments made: {commitments}. "
            f"Unresolved issues: {j('unresolved_issues')}. "
            f"Follow-ups: {j('follow_ups')}. "
            f"Previously open items resolved in this meeting: {j('resolved')}."
        )
        self.backend.retain(contact, record, "meeting record", date)

        prefs = a.get("preferences") or []
        if prefs:
            text = f"Preferences and style of {contact}, observed on {date}: " + "; ".join(prefs)
            self.backend.retain(contact, text, "contact preferences", date)

    def recall_context(self, contact: str, per_query: int = 5) -> list[str]:
        seen, out = set(), []
        for q in RECALL_QUERIES:
            for m in self.backend.recall(contact, f"{contact}: {q}", limit=per_query):
                key = m.strip().lower()
                if key not in seen:
                    seen.add(key)
                    out.append(m)
        return out
