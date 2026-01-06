from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db


st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Dashboard")

if not db.is_configured():
    st.warning("`DATABASE_URL` is not set.")
    st.stop()

low_stock_threshold = st.number_input("Low stock threshold", min_value=0.0, value=5.0, step=1.0)

kpi = db.query_df(
    """
    select
      coalesce(sum(case when sold_at::date = current_date then line_total end), 0) as sales_today,
      coalesce(sum(case when sold_at >= date_trunc('month', now()) then line_total end), 0) as sales_month,
      coalesce(count(*) filter (where sold_at::date = current_date), 0) as transactions_today
    from sales
    """
)

sales_today = kpi.loc[0, "sales_today"] if not kpi.empty else 0
sales_month = kpi.loc[0, "sales_month"] if not kpi.empty else 0
transactions_today = kpi.loc[0, "transactions_today"] if not kpi.empty else 0

c1, c2, c3 = st.columns(3)
c1.metric("Sales today", f"{sales_today}")
c2.metric("Sales this month", f"{sales_month}")
c3.metric("Transactions today", f"{transactions_today}")

st.divider()

col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("Low stock")
    low_df = db.query_df(
        """
        select item_name, sku, barcode, qty_on_hand, unit, sell_price
        from items
        where active is true and qty_on_hand <= %s
        order by qty_on_hand asc, item_name asc
        """,
        (low_stock_threshold,),
    )
    st.dataframe(low_df, use_container_width=True, hide_index=True)

with col_b:
    st.subheader("Top 10 items by revenue (month)")
    top_df = db.query_df(
        """
        select i.item_name, sum(s.line_total) as revenue
        from sales s
        join items i on i.item_id = s.item_id
        where s.sold_at >= date_trunc('month', now())
        group by i.item_name
        order by revenue desc
        limit 10
        """
    )
    st.dataframe(top_df, use_container_width=True, hide_index=True)
    if not top_df.empty:
        chart_df = top_df.set_index("item_name")
        st.bar_chart(chart_df)

st.divider()
st.subheader("Sales trend (last 30 days)")

trend_df = db.query_df(
    """
    select
      (sold_at::date) as day,
      sum(line_total) as revenue
    from sales
    where sold_at >= (current_date - interval '29 days')
    group by day
    order by day
    """
)

if trend_df.empty:
    st.info("No sales in the selected period.")
else:
    trend_df["day"] = pd.to_datetime(trend_df["day"])
    st.line_chart(trend_df.set_index("day")["revenue"])
