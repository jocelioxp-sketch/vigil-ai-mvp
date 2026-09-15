# Documentação Técnica — Vigil.AI Event Conversion Agent

## 1. Arquitetura da solução

A solução foi desenhada como um MVP transacional orientado a estado. Cada lead possui um status de funil e um histórico de interações. O agente de IA não controla toda a aplicação de forma irrestrita: ele opera dentro de ferramentas e regras de negócio explícitas.

### Camadas
1. **Entrada** — formulário web de inscrição.
2. **Persistência** — banco relacional com leads, interações e ações do agente.
3. **Enriquecimento** — consolida dados declarados e sinais profissionais em resumo e score.
4. **LLM / agente** — Claude gera mensagens e classifica respostas.
5. **Motor de regras** — aplica transições de estado do funil a partir da intenção detectada.
6. **Canal** — WhatsApp como canal principal; no MVP, envio é simulado e auditável.
7. **Dashboard** — visão operacional de inscritos, confirmados, presentes e reuniões.

Estados principais: `INSCRITO → ENRIQUECIDO → CONFIRMADO → PRESENTE → FOLLOW_UP_QUENTE → REUNIAO_AGENDADA`.

## 2. Stack tecnológico justificado

### LLM — Anthropic Claude
Escolhido por aderência ao case e bom desempenho em uso de ferramentas, classificação de intenção e geração contextual. O modelo é chamado apenas em tarefas nas quais linguagem adiciona valor; transições críticas permanecem determinísticas.

### Framework de agente — SDK nativo Anthropic
Foi escolhido em vez de LangChain/CrewAI para reduzir abstrações, dependências e custo cognitivo no MVP. A arquitetura permite migrar depois para um framework de orquestração se houver aumento de complexidade.

### Banco — SQL relacional
O domínio é naturalmente relacional: lead, interações, ações e reuniões. O MVP usa SQLite pela simplicidade local; produção recomendada: PostgreSQL/Supabase.

### Orquestração
No MVP, as ações são acionadas pela interface para tornar a demonstração previsível. Em produção, um scheduler/workflow (n8n, Celery, Temporal ou filas gerenciadas) executaria as réguas por data e eventos.

### Canal — WhatsApp + e-mail de fallback
WhatsApp tende a ter menor fricção para confirmação próxima ao evento. E-mail é adequado para conteúdo mais longo, agenda e material corporativo. O MVP registra o canal em uma caixa de saída simulada.

### Deploy
Streamlit Cloud/Render/Railway. Para produção, separar frontend/backend e usar Postgres gerenciado.

## 3. Réguas de comunicação

### Pré-evento
Objetivo: confirmação >70% e redução de no-show.

- **T-14 dias:** mensagem de boas-vindas personalizada por cargo/setor/interesse.
- **T-7:** conteúdo relevante para o perfil do lead + pedido de confirmação.
- **T-3:** se ainda não confirmou, mensagem curta com agenda e benefício central.
- **T-1:** confirmado recebe lembrete logístico; não confirmado recebe último CTA.
- **Dia do evento:** lembrete matinal com horário/local.
- **Opt-out:** encerra comunicações imediatamente.

Regras:
- Lead score alto recebe mensagem mais consultiva e conteúdo relacionado ao cargo.
- Quem não respondeu às duas primeiras mensagens recebe texto menor e CTA binário.
- Quem confirmou deixa de receber pedidos de confirmação.
- Quem recusou não entra em nova tentativa pré-evento.

Exemplo:
“Mariana, como CISO da Atlas Bank, imaginei que a trilha sobre SOC 2 e priorização contínua de vulnerabilidades possa ser especialmente útil. O Vigil Summit reunirá líderes de segurança para discutir exatamente esse cenário. Posso confirmar sua presença?”

### Pós-evento
- **D+0 (até 2h):** agradecimento contextual para presentes.
- **D+1:** follow-up citando palestra/demo/interesse observado.
- **D+3:** CTA direto para reunião de 20–30 min.
- **D+7:** último contato; sem resposta, lead vai para nutrição.

Regras:
- Presente + interesse em demo = prioridade máxima.
- Presente sem interesse explícito = conteúdo consultivo antes do CTA.
- No-show = comunicação distinta (“sentimos sua ausência”) e convite para demo remota.
- Resposta com intenção de reunião muda status para `FOLLOW_UP_QUENTE`.

Exemplo:
“Mariana, vi que seu maior interesse na demo foi o dashboard de risco ligado a SOC 2. Posso reservar 25 minutos com nosso especialista para mostrar como esse fluxo ficaria aplicado ao contexto de uma instituição financeira?”

## 4. Estratégia de dados e personalização

### Coleta
Dados declarados no formulário: nome, e-mail, telefone, cargo, empresa, setor, porte, LinkedIn opcional e interesse em segurança.

### Armazenamento
O banco separa perfil (`leads`), mensagens (`interactions`) e decisões (`agent_actions`). Isso permite auditoria e explicação das ações do agente.

### Enriquecimento
No MVP, o enriquecimento combina cargo, setor, porte, LinkedIn declarado e interesse informado. Em produção, podem ser adicionadas fontes públicas/profissionais permitidas e provedores B2B, sempre respeitando termos de uso e base legal.

### Personalização
O agente recebe perfil, resumo enriquecido, score e últimas interações. O prompt exige uso de pelo menos um dado real do lead e proíbe invenção de fatos.

### LGPD
- consentimento explícito no cadastro para comunicação do evento e desdobramentos comerciais;
- minimização de dados;
- finalidade específica;
- opt-out imediato;
- trilha de auditoria;
- exclusão/anonimização sob solicitação;
- em produção, retenção configurável e controles de acesso.

## 5. Três decisões estratégicas principais

### 1. Agente limitado por regras, não autonomia irrestrita
LLM gera/entende linguagem; mudanças críticas de status seguem regras determinísticas. Isso reduz comportamento imprevisível e facilita auditoria.

### 2. WhatsApp como canal primário, e-mail como fallback
O objetivo de confirmação exige baixa fricção. E-mail continua relevante para conteúdo corporativo e materiais extensos.

### 3. Arquitetura de MVP simples, porém substituível
SQLite, envio simulado e enriquecimento local reduzem tempo de implementação. Todos estão encapsulados de forma que possam ser trocados por Postgres, WhatsApp Business API e provedor externo sem reescrever a lógica principal.

### Alternativas descartadas
- **CrewAI/multiagentes:** complexidade sem benefício proporcional para um funil linear.
- **RAG/vector database:** não existe um corpus documental amplo que justifique embeddings neste MVP.
- **Automação 100% via n8n:** boa para produção, mas reduziria transparência do código principal na avaliação.

## 6. Plano dos primeiros 5 dias

### Dia 1 — domínio e dados
- definir estados do funil;
- criar schema SQL;
- cadastrar personas sintéticas;
- desenhar contratos de ferramentas do agente.

### Dia 2 — agente e memória
- integrar Claude;
- gerar mensagens contextualizadas;
- persistir interações e decisões.

### Dia 3 — pré-evento
- implementar regras de confirmação;
- classificar respostas;
- testar confirma/recusa/opt-out/dúvidas.

### Dia 4 — pós-evento
- registrar presença e interesse;
- gerar follow-up contextual;
- implementar reunião agendada.

### Dia 5 — dashboard, testes e deploy
- dashboard de pipeline;
- teste ponta a ponta;
- deploy público protegido;
- revisão da documentação.

## 7. Cenário de escala — 10 eventos simultâneos

A arquitetura passaria a ser multi-tenant/multi-evento. Adicionaríamos `events`, `segments`, `campaign_rules` e `event_leads`. Prompts, timings e conteúdo seriam configuráveis por evento e setor, sem alterar o núcleo do agente. Workflows seriam executados por filas e workers, com isolamento por `event_id`. O canal, enriquecimento e calendário seriam adaptadores plugáveis.

A personalização seria controlada por configuração: manufatura, saúde, financeiro e governo teriam conjuntos distintos de mensagens, campos de interesse e políticas de compliance, enquanto o motor de estados permaneceria o mesmo.

## 8. Como validar a solução

O avaliador deve conseguir:
1. cadastrar ou selecionar um lead sintético;
2. enriquecer e visualizar score;
3. gerar mensagem pré-evento com Claude;
4. simular resposta e observar a mudança de estado;
5. marcar presença e interesse em uma demo;
6. gerar follow-up pós-evento;
7. marcar reunião;
8. confirmar a atualização do dashboard.
