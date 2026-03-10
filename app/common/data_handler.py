import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time
from helpers import merge_categoria_federazione
import sqlite3
import tempfile
import gdown

calendar_file_path = "app/resources/AllCalendarsMerged.xlsx"
# db_path = "app/resources/scouting_assistant.db" #
gdrive_db_path = "https://drive.google.com/uc?id=1mDEHXgx53oxzAEOXETRXGwPXeYXlmiWx"


@st.cache_data(ttl=600)
def download_db():
    """Scarica DB da Drive in temp"""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    gdown.download(gdrive_db_path, temp_db.name, quiet=False)
    return temp_db.name

db_path = download_db()

def export_db():  # Solo se hai API key
    st.warning("Update manuale: scarica → salva su Drive")
    with open(db_path, "rb") as f:
        st.download_button("📤 Salva DB su PC/Drive", f.read(), "scouting_assistant.db")

# Crea tabella se non esiste
def init_db():
    create_sql = """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Data TEXT NOT NULL,
        Ora TEXT NOT NULL,
        Categoria TEXT NOT NULL,
        Casa TEXT NOT NULL,
        Ospite TEXT NOT NULL,
        Comune TEXT,
        Federazione TEXT NOT NULL,
        Girone TEXT NOT NULL,
        Indirizzo TEXT,
        Giornata TEXT NOT NULL,
        Competizione TEXT NOT NULL,
        "A/R" TEXT NOT NULL,
        Priorita INTEGER NOT NULL
    );
    """

    with sqlite3.connect(db_path) as conn:
        conn.execute(create_sql)

init_db()

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
        df["Fascia"] = df.apply(lambda row: f'{"🟡" if "CSI" in row["Federazione"].upper() else "🔵"}{merge_categoria_federazione(row["Categoria"])}', axis=1)
        df["Selezionato"] = False
        df = df.sort_values(by=["_TimeSort", "Casa"], ascending=[True, True]).drop(columns="_TimeSort")
        return df
    
st.cache_data(ttl="15m")
def load_calendar_data_from_db(filter_next_7_days=True):
    with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM matches", conn)
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
        df["Fascia"] = df.apply(lambda row: f'{"🟡" if "CSI" in row["Federazione"].upper() else "🔵"}{merge_categoria_federazione(row["Categoria"])}', axis=1)
        df["Selezionato"] = False
        df = df.sort_values(by=["_TimeSort", "Casa"], ascending=[True, True]).drop(columns="_TimeSort")
        return df
    
def cleanup_calendar_data(df_calendario):
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

    ########################TO DEBUG BAD COMUNE VALUES #####################################
    # left = (
    #     df_calendario[["Comune_casefold", "Comune", "Casa", "Categoria"]]
    #     .dropna(subset=["Comune_casefold", "Casa", "Categoria"])
    #     .drop_duplicates()
    # )

    # right = df_geo[["Comune_casefold"]].drop_duplicates()

    # chk = left.merge(right, on="Comune_casefold", how="left", indicator=True)

    # only_in_df = (
    #     chk[chk["_merge"] == "left_only"]
    #     .sort_values(["Comune", "Categoria", "Casa"])
    #     [["Comune", "Comune_casefold", "Categoria", "Casa"]]
    # )

    # st.write("Righe con Comune NON nel GeoJSON (con Categoria e Casa):")
    # st.dataframe(only_in_df, width='stretch', hide_index=True)
    #############################################################
    return df_dist
    

def aggregate_by_comune(df_dist, df_geo):
    df_agg = (
        df_dist.groupby("Comune_casefold", as_index=False)
        .agg(
            n_squadre=("Casa", "nunique"),
            casa_cat_list=("casa_cat", lambda s: sorted(set(s))),
        )
    )

    df_agg["case_str"] = df_agg["casa_cat_list"].apply(lambda xs: "<br>".join(xs))
    df_agg["case_str_hover"] = df_agg["case_str"].where(df_agg["n_squadre"] > 0, "-")

    df_full = df_geo.merge(df_agg, on="Comune_casefold", how="left")

    df_full["n_squadre"] = pd.to_numeric(df_full["n_squadre"], errors="coerce").fillna(0).astype(int)
    df_full["case_str_hover"] = df_full["case_str_hover"].fillna("-")
    return df_full

def add_matches_to_db(df_excel):
    try:
        with sqlite3.connect(db_path) as conn:

            # Scrive/aggiunge le righe alla tabella matches
            df_clean = df_excel.iloc[:, :13].dropna(subset=["Data"])
            df_clean.to_sql(
                "matches",
                conn,
                if_exists="append",   # oppure "replace" se vuoi sovrascrivere
                index=False,
            )

        st.success("Import completato con successo.")
    except Exception as e:
        st.error(f"Errore durante l'import: {e}")