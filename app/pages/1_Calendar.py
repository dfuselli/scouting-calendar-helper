import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


# Upload del file
uploaded_file = "app/resources/AllCalendarsMerged.xlsx"

st.set_page_config(page_title="Home", layout="wide")
st.subheader("Partite  Non Agonistica")

try:
    # Legge il file Excel
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    
    # ✅ Parsing della colonna "Data" (assicurati che il nome corrisponda esattamente)
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')

    # ✅ Filtra per i prossimi 7 giorni
    oggi = datetime.today()
    settimana_prossima = oggi + timedelta(days=14)
    df = df[(df["Data"] >= oggi) & (df["Data"] <= settimana_prossima)]

    df = df.sort_values(by=["Data", "Casa"], ascending=[True, True])

    # --- FILTRO DATA ---
     # Creiamo due colonne affiancate per i filtri
    col1, col2 = st.columns(2)

    with col1:
        # Filtro testo generico su Casa e Ospite
        testo_filtrato = st.text_input("Cerca testo in 'Casa' e 'Ospite' (case insensitive)")

    with col2:
        # Filtro data
        min_date = df["Data"].min().date()
        max_date = df["Data"].max().date()
        selected_date_range = st.date_input(
            "Filtra per Data (intervallo)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    # Applichiamo i filtri
    if testo_filtrato:
        mask_casa = df["Casa"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        mask_ospite = df["Ospite"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        df = df[mask_casa | mask_ospite]

    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
        df = df[
            (df["Data"].dt.date >= selected_date_range[0]) &
            (df["Data"].dt.date <= selected_date_range[1])
        ]
    else:
        df = df[df["Data"].dt.date == selected_date_range]

    # Nascondi colonna Indirizzo solo nella visualizzazione
    columns_to_hide = ["Indirizzo", "A/R", "Girone", "Giornata"]
    display_df = df.drop(columns=columns_to_hide, errors='ignore')
    display_df["Data"] = display_df["Data"].dt.strftime("%d/%m/%y")
    
    # Display dataframe
    st.dataframe(display_df)

except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")
