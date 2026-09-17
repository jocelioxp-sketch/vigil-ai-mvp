import tempfile
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine, event
from streamlit.testing.v1 import AppTest
import db
import agent

class AppFlowTest(unittest.TestCase):
    def test_guided_flow(self):
        with tempfile.TemporaryDirectory() as folder:
            original=db.engine
            db.engine=create_engine('sqlite:///'+folder+'/app.db')
            event.listen(db.engine,'connect',db.sqlite_setup)
            try:
                with patch('workflow.start_worker',return_value=None):
                    app=AppTest.from_file('app.py').run()
                    self.assertFalse(list(app.exception))
                    app.button[0].click().run()
                    self.assertFalse(list(app.exception))
                    def button(label):return next(x for x in app.button if x.label==label)
                    button('Analisar lead · Enriquecer e pontuar').click().run()
                    self.assertFalse(list(app.exception))
                    with patch.object(agent,'generate_message',return_value='Mensagem sintética'):
                        button('Gerar mensagem com IA').click().run()
                    self.assertFalse(list(app.exception))
                    self.assertTrue(db.list_interactions(db.list_leads()[0]['id']))
                    self.assertEqual(len(app.tabs),6)
            finally:
                db.engine.dispose();db.engine=original
