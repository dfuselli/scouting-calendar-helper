import os
import re
import sqlite3

import pandas as pd
import streamlit as st
from common.data_handler import (
    add_matches_to_db,
    download_db,
    export_db,
)
from ui.common import add_markdown_divider
from ui.nav import page_nav

# ── Costanti ────────────────────────────────────────────────────────────────
PAGE_TITLE = "Database Browser"
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

browser_password = st.secrets.get("BROWSER_PASSWORD", os.getenv("BROWSER_PASSWORD", ""))


def check_password() -> bool:
    if st.session_state.get("db_pwd_ok"):
        return True

    if not browser_password:
        st.error("Missing BROWSER_PASSWORD secret/env var.")
        st.stop()

    pwd = st.text_input("Password", type="password")
    if st.button("Entra", type="primary"):
        if pwd == browser_password:
            st.session_state["db_pwd_ok"] = True
            st.rerun()
        else:
            st.error("Password errata")

    return False


def get_conn(db_path: str):
    return sqlite3.connect(db_path, check_same_thread=False)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def sanitize_table_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Invalid table name")
    return name


def read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)


def get_columns(conn: sqlite3.Connection, table: str):
    return conn.execute(f'PRAGMA table_info("{table}")').fetchall()


def export_db_copy(src_path: str) -> bytes:
    with open(src_path, "rb") as f:
        return f.read()


def write_table(conn: sqlite3.Connection, table: str, df: pd.DataFrame) -> None:
    cols = get_columns(conn, table)
    pk_cols = [c[1] for c in cols if c[5] == 1]
    if not pk_cols and "id" in df.columns:
        pk_cols = ["id"]
    if not pk_cols:
        raise ValueError("No primary key found. Add an id column or primary key.")

    existing = read_table(conn, table).reset_index(drop=True)
    edited = df.reset_index(drop=True)

    existing_keys = {tuple(row[pk] for pk in pk_cols) for _, row in existing.iterrows()}
    edited_keys = {tuple(row[pk] for pk in pk_cols) for _, row in edited.iterrows()}

    cur = conn.cursor()

    for _, row in edited.iterrows():
        key = tuple(row[pk] for pk in pk_cols)
        values = row.to_dict()
        if key in existing_keys:
            set_cols = [c for c in edited.columns if c not in pk_cols]
            set_clause = ", ".join([f'"{c}"=?' for c in set_cols])
            where_clause = " AND ".join([f'"{pk}"=?' for pk in pk_cols])
            params = [values[c] for c in set_cols] + [values[pk] for pk in pk_cols]
            cur.execute(
                f'UPDATE "{table}" SET {set_clause} WHERE {where_clause}', params
            )
        else:
            insert_cols = list(edited.columns)
            cols_clause = ", ".join([f'"{c}"' for c in insert_cols])
            placeholders = ", ".join(["?"] * len(insert_cols))
            cur.execute(
                f'INSERT INTO "{table}" ({cols_clause}) VALUES ({placeholders})',
                [values[c] for c in insert_cols],
            )

    for _, row in existing.iterrows():
        key = tuple(row[pk] for pk in pk_cols)
        if key not in edited_keys:
            where_clause = " AND ".join([f'"{pk}"=?' for pk in pk_cols])
            cur.execute(
                f'DELETE FROM "{table}" WHERE {where_clause}',
                [row[pk] for pk in pk_cols],
            )

    conn.commit()


# ── Export / Import ──────────────────────────────────────────────────────────
def _render_export_section() -> None:
    with st.expander("📤 Esporta"):
        export_db("📤 Download DB su PC → Update Manuale su GDrive")


def _render_import_section() -> None:
    with st.expander("⬆️ Importa"):
        col1, _col2 = st.columns([30, 70])

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

if not check_password():
    st.stop()


def main() -> None:

    db_path = download_db()
    conn = get_conn(db_path)

    # tables = list_tables(conn)
    # if not tables:
    #     st.warning("No tables found in database.")
    #     st.stop()

    # table = st.selectbox("Table", tables)

    # try:
    #     sanitize_table_name(table)
    # except ValueError:
    #     st.error("Invalid table name selected.")
    #     st.stop()

    table = "matches"  # Hardcoded for now; can be made selectable later

    if (
        "df_loaded" not in st.session_state
        or st.session_state.get("loaded_table") != table
    ):
        st.session_state["df_loaded"] = read_table(conn, table)
        st.session_state["loaded_table"] = table

    st.caption(f"Rows: {len(st.session_state['df_loaded'])}")

    df = st.session_state["df_loaded"].copy()

    col1, col2 = st.columns(2)

    with col1:
        team_query = st.text_input("Filtra casa/ospite")

    with col2:
        categorie = sorted(df["Categoria"].dropna().astype(str).unique())
        categorie_sel = st.multiselect("Categoria", options=categorie, default=[])

    if team_query:
        mask_team = df["Casa"].astype(str).str.contains(
            team_query, case=False, na=False
        ) | df["Ospite"].astype(str).str.contains(team_query, case=False, na=False)
        df = df[mask_team]

    if categorie_sel:
        df = df[df["Categoria"].astype(str).isin(categorie_sel)]

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        key="table_editor",
    )

    col1, col2, _col3 = st.columns(3)

    with col1:
        if st.button("Reload from DB"):
            st.session_state["df_loaded"] = read_table(conn, table)
            st.rerun()

    with col2:
        if st.button("Save changes to DB", type="primary"):
            try:
                write_table(conn, table, edited_df)
                st.session_state["df_loaded"] = read_table(conn, table)
                st.success("Changes saved.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Save failed: {e}")

    # Export / Import
    _render_export_section()
    _render_import_section()

    add_markdown_divider()

    conn.close()


try:
    main()
except Exception as e:
    st.error(f"Errore nell'applicazione: {e}")
    raise  # utile in sviluppo; rimuovi in produzione

page_nav()
