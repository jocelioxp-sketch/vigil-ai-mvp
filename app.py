import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from db import init_db, add_lead, list_leads, get_lead, update_lead, list_interactions
from agent import enrich_locally, send_simulated, receive_reply

load_dotenv()
init_db()
st.set_page_config(page_title="Vigil.AI Event Agent", page_icon="🛡️", layout="wide")

st.title("Vigil.AI — Event Conversion Agent")
st.caption("MVP demonstrável: captação → enriquecimento → confirmação → presença → follow-up → reunião")

leads = list_leads()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Inscritos", len(leads))
c2.metric("Confirmados", sum(int(x['attendance_confirmed'] or 0) for x in leads))
c3.metric("Presentes", sum(int(x['attended'] or 0) for x in leads))
c4.metric("Reuniões", sum(int(x['meeting_scheduled'] or 0) for x in leads))

tabs = st.tabs(["Captação", "Funil / Dashboard", "Agente", "Demo pós-evento"])

with tabs[0]:
    st.subheader("Nova inscrição")
    with st.form("lead_form"):
        a,b = st.columns(2)
        name = a.text_input("Nome")
        email = b.text_input("E-mail")
        phone = a.text_input("Telefone")
        role = b.text_input("Cargo")
        company = a.text_input("Empresa")
        sector = b.selectbox("Setor", ["Tecnologia","Financeiro","Saúde","Manufatura","Governo","Outro"])
        company_size = a.number_input("Funcionários", min_value=0, value=250, step=50)
        linkedin_url = b.text_input("LinkedIn (opcional)")
        security_interest = st.text_input("Principal interesse em segurança")
        consent = st.checkbox("Concordo com o uso dos dados para comunicação sobre o Vigil Summit e seus desdobramentos comerciais.")
        submitted = st.form_submit_button("Inscrever")
        if submitted:
            if not (name and email and consent):
                st.error("Nome, e-mail e consentimento são obrigatórios.")
            else:
                try:
                    add_lead(dict(name=name,email=email,phone=phone,role=role,company=company,sector=sector,
                                  company_size=company_size,linkedin_url=linkedin_url,security_interest=security_interest))
                    st.success("Lead cadastrado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível cadastrar: {e}")

with tabs[1]:
    st.subheader("Pipeline")
    leads = list_leads()
    if leads:
        df = pd.DataFrame(leads)[["id","name","company","role","lead_score","status","attendance_confirmed","attended","meeting_scheduled"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum lead ainda.")

with tabs[2]:
    st.subheader("Operação do agente")
    leads = list_leads()
    if not leads:
        st.info("Cadastre ou rode seed.py para criar leads sintéticos.")
    else:
        labels = {f"#{x['id']} — {x['name']} ({x['company']})": x['id'] for x in leads}
        label = st.selectbox("Lead", list(labels.keys()))
        lead = get_lead(labels[label])
        st.json(lead)
        col1,col2 = st.columns(2)
        if col1.button("1. Enriquecer / pontuar"):
            summary,score = enrich_locally(lead)
            st.success(f"Score: {score}")
            st.write(summary)
            st.rerun()
        phase = col2.selectbox("Fase da mensagem", ["PRE_EVENTO","POS_EVENTO"])
        if st.button("2. Gerar e registrar mensagem com Claude"):
            try:
                msg = send_simulated(get_lead(lead['id']), phase)
                st.success("Mensagem registrada no canal simulado.")
                st.write(msg)
            except Exception as e:
                st.error(str(e))
        reply = st.text_area("3. Simular resposta do lead", placeholder="Ex.: Confirmo minha presença. Pode me mandar os detalhes?")
        if st.button("Interpretar resposta e atualizar funil"):
            try:
                result = receive_reply(get_lead(lead['id']), reply, phase)
                st.json(result)
                st.rerun()
            except Exception as e:
                st.error(str(e))
        st.markdown("#### Histórico")
        st.dataframe(pd.DataFrame(list_interactions(lead['id'])), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Simulação de contexto pós-evento")
    leads = list_leads()
    if leads:
        labels = {f"#{x['id']} — {x['name']}": x['id'] for x in leads}
        label = st.selectbox("Lead presente", list(labels.keys()), key="postlead")
        lead = get_lead(labels[label])
        attended = st.checkbox("Compareceu ao evento", value=bool(lead['attended']))
        demo_interest = st.text_input("Interesse observado", value=lead['demo_interest'] or "dashboard de risco e compliance")
        meeting_dt = st.text_input("Horário da reunião (quando houver)", value=lead['meeting_datetime'] or "2026-10-20 14:00")
        c1,c2 = st.columns(2)
        if c1.button("Salvar contexto do evento"):
            update_lead(lead['id'], attended=int(attended), demo_interest=demo_interest, status="PRESENTE" if attended else lead['status'])
            st.success("Contexto salvo.")
            st.rerun()
        if c2.button("Marcar reunião agendada"):
            update_lead(lead['id'], meeting_scheduled=1, meeting_datetime=meeting_dt, status="REUNIAO_AGENDADA")
            st.success("Reunião marcada.")
            st.rerun()
