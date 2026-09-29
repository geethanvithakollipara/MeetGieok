"""Pre-meeting brief: Current Meeting + Relevant Memories + Contact Context."""
from llm import chat_json

SYSTEM = """You are an elite executive assistant preparing the user for an upcoming meeting.
You receive (1) the current meeting, (2) contact context, (3) memories recalled from past
meetings with this contact. Ground EVERYTHING in the memories. Rules:
- Only use memories about the named contact; ignore anything else.
- Mention specific past facts (dates, numbers, names, promises) so the user feels prepared.
- Open commitments = promised but NOT yet fulfilled. Flag anything overdue or missed.
- Adapt tone/format advice to the contact's known preferences.
- If there are NO memories, say so plainly and give only generic, clearly-labelled suggestions.
Return ONLY a JSON object:
{
  "previous_context": ["..."],
  "open_commitments": [{"owner": "me | contact", "item": "...", "status_note": "e.g. overdue since ..."}],
  "unresolved_issues": ["..."],
  "suggested_questions": ["..."],
  "talking_points": ["..."],
  "potential_followups": ["..."],
  "personalization_note": "one line on how to run this meeting given their preferences"
}
Keep each list to at most 5 short, specific items."""


def generate_brief(contact: dict, meeting: dict, memories: list[str]) -> dict:
    mem = "\n".join(f"{i+1}. {m}" for i, m in enumerate(memories)) or "(NO MEMORIES - first interaction)"
    user = (
        f"CURRENT MEETING: {meeting['title']} on {meeting['date']}\n"
        f"Agenda: {meeting['agenda']}\n\n"
        f"CONTACT CONTEXT: {contact['name']}, {contact['role']} at {contact['company']}. "
        f"{contact.get('background', '')}\n\n"
        f"RELEVANT MEMORIES:\n{mem}"
    )
    return chat_json(SYSTEM, user)


SECTIONS = [
    ("previous_context", "PREVIOUS CONTEXT"),
    ("open_commitments", "OPEN COMMITMENTS"),
    ("unresolved_issues", "UNRESOLVED ISSUES"),
    ("suggested_questions", "SUGGESTED QUESTIONS"),
    ("talking_points", "TALKING POINTS"),
    ("potential_followups", "POTENTIAL FOLLOW-UPS"),
]


def render_brief(brief: dict) -> str:
    lines = []
    for key, title in SECTIONS:
        lines.append(f"\n{title}")
        items = brief.get(key) or ["-"]
        for it in items:
            if isinstance(it, dict):
                it = f"[{it.get('owner', '?')}] {it.get('item', '')} {('- ' + it['status_note']) if it.get('status_note') else ''}"
            lines.append(f"  * {it}")
    if brief.get("personalization_note"):
        lines.append(f"\nHOW TO RUN THIS MEETING\n  {brief['personalization_note']}")
    return "\n".join(lines)
