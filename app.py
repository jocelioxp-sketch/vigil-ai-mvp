import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from db import init_db, add_lead, list_leads, get_lead, update_lead, list_interactions
from agent import enrich_locally, send_simulated, receive_reply

load_dotenv()
init_db()
st.set_page_config(page_title="Vigil.AI | Event Conversion Agent", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
.hero {padding: 1.8rem 2rem; border: 1px solid rgba(128,128,128,.22); border-radius: 18px; margin-bottom: 1rem;}
.hero h1 {margin: 0 0 .35rem 0; font-size: 2.25rem;}
.hero p {margin: 0; opacity: .75; font-size: 1.05rem;}
.eyebrow {font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; opacity:.65; font-weight:700;}
.step {padding: .85rem 1rem; border: 1px solid rgba(128,128,128,.2); border-radius: 12px; min-height: 88px;}
.step strong {display:block; margin-bottom:.2rem;}
.chat-out {padding: .9rem 1rem; border-radius: 14px 14px 4px 14px; background: rgba(46,125,50,.12); margin: .5rem 0 .8rem 12%;}
.chat-in {padding: .9rem 1rem; border-radius: 14px 14px 14px 4px; background: rgba(70,90,120,.12); margin: .5rem 12% .8rem 0;}
.small-muted {opacity:.65; font-size:.88rem;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.18); padding:1rem; border-radius:14px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="eyebrow">AI Engineer Case · Demonstrable MVP</div>
  <h1>🛡️ Vigil.AI — Event Conversion Agent</h1>
  <p>Agente de IA para converter inscrições B2B em presença qualificada e reuniões comerciais.</p>
</div>
""", unsafe_allow_html=True)

leads = list_leads()
confirmed = sum(int(x['attendance_confirmed'] or 0) for x in leads)
attended_count = sum(int(x['attended'] or 0) for x in leads)
meetings = sum(int(x['meeting_scheduled'] or 0) for x in leads)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Inscritos", len(leads))
c2.metric("Confirmados", confirmed, f"{(confirmed/len(leads)*100):.0f}%" if leads else "0%")
c3.metric("Presentes", attended_count, f"{(attended_count/len(leads)*100):.0f}%" if leads else "0%")
c4.metric("Reuniões", meetings, f"{(meetings/len(leads)*100):.0f}%" if leads else "0%")

st.markdown("### Jornada do agente")
steps = [
    ("1", "Lead", "Captação e consentimento"),
    ("2", "Enriquecer", "ICP e lead score"),
    ("3", "Engajar", "Mensagem personalizada"),
    ("4", "Converter", "Presença e follow-up"),
    ("5", "Reunião", "Oportunidade comercial"),
]
cols = st.columns(5)
for col, (n, title, desc) in zip(cols, steps):
    col.markdown(f'<div class="step"><span class="eyebrow">ETAPA {n}</span><strong>{title}</strong><span class="small-muted">{desc}</span></div>', unsafe_allow_html=True)

with st.expander("▶ Roteiro rápido para o avaliador", expanded=False):
    st.markdown("""
**Demonstração sugerida (3–5 minutos):**
1. Abra **Demo guiada** e escolha um lead.
2. Execute **Enriquecer e pontuar** para visualizar o score e sua explicação.
3. Gere uma abordagem pré-evento com IA.
4. Simule a resposta **“Confirmo minha presença”** e observe a atualização do funil.
5. Em **Contexto pós-evento**, marque presença e um interesse observado.
6. Retorne à demo, gere o follow-up e simule **“Quero agendar uma conversa”**.
7. Marque a reunião e confira os indicadores em **Dashboard**.

> WhatsApp, enriquecimento externo e agenda são simulados intencionalmente neste MVP; as decisões e interações ficam registradas para auditoria.
""")

tabs = st.tabs(["✨ Demo guiada", "📊 Dashboard", "➕ Captação", "🎟️ Contexto pós-evento"])

with tabs[0]:
    st.subheader("Demonstração guiada do agente")
    leads = list_leads()
    if not leads:
        st.info("Ainda não há leads. Use a aba Captação ou execute `python seed.py` para carregar as personas sintéticas.")
    else:
        labels = {f"#{x['id']} · {x['name']} — {x['company'] or 'Empresa não informada'}": x['id'] for x in leads}
        label = st.selectbox("Escolha um lead para a demonstração", list(labels.keys()))
        lead = get_lead(labels[label])

        a, b, c, d = st.columns(4)
        a.metric("Lead score", f"{lead['lead_score'] or 0}/100")
        b.metric("Status", (lead['status'] or "NOVO").replace("_", " "))
        c.metric("Empresa", lead['company'] or "—")
        d.metric("Cargo", lead['role'] or "—")

        with st.expander("Ver perfil completo"):
            p1, p2 = st.columns(2)
            p1.markdown(f"**Nome:** {lead['name']}  \n**E-mail:** {lead['email']}  \n**Telefone:** {lead['phone'] or '—'}  \n**LinkedIn:** {lead['linkedin_url'] or '—'}")
            p2.markdown(f"**Setor:** {lead['sector'] or '—'}  \n**Funcionários:** {lead['company_size'] or '—'}  \n**Interesse:** {lead['security_interest'] or '—'}")

        st.markdown("#### 1. Entender e priorizar")
        if st.button("Analisar lead · Enriquecer e pontuar", type="primary", use_container_width=True):
            summary, score = enrich_locally(lead)
            st.success(f"Análise concluída · Lead score {score}/100")
            st.info(summary)
            st.rerun()
        if lead.get('enrichment_summary'):
            st.markdown("**Por que o agente priorizou este lead?**")
            st.info(lead['enrichment_summary'])

        st.divider()
        st.markdown("#### 2. Criar abordagem personalizada")
        phase_label = st.radio("Momento da jornada", ["Pré-evento", "Pós-evento"], horizontal=True)
        phase = "PRE_EVENTO" if phase_label == "Pré-evento" else "POS_EVENTO"
        if st.button("Gerar mensagem com IA", use_container_width=True):
            try:
                msg = send_simulated(get_lead(lead['id']), phase)
                st.success("Mensagem gerada e registrada no histórico.")
                st.markdown(f'<div class="chat-out"><span class="small-muted">Vigil.AI · WhatsApp simulado</span><br>{msg}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Não foi possível gerar a mensagem: {e}")

        interactions = list_interactions(lead['id'])
        if interactions:
            recent = interactions[-6:]
            st.markdown("**Conversa recente**")
            for item in recent:
                css = "chat-out" if item.get("direction") == "OUTBOUND" else "chat-in"
                who = "Vigil.AI" if item.get("direction") == "OUTBOUND" else lead['name']
                st.markdown(f'<div class="{css}"><span class="small-muted">{who}</span><br>{item.get("content", "")}</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 3. Simular resposta e observar a decisão")
        presets = ["Digite uma resposta...", "Confirmo minha presença. Pode me mandar os detalhes?", "Não poderei participar.", "Quero agendar uma conversa sobre isso.", "Por favor, não me envie mais mensagens."]
        preset = st.selectbox("Resposta rápida", presets)
        default_reply = "" if preset == presets[0] else preset
        reply = st.text_area("Resposta do lead", value=default_reply, placeholder="Ex.: Confirmo minha presença. Pode me mandar os detalhes?")
        if st.button("Interpretar resposta e atualizar funil", use_container_width=True):
            if not reply.strip():
                st.warning("Digite ou selecione uma resposta para continuar.")
            else:
                try:
                    result = receive_reply(get_lead(lead['id']), reply, phase)
                    intent = result.get("intent", "OUTRO").replace("_", " ")
                    confidence = float(result.get("confidence", 0))
                    st.success(f"Intenção detectada: {intent} · confiança {confidence:.0%}")
                    st.markdown(f"**Próxima ação recomendada:** {result.get('next_action', '—')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível interpretar a resposta: {e}")

        with st.expander("Histórico técnico / auditoria"):
            history = pd.DataFrame(list_interactions(lead['id']))
            if not history.empty:
                st.dataframe(history, use_container_width=True, hide_index=True)
            else:
                st.caption("Nenhuma interação registrada para este lead.")

with tabs[1]:
    st.subheader("Funil de conversão")
    leads = list_leads()
    if leads:
        df = pd.DataFrame(leads)[["id", "name", "company", "role", "lead_score", "status", "attendance_confirmed", "attended", "meeting_scheduled"]]
        df = df.rename(columns={"id":"ID", "name":"Lead", "company":"Empresa", "role":"Cargo", "lead_score":"Score", "status":"Status", "attendance_confirmed":"Confirmado", "attended":"Presente", "meeting_scheduled":"Reunião"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("O dashboard reflete imediatamente as decisões tomadas durante a demonstração.")
    else:
        st.info("Nenhum lead ainda.")

with tabs[2]:
    st.subheader("Nova inscrição")
    st.caption("Captação consentida de dados para comunicação relacionada ao Vigil Summit.")
    with st.form("lead_form"):
        a, b = st.columns(2)
        name = a.text_input("Nome *")
        email = b.text_input("E-mail *")
        phone = a.text_input("Telefone")
        role = b.text_input("Cargo")
        company = a.text_input("Empresa")
        sector = b.selectbox("Setor", ["Tecnologia", "Financeiro", "Saúde", "Manufatura", "Governo", "Outro"])
        company_size = a.number_input("Número de funcionários", min_value=0, value=250, step=50)
        linkedin_url = b.text_input("LinkedIn (opcional)")
        security_interest = st.text_input("Principal interesse em segurança")
        consent = st.checkbox("Concordo com o uso dos dados para comunicação sobre o Vigil Summit e seus desdobramentos comerciais.")
        submitted = st.form_submit_button("Cadastrar lead", type="primary", use_container_width=True)
        if submitted:
            if not (name and email and consent):
                st.error("Nome, e-mail e consentimento são obrigatórios.")
            else:
                try:
                    add_lead(dict(name=name, email=email, phone=phone, role=role, company=company, sector=sector,
                                  company_size=company_size, linkedin_url=linkedin_url, security_interest=security_interest))
                    st.success("Lead cadastrado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível cadastrar: {e}")

with tabs[3]:
    st.subheader("Contexto observado no evento")
    st.caption("Simula os sinais presenciais que alimentam o follow-up pós-evento.")
    leads = list_leads()
    if leads:
        labels = {f"#{x['id']} · {x['name']}": x['id'] for x in leads}
        label = st.selectbox("Lead", list(labels.keys()), key="postlead")
        lead = get_lead(labels[label])
        attended = st.checkbox("Compareceu ao evento", value=bool(lead['attended']))
        demo_interest = st.text_input("Interesse observado", value=lead['demo_interest'] or "dashboard de risco e compliance")
        meeting_dt = st.text_input("Horário da reunião (quando houver)", value=lead['meeting_datetime'] or "2026-10-20 14:00")
        c1, c2 = st.columns(2)
        if c1.button("Salvar contexto do evento", use_container_width=True):
            update_lead(lead['id'], attended=int(attended), demo_interest=demo_interest, status="PRESENTE" if attended else lead['status'])
            st.success("Contexto salvo.")
            st.rerun()
        if c2.button("Marcar reunião agendada", type="primary", use_container_width=True):
            update_lead(lead['id'], meeting_scheduled=1, meeting_datetime=meeting_dt, status="REUNIAO_AGENDADA")
            st.success("Reunião marcada.")
            st.rerun()
    else:
        st.info("Cadastre um lead antes de simular o contexto pós-evento.")

st.divider()
st.caption("Vigil.AI MVP · IA aplicada à conversão de eventos B2B · Dados e canais externos simulados para demonstração segura e auditável.")
