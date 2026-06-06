# map_page.py
import json

import pandas as pd
import streamlit as st
from common.data_handler import (
    add_matches_to_db,
    aggregate_by_comune,
    cleanup_calendar_data,
    export_db,
    load_calendar_data_from_db,
)
from map.data_engine import load_geojson_data
from map.map_factory import create_map
from ui.nav import page_nav

# ── Costanti ────────────────────────────────────────────────────────────────
PAGE_TITLE = "Mappa Partite"
LAYOUT_MAP = 55
LAYOUT_TABLE = 45
FILTER_COLS = [5, 4, 5, 13]

HIDE_STREAMLIT_UI = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    div.block-container { padding-top: 0.5rem; }
</style>
"""

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)


# ── Caching dati ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60 * 60)  # 1 ora
def _load_geojson() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carica e normalizza i dati GeoJSON. Cache per 1 ora."""
    gdf = load_geojson_data()
    geojson = json.loads(gdf.to_json())

    comuni = pd.Series(
        [f["properties"]["name"] for f in geojson["features"]], name="Comune"
    )
    df_geo = comuni.to_frame()
    df_geo["Comune_casefold"] = _normalize_comune(df_geo["Comune"])

    return gdf, df_geo


@st.cache_data(ttl=60 * 60)
def _load_calendar() -> pd.DataFrame:
    """Carica il calendario dal database e lo pulisce. Cache per 1 hora."""
    df_cal = load_calendar_data_from_db(filter_next_7_days=False)
    return cleanup_calendar_data(df_cal)


def _normalize_comune(series: pd.Series) -> pd.Series:
    """Normalizza nomi di comuni per matching case-insensitive robusto."""
    return (
        series.astype("string")
        .str.replace("\u200b", "", regex=False)  # ZWSP
        .str.replace("\u00a0", " ", regex=False)  # NBSP → spazio
        .str.replace(r"\s+", " ", regex=True)  # comprime whitespace
        .str.strip()
        .str.casefold()
    )


# ── Filtri ───────────────────────────────────────────────────────────────────
def _build_filter_options(df: pd.DataFrame) -> dict[str, list]:
    """Costruisce le opzioni per i multiselect dai dati puliti."""
    comuni = (
        df.dropna(subset=["Comune_casefold"])
        .sort_values(["Comune_casefold", "Comune"])
        .drop_duplicates(subset=["Comune_casefold"], keep="first")["Comune"]
        .tolist()
    )

    cat = (
        df["Categoria"]
        .dropna()
        .astype("string")
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    squadra = (
        df["Casa"].dropna().astype("string").drop_duplicates().sort_values().tolist()
    )

    return {"comuni": comuni, "categoria": cat, "squadra": squadra}


def _apply_filters(
    df: pd.DataFrame, comuni: list, cat: list, squadra: list
) -> pd.DataFrame:
    """Applica i filtri al DataFrame. Puro, nessun effetto collaterale."""
    mask = pd.Series(True, index=df.index)

    if comuni:
        mask &= df["Comune"].astype(str).isin(comuni)
    if cat:
        mask &= df["Categoria"].astype(str).isin(cat)
    if squadra:
        mask &= df["Casa"].astype(str).isin(squadra)

    return df[mask]


# ──  UI ──────────────────────────────────────────────────────────────
def _render_filter_panel(options: dict) -> tuple[list, list, list]:
    """Renderizza i filtri. Reruns indipendente dal resto della pagina."""
    col1, col2, col3, _ = st.columns(FILTER_COLS, vertical_alignment="bottom")

    with col1:
        comuni_sel = st.multiselect("Comune", options=options["comuni"], default=[])

    with col2:
        cat_sel = st.multiselect("Categoria", options=options["categoria"], default=[])

    with col3:
        squadra_sel = st.multiselect("Squadra", options=options["squadra"], default=[])

    return comuni_sel, cat_sel, squadra_sel


def _render_map(gdf: pd.DataFrame, df_agg: pd.DataFrame) -> None:
    """Renderizza la mappa. Reruns indipendente dai filtri nella tabella."""
    col1, col2 = st.columns([LAYOUT_MAP, LAYOUT_TABLE])

    with col1:
        try:
            fig = create_map(gdf, df_agg)
            st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.error(f"Errore durante la creazione della mappa: {e}")

    with col2:
        pass
        # st.dataframe(
        #     df_agg.rename(columns={"Casa": "Squadra"})
        #     .loc[:, ["Squadra", "Categoria", "Comune"]]
        #     .sort_values("Squadra"),
        #     width="stretch",
        #     hide_index=True,
        # )


# ── Export / Import ──────────────────────────────────────────────────────────
def _render_export_section() -> None:
    with st.expander("📤 Esporta"):
        export_db("📤 Download DB su PC → Update Manuale su GDrive")


def _render_import_section() -> None:
    with st.expander("⬆️ Importa"):
        col1, col2 = st.columns([30, 70])

        with col1:
            uploaded_file = st.file_uploader(" ", type=["xlsx"])

        if uploaded_file is None:
            return

        df_excel = pd.read_excel(uploaded_file, engine="openpyxl")
        df_useful = df_excel.iloc[:, :13]

        col_btn, _ = st.columns([30, 70])
        with col_btn:
            if st.button(f"Importa in database {len(df_useful)} rows"):
                add_matches_to_db(df_useful)
                st.rerun()

        st.dataframe(
            df_useful.head(),
            width="stretch",
            hide_index=True,
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    # Caricamento dati (cacheato)
    try:
        gdf, df_geo = _load_geojson()
    except Exception as e:
        st.error(f"Errore durante il caricamento del file GeoJSON: {e}")
        return

    try:
        df_cleaned = _load_calendar()
    except Exception as e:
        st.error(f"Errore durante il caricamento del calendario: {e}")
        return

    if df_cleaned.empty:
        st.warning("Nessun dato disponibile nel calendario.")
        return

    # Opzioni filtri
    options = _build_filter_options(df_cleaned)

    # Filtri interattivi
    comuni_sel, cat_sel, squadra_sel = _render_filter_panel(options)

    # Applicazione filtri
    df_view = _apply_filters(df_cleaned, comuni_sel, cat_sel, squadra_sel)
    df_agg = aggregate_by_comune(df_view, df_geo)

    # Mappa e tabella
    _render_map(gdf, df_agg)

    # Export / Import
    _render_export_section()
    _render_import_section()


try:
    main()
except Exception as e:
    st.error(f"Errore nell'applicazione: {e}")
    raise

page_nav()
