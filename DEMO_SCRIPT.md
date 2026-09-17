# Roteiro para o avaliador

Abra https://vigil-ai-mvp.streamlit.app/. O modo público contém dados sintéticos. Não precisa usar WhatsApp nem fornecer uma chave própria se o ambiente publicado estiver configurado.

1. Captação → Adicionar personas sintéticas de exemplo.
2. Demo guiada → Mariana Demo → Persona sintética → Analisar lead.
3. Gerar mensagem em Pré-evento → responder “Confirmo minha presença”. Observe status/indicadores.
4. Contexto pós-evento → mesmo lead → compareceu → interesse “priorização de vulnerabilidades/SOC 2” → salvar.
5. Demo guiada → Pós-evento → gerar mensagem → responder “Quero agendar uma reunião”.
6. Contexto pós-evento → data futura ISO com fuso → Marcar reunião agendada. Não é convite externo.
7. Evidências → mesmo lead → conferir ações/conversas/fonte → Baixar JSON.

## Fonte externa

Escolha Persona Demo Microsoft; seu emprego é fictício. Fonte Empresa pública → Q2283 → Consultar → conferir nome e descrição → confirmar correspondência → Analisar. Gere mensagem. URL/data e descrição provêm da consulta real; cargo e vínculo não são verificados. Indisponibilidade da fonte deve ser reportada, não substituída por invenção.

## Casos críticos

- Outro lead sintético enriquecido: “Confirmo presença” e depois “Não poderei participar”. Confirmados deve cair.
- “Por favor, não me envie mais mensagens”: bloqueio imediato, mesmo sem API. Tentar gerar novamente deve falhar. Reanalisar também não remove bloqueio.
- Mensagem antes de enriquecer: bloqueada.
- Resposta ambígua: revisão pendente pausa a régua; uma nova resposta inequívoca resolve.
- Reanalisar lead com reunião: estado de reunião permanece.
- Réguas → data do evento → T-7 → executar em lead não confirmado. Repetir não deve duplicar. Confirmado pula T-7, mas pode receber T-1. Opt-out/reunião não recebem mensagens.
- D+1 para lead ausente deve mencionar ausência, não presença nem demo vista.

## Limites

Dados e canais sintéticos devem permanecer identificados. Evidências do teste não comprovam 70% de comparecimento real. O worker usa relógio real apenas quando habilitado e enquanto o processo está ativo. Não há envio externo ou garantia de disponibilidade contínua neste host.

Se uma persona já estiver com reunião ou opt-out, use **Criar cópia sintética para novo teste** na Demo guiada. O original permanece preservado; a cópia começa com perfil não enriquecido e e-mail de teste novo.
