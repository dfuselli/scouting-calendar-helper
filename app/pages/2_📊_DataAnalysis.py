import pandas as pd
from ui.nav import page_nav
import streamlit as st
from map.data_engine import load_geojson_data
from map.map_factory import create_map
from common.data_loader import cleanup_calendar_data, load_calendar_data,aggregate_by_comune
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
    df_cleaned = cleanup_calendar_data(df_calendario)
    
except Exception as e:
    st.error(f"Errore durante il caricamento del file Excel: {e}")
    st.stop()

######### Start UI ############
#page_nav()
# Intestazione
filter1col, filter2col, filter3col, empty_col, top3col = st.columns([5, 4, 5, 5, 8], vertical_alignment="bottom")

with top3col:
    uploaded_file = st.file_uploader(" ", type=["xls"])

# Filtro per Comune, Categoria, Squadra
comuni_opts = (
    df_calendario
      .dropna(subset=["Comune_casefold"])
      .sort_values(["Comune_casefold", "Comune"])
      .drop_duplicates(subset=["Comune_casefold"], keep="first")
      ["Comune"]
      .tolist()
)

cat_opts = (
    df_cleaned["Categoria"]
      .dropna()
      .astype("string")
      .drop_duplicates()
      .sort_values(ascending=True)
      .tolist()
)

squadra_opts = (
    df_cleaned["Casa"]
      .dropna()
      .astype("string")
      .drop_duplicates()
      .sort_values(ascending=True)
      .tolist()
)

with filter1col:
    comuni_sel = st.multiselect("Comune", options=comuni_opts, default=[])

with filter2col:
    cat_sel = st.multiselect("Categoria", options=cat_opts, default=[])

with filter3col:
    squadra_sel = st.multiselect("Squadra", options=squadra_opts, default=[])

df_view = df_cleaned.copy()
if comuni_sel:
    df_view = df_view[df_view["Comune"].astype(str).isin(comuni_sel)]
if cat_sel:
    df_view = df_view[df_view["Categoria"].astype(str).isin(cat_sel)]
if squadra_sel:
    df_view = df_view[df_view["Casa"].astype(str).isin(squadra_sel)]
df_agg = aggregate_by_comune(df_view, df_geo)

# Configurazione layout a due colonne
col1, col2 = st.columns([55, 45])

# Visualizzazione mappa
with col1:
    try:
        fig = create_map(gdf, df_agg )
        st.plotly_chart(fig, width='stretch')
    except Exception as e:
        st.error(f"Errore durante la creazione della mappa: {e}")


# Visualizzazione dati
with col2:
    st.dataframe(
        df_view
        .rename(columns={"Casa": "Squadra"})
        .loc[:, ["Squadra", "Categoria", "Comune"]]
        .sort_values("Squadra", ascending=True),
        width="stretch",
        hide_index=True,
    )

