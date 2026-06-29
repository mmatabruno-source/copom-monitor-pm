# copom-monitor-pm

Monitora as publicações do Copom (Comunicado e Ata) e envia uma análise crítica via
Telegram — projeto pessoal construído com Spec-Driven Development (GitHub Spec Kit)
usando Claude Code.

## Como funciona

Um workflow do GitHub Actions (`.github/workflows/monitor-copom.yml`) roda em horários
fixos (cron), verifica se a API do Banco Central publicou um novo Comunicado ou uma
nova Ata, gera uma análise via API da Anthropic e notifica via Telegram. O controle do
que já foi processado fica em `estado.json`; o conteúdo bruto e a análise de cada
publicação ficam salvos permanentemente em `historico/`.

### Mapa do código (`src/`)

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Orquestra a verificação: checa Comunicado e Ata, decide o que processar |
| `bcb_client.py` | Busca dados na API pública do Banco Central (com retry) |
| `analise.py` | Monta os prompts e chama a API da Anthropic para gerar as mensagens |
| `telegram.py` | Envia as mensagens, dividindo em blocos se passar de 4096 caracteres |
| `historico.py` | Salva e lê as publicações já processadas (`historico/`) |
| `estado.py` | Guarda o último `nro_reuniao` processado de cada tipo (`estado.json`) |
| `notificar_falha.py` | Avisa via Telegram quando uma chamada externa falha |
| `teste_comunicado.py` / `teste_ata.py` | Scripts avulsos para testar mudanças de prompt sem afetar `estado.json`/`historico/` |

### Por que as coisas foram feitas assim — documentação de decisões

Este projeto foi construído com Spec-Driven Development (GitHub Spec Kit): toda decisão
relevante — e o porquê dela — está documentada em `specs/001-monitor-decisoes-copom/`
**antes** de qualquer linha de código ser escrita. Para entender o raciocínio por trás
de uma escolha (não só o que o código faz, mas por que foi feito assim), comece por:

| Documento | O que você encontra ali |
|---|---|
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | Princípios não-negociáveis do projeto (custo zero, idempotência, fonte de verdade é sempre a API, etc.) |
| [`specs/001-monitor-decisoes-copom/spec.md`](specs/001-monitor-decisoes-copom/spec.md) | Requisitos funcionais, histórias de usuário e as clarificações que resolveram ambiguidades |
| [`specs/001-monitor-decisoes-copom/plan.md`](specs/001-monitor-decisoes-copom/plan.md) | Decisões técnicas (stack, armazenamento, agendamento do cron) e por que foram tomadas |
| [`specs/001-monitor-decisoes-copom/contracts/`](specs/001-monitor-decisoes-copom/contracts/) | Contratos das APIs externas (BCB, Anthropic, Telegram) — inclusive as inconsistências de nomenclatura entre Comunicado e Ata |
| [`specs/001-monitor-decisoes-copom/research.md`](specs/001-monitor-decisoes-copom/research.md) | Pesquisa e alternativas consideradas antes de cada decisão técnica |
| [`specs/001-monitor-decisoes-copom/tasks.md`](specs/001-monitor-decisoes-copom/tasks.md) | Quebra de tarefas que guiou a implementação, tarefa por tarefa |
| [`CLAUDE.md`](CLAUDE.md) | Como o projeto é mantido com IA (Claude Code) e a metodologia adotada |

## Configuração necessária

Em Settings → Secrets and variables → Actions do repositório, cadastre:

| Secret | Para quê |
|---|---|
| `ANTHROPIC_API_KEY` | gerar as análises (Claude Sonnet) |
| `TELEGRAM_BOT_TOKEN` | enviar as mensagens |
| `TELEGRAM_CHAT_ID` | identificar para quem enviar |

Nenhum segredo deve aparecer em texto plano no código ou no histórico do Git.

## Rodar localmente

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python -m src.main
```

Para rodar a suíte de testes (não faz nenhuma chamada externa real):

```bash
pip install pytest ruff
python -m pytest -q
ruff check .
```

## Testar mudanças no texto das mensagens sem afetar produção

Os scripts `src/teste_comunicado.py` e `src/teste_ata.py` geram e enviam mensagens para
o Telegram a partir de uma reunião real do Copom, **sem** alterar `estado.json` nem
`historico/`. Também é possível disparar via GitHub Actions (workflow_dispatch) usando
`teste-comunicado.yml` / `teste-ata.yml`, informando o número da reunião.

## Se algo der errado

- **O robô parou de notificar**: confira se o workflow `Monitor Copom` está rodando em
  Actions → o GitHub desativa automaticamente cron jobs de repositórios sem nenhum commit
  por 60+ dias (a execução do próprio cron NÃO conta como atividade para esse efeito).
  Como o Monitor Copom só comita quando há publicação nova (~16x/ano), isso seria um risco
  real; por isso existe o workflow `.github/workflows/keepalive.yml`, que roda a cada 30
  dias e cria um commit vazio só para resetar esse contador — não deveria ser necessário
  reativar nada manualmente, mas se mesmo assim acontecer, basta reativar em Settings →
  Actions.
- **Uma chamada externa falhou** (API do BCB, Anthropic ou Telegram): o robô tenta de
  novo automaticamente (API do BCB) ou aborta sem marcar a publicação como processada,
  de forma que a próxima execução do cron tenta de novo sozinha. Você deve receber um
  aviso no Telegram sobre a falha (exceto se o próprio Telegram for o componente
  falho — nesse caso, olhe os logs da execução em Actions).
- **`estado.json` ou algum arquivo em `historico/` parece corrompido**: o histórico é
  versionado no Git, então basta consultar commits anteriores (`git log -- estado.json`)
  para recuperar uma versão íntegra.
