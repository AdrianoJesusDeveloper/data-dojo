# 🥋 Dojo Dashboard

Camada de Analytics, Data Engineering e Data Science do ecossistema Data Driven Dojô.

## Arquitetura

```text
Django/PostgreSQL → ingestão → transformação → KPI marts → Streamlit
                                      ↑
                           marketing adapters (futuro)
```

### Fontes internas já suportadas
- Usuários
- Cursos
- Comunidade
- Produtos
- Pedidos
- Itens de pedidos

### KPIs iniciais
- usuários totais/ativos
- cursos
- tópicos e comentários
- pedidos
- pedidos pagos
- receita
- ticket médio
- produtos ativos
- conversão operacional disponível

## Execução local

```bash
pip install -r analytics/requirements.txt
streamlit run analytics/dashboard.py
```

Defina `DATABASE_URL` no ambiente ou em `.streamlit/secrets.toml`.

## Atualização automática

O workflow `/.github/workflows/dojo-analytics.yml` executa o pipeline diariamente. Configure o secret `DOJO_DATABASE_URL` no GitHub antes de ativá-lo.

> APIs de Meta Ads, Google Ads, LinkedIn, YouTube e outros canais devem ser conectadas com credenciais próprias antes que métricas externas sejam consideradas reais. O dashboard não inventa esses dados: mostra `N/D` até a fonte ser configurada.
