import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time
from helpers import merge_categoria_federazione

calendar_file_path = "app/resources/AllCalendarsMerged.xlsx"

@st.cache_data(ttl="15m")
def load_calendar_data(filter_next_7_days=True):
    df = pd.read_excel(calendar_file_path, engine="openpyxl")
    df = df[df["Data"].notna()]  
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    
    # Filtra per i prossimi 7 giorni
    if filter_next_7_days:
        oggi_mezzanotte = datetime.combine(datetime.today(), time.min)
        stasera_mezzanotte = datetime.combine(datetime.today(), time.max)
        settimana_prossima = stasera_mezzanotte + timedelta(days=8)
        df = df[(df["Data"] >= oggi_mezzanotte) & (df["Data"] < settimana_prossima)]

    
    # Aggiungi colonna ID univoco per tracciabilità
    if df.empty:
        st.warning("Nessuna partita trovata nei prossimi 7 giorni." if filter_next_7_days else "Il calendario è vuoto.")
        return df
    else:
        df["ID"] = df.apply(lambda row: f'{row["Data"].strftime("%Y%m%d")}_{row["Categoria"]}_{row["Casa"]}_{row["Ospite"]}', axis=1)
        df["_TimeSort"] = pd.to_datetime(df["Data"].dt.strftime("%Y-%m-%d") + " " + df["Ora"])
        df["Time"] = df["_TimeSort"].dt.strftime("%d/%m %H:%M")
        df["Fascia"] = df.apply(lambda row: f'{"🟡" if row["Federazione"].upper() == 'CSI' else "🔵"}{merge_categoria_federazione(row["Categoria"])}', axis=1)
        df["Selezionato"] = False
        df = df.sort_values(by=["_TimeSort", "Casa"], ascending=[True, True]).drop(columns="_TimeSort")
        return df
    

def cleanup_calendar_data(df_calendario, df_geo):
    df_calendario["Comune_casefold"] = (
        df_calendario["Comune"].astype("string")
        .str.replace("\u200b", "", regex=False)   # toglie ZWSP
        .str.replace("\u00a0", " ", regex=False)  # (opzionale) NBSP -> spazio
        .str.replace(r"\s+", " ", regex=True)     # comprime whitespace
        .str.strip()
        .str.casefold()
    )
    
    # 1) Tieni solo le colonne che servono e fai distinct (Casa, Categoria, Comune)
    df_dist = (
        df_calendario[["Casa", "Categoria", "Comune", "Comune_casefold"]]
        .dropna(subset=["Comune", "Casa", "Categoria","Comune_casefold"])
        .drop_duplicates()
    )

    df_dist["casa_cat"] = df_dist["Casa"].astype(str) + " (" + df_dist["Categoria"].astype(str) + ")"

    df_agg = (
        df_dist.groupby("Comune_casefold", as_index=False)
        .agg(
            n_squadre=("Casa", "nunique"),
            casa_cat_list=("casa_cat", lambda s: sorted(set(s))),
        )
    )

    df_agg["case_str"] = df_agg["casa_cat_list"].apply(lambda xs: "<br>".join(xs))
    df_agg["case_str_hover"] = df_agg["case_str"].where(df_agg["n_squadre"] > 0, "-")

    ########################TO DEBUG BAD COMUNE VALUES #####################################
    left = (
        df_calendario[["Comune_casefold", "Comune", "Casa", "Categoria"]]
        .dropna(subset=["Comune_casefold", "Casa", "Categoria"])
        .drop_duplicates()
    )

    right = df_geo[["Comune_casefold"]].drop_duplicates()

    chk = left.merge(right, on="Comune_casefold", how="left", indicator=True)

    only_in_df = (
        chk[chk["_merge"] == "left_only"]
        .sort_values(["Comune", "Categoria", "Casa"])
        [["Comune", "Comune_casefold", "Categoria", "Casa"]]
    )

    st.write("Righe con Comune NON nel GeoJSON (con Categoria e Casa):")
    st.dataframe(only_in_df, width='stretch', hide_index=True)
    #############################################################

    df_full = df_geo.merge(df_agg, on="Comune_casefold", how="left")

    df_full["n_squadre"] = pd.to_numeric(df_full["n_squadre"], errors="coerce").fillna(0).astype(int)
    df_full["case_str_hover"] = df_full["case_str_hover"].fillna("-")
    return df_full