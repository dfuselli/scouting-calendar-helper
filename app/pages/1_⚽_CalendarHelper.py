# home.py
import streamlit as st
from common.data_handler import load_calendar_data_from_db
from ui.common import add_markdown_divider
from ui.nav import page_nav

# ── Costanti ────────────────────────────────────────────────────────────────
PAGE_TITLE = "Home"
ROW_HEIGHT_PX = 35
MAX_TABLE_HEIGHT_PX = 350
COLUMN_ORDER = ("Selezionato", "Time", "Casa", "Ospite", "Fascia")

HIDE_STREAMLIT_UI = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    div.block-container { padding-top: 0.5rem; }
    div[data-testid="stDataFrameContainer"] {
        overflow-y: auto;
        overscroll-behavior: contain;
    }
</style>
"""

LINKS = [
    ("CSI", "https://live.centrosportivoitaliano.it/25/Lombardia/Bergamo"),
    (
        "FIGC",
        "https://www.crlombardia.it/comunicati?q=&page=&content_category_value_id=27&delegazioni%5B%5D=13",
    ),
    # ("TuttoCampo", "https://www.tuttocampo.it/Lombardia/BG/"),
]

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
def _init_session_state() -> None:
    """Inizializza lo stato della sessione se non già presente."""
    if "original_df" not in st.session_state:
        st.session_state.original_df = load_calendar_data_from_db()
        st.session_state.df_visible = st.session_state.original_df.copy()
    if "last_selected_id" not in st.session_state:
        st.session_state.last_selected_id = None


# ── Logica filtri ─────────────────────────────────────────────────────────────
def _apply_filters(testo: str, categoria: str):
    """Restituisce il DataFrame filtrato senza effetti collaterali su session_state."""
    df = st.session_state.original_df.copy()

    if testo:
        mask = df["Casa"].astype(str).str.contains(testo, case=False, na=False) | df[
            "Ospite"
        ].astype(str).str.contains(testo, case=False, na=False)
        df = df[mask]

    if categoria != "Tutte":
        df = df[df["Fascia"] == categoria]

    return df


# ── Callback data_editor ──────────────────────────────────────────────────────
def _handle_change() -> None:
    changes = st.session_state.get("match_table", {})
    edited_rows = changes.get("edited_rows", {})
    if not edited_rows:
        return

    df = st.session_state.original_df
    df_visible = st.session_state.df_visible

    for row_index_str, row_changes in edited_rows.items():
        row_index = int(row_index_str)
        row_id = df_visible.iloc[row_index]["ID"]
        df_row_index = df[df["ID"] == row_id].index[0]

        for col, new_value in row_changes.items():
            old_value = df.at[df_row_index, col]
            df.at[df_row_index, col] = new_value

            if (
                col == "Selezionato"
                and new_value is True
                and old_value is not True
                and st.session_state.last_selected_id != row_id
            ):
                st.session_state.last_selected_id = row_id

            else:
                st.session_state.last_selected_id = None


# ── Componenti UI ─────────────────────────────────────────────────────────────
def _render_table(df_visible) -> None:
    height = min(ROW_HEIGHT_PX * (len(df_visible) + 1), MAX_TABLE_HEIGHT_PX)
    st.data_editor(
        data=df_visible,
        width="stretch",
        height=height,
        column_order=COLUMN_ORDER,
        key="match_table",
        hide_index=True,
        on_change=_handle_change,
        column_config={
            "Selezionato": st.column_config.CheckboxColumn("", width=25, pinned=True),
            "Time": st.column_config.TextColumn("Data", width=30, disabled=True),
            "Casa": st.column_config.TextColumn("Casa", width=50, disabled=True),
            "Ospite": st.column_config.TextColumn("Ospite", width=50, disabled=True),
            "Fascia": st.column_config.TextColumn("Fascia", width=10, disabled=True),
        },
    )


def _render_match_details(df) -> None:
    add_markdown_divider()
    st.markdown("✅ *_DETTAGLI PARTITA:_*")
    selected_id = st.session_state.last_selected_id

    if not selected_id:
        st.write("Seleziona una riga per vedere i dettagli.")
        return

    row = df[df["ID"] == selected_id]
    if row.empty:
        st.write("Partita non trovata.")
        return

    d = row.iloc[0]
    st.markdown(
        f"<p style='margin:2px 0'>🏟️ {d['Casa']} &emsp;-&emsp; {d['Ospite']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='margin:2px 0'>{d['Fascia']} &emsp;🏆 {d['Competizione']} &emsp;<strong>Girone:</strong>&nbsp;{d['Girone']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='margin:2px 0'>🕒 {d['Time']} &emsp;📅 {int(d['Giornata'])} {d['A/R']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='margin:2px 0'>📍 {d['Comune']} - {d['Indirizzo']}</p>",
        unsafe_allow_html=True,
    )


def _render_wa_code(df) -> None:
    selected = df[df["Selezionato"]]
    if selected.empty:
        return

    righe = []
    for _, row in selected.iterrows():
        righe.append(
            f"🏟️{row['Casa']}-{row['Ospite']}\n"
            f"{row['Fascia']} {row['Federazione'].upper()} 🏆{row['Competizione']} Gir. {row['Girone']}\n"
            f"🕒{row['Time']} 📅{int(row['Giornata'])} {row['A/R']}\n"
            f"📍{row['Comune'].strip()}-{row['Indirizzo']}"
        )

    testo_wa = "⚽Programma partite da visionare\n\n" + "\n\n".join(righe)

    add_markdown_divider()
    col, _ = st.columns([6, 8])
    with col:
        st.markdown("✅ *_TESTO PER INVIO PROGRAMMA VIA WHATSAPP:_*")
        st.code(testo_wa, language=None)


def _render_links() -> None:
    add_markdown_divider()
    st.markdown("🔗 *_LINKS VERIFICA DATE DAI SITI UFFICIALI:_*")
    cols = st.columns([0.5] * len(LINKS) + [13 - 0.5 * len(LINKS)])
    for col, (label, url) in zip(cols, LINKS):
        with col:
            st.markdown(f"[{label}]({url})", unsafe_allow_html=True)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    _init_session_state()

    if st.session_state.original_df.empty:
        st.warning("Nessun dato disponibile nel calendario.")
        return

    # Filtri
    col_testo, _ = st.columns([4, 16])
    with col_testo:
        testo = st.text_input("Squadra Casa/Ospite", placeholder="", icon="⚽").strip()

    col_cat, _ = st.columns([4, 16])
    with col_cat:
        opzioni_cat = ["Tutte"] + sorted(
            st.session_state.original_df["Fascia"].dropna().unique()
        )
        categoria = st.selectbox("🔵FIGC 🟡CSI", options=opzioni_cat, index=0)

    # Aggiorna df_visible ad ogni run (Streamlit re-esegue tutto comunque)
    st.session_state.df_visible = _apply_filters(testo, categoria)
    df_visible = st.session_state.df_visible

    col_table, _ = st.columns([4.5, 6])
    col_details, _ = st.columns([4.5, 6])

    with col_table:
        _render_table(df_visible)

    with col_details:
        _render_match_details(st.session_state.original_df)

    _render_wa_code(st.session_state.original_df)
    _render_links()
    add_markdown_divider()


try:
    main()
except Exception as e:
    st.error(f"Errore nell'applicazione: {e}")
    raise  # utile in sviluppo; rimuovi in produzione

page_nav()
