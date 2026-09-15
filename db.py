import os
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vigil_ai.db")
engine = create_engine(DATABASE_URL, future=True)

LEADS_DDL = """
CREATE TABLE IF NOT EXISTS leads (
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
)
"""
INTERACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  phase TEXT NOT NULL,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL,
  content TEXT NOT NULL,
  intent TEXT,
  created_at TEXT NOT NULL
)
"""
ACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS agent_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  rationale TEXT NOT NULL,
  payload TEXT,
  created_at TEXT NOT NULL
)
"""

def init_db():
    with engine.begin() as conn:
        conn.execute(text(LEADS_DDL))
        conn.execute(text(INTERACTIONS_DDL))
        conn.execute(text(ACTIONS_DDL))


def now():
    return datetime.utcnow().isoformat(timespec="seconds")


def add_lead(data):
    ts = now()
    q = text("""
      INSERT INTO leads (name,email,phone,role,company,sector,company_size,linkedin_url,security_interest,consent_at,created_at,updated_at)
      VALUES (:name,:email,:phone,:role,:company,:sector,:company_size,:linkedin_url,:security_interest,:consent_at,:created_at,:updated_at)
    """)
    payload = {**data, "consent_at": ts, "created_at": ts, "updated_at": ts}
    with engine.begin() as conn:
        result = conn.execute(q, payload)
        return result.lastrowid


def list_leads():
    with engine.begin() as conn:
        return [dict(r._mapping) for r in conn.execute(text("SELECT * FROM leads ORDER BY id DESC")).fetchall()]


def get_lead(lead_id):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM leads WHERE id=:id"), {"id": lead_id}).fetchone()
        return dict(row._mapping) if row else None


def update_lead(lead_id, **fields):
    if not fields:
        return
    fields["updated_at"] = now()
    set_clause = ", ".join([f"{k}=:{k}" for k in fields])
    fields["id"] = lead_id
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE leads SET {set_clause} WHERE id=:id"), fields)


def add_interaction(lead_id, phase, channel, direction, content, intent=None):
    with engine.begin() as conn:
        conn.execute(text("""
          INSERT INTO interactions (lead_id,phase,channel,direction,content,intent,created_at)
          VALUES (:lead_id,:phase,:channel,:direction,:content,:intent,:created_at)
        """), {
            "lead_id": lead_id, "phase": phase, "channel": channel,
            "direction": direction, "content": content, "intent": intent,
            "created_at": now()
        })


def list_interactions(lead_id):
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT * FROM interactions WHERE lead_id=:id ORDER BY id"), {"id": lead_id}).fetchall()
        return [dict(r._mapping) for r in rows]


def add_action(lead_id, action_type, rationale, payload=""):
    with engine.begin() as conn:
        conn.execute(text("""
          INSERT INTO agent_actions (lead_id,action_type,rationale,payload,created_at)
          VALUES (:lead_id,:action_type,:rationale,:payload,:created_at)
        """), {"lead_id": lead_id, "action_type": action_type, "rationale": rationale, "payload": payload, "created_at": now()})
