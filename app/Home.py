import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


# Upload del file
uploaded_file = "app/resources/AllCalendarsMerged.xlsx"

st.set_page_config(page_title="Home", layout="wide")
st.write(
    "<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True
)
st.subheader("Partite Settore di Base")

try:
    # Legge il file Excel
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    
    # ✅ Parsing della colonna "Data" (assicurati che il nome corrisponda esattamente)
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')

    # ✅ Filtra per i prossimi 7 giorni
    oggi = datetime.today()
    settimana_prossima = oggi + timedelta(days=7)
    df = df[(df["Data"] >= oggi) & (df["Data"] <= settimana_prossima)]
    df = df.sort_values(by=["Data", "Casa"], ascending=[True, True])

    # --- FILTRO DATA ---
     # Creiamo due colonne affiancate per i filtri
    col1, col2, col3 = st.columns([2, 2, 6])  # 1:1:2 dimension ratio

    with col1:
        # Filtro testo generico su Casa e Ospite
        testo_filtrato = st.text_input(label="",placeholder="Cerca per Squadra", icon="⚽")

    # with col2:
    #     # Filtro data
    #     min_date = df["Data"].min().date()
    #     max_date = df["Data"].max().date()
    #     selected_date_range = st.date_input(
    #         "Filtra per intervallo Data",
    #         value=(min_date, max_date),
    #         min_value=min_date,
    #         max_value=max_date,
    #     )

    # Applichiamo i filtri
    if testo_filtrato:
        mask_casa = df["Casa"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        mask_ospite = df["Ospite"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        df = df[mask_casa | mask_ospite]

    # if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
    #     df = df[
    #         (df["Data"].dt.date >= selected_date_range[0]) &
    #         (df["Data"].dt.date <= selected_date_range[1])
    #     ]
    # else:
    #     df = df[df["Data"].dt.date == selected_date_range]

    # Nascondi colonna Indirizzo solo nella visualizzazione
    columns_to_hide = ["Indirizzo", "A/R", "Girone", "Giornata", "Federazione"]
    display_df = df.drop(columns=columns_to_hide, errors='ignore')
    display_df["Data"] = display_df["Data"].dt.strftime("%d/%m/%y")
    
    # Recupera indice riga selezionata
    selected_rows = st.session_state.get("match_table", {}).get("selection", {}).get("rows", [])

    col1, col2 = st.columns([5, 5])  # 3:1 dimension ratio

    with col1:
        # Mostra il dataframe con selezione abilitata
        ordine_colonne = ["Casa", "Ospite","Categoria", "Ora", "Data"]
        colonne = [col for col in ordine_colonne if col in display_df.columns]
        st.dataframe(
            display_df[colonne],
            width='stretch',
            height=350,
            on_select="rerun",
            selection_mode="single-row",
            key="match_table",
            hide_index=True
        )

    with col2:
        st.subheader("Dettagli partita")
        if selected_rows:
            selected_idx = selected_rows[0]
            dettagli = df.iloc[selected_idx]
            for col, val in dettagli.items():
                st.markdown(f"<p style='margin: 2px 0;'><strong>{col}:</strong> {val}</p>", unsafe_allow_html=True)
        else:
            st.write("Seleziona una riga per vedere i dettagli.")
    

    if selected_rows:
        testo_da_copiare = f'{dettagli["Categoria"]} {dettagli["Federazione"].upper()} \n{dettagli["Casa"]} - {dettagli["Ospite"]}\nGirone {dettagli["Girone"]}\n{dettagli["Ora"]}'
        st.markdown("---")
        wa_col1, wa_col2 = st.columns([6, 8]) 
        with wa_col1:
            st.markdown("Testo da copiare per inviarlo via WhatsApp")
            st.code(testo_da_copiare, language=None)
        
    st.markdown("---")
    st.write("Link per verifica calendari dai siti ufficiali")
    btn_col2, btn_col3, btn_col4 = st.columns([1,1,13]) 
    with btn_col2:
        st.markdown("[CSI](https://live.centrosportivoitaliano.it/25/Lombardia/Bergamo)", unsafe_allow_html=True)
    with btn_col3:
        st.markdown("[FIGC](https://www.crlombardia.it/comunicati?q=&page=&content_category_value_id=27&delegazioni%5B%5D=13)", unsafe_allow_html=True)


except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")
