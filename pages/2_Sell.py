from __future__ import annotations

from decimal import Decimal, InvalidOperation

import psycopg
import streamlit as st
from psycopg.rows import dict_row

import db
import ui


st.set_page_config(page_title="Sell (POS)", layout="wide")
ui.render_branding()
st.title("Sell (POS)")

if not db.is_configured():
    st.warning("`DATABASE_URL` is not set.")
    st.stop()

cashiers = db.active_cashiers_df()
items = db.active_items_for_pos_df()

if cashiers.empty:
    st.info("No active cashiers found. Add one in the Cashiers page.")
    st.stop()

if items.empty:
    st.info("No active items found. Add items in the Items page.")
    st.stop()

cashier_ids = cashiers["cashier_id"].tolist()


def _cashier_label(cid: int) -> str:
    row = cashiers.loc[cashiers["cashier_id"] == cid].iloc[0]
    username = row["username"]
    suffix = f" (@{username})" if username else ""
    return f"{row['full_name']}{suffix}"


st.subheader("Cashier")
cashier_id = st.selectbox("Select cashier", options=cashier_ids, format_func=_cashier_label)

st.divider()
st.subheader("Item lookup")

left, right = st.columns([1, 1])

with left:
    lookup = st.text_input("Scan/enter barcode or SKU", placeholder="e.g. 0123456789 or SKU123")
    if st.button("Find item", use_container_width=True) and lookup.strip():
        found = db.query_df(
            """
            select item_id
            from items
            where active is true and (barcode = %s or sku = %s)
            limit 1
            """,
            (lookup.strip(), lookup.strip()),
        )
        if found.empty:
            st.warning("No active item matched that barcode/SKU.")
        else:
            st.session_state["selected_item_id"] = int(found.loc[0, "item_id"])

with right:
    item_ids = items["item_id"].tolist()

    def _item_label(iid: int) -> str:
        row = items.loc[items["item_id"] == iid].iloc[0]
        sku = row["sku"] or ""
        barcode = row["barcode"] or ""
        extras = " • ".join([x for x in [sku, barcode] if x])
        suffix = f" ({extras})" if extras else ""
        return f"{row['item_name']}{suffix}"

    selected_item_id = st.selectbox(
        "Search/select item",
        options=item_ids,
        key="selected_item_id",
        format_func=_item_label,
    )

selected_row = items.loc[items["item_id"] == selected_item_id].iloc[0]

qty_on_hand = selected_row["qty_on_hand"]
unit = selected_row["unit"]
sell_price = selected_row["sell_price"]

c1, c2, c3 = st.columns(3)
c1.metric("Qty on hand", f"{qty_on_hand} {unit}")
c2.metric("Unit", f"{unit}")
c3.metric("Sell price", f"{sell_price}")

st.divider()
st.subheader("Sell")

qty_input = st.number_input("Quantity", min_value=0.001, value=1.0, step=1.0, format="%.3f")

sell_clicked = st.button("Sell", type="primary", use_container_width=True)

if sell_clicked:
    try:
        qty = Decimal(str(qty_input))
        if qty <= 0:
            raise ValueError("Quantity must be > 0.")
    except (InvalidOperation, ValueError) as exc:
        st.error(f"Invalid quantity: {exc}")
        st.stop()

    try:
        with db.transaction() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    select sell_price
                    from items
                    where item_id = %s and active is true
                    """,
                    (int(selected_item_id),),
                )
                item_price_row = cur.fetchone()
                if not item_price_row:
                    raise RuntimeError("Selected item is not active or no longer exists.")
                unit_price = item_price_row["sell_price"]

                cur.execute(
                    """
                    insert into sales (cashier_id, item_id, qty, unit_price)
                    values (%s, %s, %s, %s)
                    returning sale_id, sold_at, cashier_id, item_id, qty, unit_price, line_total
                    """,
                    (cashier_id, int(selected_item_id), qty, unit_price),
                )
                sale = cur.fetchone()
                cur.execute(
                    """
                    select
                      s.sale_id, s.sold_at,
                      c.full_name as cashier,
                      i.item_name, i.unit,
                      s.qty, s.unit_price, s.line_total
                    from sales s
                    join cashiers c on c.cashier_id = s.cashier_id
                    join items i on i.item_id = s.item_id
                    where s.sale_id = %s
                    """,
                    (sale["sale_id"],),
                )
                receipt = cur.fetchone()

        db.active_items_for_pos_df.clear()
        db.items_index_df.clear()

        st.success("Sale recorded.")
        st.subheader("Receipt")
        st.write(
            {
                "sold_at": str(receipt["sold_at"]),
                "cashier": receipt["cashier"],
                "item": receipt["item_name"],
                "qty": f"{receipt['qty']} {receipt['unit']}",
                "unit_price": str(receipt["unit_price"]),
                "line_total": str(receipt["line_total"]),
                "sale_id": receipt["sale_id"],
            }
        )
    except psycopg.errors.RaiseException as exc:
        msg = getattr(getattr(exc, "diag", None), "message_primary", None) or str(exc)
        st.error(f"Sale rejected: {msg}")
    except Exception as exc:
        st.error("Failed to record sale.")
        st.exception(exc)
