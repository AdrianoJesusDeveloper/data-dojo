import streamlit as st
from pipeline import build_kpis

st.set_page_config(page_title="Dojo Dashboard", page_icon="🥋", layout="wide")
st.title("🥋 Dojo Dashboard")
st.caption("Data Driven Dojô · Determinação · Disciplina · Desenvolvimento")

try:
    k = build_kpis()
except Exception as exc:
    st.error("Dashboard publicado, aguardando conexão com o PostgreSQL.")
    st.code(str(exc))
    st.info("Configure DATABASE_URL em Settings → Secrets no Streamlit Cloud.")
    st.stop()

for values in [
    [("Usuários", k["users"]), ("Ativos", k["active_users"]), ("Cursos", k["courses"]), ("Produtos", k["active_products"])],
    [("Pedidos", k["orders"]), ("Pagos", k["paid_orders"]), ("Receita", f'R$ {k["revenue"]:,.2f}'), ("Ticket médio", f'R$ {k["average_ticket"]:,.2f}')],
]:
    cols = st.columns(4)
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)

st.divider()
st.subheader("Comunidade")
a, b = st.columns(2)
a.metric("Tópicos", k["topics"])
b.metric("Comentários", k["comments"])

st.subheader("Marketing Digital")
st.dataframe({"Canal": ["Instagram", "LinkedIn", "YouTube", "Meta Ads", "Google Ads"], "Status": ["N/D"] * 5}, hide_index=True, use_container_width=True)
st.caption("Canais externos serão conectados por APIs oficiais. N/D significa fonte ainda não configurada.")
st.caption(f'Última leitura: {k["generated_at"]}')
