from ui.nav import page_nav
import streamlit as st
import plotly.express as px
from map.data_engine import load_geojson_data
from map.map_factory import create_map
from common.data_loader import load_calendar_data

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
except Exception as e:
    st.error(f"Errore durante il caricamento del file GeoJSON: {e}")
    st.stop()

try:
    df_calendario = load_calendar_data(filter_next_7_days=False)
    # 1) Tieni solo le colonne che servono e fai distinct (Casa, Categoria, Comune)
    df_dist = (
        df_calendario[["Casa", "Categoria", "Comune"]]
        .dropna(subset=["Comune", "Casa", "Categoria"])
        .drop_duplicates()
    )

    df_dist["casa_cat"] = df_dist["Casa"].astype(str) + " (" + df_dist["Categoria"].astype(str) + ")"

    df_agg = (
        df_dist.groupby("Comune", as_index=False)
        .agg(
            n_casa=("Casa", "nunique"),
            casa_cat_list=("casa_cat", lambda s: sorted(set(s))),
        )
    )

    df_agg["case_str"] = df_agg["casa_cat_list"].apply(lambda xs: "<br>".join(xs))
    df_agg["case_str_hover"] = df_agg["case_str"].where(df_agg["n_casa"] > 0, "-")

except Exception as e:
    st.error(f"Errore durante il caricamento del file Excel: {e}")
    st.stop()


# Configurazione layout a due colonne
col1, col2 = st.columns([80, 20])

# Visualizzazione mappa
with col1:
    st.subheader("Mappa")
    try:
        fig = create_map(gdf, df_agg)
        st.plotly_chart(fig, width='stretch')
    except Exception as e:
        st.error(f"Errore durante la creazione della mappa: {e}")

    st.subheader("Aggregati per comune")
    st.dataframe(
        df_agg.sort_values("n_casa", ascending=False),
        width='stretch',
        hide_index=True,
    )


# Visualizzazione dati
with col2:
    st.subheader("Dati")
