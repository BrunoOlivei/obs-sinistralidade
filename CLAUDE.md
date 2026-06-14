# CLAUDE.md — Observatório de Sinistralidade da Saúde Suplementar

> Memória de bordo do projeto. Lida pelo Claude Code a cada sessão.
> Contém as decisões já tomadas para que não precisem ser rediscutidas.

## O que é o projeto

Pipeline de dados ponta a ponta sobre os **dados abertos da ANS** (Agência
Nacional de Saúde Suplementar). Ingere demonstrações contábeis, cadastro de
operadoras e beneficiários, calcula **sinistralidade** por operadora/região e
entrega indicadores para um dashboard.

> Sinistralidade = despesas assistenciais ÷ receitas de contraprestação.
> É o principal indicador de desempenho operacional do setor de saúde suplementar.

## Objetivo (importante para todas as decisões)

**Passaporte para vaga**, não vitrine técnica. Toda escolha de ferramenta é
guiada por "isso aparece nas vagas brasileiras de engenharia de dados?", não
por necessidade técnica pura. O projeto é peça de portfólio para conseguir
entrevista.

## Pergunta de negócio (a âncora de tudo)

> Quais operadoras e regiões combinam sinistralidade elevada com crescimento de
> despesa assistencial acima da mediana — e em quais procedimentos esse custo
> está concentrado?

Sobe a escada analítica: descritivo → diagnóstico → prescritivo.

## Stack final (TRAVADA — não rediscutir sem motivo forte)

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem/ambiente | Python 3.12+ com UV, em WSL (Ubuntu 24.04) | terreno do dev; WSL evita inferno de JVM no Windows |
| Processamento | **PySpark** (local agora → Databricks depois) | palavra-chave nº1 nas vagas; uma API só, coerente |
| Ingestão | `httpx` (streaming) + `beautifulsoup4` (parse do índice FTP) | desafio é tratamento, não ferramenta |
| Transformação/marts | **dbt** (`dbt-databricks`) | alto retorno de contratação; entra na fase de marts |
| Armazenamento/arquitetura | **Delta Lake** + medalhão bronze/silver/gold | pedido nominalmente nas vagas |
| Nuvem | **Azure Databricks** + Unity Catalog + Workflows | "Azure Databricks" é o combo mais pedido no BR |
| Orquestração | **Databricks Workflows** (nativo) | simplicidade; Airflow ficou para projeto futuro |
| Visualização | **Power BI** (modo Import na gold) | dev já domina; mercado pede |
| Qualidade | `ruff` + `mypy` + `pytest` + GitHub Actions (CI/CD) | sinal de senioridade; vagas sênior pedem |

### Deliberadamente FORA (não instalar/usar neste projeto)
- **Polars** e **DuckDB** — reservados para um projeto-irmão futuro (Airflow sem Databricks). Não são palavra-chave, só diferencial técnico.
- **Airflow / Dagster / Prefect** — orquestração externa fica para o projeto-irmão. Aqui é Workflows nativo.
- **pandas** como ferramenta principal — processamento é PySpark. (Pode aparecer como dependência transitiva.)
- Streaming / Kafka / Kubernetes — dados da ANS são batch trimestral; seria teatro.

## Princípio de custo (CRÍTICO)

**Desenvolver tudo localmente (PySpark local, custo zero). Subir para o Azure só
no FIM, numa janela paga, curta e planejada. Teto de gasto: R$100.**

O Databricks NÃO é necessário pelo volume (núcleo cabe em centenas de MB após
agregação). É usado pela palavra-chave de vaga, não pela escala.

Armadilha conhecida: o trial de 14 dias de DBUs do Databricks exige assinatura
pay-as-you-go com limite de gastos REMOVIDO. Por isso a proteção é manual:
**budget alert no Azure (50/80/95%)**. As VMs do Azure são cobradas por baixo
mesmo com DBUs grátis. Travas de custo: auto-termination 10 min, cluster single
node, budget alert, e só subir no fim.

> Runbook detalhado do "dia de subida" existe à parte (Fases 0–6).

## Arquitetura de pastas

```
obs-sinistralidade/
├── pyproject.toml        # config UV + dependências
├── .env.example          # OBS_ANS_BASE_URL, janela de competência, etc.
├── README.md
├── data/                 # NUNCA versionar (regenerável)
│   ├── landzone/
│   │   ├── zips/         # ZIPs como baixados da ANS (ex: zips/demonstracoes_contabeis/)
│   │   └── csv/          # CSVs extraídos dos ZIPs (ex: csv/demonstracoes_contabeis/)
│   ├── bronze/           # Delta tables — CSV lido e persistido sem transformação
│   ├── silver/           # Delta tables — limpo e conformado
│   └── gold/             # Delta tables — marts prontos pro consumo
├── src
│   ├── config/           # Settings (Pydantic) — caminhos, janela, rede
│   ├── core/             # models.py (domínio) + base.py (classes ABSTRATAS / contratos)
│   ├── ingestion/        # discoverer (parse FTP) · downloader · ans_ingestor
│   ├── processing/       # transformers concretos por dataset (bronze→silver→gold)
│   ├── storage/          # (gancho) escrita DuckDB/Delta
│   ├── pipelines/        # entry points executáveis
│   └── utils/            # logging
├── tests/                # espelha src/
├── notebooks/            # discovery exploratório (descartável)
└── scripts/              # tarefas avulsas
```

## Princípios de design (OO)

- `core/` define **contratos abstratos** (`FileDiscoverer`, `Downloader`,
  `Extractor`, `Ingestor`, `Transformer`) e tipos de domínio. Não depende de
  ninguém — evita import circular, mantém o domínio estável.
- Implementações concretas herdam dos contratos e são montadas por
  **composição / injeção de dependência** nos pipelines. Trocar fonte ou formato
  = trocar subclasse, não reescrever o fluxo.
- `ingestion/` (rede, formato físico) e `processing/` (regra de negócio) têm
  ciclos de vida diferentes. Espera-se mexer muito em `processing/`, pouco em
  `ingestion/` depois de pronto.
- `notebooks/` é onde mora o discovery sujo. Quando uma regra "endurece",
  migra do notebook para um transformer em `processing/`.

## Fontes de dados (FTP da ANS)

Base: `https://dadosabertos.ans.gov.br/FTP/PDA/` (responde em **ISO-8859-1**).

| Pasta | Papel | Fase |
|---|---|---|
| `demonstracoes_contabeis` | receitas/despesas — numerador/denominador | MVP |
| `operadoras_de_plano_de_saude_ativas` | dimensão operadora (chave: registro ANS) | MVP |
| `informacoes_consolidadas_de_beneficiarios-024` | normalização por vidas | MVP |
| `TISS` | procedimentos por UF (drill-down via PySpark) | fim de semana 3 |

Opcionais (escolher 1, só após o núcleo): `painel_de_glosas-057`,
`demandas_dos_consumidores_nip`, `terminologia_unificada...TUSS` (dicionário de códigos).

## Tratamento de dados (o que diferencia de dados "limpos" de Kaggle)

- Servidor em **ISO-8859-1**; nomes dentro de ZIP vêm em cp437/latin-1 → corrigir encoding.
- Decimais no formato brasileiro: `1.234,56` → `1234.56`.
- Razão social inconsistente entre bases → deduplicar pelo **registro ANS**.
- Competências faltantes e schema que muda entre anos.
- Granularidade temporal: **competência** (trimestral nas demonstrações). É chave em quase tudo.

## Roadmap

- [ ] Fim de semana 1 — ingestão (discover/download/extract), camada bronze
- [ ] Fim de semana 2 — silver com transformers + tratamento + dedup operadoras
- [ ] Fim de semana 3 — gold + cálculo de sinistralidade + PySpark na base TISS
- [ ] Fim de semana 4 — Workflows + checks + dashboard Power BI + README final + vídeo/prints

## Como trabalhar comigo (preferências do dev)

- O dev codifica no próprio ritmo, conforme faz o discovery dos dados. O Claude
  atua mais como **consultor/PO** (regras de negócio, fonte de dados, modelagem)
  do que como executor. Não escrever o projeto inteiro de uma vez.
- Ambiente: WSL Ubuntu 24.04, shell **zsh**, Java 17 (OpenJDK) instalado, UV.
- Background do dev: Senior Data Engineer (Azure/Databricks/PySpark no trabalho),
  experiência em saúde (gestão de clínica) e em risco/commodities — usar esses
  domínios como vantagem comparativa nas perguntas de negócio.

## Projetos-irmãos (NÃO misturar contexto aqui)

- **Versão Airflow sem Databricks**: clone conceitual com Airflow + Polars +
  DuckDB em containers. Mira startups/PMEs. Reaproveita o miolo de
  ingestão/regras deste projeto. Fazer só DEPOIS deste no ar.
- **Gerenciador de despesas via WhatsApp**: aplicação (backend + integração
  WhatsApp + LLM + DB). Universo diferente — merece Projeto próprio, não pertence aqui.
