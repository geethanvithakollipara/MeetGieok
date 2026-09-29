"""Meeting prep generator: generic vs memory-personalized."""
from __future__ import annotations
from typing import Dict, List
from .models import Contact


def generic_prep(contact: Contact) -> str:
    return (f"Prep for meeting with {contact.name}:\n"
            "  - Introduce yourself and the agenda\n"
            "  - Ask about their goals\n"
            "  - Share product overview\n"
            "  - Agree on next steps")


def personalized_prep(contact: Contact, mem: Dict[str, List[str]]) -> str:
    def block(title, key):
        items = mem.get(key) or []
        return [f"  {title}"] + [f"    - {i}" for i in items] if items else []

    lines = [f"Prep for meeting with {contact.name}:"]
    lines += block("Follow up first (undelivered):", "commitments")
    lines += block("Unresolved topics to close:", "unresolved")
    lines += block("How they like to work:", "preferences")
    lines += block("Last time:", "history")
    lines += block("Profile:", "profile")
    return "\n".join(lines) if len(lines) > 1 else generic_prep(contact)
