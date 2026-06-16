from __future__ import annotations

from pathlib import Path

import streamlit as st
from streamlit_option_menu import option_menu

from src.auth import logout
from src.config.settings import NAVIGATION_ITEMS, PRIMARY_COLOR, SIDEBAR_CSS
from src.i18n import AVAILABLE_LANGUAGES, get_language, set_language, t


def _render_language_selector() -> None:
    options = list(AVAILABLE_LANGUAGES.keys())
    current = get_language()
    index = options.index(current) if current in options else 0

    selected = st.sidebar.selectbox(
        t("sidebar.language"),
        options=options,
        index=index,
        format_func=lambda code: AVAILABLE_LANGUAGES[code],
        key="sidebar_language_selector",
    )
    if selected != current:
        set_language(selected)
        st.rerun()


def render_sidebar(user_email: str | None = None, user_role_key: str | None = None, auth_enabled: bool = False) -> str:
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

    logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo_CEAGRE.avif"
    if logo_path.exists():
        try:
            st.sidebar.image(str(logo_path), width=200)
        except Exception:
            st.sidebar.caption(t("sidebar.logo_fallback"))

    st.sidebar.markdown(f'<div class="ceagre-title">{t("sidebar.title")}</div>', unsafe_allow_html=True)

    _render_language_selector()

    with st.sidebar:
        labels = [t(item.label_key) for item in NAVIGATION_ITEMS]
        selected_label = option_menu(
            menu_title=None,
            options=labels,
            icons=[item.icon for item in NAVIGATION_ITEMS],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": PRIMARY_COLOR, "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "4px 0",
                    "--hover-color": "#e2e8f0",
                    "border-radius": "8px",
                    "padding": "10px 12px",
                },
                "nav-link-selected": {"background-color": PRIMARY_COLOR, "color": "white"},
            },
        )

        if auth_enabled:
            st.markdown("---")
            st.caption(t("sidebar.connected_as", email=user_email or "anonymous"))
            if user_role_key:
                st.caption(t("sidebar.profile", role=t(user_role_key)))
            if st.button(t("sidebar.logout"), use_container_width=True):
                logout()
                st.rerun()

    selected_index = labels.index(selected_label)
    return NAVIGATION_ITEMS[selected_index].key



