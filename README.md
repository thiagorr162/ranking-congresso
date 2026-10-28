# Ranking do Congresso

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

Para cada casa, o projeto também baixa, para o ano atual, as despesas da cota parlamentar, o comparecimento em sessões e as autorias de cada parlamentar, além da data em que cada um começou a atuar no mandato.

- **Câmara**: cota parlamentar (CEAP, com link da nota fiscal), presença nas sessões deliberativas do Plenário e proposições em que o deputado é proponente. A Câmara publica apenas as presenças, então uma falta é uma sessão deliberativa, ocorrida enquanto o deputado estava em exercício, sem presença registrada. Não há informação sobre justificativas.
- **Senado**: despesas da CEAPS, comparecimento nas votações nominais (com o motivo oficial das ausências) e autorias.

No site, "projetos" conta só projetos de lei, PECs, projetos de decreto legislativo e de resolução; requerimentos e indicações entram apenas no total de autorias. Para informar outro ano:

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

1. Adicionar análises de anomalias, sempre exibindo evidências e fontes.

## Publicação

O workflow `.github/workflows/atualizar.yml` coleta as duas casas, gera o site e publica no GitHub Pages todo dia, além de poder ser disparado manualmente.
