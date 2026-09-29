# Meeting Prep Agent - backend

Remembers every meeting per contact (what was discussed, what was promised, what was missed) and
produces a pre-meeting brief shaped by what it has learned about how *you* prepare.

Zero dependencies (Python 3.10+ stdlib, SQLite). `python -m unittest discover -s tests` to test.

## Run
    MPA_ADMIN_TOKEN=secret python -m meeting_prep        # serves :8000, DB in ./meeting_prep.db
    curl -XPOST :8000/users -H 'X-Admin-Token: secret' -d '{"name":"Alex"}'   # returns your api_key

Send `X-API-Key: <key>` on every other request. All data is scoped per user.

## Architecture
    api.py        HTTP routing, auth, error mapping (swap for FastAPI/Flask - handlers are thin)
    services.py   contacts, meetings, commitments, relationship stats, search
    extract.py    notes -> topics + commitments (rule-based; ClaudeExtractor optional drop-in)
    learning.py   preference + meeting-style learning, section ordering/hiding
    briefing.py   brief generation + markdown rendering
    schema.sql    12 tables: users, contacts, contact_facts, meetings, meeting_attendees,
                  meeting_topics, commitments, briefs, brief_feedback, preferences, section_stats

## Business rules
- **Commitments** have an owner (`me` you promised / `them` they promised) and a due date
  (date-only = end of day). Open + past due => `missed` automatically (sweep runs on brief
  generation and when listing). Completing a missed item marks it `done`, `completed_late=1`.
- **Reliability**: on-time rate per owner per contact, shown only after 3+ tracked items.
- **Closing a meeting** (`POST /meetings/{id}/complete`) stores summary/notes/sentiment(-2..2),
  topics (given or extracted), and commitments (given + extracted from notes:
  "I'll ... by Friday" -> me; "Priya will ..." / "they'll ..." -> them; `ACTION (me|them): ...`).
- **Brief sections** (empty ones dropped): flags, missed, open_mine, open_theirs, last_time,
  suggested agenda (time-boxed), recurring_topics, personal notes, history.
  Flags: first meeting, overdue-for-contact vs. usual cadence, low reliability, negative trend.
- **Learning**: feedback `{section, useful}` moves a per-section score (EMA, alpha 0.3).
  Sections with 4+ votes and score < 0.25 are hidden; others are ordered by score; `pinned_sections`
  go first. `flags`, `missed`, `open_mine` are protected (never hidden/demoted) so accountability
  items can't be tuned away. `{length: too_long|too_short}` adjusts `max_items` (2-10).
  Meeting style (avg duration, typical type/hour) is learned on every completed meeting and
  sets agenda time-boxes.

## API
    POST /users (admin)             GET/POST /contacts   GET/PATCH /contacts/{id}
    POST /contacts/{id}/facts       GET /contacts/{id}/timeline
    POST /meetings                  GET /meetings?upcoming=1&contact_id=
    POST /meetings/{id}/complete    POST /meetings/{id}/cancel
    POST /meetings/{id}/brief       GET /meetings/{id}/brief[?format=markdown]
    POST /briefs/{id}/feedback      GET/PUT /preferences
    GET/POST /commitments[?status=&owner=&contact_id=]   POST /commitments/{id}/complete|cancel
    GET /search?q=

## Next steps for production
Postgres (schema ports directly), calendar sync (Google/Outlook) to auto-create meetings and
trigger briefs N minutes before start, `ClaudeExtractor` for better extraction, rate limiting/TLS.
