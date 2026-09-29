"""Post-meeting analysis: raw notes/transcript -> structured data for memory."""
from llm import chat_json

SYSTEM = """You are a meeting analyst for a professional's private assistant.
Extract facts ONLY from the notes. Never invent details. Return ONLY a JSON object:
{
  "summary": "2 sentence summary",
  "topics": ["..."],
  "decisions": ["..."],
  "commitments": [{"owner": "me | <contact name>", "task": "...", "due": "date or null"}],
  "unresolved_issues": ["..."],
  "preferences": ["communication style, format, timing, priorities of the contact"],
  "follow_ups": ["concrete next steps"],
  "resolved": ["items from PRIOR CONTEXT that this meeting closed or fulfilled"]
}
Use empty lists when nothing applies. "me" is the user who took the notes."""


def analyze_meeting(contact: dict, title: str, date: str, notes: str, prior_context: list[str] | None = None) -> dict:
    prior = "\n".join(f"- {m}" for m in (prior_context or [])) or "(none)"
    user = (
        f"CONTACT: {contact['name']}, {contact['role']} at {contact['company']}\n"
        f"MEETING: {title} on {date}\n\n"
        f"PRIOR CONTEXT (from memory):\n{prior}\n\n"
        f"MEETING NOTES:\n{notes}"
    )
    result = chat_json(SYSTEM, user)
    for key in ("topics", "decisions", "commitments", "unresolved_issues", "preferences", "follow_ups", "resolved"):
        result.setdefault(key, [])
    result.setdefault("summary", "")
    return result
