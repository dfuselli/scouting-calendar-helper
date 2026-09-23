import re

import pandas as pd
import streamlit as st
from streamlit_pivot import st_pivot_table
from ui.common import add_markdown_divider
from ui.nav import page_nav

PAGE_TITLE = "Business Intelligence: Incrocio Segnalazioni Partite"

HIDE_STREAMLIT_UI = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    div.block-container { padding-top: 0.5rem; }
</style>
"""

st.set_page_config(page_title=PAGE_TITLE, page_icon="⚽", layout="wide")
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)

GRUPPI = ["Anno", "Societa", "Nome", "Osservatore"]


def is_segnalato(row) -> bool:
    return str(row["Segnalato"]).strip().lower() == "true"


def voto_numerico(voto) -> float | None:
    m = re.match(r"^\s*([0-9]+(?:[.,][0-9]+)?)", str(voto))
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v if v > 0 else None


def esito(row) -> str:
    if not is_segnalato(row):
        return "❌"
    stato = str(row["Stato"]).strip()
    v = voto_numerico(row["Voto"])
    if v is not None:
        return f"{stato or 'Segnalato'} ({v:.2f})"
    return stato or "Segnalato"


@st.cache_data(show_spinner=False)
def load_csv(buffer) -> pd.DataFrame:
    df = pd.read_csv(buffer, sep=";", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.fillna("")

    df["Anno"] = df["Anno"].astype(str).str.strip()
    df["Nome"] = df["Nome"].astype(str).str.strip()
    df["Societa"] = df["Societa"].astype(str).str.strip()
    df["Stato"] = df["Stato"].astype(str).str.strip()
    df["Osservatore"] = df["Osservatore"].astype(str).str.strip()
    df["ClasseOsservatore"] = df["ClasseOsservatore"].astype(str).str.strip()
    df["Partita"] = df["Partita"].astype(str).str.strip()

    df["Data_Partita_dt"] = pd.to_datetime(
        df["Data_Partita"], format="%d/%m/%Y", errors="coerce"
    )

    df["Esito"] = df.apply(esito, axis=1)
    df["Voto_num"] = df["Voto"].map(voto_numerico)
    df["NDS"] = (~df["Segnalato"].str.strip().str.lower().eq("true")).astype(int)
    df["Segnalato_num"] = df["NDS"].eq(0).astype(int)
    df["Giocatore_Segnalato"] = df["Nome"].where(df["Segnalato_num"].eq(1))

    # ---- Colonne per classe osservatore (flag 0/1) ----
    def has_classe(classe: str, keyword: str) -> int:
        return 1 if keyword in str(classe).strip().lower() else 0

    df["Has_Staff"] = df["ClasseOsservatore"].apply(lambda c: has_classe(c, "staff"))
    df["Has_Responsabile"] = df["ClasseOsservatore"].apply(
        lambda c: has_classe(c, "respons")
    )
    df["Has_Scouting"] = df["ClasseOsservatore"].apply(lambda c: has_classe(c, "scout"))

    return df


uploaded = st.file_uploader(
    "Carica il CSV (Incrocio Segnalazioni Partite)", type=["csv"]
)
if uploaded is None:
    st.info("👆 Carica un file CSV per iniziare.")
    st.stop()

df = load_csv(uploaded)

# DEBUG temporaneo: scommenta per verificare le nuove colonne
# st.write(df[["ClasseOsservatore", "Has_Staff", "Has_Responsabile", "Has_Scouting"]].drop_duplicates())

# ------------------------------------------------------------------ KPI
add_markdown_divider()
tot = len(df)
n_segnalati = int(df["Segnalato_num"].sum())
n_nds = int(df["NDS"].sum())
n_partite = int(df.loc[df["Partita"].ne(""), "Partita"].nunique())
n_giocatori_segnalati = int(df["Giocatore_Segnalato"].nunique())
media = df["Voto_num"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Dataset", tot)
c2.metric("Partite osservate", n_partite)
c3.metric("Giocatori segnalati (distinti)", n_giocatori_segnalati)
c4.metric("Visti senza segnalazione (❌)", n_nds)
c5.metric("Voto medio", f"{media:.2f}" if pd.notna(media) else "—")


# ================================================== vista 1: alberatura ==
add_markdown_divider()
st_pivot_table(
    df,
    key="alberatura",
    rows=GRUPPI,
    values=[
        "Giocatore_Segnalato",
        "Voto_num",
        "Has_Staff",
        "Has_Responsabile",
        "Has_Scouting",
    ],
    aggregation={
        "Giocatore_Segnalato": "count_distinct",
        "Voto_num": "avg",
        "Has_Staff": "max",
        "Has_Responsabile": "max",
        "Has_Scouting": "max",
    },
    collapse_row_groups=True,
    row_layout="hierarchy",
    show_subtotals=True,
    values_axis="columns",
    number_format={"Giocatore_Segnalato": "0", "Voto_num": ".2f"},
    empty_cell_value="—",
    style="striped",
    column_config={
        "Giocatore_Segnalato": {
            "label": "Giocatori segnalati",
            "help": "Numero di giocatori distinti segnalati (Segnalato = True)",
            "width": "medium",
            "alignment": "center",
        },
        "Voto_num": {
            "label": "Voto medio",
            "help": "Media dei voti numerici (0.0 = segnalato senza giudizio, escluso)",
            "width": "medium",
            "alignment": "center",
        },
        "Has_Staff": {
            "label": "Staff",
            "help": "Almeno un osservatore Staff nel gruppo",
            "width": "small",
            "alignment": "center",
        },
        "Has_Responsabile": {
            "label": "Responsabile",
            "help": "Almeno un osservatore Responsabile nel gruppo",
            "width": "small",
            "alignment": "center",
        },
        "Has_Scouting": {
            "label": "Scouting",
            "help": "Almeno un osservatore Scouting nel gruppo",
            "width": "small",
            "alignment": "center",
        },
        "Nome": {"label": "Giocatore"},
    },
    filter_fields=[
        "Anno",
        "Societa",
        "Stato",
        "Osservatore",
        "ClasseOsservatore",
        "Partita",
    ],
    enable_drilldown=True,
    max_height=650,
    export_filename="incrocio_segnalazioni_alberatura",
)

add_markdown_divider()
page_nav()
