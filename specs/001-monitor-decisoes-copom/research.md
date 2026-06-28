# Research: Monitor de Decisões do Copom

## 1. Cliente HTTP para as integrações externas

**Decision**: usar `requests` para BCB e Telegram; usar o SDK oficial `anthropic` para
a chamada de geração de análise.

**Rationale**: BCB e Telegram são APIs REST simples (GET/POST com JSON), sem
necessidade de recursos avançados de SDK. `anthropic` SDK oficial cobre formatação de
mensagens, streaming (não usado aqui) e tratamento de erros específicos da API de
forma mais robusta que requisições HTTP cruas.

**Alternatives considered**: `httpx` (assíncrono) — rejeitado por desnecessário dado o
volume de chamadas (~16/ano, sequenciais, sem concorrência real); SDK próprio do
Telegram (`python-telegram-bot`) — rejeitado por ser orientado a bots interativos
(polling, handlers), enquanto aqui só é necessário `sendMessage` pontual.

## 2. Estrutura de estado e idempotência

**Decision**: `estado.json` com formato `{"ultima_ata": <nroReuniao>, "ultimo_comunicado": <nroReuniao>}`,
atualizado e commitado **somente após** a notificação ao Telegram ter sido confirmada
com sucesso (HTTP 200 da API do Telegram).

**Rationale**: Garante FR-010/FR-011 — nenhuma publicação é marcada como processada
antes de o usuário efetivamente ser notificado. Se a execução falhar em qualquer ponto
anterior, `estado.json` permanece inalterado e a próxima execução do cron reprocessa a
mesma publicação do início.

**Alternatives considered**: marcar como processado logo após buscar o conteúdo (antes
da notificação) — rejeitado porque, se o Telegram falhar depois, o usuário nunca seria
notificado e o sistema acharia que já processou (viola FR-010 implicitamente, criando
notificação "perdida" sem possibilidade de retry).

## 3. Execução serializada (FR-014)

**Decision**: usar a chave `concurrency` do GitHub Actions no nível do workflow, com
`group: monitor-copom` e `cancel-in-progress: false`.

**Rationale**: `cancel-in-progress: false` garante que uma execução nova **espera** a
anterior terminar em vez de cancelá-la — importante porque cancelar uma execução no
meio poderia deixar o histórico em estado parcial (ex.: arquivo `.md` salvo mas commit
não realizado). Esperar é mais seguro que cancelar neste domínio.

**Alternatives considered**: lock manual via arquivo no repositório — rejeitado por
adicionar complexidade (criação/remoção/limpeza de lock órfão) que o recurso nativo do
GitHub Actions já resolve sem custo.

## 4. Geração da análise crítica (prompt da Anthropic)

**Decision**: dois prompts distintos e fixos (não configuráveis em runtime): um para
Comunicado (decisão + tom, 2 itens) e um para Ata (6 itens, na ordem definida em
FR-005). O prompt da Ata recebe o texto da Ata atual e, quando existir, o texto da Ata
anterior armazenada em `historico/atas/`, pedindo explicitamente a comparação de tom.

**Rationale**: Prompts fixos e versionados no código (não em configuração externa)
mantêm rastreabilidade via Git e evitam a complexidade de um sistema de templates
dinâmico para um caso de uso de baixíssimo volume.

**Alternatives considered**: prompt único parametrizado por tipo de publicação —
rejeitado porque a estrutura de saída (2 itens vs. 6 itens) é suficientemente diferente
para justificar prompts separados e mais simples de revisar individualmente.

## 5. Divisão de mensagens longas no Telegram

**Decision**: função utilitária que recebe o texto completo da análise e o divide em
blocos de até 4096 caracteres, preferencialmente quebrando em limites de parágrafo
(linha em branco) mais próximos do limite, para não cortar uma frase no meio.

**Rationale**: Atende FR-009 sem necessidade de resumir ou truncar conteúdo. Quebra por
parágrafo preserva legibilidade.

**Alternatives considered**: truncar e linkar para o arquivo `.md` no histórico —
rejeitado anteriormente nesta mesma sessão de decisão com o usuário (já registrado nas
restrições técnicas da constituição).

## 6. Pendência técnica: endpoint de Comunicados

**Decision**: validar a URL e o payload reais do endpoint de Comunicados como a
primeira tarefa de implementação do fluxo de Comunicado (antes de codar
`bcb_client.py` para esse fluxo), por inspeção manual da resposta da API.

**Rationale**: Constitution e spec.md já marcam isso como pendência conhecida, não
ambiguidade de requisito — é validação técnica, não decisão de produto.

**Atualização (28/06/2026)**: listagem confirmada via navegador (`GET
.../comunicados?quantidade=N`). O payload real diverge da hipótese original em dois
pontos — ver `contracts/bcb-api.md`:
1. Vem envelopado em `{"conteudo": [...]}`, não como array na raiz.
2. O identificador é `nro_reuniao` (snake_case), enquanto Atas usa `nroReuniao`
   (camelCase) — os dois endpoints **não** seguem a mesma convenção de nomes.

**Atualização (28/06/2026, segunda validação)**: endpoint de detalhes confirmado.
Mesmo padrão de envelope `"conteudo"` da listagem (lista de um único item). Campo de
texto completo: `textoComunicado` (HTML). Confirmado também que **nenhum dos dois
endpoints de Comunicado** retorna campos estruturados de Selic resultante/variação/
votação — esses dados existem só como texto livre, exigindo extração via análise da
Anthropic (já era o desenho original, sem mudança de arquitetura). `detalhes_comunicado`
em `src/bcb_client.py` ajustado para desembrulhar o envelope. Pendência técnica de
Comunicado encerrada (T005a + T005b).

**Atualização (28/06/2026, terceira validação — Atas)**: a nota de risco sobre Atas
nunca ter sido testada de fato (ver `contracts/bcb-api.md`) foi resolvida. `atas` e
`atas_detalhes` também usam o envelope `{"conteudo": [...]}`, confirmando que esse é o
padrão geral da API do BCB (não uma particularidade de Comunicados). Nomes de campo
(`nroReuniao` camelCase, `textoAta`, `urlPdfAta`, `dataPublicacao`) confirmados iguais à
hipótese original. `src/bcb_client.py` (`listar_atas`, `detalhes_ata`) ajustado para
desembrulhar o envelope, no mesmo padrão de Comunicados.

**Alternatives considered**: nenhuma — é uma verificação obrigatória antes de codar,
não uma escolha de design.

## 7. Geração do workflow do GitHub Actions

**Decision**: um único arquivo `monitor-copom.yml` com três entradas `schedule:` (cron
de 3 camadas), `concurrency` no nível do workflow, `permissions: contents: write`, e um
job único que executa `python -m src.main`, seguido de um passo de commit condicional
(só commita se `git status --porcelain` não estiver vazio).

**Rationale**: Um job único é suficiente dado que toda a lógica de decisão (o que
processar) já vive em `main.py`; múltiplos jobs adicionariam complexidade de
orquestração sem benefício real para este volume.

**Alternatives considered**: jobs separados para Ata e Comunicado — rejeitado porque
FR-014 exige execução serializada de qualquer forma, e jobs separados tornariam o
controle de concorrência mais complexo (duas `concurrency groups` precisariam
coordenar a mesma escrita em `estado.json`).
