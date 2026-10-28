# Saiu do Seu Bolso

Dados oficiais de deputados e senadores apresentados em linguagem simples. O projeto começa pelas APIs da Câmara dos Deputados e do Senado Federal, sem scraping de HTML.

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

Ao coletar o Senado, o projeto também baixa, para o ano atual, as despesas da CEAPS, o comparecimento nas votações nominais e as autorias de cada senador, além da data em que cada um começou a atuar no mandato. No site, "projetos" conta só projetos de lei, PECs, projetos de decreto legislativo e de resolução; requerimentos e indicações entram apenas no total de autorias. Para informar outro ano:

```bash
uv run deputados coletar --casa senado --ano 2025
```

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

- Câmara: `https://dadosabertos.camara.leg.br/api/v2`
- Senado: `https://legis.senado.leg.br/dadosabertos`

## Próximas etapas

1. Criar a página de deputados.
2. Automatizar a atualização diária.
3. Adicionar análises de anomalias, sempre exibindo evidências e fontes.
