from __future__ import annotations

import psycopg
import streamlit as st

import db
import ui


st.set_page_config(page_title="Cashiers", layout="wide")
ui.render_branding()
st.title("Cashiers")

if not db.is_configured():
    st.warning("`DATABASE_URL` is not set.")
    st.stop()

tab_browse, tab_add, tab_edit = st.tabs(["Browse", "Add", "Edit"])

with tab_browse:
    st.subheader("Browse cashiers")
    search = st.text_input("Search (name or username)", placeholder="e.g. Alex, alex01")
    where = []
    params: list[object] = []
    if search.strip():
        where.append("(full_name ilike %s or username ilike %s)")
        like = f"%{search.strip()}%"
        params.extend([like, like])
    where_sql = "where " + " and ".join(where) if where else ""
    cashiers_df = db.query_df(
        f"""
        select cashier_id, full_name, username, active, created_at
        from cashiers
        {where_sql}
        order by full_name
        """,
        tuple(params) if params else None,
    )
    st.dataframe(cashiers_df, use_container_width=True, hide_index=True)

with tab_add:
    st.subheader("Add cashier")
    with st.form("add_cashier"):
        full_name = st.text_input("Full name")
        username = st.text_input("Username (unique, optional)").strip() or None
        active = st.checkbox("Active", value=True)
        submitted = st.form_submit_button("Create", type="primary")

    if submitted:
        if not full_name.strip():
            st.error("Full name is required.")
            st.stop()
        try:
            db.execute(
                """
                insert into cashiers (full_name, username, active)
                values (%s, %s, %s)
                """,
                (full_name.strip(), username, active),
            )
            db.cashiers_index_df.clear()
            db.active_cashiers_df.clear()
            st.success("Cashier created.")
        except psycopg.errors.UniqueViolation:
            st.error("Username already exists.")
        except Exception as exc:
            st.error("Failed to create cashier.")
            st.exception(exc)

with tab_edit:
    st.subheader("Edit cashier")
    idx = db.cashiers_index_df()
    if idx.empty:
        st.info("No cashiers found.")
        st.stop()

    def _label(cid: int) -> str:
        row = idx.loc[idx["cashier_id"] == cid].iloc[0]
        username = row["username"]
        suffix = f" (@{username})" if username else ""
        return f"{row['full_name']}{suffix}"

    cashier_id = st.selectbox("Select cashier", options=idx["cashier_id"].tolist(), format_func=_label)
    row = idx.loc[idx["cashier_id"] == cashier_id].iloc[0]

    with st.form("edit_cashier"):
        full_name = st.text_input("Full name", value=str(row["full_name"] or ""))
        username = st.text_input("Username", value=str(row["username"] or "")).strip() or None
        active = st.checkbox("Active", value=bool(row["active"]))
        saved = st.form_submit_button("Save changes", type="primary")

    if saved:
        if not full_name.strip():
            st.error("Full name is required.")
            st.stop()
        try:
            db.execute(
                """
                update cashiers
                set full_name = %s,
                    username = %s,
                    active = %s
                where cashier_id = %s
                """,
                (full_name.strip(), username, active, int(cashier_id)),
            )
            db.cashiers_index_df.clear()
            db.active_cashiers_df.clear()
            st.success("Cashier updated.")
        except psycopg.errors.UniqueViolation:
            st.error("Username already exists.")
        except Exception as exc:
            st.error("Failed to update cashier.")
            st.exception(exc)
