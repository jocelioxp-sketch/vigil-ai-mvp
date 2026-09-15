from db import init_db, add_lead, list_leads, update_lead

SYNTHETIC = [
    dict(name="Mariana Costa", email="mariana@atlasbank.demo", phone="11999990001", role="CISO", company="Atlas Bank", sector="Financeiro", company_size=1800, linkedin_url="https://linkedin.com/in/mariana-demo", security_interest="SOC 2 e gestão contínua de vulnerabilidades"),
    dict(name="Ricardo Lima", email="ricardo@mednova.demo", phone="11999990002", role="CTO", company="MedNova", sector="Saúde", company_size=620, linkedin_url="https://linkedin.com/in/ricardo-demo", security_interest="LGPD e resposta a incidentes"),
    dict(name="Paula Nunes", email="paula@fabritech.demo", phone="11999990003", role="Diretora de TI", company="FabriTech", sector="Manufatura", company_size=950, linkedin_url="", security_interest="redução de superfície de ataque"),
    dict(name="André Melo", email="andre@softprime.demo", phone="11999990004", role="Gerente de Segurança", company="SoftPrime", sector="Tecnologia", company_size=410, linkedin_url="https://linkedin.com/in/andre-demo", security_interest="ISO 27001 e priorização de risco"),
    dict(name="Carla Reis", email="carla@govdigital.demo", phone="11999990005", role="Head de Infraestrutura", company="GovDigital", sector="Governo", company_size=2400, linkedin_url="", security_interest="monitoramento contínuo e compliance"),
]

if __name__ == "__main__":
    init_db()
    existing = {x['email'] for x in list_leads()}
    for item in SYNTHETIC:
        if item['email'] not in existing:
            add_lead(item)
    leads = list_leads()
    if leads:
        update_lead(leads[0]['id'], attendance_confirmed=1, attended=1, demo_interest="SOC 2; dashboard de risco", status="PRESENTE")
    print("Base sintética criada.")
