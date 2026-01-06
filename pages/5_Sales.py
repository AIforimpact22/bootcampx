from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

import db
import ui


st.set_page_config(page_title="Sales", layout="wide")
ui.render_branding()
st.title("Sales")

if not db.is_configured():
    st.warning("`DATABASE_URL` is not set.")
    st.stop()

st.subheader("Filters")

default_end = date.today()
default_start = default_end - timedelta(days=6)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    date_range = st.date_input("Date range", (default_start, default_end))
with col2:
    cashiers = db.cashiers_index_df()
    cashier_options = ["All"] + (cashiers["cashier_id"].tolist() if not cashiers.empty else [])

    def _cashier_label(opt):
        if opt == "All":
            return "All"
        row = cashiers.loc[cashiers["cashier_id"] == opt].iloc[0]
        username = row["username"]
        suffix = f" (@{username})" if username else ""
        return f"{row['full_name']}{suffix}"

    cashier_filter = st.selectbox("Cashier", options=cashier_options, format_func=_cashier_label)
with col3:
    item_search = st.text_input("Item search (name, barcode, SKU)", placeholder="e.g. milk, 0123456789, SKU123")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

start_dt = datetime.combine(start_date, datetime.min.time())
end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

conditions = ["s.sold_at >= %s", "s.sold_at < %s"]
params: list[object] = [start_dt, end_dt]

if cashier_filter != "All":
    conditions.append("s.cashier_id = %s")
    params.append(int(cashier_filter))

if item_search.strip():
    conditions.append("(i.item_name ilike %s or i.sku ilike %s or i.barcode ilike %s)")
    like = f"%{item_search.strip()}%"
    params.extend([like, like, like])

where_sql = " and ".join(conditions)

sales_df = db.query_df(
    f"""
    select
      s.sale_id,
      s.sold_at,
      c.full_name as cashier,
      i.item_name,
      i.sku,
      i.barcode,
      s.qty,
      i.unit,
      s.unit_price,
      s.line_total
    from sales s
    join cashiers c on c.cashier_id = s.cashier_id
    join items i on i.item_id = s.item_id
    where {where_sql}
    order by s.sold_at desc, s.sale_id desc
    """,
    tuple(params),
)

st.subheader("Results")
st.dataframe(sales_df, use_container_width=True, hide_index=True)

if sales_df.empty:
    st.info("No sales matched your filters.")
else:
    total_revenue = sales_df["line_total"].sum()
    total_qty = sales_df["qty"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(sales_df)}")
    c2.metric("Total qty", f"{total_qty}")
    c3.metric("Total revenue", f"{total_revenue}")

    csv_bytes = sales_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"sales_{start_date}_to_{end_date}.csv",
        mime="text/csv",
        use_container_width=True,
    )
