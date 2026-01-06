from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterable

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url

    try:
        if "DATABASE_URL" in st.secrets:
            secret_url = str(st.secrets["DATABASE_URL"]).strip()
            if secret_url:
                return secret_url
        if "postgres" in st.secrets and "url" in st.secrets["postgres"]:
            secret_url = str(st.secrets["postgres"]["url"]).strip()
            if secret_url:
                return secret_url
    except Exception:
        pass

    raise RuntimeError("DATABASE_URL is not set (env/.env/.streamlit/secrets.toml).")


def is_configured() -> bool:
    try:
        _database_url()
        return True
    except Exception:
        return False


@st.cache_resource
def _pool() -> ConnectionPool:
    return ConnectionPool(conninfo=_database_url(), min_size=1, max_size=5, open=True)


@contextmanager
def get_connection() -> Iterable[psycopg.Connection[Any]]:
    with _pool().connection() as conn:
        yield conn


@contextmanager
def transaction() -> Iterable[psycopg.Connection[Any]]:
    with get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def query_df(sql: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame(rows)


def execute(
    sql: str,
    params: tuple[Any, ...] | None = None,
    *,
    fetchone: bool = False,
    fetchall: bool = False,
) -> Any:
    with transaction() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            return None


@st.cache_data(ttl=60)
def active_cashiers_df() -> pd.DataFrame:
    return query_df(
        """
        select cashier_id, full_name, username
        from cashiers
        where active is true
        order by full_name
        """
    )


@st.cache_data(ttl=60)
def cashiers_index_df() -> pd.DataFrame:
    return query_df(
        """
        select cashier_id, full_name, username, active, created_at
        from cashiers
        order by full_name
        """
    )


@st.cache_data(ttl=60)
def active_items_for_pos_df() -> pd.DataFrame:
    return query_df(
        """
        select item_id, item_name, sku, barcode, qty_on_hand, unit, sell_price
        from items
        where active is true
        order by item_name
        """
    )


@st.cache_data(ttl=60)
def items_index_df() -> pd.DataFrame:
    return query_df(
        """
        select item_id, item_name, sku, barcode, qty_on_hand, unit, sell_price, active, created_at
        from items
        order by item_name
        """
    )
