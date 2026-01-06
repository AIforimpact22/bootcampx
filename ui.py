from __future__ import annotations

import streamlit as st


LOGO_PATH = "assets/logo.png"


def render_branding() -> None:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
