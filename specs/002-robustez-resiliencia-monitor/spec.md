# Feature Specification: Robustez e Resiliência Operacional do Monitor

**Feature Branch**: `002-robustez-resiliencia-monitor`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Robustecer o monitor do Copom contra falhas parciais e reforçar sua confiabilidade operacional", cobrindo: isolamento de falha entre os fluxos de Comunicado e Ata; resiliência do push do estado/histórico; retry/backoff nas chamadas à Anthropic e ao Telegram; retry mais criterioso na API do BCB; mitigação de duplicação de mensagens longas no Telegram; eliminação de vazamento do token do Telegram em logs/erros; observabilidade mínima (resumo por execução); cobertura de testes para módulos hoje sem testes; e versões fixas das dependências.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nenhuma notificação duplicada mesmo com falha parcial (Priority: P1)

Como destinatário das notificações no Telegram, quero nunca receber uma notificação duplicada do mesmo Comunicado ou Ata, mesmo quando a outra publicação processada na mesma execução falhar depois, para poder confiar em cada alerta recebido sem precisar checar manualmente se já tinha visto aquele conteúdo.

**Why this priority**: É a garantia mais crítica do projeto — a constituição do projeto já trata idempotência como princípio não-negociável. Uma falha aqui corrói a confiança no robô mais do que qualquer outra falha listada.

**Independent Test**: Simular a execução processando com sucesso o Comunicado e depois forçar uma falha no processamento da Ata na mesma execução; verificar que, na execução seguinte, o Comunicado não é notificado de novo e a Ata continua sendo tentada.

**Acceptance Scenarios**:

1. **Given** o Comunicado de uma reunião foi notificado com sucesso e seu estado foi persistido nesta execução, **When** o processamento da Ata da mesma execução falha em seguida, **Then** a próxima execução não reenvia a notificação do Comunicado.
2. **Given** o processamento da Ata falhou nesta execução, **When** a próxima execução roda, **Then** o robô tenta processar a Ata normalmente, como se a tentativa anterior não tivesse acontecido.

---

### User Story 2 - Recuperação automática de falhas passageiras nos serviços externos (Priority: P2)

Como destinatário das notificações, quero que falhas passageiras nos serviços externos (API do BCB, API da Anthropic, Telegram) sejam resolvidas automaticamente dentro da mesma execução sempre que possível, para não ficar até 3 horas sem receber uma decisão importante do Copom por causa de uma instabilidade momentânea de um desses serviços.

**Why this priority**: Reduz diretamente a latência percebida pelo usuário e o número de execuções desperdiçadas, sem exigir intervenção humana.

**Independent Test**: Simular uma falha transitória isolada (ex.: um erro momentâneo) em cada uma das três integrações e verificar que a execução se recupera sozinha e conclui o processamento, sem esperar a próxima execução agendada.

**Acceptance Scenarios**:

1. **Given** a API do BCB responde com um erro tipicamente transitório na primeira tentativa, **When** o robô tenta novamente dentro da mesma execução, **Then** o processamento conclui normalmente sem intervenção externa.
2. **Given** a API da Anthropic ou o Telegram respondem com um erro tipicamente transitório (ex.: limite de taxa, sobrecarga), **When** o robô tenta novamente dentro da mesma execução, **Then** o processamento conclui normalmente.
3. **Given** a API do BCB responde com um erro permanente (ex.: reunião inexistente), **When** o robô decide se tenta novamente, **Then** ele não insiste em novas tentativas para esse erro.

---

### User Story 3 - Nenhum segredo exposto em logs ou mensagens (Priority: P3)

Como responsável técnico pelo projeto, quero ter certeza de que o token do bot do Telegram nunca apareça em texto legível em logs do GitHub Actions ou em mensagens de erro devolvidas ao próprio Telegram, para não precisar revogar credenciais em caráter de urgência após um incidente.

**Why this priority**: É uma garantia de segurança da constituição do projeto (segredos nunca em texto plano); o risco é baixo em frequência mas alto em impacto caso se concretize.

**Independent Test**: Forçar um erro de rede na chamada ao Telegram e inspecionar o texto de log gerado e o texto de qualquer aviso de falha reenviado ao usuário, confirmando a ausência do token em ambos.

**Acceptance Scenarios**:

1. **Given** uma chamada à API do Telegram falha por erro de rede, **When** o sistema registra o erro em log, **Then** o texto do log não contém o token de acesso.
2. **Given** uma chamada à API do Telegram falha por erro de rede, **When** o sistema tenta avisar o usuário sobre a falha, **Then** a mensagem de aviso não contém o token de acesso.

---

### User Story 4 - Resumo objetivo de cada execução (Priority: P4)

Como responsável técnico, quero um resumo objetivo do que aconteceu em cada execução do robô (o que foi verificado, o que foi processado, se houve falha), para diagnosticar problemas rapidamente sem precisar ler logs brutos linha a linha.

**Why this priority**: Melhora a manutenibilidade e reduz o tempo de diagnóstico, mas não afeta diretamente a confiabilidade percebida pelo destinatário das notificações.

**Independent Test**: Rodar o robô (ou um teste que simule uma execução completa) e verificar que ao final existe um resumo legível contendo o que foi verificado, o que foi notificado e quaisquer falhas ocorridas.

**Acceptance Scenarios**:

1. **Given** uma execução completa do robô, **When** ela termina (com ou sem falha), **Then** existe um resumo registrado indicando quais publicações foram verificadas, quais foram notificadas e quais falharam.

---

### User Story 5 - Cobertura de testes para os módulos críticos ainda sem testes (Priority: P5)

Como responsável técnico, quero que os módulos hoje sem testes automatizados (cliente da API do BCB, geração de análise, histórico local, notificação de falha) tenham testes cobrindo cenários de sucesso e de falha, para poder alterar o código no futuro com confiança de que uma garantia existente não foi quebrada.

**Why this priority**: Protege as demais garantias desta funcionalidade no longo prazo, mas não tem efeito operacional imediato por si só.

**Independent Test**: Rodar a suíte de testes automatizados e confirmar que os módulos listados têm casos de teste cobrindo pelo menos um caminho de sucesso e um caminho de falha cada.

**Acceptance Scenarios**:

1. **Given** a suíte de testes automatizados do projeto, **When** ela é executada, **Then** os módulos de cliente da API do BCB, geração de análise, histórico local e notificação de falha têm casos de teste cobrindo sucesso e falha.
2. **Given** a suíte de testes automatizados, **When** ela é executada, **Then** existe um teste do fluxo principal cobrindo o cenário em que um dos dois processamentos falha depois do outro ter sido concluído com sucesso na mesma execução.

---

### User Story 6 - Dependências com versão travada (Priority: P6)

Como responsável técnico, quero que as dependências externas do projeto tenham versão travada, para que uma atualização não controlada de uma biblioteca não quebre uma execução agendada sem aviso prévio.

**Why this priority**: Reduz um risco de baixa frequência mas de fácil prevenção; é a mudança de menor esforço entre todas as listadas.

**Independent Test**: Inspecionar o arquivo de dependências do projeto e confirmar que cada dependência tem uma versão específica declarada, não um intervalo aberto.

**Acceptance Scenarios**:

1. **Given** o arquivo de dependências do projeto, **When** ele é inspecionado, **Then** cada dependência declara uma versão específica.

---

### Edge Cases

- O que acontece se o Comunicado for processado e notificado com sucesso, mas a Ata falhar logo em seguida, na mesma execução? O estado do Comunicado deve ser preservado e persistido; a falha da Ata não deve impedir essa persistência nem gerar uma notificação incompleta.
- O que acontece se a API do BCB retornar um erro permanente (ex.: reunião inexistente)? O sistema não deve insistir em novas tentativas para esse tipo de erro.
- O que acontece se o envio de uma análise longa dividida em múltiplos blocos falhar no meio do envio e precisar ser retomado? Os blocos já entregues com sucesso não devem ser reenviados.
- O que acontece se a persistência durável do estado processado (commit e envio ao repositório remoto) falhar mesmo depois de novas tentativas, após a notificação já ter sido entregue ao usuário? Ver Questão de Clarificação abaixo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST garantir que uma falha no processamento de uma publicação (Ata ou Comunicado) não impeça a persistência durável do resultado já concluído com sucesso da outra publicação processada na mesma execução.
- **FR-002**: O sistema MUST persistir de forma durável o estado de uma publicação processada somente depois que a notificação correspondente tiver sido entregue com sucesso ao Telegram.
- **FR-003**: O sistema MUST tentar novamente, dentro da mesma execução, operações que falharem por motivo tipicamente transitório junto às APIs do BCB, da Anthropic e do Telegram, antes de desistir e adiar o processamento para a próxima execução agendada.
- **FR-004**: O sistema MUST distinguir falhas permanentes (ex.: recurso inexistente) de falhas tipicamente transitórias (ex.: indisponibilidade momentânea, limite de taxa) ao decidir se deve tentar novamente uma chamada à API do BCB, evitando novas tentativas quando a falha for permanente.
- **FR-005**: Ao retomar o envio de uma análise dividida em múltiplas mensagens do Telegram após uma falha parcial, o sistema MUST evitar reenviar blocos que já haviam sido entregues com sucesso.
- **FR-006**: O sistema MUST impedir que o token de acesso ao Telegram apareça em texto legível em logs de execução ou em mensagens de aviso de falha enviadas ao usuário.
- **FR-007**: Ao final de cada execução, o sistema MUST registrar um resumo objetivo do que foi verificado e do que foi processado (publicações verificadas, publicações notificadas, falhas ocorridas), permitindo diagnóstico sem inspecionar logs linha a linha.
- **FR-008**: O sistema MUST ter testes automatizados cobrindo cenários de sucesso e de falha dos seguintes componentes: cliente da API do BCB, geração de análise (parsing e extração de dados), carregamento de histórico local e notificação de falha.
- **FR-009**: O sistema MUST ter um teste automatizado que verifique o comportamento do fluxo principal quando um dos dois processamentos (Comunicado ou Ata) falha depois que o outro já foi concluído com sucesso na mesma execução.
- **FR-010**: O sistema MUST utilizar versões fixas de suas dependências externas, de modo que uma atualização de biblioteca não controlada pelo projeto não altere o comportamento de uma execução agendada.
- **FR-011**: Quando a persistência durável do estado processado falhar mesmo após novas tentativas, o sistema MUST avisar o usuário via Telegram que a notificação já foi entregue mas o estado pode não ter sido salvo, alertando sobre o risco de uma possível notificação duplicada na próxima execução — seguindo o mesmo padrão de aviso de falha já usado para as demais integrações externas do projeto.

### Key Entities

- **Resumo de Execução**: representa o resultado consolidado de uma execução do robô — quais publicações foram verificadas, quais foram notificadas com sucesso, quais falharam e em qual etapa. Usado para diagnóstico rápido, não é armazenado no histórico de publicações.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um cenário onde o processamento de uma das duas publicações falha depois que a outra já foi notificada com sucesso na mesma execução, a publicação bem-sucedida nunca é notificada uma segunda vez em execuções subsequentes.
- **SC-002**: Falhas transitórias simuladas em qualquer uma das três integrações externas (BCB, Anthropic, Telegram) são recuperadas automaticamente dentro da mesma execução, sem exigir espera pelo próximo ciclo do cron.
- **SC-003**: Em nenhum cenário de teste ou execução real auditada o token do Telegram aparece em texto legível em logs ou em mensagens enviadas ao usuário.
- **SC-004**: Um responsável técnico consegue identificar o resultado de qualquer execução (o que foi verificado, processado, e se houve falha) lendo apenas o resumo gerado, sem abrir o log bruto.
- **SC-005**: A suíte automatizada de testes cobre, com casos de sucesso e de falha, os quatro módulos hoje sem testes (cliente do BCB, análise, histórico, notificação de falha) e o cenário de falha parcial do fluxo principal — verificável pela suíte passando no CI.
- **SC-006**: Uma atualização externa de uma dependência não instalada explicitamente pelo projeto não altera o comportamento de uma execução agendada, pois toda dependência tem versão fixa declarada.

## Assumptions

- O ambiente de execução continua sendo GitHub Actions (cron), sem mudança de infraestrutura, custo ou serviços externos além dos já utilizados (BCB, Anthropic, Telegram, Git).
- "Falha transitória" refere-se a erros tipicamente recuperáveis em minutos (indisponibilidade momentânea, limite de taxa), não a interrupções prolongadas do serviço externo — para interrupções prolongadas, o comportamento esperado continua sendo adiar o processamento para a próxima execução agendada, como já ocorre hoje.
- O número exato de tentativas e o tempo de espera entre elas para cada integração serão definidos na fase de planejamento técnico (`plan.md`), seguindo o padrão simples já usado pelo cliente da API do BCB, sem introduzir bibliotecas ou infraestrutura adicional (princípio de simplicidade da constituição).
- Persistir "de forma durável" significa que a alteração está commitada e enviada (push) ao repositório Git remoto — gravação apenas local no runner efêmero não conta como persistida, pois é descartada ao final da execução.
- A cobertura de testes exigida (FR-008, FR-009) cobre os principais caminhos de sucesso e de falha de cada módulo listado; não é exigida cobertura exaustiva de cada ramo de código.
