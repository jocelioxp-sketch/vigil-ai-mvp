# Vigil.AI — Event Conversion Agent

**Aplicação:** https://vigil-ai-mvp.streamlit.app/  
**Entrega MBA AI Leader:** Jocélio de Souza Santos · case Vigil Summit.

MVP testável para captação → enriquecimento → confirmação → presença → follow-up → reunião. Claude interpreta respostas e seleciona o tema contextual; o motor determinístico aplica estados, bloqueios, réguas e textos com fatos controlados.

## Avaliar em 5 minutos

1. Abra **Captação** → **Adicionar personas sintéticas de exemplo**. Só adiciona as ausentes.
2. Em **Demo guiada**, escolha uma persona. Execute **Analisar lead · Enriquecer e pontuar** no modo sintético.
3. Gere uma mensagem pré-evento; responda “Confirmo minha presença”. Veja status, confiança e histórico.
4. Em **Contexto pós-evento**, marque presença e interesse observado; salve.
5. Em **Demo guiada**, selecione pós-evento, gere follow-up e responda “Quero agendar uma reunião”.
6. Em **Contexto pós-evento**, informe data futura **com fuso** e marque a reunião. Isso registra a reunião; não cria convite externo.
7. Confira o **Dashboard** e baixe o JSON na aba **Evidências**.

### Conferir fonte pública real

Escolha “Persona Demo Microsoft” (pessoa fictícia; nenhum vínculo profissional real afirmado). Selecione **Empresa pública (Wikidata)**, informe **Q2283**, consulte a fonte, confira a empresa e marque a confirmação. Execute a análise. Descrição, sites, URL e data da consulta ficam registrados; vínculo, cargo, porte e interesses permanecem declarados. Se a fonte falhar, não há validação pública inventada. Dados Wikidata podem conter erros e devem ser conferidos.

### Conferir regras e automação

Na aba **Réguas**, informe início do evento com fuso e avance T-14/T-7/T-3/T-1/D+0/D+1/D+3/D+7. A simulação só atua sobre personas sintéticas, com histórico separado da execução de relógio real. Executar a mesma janela de novo não duplica sua mensagem. Leads confirmados não recebem novos pedidos de confirmação; opt-out e reuniões encerram a comunicação.

Para execução automática, salve a data e habilite o checkbox. O worker processa a cada minuto **enquanto o processo estiver ativo**. Não garante execução quando a hospedagem suspende a aplicação. Para serviço contínuo, rode `python workflow.py` em processo supervisionado com o mesmo SQLite em armazenamento persistente.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configure sua própria ANTHROPIC_API_KEY no .env.
python seed.py
streamlit run app.py
```

Windows: `.venv\Scripts\activate` e `Copy-Item .env.example .env`.

No Streamlit Cloud, configure `ANTHROPIC_API_KEY` em **Settings → Secrets**, com sintaxe TOML: `ANTHROPIC_API_KEY = "sua-chave"`. Nunca inclua credenciais no GitHub. O modelo padrão é `claude-sonnet-4-5`; `ANTHROPIC_MODEL` permite configuração explícita. Uma chave ativa e limite disponível são necessários para testar o LLM.

O padrão é `DEMO_MODE=true`: cadastros sintéticos com e-mail `@example.invalid` ou `.demo`. Para trabalhar com dados reais, é obrigatório configurar `DEMO_PASSWORD` e desativar DEMO_MODE. Senha não substitui uma solução de autenticação/segregação de produção. Não use dados reais neste ambiente público de avaliação.

## Testes

```bash
python -m unittest discover -s tests -v
```

Testes usam bancos temporários e mocks de LLM. Cobrem defeitos da auditoria, migração de dados, opt-out durante geração, JSON inválido, idempotência, incerteza, fonte indisponível e estados. Não chamam a API paga nem enviam mensagens externas. Ver [VALIDATION.md](VALIDATION.md).

Recusas permanecem bloqueadas mesmo após salvar contexto e impedem mensagens manuais e automáticas nas duas fases. Uma nova resposta esclarecedora pode atualizar a decisão. Revisão pendente também impede registrar reunião; primeiro interprete uma resposta inequívoca de interesse.

## Arquivos

- [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md): requisitos, arquitetura, decisões e limites.
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md): roteiro e casos de borda.
- [architecture.mmd](architecture.mmd): arquitetura.
- `app.py`: interface; `agent.py`: LLM e comunicação controlada.
- `workflow.py`: elegibilidade, execução temporal e deduplicação.
- `enrichment.py`: consulta pública com proveniência.
- `db.py` e [schema.sql](schema.sql): SQLite, migração e estados.
- `seed.py`: personas; `tests/`: regressões.

## Limites explícitos

WhatsApp é uma caixa de saída **simulada**; não há credenciais de canal nem envios reais. Calendário é um registro local, sem reserva externa. Fonte pública cobre a **organização**, não valida todos os dados pessoais/profissionais. SQLite é a única opção implementada: PostgreSQL exige migração e driver, não basta trocar uma URL. Configure armazenamento persistente e backup antes de operar fora da demonstração; exportação JSON do avaliador não é backup completo. Dados existentes são migrados sem apagar histórico. Alteração de fonte/regra e idempotência são rastreáveis.

Se uma persona já estiver com reunião ou opt-out, use **Criar cópia sintética para novo teste** na Demo guiada. O original permanece preservado; a cópia começa com perfil não enriquecido e e-mail de teste novo.
