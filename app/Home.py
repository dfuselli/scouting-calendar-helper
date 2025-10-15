import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from helpers import merge_categoria_federazione

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

uploaded_file = "app/resources/AllCalendarsMerged.xlsx"

@st.cache_data(ttl="1h")
def load_excel(file_path):
    df = pd.read_excel(file_path, engine="openpyxl")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    
    # Filtra per i prossimi 7 giorni
    oggi = datetime.today()
    settimana_prossima = oggi + timedelta(days=7)
    df = df[(df["Data"] >= oggi) & (df["Data"] <= settimana_prossima)]
    df = df.sort_values(by=["Casa", "Ospite"], ascending=[True, True])
    
    # Aggiungi colonna ID univoco per tracciabilità
    df["ID"] = df.apply(lambda row: f'{row["Data"].strftime("%Y%m%d")}_{row["Categoria"]}_{row["Casa"]}_{row["Ospite"]}', axis=1)
    df["Time"] = df.apply(lambda row: f'{row["Data"].strftime("%d/%m")} {row["Ora"]}', axis=1)
    df["Fascia"] = df.apply(lambda row: f'{merge_categoria_federazione(row["Categoria"])} {row["Federazione"].upper()}', axis=1)
    df["Selezionato"] = df.apply(lambda row: False, axis=1)

    return df


def handle_change():

    changes = st.session_state["match_table"]
    df = st.session_state.original_df

    if "edited_rows" not in changes:
            return
    
    for row_index_str, row_changes in changes["edited_rows"].items():
        row_index = int(row_index_str)

        # Ottieni l'ID dalla riga visibile
        df_clone = st.session_state.df_clone  # df visibile nel momento della modifica
        row_id = df_clone.iloc[row_index]["ID"]

        # Trova la riga corrispondente nell'original_df
        df_row_index = df[df["ID"] == row_id].index[0]

        for col, new_value in row_changes.items():
            old_value = df.at[df_row_index, col]
            df.at[df_row_index, col] = new_value

            if col == "Selezionato" and new_value is True and old_value != True:
                if st.session_state.get("last_selected_id") != df.at[df_row_index, "ID"]:
                    st.session_state["last_selected_id"] = df.at[df_row_index, "ID"]


def print_match_details(df):
    st.subheader("Dettagli partita")
    if st.session_state.get("last_selected_id", None):
        dettagli = df[df["ID"] == st.session_state.get("last_selected_id")].iloc[0]
        st.markdown(f"<p style='margin: 2px 0;'>{dettagli["Casa"]} - {dettagli["Ospite"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'><strong>Categoria:</strong> {dettagli["Fascia"]} <strong>Girone:</strong>{dettagli["Girone"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'><strong>Data:</strong> {dettagli["Time"]} <strong>Giornata:</strong> {dettagli["Giornata"]} {dettagli["A/R"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'><strong>Indirizzo:</strong> {dettagli["Indirizzo"]}</p>", unsafe_allow_html=True)
    else:
        st.write("Seleziona una riga per vedere i dettagli.")

def print_wa_code(df):
    righe_selezionate =  df[df["Selezionato"]]
    if not righe_selezionate.empty:
        testo_wa = "⚽Partite in programma da visionare:"
        for _, row in righe_selezionate.iterrows():
            blocco = (
                f'{row["Categoria"]} {row["Federazione"].upper()} \n'
                f'{row["Casa"]} - {row["Ospite"]}\n'
                f'Girone {row["Girone"]}\n'
                f'{row["Time"]}'
            ) 
            testo_wa += "\n\n" + blocco if testo_wa else blocco

        st.markdown("---")
        wa_cols = st.columns([6, 8])
        with wa_cols[0]:
            st.markdown("Testo da copiare per inviarlo via WhatsApp")
            st.code(testo_wa, language=None)

try:
    # Legge il file Excel
    if "original_df" not in st.session_state:
        st.session_state.original_df = load_excel(uploaded_file)

    df_clone = st.session_state.original_df.copy()

    # Filtri
    cols = st.columns([3, 3, 2, 12])
    with cols[0]:
        testo_filtrato = st.text_input("Squadra Casa/Ospite", placeholder="", icon="⚽").strip()
    with cols[1]:
        categoria_selezionata = st.selectbox("Fascia", options=["Tutte"] + sorted(df_clone["Fascia"].dropna().unique()), index=0)
    with cols[2]:
        girone_selezionato = st.selectbox("Girone", options=["Tutti"] + sorted(df_clone["Girone"].dropna().unique()), index=0)

    if testo_filtrato:
        mask_casa = df_clone["Casa"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        mask_ospite = df_clone["Ospite"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        df_clone = df_clone[mask_casa | mask_ospite]
    
    if categoria_selezionata != "Tutte":
        df_clone = df_clone[df_clone["Fascia"] == categoria_selezionata]

    if girone_selezionato != "Tutti":
        df_clone = df_clone[df_clone["Girone"] == girone_selezionato]

    # Dopo il filtro, aggiorna il df visibile
    st.session_state.df_clone = df_clone

    cols = st.columns([4.5, 6])
    with cols[0]:
        st.data_editor(
            data=df_clone,
            width='stretch',
            height=350,
            column_order = ("Selezionato", "Time", "Casa", "Ospite", "Fascia"),
            key="match_table",
            hide_index=True,
            on_change=handle_change,
            column_config={
                "Selezionato": st.column_config.CheckboxColumn(width=30, pinned=True),
                "Time": st.column_config.TextColumn("Data", disabled=True),
                "Casa": st.column_config.TextColumn("Casa", disabled=True),
                "Ospite": st.column_config.TextColumn("Ospite", disabled=True),
                "Fascia": st.column_config.TextColumn("Fascia", disabled=True),
            },
        )

    # Filtra df per mostrare dettagli delle righe selezionate
    with cols[1]:
        print_match_details(st.session_state.original_df)

    # Genera testo WhatsApp
    print_wa_code(st.session_state.original_df)

    st.markdown("---")
    st.write("Link per verifica calendari dai siti ufficiali")
    btn_cols = st.columns([0.5, 0.5, 1.5, 13])
    with btn_cols[0]:
        st.markdown("[CSI](https://live.centrosportivoitaliano.it/25/Lombardia/Bergamo)", unsafe_allow_html=True)
    with btn_cols[1]:
        st.markdown("[FIGC](https://www.crlombardia.it/comunicati?q=&page=&content_category_value_id=27&delegazioni%5B%5D=13)", unsafe_allow_html=True)
    with btn_cols[2]:
        st.markdown("[TuttoCampo](https://www.tuttocampo.it/Lombardia/BG/)", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")

