-- Meeting Prep Agent schema (SQLite; portable to Postgres with minor type changes)
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  email         TEXT UNIQUE,
  api_key_hash  TEXT NOT NULL UNIQUE,
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  email       TEXT,
  company     TEXT,
  role        TEXT,
  notes       TEXT,
  created_at  TEXT NOT NULL,
  UNIQUE (user_id, email)
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id, name);

-- Personal / relationship details worth remembering (kids, hobbies, preferences...)
CREATE TABLE IF NOT EXISTS contact_facts (
  id          INTEGER PRIMARY KEY,
  contact_id  INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  category    TEXT NOT NULL DEFAULT 'general',
  fact        TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meetings (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  scheduled_at  TEXT NOT NULL,              -- ISO-8601 UTC
  duration_min  INTEGER NOT NULL DEFAULT 30,
  meeting_type  TEXT NOT NULL DEFAULT 'general',
  location      TEXT,
  agenda        TEXT,
  status        TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled','completed','cancelled')),
  summary       TEXT,
  notes         TEXT,
  sentiment     INTEGER CHECK (sentiment BETWEEN -2 AND 2),
  completed_at  TEXT,
  created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meetings_user_time ON meetings(user_id, scheduled_at);

CREATE TABLE IF NOT EXISTS meeting_attendees (
  meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  contact_id  INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  PRIMARY KEY (meeting_id, contact_id)
);
CREATE INDEX IF NOT EXISTS idx_attendees_contact ON meeting_attendees(contact_id);

CREATE TABLE IF NOT EXISTS meeting_topics (
  meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  topic       TEXT NOT NULL,
  PRIMARY KEY (meeting_id, topic)
);

-- Promises. owner='me' = you promised them; owner='them' = they promised you.
-- Lifecycle: open -> done | missed (auto, when past due) | cancelled.
-- A 'missed' item can still be completed later (status=done, completed_late=1).
CREATE TABLE IF NOT EXISTS commitments (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  meeting_id     INTEGER REFERENCES meetings(id) ON DELETE SET NULL,
  contact_id     INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  owner          TEXT NOT NULL CHECK (owner IN ('me','them')),
  description    TEXT NOT NULL,
  due_date       TEXT,
  status         TEXT NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open','done','missed','cancelled')),
  created_at     TEXT NOT NULL,
  completed_at   TEXT,
  missed_at      TEXT,
  completed_late INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_commit_contact ON commitments(contact_id, status);
CREATE INDEX IF NOT EXISTS idx_commit_due ON commitments(user_id, status, due_date);

-- Every generated brief is stored so feedback can be tied to what was shown.
CREATE TABLE IF NOT EXISTS briefs (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  meeting_id    INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  generated_at  TEXT NOT NULL,
  content       TEXT NOT NULL              -- JSON
);

CREATE TABLE IF NOT EXISTS brief_feedback (
  id          INTEGER PRIMARY KEY,
  brief_id    INTEGER NOT NULL REFERENCES briefs(id) ON DELETE CASCADE,
  section     TEXT NOT NULL,               -- section key, or '_length'
  useful      INTEGER,                     -- 1 / 0 / NULL
  comment     TEXT,
  created_at  TEXT NOT NULL
);

-- Learned + explicit preferences (JSON values). Keys: max_items, hidden_sections,
-- pinned_sections, style (learned meeting-style stats).
CREATE TABLE IF NOT EXISTS preferences (
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  key         TEXT NOT NULL,
  value       TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (user_id, key)
);

-- Per-section usefulness score (EMA in [0,1]) learned from brief feedback.
CREATE TABLE IF NOT EXISTS section_stats (
  user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  section  TEXT NOT NULL,
  score    REAL NOT NULL DEFAULT 0.5,
  samples  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, section)
);
