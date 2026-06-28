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
- `/speckit.constitution` — cria ou atualiza os princípios do projeto
- `/speckit.specify` — cria ou atualiza o spec.md de uma funcionalidade
- `/speckit.clarify` — faz perguntas estruturadas sobre ambiguidades na spec
- `/speckit.plan` — gera o plan.md técnico a partir do spec.md
- `/speckit.tasks` — quebra o plan.md em tasks.md (tarefas atômicas)
- `/speckit.implement` — implementa o código seguindo o tasks.md, tarefa por tarefa
- `/speckit.analyze` — verifica consistência entre spec/plan/tasks
- `/speckit.checklist` — gera checklist de validação antes de considerar concluído

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

## Pendências conhecidas a validar com `/speckit.clarify` antes de implementar
- Confirmar a URL exata e o payload do endpoint de **comunicados** do BCP — só o endpoint
  de **atas** foi testado e confirmado até agora

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
