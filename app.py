import os
import json
import hmac
from html import escape
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
# Streamlit hot updates can retain v1 modules while replacing app.py.
# Upgrade these legacy modules once; never reload an active v2 worker on each rerun.
import importlib
import db as _db_module
if not hasattr(_db_module, "anonymize_lead"):
    importlib.reload(_db_module)
import agent as _agent_module
if not hasattr(_agent_module, "eligible"):
    importlib.reload(_agent_module)

from db import init_db, add_lead, list_leads, get_lead, list_interactions, list_actions, save_context, schedule_meeting, setting, set_setting, rows, anonymize_lead
from enrichment import enrich, fetch_company
from workflow import start_worker, run_due, parse_date
from seed import seed
from agent import enrich_locally, send_simulated, receive_reply

load_dotenv()
init_db()
st.set_page_config(page_title="Vigil.AI | Event Conversion Agent", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

password = os.getenv("DEMO_PASSWORD", "")
if os.getenv("DEMO_MODE", "true").lower() != "true" and not password:
    st.error("Configure uma senha de avaliação antes de habilitar cadastro de dados reais.")
    st.stop()
if password:
    entered = st.text_input("Senha de avaliação", type="password")
    if not hmac.compare_digest(entered, password):
        st.info("Informe a senha de avaliação para acessar.")
        st.stop()

@st.cache_resource
def worker():
    return start_worker()
worker()

if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

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

> WhatsApp e convite de calendário são simulados. A consulta pública da empresa é real quando selecionada. Personas fictícias e dados declarados ficam identificados.
""")

tabs = st.tabs(["✨ Demo guiada", "📊 Dashboard", "➕ Captação", "🎟️ Contexto pós-evento", "⏱️ Réguas", "🔎 Evidências"])

with tabs[0]:
    st.subheader("Demonstração guiada do agente")
    leads = list_leads()
    if not leads:
        st.info("Carregue as personas sintéticas para iniciar a avaliação.")
        if st.button("Carregar personas de demonstração"):
            seed()
            st.rerun()
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
        mode = st.radio("Fonte do enriquecimento", ["Persona sintética", "Empresa pública (Wikidata)"], horizontal=True)
        qid = None
        source_confirmed = False
        if mode == "Empresa pública (Wikidata)":
            st.caption("Verifica descrição e site da empresa, sem comprovar vínculo, cargo ou porte do lead. Para a persona Microsoft: Q2283.")
            qid = st.text_input("Identificador Wikidata da empresa", value=lead.get("source_qid") or "", key=f"qid_{lead['id']}")
            if st.button("Consultar fonte pública"):
                try:
                    st.session_state["source_preview"] = fetch_company(qid)
                except Exception:
                    st.error("Não foi possível consultar a fonte. Confira o identificador ou tente mais tarde.")
            preview = st.session_state.get("source_preview", {})
            if preview.get("qid") == qid.strip().upper():
                st.json(preview)
                source_confirmed = st.checkbox("Confirmei que esta fonte corresponde à empresa selecionada")
        if st.button("Analisar lead · Enriquecer e pontuar", type="primary", use_container_width=True):
            try:
                summary, score = enrich(lead['id'], qid if mode.startswith("Empresa") else None, source_confirmed)
                st.session_state["notice"] = f"Análise concluída: {score}/100. Origem dos dados registrada."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception:
                st.error("Fonte indisponível. Nenhum enriquecimento público foi inventado.")
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
                st.markdown(f'<div class="chat-out"><span class="small-muted">Vigil.AI · WhatsApp simulado</span><br>{escape(msg)}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(str(e) if isinstance(e, ValueError) else "Serviço de IA indisponível. Confira a configuração ou tente novamente.")

        interactions = list_interactions(lead['id'])
        if interactions:
            recent = interactions[-6:]
            st.markdown("**Conversa recente**")
            for item in recent:
                css = "chat-out" if item.get("direction") == "OUTBOUND" else "chat-in"
                who = "Vigil.AI" if item.get("direction") == "OUTBOUND" else lead['name']
                st.markdown(f'<div class="{css}"><span class="small-muted">{escape(who)}</span><br>{escape(item.get("content", ""))}</div>', unsafe_allow_html=True)

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
                    st.session_state["notice"] = f"Intenção: {intent} · confiança {confidence:.0%}. {result.get('next_action', '')}"
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
    st.caption("Ambiente de avaliação: use apenas personas fictícias e e-mail @example.invalid. Consentimento sintético fica identificado no banco.")
    if st.button("Adicionar personas sintéticas de exemplo"):
        seed()
        st.rerun()
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
                    synthetic = os.getenv("DEMO_MODE", "true").lower() == "true"
                    add_lead(dict(name=name, email=email, phone=phone, role=role, company=company, sector=sector,
                                  company_size=company_size, linkedin_url=linkedin_url, security_interest=security_interest, consent=consent, synthetic=synthetic))
                    st.success("Lead cadastrado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e) if isinstance(e, ValueError) else "Cadastro não concluído. Verifique se o e-mail já está cadastrado.")

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
        meeting_dt = st.text_input("Horário da reunião (quando houver)", value=lead['meeting_datetime'] or "2026-10-20T14:00:00-03:00")
        c1, c2 = st.columns(2)
        if c1.button("Salvar contexto do evento", use_container_width=True):
            save_context(lead['id'], attended, demo_interest)
            st.success("Contexto salvo.")
            st.rerun()
        if c2.button("Marcar reunião agendada", type="primary", use_container_width=True):
            try:
                schedule_meeting(lead['id'], meeting_dt)
                st.session_state["notice"] = "Reunião registrada no MVP; nenhum convite externo enviado."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    else:
        st.info("Cadastre um lead antes de simular o contexto pós-evento.")

with tabs[4]:
    st.subheader("Réguas por data e estado")
    st.caption("A execução registra mensagens no canal simulado. Confirmações, recusas, opt-out e reuniões mudam a elegibilidade.")
    event_text = st.text_input("Início do evento (ISO com fuso)", value=setting("event_at", "2026-10-20T09:00:00-03:00"))
    auto = st.checkbox("Executar automaticamente a cada minuto enquanto a aplicação estiver ativa", value=setting("automation_enabled") == "1")
    if st.button("Salvar configuração das réguas"):
        try:
            event_at = parse_date(event_text)
            set_setting("event_at", event_at.isoformat())
            set_setting("automation_enabled", "1" if auto else "0")
            st.success("Configuração salva. O relógio automático usa a data real.")
        except ValueError as e:
            st.error(str(e))
    offset = st.selectbox("Avançar relógio de demonstração", [-14, -7, -3, -1, 0, 1, 3, 7], format_func=lambda x: f"{'T' if x<0 else 'D'}{x:+d}")
    if st.button("Executar etapa de demonstração"):
        try:
            event_at = parse_date(event_text)
            clock = event_at + timedelta(days=offset, hours=9 if offset == 0 else 0)
            outcome = run_due(clock, event_at, simulated=True)
            if outcome:
                st.dataframe(outcome, hide_index=True)
            else:
                st.info("Nenhuma ação elegível ou etapa já executada. O relógio simulado atua apenas sobre personas sintéticas.")
        except ValueError as e:
            st.error(str(e))
    st.caption("T14/T7/T3: confirmação pendente. T1/T0: lembrete. D0: agradecimento após o evento; D1/D3/D7: follow-up, com texto distinto para ausentes. Cada janela executa uma vez por lead. O worker não permanece ativo quando o host suspende o app.")

with tabs[5]:
    st.subheader("Evidências para avaliação")
    st.caption("Perfil declarado, fonte pública, conversas, decisões e execuções das réguas.")
    all_leads = list_leads()
    if all_leads:
        chosen = st.selectbox("Lead para auditoria", [x['id'] for x in all_leads], format_func=lambda n: next(x['name'] for x in all_leads if x['id']==n))
        selected = get_lead(chosen)
        st.json({"tipo": "sintético" if selected["synthetic"] else "real", "origem_consentimento": selected["consent_source"], "bloqueado": bool(selected["suppressed"]), "enriquecimento": selected["enrichment_kind"], "fonte": json.loads(selected["source_json"] or "{}")})
        st.dataframe(list_actions(chosen), hide_index=True, use_container_width=True)
        st.dataframe(rows("SELECT * FROM deliveries WHERE lead_id=:id", {"id": chosen}), hide_index=True, use_container_width=True)
        export = {"lead": selected, "conversas": list_interactions(chosen), "decisoes": list_actions(chosen), "execucoes": rows("SELECT * FROM deliveries WHERE lead_id=:id", {"id": chosen})}
        st.download_button("Baixar evidências do lead (JSON)", json.dumps(export,ensure_ascii=False,indent=2), file_name="vigil-evidencias.json", mime="application/json")
        with st.expander("Anonimizar dados deste registro"):
            st.caption("Remove nome, contato, perfil, fontes e conteúdo das conversas/decisões. Mantém apenas contagens anônimas e bloqueia comunicações. Não é reversível.")
            confirmed_erase = st.checkbox("Confirmo a anonimização deste registro", key=f"erase_{chosen}")
            if st.button("Anonimizar registro", disabled=not confirmed_erase):
                anonymize_lead(chosen)
                st.session_state["notice"] = "Registro anonimizado e bloqueado."
                st.rerun()
    st.markdown("[Documentação técnica](https://github.com/jocelioxp-sketch/vigil-ai-mvp/blob/main/TECHNICAL_DOCUMENTATION.md) · [Roteiro de teste](https://github.com/jocelioxp-sketch/vigil-ai-mvp/blob/main/DEMO_SCRIPT.md)")

st.divider()
st.caption("Vigil.AI MVP · IA aplicada à conversão de eventos B2B · Versão 2 · Canal e agenda simulados; fontes públicas e decisões rastreáveis.")

