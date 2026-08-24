import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline import build_kpis

st.set_page_config(page_title="Dojo Dashboard", page_icon="🥋", layout="wide")
st.title("🥋 Dojo Dashboard")
st.caption("Data Driven Dojô · Analytics · Data Engineering · Data Science")

try:
    k = build_kpis()
except Exception as exc:
    st.error("O Dashboard está publicado, mas ainda não conseguiu acessar o banco de dados.")
    st.code(str(exc))
    st.info("Configure DATABASE_URL nos Secrets do Streamlit Cloud.")
    st.stop()

c = st.columns(4)
c[0].metric("Usuários", k["users"])
c[1].metric("Usuários ativos", k["active_users"])
c[2].metric("Cursos", k["courses"])
c[3].metric("Produtos ativos", k["active_products"])

c = st.columns(4)
c[0].metric("Pedidos", k["orders"])
c[1].metric("Pedidos pagos", k["paid_orders"])
c[2].metric("Receita", f"R$ {k['revenue']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
c[3].metric("Ticket médio", f"R$ {k['average_ticket']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

st.subheader("Comunidade")
c = st.columns(2)
c[0].metric("Tópicos", k["topics"])
c[1].metric("Comentários", k["comments"])

st.subheader("Marketing Digital")
st.dataframe({"Canal": ["Instagram", "LinkedIn", "YouTube", "Meta Ads", "Google Ads"], "Status": ["N/D"] * 5}, hide_index=True, use_container_width=True)
st.caption(f"Última leitura: {k['generated_at']}")
