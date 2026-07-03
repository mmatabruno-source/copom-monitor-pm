# Feature Specification: Melhorias Operacionais e de Confiabilidade do Monitor

**Feature Branch**: `003-melhorias-operacionais-confiabilidade`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "Melhorias operacionais e de confiabilidade do monitor: (1) corrigir CLAUDE.md removendo a pendência desatualizada sobre o endpoint de Comunicados do BCB, que já foi confirmado e está em produção; (2) garantir que uma notificação no Telegram nunca seja perdida por erro de formatação Markdown do texto gerado pela LLM — se o Telegram rejeitar a formatação, tentar reenviar o mesmo bloco em texto plano antes de desistir; (3) criar um watchdog que alerte via Telegram se o workflow de monitoramento (monitor-copom.yml) parar de rodar ou falhar repetidamente, já que hoje só há alerta para falhas dentro de uma execução, não para ausência de execução; (4) incluir, ao final da mensagem 1 de cada fluxo (Comunicado e Ata), um link oficial do BCB para a página cronológica correspondente, formatado em negrito, consistente com o padrão de formatação já usado no projeto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Notificação nunca perdida por erro de formatação (Priority: P1)

Como usuário do monitor, quero sempre receber a notificação de uma decisão do Copom
mesmo que o texto gerado contenha um caractere que quebre a formatação em negrito do
Telegram, para que uma falha cosmética nunca me faça perder a informação de negócio
mais importante do sistema.

**Why this priority**: É o item de maior risco: se a formatação falhar hoje, a
mensagem inteira falha e o usuário não recebe a decisão — o propósito central do
projeto. Nenhuma outra melhoria tem esse potencial de dano se não for feita.

**Independent Test**: Simular o Telegram rejeitando um bloco por erro de formatação
(HTTP 400 com corpo indicando falha ao interpretar entidades) e confirmar que o
sistema entrega o mesmo conteúdo em texto simples, sem propagar falha nem duplicar
envio.

**Acceptance Scenarios**:

1. **Given** um bloco de mensagem com formatação inválida para o Telegram, **When** o
   Telegram rejeita o envio por erro de formatação, **Then** o sistema reenvia o mesmo
   bloco sem formatação especial e a notificação chega ao usuário.
2. **Given** um bloco de mensagem rejeitado por erro de formatação e a tentativa sem
   formatação também falhando por outro motivo (ex.: token inválido), **When** o
   sistema esgota as tentativas, **Then** o erro observável indica claramente que a
   notificação não foi entregue (não fica silencioso).
3. **Given** um envio de múltiplos blocos onde um bloco anterior já foi entregue com
   sucesso, **When** um bloco seguinte precisa do reenvio em texto simples, **Then** o
   bloco já entregue não é reenviado.

---

### User Story 2 - Alerta quando o monitoramento parar de rodar (Priority: P2)

Como usuário do monitor, quero ser avisado se a verificação automática parar de
acontecer (por qualquer motivo fora do controle do próprio código de verificação),
para que eu não descubra uma falha de infraestrutura só pela ausência prolongada de
notificações.

**Why this priority**: Hoje existe alerta só para falhas *dentro* de uma execução; a
ausência completa de execuções é um ponto cego que ataca a mesma garantia central do
item anterior (nunca perder uma decisão do Copom), mas por uma causa diferente
(agendamento parado, não erro de processamento).

**Independent Test**: Simular um cenário em que a última verificação bem-sucedida
está muito além do intervalo máximo esperado, ou em que as últimas verificações
falharam em sequência, e confirmar que um alerta é enviado ao usuário nesse caso e
não é enviado quando o monitoramento está funcionando normalmente.

**Acceptance Scenarios**:

1. **Given** a verificação automática não roda há muito mais tempo que o intervalo
   máximo normal entre execuções, **When** a checagem periódica de saúde é executada,
   **Then** o usuário recebe um alerta avisando que o monitoramento pode estar parado.
2. **Given** a verificação automática está rodando dentro do intervalo esperado,
   **When** a checagem periódica de saúde é executada, **Then** nenhum alerta é
   enviado.
3. **Given** as últimas execuções da verificação automática falharam repetidamente,
   **When** a checagem periódica de saúde é executada, **Then** o usuário recebe um
   alerta distinto indicando falhas repetidas (não apenas ausência de execução).

---

### User Story 3 - Link oficial na notificação (Priority: P3)

Como usuário do monitor, quero que a mensagem principal de cada notificação (Comunicado
ou Ata) inclua um link para a página oficial do Banco Central correspondente, para que
eu possa acessar rapidamente a fonte primária sem precisar procurar por conta própria.

**Why this priority**: Melhoria de conveniência, sem risco de perda de notificação —
prioridade menor que os itens de confiabilidade acima.

**Independent Test**: Processar uma nova publicação de cada tipo (Comunicado e Ata) e
verificar que a mensagem principal enviada e o histórico salvo contêm o link oficial
correto para aquele tipo de publicação, formatado de forma consistente com o resto da
mensagem.

**Acceptance Scenarios**:

1. **Given** uma nova publicação de Comunicado processada, **When** a mensagem
   principal é enviada ao usuário, **Then** ela contém o link oficial da página de
   Comunicados do Copom, em destaque igual aos demais rótulos de seção da mensagem.
2. **Given** uma nova publicação de Ata processada, **When** a mensagem principal é
   enviada ao usuário, **Then** ela contém o link oficial da página de Atas do Copom,
   em destaque igual aos demais rótulos de seção da mensagem.
3. **Given** qualquer uma das mensagens acima, **When** ela é salva no histórico do
   repositório, **Then** o link também está presente no registro salvo.

---

### User Story 4 - Documentação do projeto sem pendência resolvida (Priority: P4)

Como mantenedor do projeto (via sessões futuras do Spec Kit), quero que o `CLAUDE.md`
não liste como pendente algo que já foi confirmado e está em produção, para que
decisões futuras não sejam tomadas com base em uma premissa desatualizada.

**Why this priority**: Risco baixo e já não bloqueia nenhuma funcionalidade (o sistema
já processa Comunicados normalmente), mas é uma correção simples que evita confusão e
retrabalho em qualquer sessão futura que leia o `CLAUDE.md` antes de agir.

**Independent Test**: Ler o `CLAUDE.md` atualizado e confirmar que não há mais menção
ao endpoint de Comunicados como não confirmado.

**Acceptance Scenarios**:

1. **Given** o `CLAUDE.md` atual, **When** a documentação é revisada, **Then** a
   pendência sobre o endpoint de Comunicados é removida ou substituída por um registro
   de que já foi confirmado, sem contradizer o restante do documento.

---

### Edge Cases

- O que acontece se o Telegram rejeitar a formatação de um bloco e a tentativa em
  texto simples também for rejeitada por outro motivo? (coberto no Cenário 2 da User
  Story 1 — a falha deve ficar visível, não silenciosa.)
- O que acontece se a checagem periódica de saúde (User Story 2) ela mesma não
  conseguir avisar o usuário (ex.: Telegram indisponível)? Deve seguir a mesma regra
  já estabelecida no projeto para falha de notificação: tentativa única, falha
  silenciosa sem travar a checagem seguinte.
- O que acontece se não houver nenhuma execução anterior registrada (cold start) no
  momento da primeira checagem periódica de saúde? Não deve gerar alerta falso —
  deve ser tratado como "ainda sem dado suficiente para avaliar", não como falha.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE, ao falhar em enviar um bloco de mensagem ao Telegram
  especificamente por erro de formatação do texto, tentar reenviar o mesmo bloco sem
  formatação especial antes de considerar o envio como falho.
- **FR-002**: O sistema DEVE continuar tratando qualquer outro tipo de falha de envio
  (rede, autenticação, indisponibilidade do Telegram) exatamente como já trata hoje,
  sem alterar esse comportamento.
- **FR-003**: O sistema NUNCA DEVE reenviar um bloco que já foi confirmado como
  entregue com sucesso.
- **FR-004**: O sistema DEVE verificar periodicamente, de forma independente da
  verificação de novas publicações, se as execuções de verificação estão ocorrendo
  dentro do intervalo esperado.
- **FR-005**: O sistema DEVE alertar o usuário via Telegram quando a verificação
  automática não tiver rodado dentro do intervalo esperado.
- **FR-006**: O sistema DEVE alertar o usuário via Telegram quando as execuções mais
  recentes da verificação automática tiverem falhado repetidamente.
- **FR-007**: O sistema NÃO DEVE alertar o usuário quando a verificação automática
  estiver ocorrendo normalmente dentro do intervalo esperado.
- **FR-008**: O sistema DEVE incluir, na mensagem principal de cada notificação de
  Comunicado, um link para a página oficial de Comunicados do Copom no site do Banco
  Central.
- **FR-009**: O sistema DEVE incluir, na mensagem principal de cada notificação de
  Ata, um link para a página oficial de Atas do Copom no site do Banco Central.
- **FR-010**: O link incluído (FR-008, FR-009) DEVE seguir o mesmo padrão visual de
  destaque (rótulo em negrito) já usado nas demais seções da mensagem.
- **FR-011**: O registro salvo no histórico de cada publicação DEVE conter o mesmo
  link enviado ao usuário.
- **FR-012**: A documentação do projeto (`CLAUDE.md`) DEVE refletir que o endpoint de
  Comunicados do BCB já está confirmado e em uso em produção, sem listá-lo como
  pendência de validação.

### Key Entities

- **Checagem de saúde do monitoramento**: representa uma avaliação periódica e
  independente de se as execuções regulares de verificação (Comunicado/Ata) estão
  ocorrendo como esperado; não descreve uma nova publicação, apenas o estado
  operacional do próprio sistema de monitoramento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nenhuma notificação de decisão do Copom deixa de ser entregue ao usuário
  por causa exclusivamente de um erro de formatação de texto.
- **SC-002**: Uma interrupção do monitoramento automático (ausência de execuções ou
  falhas repetidas) é sinalizada ao usuário em até 24 horas após o início da
  interrupção.
- **SC-003**: Zero alertas falsos de interrupção do monitoramento são gerados durante
  operação normal, incluindo no primeiro dia após a implantação (cold start).
- **SC-004**: 100% das notificações principais de Comunicado e de Ata enviadas após a
  implementação contêm o link oficial correspondente, tanto na mensagem entregue
  quanto no histórico salvo.
- **SC-005**: A documentação do projeto não contém nenhuma referência desatualizada
  ao status do endpoint de Comunicados.

## Assumptions

- O intervalo máximo esperado entre execuções, para fins da User Story 2, é derivado
  do agendamento "baseline" já documentado no `CLAUDE.md` (a cada 3h), com margem de
  segurança — assume-se um limiar de alerta de aproximadamente 24 a 30 horas sem
  execução bem-sucedida para tolerar instabilidades pontuais da plataforma de
  agendamento sem gerar alertas falsos.
- A checagem periódica de saúde (User Story 2) roda com frequência muito menor que a
  verificação principal (ex.: uma vez por dia), pois seu objetivo é detectar ausência
  prolongada, não latência de poucas horas — já coberta pelo baseline existente.
- Os links oficiais de Comunicados e Atas (User Story 3) são páginas gerais
  (cronológicas), não o documento específico da reunião, pois a API do BCB não
  fornece hoje uma URL individual por Comunicado (diferente da Ata, que tem PDF
  específico, mas fora do escopo desta feature usar).
- "Erro de formatação" (User Story 1) é identificável a partir da resposta de erro
  retornada pelo Telegram para essa condição específica, distinguível de outros tipos
  de falha (rede, autenticação, indisponibilidade).
- Esta feature não introduz nenhum novo serviço externo além dos já usados pelo
  projeto (BCB, Anthropic, Telegram) e, para a User Story 2, a própria plataforma de
  execução agendada já em uso, mantendo a restrição de custo zero.
