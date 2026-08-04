import streamlit as st


def add_markdown_divider() -> None:
    st.markdown(
        '<hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">',
        unsafe_allow_html=True,
    )
