from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, "apps", "api", ".env"))

RECOGNIZED_ORDER_STATUSES = ("paid", "processing", "fulfilled")


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("DOJO_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL/DOJO_DATABASE_URL não configurada")
    # SQLAlchemy 2 uses the explicit postgresql dialect name.
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    return url


@lru_cache(maxsize=1)
def engine():
    return create_engine(
        database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=max(1, int(os.getenv("DASHBOARD_DB_POOL_SIZE", "2"))),
        max_overflow=max(0, int(os.getenv("DASHBOARD_DB_MAX_OVERFLOW", "1"))),
    )


def _number(value, default=0):
    return default if value is None else value


def calculate_kpis(row: dict) -> dict:
    """Pure metric calculation kept separate so definitions are testable."""
    users = int(_number(row.get("users")))
    buyers = int(_number(row.get("buyers")))
    revenue = Decimal(str(_number(row.get("revenue"), Decimal("0"))))
    paid_orders = int(_number(row.get("paid_orders")))
    orders = int(_number(row.get("orders")))
    cancelled_orders = int(_number(row.get("cancelled_orders")))
    return {
        **row,
        "users": users,
        "buyers": buyers,
        "orders": orders,
        "cancelled_orders": cancelled_orders,
        "revenue": float(revenue),
        "average_ticket": float(revenue / paid_orders) if paid_orders else 0.0,
        "buyer_conversion_rate": (buyers / users * 100) if users else 0.0,
        "order_cancellation_rate": (cancelled_orders / orders * 100) if orders else 0.0,
        "community_today": int(_number(row.get("topics_today"))) + int(_number(row.get("comments_today"))),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_kpis():
    query = text("""
        SELECT
          (SELECT COUNT(*) FROM core_user) AS users,
          (SELECT COUNT(*) FROM core_user WHERE is_active = TRUE) AS enabled_accounts,
          (SELECT COUNT(*) FROM core_user WHERE date_joined::date = CURRENT_DATE) AS new_users_today,
          (SELECT COUNT(*) FROM core_course) AS courses,
          (SELECT COUNT(*) FROM core_studentproject WHERE status = 'published') AS published_portfolios,
          (SELECT COUNT(*) FROM core_forumtopic) AS topics,
          (SELECT COUNT(*) FROM core_forumcomment) AS comments,
          (SELECT COUNT(*) FROM core_forumtopic WHERE created_at::date = CURRENT_DATE) AS topics_today,
          (SELECT COUNT(*) FROM core_forumcomment WHERE created_at::date = CURRENT_DATE) AS comments_today,
          (SELECT COUNT(*) FROM store_product WHERE active = TRUE) AS active_products,
          (SELECT COUNT(*) FROM store_order) AS orders,
          (SELECT COUNT(*) FROM store_order WHERE status = 'pending') AS pending_orders,
          (SELECT COUNT(*) FROM store_order WHERE status = 'cancelled') AS cancelled_orders,
          (SELECT COUNT(*) FROM store_order WHERE status IN ('paid','processing','fulfilled')) AS paid_orders,
          (SELECT COUNT(DISTINCT user_id) FROM store_order WHERE status IN ('paid','processing','fulfilled')) AS buyers,
          (SELECT COALESCE(SUM(total), 0) FROM store_order WHERE status IN ('paid','processing','fulfilled')) AS revenue,
          (SELECT COALESCE(SUM(total), 0) FROM store_order WHERE status IN ('paid','processing','fulfilled') AND created_at::date = CURRENT_DATE) AS revenue_today,
          CURRENT_DATE AS data_date
    """)
    with engine().connect() as conn:
        row = dict(conn.execute(query).mappings().one())
    return calculate_kpis(row)


def _complete_daily_series(frame: pd.DataFrame, days: int) -> pd.DataFrame:
    end = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    calendar = pd.DataFrame({"day": pd.date_range(end=end, periods=days, freq="D")})
    if frame.empty:
        calendar["value"] = 0.0
        return calendar
    clean = frame.copy()
    clean["day"] = pd.to_datetime(clean["day"])
    return calendar.merge(clean, on="day", how="left").fillna({"value": 0.0})


def build_timeseries(days: int = 30):
    days = max(7, min(int(days), 365))
    queries = {
        "users": "SELECT date_joined::date AS day, COUNT(*) AS value FROM core_user WHERE date_joined::date > CURRENT_DATE - :days GROUP BY 1 ORDER BY 1",
        "community": "SELECT day, SUM(value) AS value FROM (SELECT created_at::date AS day, COUNT(*) AS value FROM core_forumtopic WHERE created_at::date > CURRENT_DATE - :days GROUP BY 1 UNION ALL SELECT created_at::date AS day, COUNT(*) AS value FROM core_forumcomment WHERE created_at::date > CURRENT_DATE - :days GROUP BY 1) x GROUP BY day ORDER BY day",
        "revenue": "SELECT created_at::date AS day, COALESCE(SUM(total),0) AS value FROM store_order WHERE status IN ('paid','processing','fulfilled') AND created_at::date > CURRENT_DATE - :days GROUP BY 1 ORDER BY 1",
        "cancelled_orders": "SELECT created_at::date AS day, COUNT(*) AS value FROM store_order WHERE status = 'cancelled' AND created_at::date > CURRENT_DATE - :days GROUP BY 1 ORDER BY 1",
    }
    with engine().connect() as conn:
        frames = {name: pd.read_sql(text(query), conn, params={"days": days}) for name, query in queries.items()}
    return {name: _complete_daily_series(frame, days) for name, frame in frames.items()}


def build_order_status_distribution():
    query = text("""
        SELECT status, COUNT(*) AS orders, COALESCE(SUM(total), 0) AS gross_value
        FROM store_order
        GROUP BY status
        ORDER BY orders DESC, status
    """)
    with engine().connect() as conn:
        return pd.read_sql(query, conn)


def build_admin_tables(limit: int = 30):
    limit = max(5, min(int(limit), 100))
    with engine().connect() as conn:
        users = pd.read_sql(text("SELECT id, username, email, is_active, is_staff, date_joined FROM core_user ORDER BY date_joined DESC LIMIT :limit"), conn, params={"limit": limit})
        orders = pd.read_sql(text("SELECT id, user_id, status, total, created_at, updated_at FROM store_order ORDER BY created_at DESC LIMIT :limit"), conn, params={"limit": limit})
        topics = pd.read_sql(text("SELECT id, title, user_id, created_at, updated_at FROM core_forumtopic ORDER BY created_at DESC LIMIT :limit"), conn, params={"limit": limit})
    return {"users": users, "orders": orders, "topics": topics}
