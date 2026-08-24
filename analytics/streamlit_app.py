from __future__ import annotations

import hmac
import os
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline import (  # noqa: E402
    build_admin_tables,
    build_kpis,
    build_order_status_distribution,
    build_timeseries,
)

st.set_page_config(page_title="Dojo Command Center", page_icon="🥋", layout="wide")

REFRESH_SECONDS = max(15, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "60")))
ADMIN_PASSWORD = os.getenv("DOJO_ADMIN_PASSWORD", "")
DOJO_APP_URL = os.getenv("DOJO_APP_URL", "https://data-dojo-nine.vercel.app/")
LEXDATA_URL = os.getenv("LEXDATA_URL", "https://frontend-eta-vert-44.vercel.app/")
MARKETING_URL = os.getenv("MARKETING_URL", "")
APP_VERSION = "2026.08.24.2"
BRAND_ORANGE = "#F59E0B"
BRAND_BLUE = "#38BDF8"
STATUS_LABELS = {
    "pending": "Pendente", "paid": "Pago", "processing": "Em processamento",
    "fulfilled": "Concluído", "cancelled": "Cancelado",
}

st.markdown("""
<style>
  .stApp { background: linear-gradient(180deg, #0b1120 0%, #111827 100%); }
  [data-testid="stSidebar"] { background: #0f172a; border-right: 1px solid #263449; }
  [data-testid="stMetric"] { background: rgba(30,41,59,.72); border: 1px solid #334155; border-radius: 14px; padding: 16px; }
  [data-testid="stMetricValue"] { color: #f8fafc; }
  h1, h2, h3 { letter-spacing: -.02em; }
  .dojo-kicker { color: #f59e0b; font-weight: 700; letter-spacing: .16em; font-size: .78rem; }
  .dojo-subtitle { color: #94a3b8; margin-top: -.5rem; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)


def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner="Atualizando indicadores...")
def cached_kpis():
    return build_kpis()


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner="Atualizando séries...")
def cached_timeseries(days: int):
    return build_timeseries(days)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner="Atualizando pedidos...")
def cached_order_status():
    return build_order_status_distribution()


def line_chart(frame, title: str, color: str, y_title: str):
    figure = px.line(frame, x="day", y="value", markers=True, title=title)
    figure.update_traces(line_color=color, marker_color=color)
    figure.update_layout(
        template="plotly_dark", height=330, margin=dict(l=16, r=16, t=55, b=16),
        xaxis_title=None, yaxis_title=y_title, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,.65)", hovermode="x unified",
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def overview(days: int):
    kpis = cached_kpis()
    generated = kpis["generated_at"].replace("T", " ")[:19]
    st.caption(f"Atualização: {REFRESH_SECONDS}s · dados: {kpis['data_date']} · consulta: {generated} UTC")

    cols = st.columns(5)
    cols[0].metric("Usuários", kpis["users"], f"+{kpis['new_users_today']} hoje")
    cols[1].metric("Contas habilitadas", kpis["enabled_accounts"])
    cols[2].metric("Cursos", kpis["courses"])
    cols[3].metric("Produtos ativos", kpis["active_products"])
    cols[4].metric("Portfólios publicados", kpis["published_portfolios"])

    cols = st.columns(5)
    cols[0].metric("Pedidos", kpis["orders"])
    cols[1].metric("Pedidos reconhecidos", kpis["paid_orders"], f"{kpis['pending_orders']} pendentes")
    cols[2].metric("Receita reconhecida", brl(kpis["revenue"]), f"{brl(kpis['revenue_today'])} hoje")
    cols[3].metric("Ticket médio", brl(kpis["average_ticket"]))
    cols[4].metric("Conversão em comprador", f"{kpis['buyer_conversion_rate']:.1f}%")

    cols = st.columns(3)
    cols[0].metric("Pedidos cancelados", kpis["cancelled_orders"])
    cols[1].metric("Taxa de cancelamento", f"{kpis['order_cancellation_rate']:.1f}%")
    cols[2].metric("Comunidade hoje", kpis["community_today"])

    series = cached_timeseries(days)
    left, right = st.columns(2)
    with left:
        line_chart(series["users"], f"Novos usuários · {days} dias", BRAND_BLUE, "Usuários")
        line_chart(series["revenue"], f"Receita reconhecida · {days} dias", BRAND_ORANGE, "R$")
    with right:
        line_chart(series["community"], f"Conteúdos na comunidade · {days} dias", "#A78BFA", "Conteúdos")
        line_chart(series["cancelled_orders"], f"Cancelamentos · {days} dias", "#FB7185", "Pedidos")

    statuses = cached_order_status()
    if not statuses.empty:
        statuses["status_label"] = statuses["status"].map(STATUS_LABELS).fillna(statuses["status"])
        chart = px.bar(
            statuses, x="status_label", y="orders", color="status_label",
            title="Distribuição dos pedidos por status",
            labels={"status_label": "Status", "orders": "Pedidos"},
            color_discrete_sequence=[BRAND_ORANGE, BRAND_BLUE, "#22C55E", "#A78BFA", "#FB7185"],
        )
        chart.update_layout(template="plotly_dark", showlegend=False, height=360,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,.65)")
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

    with st.expander("Definições e critérios dos indicadores"):
        st.markdown("""
- **Receita reconhecida:** soma de pedidos `paid`, `processing` e `fulfilled`; pendentes e cancelados não entram.
- **Ticket médio:** receita reconhecida dividida pela quantidade de pedidos reconhecidos.
- **Conversão em comprador:** usuários distintos com pedido reconhecido divididos por usuários cadastrados.
- **Taxa de cancelamento:** pedidos `cancelled` divididos por todos os pedidos. É churn transacional, não retenção de alunos.
- **Portfólios publicados:** projetos de alunos com status `published`; rascunhos permanecem privados.
- **Comunidade hoje:** tópicos e comentários criados na data corrente do banco.
        """)


def administration():
    st.subheader("🔐 Administração")
    if not ADMIN_PASSWORD:
        st.warning("Defina DOJO_ADMIN_PASSWORD nos Secrets para habilitar esta área.")
        return
    if not st.session_state.get("admin_authenticated"):
        with st.form("admin_login"):
            password = st.text_input("Senha administrativa", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
        if not submitted:
            st.info("Informe a senha administrativa para acessar dados operacionais.")
            return
        if not hmac.compare_digest(password, ADMIN_PASSWORD):
            st.error("Senha inválida.")
            return
        st.session_state.admin_authenticated = True
        st.rerun()
    if st.button("Sair da área administrativa"):
        st.session_state.admin_authenticated = False
        st.rerun()
    tables = build_admin_tables()
    tab_users, tab_orders, tab_community = st.tabs(["Usuários", "Pedidos", "Comunidade"])
    with tab_users:
        st.dataframe(tables["users"], hide_index=True, use_container_width=True)
    with tab_orders:
        st.caption("Cancelados permanecem no banco para churn, auditoria e análise operacional.")
        st.dataframe(tables["orders"], hide_index=True, use_container_width=True)
    with tab_community:
        st.dataframe(tables["topics"], hide_index=True, use_container_width=True)
    st.caption("Área somente leitura. Alterações continuam no Django Admin/API autenticada.")


def ecosystem():
    st.subheader("🌐 Ecossistema 3DS")
    st.markdown("**Data Driven Dojô** — educação, comunidade, IA, analytics, portfólios e 3DStore.")
    st.markdown("**3DS Marketing Digital** — dados, automação, IA, marketing e tráfego pago.")
    st.markdown("**LexData & Finance Solutions** — direito, dados e soluções financeiras.")
    st.link_button("Abrir Data Driven Dojô", DOJO_APP_URL, use_container_width=True)
    st.link_button("Abrir LexData", LEXDATA_URL, use_container_width=True)
    if MARKETING_URL:
        st.link_button("Abrir 3DS Marketing", MARKETING_URL, use_container_width=True)
    else:
        st.info("Ative o link da 3DS Marketing pelo Secret MARKETING_URL.")


st.markdown('<div class="dojo-kicker">DETERMINAÇÃO · DISCIPLINA · DIREÇÃO</div>', unsafe_allow_html=True)
st.title("🥋 Dojo Command Center")
st.markdown('<div class="dojo-subtitle">Inteligência operacional do Data Driven Dojô e do ecossistema 3DS.</div>', unsafe_allow_html=True)
st.sidebar.markdown("## Dojo Command Center")
st.sidebar.caption("Data Driven Dojô · Analytics · Administração")
page = st.sidebar.radio("Navegação", ["Visão geral", "Administração", "Ecossistema"])
days = st.sidebar.selectbox("Período dos gráficos", [7, 30, 90, 180, 365], index=1,
                            format_func=lambda value: f"{value} dias", disabled=page != "Visão geral")
st.sidebar.link_button("↩ Voltar ao Data Driven Dojô", DOJO_APP_URL, use_container_width=True)
st.sidebar.caption(f"Versão {APP_VERSION}")

try:
    if page == "Visão geral":
        overview(days)
    elif page == "Administração":
        administration()
    else:
        ecosystem()
except Exception as exc:
    st.error("O Command Center não conseguiu consultar o banco de dados.")
    st.info("Confira a External Database URL do Render em DATABASE_URL e reinicie o aplicativo.")
    if os.getenv("DASHBOARD_DEBUG", "false").lower() == "true":
        st.code(f"{type(exc).__name__}: {exc}")
