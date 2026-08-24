from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, text


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("DOJO_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL/DOJO_DATABASE_URL não configurada")
    return url


def scalar(conn, query: str, params: dict | None = None):
    return conn.execute(text(query), params or {}).scalar_one()


def build_kpis():
    engine = create_engine(database_url(), pool_pre_ping=True)
    with engine.begin() as conn:
        # Data quality: these tables are created by Django migrations.
        tables = {r[0] for r in conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"))}
        required = {"core_user", "core_course", "store_product", "store_order", "store_orderitem", "core_forumtopic", "core_forumcomment"}
        missing = required - tables
        if missing:
            raise RuntimeError(f"Tabelas ainda não migradas: {', '.join(sorted(missing))}")

        users = scalar(conn, "SELECT COUNT(*) FROM core_user")
        active_users = scalar(conn, "SELECT COUNT(*) FROM core_user WHERE is_active = TRUE")
        courses = scalar(conn, "SELECT COUNT(*) FROM core_course")
        topics = scalar(conn, "SELECT COUNT(*) FROM core_forumtopic")
        comments = scalar(conn, "SELECT COUNT(*) FROM core_forumcomment")
        products = scalar(conn, "SELECT COUNT(*) FROM store_product WHERE active = TRUE")
        orders = scalar(conn, "SELECT COUNT(*) FROM store_order")
        paid_orders = scalar(conn, "SELECT COUNT(*) FROM store_order WHERE status IN ('paid','fulfilled')")
        revenue = scalar(conn, "SELECT COALESCE(SUM(total), 0) FROM store_order WHERE status IN ('paid','fulfilled')")
        ticket = (Decimal(str(revenue)) / paid_orders) if paid_orders else Decimal("0")

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "users": users,
            "active_users": active_users,
            "courses": courses,
            "topics": topics,
            "comments": comments,
            "active_products": products,
            "orders": orders,
            "paid_orders": paid_orders,
            "revenue": float(revenue),
            "average_ticket": float(ticket),
        }


if __name__ == "__main__":
    print(build_kpis())
