# Research: Melhorias Operacionais e de Confiabilidade do Monitor

## D1 — Como distinguir "erro de formatação" de outras falhas do Telegram

**Decision**: Em `src/telegram.py::_enviar_bloco`, detectar erro de formatação
verificando se a resposta HTTP tem `status_code == 400` e se o corpo (`resposta.text`
ou `resposta.json().get("description", "")`) contém, de forma case-insensitive, a
substring `"can't parse entities"` — mensagem de erro padrão e estável da API do
Telegram para `parse_mode` inválido. Quando detectado, fazer uma única tentativa
extra do mesmo bloco com `payload` sem a chave `parse_mode` (texto plano), antes de
levantar `FalhaExternaTelegram`.

**Rationale**: É a forma mais direta de diferenciar "o Telegram não entendeu a
formatação" (recuperável trocando para texto plano) de "o Telegram está fora do ar" ou
"token inválido" (não recuperável trocando o `parse_mode`). Reaproveita a estrutura de
retry por bloco já existente (`_enviar_bloco_com_retry`), sem introduzir biblioteca ou
abstração nova (Princípio VII).

**Alternatives considered**:
- Trocar globalmente para `MarkdownV2`: exigiria escapar manualmente todos os
  caracteres especiais (`_*[]()~\`>#+-=|{}.!`) em todo texto gerado pela LLM, um
  trabalho de escaping muito mais invasivo e arriscado de introduzir novos bugs de
  formatação — rejeitado por desproporcional ao problema (perder a notificação),
  quando o objetivo real é garantir entrega, não preservar negrito a todo custo.
- Tentar sempre as duas variantes (com e sem `parse_mode`) em paralelo: complexidade
  desnecessária; o fallback só precisa ocorrer no caminho de exceção.

## D2 — Como o watchdog verifica se o monitoramento está saudável

**Decision**: `src/watchdog.py` consulta a API pública do GitHub Actions —
`GET https://api.github.com/repos/{owner}/{repo}/actions/workflows/monitor-copom.yml/runs?per_page=5`
— autenticada com o `GITHUB_TOKEN` padrão injetado automaticamente pelo próprio
GitHub Actions no workflow do watchdog (permissão `actions: read` no workflow).
Repositório e dono são lidos das variáveis de ambiente padrão do runner
(`GITHUB_REPOSITORY`, no formato `owner/repo`). A lógica de decisão:
- Sem nenhuma execução retornada → não alerta (cold start, ainda sem dado suficiente).
- `created_at` da execução mais recente com mais de 30h → alerta de "ausência de
  execução".
- As últimas 3 execuções (`conclusion`) todas `"failure"` → alerta de "falhas
  repetidas", mesmo que dentro do intervalo de tempo esperado.
- Caso contrário → nenhum alerta.

**Rationale**: Reaproveita a mesma API já usada implicitamente pelo próprio GitHub
Actions, sem custo e sem exigir um `PAT` (personal access token) adicional como
secret — o `GITHUB_TOKEN` padrão já tem escopo de leitura suficiente para o próprio
repositório. O limiar de 30h dá margem sobre o baseline de 3h (Princípio V/constituição)
para tolerar atrasos pontuais de fila do GitHub Actions sem gerar alerta falso (SC-003).
3 falhas consecutivas é um número pequeno o bastante para não demorar a alertar, mas
grande o bastante para não confundir uma falha transitória isolada (já coberta pelo
retry interno de cada execução) com um problema sistêmico.

**Alternatives considered**:
- Guardar o timestamp da última execução bem-sucedida em `estado.json`: rejeitado —
  criaria uma segunda fonte de verdade sobre "quando rodou pela última vez",
  divergente da API do GitHub Actions, que já é a fonte de verdade real (mais robusta
  a um `estado.json` corrompido ou não commitado).
- Usar um serviço externo de heartbeat/monitoring (ex.: Healthchecks.io): violaria o
  Princípio I (nenhuma dependência de infraestrutura externa, mesmo que tier gratuito,
  sem justificativa forte) — a própria API do GitHub Actions já resolve o problema sem
  serviço adicional.

## D3 — Frequência e agendamento do watchdog

**Decision**: Novo workflow `.github/workflows/watchdog.yml`, agendado 1x/dia
(`cron: "0 12 * * *"`, horário fora das janelas densas de terça/quarta), com
`permissions: { contents: read, actions: read }`.

**Rationale**: O objetivo é detectar ausência *prolongada* (dezenas de horas), não
substituir o baseline de 3h já existente. Uma vez por dia é suficiente para cumprir
SC-002 (alerta em até 24h) sem consumir minutos de Actions desnecessariamente.

**Alternatives considered**: Rodar o watchdog a cada poucas horas — descartado por
não agregar valor (o limiar de alerta é de ~30h) e consumir mais minutos de execução
sem necessidade (Princípio VII).

## D4 — Onde inserir o link oficial nas mensagens

**Decision**: Concatenar o link ao final da `mensagem1` em `src/main.py`, fora do
prompt enviado à Anthropic — ver `verificar_comunicado` e `verificar_ata`. Formato:
`\n\n🔗 *Leia na íntegra*: <url>`, adicionado após `gerar_mensagens_comunicado`/
`gerar_analise_ata` retornarem e antes do envio via `enviar_mensagem` e do registro em
`historico`.

**Rationale**: Mantém o link fora do controle da LLM (elimina risco de reformatação ou
omissão pelo prompt) e garante presença em 100% das mensagens (SC-004), já que o
código sempre executa essa concatenação, independente do que a LLM gerou. Reaproveita
o padrão de formatação (`emoji *Rótulo*: conteúdo`) já usado nos templates de prompt
em `analise.py`, sem precisar tocar nos prompts.

**Alternatives considered**: Incluir a URL como instrução no próprio prompt da LLM —
rejeitado por risco de a LLM alterar, remover ou formatar incorretamente uma URL fixa
que não deveria ser objeto de geração de texto.

## D5 — Correção do CLAUDE.md

**Decision**: Remover a seção "Pendências conhecidas a validar com `/speckit-clarify`
antes de implementar" do `CLAUDE.md`, já que seu único item (endpoint de Comunicados)
está confirmado em `specs/001-monitor-decisoes-copom/contracts/bcb-api.md` e em
produção (`historico/comunicados/`).

**Rationale**: Evita que sessões futuras tratem como incerto algo já resolvido.

**Alternatives considered**: Manter a seção e só marcar o item como resolvido —
rejeitado por deixar uma seção vazia/morta no documento sem propósito.
