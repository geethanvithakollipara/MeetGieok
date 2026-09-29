"""Storage backends: real Hindsight + an offline fallback with same interface."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Dict, List, Optional


class HindsightBackend:
    """Thin wrapper over the official `hindsight-client` (Vectorize Hindsight)."""

    def __init__(self, base_url: str):
        from hindsight_client import Hindsight  # imported lazily
        self.client = Hindsight(base_url=base_url)
        self._banks = set()

    def _ensure_bank(self, bank_id: str, name: str):
        if bank_id in self._banks:
            return
        try:  # ignore if bank exists / method differs by version
            self.client.create_bank(bank_id=bank_id, name=name)
        except Exception:
            pass
        self._banks.add(bank_id)

    def retain(self, bank_id: str, content: str, *, context: str = "",
               timestamp: Optional[datetime] = None,
               document_id: Optional[str] = None, name: str = "") -> None:
        self._ensure_bank(bank_id, name or bank_id)
        kwargs = dict(bank_id=bank_id, content=content, context=context)
        if timestamp:
            kwargs["timestamp"] = timestamp
        if document_id:
            kwargs["document_id"] = document_id
        self.client.retain(**kwargs)

    def recall(self, bank_id: str, query: str, top_k: int = 8) -> List[str]:
        self._ensure_bank(bank_id, bank_id)
        resp = self.client.recall(bank_id=bank_id, query=query, budget="mid")
        results = getattr(resp, "results", resp) or []
        texts = []
        for r in results[:top_k]:
            texts.append(r.get("text") if isinstance(r, dict) else getattr(r, "text", str(r)))
        return texts

    def clear(self, bank_id: str) -> None:
        try:
            self.client.delete_bank(bank_id=bank_id)
        except Exception:
            pass
        self._banks.discard(bank_id)


class LocalBackend:
    """Offline fallback so demo/tests run without a server or LLM key.

    Each bank is a separate list => same isolation guarantee as Hindsight banks.
    """

    _STOP = set("a an the and or of to in on for with is are was were we i he she it "
                "this that what who how about from by at as be do does did".split())

    def __init__(self):
        self.banks: Dict[str, List[str]] = {}

    @classmethod
    def _tokens(cls, s: str):
        return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in cls._STOP}

    def retain(self, bank_id, content, *, context="", timestamp=None,
               document_id=None, name=""):
        facts = self.banks.setdefault(bank_id, [])
        prefix = ""
        if document_id:  # upsert semantics, like Hindsight documents
            prefix = f"[{document_id}]"
            facts[:] = [f for f in facts if not f.startswith(prefix)]
        for line in content.splitlines():
            if line.strip():
                facts.append(f"{prefix} {line}".strip() if prefix else line)

    def recall(self, bank_id, query, top_k=8):
        facts = self.banks.get(bank_id, [])
        toks = [self._tokens(f) for f in facts]
        n = len(facts)
        q = self._tokens(query)
        if n >= 3:  # drop near-ubiquitous words (e.g. the contact's name)
            q = {w for w in q if sum(w in t for t in toks) < 0.6 * n}
        scored = [(len(q & t), f) for t, f in zip(toks, facts) if q & t]
        scored.sort(key=lambda x: -x[0])
        return [re.sub(r"^\[[^\]]*\]\s*", "", f) for _, f in scored[:top_k]]

    def clear(self, bank_id):
        self.banks.pop(bank_id, None)
