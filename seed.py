from db import init_db, add_lead, list_leads

SYNTHETIC=[
 dict(name='Mariana Demo',email='mariana@example.invalid',role='CISO',company='Atlas Bank (fictícia)',sector='Financeiro',company_size=1200,security_interest='SOC 2'),
 dict(name='Ricardo Demo',email='ricardo@example.invalid',role='CTO',company='MedNova (fictícia)',sector='Saúde',company_size=620,security_interest='resposta a incidentes'),
 dict(name='Persona Demo Microsoft',email='empresa-publica@example.invalid',role='CTO (fictício)',company='Microsoft',sector='Tecnologia',company_size=1000,security_interest='gestão de vulnerabilidades'),
]

def seed():
    init_db()
    existing={x['email'] for x in list_leads()}
    for data in SYNTHETIC:
        if data['email'] not in existing:
            add_lead({**data,'synthetic':True})

if __name__=='__main__':
    seed()
    print('Personas sintéticas criadas sem alterar estados existentes.')
