import re

import pandas as pd
import streamlit as st

PAGE_TITLE = "Business Intelligence: Anagrafica Scouting"

HIDE_STREAMLIT_UI = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    div.block-container { padding-top: 0.5rem; }
</style>
"""

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title=PAGE_TITLE, page_icon="⚽", layout="wide")
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)


try:
    from streamlit_pivot import st_pivot_table
except ImportError:
    st.error(
        "Installa il componente: `pip install streamlit-pivot` (richiede Streamlit >= 1.51)"
    )
    st.stop()

GRUPPI = ["Anno", "Societa", "Stato", "Nome_Giocatore", "Osservatore"]


# ------------------------------------------------------------------ dati
def voto_numerico(voto) -> float | None:
    m = re.match(r"^\s*([0-9]+(?:[.,][0-9]+)?)", str(voto))
    return float(m.group(1).replace(",", ".")) if m else None


def esito(row) -> str:
    presenza = str(row["Presenza_In_Partita"])
    if "NON Segnalato" in presenza or "NDS" in presenza:
        return "❌"
    if voto_numerico(row["Voto"]) is not None:
        return str(row["Voto"]).strip()
    v = str(row["Voto"]).strip()
    return "—" if v in ("", "nan", "ND", "ND / Non Segnalato") else v


@st.cache_data(show_spinner=False)
def load_csv(buffer) -> pd.DataFrame:
    df = pd.read_csv(buffer, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.fillna("")
    df["Anno"] = df["Anno"].astype(str).str.strip()  # stringa: niente "2,014"
    df["Esito"] = df.apply(esito, axis=1)  # visibile nel drill-down
    df["Voto_num"] = df["Voto"].map(voto_numerico)
    df["NDS"] = df["Esito"].eq("❌").astype(int)  # 1 = visto senza segnalare
    return df


uploaded = st.file_uploader("Carica il CSV (Anagrafica Scouting)", type=["csv"])
if uploaded is None:
    st.info("👆 Carica un file CSV per iniziare.")
    st.stop()

df = load_csv(uploaded)

# ------------------------------------------------------------------ KPI
tot, n_voto, n_nds = len(df), int(df["Voto_num"].notna().sum()), int(df["NDS"].sum())
media = df["Voto_num"].mean()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Righe (osservazioni)", tot)
c2.metric("Con voto numerico", n_voto)
c3.metric("Viste senza segnalazione (❌)", n_nds)
c4.metric("Voto medio", f"{media:.2f}" if pd.notna(media) else "—")

tab1, tab2 = st.tabs(
    ["🌳 Alberatura collassabile", "🔀 Matrice giocatore × osservatore"]
)

# ================================================== vista 1: alberatura ==
with tab1:
    st.markdown(
        "Espandi i gruppi con i toggle **+/−** (o **Expand All / Collapse All** dal menu "
        "utility della toolbar). Ogni nodo gruppo mostra il subtotal: il **voto medio** "
        "della sottogerarchia."
    )
    st_pivot_table(
        df,
        key="alberatura",
        rows=GRUPPI,
        values=["Voto_num", "NDS"],
        aggregation={"Voto_num": "avg", "NDS": "max"},
        row_layout="hierarchy",  # colonna-albero indentata, breadcrumb in alto
        show_subtotals=True,
        values_axis="columns",
        number_format={"Voto_num": ".2f", "NDS": "0"},
        empty_cell_value="—",
        column_config={
            "Voto_num": {
                "label": "Voto medio",
                "help": "Media dei voti numerici",
                "width": "medium",
                "alignment": "center",
            },
            "NDS": {
                "label": "❌ Visto senza segnalare",
                "help": "1 = l'osservatore ha visto la partita ma non ha segnalato il giocatore",
                "width": "medium",
                "alignment": "center",
            },
            "Nome_Giocatore": {"label": "Giocatore"},
        },
        filter_fields=["Anno", "Societa", "Stato", "Osservatore"],
        enable_drilldown=True,
        max_height=650,
        export_filename="scouting_alberatura",
    )

# ================================================== vista 2: matrice =====
with tab2:
    st.markdown(
        "Ogni cella = **voto medio** dato da quell'osservatore a quel giocatore "
        "(attraverso le partite viste). Cell vuota = non l'ha mai osservato; "
        "il drill-down mostra se esiste una riga ❌. "
        "Da qui puoi anche trascinare un campo tra Righe e Colonne dalla toolbar."
    )
    st_pivot_table(
        df,
        key="matrice",
        rows=["Anno", "Societa", "Nome_Giocatore"],
        columns=["Osservatore"],
        values=["Voto_num", "NDS"],
        aggregation={"Voto_num": "avg", "NDS": "max"},
        row_layout="hierarchy",
        show_subtotals=["Anno"],  # subtotal per anno, niente rumore intermedio
        number_format={"Voto_num": ".2f", "NDS": "0"},
        empty_cell_value="",
        column_config={
            "Voto_num": {"label": "Voto medio"},
            "NDS": {"label": "❌ Visto senza segnalare"},
        },
        filter_fields=["Anno", "Societa", "Osservatore"],
        enable_drilldown=True,
        max_height=650,
        export_filename="scouting_matrice",
    )

st.markdown(
    "💡 **Suggerimenti**: dalla toolbar puoi cambiare aggregazione (es. `max` per vedere "
    "il voto più alto), trascinare `Osservatore` tra righe e colonne, e usare "
    "l'icona a schermo intero. Gli export Excel/CSV/TSV seguono il layout corrente, "
    "gerarchia e indentazioni incluse."
)
