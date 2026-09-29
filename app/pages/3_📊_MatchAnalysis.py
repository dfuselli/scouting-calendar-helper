import json
import re

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from map.constants import CENTER_GPS_COORD
from map.data_engine import load_geojson_data
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


def reports_theme():
    return {
        "config": {
            # Sfondo SOLO del grafico Altair
            "background": "#FFFFFF",
            # Assi
            "axis": {
                "labelColor": "#000000",
                "titleColor": "#000000",
                "domainColor": "#000000",
                "tickColor": "#000000",
                "gridColor": "#E5E5E5",
                "gridOpacity": 1,
            },
            # Legende
            "legend": {
                "labelColor": "#000000",
                "titleColor": "#000000",
            },
            # Titoli
            "title": {
                "color": "#000000",
            },
            # Rimuove il bordo del grafico
            "view": {
                "stroke": None,
            },
            # Palette Villa Almé
            "range": {
                "category": [
                    "#D0372D",  # rosso
                    "#F7BE00",  # giallo
                    "#333333",
                ]
            },
        }
    }


alt.themes.register("reports_theme", reports_theme)
alt.themes.enable("reports_theme")


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
    # df["Comune"] = df["Comune"].astype(str).str.strip()
    df["Comune"] = ""

    df["Data_Partita_dt"] = pd.to_datetime(
        df["Data_Partita"], format="%d/%m/%Y", errors="coerce"
    )

    df["Esito"] = df.apply(esito, axis=1)
    df["Voto_num"] = df["Voto"].map(voto_numerico)
    df["NDS"] = (~df["Segnalato"].str.strip().str.lower().eq("true")).astype(int)
    df["Segnalato_num"] = df["NDS"].eq(0).astype(int)
    df["Giocatore_Segnalato"] = df["Nome"].where(df["Segnalato_num"].eq(1))

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


tab_pivot, tab_grafici, tab_mappe = st.tabs(["Pivot", "Grafici", "Mappe"])

with tab_pivot:
    add_markdown_divider()
    tot = len(df)
    n_segnalati = int(df["Segnalato_num"].sum())
    n_nds = int(df["NDS"].sum())
    n_partite = len(
        df.loc[df["Partita"].ne(""), ["Partita", "Data_Partita"]].drop_duplicates()
    )
    n_giocatori_segnalati = int(df["Giocatore_Segnalato"].nunique())
    media = df["Voto_num"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Dataset", tot)
    c2.metric("Partite osservate", n_partite)
    c3.metric("Giocatori segnalati (distinti)", n_giocatori_segnalati)
    c4.metric("Visti senza segnalazione (❌)", n_nds)
    c5.metric("Voto medio", f"{media:.2f}" if pd.notna(media) else "—")

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

with tab_grafici:
    import altair as alt

    classi = ["Responsabile", "Scouting", "Staff", "Segnalazione Esterna"]
    colori = ["#F2C94C", "#E53935", "#808080", "#F28C28"]

    def classe_grafico(valore: str) -> str | None:
        classe = str(valore).strip().lower()
        if "respons" in classe:
            return "Responsabile"
        if "scout" in classe:
            return "Scouting"
        if "esterna" in classe:
            return "Segnalazione Esterna"
        return "Staff"

    def render_grafici(df_filtrato: pd.DataFrame) -> None:
        partite = df_filtrato.loc[
            df_filtrato["Partita"].ne("") & df_filtrato["Osservatore"].ne(""),
            ["Anno", "Partita", "Osservatore", "ClasseOsservatore"],
        ].drop_duplicates()
        partite["Classe"] = partite["ClasseOsservatore"].map(classe_grafico)

        segnalati = df_filtrato.loc[
            df_filtrato["Giocatore_Segnalato"].notna()
            & df_filtrato["Giocatore_Segnalato"].ne("")
            & df_filtrato["Osservatore"].ne(""),
            ["Anno", "Giocatore_Segnalato", "Osservatore", "ClasseOsservatore"],
        ].drop_duplicates()
        segnalati["Classe"] = segnalati["ClasseOsservatore"].map(classe_grafico)

        if partite.empty and segnalati.empty:
            st.info("Nessun dato disponibile in questo intervallo.")
            return

        scala_classi = alt.Scale(domain=classi, range=colori)

        def ordine_osservatori_per_classe(dati: pd.DataFrame) -> list[str]:
            ordinati = dati.copy()
            ordinati["Ordine_classe"] = pd.Categorical(
                ordinati["Classe"], categories=classi, ordered=True
            )
            return (
                ordinati.sort_values(["Ordine_classe", "Osservatore"])["Osservatore"]
                .drop_duplicates()
                .tolist()
            )

        def barre_orizzontali(
            dati: pd.DataFrame,
            y_col: str,
            y_ordine: list[str],
            valore: str,
            titolo_valore: str,
            altezza: int,
        ) -> alt.Chart:
            return (
                alt.Chart(dati)
                .mark_bar()
                .encode(
                    x=alt.X(
                        f"{valore}:Q",
                        title=titolo_valore,
                        axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                    y=alt.Y(f"{y_col}:N", sort=y_ordine),
                    color=alt.Color(
                        "Classe:N",
                        scale=scala_classi,
                        legend=alt.Legend(title="Classe osservatore"),
                    ),
                    order=alt.Order("Classe:N", sort="descending"),
                    tooltip=[
                        alt.Tooltip(f"{y_col}:N"),
                        alt.Tooltip("Classe:N", title="Classe"),
                        alt.Tooltip(f"{valore}:Q", title=titolo_valore),
                    ],
                )
                .properties(height=altezza)
            )

        if not partite.empty:
            st.markdown("**Partite visionate per osservatore e classe**")
            partite_oss = (
                partite.groupby(["Osservatore", "Classe"])["Partita"]
                .nunique()
                .reset_index(name="Partite visionate")
            )
            st.altair_chart(
                barre_orizzontali(
                    partite_oss,
                    y_col="Osservatore",
                    y_ordine=ordine_osservatori_per_classe(partite_oss),
                    valore="Partite visionate",
                    titolo_valore="Numero di partite visionate",
                    altezza=max(300, 32 * partite_oss["Osservatore"].nunique()),
                ),
                width="stretch",
            )

            st.markdown("**Partite visionate per annata e classe osservatore**")
            partite_anno = (
                partite.loc[partite["Anno"].ne("")]
                .groupby(["Anno", "Classe"])["Partita"]
                .nunique()
                .reset_index(name="Partite visionate")
            )
            if not partite_anno.empty:
                ordine_anni = sorted(partite_anno["Anno"].unique().tolist())
                st.altair_chart(
                    barre_orizzontali(
                        partite_anno,
                        y_col="Anno",
                        y_ordine=ordine_anni,
                        valore="Partite visionate",
                        titolo_valore="Numero di partite visionate",
                        altezza=max(220, 40 * len(ordine_anni)),
                    ),
                    width="stretch",
                )

        if segnalati.empty:
            st.info("Nessun giocatore segnalato in questo intervallo.")
            return

        st.markdown("**Giocatori segnalati per osservatore e classe**")
        segn_oss = (
            segnalati.groupby(["Osservatore", "Classe"])["Giocatore_Segnalato"]
            .nunique()
            .reset_index(name="Giocatori segnalati")
        )
        st.altair_chart(
            barre_orizzontali(
                segn_oss,
                y_col="Osservatore",
                y_ordine=ordine_osservatori_per_classe(segn_oss),
                valore="Giocatori segnalati",
                titolo_valore="Numero di giocatori segnalati (distinti)",
                altezza=max(300, 32 * segn_oss["Osservatore"].nunique()),
            ),
            width="stretch",
        )

        st.markdown("**Giocatori segnalati per annata e classe osservatore**")
        segn_anno = (
            segnalati.loc[segnalati["Anno"].ne("")]
            .groupby(["Anno", "Classe"])["Giocatore_Segnalato"]
            .nunique()
            .reset_index(name="Giocatori segnalati")
        )
        if not segn_anno.empty:
            ordine_anni = sorted(segn_anno["Anno"].unique().tolist())
            st.altair_chart(
                barre_orizzontali(
                    segn_anno,
                    y_col="Anno",
                    y_ordine=ordine_anni,
                    valore="Giocatori segnalati",
                    titolo_valore="Numero di giocatori segnalati (distinti)",
                    altezza=max(220, 40 * len(ordine_anni)),
                ),
                width="stretch",
            )
        stati = [
            "Segnalato",
            "Da rivedere",
            "Da prendere",
            "Da provare",
            "Negativo",
            "Da seguire",
            "Preso",
            "Scartato",
            "Da seguire con attenzione",
        ]
        colori_stati = [
            "#4E79A7",
            "#F28E2B",
            "#59A14F",
            "#E15759",
            "#9C755F",
            "#76B7B2",
            "#B07AA1",
            "#BAB0AC",
            "#EDC948",
        ]
        scala_stati = alt.Scale(domain=stati, range=colori_stati)

        dati_stati = df_filtrato.loc[
            df_filtrato["Segnalato_num"].eq(1)
            & df_filtrato["Nome"].ne("")
            & df_filtrato["Stato"].isin(stati),
            ["Anno", "Nome", "Osservatore", "Stato"],
        ].drop_duplicates()

        if dati_stati.empty:
            st.info("Nessun giocatore segnalato con uno degli stati previsti.")
            return

        st.markdown("**Giocatori segnalati per osservatore e stato**")
        stati_oss = (
            dati_stati.loc[dati_stati["Osservatore"].ne("")]
            .groupby(["Osservatore", "Stato"])["Nome"]
            .nunique()
            .reset_index(name="Giocatori segnalati")
        )
        if not stati_oss.empty:
            ordine_osservatori = (
                stati_oss.groupby("Osservatore")["Giocatori segnalati"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            grafico_stati_oss = (
                alt.Chart(stati_oss)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Giocatori segnalati:Q",
                        title="Numero di giocatori segnalati (distinti)",
                        axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                    y=alt.Y(
                        "Osservatore:N",
                        title="Osservatore",
                        sort=ordine_osservatori,
                    ),
                    color=alt.Color(
                        "Stato:N",
                        scale=scala_stati,
                        legend=alt.Legend(title="Stato"),
                    ),
                    tooltip=[
                        alt.Tooltip("Osservatore:N"),
                        alt.Tooltip("Stato:N"),
                        alt.Tooltip("Giocatori segnalati:Q"),
                    ],
                )
                .properties(height=max(300, 32 * stati_oss["Osservatore"].nunique()))
            )
            st.altair_chart(grafico_stati_oss, width="stretch")

        st.markdown("**Giocatori segnalati per annata e stato**")
        stati_anno = (
            dati_stati.loc[dati_stati["Anno"].ne("")]
            .groupby(["Anno", "Stato"])["Nome"]
            .nunique()
            .reset_index(name="Giocatori segnalati")
        )
        if not stati_anno.empty:
            ordine_anni = sorted(stati_anno["Anno"].unique().tolist())
            grafico_stati_anno = (
                alt.Chart(stati_anno)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Giocatori segnalati:Q",
                        title="Numero di giocatori segnalati (distinti)",
                        axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                    y=alt.Y("Anno:N", title="Annata", sort=ordine_anni),
                    color=alt.Color(
                        "Stato:N",
                        scale=scala_stati,
                        legend=alt.Legend(title="Stato"),
                    ),
                    tooltip=[
                        alt.Tooltip("Anno:N"),
                        alt.Tooltip("Stato:N"),
                        alt.Tooltip("Giocatori segnalati:Q"),
                    ],
                )
                .properties(height=max(220, 40 * len(ordine_anni)))
            )
            st.altair_chart(grafico_stati_anno, width="stretch")

    OPZIONI_SEZIONI = {
        "Tutto": (None, None),
        "Agonistica": ("2010", "2013"),
        "Settore di Base": ("2014", "2017"),
        "Scuola Calcio": ("2018", None),
    }

    sezione = st.radio(
        "Settore",
        options=list(OPZIONI_SEZIONI.keys()),
        horizontal=True,
    )

    anno_da, anno_a = OPZIONI_SEZIONI[sezione]
    mask = pd.Series(True, index=df.index)
    if anno_da is not None:
        mask &= df["Anno"].ge(anno_da)
    if anno_a is not None:
        mask &= df["Anno"].le(anno_a)

    render_grafici(df.loc[mask])

with tab_mappe:

    @st.cache_data(ttl=60 * 60, show_spinner=False)
    def load_comuni_geojson() -> dict:
        gdf = load_geojson_data()
        return json.loads(gdf.to_json())

    def normalizza_comune(series: pd.Series) -> pd.Series:
        return (
            series.astype("string")
            .str.replace("\u200b", "", regex=False)
            .str.replace("\u00a0", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.casefold()
        )

    annata_mappa = st.selectbox(
        "Annata",
        options=list(range(2010, 2026)),
        index=0,
        key="annata_mappa",
    )

    try:
        geojson = load_comuni_geojson()
    except Exception as e:  # noqa: BLE001
        st.error(f"Errore durante il caricamento del GeoJSON: {e}")
        st.stop()

    nomi_geo = [feature["properties"]["name"] for feature in geojson["features"]]
    comuni_geo = pd.DataFrame({"Comune_geo": nomi_geo})
    comuni_geo["Comune_key"] = normalizza_comune(comuni_geo["Comune_geo"])

    segnalazioni = df.loc[
        df["Anno"].eq(str(annata_mappa))
        & df["Segnalato_num"].eq(1)
        & df["Comune"].ne("")
        & df["Nome"].ne(""),
        ["Comune", "Nome"],
    ].copy()

    segnalazioni["Comune_key"] = normalizza_comune(segnalazioni["Comune"])

    # Elenco dei nomi distinti per comune, senza righe duplicate nel tooltip.
    nomi_per_comune = (
        segnalazioni.groupby("Comune_key")["Nome"]
        .apply(lambda nomi: "<br>".join(f"• {nome}" for nome in sorted(set(nomi))))
        .rename("Nomi")
    )

    comuni_mappa = comuni_geo.copy()
    comuni_mappa["Segnalazioni"] = (
        segnalazioni.groupby("Comune_key")
        .size()
        .reindex(comuni_mappa["Comune_key"], fill_value=0)
        .to_numpy()
    )
    comuni_mappa["Nomi"] = (
        comuni_mappa["Comune_key"].map(nomi_per_comune).fillna("Nessuna segnalazione")
    )

    # Mappa principale: grigio senza segnalazioni, verde con segnalazioni.
    comuni_mappa["Con segnalazioni"] = comuni_mappa["Segnalazioni"].gt(0).astype(int)

    fig = go.Figure(
        go.Choroplethmap(
            geojson=geojson,
            locations=comuni_mappa["Comune_geo"],
            featureidkey="properties.name",
            z=comuni_mappa["Con segnalazioni"],
            customdata=comuni_mappa[["Segnalazioni", "Nomi"]].to_numpy(),
            colorscale=[
                [0.0, "#D3D3D3"],
                [0.499, "#D3D3D3"],
                [0.5, "#005723"],
                [1.0, "#005723"],
            ],
            zmin=0,
            zmax=1,
            showscale=False,
            marker_opacity=0.65,
            marker_line_width=1,
            marker_line_color="rgba(0,0,0,0.55)",
            hovertemplate=(
                "<b>%{location}</b>"
                "<br>Segnalazioni: %{customdata[0]}"
                "<br>%{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    # Secondo trace: Villa d'Almè sempre gialla, anche senza segnalazioni.
    villa = comuni_mappa.loc[comuni_mappa["Comune_key"].eq("villa d'alme'")]

    if not villa.empty:
        fig.add_trace(
            go.Choroplethmap(
                geojson=geojson,
                locations=villa["Comune_geo"],
                featureidkey="properties.name",
                z=[1] * len(villa),
                customdata=villa[["Segnalazioni", "Nomi"]].to_numpy(),
                colorscale=[[0, "#FFD700"], [1, "#FFD700"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_opacity=0.65,
                marker_line_width=1,
                marker_line_color="rgba(0,0,0,0.55)",
                hovertemplate=(
                    "<b>%{location}</b>"
                    "<br>Segnalazioni: %{customdata[0]}"
                    "<br>%{customdata[1]}"
                    "<extra></extra>"
                ),
                name="Villa d'Almè",
            )
        )
    else:
        st.warning("Villa d'Almè non trovata nei nomi del GeoJSON.")

    fig.update_layout(
        map={
            "style": "open-street-map",
            "zoom": 8.5,
            "center": {
                "lat": CENTER_GPS_COORD[0],
                "lon": CENTER_GPS_COORD[1],
            },
        },
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )

    st.plotly_chart(fig, width="stretch")

add_markdown_divider()
page_nav()
