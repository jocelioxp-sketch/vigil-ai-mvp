# Validação da correção da auditoria

Data: 17/09/2026. Base anterior: 4eba3f18c54a3d92e9b2b794e9d1763193565119.

## Evidência local

`python -m unittest discover -s tests -v`: **32 testes passaram** na revisão final de 17/09/2026, sobre a base 27e316079a034688a9fe421cf4486d7e810f108b mais estas correções. Bancos temporários; nenhuma chamada paga durante a suíte.

Cinco regressões adicionais cobrem: recusa preservada após salvar contexto, bloqueio manual/automático nas duas fases, retomada após esclarecimento, negação de opt-out encaminhada intacta ao classificador, descadastro explícito independente da API e agendamento bloqueado até resolver revisão pendente. A interpretação do LLM nesses testes é simulada. Esta revisão não repetiu o teste completo publicado nem uma chamada real ao Claude; a evidência publicada abaixo corresponde à verificação anterior.

Cobertura: pré-condição de enriquecimento; opt-out sem depender de IA; persistência do bloqueio; recusa após confirmação; baixa confiança; reunião preservada após reanálise/edição; validação de data; integridade referencial; e-mail; intenção no histórico; falha da API; origem pública; indisponibilidade da fonte; rejeição de URL arbitrária; idempotência; janelas da régua; ausência de alegações livres; JSON inválido; opt-out concorrente à geração; migração do banco antigo; anonimização; orçamento de chamadas; execução concorrente; exigência de consentimento/fonte; contexto de classificação e fluxo de interface com AppTest.

Consulta real ao Wikidata Q2283 executada com sucesso: nome Microsoft, descrição e sites retornados com URL e timestamp. Isso prova acesso à fonte da organização, não vínculo profissional de uma persona ou qualidade de todos os dados da fonte.

## O que mudou desde a auditoria

- Supressão independente de estado e verificada antes/depois da geração.
- Regras de estado e contadores, baixa confiança e JSON validado.
- Réguas executáveis, relógio de demonstração, worker de um minuto, reservas únicas e tentativas limitadas.
- Enriquecimento público da organização com proveniência; modo sintético explícito.
- Templates factuais controlados; Claude escolhe tema e interpreta respostas.
- Schema único, migração preservando histórico, .env carregado antes de criar engine.
- Evidências exportáveis, anonimização, validação de e-mail, HTML escapado e limite de chamadas.
- README, roteiro e documentação consistentes com as abas e o comportamento.

## Limites dos testes

A suíte usa mocks de LLM, portanto não mede acurácia estatística nem substitui teste publicado com chave ativa. Não houve teste de carga, calendário externo, WhatsApp real ou PostgreSQL. A consulta pública cobre organização; dados profissionais individuais permanecem declarados. Worker depende do processo ativo. Conformidade jurídica integral e disponibilidade contínua não são alegadas.

## Verificação publicada da versão 2

A aplicação carregou com os registros antigos preservados após tratar módulos v1 retidos no hot deploy. No ambiente publicado: consulta Wikidata Q2283 retornou nome/descrição/sites; enriquecimento gravou proveniência; a chamada real ao Claude gerou mensagem com fato público atribuído; T-14 registrou uma única saída e repetição foi bloqueada; opt-out mudou o estado e nova tentativa retornou “Opt-out: novas mensagens estão bloqueadas.” O teste foi feito apenas com persona sintética. A automação contínua de relógio real foi deixada desabilitada; avaliador pode habilitar com a data do evento. Não foi feito teste de duração do worker ou suspensão do host.
