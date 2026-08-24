from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from pipeline import build_kpis  # noqa: E402

st.set_page_config(page_title="Dojo Dashboard", page_icon="🥋", layout="wide")

st.title("🥋 Dojo Dashboard")
st.caption("Data Driven Dojô · Analytics · Data Engineering · Data Science")

with st.sidebar:
    st.header("Controle")
    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Fontes externas de marketing ficam como N/D até suas APIs/credenciais serem configuradas.")

try:
    k = build_kpis()
except Exception as exc:
    st.error("O pipeline ainda não conseguiu acessar a base operacional.")
    st.code(str(exc))
    st.info("Configure DATABASE_URL/DOJO_DATABASE_URL e execute as migrations do Django.")
    st.stop()

cols = st.columns(4)
cols[0].metric("Usuários", f"{k['users']:,}".replace(',', '.'))
cols[1].metric("Usuários ativos", f"{k['active_users']:,}".replace(',', '.'))
cols[2].metric("Cursos", f"{k['courses']:,}".replace(',', '.'))
cols[3].metric("Produtos ativos", f"{k['active_products']:,}".replace(',', '.'))

st.divider()

cols = st.columns(4)
cols[0].metric("Pedidos", f"{k['orders']:,}".replace(',', '.'))
cols[1].metric("Pedidos pagos", f"{k['paid_orders']:,}".replace(',', '.'))
cols[2].metric("Receita", f"R$ {k['revenue']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
cols[3].metric("Ticket médio", f"R$ {k['average_ticket']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

st.subheader("Ecossistema")
left, right = st.columns(2)
with left:
    df = pd.DataFrame({"Área": ["Educação", "Comunidade", "Commerce"], "Indicador": [k['courses'], k['topics'] + k['comments'], k['paid_orders']]})
    st.plotly_chart(px.bar(df, x="Área", y="Indicador", title="Atividade por domínio"), use_container_width=True)
with right:
    st.metric("Tópicos da comunidade", k["topics"])
    st.metric("Comentários", k["comments"])

st.subheader("Marketing Digital")
marketing = pd.DataFrame([
    ["Instagram", "N/D"], ["LinkedIn", "N/D"], ["YouTube", "N/D"], ["Meta Ads", "N/D"], ["Google Ads", "N/D"]
], columns=["Canal", "Status"])
st.dataframe(marketing, hide_index=True, use_container_width=True)
st.caption("Próxima etapa: conectar APIs oficiais e armazenar campanhas, anúncios, custos, cliques, leads, conversões, ROAS e receita atribuída.")

st.caption(f"Última leitura: {k['generated_at']}")
