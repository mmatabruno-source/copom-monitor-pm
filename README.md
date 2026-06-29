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
  Actions → o GitHub desativa automaticamente cron jobs de repositórios inativos por
  60+ dias. Se isso acontecer, basta reativar manualmente em Settings → Actions.
- **Uma chamada externa falhou** (API do BCB, Anthropic ou Telegram): o robô tenta de
  novo automaticamente (API do BCB) ou aborta sem marcar a publicação como processada,
  de forma que a próxima execução do cron tenta de novo sozinha. Você deve receber um
  aviso no Telegram sobre a falha (exceto se o próprio Telegram for o componente
  falho — nesse caso, olhe os logs da execução em Actions).
- **`estado.json` ou algum arquivo em `historico/` parece corrompido**: o histórico é
  versionado no Git, então basta consultar commits anteriores (`git log -- estado.json`)
  para recuperar uma versão íntegra.
