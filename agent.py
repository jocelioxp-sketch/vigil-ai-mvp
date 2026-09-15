import os, json, re
from anthropic import Anthropic
from db import add_interaction, add_action, update_lead, list_interactions

MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """Você é o agente comercial autônomo do Vigil Summit, evento B2B da Vigil.AI.
Seu objetivo é maximizar presença no evento e, após o evento, converter interesse em reunião comercial.
Você deve ser profissional, conciso, contextual e nunca inventar fatos.
Use os dados disponíveis do lead para personalizar a abordagem.
Respeite LGPD: use apenas dados fornecidos ou públicos, explique finalidade quando necessário e honre opt-out.
Não tome decisões fora do escopo comercial do evento.
"""


def _client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada")
    return Anthropic(api_key=key)


def enrich_locally(lead):
    score = 20
    reasons = []
    role = (lead.get("role") or "").lower()
    sector = (lead.get("sector") or "").lower()
    size = lead.get("company_size") or 0
    interest = lead.get("security_interest") or "segurança cibernética"
    if any(x in role for x in ["ciso", "cto", "diretor", "head", "gerente"]):
        score += 35; reasons.append("cargo decisor ou influenciador")
    if size >= 200:
        score += 25; reasons.append("empresa dentro do ICP (>200 funcionários)")
    if sector in ["financeiro", "saúde", "governo", "manufatura", "tecnologia"]:
        score += 10; reasons.append("setor com alta exposição regulatória/operacional")
    if lead.get("linkedin_url"):
        score += 5; reasons.append("presença profissional identificada")
    score = min(score, 100)
    summary = f"Perfil: {lead.get('role') or 'cargo não informado'} na {lead.get('company') or 'empresa não informada'}; setor {lead.get('sector') or 'não informado'}; porte {size or 'não informado'}; interesse declarado: {interest}. Sinais: {', '.join(reasons) if reasons else 'dados ainda limitados'}."
    update_lead(lead["id"], enrichment_summary=summary, lead_score=score, status="ENRIQUECIDO")
    add_action(lead["id"], "ENRICHMENT", "Score e resumo produzidos com dados declarados e sinais profissionais disponíveis.", summary)
    return summary, score


def generate_message(lead, phase="PRE_EVENTO"):
    interactions = list_interactions(lead["id"])
    context = {
        "lead": lead,
        "historico": interactions[-6:],
        "fase": phase
    }
    prompt = f"""Gere UMA mensagem para WhatsApp, com no máximo 600 caracteres.
Contexto JSON:\n{json.dumps(context, ensure_ascii=False, default=str)}

Regras:
- PRE_EVENTO: aumentar relevância e pedir confirmação de presença.
- POS_EVENTO: mencionar interesse/demonstração observada e convidar para reunião.
- Não seja genérico; use pelo menos 1 dado do lead.
- Sem emojis excessivos.
- Termine com uma ação objetiva.
Retorne apenas a mensagem."""
    resp = _client().messages.create(model=MODEL, max_tokens=350, temperature=0.3,
                                     system=SYSTEM_PROMPT,
                                     messages=[{"role":"user","content":prompt}])
    return resp.content[0].text.strip()


def classify_reply(lead, reply):
    prompt = f"""Classifique a resposta de um lead do Vigil Summit.
Resposta: {reply!r}
Retorne JSON válido com: intent (CONFIRMA, RECUSA, DUVIDA, OPT_OUT, INTERESSE_REUNIAO, OUTRO), confidence (0-1), next_action.
Apenas JSON."""
    resp = _client().messages.create(model=MODEL, max_tokens=200, temperature=0,
                                     system=SYSTEM_PROMPT,
                                     messages=[{"role":"user","content":prompt}])
    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```json|```$", "", raw).strip()
    data = json.loads(raw)
    intent = data.get("intent", "OUTRO")
    if intent == "CONFIRMA":
        update_lead(lead["id"], attendance_confirmed=1, status="CONFIRMADO")
    elif intent == "RECUSA":
        update_lead(lead["id"], status="NAO_COMPARECERA")
    elif intent == "INTERESSE_REUNIAO":
        update_lead(lead["id"], status="FOLLOW_UP_QUENTE")
    elif intent == "OPT_OUT":
        update_lead(lead["id"], status="OPT_OUT")
    add_action(lead["id"], "CLASSIFY_REPLY", data.get("next_action", ""), raw)
    return data


def send_simulated(lead, phase, channel="WhatsApp"):
    msg = generate_message(lead, phase)
    add_interaction(lead["id"], phase, channel, "OUTBOUND", msg)
    add_action(lead["id"], "SEND_MESSAGE", f"Mensagem {phase} gerada e registrada no canal simulado.", msg)
    return msg


def receive_reply(lead, reply, phase="PRE_EVENTO", channel="WhatsApp"):
    add_interaction(lead["id"], phase, channel, "INBOUND", reply)
    return classify_reply(lead, reply)
