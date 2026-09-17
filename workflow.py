"""Executable timed rules. No real channel sends. One current window per lead."""
import os
import threading
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import db
from agent import send_simulated, eligible

RULES=[('T14',-14),('T7',-7),('T3',-3),('T1',-1),('T0',0),('D0',0),('D1',1),('D3',3),('D7',7)]


def parse_date(value):
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('A data precisa incluir fuso, ex.: -03:00.')
    return dt


def due_rule(lead,clock,event):
    delta=(clock-event).total_seconds()/86400
    if delta < -14 or delta>=8:
        return None
    if delta<0:
        key=next(k for k,b in reversed(RULES[:4]) if delta>=b)
        phase='PRE_EVENTO'
    elif delta<8/24:
        key='T0'; phase='PRE_EVENTO'
    else:
        phase='POS_EVENTO'
        key='D7' if delta>=7 else 'D3' if delta>=3 else 'D1' if delta>=1 else 'D0'
        if key=='D0' and not lead['attended']:
            return None
    try: eligible(lead,phase)
    except ValueError: return None
    if phase=='POS_EVENTO' and lead['status']=='NAO_COMPARECERA':
        return None
    # Already confirmed leads only receive logistics near the event.
    if phase=='PRE_EVENTO' and lead['attendance_confirmed'] and key in ('T14','T7','T3'):
        return None
    return key,phase


def run_due(clock,event,simulated=False):
    if clock.tzinfo is None or event.tzinfo is None:
        raise ValueError('Relógio e evento devem ter fuso.')
    event_key=('DEMO:' if simulated else 'LIVE:')+event.isoformat()
    outcomes=[]
    for lead in db.list_leads():
        if simulated and not lead['synthetic']:
            continue
        rule=due_rule(lead,clock,event)
        if not rule: continue
        key,phase=rule
        with db.transaction() as c:
            found=c.execute(text('SELECT * FROM deliveries WHERE lead_id=:lead AND event_key=:event AND rule_key=:rule'),{'lead':lead['id'],'event':event_key,'rule':key}).mappings().first()
            if found:
                if found['status']=='SENT' or found['attempts']>=3:
                    continue
                age=datetime.now(timezone.utc)-parse_date(found['updated_at'])
                if age<timedelta(minutes=5):
                    continue
                delivery=found['id']
                c.execute(text("UPDATE deliveries SET status='PROCESSING',attempts=attempts+1,updated_at=:ts WHERE id=:id"),{'ts':db.now(),'id':delivery})
            else:
                result=c.execute(text("INSERT INTO deliveries(lead_id,event_key,rule_key,status,updated_at) VALUES(:lead,:event,:rule,'PROCESSING',:ts)"),{'lead':lead['id'],'event':event_key,'rule':key,'ts':db.now()})
                delivery=result.lastrowid
        try:
            send_simulated(lead,phase,step=key,delivery=delivery)
            outcomes.append({'lead':lead['name'],'etapa':key,'resultado':'Registrada (canal simulado)'})
        except Exception as e:
            # No raw API/credential errors exposed in shared UI.
            reason=type(e).__name__
            with db.transaction() as c:
                c.execute(text("UPDATE deliveries SET status='FAILED',error=:error,updated_at=:ts WHERE id=:id AND status!='SENT'"),{'error':reason,'ts':db.now(),'id':delivery})
            outcomes.append({'lead':lead['name'],'etapa':key,'resultado':'Falha; tentativa limitada após 5 minutos.'})
    return outcomes


def start_worker():
    stop=threading.Event()
    def work():
        while not stop.wait(60):
            try:
                event=db.setting('event_at')
                if event and db.setting('automation_enabled')=='1':
                    run_due(datetime.now(timezone.utc),parse_date(event))
            except Exception:
                logging.exception('Falha no ciclo de workflow')
    thread=threading.Thread(target=work,daemon=True,name='vigil-workflow')
    thread.start()
    return stop

if __name__=='__main__':
    import time
    db.init_db()
    start_worker()
    while True: time.sleep(60)
