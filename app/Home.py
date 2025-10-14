import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Configura la pagina
st.set_page_config(page_title="Home", layout="wide")
st.write("<style>div.block-container{padding-top:0.5rem;}</style>", unsafe_allow_html=True)
st.markdown("Partite Settore di Base")

uploaded_file = "app/resources/AllCalendarsMerged.xlsx"

@st.cache_data(ttl="1h")
def load_excel(file_path):
    df = pd.read_excel(file_path, engine="openpyxl")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    
    # Filtra per i prossimi 7 giorni
    oggi = datetime.today()
    settimana_prossima = oggi + timedelta(days=7)
    df = df[(df["Data"] >= oggi) & (df["Data"] <= settimana_prossima)]
    df = df.sort_values(by=["Data", "Casa"], ascending=[True, True])
    
    # Aggiungi colonna ID univoco per tracciabilità
    df["ID"] = df.apply(lambda row: f'{row["Data"].strftime("%Y%m%d")}_{row["Categoria"]}_{row["Casa"]}_{row["Ospite"]}', axis=1)
    df["Time"] = df.apply(lambda row: f'{row["Data"].strftime("%d/%m")} {row["Ora"]}', axis=1)

    return df

try:
    # Legge il file Excel
    df = load_excel(uploaded_file)

    # Filtri
    cols = st.columns([4, 3, 2, 12])
    with cols[0]:
        testo_filtrato = st.text_input("Squadra Casa/Ospite", placeholder="", icon="⚽").strip()
    with cols[1]:
        categoria_selezionata = st.selectbox("Categoria", options=["Tutte"] + sorted(df["Categoria"].dropna().unique()), index=0)
    with cols[2]:
        girone_selezionato = st.selectbox("Girone", options=["Tutti"] + sorted(df["Girone"].dropna().unique()), index=0)

    # Applichiamo i filtri
    df_clone = df.copy()  # evita SettingWithCopyWarning
    if testo_filtrato:
        mask_casa = df_clone["Casa"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        mask_ospite = df_clone["Ospite"].astype(str).str.contains(testo_filtrato, case=False, na=False)
        df_clone = df_clone[mask_casa | mask_ospite]
    
    if categoria_selezionata != "Tutte":
        df_clone = df_clone[df_clone["Categoria"] == categoria_selezionata]

    if girone_selezionato != "Tutti":
        df_clone = df_clone[df_clone["Girone"] == girone_selezionato]

    # Prepara DataFrame da mostrare
    columns_to_hide = ["Data","Ora","Indirizzo", "A/R", "Girone", "Giornata", "Federazione"]
    display_df = df_clone.drop(columns=columns_to_hide, errors='ignore')
    ordine_colonne = ["Time", "Casa", "Ospite", "Categoria"]
    colonne = [col for col in ordine_colonne if col in display_df.columns]
    display_df["ID"] = df_clone["ID"].values  # mantiene ID anche nella vista

    # Recupera selezione precedente (se esiste)
    prev_selected_ids = st.session_state.get("selected_ids", set())

    cols = st.columns([5, 5])
    with cols[0]:
        st.dataframe(
            display_df[colonne],
            width='stretch',
            height=350,
            on_select="rerun",
            selection_mode="multi-row",
            key="match_table",
            hide_index=True
        )

    # Rileva righe selezionate nella visualizzazione attuale
    selected_rows = st.session_state.get("match_table", {}).get("selection", {}).get("rows", [])
    selected_ids_now  = set(display_df.iloc[selected_rows]["ID"]) if selected_rows else set()
    # Inizializza lo stato globale
    if "selected_ids" not in st.session_state:
        st.session_state["selected_ids"] = set()

    # Identifica nuova selezione
    new_selection = selected_ids_now  - prev_selected_ids
    if new_selection:
        last_selected_id = list(new_selection)[-1]  # prendi l'ultima "nuova" selezione
        st.session_state["last_selected_id"] = last_selected_id
    else:
        last_selected_id = st.session_state.get("last_selected_id", None)

    # Accumula selezioni: unisci selezioni precedenti con quelle attuali
    deselezionati = st.session_state["selected_ids"] - selected_ids_now
    st.session_state["selected_ids"].update(selected_ids_now)
    # Rimuovere selezioni deselezionate, devi fare diff:
    st.session_state["selected_ids"] -= deselezionati

    # Filtra df per mostrare dettagli delle righe selezionate
    with cols[1]:
        st.subheader("Dettagli partita")
        if last_selected_id:
            dettagli = df[df["ID"] == last_selected_id].iloc[0]
            for col, val in dettagli.items():
                if col == "ID":
                    continue  # salta la colonna ID
                st.markdown(f"<p style='margin: 2px 0;'><strong>{col}:</strong> {val.strftime("%d/%m/%y") if col=="Data" else val}</p>", unsafe_allow_html=True)
        else:
            st.write("Seleziona una riga per vedere i dettagli.")

    # Genera testo WhatsApp
    righe_selezionate = df[df["ID"].isin(st.session_state["selected_ids"])]
    if not righe_selezionate.empty:
        testo_wa = ""
        for _, row in righe_selezionate.iterrows():
            blocco = (
                f'{row["Categoria"]} {row["Federazione"].upper()} \n'
                f'{row["Casa"]} - {row["Ospite"]}\n'
                f'Girone {row["Girone"]}\n'
                f'{row["Ora"]}'
            ) 
            testo_wa += "\n\n" + blocco if testo_wa else blocco

        st.markdown("---")
        wa_cols = st.columns([6, 8])
        with wa_cols[0]:
            st.markdown("Testo da copiare per inviarlo via WhatsApp")
            st.code(testo_wa, language=None)

    st.markdown("---")
    st.write("Link per verifica calendari dai siti ufficiali")
    btn_cols = st.columns([1, 1, 13])
    with btn_cols[0]:
        st.markdown("[CSI](https://live.centrosportivoitaliano.it/25/Lombardia/Bergamo)", unsafe_allow_html=True)
    with btn_cols[1]:
        st.markdown("[FIGC](https://www.crlombardia.it/comunicati?q=&page=&content_category_value_id=27&delegazioni%5B%5D=13)", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")
