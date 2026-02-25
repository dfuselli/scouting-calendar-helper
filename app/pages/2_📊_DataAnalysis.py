import pandas as pd
from ui.nav import page_nav
import streamlit as st
from map.data_engine import load_geojson_data
from map.map_factory import create_map
from common.data_loader import cleanup_calendar_data, load_calendar_data
import json

# Configura la pagina
st.set_page_config(page_title="Home", layout="wide")
st.write("<style>div.block-container{padding-top:0.5rem;}</style>", unsafe_allow_html=True)

# CSS per nascondere la topbar e il footer
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

page_nav()
# Intestazione
top3col, filter1col, filter2col, empty_col = st.columns([4, 2, 2, 5])

with top3col:
    uploaded_file = st.file_uploader("Carica file .xls", type=["xls"])

# Caricamento dei dati
try:
    gdf = load_geojson_data()
    geojson = json.loads(gdf.to_json())
    geo_comune_names = pd.Series([f["properties"]["name"] for f in geojson["features"]], name="Comune")
    df_geo = geo_comune_names.to_frame()
    df_geo["Comune_casefold"] = (
        df_geo["Comune"].astype("string")
        .str.replace("\u200b", "", regex=False)   # toglie ZWSP
        .str.replace("\u00a0", " ", regex=False)  # (opzionale) NBSP -> spazio
        .str.replace(r"\s+", " ", regex=True)     # comprime whitespace
        .str.strip()
        .str.casefold()
    )

except Exception as e:
    st.error(f"Errore durante il caricamento del file GeoJSON: {e}")
    st.stop()

try:
    df_calendario = load_calendar_data(filter_next_7_days=False)
    df_full = cleanup_calendar_data(df_calendario, df_geo)
    
except Exception as e:
    st.error(f"Errore durante il caricamento del file Excel: {e}")
    st.stop()


# Configurazione layout a due colonne
col1, col2 = st.columns([80, 20])

# Visualizzazione mappa
with col1:
    st.subheader("Mappa")
    try:
        fig = create_map(gdf, df_full)
        st.plotly_chart(fig, width='stretch')
    except Exception as e:
        st.error(f"Errore durante la creazione della mappa: {e}")

    st.subheader("Aggregati per comune")
    st.dataframe(
        df_full.sort_values("n_squadre", ascending=False),
        width='stretch',
        hide_index=True,
    )


# Visualizzazione dati
with col2:
    st.subheader("Dati")
