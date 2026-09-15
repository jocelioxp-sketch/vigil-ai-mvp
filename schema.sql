CREATE TABLE leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT,
  role TEXT,
  company TEXT,
  sector TEXT,
  company_size INTEGER,
  linkedin_url TEXT,
  security_interest TEXT,
  enrichment_summary TEXT,
  lead_score INTEGER DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'INSCRITO',
  attendance_confirmed INTEGER DEFAULT 0,
  attended INTEGER DEFAULT 0,
  demo_interest TEXT,
  meeting_scheduled INTEGER DEFAULT 0,
  meeting_datetime TEXT,
  consent_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  phase TEXT NOT NULL,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL,
  content TEXT NOT NULL,
  intent TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE agent_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  rationale TEXT NOT NULL,
  payload TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (lead_id) REFERENCES leads(id)
);
