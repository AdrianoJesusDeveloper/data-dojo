# Dojo Command Center

Dashboard operacional do ecossistema Data Driven Dojô.

## Arquitetura

PostgreSQL (Django/3DStore/Comunidade) -> SQLAlchemy/Pandas -> Streamlit.

A visão geral usa `st.fragment(run_every=...)` e consulta o PostgreSQL novamente em intervalos configuráveis. Isso caracteriza **near real-time**, não streaming/event-time.

## Variáveis de ambiente / Secrets

- `DATABASE_URL` ou `DOJO_DATABASE_URL`: PostgreSQL do Data Driven Dojô.
- `DASHBOARD_REFRESH_SECONDS`: intervalo de atualização, padrão 60 segundos.
- `DOJO_ADMIN_PASSWORD`: protege a página administrativa somente leitura.
- `LEXDATA_URL`: URL publicada da LexData & Finance Solutions. Enquanto não configurada, aponta para o repositório.
- `MARKETING_URL`: URL futura do site/subdomínio 3DS Marketing Digital & Soluções Tecnológicas.

## Segurança

A página administrativa do Streamlit é deliberadamente somente leitura. Operações destrutivas ou alterações de usuários/pedidos devem permanecer no Django Admin/API com autenticação e autorização apropriadas.

## Próximas fontes

A camada de Marketing Digital deve usar APIs oficiais (YouTube, Meta e Google Ads) e persistir snapshots/ fatos em tabelas analíticas antes de alimentar KPIs históricos.
