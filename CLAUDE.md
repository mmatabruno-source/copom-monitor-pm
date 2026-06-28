# CLAUDE.md — Contexto do projeto para o Claude Code

## O que é este projeto
Monitor automático das publicações do Copom (Banco Central do Brasil) — Comunicado e Ata —
que gera uma análise crítica orientada a negócio (impacto em portfólio de investimentos e
comunicação com clientes) e envia por Telegram. Histórico preservado no próprio repositório.

## Metodologia: Spec-Driven Development (GitHub Spec Kit)
Este projeto segue SDD via Spec Kit. **Antes de escrever ou alterar qualquer código**, sempre:

1. Leia `.specify/memory/constitution.md` — princípios não-negociáveis do projeto
2. Leia `specs/<feature>/spec.md` — requisitos da funcionalidade (formato EARS)
3. Leia `specs/<feature>/plan.md` — decisões técnicas já tomadas
4. Leia `specs/<feature>/tasks.md` — qual é a próxima tarefa pendente

**Nunca implemente algo que não esteja rastreável a uma tarefa em `tasks.md`.**
Se notar uma lacuna, contradição ou ambiguidade na spec, pare e sinalize ao usuário —
não assuma e não preencha a lacuna silenciosamente.

**Após concluir cada tarefa do `tasks.md`, faça commit referenciando o ID da tarefa**
(ex.: `git commit -m "T3.2: implementa extração de decisão do Comunicado"`). Um commit por
tarefa, não um commit gigante ao final — assim o histórico do Git documenta sozinho a
execução do SDD, tarefa por tarefa.

## Comandos do Spec Kit disponíveis neste projeto
- `/speckit-constitution` — cria ou atualiza os princípios do projeto
- `/speckit-specify` — cria ou atualiza o spec.md de uma funcionalidade
- `/speckit-clarify` — faz perguntas estruturadas sobre ambiguidades na spec
- `/speckit-plan` — gera o plan.md técnico a partir do spec.md
- `/speckit-tasks` — quebra o plan.md em tasks.md (tarefas atômicas)
- `/speckit-implement` — implementa o código seguindo o tasks.md, tarefa por tarefa
- `/speckit-analyze` — verifica consistência entre spec/plan/tasks
- `/speckit-checklist` — gera checklist de validação antes de considerar concluído

## Restrições conhecidas deste projeto (constituição resumida)
- **Linguagem:** Python
- **Execução:** GitHub Actions (cron), sem servidor dedicado
- **Custo:** zero — apenas serviços com tier gratuito
- **Armazenamento:** arquivos (JSON + Markdown) no próprio repositório Git, sem banco externo
- **Segredos:** token do Telegram, chat_id e chave da API Anthropic — apenas via GitHub
  Secrets, nunca em texto plano no código ou no histórico versionado
- **Idioma:** todas as mensagens ao usuário (Telegram) em português
- **Idempotência:** nenhuma publicação processada pode gerar uma segunda notificação
- **Resiliência:** falha numa execução não pode corromper o histórico nem travar a próxima
- **Fonte de verdade:** detecção de novidade sempre via API do BCB, nunca via calendário
  estimado de reuniões

## Pendências conhecidas a validar com `/speckit-clarify` antes de implementar
- Confirmar a URL exata e o payload do endpoint de **comunicados** do BCB — só o endpoint
  de **atas** foi testado e confirmado até agora

## Decisões já tomadas (clarificações resolvidas em 28/06/2026)
Estas decisões devem ser incorporadas ao `spec.md` e `plan.md` quando gerados via
`/speckit-specify` e `/speckit-plan` — não repetir o `/speckit-clarify` para estes pontos:

- **Notificação de falha:** quando uma chamada externa falhar (API do BCB, API da
  Anthropic ou Telegram), o sistema deve tentar avisar o usuário via Telegram (ex.:
  "⚠️ Falha ao buscar API do BCB, tentando novamente na próxima execução"). Se o próprio
  Telegram for o componente que falhou, a tentativa de aviso falha silenciosamente (sem
  retry adicional) — a execução não deve travar por isso.
- **Modelo Claude:** usar Claude Sonnet (atualmente `claude-sonnet-4-6`) para gerar
  resumos e análises. Volume baixíssimo (~16 chamadas/ano) torna o custo irrelevante;
  prioriza-se qualidade analítica sobre economia.
- **Mensagens longas no Telegram:** a análise completa da Ata pode exceder o limite de
  4096 caracteres por mensagem. Dividir em múltiplas mensagens sequenciais (não truncar,
  não substituir por link).
- **Agendamento do cron (3 camadas, todos os horários em UTC — Brasília é UTC-3 fixo,
  sem horário de verão desde 2019):**
  1. **Baseline (todos os dias do ano):** a cada 3h — garante detecção de reuniões
     extraordinárias fora do calendário típico, sem depender dele (RNF: fonte de verdade
     é sempre a API, nunca o calendário).
  2. **Janela densa de terça-feira** (dia típico de publicação da Ata, 8h BRT): a cada
     15 min entre 10:45–13:00 UTC (7:45–10:00 BRT).
  3. **Janela densa de quarta-feira** (dia típico de publicação do Comunicado, a partir
     de ~18h30 BRT): a cada 15 min entre 21:15–23:45 UTC (18:15–20:45 BRT).
  O calendário oficial do Copom **não** é usado para decidir *se* o robô verifica (isso
  seria depender do calendário como gatilho, proibido pela spec) — só para decidir a
  *frequência* de verificação em dias normais. Em qualquer outro dia, o baseline garante
  teto de latência de ~3h.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
