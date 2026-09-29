"""Public API: retain_memory() and recall_memory()."""
from __future__ import annotations
import os
from typing import Dict, List, Optional

from .backends import HindsightBackend, LocalBackend
from .models import Contact, MeetingRecord, contact_profile_text, meeting_to_text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_backend = None

# WHAT we recall before the next meeting -> one query per category.
RECALL_QUERIES: Dict[str, str] = {
    "commitments": "NOT DELIVERED outstanding promised deliver overdue {name}",
    "unresolved":  "UNRESOLVED open issue pending {name}",
    "preferences": "{name} prefers wants likes decision style preferences",
    "history":     "meeting discussed topics with {name}",
    "profile":     "{name} role works company",   # last: most generic
}


def _get_backend():
    global _backend
    if _backend is None:
        if os.getenv("MEMORY_BACKEND", "hindsight").lower() == "local":
            _backend = LocalBackend()
        else:
            try:
                _backend = HindsightBackend(os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888"))
            except Exception as e:  # missing package -> degrade gracefully
                print(f"[memory] Hindsight unavailable ({e}); using local fallback.")
                _backend = LocalBackend()
    return _backend


def reset_backend(backend=None):
    """Swap/reset backend (used by tests and demo)."""
    global _backend
    _backend = backend


def bank_id(contact: Contact) -> str:
    """One Hindsight memory bank per contact => hard isolation between contacts."""
    return f"{os.getenv('BANK_PREFIX', 'contact')}-{contact.slug}"


def retain_memory(contact: Contact, meeting: MeetingRecord) -> str:
    """Store a meeting in the contact's own Hindsight bank."""
    b, bid = _get_backend(), bank_id(contact)
    b.retain(bid, contact_profile_text(contact), context="contact profile",
             document_id=f"{contact.slug}-profile", name=contact.name)
    b.retain(bid, meeting_to_text(contact, meeting),
             context=f"meeting notes with {contact.name}",
             timestamp=meeting.timestamp(),
             document_id=f"{contact.slug}-meeting-{meeting.date}",
             name=contact.name)
    return bid


def recall_memory(contact: Contact, query: Optional[str] = None,
                  top_k: int = 6) -> Dict[str, List[str]]:
    """Recall what matters before the next meeting, grouped by category.

    Only ever queries this contact's bank, so nothing leaks across contacts.
    Pass `query` to do a single custom lookup instead.
    """
    b, bid = _get_backend(), bank_id(contact)
    queries = ({"custom": query} if query else
               {k: v.format(name=contact.name) for k, v in RECALL_QUERIES.items()})
    out: Dict[str, List[str]] = {}
    seen = set()
    for cat, q in queries.items():
        items = []
        for t in b.recall(bid, q, top_k=top_k):
            if t not in seen:
                seen.add(t)
                items.append(t)
        out[cat] = items
    return out
