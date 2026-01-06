import streamlit as st

import db
import ui


st.set_page_config(page_title="Bootcampx Cashier System", page_icon="assets/logo.png", layout="wide")
ui.render_branding()

st.title("Bootcampx Cashier System")
st.caption("Use the sidebar to navigate: Dashboard, Sell, Items, Cashiers, Sales.")

if not db.is_configured():
    st.warning(
        "`DATABASE_URL` is not set. Add it to your environment, a local `.env`, or `.streamlit/secrets.toml`."
    )
    st.code('DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"')
    st.stop()

try:
    db.query_df("select 1 as ok")
    st.success("Database connection OK.")
except Exception as exc:
    st.error("Database connection failed.")
    st.exception(exc)
    st.stop()

st.info("Open a page from the sidebar to begin.")
