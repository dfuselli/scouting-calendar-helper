import streamlit as st

# Configura l'app
st.set_page_config(page_title="Home", layout="wide")
st.write(
    "<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True
)

st.title("Calendari Calcio")
st.markdown(
    """
    Scegli una delle opzioni dal menu a sinistra:
    - [Calendar]: Visualizza il calendario delle partite.
    """
)
