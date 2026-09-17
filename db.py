"""SQLite MVP: schema único, migração transacional e estados protegidos."""
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///vigil_ai.db')
if not DATABASE_URL.startswith('sqlite:'):
    raise RuntimeError('Este MVP suporta SQLite. PostgreSQL exige migração específica.')
engine = create_engine(DATABASE_URL, future=True, connect_args={'timeout': 30, 'check_same_thread': False})

@event.listens_for(engine, 'connect')
def sqlite_setup(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=30000')

@contextmanager
def transaction():
    with engine.connect() as conn:
        conn.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def init_db():
    with transaction() as c:
        if c.exec_driver_sql('PRAGMA user_version').scalar() >= 2:
            return
        statements = [s.strip() for s in Path(__file__).with_name('schema.sql').read_text().split(';') if s.strip()]
        for statement in statements:
            c.exec_driver_sql(statement)
        columns = {r[1] for r in c.exec_driver_sql('PRAGMA table_info(leads)')}
        additions = {'suppressed':'INTEGER NOT NULL DEFAULT 0', 'consent_source':"TEXT NOT NULL DEFAULT 'legacy'",
                     'synthetic':'INTEGER NOT NULL DEFAULT 0', 'enriched_at':'TEXT', 'enrichment_kind':'TEXT',
                     'source_json':'TEXT', 'source_qid':'TEXT', 'review_required':'INTEGER NOT NULL DEFAULT 0'}
        for col, definition in additions.items():
            if col not in columns:
                c.exec_driver_sql(f'ALTER TABLE leads ADD COLUMN {col} {definition}')
        # Preserve all existing rows. An orphan causes rollback instead of silent loss.
        for table in ('interactions', 'agent_actions'):
            if not list(c.exec_driver_sql(f'PRAGMA foreign_key_list({table})')):
                ddl = next(s for s in statements if s.startswith(f'CREATE TABLE IF NOT EXISTS {table} '))
                c.exec_driver_sql(ddl.replace(f'IF NOT EXISTS {table}', f'{table}_migration'))
                c.exec_driver_sql(f'INSERT INTO {table}_migration SELECT * FROM {table}')
                c.exec_driver_sql(f'DROP TABLE {table}')
                c.exec_driver_sql(f'ALTER TABLE {table}_migration RENAME TO {table}')
        c.exec_driver_sql("UPDATE leads SET suppressed=1 WHERE status='OPT_OUT'")
        c.exec_driver_sql("UPDATE leads SET attendance_confirmed=0 WHERE status='NAO_COMPARECERA'")
        c.exec_driver_sql("UPDATE leads SET synthetic=1, consent_source='synthetic_demo' WHERE email LIKE '%.demo' OR email LIKE '%@example.invalid'")
        # Previous declaration-only summaries must be regenerated with explicit provenance.
        c.exec_driver_sql('PRAGMA user_version=2')

def rows(query, params=None):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(query), params or {})]

def list_leads():
    return rows('SELECT * FROM leads ORDER BY id DESC')

def get_lead(lead_id, conn=None):
    if conn is not None:
        r = conn.execute(text('SELECT * FROM leads WHERE id=:id'), {'id':lead_id}).mappings().first()
        if not r:
            raise ValueError('Lead não encontrado.')
        return dict(r)
    found = rows('SELECT * FROM leads WHERE id=:id', {'id':lead_id})
    if not found:
        raise ValueError('Lead não encontrado.')
    return found[0]

def add_lead(data):
    fields = ['name','email','phone','role','company','sector','company_size','linkedin_url','security_interest']
    payload = {k:data.get(k) for k in fields}
    payload['name'] = (payload['name'] or '').strip()
    payload['email'] = (payload['email'] or '').strip().lower()
    if not payload['name'] or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', payload['email']):
        raise ValueError('Informe nome e e-mail válido.')
    synthetic = bool(data.get('synthetic'))
    if synthetic and not payload['email'].endswith(('@example.invalid','.demo')):
        raise ValueError('Use example.invalid para uma persona sintética.')
    if not synthetic and not data.get('consent'):
        raise ValueError('Consentimento explícito obrigatório.')
    for k,v in payload.items():
        if isinstance(v,str) and len(v)>1000:
            raise ValueError('Campo muito longo.')
    payload.update(synthetic=int(synthetic),consent_source='synthetic_demo' if synthetic else 'form_v2',
                   consent_at=now(), created_at=now(),updated_at=now())
    with transaction() as c:
        keys=','.join(payload)
        result=c.execute(text(f"INSERT INTO leads ({keys}) VALUES ({','.join(':'+k for k in payload)})"),payload)
        return result.lastrowid

def _update(c, lead_id, fields):
    fields={**fields,'updated_at':now()}
    c.execute(text('UPDATE leads SET '+','.join(k+'=:'+k for k in fields)+' WHERE id=:id'),{**fields,'id':lead_id})

def action(c, lead_id, kind, rationale, payload=''):
    c.execute(text('INSERT INTO agent_actions(lead_id,action_type,rationale,payload,created_at) VALUES(:id,:kind,:why,:payload,:ts)'),
              {'id':lead_id,'kind':kind,'why':rationale,'payload':payload,'ts':now()})

def add_action(lead_id, action_type, rationale, payload=''):
    with transaction() as c:
        action(c,lead_id,action_type,rationale,payload)

def update_lead(lead_id, **fields):
    # Compatibility only for non-state profile fields. State mutations use dedicated services.
    allowed={'name','phone','role','company','sector','company_size','linkedin_url','security_interest'}
    if not set(fields)<=allowed:
        raise ValueError('Use as transições de domínio para atualizar o funil.')
    with transaction() as c:
        _update(c,lead_id,fields)

def save_enrichment(lead_id, summary, score, kind, source, qid=None):
    with transaction() as c:
        lead=get_lead(lead_id,c)
        fields=dict(enrichment_summary=summary,lead_score=score,enriched_at=now(),enrichment_kind=kind,
                    source_json=json.dumps(source,ensure_ascii=False),source_qid=qid)
        if lead['status']=='INSCRITO':
            fields['status']='ENRIQUECIDO'
        _update(c,lead_id,fields)
        action(c,lead_id,'ENRICHMENT','Dados declarados separados da fonte externa.',json.dumps(source,ensure_ascii=False))

def suppress(lead_id):
    with transaction() as c:
        _update(c,lead_id,{'suppressed':1,'status':'OPT_OUT','review_required':0})
        action(c,lead_id,'OPT_OUT','Comunicações bloqueadas independentemente do estado comercial.')

def apply_intent(c, lead_id, intent, confidence):
    lead=get_lead(lead_id,c)
    if intent=='OPT_OUT':
        _update(c,lead_id,dict(suppressed=1,status='OPT_OUT',review_required=0))
    elif lead['suppressed'] or lead['meeting_scheduled']:
        return
    elif confidence<0.8 or intent in ('DUVIDA','OUTRO'):
        _update(c,lead_id,{'review_required':1})
    elif intent=='RECUSA':
        _update(c,lead_id,dict(attendance_confirmed=0,status='NAO_COMPARECERA',review_required=0))
    elif intent=='CONFIRMA':
        _update(c,lead_id,dict(attendance_confirmed=1,status='PRESENTE' if lead['attended'] else 'CONFIRMADO',review_required=0))
    elif intent=='INTERESSE_REUNIAO':
        _update(c,lead_id,dict(status='FOLLOW_UP_QUENTE',review_required=0))

def save_context(lead_id, attended, interest):
    with transaction() as c:
        lead=get_lead(lead_id,c)
        status=lead['status']
        if not lead['suppressed'] and not lead['meeting_scheduled'] and status not in ('FOLLOW_UP_QUENTE', 'NAO_COMPARECERA'):
            status='PRESENTE' if attended else ('CONFIRMADO' if lead['attendance_confirmed'] else 'ENRIQUECIDO' if lead['enriched_at'] else 'INSCRITO')
        _update(c,lead_id,dict(attended=int(attended),demo_interest=interest[:1000],status=status))
        action(c,lead_id,'EVENT_CONTEXT','Presença e interesse registrados pelo operador.')

def schedule_meeting(lead_id, when):
    dt=datetime.fromisoformat(when)
    if dt.tzinfo is None or dt<=datetime.now(timezone.utc):
        raise ValueError('Informe data futura com fuso, ex.: 2026-10-20T14:00:00-03:00.')
    with transaction() as c:
        lead=get_lead(lead_id,c)
        if lead['review_required']:
            raise ValueError('Esclareça a resposta pendente antes de registrar a reunião.')
        if lead['suppressed'] or lead['status']!='FOLLOW_UP_QUENTE':
            raise ValueError('É necessário interesse em reunião e ausência de opt-out.')
        _update(c,lead_id,dict(meeting_scheduled=1,meeting_datetime=dt.isoformat(),status='REUNIAO_AGENDADA'))
        action(c,lead_id,'MEETING','Reunião registrada manualmente; sem convite externo.',dt.isoformat())

def list_interactions(lead_id):
    return rows('SELECT * FROM interactions WHERE lead_id=:id ORDER BY id',{'id':lead_id})

def list_actions(lead_id):
    return rows('SELECT * FROM agent_actions WHERE lead_id=:id ORDER BY id',{'id':lead_id})

def setting(key, default=''):
    result=rows('SELECT value FROM settings WHERE key=:key',{'key':key})
    return result[0]['value'] if result else default

def set_setting(key,value):
    with transaction() as c:
        c.execute(text('INSERT INTO settings(key,value) VALUES(:key,:value) ON CONFLICT(key) DO UPDATE SET value=excluded.value'),{'key':key,'value':value})


def anonymize_lead(lead_id):
    """Remove identifying content from the lead and its histories; keep anonymous counts."""
    with transaction() as c:
        get_lead(lead_id,c)
        _update(c,lead_id,dict(name='Registro anonimizado',email=f'erased-{lead_id}@example.invalid',phone=None,
                 role=None,company=None,sector=None,company_size=None,linkedin_url=None,security_interest=None,
                 enrichment_summary=None,source_json=None,source_qid=None,demo_interest=None,meeting_datetime=None,
                 consent_at=None,consent_source='withdrawn',suppressed=1,status='OPT_OUT'))
        c.execute(text("UPDATE interactions SET content='[conteúdo removido]' WHERE lead_id=:id"),{'id':lead_id})
        c.execute(text("UPDATE agent_actions SET rationale='[conteúdo removido]', payload='' WHERE lead_id=:id"),{'id':lead_id})
        action(c,lead_id,'ANONYMIZE','Dados identificadores removidos; comunicações bloqueadas.')


def reserve_llm_call():
    key='llm_calls:'+now()[:10]
    with transaction() as c:
        raw=c.execute(text('SELECT value FROM settings WHERE key=:key'),{'key':key}).scalar()
        count=int(raw or 0)
        if count>=int(os.getenv('MAX_LLM_CALLS_PER_DAY','200')):
            raise ValueError('Limite diário de chamadas de IA atingido.')
        c.execute(text('INSERT INTO settings(key,value) VALUES(:key,:value) ON CONFLICT(key) DO UPDATE SET value=excluded.value'),{'key':key,'value':str(count+1)})
