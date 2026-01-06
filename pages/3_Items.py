from __future__ import annotations

from decimal import Decimal, InvalidOperation

import psycopg
import streamlit as st

import db


st.set_page_config(page_title="Items", layout="wide")
st.title("Items (Inventory)")

if not db.is_configured():
    st.warning("`DATABASE_URL` is not set.")
    st.stop()

tab_browse, tab_add, tab_edit = st.tabs(["Browse", "Add", "Edit"])

with tab_browse:
    st.subheader("Browse items")
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search (name, barcode, SKU)", placeholder="e.g. milk, 0123456789, SKU123")
    with col2:
        active_only = st.checkbox("Active only", value=True)

    where = []
    params: list[object] = []
    if active_only:
        where.append("active is true")
    if search.strip():
        where.append("(item_name ilike %s or sku ilike %s or barcode ilike %s)")
        like = f"%{search.strip()}%"
        params.extend([like, like, like])

    where_sql = "where " + " and ".join(where) if where else ""
    items_df = db.query_df(
        f"""
        select item_id, item_name, sku, barcode, qty_on_hand, unit, sell_price, active, created_at
        from items
        {where_sql}
        order by item_name
        """,
        tuple(params) if params else None,
    )

    st.dataframe(items_df, use_container_width=True, hide_index=True)

with tab_add:
    st.subheader("Add item")
    with st.form("add_item"):
        item_name = st.text_input("Item name")
        sku = st.text_input("SKU", help="Must be unique (optional).").strip() or None
        barcode = st.text_input("Barcode", help="Must be unique (optional).").strip() or None
        unit = st.text_input("Unit", value="pcs")
        qty_on_hand = st.number_input("Qty on hand", value=0.0, step=1.0, format="%.3f")
        sell_price = st.number_input("Sell price", value=0.0, step=0.5, format="%.2f")
        active = st.checkbox("Active", value=True)
        submitted = st.form_submit_button("Create", type="primary")

    if submitted:
        if not item_name.strip():
            st.error("Item name is required.")
            st.stop()
        try:
            qty_dec = Decimal(str(qty_on_hand))
            price_dec = Decimal(str(sell_price))
        except InvalidOperation:
            st.error("Invalid numeric input.")
            st.stop()

        try:
            db.execute(
                """
                insert into items (item_name, sku, barcode, unit, qty_on_hand, sell_price, active)
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (item_name.strip(), sku, barcode, unit.strip() or "pcs", qty_dec, price_dec, active),
            )
            db.items_index_df.clear()
            db.active_items_for_pos_df.clear()
            st.success("Item created.")
        except psycopg.errors.UniqueViolation as exc:
            constraint = getattr(getattr(exc, "diag", None), "constraint_name", "") or ""
            if "sku" in constraint:
                st.error("SKU already exists.")
            elif "barcode" in constraint:
                st.error("Barcode already exists.")
            else:
                st.error("SKU or barcode must be unique.")
        except Exception as exc:
            st.error("Failed to create item.")
            st.exception(exc)

with tab_edit:
    st.subheader("Edit item")
    idx = db.items_index_df()
    if idx.empty:
        st.info("No items found.")
        st.stop()

    def _label(iid: int) -> str:
        row = idx.loc[idx["item_id"] == iid].iloc[0]
        sku = row["sku"] or ""
        barcode = row["barcode"] or ""
        extras = " • ".join([x for x in [sku, barcode] if x])
        suffix = f" ({extras})" if extras else ""
        return f"{row['item_name']}{suffix}"

    item_id = st.selectbox("Select item", options=idx["item_id"].tolist(), format_func=_label)
    row = idx.loc[idx["item_id"] == item_id].iloc[0]

    with st.form("edit_item"):
        item_name = st.text_input("Item name", value=str(row["item_name"] or ""))
        sku = st.text_input("SKU", value=str(row["sku"] or "")).strip() or None
        barcode = st.text_input("Barcode", value=str(row["barcode"] or "")).strip() or None
        unit = st.text_input("Unit", value=str(row["unit"] or "pcs"))
        qty_on_hand = st.number_input("Qty on hand", value=float(row["qty_on_hand"]), step=1.0, format="%.3f")
        sell_price = st.number_input("Sell price", value=float(row["sell_price"]), step=0.5, format="%.2f")
        active = st.checkbox("Active", value=bool(row["active"]))
        saved = st.form_submit_button("Save changes", type="primary")

    if saved:
        if not item_name.strip():
            st.error("Item name is required.")
            st.stop()
        try:
            qty_dec = Decimal(str(qty_on_hand))
            price_dec = Decimal(str(sell_price))
        except InvalidOperation:
            st.error("Invalid numeric input.")
            st.stop()

        try:
            db.execute(
                """
                update items
                set item_name = %s,
                    sku = %s,
                    barcode = %s,
                    unit = %s,
                    qty_on_hand = %s,
                    sell_price = %s,
                    active = %s
                where item_id = %s
                """,
                (
                    item_name.strip(),
                    sku,
                    barcode,
                    unit.strip() or "pcs",
                    qty_dec,
                    price_dec,
                    active,
                    int(item_id),
                ),
            )
            db.items_index_df.clear()
            db.active_items_for_pos_df.clear()
            st.success("Item updated.")
        except psycopg.errors.UniqueViolation as exc:
            constraint = getattr(getattr(exc, "diag", None), "constraint_name", "") or ""
            if "sku" in constraint:
                st.error("SKU already exists.")
            elif "barcode" in constraint:
                st.error("Barcode already exists.")
            else:
                st.error("SKU or barcode must be unique.")
        except Exception as exc:
            st.error("Failed to update item.")
            st.exception(exc)
