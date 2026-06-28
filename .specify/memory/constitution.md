# Monitor de Decisões do Copom Constitution

## Core Principles

### I. Stack Mínimo e Custo Zero (NON-NEGOTIABLE)
O projeto MUST ser implementado em Python e executado exclusivamente via GitHub Actions
(cron), sem servidor dedicado. Toda dependência externa (hospedagem, API, agendamento)
MUST operar dentro de um tier gratuito. Nenhuma decisão de arquitetura pode introduzir
custo de infraestrutura, mesmo que marginal.
**Racional:** este é um projeto pessoal de aprendizado; custo zero é condição de
existência do projeto, não uma preferência de otimização.

### II. Armazenamento em Arquivos no Repositório
Todo histórico de publicações (Comunicados e Atas) e toda análise gerada MUST ser
persistido como arquivos JSON + Markdown dentro do próprio repositório Git, commitados
automaticamente pela GitHub Action. Nenhum banco de dados externo é permitido. O
arquivo `estado.json` MUST registrar o último `nroReuniao` processado, separadamente
para Ata e Comunicado.
**Racional:** Git como banco de dados elimina custo, garante durabilidade de anos sem
manutenção e torna o histórico navegável por humanos diretamente no GitHub.

### III. Segredos Nunca em Texto Plano (NON-NEGOTIABLE)
Tokens e chaves de API (Telegram, Anthropic) MUST ser fornecidos apenas via GitHub
Secrets. É proibido registrá-los em código, arquivos versionados, logs ou no histórico
de commits, em qualquer circunstância.

### IV. Idempotência e Resiliência (NON-NEGOTIABLE)
Nenhuma publicação já processada pode gerar uma segunda notificação. Uma publicação só
é marcada como processada em `estado.json` após a notificação ter sido enviada com
sucesso. Falha em qualquer chamada externa (API do BCB, API da Anthropic, Telegram)
MUST abortar a execução sem marcar a publicação como processada, deixando o trabalho
para a próxima execução do cron, e nunca deve corromper o histórico já salvo.
**Racional:** o robô roda sem supervisão; falhas parciais são esperadas e não podem se
tornar inconsistências permanentes.

### V. Fonte de Verdade é a API, Nunca o Calendário
A detecção de uma nova publicação MUST sempre ser feita por consulta à API oficial do
BCB, comparando o `nroReuniao` mais recente com o registrado em `estado.json`. O
calendário anual de reuniões do Copom MAY ser usado apenas como heurística para ajustar
a *frequência* de verificação (ex.: checagens mais frequentes nos dias típicos de
publicação), mas NUNCA como condição para decidir *se* o robô verifica a API. Reuniões
extraordinárias fora do calendário MUST continuar sendo detectadas dentro de um teto de
latência definido (baseline de verificação contínua, independente de calendário).

### VI. Comunicação Transparente em Português
Toda mensagem voltada ao usuário final (Telegram) MUST estar em português. Falhas em
chamadas externas MUST, sempre que possível, ser comunicadas ao usuário via Telegram
(ex.: aviso de que a API do BCB falhou e será tentada novamente), em vez de apenas
registradas em log silencioso — exceto quando o próprio Telegram for o componente
falho, caso em que a notificação de falha falha silenciosamente sem retry adicional.

### VII. Simplicidade sobre Otimização Prematura
Entre duas soluções igualmente corretas, a mais simples MUST prevalecer. Este é um
projeto de aprendizado pessoal: complexidade adicional (ex.: filas, workers, frameworks)
exige justificativa explícita e MUST ser rejeitada por padrão.

## Restrições Técnicas Adicionais

- **Modelo de IA:** Claude Sonnet (`claude-sonnet-4-6`) é o modelo usado para gerar
  resumos e análises críticas. O volume de chamadas é baixo (~16/ano), tornando custo
  irrelevante frente à qualidade analítica necessária para interpretar diagnóstico
  macroeconômico e nuances de tom.
- **Agendamento do cron (GitHub Actions, horários em UTC; Brasília é UTC-3 fixo, sem
  horário de verão desde 2019):**
  1. Baseline diário, todos os dias do ano: a cada 3h — garante teto de latência para
     reuniões extraordinárias fora do calendário típico.
  2. Janela densa de terça-feira (Ata, publicada 8h BRT): a cada 15 min entre
     10:45–13:00 UTC.
  3. Janela densa de quarta-feira (Comunicado, publicado a partir de 18h30 BRT): a cada
     15 min entre 21:15–23:45 UTC.
- **Limite de mensagem do Telegram:** análises que excedam 4096 caracteres MUST ser
  divididas em múltiplas mensagens sequenciais, nunca truncadas ou substituídas por link.

## Fluxo de Desenvolvimento (SDD)

Este projeto segue Spec-Driven Development via GitHub Spec Kit. Nenhum código MUST ser
escrito sem rastreabilidade a uma tarefa em `tasks.md`, que por sua vez deriva de
`plan.md` e `spec.md`. Ambiguidades na spec MUST ser sinalizadas ao usuário via
`/speckit-clarify` — nunca preenchidas silenciosamente por suposição. Cada tarefa
concluída de `tasks.md` MUST gerar um commit próprio, referenciando o ID da tarefa.

## Governance

Esta constituição tem precedência sobre qualquer decisão técnica tomada em `plan.md` ou
durante a implementação. Qualquer alteração de princípio MUST ser proposta e registrada
neste arquivo antes de ser aplicada ao código, com incremento de versão semântico:
MAJOR para remoção/redefinição incompatível de princípio, MINOR para adição de
princípio ou seção, PATCH para esclarecimentos sem mudança de regra. Toda revisão de
`plan.md` ou `tasks.md` MUST verificar conformidade com os princípios aqui definidos.

**Version**: 1.0.0 | **Ratified**: 2026-06-28 | **Last Amended**: 2026-06-28
