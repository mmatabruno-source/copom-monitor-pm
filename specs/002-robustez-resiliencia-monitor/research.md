# Phase 0 Research: Robustez e Resiliência Operacional do Monitor

Todas as decisões abaixo seguem o Princípio VII da constituição (simplicidade sobre
otimização prematura): nenhuma biblioteca nova de retry/circuit-breaker é introduzida;
reaproveita-se o padrão simples já existente em `bcb_client._get`.

## D1 — Retry/backoff para Anthropic e Telegram

**Decision**: Para a Anthropic, usar o parâmetro nativo `max_retries` do SDK oficial
(`anthropic.Anthropic(api_key=..., max_retries=3)`) em vez de um loop manual — o SDK já
implementa retry com backoff para erros tipicamente transitórios (erro de conexão,
timeout, `429`, `5xx`), então declarar `max_retries=3` (em vez do padrão `2` do SDK, para
manter consistência com `TENTATIVAS = 3` do `bcb_client`) é suficiente. Para o Telegram,
que não tem um SDK com retry embutido (é `requests` puro), reaproveitar o mesmo padrão
manual já usado em `bcb_client._get` (loop de N tentativas com espera crescente),
aplicado por bloco (ver D3).

**Rationale**: Usar a funcionalidade nativa do SDK da Anthropic é mais simples e mais
correto do que reimplementar retry por cima de uma biblioteca que já retenta sozinha
(Princípio VII) — evita um retry duplicado (SDK tentando novamente por dentro enquanto
um loop externo também tenta). Para o Telegram, sem SDK, o padrão manual do BCB é a
opção mais simples disponível.

**Alternatives considered**: Biblioteca `tenacity` — rejeitada por adicionar dependência
externa para um padrão trivial já disponível nativamente (Anthropic) ou já implementado
manualmente no projeto (BCB/Telegram). Loop manual também para a Anthropic — rejeitado
por duplicar uma capacidade que o SDK já oferece.

## D2 — Retry criterioso na API do BCB

**Decision**: `bcb_client._get` passa a tratar como retentável apenas: erros de conexão
(`requests.RequestException`), status `>= 500`, e status `429` (respeitando o cabeçalho
`Retry-After` quando presente, com fallback para o backoff atual se ausente ou
inválido). Qualquer outro status `4xx` (ex.: `404`) é tratado como falha permanente —
levanta `FalhaExternaBCB` na primeira tentativa, sem novas tentativas.

**Rationale**: Evita desperdiçar ~6s em 3 tentativas para um erro que nunca vai se
resolver sozinho (ex.: número de reunião inexistente).

**Alternatives considered**: Tratar todo `4xx` como retentável (comportamento atual) —
rejeitado, é a causa raiz do desperdício de tempo identificado na auditoria.

## D3 — Evitar duplicação de blocos no Telegram

**Decision**: O retry (D1) é aplicado **por bloco**, dentro do laço existente em
`enviar_mensagem` que já itera bloco a bloco. Isso significa que, se o bloco 2 de 4
falhar, apenas o bloco 2 é tentado novamente — os blocos 1 (já entregue) não são
reenviados, e os blocos 3-4 só são enviados depois que o 2 tiver sucesso.

**Rationale**: Resolve a duplicação na raiz (nunca reenvia do início) sem precisar
persistir estado entre tentativas ou entre execuções — a mesma execução já sabe quais
blocos enviou.

**Alternatives considered**: Persistir em disco quais blocos já foram enviados para
permitir retomada entre execuções — rejeitado por complexidade desproporcional ao
risco (mensagem de Ata tem no máximo ~4-5 blocos; a janela de falha é de segundos).

## D4 — Não vazar o token do Telegram em logs/erros

**Decision**: Adicionar uma função `_sanitizar(texto, token)` em `telegram.py` que
substitui qualquer ocorrência literal do token por `***` antes que o texto entre em uma
`Exception`, em um `logger.error`/`logger.warning`, ou em uma mensagem passada para
`notificar_falha`. Aplicada no ponto onde a exceção é formatada (`_enviar_bloco`), única
função que constrói a URL com o token embutido.

**Rationale**: Único ponto do código onde o token entra na URL da requisição (`telegram.py:31`);
sanitizar ali cobre logs, mensagens de aviso de falha e qualquer outro consumidor da
exceção, sem precisar tocar em `main.py` ou `notificar_falha.py`.

**Alternatives considered**: Mascaramento automático do GitHub Actions (`::add-mask::`) —
já existe como camada adicional, mas não cobre a mensagem de aviso que o próprio robô
manda de volta ao Telegram; a sanitização na origem cobre os dois casos.

## D5 — Isolamento de falha entre Comunicado e Ata

**Decision**: `main()` passa a envolver cada chamada (`verificar_comunicado()` e
`verificar_ata()`) em um `try/except Exception` amplo, registrando a exceção inesperada
em log e avisando o usuário via `notificar_falha`, sem relançar. `python -m src.main`
portanto sempre termina com código de saída 0, e o step "Commitar histórico" do workflow
(que já roda incondicionalmente após o step anterior ter sucesso) continua rodando sempre,
persistindo o que cada fluxo bem-sucedido já gravou localmente.

**Rationale**: É a solução mais simples (Princípio VII) — não exige alterar o workflow
YAML (`if: always()` mais o cuidado de diferenciar "nada mudou" de "falha real"). Os
erros já esperados (`FalhaExternaBCB`, `FalhaExternaAnthropic`, `FalhaExternaTelegram`)
já são tratados dentro de cada função `verificar_*`; este `except Exception` amplo em
`main()` cobre apenas bugs/erros verdadeiramente inesperados (ex.: `KeyError` por um
campo novo da API do BCB), que hoje derrubam o processo inteiro.

**Alternatives considered**: Adicionar `if: always()` ao step de commit no workflow —
rejeitada como solução principal porque, sozinha, ainda exigiria que `main()` não
interrompesse a execução do segundo fluxo após uma falha no primeiro (o que já é
garantido pela chamada sequencial existente) e traria complexidade extra de step
condicional sem necessidade.

## D6 — Resiliência do push do estado para o Git

**Decision**: O step "Commitar histórico atualizado" do workflow passa a envolver
`git pull --rebase --autostash` + `git push` em um laço de até 3 tentativas com espera
entre elas (backoff simples em shell, sem ferramenta adicional). Se todas as tentativas
falharem, o mesmo step invoca `python -m src.notificar_falha` (via uma pequena
interface de linha de comando) para avisar o usuário via Telegram sobre o risco de uma
possível notificação duplicada na próxima execução (FR-011, decisão confirmada com o
usuário).

**Rationale**: Resolve o caso comum (falha transitória de rede) sem ferramentas novas;
para o caso raro de falha persistente, cumpre o padrão de aviso já estabelecido pela
constituição para as demais integrações externas.

**Alternatives considered**: Deixar o step falhar sem aviso (comportamento atual) —
rejeitado, é exatamente o gap identificado na auditoria e resolvido pela clarificação
com o usuário.

## D7 — Observabilidade mínima (resumo por execução)

**Decision**: `main()` acumula um dicionário simples (`resumo`) com o resultado de cada
fluxo (`verificado`, `processado`, `falhou`) e a duração total da execução, registrando-o
como uma única linha de log estruturada (`logger.info`) ao final. Não é persistido em
arquivo nem enviado ao Telegram — é apenas para leitura nos logs do GitHub Actions.

**Rationale**: Atende à necessidade de diagnóstico rápido sem violar o Princípio II
(nenhum armazenamento novo) nem introduzir um sistema de métricas.

**Alternatives considered**: Enviar o resumo por Telegram a cada execução — rejeitado,
geraria ruído (~1300 execuções/ano) incompatível com o Princípio VI de comunicação
enxuta e relevante ao usuário final.

## D8 — Versões fixas das dependências

**Decision**: Fixar em `requirements.txt`: `requests==2.34.2`, `anthropic==0.115.1`,
`pytest==9.1.1` (versões estáveis mais recentes disponíveis no PyPI no momento desta
mudança).

**Rationale**: Elimina o risco de uma atualização incompatível quebrar uma execução
agendada sem que isso seja uma decisão explícita do responsável pelo projeto.

**Alternatives considered**: Usar limites de versão compatível (`~=`) — rejeitado por
ainda permitir mudanças não revisadas dentro da faixa; para um projeto de baixíssimo
volume de execuções, a atualização manual e deliberada é mais simples e segura.

## D9 — Estratégia de testes para os módulos hoje sem cobertura

**Decision**: Usar `unittest.mock` (biblioteca padrão, já implícita no padrão de testes
existente) para simular `requests` e o cliente `anthropic`, sem introduzir bibliotecas de
teste adicionais (`responses`, `httpretty` etc.).

**Rationale**: Mantém a suíte de testes consistente com o padrão já usado no projeto
(`tests/unit/test_telegram.py`) e evita nova dependência para um volume de testes
pequeno.

**Alternatives considered**: Biblioteca `responses` para mockar HTTP — rejeitada por não
ser necessária dado o volume de casos de teste.
