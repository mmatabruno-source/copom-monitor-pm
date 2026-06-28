# Feature Specification: Monitor de Decisões do Copom

**Feature Branch**: `001-monitor-decisoes-copom`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "Quero monitorar quando o Banco Central do Brasil publica um novo Comunicado ou uma nova Ata do Copom, e me notificar via Telegram com uma análise crítica, orientada a um Product Manager de investimentos, com histórico permanente das publicações."

## Clarifications

### Session 2026-06-28

- Q: Dentro das janelas densas de verificação (a cada 15 min), uma execução pode demorar
  mais que o intervalo e se sobrepor à próxima, criando risco de concorrência na escrita
  do registro de processamento e do histórico. Como evitar isso? → A: o sistema MUST
  garantir que apenas uma verificação seja executada por vez — uma nova verificação
  agendada não pode iniciar enquanto a anterior ainda estiver em andamento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alerta imediato da decisão de juros (Priority: P1)

Como Product Manager de investimentos, quando o Copom publica o Comunicado com a nova
decisão da Selic, quero receber uma notificação no Telegram com a decisão objetiva e o
tom da comunicação, sem precisar ler o comunicado oficial inteiro, para poder reagir
rapidamente no posicionamento de portfólio e na comunicação com clientes.

**Why this priority**: É o evento de maior frequência (8x/ano) e o de maior urgência —
o mercado já reage no mesmo instante da publicação; um atraso na notificação tem custo
de oportunidade direto.

**Independent Test**: Pode ser testado isoladamente publicando (ou simulando) um novo
Comunicado e verificando que uma mensagem chega ao Telegram em até uma janela de
verificação após a publicação, contendo Selic resultante, variação em p.p., votação e
tom.

**Acceptance Scenarios**:

1. **Given** o último Comunicado processado é o de nº N, **When** a API do BCB passa a
   informar um Comunicado nº N+1, **Then** o sistema extrai a decisão, gera um resumo
   curto (decisão + tom) e envia uma notificação no Telegram em português.
2. **Given** uma notificação de Comunicado já foi enviada com sucesso para o nº N+1,
   **When** o sistema verifica novamente a API e ainda vê o nº N+1 como o mais recente,
   **Then** nenhuma nova notificação é enviada.

---

### User Story 2 - Análise crítica completa da Ata (Priority: P2)

Como Product Manager de investimentos, quando o Copom publica a Ata da reunião, quero
receber uma análise crítica completa no Telegram — incluindo o que mudou na narrativa
do Copom desde a Ata anterior — para entender o racional completo por trás da decisão e
ajustar a leitura por classe de ativo e a mensagem a clientes.

**Why this priority**: Complementa a User Story 1 com profundidade analítica, mas ocorre
na semana seguinte ao Comunicado — a urgência é menor, pois o mercado já precificou a
decisão objetiva.

**Independent Test**: Pode ser testado isoladamente publicando (ou simulando) uma nova
Ata e verificando que a análise enviada contém, nesta ordem, decisão objetiva,
diagnóstico, balanço de riscos, sinalização com comparação explícita à Ata anterior,
leitura por classe de ativo e sugestão de mensagem ao cliente.

**Acceptance Scenarios**:

1. **Given** o último número de Ata processado é N, **When** a API do BCB passa a
   informar uma Ata nº N+1, **Then** o sistema busca o texto completo, compara com a
   Ata nº N já armazenada no histórico, gera a análise nos 6 itens definidos e envia ao
   Telegram, dividindo em múltiplas mensagens se exceder o limite de caracteres de uma
   mensagem.
2. **Given** não existe nenhuma Ata anterior no histórico (primeira execução do
   sistema), **When** uma Ata é processada, **Then** a análise é gerada normalmente,
   omitindo apenas a comparação de tom (que não tem base de comparação).

---

### User Story 3 - Histórico navegável de publicações e análises (Priority: P3)

Como Product Manager de investimentos, quero poder abrir o repositório em qualquer
momento futuro e encontrar todas as publicações já processadas e suas análises, para
acompanhar a evolução do discurso do Copom ao longo de um ciclo, sem depender de o robô
estar rodando no momento da consulta.

**Why this priority**: É valor cumulativo, não cria urgência própria — mas sem ele as
User Stories 1 e 2 perdem valor de longo prazo (a comparação de tom da US2 depende
diretamente deste histórico existir e ser confiável).

**Independent Test**: Pode ser testado abrindo o repositório (sem rodar o robô) e
confirmando que cada publicação processada anteriormente tem um arquivo legível
(Markdown) e um arquivo de dados (JSON) correspondente, navegável diretamente pela
interface do GitHub.

**Acceptance Scenarios**:

1. **Given** uma publicação (Comunicado ou Ata) foi processada com sucesso, **When** o
   usuário acessa o repositório, **Then** existe um arquivo `.md` legível e um `.json`
   com os dados brutos e a análise, ambos sob controle de versão.
2. **Given** o sistema processou múltiplas Atas ao longo do tempo, **When** uma nova Ata
   é processada, **Then** a análise referencia explicitamente a Ata imediatamente
   anterior already presente no histórico.

### Edge Cases

- O que acontece se a API do BCB estiver fora do ar no momento da verificação? O
  sistema deve abortar essa execução sem marcar nada como processado e, se possível,
  notificar a falha via Telegram; a próxima verificação agendada tenta novamente.
- O que acontece se a geração da análise (chamada à API da Anthropic) falhar após a
  publicação já ter sido buscada com sucesso? O sistema não marca a publicação como
  processada nem envia notificação parcial; tenta novamente na próxima verificação.
- O que acontece se o envio ao Telegram falhar após a análise ter sido gerada com
  sucesso? A publicação não é marcada como processada (para permitir nova tentativa de
  notificação); o sistema tenta notificar sobre essa falha por Telegram, mas se o
  próprio Telegram for o componente indisponível, essa tentativa de aviso falha
  silenciosamente sem retry adicional.
- O que acontece se uma reunião extraordinária do Copom ocorrer fora do calendário
  típico (fora das janelas de verificação mais frequentes)? O sistema ainda deve
  detectá-la dentro de um teto de latência definido, pois a detecção nunca depende do
  calendário — apenas a frequência de verificação varia por dia.
- O que acontece na primeira execução do sistema, sem nenhum histórico ainda salvo? O
  sistema deve processar a publicação mais recente disponível na API como se fosse nova,
  sem comparação com uma Ata anterior inexistente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST verificar periodicamente a API oficial do BCB para detectar
  um novo Comunicado, comparando o identificador da publicação mais recente com o último
  registrado no histórico.
- **FR-002**: O sistema MUST verificar periodicamente a API oficial do BCB para detectar
  uma nova Ata, usando o mesmo princípio de comparação do FR-001.
- **FR-003**: A detecção de novidade MUST depender exclusivamente da resposta da API
  oficial — o calendário de reuniões do Copom MUST NOT ser usado como condição para
  decidir se uma verificação resulta em algo novo (pode apenas influenciar a frequência
  das verificações).
- **FR-004**: Ao detectar um novo Comunicado, o sistema MUST extrair a decisão objetiva
  (Selic resultante, variação em p.p., votação) e gerar um resumo contendo a decisão
  objetiva e a sinalização/tom.
- **FR-005**: Ao detectar uma nova Ata, o sistema MUST extrair o conteúdo completo e
  gerar uma análise crítica contendo, nesta ordem: decisão objetiva; diagnóstico do
  Copom; balanço de riscos; sinalização (forward guidance) com o que mudou desde a Ata
  anterior; leitura por classe de ativo; sugestão de mensagem ao cliente.
- **FR-006**: A análise da Ata MUST comparar explicitamente o tom/discurso com a Ata
  imediatamente anterior já presente no histórico, quando esta existir.
- **FR-007**: O sistema MUST salvar permanentemente, no histórico do projeto, o conteúdo
  bruto de cada publicação processada e a análise gerada para ela, em formato legível
  por humanos (Markdown) e em formato estruturado (dados).
- **FR-008**: O sistema MUST notificar o usuário via Telegram, em português, a cada nova
  publicação processada com sucesso.
- **FR-009**: Notificações que excedam o limite de tamanho de uma única mensagem do
  Telegram MUST ser divididas em múltiplas mensagens sequenciais, preservando o conteúdo
  completo.
- **FR-010**: O sistema MUST NOT notificar duas vezes a mesma publicação — uma
  publicação só é considerada processada após a notificação ter sido enviada com
  sucesso.
- **FR-011**: Quando qualquer etapa externa (consulta à API do BCB, geração de análise,
  envio ao Telegram) falhar, o sistema MUST abortar o processamento daquela publicação
  sem marcá-la como processada, preservando a tentativa para a próxima verificação
  agendada.
- **FR-012**: Quando uma etapa externa falhar, o sistema MUST tentar notificar o usuário
  sobre a falha via Telegram, exceto quando o próprio envio ao Telegram for o componente
  que falhou.
- **FR-013**: Uma falha em qualquer execução MUST NOT corromper ou sobrescrever
  incorretamente o histórico de publicações e análises já salvas.
- **FR-014**: O sistema MUST garantir que apenas uma verificação seja executada por vez
  — uma nova verificação agendada não pode iniciar enquanto uma anterior ainda estiver
  em andamento, para evitar escrita concorrente do registro de processamento e do
  histórico.

### Key Entities

- **Comunicado**: publicação oficial do Copom com a decisão de juros. Atributos
  relevantes: identificador da reunião, data de publicação, Selic resultante, variação
  em p.p., resultado da votação, texto da decisão, análise gerada (resumo curto).
- **Ata**: publicação oficial do Copom com o detalhamento da decisão. Atributos
  relevantes: identificador da reunião, data de publicação, texto completo estruturado
  por seções, análise gerada (completa, com comparação à Ata anterior).
- **Registro de processamento**: estado que indica, separadamente para Comunicado e
  Ata, qual foi a última publicação processada com sucesso — usado para detectar
  novidade e garantir idempotência.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma notificação de novo Comunicado chega ao Telegram do usuário em até uma
  janela de verificação (no máximo poucas horas) após a publicação oficial.
- **SC-002**: Uma notificação de nova Ata chega ao Telegram do usuário em até uma janela
  de verificação após a publicação oficial, e a análise inclui comparação explícita com
  a Ata anterior em 100% dos casos em que uma Ata anterior exista no histórico.
- **SC-003**: Nenhuma publicação processada gera uma segunda notificação, em 100% das
  execuções, inclusive após falhas e reexecuções.
- **SC-004**: Uma falha em uma única verificação não impede o processamento correto na
  verificação agendada seguinte, sem necessidade de intervenção manual.
- **SC-005**: 100% do histórico de Comunicados e Atas processados está navegável e
  legível por humanos diretamente no repositório, mesmo sem o sistema estar em execução.

## Assumptions

- O endpoint de Comunicados da API do BCB segue um padrão de payload análogo ao de
  Atas (já confirmado), mas sua URL exata ainda não foi validada — essa validação é uma
  pendência técnica a ser resolvida antes da implementação do fluxo de Comunicado, não
  uma ambiguidade de requisito.
- O usuário final é uma única pessoa (o próprio operador do sistema); múltiplos
  destinatários estão fora de escopo desta versão.
- A frequência de verificação (mais densa em torno dos horários típicos de publicação,
  com uma verificação de base nos demais momentos) é tratada como decisão de
  implementação que não afeta o comportamento funcional descrito aqui — em nenhum caso
  ela substitui a API como fonte de verdade da detecção.
- Eventos fora de escopo nesta versão: coletiva de imprensa trimestral do Relatório de
  Política Monetária, Carta Aberta, decisões do CMN sobre a meta de inflação, dashboard
  visual, múltiplos destinatários de notificação.
