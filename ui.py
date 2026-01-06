from __future__ import annotations

import streamlit as st


LOGO_PATH = "assets/logo.png"


def render_branding() -> None:
    logo = getattr(st, "logo", None)
    if callable(logo):
        logo(LOGO_PATH)
        return

    st.sidebar.image(LOGO_PATH, use_container_width=True)

