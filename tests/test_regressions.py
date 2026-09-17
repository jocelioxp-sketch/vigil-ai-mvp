import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import create_engine, text, event
import db
import agent
import enrichment
import workflow

class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=db.engine
        db.engine=create_engine('sqlite:///'+self.tmp.name+'/test.db',connect_args={'check_same_thread':False})
        event.listen(db.engine,'connect',db.sqlite_setup)
        db.init_db()
        self.lead=db.add_lead(dict(name='Persona Teste',email='test@example.invalid',role='CTO',company='Empresa',sector='Tecnologia',company_size=300,security_interest='SOC 2',synthetic=True))
    def tearDown(self):
        db.engine.dispose(); db.engine=self.old; self.tmp.cleanup()
    def current(self): return db.get_lead(self.lead)
    def enrich(self): return enrichment.enrich(self.lead)
    def mock_client(self,payload):
        return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])))
    def reply(self,intent,confidence=1):
        with patch.object(agent,'classify_reply',return_value=dict(intent=intent,confidence=confidence,next_action='teste')):
            return agent.receive_reply(self.current(),'texto de teste')
    def test_01_precondition(self):
        with patch.object(agent,'generate_message') as generate:
            with self.assertRaises(ValueError): agent.send_simulated(self.current(),'PRE_EVENTO')
            generate.assert_not_called()
    def test_02_opt_out_without_api(self):
        with patch.object(agent,'_client') as client:
            result=agent.receive_reply(self.current(),'Por favor, não me envie mais mensagens.')
            self.assertEqual(result['intent'],'OPT_OUT');client.assert_not_called()
        self.assertTrue(self.current()['suppressed'])
    def test_03_suppression_survives_context(self):
        self.enrich();db.suppress(self.lead)
        with self.assertRaises(ValueError): self.enrich()
        db.save_context(self.lead,True,'SOC 2')
        self.assertEqual(self.current()['status'],'OPT_OUT')
        with self.assertRaises(ValueError): agent.send_simulated(self.current(),'POS_EVENTO')
    def test_04_confirm_then_decline(self):
        self.reply('CONFIRMA');self.reply('RECUSA')
        self.assertEqual(self.current()['attendance_confirmed'],0)
    def test_05_low_confidence(self):
        self.reply('CONFIRMA',0.01)
        self.assertFalse(self.current()['attendance_confirmed']);self.assertTrue(self.current()['review_required'])
    def test_06_reenrichment_preserves_meeting(self):
        self.enrich();self.reply('INTERESSE_REUNIAO')
        db.schedule_meeting(self.lead,(datetime.now(timezone.utc)+timedelta(days=30)).isoformat())
        self.enrich();db.save_context(self.lead,True,'interesse')
        self.assertEqual(self.current()['status'],'REUNIAO_AGENDADA')
    def test_07_meeting_validation(self):
        self.reply('INTERESSE_REUNIAO')
        for value in ['garbage','2020-01-01T10:00:00-03:00','2029-01-01 10:00']:
            with self.assertRaises(ValueError): db.schedule_meeting(self.lead,value)
    def test_08_foreign_keys(self):
        with db.engine.connect() as c:
            self.assertEqual(len(list(c.exec_driver_sql('PRAGMA foreign_key_list(interactions)'))),1)
        with self.assertRaises(Exception): db.add_action(999,'TEST','invalid')
    def test_09_invalid_email(self):
        with self.assertRaises(ValueError):db.add_lead(dict(name='x',email='invalid',synthetic=True))
    def test_10_history_intent(self):
        self.reply('CONFIRMA');self.assertEqual(db.list_interactions(self.lead)[0]['intent'],'CONFIRMA')
    def test_11_failure_pauses(self):
        self.enrich()
        with patch.object(agent,'classify_reply',side_effect=RuntimeError('API down')):
            agent.receive_reply(self.current(),'talvez')
        self.assertTrue(self.current()['review_required'])
        self.assertEqual(len(db.list_interactions(self.lead)),1)
    def test_12_provenance(self):
        source=dict(qid='Q2283',company_label='Microsoft',description='empresa de tecnologia',source_url='https://www.wikidata.org/wiki/Special:EntityData/Q2283.json')
        with patch.object(enrichment,'fetch_company',return_value=source):
            enrichment.enrich(self.lead,'Q2283',True)
        self.assertEqual(self.current()['enrichment_kind'],'PUBLIC_COMPANY')
        self.assertEqual(json.loads(self.current()['source_json'])['qid'],'Q2283')
    def test_13_public_failure_no_fake(self):
        with patch.object(enrichment,'fetch_company',side_effect=OSError()):
            with self.assertRaises(OSError):enrichment.enrich(self.lead,'Q2283',True)
        self.assertIsNone(self.current()['enriched_at'])
    def test_14_source_no_arbitrary_url(self):
        with self.assertRaises(ValueError): enrichment.fetch_company('http://127.0.0.1')
    def test_15_idempotent_rule(self):
        self.enrich();date=datetime(2026,10,20,9,tzinfo=timezone.utc)
        with patch.object(agent,'generate_message',return_value='Mensagem de teste'):
            first=workflow.run_due(date-timedelta(days=7),date,True)
            second=workflow.run_due(date-timedelta(days=7),date,True)
        self.assertEqual(len(first),1);self.assertEqual(second,[])
        self.assertEqual(len(db.list_interactions(self.lead)),1)
    def test_16_due_conditions(self):
        self.enrich(); date=datetime(2026,10,20,9,tzinfo=timezone.utc)
        self.reply('CONFIRMA')
        self.assertIsNone(workflow.due_rule(self.current(),date-timedelta(days=7),date))
        self.assertEqual(workflow.due_rule(self.current(),date-timedelta(days=1),date)[0],'T1')
        db.suppress(self.lead)
        self.assertIsNone(workflow.due_rule(self.current(),date+timedelta(days=3),date))
    def test_17_message_no_hallucination(self):
        self.enrich()
        with patch.object(agent,'_client',return_value=self.mock_client({'topic_index':0,'invented':'clientes globais'})):
            msg=agent.generate_message(self.current(),'POS_EVENTO')
        self.assertNotIn('clientes globais',msg)
        self.assertIn('ausência',msg);self.assertIn('SOC 2',msg)
    def test_18_schema_validated_classification(self):
        with patch.object(agent,'_client',return_value=self.mock_client({'intent':'CONFIRMA','confidence':'high','next_action':'x'})):
            result=agent.receive_reply(self.current(),'confirmo')
        self.assertEqual(result['confidence'],0);self.assertFalse(self.current()['attendance_confirmed'])
    def test_19_optout_during_generation(self):
        self.enrich()
        def generate(*args):db.suppress(self.lead);return 'should never persist'
        with patch.object(agent,'generate_message',side_effect=generate):
            with self.assertRaises(ValueError):agent.send_simulated(self.current(),'PRE_EVENTO')
        self.assertEqual(db.list_interactions(self.lead),[])
    def test_20_legacy_migration(self):
        db.engine.dispose()
        legacy=self.tmp.name+'/legacy.db'
        c=sqlite3.connect(legacy)
        # Exact old schema minus the FKs missing from the old runtime.
        old=(Path(__file__).parent / 'fixtures' / 'legacy_schema.sql').read_text()
        old=old.replace(',\n  FOREIGN KEY (lead_id) REFERENCES leads(id)','')
        c.executescript(old)
        c.execute("INSERT INTO leads(name,email,status,created_at,updated_at) VALUES('old','old@example.invalid','OPT_OUT','2026-01-01','2026-01-01')")
        c.execute("INSERT INTO interactions(lead_id,phase,channel,direction,content,created_at) VALUES(1,'PRE_EVENTO','WhatsApp','INBOUND','sair','2026-01-01')")
        c.commit();c.close()
        db.engine=create_engine('sqlite:///'+legacy)
        event.listen(db.engine,'connect',db.sqlite_setup)
        db.init_db();db.init_db()
        self.assertTrue(db.get_lead(1)['suppressed'])
        self.assertEqual(db.list_interactions(1)[0]['content'],'sair')

    def test_21_anonymization(self):
        self.enrich();self.reply('CONFIRMA')
        db.anonymize_lead(self.lead)
        self.assertTrue(self.current()['suppressed'])
        self.assertIsNone(self.current()['consent_at'])
        self.assertEqual(db.list_interactions(self.lead)[0]['content'],'[conteúdo removido]')
        self.assertNotIn('SOC 2',json.dumps(db.list_actions(self.lead)))
    def test_22_llm_budget(self):
        with patch.dict(os.environ,{'MAX_LLM_CALLS_PER_DAY':'1'}):
            db.reserve_llm_call()
            with self.assertRaises(ValueError):db.reserve_llm_call()
    def test_23_rules_all_windows(self):
        self.enrich();date=datetime(2026,10,20,9,tzinfo=timezone.utc)
        for days,key in [(-14,'T14'),(-7,'T7'),(-3,'T3'),(-1,'T1'),(0,'T0'),(1,'D1'),(3,'D3'),(7,'D7')]:
            self.assertEqual(workflow.due_rule(self.current(),date+timedelta(days=days),date)[0],key)
        self.assertIsNone(workflow.due_rule(self.current(),date+timedelta(days=8),date))
        db.save_context(self.lead,True,'SOC 2')
        self.assertEqual(workflow.due_rule(self.current(),date+timedelta(hours=9),date)[0],'D0')
    def test_24_concurrent_dedup(self):
        from concurrent.futures import ThreadPoolExecutor
        self.enrich();date=datetime(2026,10,20,9,tzinfo=timezone.utc)
        with patch.object(agent,'generate_message',return_value='Mensagem de teste'):
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes=list(pool.map(lambda _:workflow.run_due(date-timedelta(days=7),date,True),range(2)))
        self.assertEqual(len(db.list_interactions(self.lead)),1)
    def test_25_real_requires_consent_and_source(self):
        data=dict(name='Teste Real',email='test@example.org')
        with self.assertRaises(ValueError):db.add_lead(data)
        real=db.add_lead({**data,'consent':True})
        with self.assertRaises(ValueError):enrichment.enrich(real)
    def test_26_context_to_classifier(self):
        observed=[]
        client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:(observed.append(kw) or SimpleNamespace(content=[SimpleNamespace(text=json.dumps(dict(intent='INTERESSE_REUNIAO',confidence=1,next_action='registrar')))]))))
        with patch.object(agent,'_client',return_value=client):
            agent.receive_reply(self.current(),'Quinta às 10h','POS_EVENTO')
        self.assertIn('POS_EVENTO',observed[0]['messages'][0]['content'])
        self.assertEqual(self.current()['status'],'FOLLOW_UP_QUENTE')

    def test_27_refusal_survives_context_and_blocks_all_sends(self):
        self.enrich();self.reply('RECUSA')
        date=datetime.now(timezone.utc)+timedelta(days=30)
        for attended in (False,True):
            db.save_context(self.lead,attended,'SOC 2')
            self.assertEqual(self.current()['status'],'NAO_COMPARECERA')
            with patch.object(agent,'generate_message') as generate:
                for phase in ('PRE_EVENTO','POS_EVENTO'):
                    with self.assertRaises(ValueError):agent.send_simulated(self.current(),phase)
                self.assertEqual(workflow.run_due(date-timedelta(days=7),date,True),[])
                self.assertEqual(workflow.run_due(date+timedelta(days=1),date,True),[])
                generate.assert_not_called()

    def test_28_refusal_can_be_clarified(self):
        self.enrich();self.reply('RECUSA');db.save_context(self.lead,False,'SOC 2')
        self.reply('CONFIRMA')
        with patch.object(agent,'generate_message',return_value='Presença confirmada'):
            agent.send_simulated(self.current(),'PRE_EVENTO')
        self.assertEqual(self.current()['status'],'CONFIRMADO')

    def test_29_negated_optout_reaches_classifier_unchanged(self):
        replies=['Não quero sair da lista. Confirmo minha presença.',
                 'Não desejo parar de receber mensagens.',
                 'Não me remova da lista.']
        for reply in replies:
            observed=[]
            def create(**kwargs):
                observed.append(kwargs['messages'][0]['content'])
                return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(dict(intent='CONFIRMA',confidence=1,next_action='confirmar')))])
            client=SimpleNamespace(messages=SimpleNamespace(create=create))
            with self.subTest(reply=reply), patch.object(agent,'_client',return_value=client):
                result=agent.receive_reply(self.current(),reply)
                self.assertEqual(result['intent'],'CONFIRMA')
                self.assertFalse(self.current()['suppressed'])
                self.assertIn(reply,observed[0])

    def test_30_explicit_optout_still_works_without_api(self):
        for reply in ['SAIR','Por favor, não me envie mais mensagens.',
                      'Remova meu contato da lista.',
                      'Não quero sair do evento, mas não quero receber mensagens.']:
            with self.subTest(reply=reply), patch.object(agent,'_client') as client:
                self.assertEqual(agent.classify_reply(self.current(),reply)['intent'],'OPT_OUT')
                client.assert_not_called()

    def test_31_review_blocks_meeting_until_clarification(self):
        self.reply('INTERESSE_REUNIAO');self.reply('DUVIDA',0.1)
        when=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
        with self.assertRaisesRegex(ValueError,'Esclareça'):db.schedule_meeting(self.lead,when)
        self.assertFalse(self.current()['meeting_scheduled'])
        self.assertFalse(any(a['action_type']=='MEETING' for a in db.list_actions(self.lead)))
        self.reply('INTERESSE_REUNIAO')
        db.schedule_meeting(self.lead,when)
        self.assertTrue(self.current()['meeting_scheduled'])
        self.assertFalse(self.current()['review_required'])

if __name__=='__main__': unittest.main()
