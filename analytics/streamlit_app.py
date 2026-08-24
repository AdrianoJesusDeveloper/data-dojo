import os
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from pipeline import build_admin_tables, build_kpis, build_timeseries

st.set_page_config(page_title="Dojo Command Center", page_icon="🥋", layout="wide")
REFRESH_SECONDS = max(15, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "60")))
ADMIN_PASSWORD = os.getenv("DOJO_ADMIN_PASSWORD", "")
LEXDATA_URL = os.getenv("LEXDATA_URL", "https://github.com/AdrianoJesusDeveloper/lex_data_project_")
MARKETING_URL = os.getenv("MARKETING_URL", "")


def brl(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def overview():
    k = build_kpis()
    st.caption(f"Near real-time · atualização a cada {REFRESH_SECONDS}s · leitura {k['generated_at']}")
    cols = st.columns(5)
    cols[0].metric("Usuários", k["users"], f"+{k['new_users_today']} hoje")
    cols[1].metric("Ativos", k["active_users"])
    cols[2].metric("Cursos", k["courses"])
    cols[3].metric("Produtos", k["active_products"])
    cols[4].metric("Conversão", f"{k['conversion_rate']:.1f}%")
    cols = st.columns(5)
    cols[0].metric("Pedidos", k["orders"])
    cols[1].metric("Pagos", k["paid_orders"])
    cols[2].metric("Receita", brl(k["revenue"]), brl(k["revenue_today"]) + " hoje")
    cols[3].metric("Ticket médio", brl(k["average_ticket"]))
    cols[4].metric("Comunidade hoje", k["topics_today"] + k["comments_today"])
    series = build_timeseries(30)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.line(series["users"], x="day", y="value", markers=True, title="Novos usuários · 30 dias"), use_container_width=True)
        st.plotly_chart(px.line(series["revenue"], x="day", y="value", markers=True, title="Receita · 30 dias"), use_container_width=True)
    with right:
        st.plotly_chart(px.line(series["community"], x="day", y="value", markers=True, title="Interações na comunidade · 30 dias"), use_container_width=True)
        st.info("Próxima camada: APIs oficiais do YouTube, Meta e Google Ads.")


st.title("🥋 Dojo Command Center")
st.caption("Data Driven Dojô · Analytics · Administração · Ecossistema 3DS")
page = st.sidebar.radio("Navegação", ["Visão geral", "Administração", "Ecossistema"])

try:
    if page == "Visão geral":
        overview()
    elif page == "Administração":
        st.subheader("🔐 Administração")
        if not ADMIN_PASSWORD:
            st.warning("Defina DOJO_ADMIN_PASSWORD nos Secrets antes de habilitar esta área em produção.")
            st.stop()
        password = st.text_input("Senha administrativa", type="password")
        if password != ADMIN_PASSWORD:
            st.info("Informe a senha administrativa para acessar dados operacionais.")
            st.stop()
        tables = build_admin_tables()
        tab_users, tab_orders, tab_community = st.tabs(["Usuários", "Pedidos", "Comunidade"])
        with tab_users: st.dataframe(tables["users"], hide_index=True, use_container_width=True)
        with tab_orders: st.dataframe(tables["orders"], hide_index=True, use_container_width=True)
        with tab_community: st.dataframe(tables["topics"], hide_index=True, use_container_width=True)
        st.caption("Admin somente leitura. Alterações permanecem no Django Admin/API autenticada.")
    else:
        st.subheader("🌐 Ecossistema 3DS")
        st.markdown("**Data Driven Dojô** — educação, comunidade, IA, analytics e 3DStore.")
        st.markdown("**3DS Marketing Digital & Soluções Tecnológicas** — dados, automação, IA, cloud e marketing.")
        st.markdown("**LexData & Finance Solutions** — dados e soluções financeiras.")
        st.link_button("Abrir LexData", LEXDATA_URL)
        if MARKETING_URL:
            st.link_button("Abrir 3DS Marketing", MARKETING_URL)
        else:
            st.info("MARKETING_URL será conectado quando o site/subdomínio estiver publicado.")
except Exception as exc:
    st.error("O Command Center não conseguiu acessar uma das fontes de dados.")
    st.code(str(exc))
    st.info("Confira DATABASE_URL e os Secrets do ambiente Streamlit.")
