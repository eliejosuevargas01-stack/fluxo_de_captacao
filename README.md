# Coletor de Leads

## Como executar localmente

1. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Rode o scraper principal:
   ```bash
   python main.py
   ```

O comando acima gera `outputs/leads_raw.csv` e normaliza para `outputs/leads.csv`.

## Pipelines disponíveis

- `python main.py` — roda o Google Maps scraper usando a imagem Docker `gosom/google-maps-scraper` e gera `outputs/leads.csv`.
- `python lead_pipeline.py` — qualifica e gera:
  - `outputs/leads_qualificados.csv`
  - `outputs/leads_top50.csv`
  - `outputs/propostas.csv`
- `python meta_ads_pipeline.py` — coleta anúncios do Meta Ads Library e gera:
  - `outputs/meta_ads_raw.csv`
  - `outputs/meta_ads_opportunities.csv`
- `python app.py` — abre o dashboard Streamlit local.
- `python serve_index.py` — serve `index.html` e os CSVs via HTTP local.

## Deploy no Coolify

Este projeto já possui `Dockerfile` para deploy em Coolify e um `Procfile` + `nixpacks.toml` para uso Nixpacks/Heroku-style deployments.

- Crie um novo serviço no Coolify
- Aponte para este repositório
- Configure a porta `8000` ou deixe o Coolify fornecer `PORT`
- Use a imagem Docker padrão com o `Dockerfile` do projeto ou selecione Nixpacks

O container inicia a API em `http://0.0.0.0:8000` por padrão, mas respeita a variável `PORT` do ambiente.

### Healthcheck

A aplicação expõe um endpoint de healthcheck em:

- `GET /health`

Use esse endpoint para verificar se o serviço está ativo.

## Observação importante

O script `main.py` depende de Docker para executar `gosom/google-maps-scraper`.
Se você quiser rodar este scraper dentro de um serviço Coolify, o host precisa expor o socket Docker ao container ou você deve executar `main.py` diretamente na máquina com Docker instalado.
