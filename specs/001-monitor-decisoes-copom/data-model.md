# Data Model: Monitor de Decisões do Copom

## Entidade: Comunicado

Representa a publicação oficial da decisão de juros.

| Campo | Tipo | Descrição |
|---|---|---|
| `nro_reuniao` | int | Identificador único da reunião, usado para idempotência |
| `data_referencia` | date | Data da 2ª sessão da reunião (data de divulgação) |
| `data_publicacao` | datetime | Timestamp de publicação reportado pela API do BCB |
| `selic_resultante` | decimal | Taxa Selic definida pela decisão |
| `variacao_pp` | decimal | Variação em pontos percentuais em relação à reunião anterior |
| `votacao` | string | "Unânime" ou descrição da divisão de votos |
| `texto_bruto` | string | Conteúdo original da publicação (fonte para auditoria) |
| `analise` | string | Resumo curto gerado (decisão objetiva + sinalização/tom) |
| `url_origem` | string | URL/PDF oficial, se disponível, para referência |

**Identidade/unicidade**: `nro_reuniao` é a chave única — nunca duas publicações de
Comunicado compartilham o mesmo `nro_reuniao`.

**Persistência**: `historico/comunicados/{nro_reuniao}.json` (todos os campos acima) e
`historico/comunicados/{nro_reuniao}.md` (versão legível, com a análise em destaque).

## Entidade: Ata

Representa a publicação com o detalhamento da decisão.

| Campo | Tipo | Descrição |
|---|---|---|
| `nro_reuniao` | int | Identificador único da reunião, usado para idempotência |
| `data_referencia` | date | Data de término da reunião |
| `data_publicacao` | datetime | Timestamp de publicação reportado pela API do BCB |
| `texto_estruturado` | object | Conteúdo completo, mantendo as seções originais (A/B/C/D) |
| `analise` | object | Análise crítica completa, com os 6 itens definidos em FR-005 |
| `url_pdf` | string | URL do PDF oficial da Ata |

**Identidade/unicidade**: `nro_reuniao` é a chave única.

**Relacionamento**: cada Ata pode referenciar a Ata imediatamente anterior (a de
`nro_reuniao` mais alto entre os já processados, antes do atual) para a comparação de
tom exigida por FR-006. Essa referência é resolvida em tempo de processamento (busca no
histórico), não armazenada como campo persistido.

**Persistência**: `historico/atas/{nro_reuniao}.json` e `historico/atas/{nro_reuniao}.md`.

## Entidade: Registro de Processamento (estado.json)

| Campo | Tipo | Descrição |
|---|---|---|
| `ultima_ata` | int \| null | `nro_reuniao` da última Ata processada com sucesso |
| `ultimo_comunicado` | int \| null | `nro_reuniao` do último Comunicado processado com sucesso |

**Ciclo de vida**: ambos os campos começam `null` na primeira execução (nenhum
histórico ainda). Cada campo só é atualizado **após** a notificação correspondente ter
sido confirmada como enviada com sucesso (ver research.md, seção 2). Atualização é
atômica por tipo de publicação — processar Comunicado não interfere no valor de
`ultima_ata` e vice-versa (suporta o cenário de processamento simultâneo de FR-014/edge
case já clarificado).

## Estrutura de mensagem ao Telegram (não persistida)

Não é uma entidade de dados, mas um contrato de saída: uma lista ordenada de blocos de
texto (cada um ≤4096 caracteres), enviados sequencialmente como mensagens separadas via
`sendMessage`, preservando a ordem dos 6 itens da análise (Ata) ou dos 2 itens
(Comunicado).
