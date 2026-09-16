# Vigil.AI Event Conversion Agent — MVP

MVP para o case de AI Engineer da Pareto. O produto demonstra um agente de IA capaz de operar um funil B2B de evento: **captação → enriquecimento → engajamento pré-evento → presença → follow-up → reunião comercial**.

## Stack
- **Python + Streamlit**: interface de demonstração e dashboard no mesmo projeto.
- **Anthropic Claude**: geração de mensagens e classificação de respostas.
- **SQLAlchemy + SQLite (demo)**: banco relacional simples e auditável. Em produção, `DATABASE_URL` pode apontar para Postgres/Supabase.
- **Deploy sugerido**: Streamlit Community Cloud, Render ou Railway.

## Como rodar
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env       # Windows (PowerShell): Copy-Item .env.example .env
# edite .env e adicione sua ANTHROPIC_API_KEY
python seed.py
streamlit run app.py
```

> Nunca versione sua chave real de API. O arquivo `.env.example` contém apenas placeholders seguros.

## Fluxo de demonstração
1. Abra **Captação** e cadastre um lead ou rode `python seed.py`.
2. Em **Agente**, selecione o lead e clique em **Enriquecer / pontuar**.
3. Gere uma mensagem `PRE_EVENTO` com Claude.
4. Simule uma resposta como “Confirmo presença”. O agente classifica e atualiza o status.
5. Em **Demo pós-evento**, marque o lead como presente e registre um interesse observado.
6. Volte ao **Agente** e gere uma mensagem `POS_EVENTO`.
7. Simule “Quero agendar uma conversa”.
8. Em **Demo pós-evento**, marque a reunião como agendada.
9. Mostre o **Dashboard** com a atualização do funil.

## Estrutura
- `app.py`: interface e dashboard
- `agent.py`: LLM, mensagens, classificação e ações
- `db.py`: persistência e histórico
- `seed.py`: personas sintéticas
- `schema.sql`: modelo relacional
- `TECHNICAL_DOCUMENTATION.md`: documentação técnica e decisões
- `docs/architecture.mmd`: diagrama Mermaid

## Limitações assumidas no MVP
- Enriquecimento externo real foi substituído por enriquecimento determinístico com dados declarados/públicos simulados. A interface está preparada para substituir essa função por Clearbit/Apollo/Proxycurl ou outra fonte autorizada.
- Envio de WhatsApp é simulado e registrado em `interactions`. Em produção, o adaptador seria WhatsApp Business API/Twilio.
- Agendamento é marcado no sistema. Em produção, integrar Calendly/Google Calendar.

Essas decisões reduzem risco operacional para o case, preservando arquitetura evolutiva e demonstração ponta a ponta.
