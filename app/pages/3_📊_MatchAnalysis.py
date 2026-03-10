import pandas as pd
import xlrd
from ui.nav import page_nav
import streamlit as st
from common.data_handler import cleanup_calendar_data, load_calendar_data
import numpy as np
import plotly.express as px

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

try:
    df_calendario = load_calendar_data(filter_next_7_days=False)
    df_cleaned = cleanup_calendar_data(df_calendario)
    
except Exception as e:
    st.error(f"Errore durante il caricamento del file Excel: {e}")
    st.stop()

######### Start UI ############
page_nav()
# Intestazione
filter1col, filter2col, filter3col, empty_col, top3col = st.columns([5, 4, 5, 5, 8], vertical_alignment="top")
match_data = None
osservatore_opts=[]
cat_opts=[]
squadra_opts=[]
with top3col:
    uploaded_file = st.file_uploader("Carica Excel", type=["xls"])

    if uploaded_file:
        data = uploaded_file.getvalue()

        book = xlrd.open_workbook(
            file_contents=data,
            ignore_workbook_corruption=True
        )  # ignora CompDocError [web:59]

        match_data = pd.read_excel(book, sheet_name=0, header=1,)
        match_data = match_data.drop(columns=["Risultato", "Torneo/Campionato"])

        osservatore_opts = (
            match_data["Osservatore"]
            .dropna()
            .astype("string")
            .drop_duplicates()
            .sort_values(ascending=True)
            .tolist()
        )

        cat_opts = (
            match_data["Categoria"]
            .dropna()
            .astype("string")
            .drop_duplicates()
            .sort_values(ascending=True)
            .tolist()
        )

        squadra_opts = (
            pd.concat([match_data["Squadra (casa)"], match_data["Squadra (trasferta)"]], ignore_index=True)
            .dropna()
            .astype("string")
            .drop_duplicates()
            .sort_values(ascending=True)
            .tolist()
        )

with filter1col:
    comuni_sel = st.multiselect("Osservatore", options=osservatore_opts, default=[])

with filter2col:
    cat_sel = st.multiselect("Categoria", options=cat_opts, default=[])

with filter3col:
    squadra_sel = st.multiselect("Squadra", options=squadra_opts, default=[])


# Applica filtri
if match_data is not None and not match_data.empty:
    df = match_data.copy()

    # Parsing Data
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)

    # Applica filtri
    if comuni_sel:
        df = df[df["Osservatore"].astype("string").isin(comuni_sel)]

    if cat_sel:
        df = df[df["Categoria"].astype("string").isin(cat_sel)]

    if squadra_sel:
        casa = df["Squadra (casa)"].astype("string")
        trasf = df["Squadra (trasferta)"].astype("string")
        df = df[casa.isin(squadra_sel) | trasf.isin(squadra_sel)]

    filtered_df = df
    safe_df = filtered_df.copy()
    obj_cols = safe_df.select_dtypes(include=["object"]).columns
    safe_df[obj_cols] = safe_df[obj_cols].astype("string")
else:
    filtered_df = None

if filtered_df is not None and not filtered_df.empty:
    date_ok = filtered_df["Data"].dropna()
    first_date = date_ok.min()
    last_date  = date_ok.max()
    st.caption(f"Periodo: {first_date:%d/%m/%Y} → {last_date:%d/%m/%Y}")
# Configurazione layout a due colonne
col1, col2 = st.columns([50, 50])

with col1:
    if filtered_df is not None and not filtered_df.empty:
        dfv = filtered_df.copy()
        dfv["Data"] = pd.to_datetime(dfv["Data"], errors="coerce", dayfirst=True)

        # --- KPI ---
        n_match = len(dfv)
        n_osservatori = dfv["Osservatore"].dropna().astype("string").nunique()
        n_squadre = pd.concat(
            [dfv["Squadra (casa)"], dfv["Squadra (trasferta)"]],
            ignore_index=True
        ).dropna().astype("string").nunique()

        k1, k2, k3 = st.columns(3)
        k1.metric("Match", n_match)  # widget KPI [web:174]
        k2.metric("Osservatori", n_osservatori)  # [web:174]
        k3.metric("Squadre", n_squadre)  # [web:174]


        # --- Grafico 1: Match nel tempo (giorno) ---
        ts = (
            dfv.dropna(subset=["Data"])
            .assign(Giorno=lambda d: d["Data"].dt.floor("D"))  # <-- qui
            .groupby("Giorno", as_index=False)
            .size()
            .rename(columns={"size": "Match"})
            .sort_values("Giorno")
        )
        fig1 = px.line(ts, x="Giorno", y="Match", markers=True, title="Match per giorno")  # line chart [web:176]
        st.plotly_chart(fig1, width='stretch')

        # --- Grafico 3: Heatmap giorno-settimana x ora (densità) ---
        tmp = dfv.dropna(subset=["Data"]).copy()
        tmp["GiornoSettimana"] = tmp["Data"].dt.day_name()   # es. Monday...
        tmp["Ora"] = tmp["Data"].dt.hour

        pivot = (
            tmp.pivot_table(index="GiornoSettimana", columns="Ora", values="Data", aggfunc="count")
            .fillna(0)
        )

        fig3 = px.imshow(pivot, aspect="auto", title="Densità match: giorno della settimana x ora")  # heatmap [web:181]
        st.plotly_chart(fig3, width='stretch')
    else:
        st.info("Carica il file Excel di Weak Risk con i dati dei match per visualizzare le analisi.")

with col2:
    if filtered_df is not None and not filtered_df.empty:
        dfv = filtered_df.copy()

        # KPI extra

        n_localita = dfv["Località"].dropna().astype("string").nunique()
        n_tornei = dfv.get("Torneo/Campionato", pd.Series(dtype="string")).dropna().astype("string").nunique()
        n_giocatori = (
            dfv["Giocatori"].fillna("")
                .astype("string")
                .str.split(",")
                .explode()
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
        )

        k4, k5, k6 = st.columns(3)
        k4.metric("Località uniche", n_localita)  # [web:174]
        k5.metric("Tornei unici", n_tornei)        # [web:174]
        k6.metric("Giocatori unici", n_giocatori)  # [web:174]

        # --- Grafico 2: Top categorie ---
        top_cat = (
            dfv["Categoria"].dropna().astype("string")
            .value_counts()
            .head(10)
            .reset_index()
        )
        top_cat.columns = ["Categoria", "Match"]
        fig2 = px.bar(top_cat, x="Match", y="Categoria", orientation="h", title="Top 10 categorie")  # bar chart [web:180]
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})  # ordina per valore [web:180]
        st.plotly_chart(fig2, width='stretch')


        top_obs = (
                filtered_df["Osservatore"].dropna().astype("string")
                    .value_counts()
                    .head(10)
                    .reset_index()
            )
        top_obs.columns = ["Osservatore", "Match"]

        fig_obs = px.bar(
            top_obs, x="Match", y="Osservatore",
            orientation="h",
            title="Top 10 osservatori (per # match)"
        )  # bar chart [web:180]
        fig_obs.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_obs, use_container_width=True)  # [web:223]


if filtered_df is not None and not filtered_df.empty:
    st.dataframe(
        filtered_df,
        hide_index=True,
        column_config={"Note": None},  # nasconde Note in UI [web:119]
    )