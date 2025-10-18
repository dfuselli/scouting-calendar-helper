import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time
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

def stop_scrolldown():
    st.markdown(
                """
                <style>
                div[data-testid="stDataFrameContainer"] {
                    overflow-y: auto;  /* permette solo scroll interno */
                    overscroll-behavior: contain;  /* evita propagazione momentum */
                }
                </style>
                """,
                unsafe_allow_html=True
            )
    
@st.cache_data(ttl="15m")
def load_excel(file_path):
    df = pd.read_excel(file_path, engine="openpyxl")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    
    # Filtra per i prossimi 7 giorni
    oggi_mezzanotte = datetime.combine(datetime.today(), time.min)
    settimana_prossima = oggi_mezzanotte + timedelta(days=7)
    df = df[(df["Data"] >= oggi_mezzanotte) & (df["Data"] < settimana_prossima)]
    df = df.sort_values(by=["Casa", "Ospite"], ascending=[True, True])
    
    # Aggiungi colonna ID univoco per tracciabilità
    df["ID"] = df.apply(lambda row: f'{row["Data"].strftime("%Y%m%d")}_{row["Categoria"]}_{row["Casa"]}_{row["Ospite"]}', axis=1)
    df["Time"] = df.apply(lambda row: f'{row["Data"].strftime("%d/%m")} {row["Ora"]}', axis=1)
    df["Fascia"] = df.apply(lambda row: f'{"🟡" if row["Federazione"].upper() == 'CSI' else "🔵"}{merge_categoria_federazione(row["Categoria"])}', axis=1)
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
        df_visible = st.session_state.df_visible  # df visibile nel momento della modifica
        row_id = df_visible.iloc[row_index]["ID"]

        # Trova la riga corrispondente nell'original_df
        df_row_index = df[df["ID"] == row_id].index[0]

        for col, new_value in row_changes.items():
            old_value = df.at[df_row_index, col]
            df.at[df_row_index, col] = new_value

            if col == "Selezionato" and new_value is True and old_value != True:
                if st.session_state.get("last_selected_id") != df.at[df_row_index, "ID"]:
                    st.session_state["last_selected_id"] = df.at[df_row_index, "ID"]


def print_match_details(df):
    st.markdown("✅*_DETTAGLI PARTITA:_*")
    if st.session_state.get("last_selected_id", None):
        dettagli = df[df["ID"] == st.session_state.get("last_selected_id")].iloc[0]
        st.markdown(f"<p style='margin: 2px 0;'>🏟️{dettagli["Casa"]}&emsp;✈️{dettagli["Ospite"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'>{dettagli["Fascia"]} &emsp;<strong>Girone:</strong>&nbsp;{dettagli["Girone"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'>🕒{dettagli["Time"]} &emsp;📅 {dettagli["Giornata"]} {dettagli["A/R"]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 2px 0;'>📍{dettagli["Indirizzo"]}</p>", unsafe_allow_html=True)
    else:
        st.write("Seleziona una riga per vedere i dettagli.")

def print_wa_code(df):
    righe_selezionate =  df[df["Selezionato"]]
    if not righe_selezionate.empty:
        testo_wa = "⚽Programma partite da visionare⚽"
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
            st.markdown("✅*_TESTO PER INVIO PROGRAMMA VIA WHATSAPP:_*")
            st.code(testo_wa, language=None)

try:
    # Legge il file Excel
    if "original_df" not in st.session_state:
        st.session_state.original_df = load_excel(uploaded_file)
        st.session_state.df_visible  = st.session_state.original_df.copy()

    # 🔹 Salva i vecchi valori (solo la prima volta)
    for key in ["old_testo", "old_categoria", "old_girone"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # Filtri
    cols = st.columns([4, 16])
    with cols[0]:
        testo_filtrato = st.text_input("Squadra Casa/Ospite", placeholder="", icon="⚽").strip()
    cols = st.columns([4, 16])
    with cols[0]:
        categoria_selezionata = st.selectbox("🔵FIGC 🟡CSI ", options=["Tutte"] + sorted(st.session_state.original_df["Fascia"].dropna().unique()), index=0)
    # with cols[1]:
    #     girone_selezionato = st.selectbox("Girone", options=["Tutti"] + sorted(st.session_state.original_df["Girone"].dropna().unique()), index=0)

    # --- CONTROLLO VARIAZIONI ---
    filtri_cambiati = (
        testo_filtrato != st.session_state.old_testo or
        # girone_selezionato != st.session_state.old_girone or
        categoria_selezionata != st.session_state.old_categoria
    )

    if filtri_cambiati:
        st.session_state.df_visible  = st.session_state.original_df.copy()
        df_visible = st.session_state.df_visible
        if testo_filtrato:
            mask_casa = df_visible["Casa"].astype(str).str.contains(testo_filtrato, case=False, na=False)
            mask_ospite = df_visible["Ospite"].astype(str).str.contains(testo_filtrato, case=False, na=False)
            df_visible = df_visible[mask_casa | mask_ospite]
        
        if categoria_selezionata != "Tutte":
            df_visible = df_visible[df_visible["Fascia"] == categoria_selezionata]

        # if girone_selezionato != "Tutti":
        #     df_visible = df_visible[df_visible["Girone"] == girone_selezionato]

        # Aggiorna stato e salvataggio dei valori attuali
        st.session_state.df_visible = df_visible
        st.session_state.old_testo = testo_filtrato
        st.session_state.old_categoria = categoria_selezionata
        # st.session_state.old_girone = girone_selezionato
    else:
        df_visible = st.session_state.df_visible

    stop_scrolldown()
    cols = st.columns([4.5, 6])
    with cols[0]:
        with st.container():
            altezza_per_riga = 35  # px per riga (approssimativa)
            altezza_massima = 350  # px, per non occupare tutto lo schermo

            altezza_calcolata = min(altezza_per_riga * (len(df_visible) + 1), altezza_massima)
            st.data_editor(
                data=df_visible,
                width='stretch',
                height=altezza_calcolata,
                column_order = ("Selezionato", "Time", "Casa", "Ospite", "Fascia"),
                key="match_table",
                hide_index=True,
                on_change=handle_change,
                column_config={
                    "Selezionato": st.column_config.CheckboxColumn("", width=35, pinned=True),
                    "Time": st.column_config.TextColumn("Data", disabled=True),
                    "Casa": st.column_config.TextColumn("Casa", disabled=True),
                    "Ospite": st.column_config.TextColumn("Ospite", disabled=True),
                    "Fascia": st.column_config.TextColumn("Fascia", disabled=True),
                },
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # Filtra df per mostrare dettagli delle righe selezionate
    cols = st.columns([4.5, 6])
    with cols[0]:
        with st.container():
            print_match_details(st.session_state.original_df)

    # Genera testo WhatsApp
    print_wa_code(st.session_state.original_df)

    st.markdown("---")
    st.markdown("🔗*_LINKS VERIFICA DATE DAI SITI UFFICIALI:_*")
    btn_cols = st.columns([0.5, 0.5, 1.5, 13])
    with btn_cols[0]:
        st.markdown("[CSI](https://live.centrosportivoitaliano.it/25/Lombardia/Bergamo)", unsafe_allow_html=True)
    with btn_cols[1]:
        st.markdown("[FIGC](https://www.crlombardia.it/comunicati?q=&page=&content_category_value_id=27&delegazioni%5B%5D=13)", unsafe_allow_html=True)
    with btn_cols[2]:
        st.markdown("[TuttoCampo](https://www.tuttocampo.it/Lombardia/BG/)", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")

