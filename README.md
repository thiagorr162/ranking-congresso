# Ranking do Congresso

Dados oficiais de deputados e senadores apresentados em linguagem simples: gastos da cota parlamentar, presença em sessões, projetos apresentados e custo da campanha eleitoral. Tudo vem de APIs e arquivos de dados abertos da Câmara dos Deputados, do Senado Federal e do TSE, sem scraping de HTML (veja [Fontes](#fontes)).

## Configuração

```bash
uv sync
```

## Coleta

```bash
# Câmara e Senado
uv run deputados coletar --casa todas

# Uma casa específica
uv run deputados coletar --casa camara
uv run deputados coletar --casa senado
```

Os arquivos são gravados em `data/raw/<casa>/parlamentares.json`. Cada arquivo informa a fonte, o instante da coleta e os registros em um formato comum.

Para cada casa, o projeto também baixa, para o ano atual, as despesas da cota parlamentar, o comparecimento em sessões e as autorias de cada parlamentar, além da data em que cada um começou a atuar no mandato.

- **Câmara**: cota parlamentar (CEAP, com link da nota fiscal), presença nas sessões deliberativas do Plenário e proposições em que o deputado é proponente. A Câmara publica apenas as presenças, então uma falta é uma sessão deliberativa, ocorrida enquanto o deputado estava em exercício, sem presença registrada. Não há informação sobre justificativas.
- **Senado**: despesas da CEAPS, comparecimento nas votações nominais (com o motivo oficial das ausências) e autorias.

No site, "projetos" conta só projetos de lei, PECs, projetos de decreto legislativo e de resolução; requerimentos e indicações entram apenas no total de autorias. Para informar outro ano:

```bash
uv run deputados coletar --casa senado --ano 2025
```

## Eleições

Os dados de campanha (custo, dinheiro público, doadores, fornecedores, votos e patrimônio declarado) vêm dos arquivos do TSE, que somam cerca de 2 GB por eleição. Por isso eles não são baixados na atualização diária: um comando gera um resumo pequeno, só com os parlamentares em exercício, e esse resumo fica versionado em `eleicoes/`.

```bash
# Requer data/raw/<casa>/parlamentares.json (rode a coleta antes)
uv run deputados coletar-eleicoes
```

- Os arquivos brutos ficam em `data/tse/` (ignorado pelo git) e são reaproveitados nas execuções seguintes.
- Deputados são ligados à última eleição geral; senadores, às duas últimas, porque o mandato é de 8 anos. A troca para a eleição seguinte acontece sozinha em 1º de fevereiro, quando a nova legislatura toma posse.
- A ligação entre parlamentar e candidato é feita pelo nome completo e pela UF. O CPF dos candidatos é usado só em memória, para achar o patrimônio da eleição anterior, e não é gravado. Suplentes de senador não têm campanha própria e ficam sem esses dados.
- O workflow `.github/workflows/eleicoes.yml` refaz o resumo no dia 1 de cada mês (ou manualmente) e faz commit apenas se algo mudou.

## Site

Depois da coleta, gere a página estática:

```bash
uv run deputados construir-site --ano 2026
uv run deputados servir-site
```

Abra `http://localhost:8000`. A pasta `dist/` fica pronta para publicação no GitHub Pages.

## Qualidade

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Fontes

Todos os dados vêm de canais oficiais de dados abertos: APIs e arquivos publicados pelos próprios órgãos para download. O projeto não faz scraping de páginas HTML.

| Fonte | Canal | O que usamos |
|---|---|---|
| Câmara dos Deputados | API (`https://dadosabertos.camara.leg.br/api/v2`) | lista de deputados, nome completo e histórico de exercício |
| Câmara dos Deputados | Arquivos anuais (`https://dadosabertos.camara.leg.br/arquivos`) | eventos, presença nas sessões, proposições e autores |
| Câmara dos Deputados | Arquivo anual da cota (`https://www.camara.leg.br/cotas`) | despesas da cota parlamentar (CEAP), com link da nota fiscal |
| Senado Federal | API (`https://legis.senado.leg.br/dadosabertos`) | lista de senadores, mandatos, votações nominais e projetos |
| Senado Federal | API administrativa (`https://adm.senado.gov.br/adm-dadosabertos`) | despesas da cota parlamentar (CEAPS) |
| TSE | Portal de dados abertos (`https://dadosabertos.tse.jus.br`) | candidatos, bens declarados, prestação de contas e votação |

Por usar apenas canais oficiais, a coleta não depende do layout de nenhuma página e cada número exibido no site aponta para a fonte. O risco que resta é um órgão mudar o formato de uma API ou de um arquivo (o TSE, por exemplo, às vezes renomeia colunas). Nesse caso a coleta falha com erro no GitHub Actions, sem publicar dados errados, e basta ajustar o código.

### Comparações

As equivalências exibidas junto aos gastos ("equivalente a X salários mínimos") não são coletadas automaticamente. Os valores de referência ficam em `web/comparacoes.json`, cada um com a fonte oficial e a data, e devem ser revisados ao menos uma vez por ano (salário mínimo e pisos mudam em janeiro).

## Próximas etapas

1. Adicionar análises de anomalias, sempre exibindo evidências e fontes.

## Publicação

O workflow `.github/workflows/atualizar.yml` coleta as duas casas, gera o site e publica no GitHub Pages todo dia, além de poder ser disparado manualmente. Ele usa o resumo eleitoral já versionado em `eleicoes/`, atualizado pelo workflow mensal descrito em [Eleições](#eleições).
