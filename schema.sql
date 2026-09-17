CREATE TABLE IF NOT EXISTS leads (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone TEXT, role TEXT, company TEXT,
 sector TEXT, company_size INTEGER, linkedin_url TEXT, security_interest TEXT,
 enrichment_summary TEXT, lead_score INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'INSCRITO',
 attendance_confirmed INTEGER DEFAULT 0, attended INTEGER DEFAULT 0, demo_interest TEXT,
 meeting_scheduled INTEGER DEFAULT 0, meeting_datetime TEXT, consent_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 suppressed INTEGER NOT NULL DEFAULT 0, consent_source TEXT NOT NULL DEFAULT 'legacy',
 synthetic INTEGER NOT NULL DEFAULT 0, enriched_at TEXT, enrichment_kind TEXT,
 source_json TEXT, source_qid TEXT, review_required INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS interactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
 phase TEXT NOT NULL, channel TEXT NOT NULL, direction TEXT NOT NULL, content TEXT NOT NULL,
 intent TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_actions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
 action_type TEXT NOT NULL, rationale TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deliveries (
 id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
 event_key TEXT NOT NULL, rule_key TEXT NOT NULL, status TEXT NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 1, error TEXT, updated_at TEXT NOT NULL,
 UNIQUE(lead_id, event_key, rule_key)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
