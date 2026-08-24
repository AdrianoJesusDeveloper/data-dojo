from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy import create_engine, text


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("DOJO_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL/DOJO_DATABASE_URL não configurada")
    return url


def engine():
    return create_engine(database_url(), pool_pre_ping=True, pool_recycle=300)


def scalar(conn, query: str, params=None):
    return conn.execute(text(query), params or {}).scalar_one()


def _tables(conn):
    return {r[0] for r in conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"))}


def build_kpis():
    with engine().begin() as conn:
        tables = _tables(conn)
        required = {"core_user", "core_course", "store_product", "store_order", "core_forumtopic", "core_forumcomment"}
        missing = required - tables
        if missing:
            raise RuntimeError(f"Tabelas ainda não migradas: {', '.join(sorted(missing))}")

        users = scalar(conn, "SELECT COUNT(*) FROM core_user")
        active_users = scalar(conn, "SELECT COUNT(*) FROM core_user WHERE is_active = TRUE")
        new_users_today = scalar(conn, "SELECT COUNT(*) FROM core_user WHERE date_joined::date = CURRENT_DATE")
        courses = scalar(conn, "SELECT COUNT(*) FROM core_course")
        topics = scalar(conn, "SELECT COUNT(*) FROM core_forumtopic")
        comments = scalar(conn, "SELECT COUNT(*) FROM core_forumcomment")
        topics_today = scalar(conn, "SELECT COUNT(*) FROM core_forumtopic WHERE created_at::date = CURRENT_DATE")
        comments_today = scalar(conn, "SELECT COUNT(*) FROM core_forumcomment WHERE created_at::date = CURRENT_DATE")
        products = scalar(conn, "SELECT COUNT(*) FROM store_product WHERE active = TRUE")
        orders = scalar(conn, "SELECT COUNT(*) FROM store_order")
        paid_orders = scalar(conn, "SELECT COUNT(*) FROM store_order WHERE status IN ('paid','processing','fulfilled','completed')")
        revenue = scalar(conn, "SELECT COALESCE(SUM(total), 0) FROM store_order WHERE status IN ('paid','processing','fulfilled','completed')")
        revenue_today = scalar(conn, "SELECT COALESCE(SUM(total), 0) FROM store_order WHERE status IN ('paid','processing','fulfilled','completed') AND created_at::date = CURRENT_DATE")
        ticket = Decimal(str(revenue)) / paid_orders if paid_orders else Decimal("0")
        conversion = (paid_orders / users * 100) if users else 0

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "users": users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "courses": courses,
            "topics": topics,
            "comments": comments,
            "topics_today": topics_today,
            "comments_today": comments_today,
            "active_products": products,
            "orders": orders,
            "paid_orders": paid_orders,
            "revenue": float(revenue),
            "revenue_today": float(revenue_today),
            "average_ticket": float(ticket),
            "conversion_rate": float(conversion),
        }


def build_timeseries(days: int = 30):
    days = max(7, min(int(days), 365))
    queries = {
        "users": """SELECT date_joined::date AS day, COUNT(*) AS value FROM core_user WHERE date_joined >= CURRENT_DATE - (:days * INTERVAL '1 day') GROUP BY 1 ORDER BY 1""",
        "community": """SELECT day, SUM(value) AS value FROM (SELECT created_at::date AS day, COUNT(*) AS value FROM core_forumtopic WHERE created_at >= CURRENT_DATE - (:days * INTERVAL '1 day') GROUP BY 1 UNION ALL SELECT created_at::date AS day, COUNT(*) AS value FROM core_forumcomment WHERE created_at >= CURRENT_DATE - (:days * INTERVAL '1 day') GROUP BY 1) x GROUP BY day ORDER BY day""",
        "revenue": """SELECT created_at::date AS day, COALESCE(SUM(total),0) AS value FROM store_order WHERE status IN ('paid','processing','fulfilled','completed') AND created_at >= CURRENT_DATE - (:days * INTERVAL '1 day') GROUP BY 1 ORDER BY 1""",
    }
    with engine().connect() as conn:
        return {name: pd.read_sql(text(query), conn, params={"days": days}) for name, query in queries.items()}


def build_admin_tables(limit: int = 20):
    limit = max(5, min(int(limit), 100))
    with engine().connect() as conn:
        users = pd.read_sql(text("SELECT id, username, email, is_active, is_staff, date_joined FROM core_user ORDER BY date_joined DESC LIMIT :limit"), conn, params={"limit": limit})
        orders = pd.read_sql(text("SELECT id, status, total, created_at FROM store_order ORDER BY created_at DESC LIMIT :limit"), conn, params={"limit": limit})
        topics = pd.read_sql(text("SELECT id, title, user_id, created_at, updated_at FROM core_forumtopic ORDER BY created_at DESC LIMIT :limit"), conn, params={"limit": limit})
    return {"users": users, "orders": orders, "topics": topics}


if __name__ == "__main__":
    print(build_kpis())
