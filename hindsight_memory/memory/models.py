"""Data models + the decision of WHAT gets stored from a meeting."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Contact:
    name: str
    role: str = ""
    company: str = ""

    @property
    def slug(self) -> str:
        # Company is part of the identity so two "Sarah"s never collide.
        raw = f"{self.name}-{self.company}".lower()
        return "".join(c if c.isalnum() else "-" for c in raw).strip("-")


@dataclass
class MeetingRecord:
    date: str                                   # ISO date, e.g. "2026-09-01"
    topics: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    promises_made: List[str] = field(default_factory=list)      # user promised
    promises_delivered: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    @property
    def undelivered(self) -> List[str]:
        done = {p.lower() for p in self.promises_delivered}
        return [p for p in self.promises_made if p.lower() not in done]

    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.date)


def contact_profile_text(c: Contact) -> str:
    parts = [f"{c.name} is a contact."]
    if c.role:
        parts.append(f"{c.name}'s role is {c.role}.")
    if c.company:
        parts.append(f"{c.name} works at {c.company}.")
    return " ".join(parts)


def meeting_to_text(c: Contact, m: MeetingRecord) -> str:
    """Turn a meeting into self-contained sentences.

    Hindsight extracts facts with an LLM, so full natural sentences that
    always name the person retrieve far better than terse bullet fragments.
    """
    lines = [f"Meeting with {c.name} on {m.date}."]
    lines += [f"We discussed {t}." for t in m.topics]
    lines += [f"{c.name} {p}." for p in m.preferences]
    lines += [f"I promised {c.name}: {p}." for p in m.promises_made]
    lines += [f"I delivered to {c.name}: {p}." for p in m.promises_delivered]
    lines += [f"NOT DELIVERED yet to {c.name}: {p} (still outstanding)."
              for p in m.undelivered]
    lines += [f"UNRESOLVED with {c.name}: {u}." for u in m.unresolved]
    if m.notes:
        lines.append(m.notes)
    return "\n".join(lines)
