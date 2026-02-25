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
    

def norm_key(s):
    return (
        s.astype("string")
         .str.replace("\u200b", "", regex=False)     # ZWSP
         .str.replace("\u00a0", " ", regex=False)    # NBSP
         .str.replace(r"\s+", " ", regex=True)       # spazi multipli
         .str.strip()
         .str.casefold()
    )