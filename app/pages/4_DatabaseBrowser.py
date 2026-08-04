import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = st.secrets.get("db_path", os.getenv("DB_PATH", "app.db"))
BROWSER_PASSWORD = st.secrets.get("browser_password", os.getenv("BROWSER_PASSWORD", ""))


def check_password() -> bool:
    if st.session_state.get("db_pwd_ok"):
        return True

    if not BROWSER_PASSWORD:
        st.error("Missing sqlite_browser_password secret/env var.")
        st.stop()

    pwd = st.text_input("Password", type="password")
    if st.button("Entra", type="primary"):
        if pwd == BROWSER_PASSWORD:
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


def get_columns(conn: sqlite3.Connection, table: str) -> list[dict]:
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)


def sanitize_table_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Invalid table name")
    return name


def export_db_copy(src_path: str) -> bytes:
    with open(src_path, "rb") as f:
        return f.read()


def write_table(conn: sqlite3.Connection, table: str, df: pd.DataFrame) -> None:
    cols = get_columns(conn, table)
    pk_cols = [c[1] for c in cols if c[5] == 1]
    if not pk_cols and "id" in df.columns:
        pk_cols = ["id"]
    if not pk_cols:
        raise ValueError(
            "No primary key found. Add an id column or a primary key to support updates."
        )

    table_quoted = f'"{table}"'
    existing = pd.read_sql_query(f"SELECT * FROM {table_quoted}", conn)
    existing = existing.reset_index(drop=True)
    edited = df.reset_index(drop=True)

    existing_keys = set()
    for _, row in existing.iterrows():
        existing_keys.add(tuple(row[pk] for pk in pk_cols))

    edited_keys = set()
    for _, row in edited.iterrows():
        edited_keys.add(tuple(row[pk] for pk in pk_cols))

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
                f"UPDATE {table_quoted} SET {set_clause} WHERE {where_clause}", params
            )
        else:
            insert_cols = list(edited.columns)
            placeholders = ", ".join(["?"] * len(insert_cols))
            cols_clause = ", ".join([f'"{c}"' for c in insert_cols])
            cur.execute(
                f"INSERT INTO {table_quoted} ({cols_clause}) VALUES ({placeholders})",
                [values[c] for c in insert_cols],
            )

    for _, row in existing.iterrows():
        key = tuple(row[pk] for pk in pk_cols)
        if key not in edited_keys:
            where_clause = " AND ".join([f'"{pk}"=?' for pk in pk_cols])
            cur.execute(
                f"DELETE FROM {table_quoted} WHERE {where_clause}",
                [row[pk] for pk in pk_cols],
            )

    conn.commit()


st.title("SQLite Browser")

if not check_password():
    st.stop()

if not Path(DB_PATH).exists():
    st.error(f"DB not found: {DB_PATH}")
    st.stop()

conn = get_conn(DB_PATH)

tables = list_tables(conn)
if not tables:
    st.warning("No tables found in database.")
    st.stop()

table = st.selectbox("Table", tables)

try:
    sanitize_table_name(table)
except ValueError:
    st.error("Invalid table name selected.")
    st.stop()

if "df_loaded" not in st.session_state or st.session_state.get("loaded_table") != table:
    st.session_state["df_loaded"] = read_table(conn, table)
    st.session_state["loaded_table"] = table

st.caption(f"DB: {DB_PATH}")
st.caption(f"Rows: {len(st.session_state['df_loaded'])}")

edited_df = st.data_editor(
    st.session_state["df_loaded"],
    num_rows="dynamic",
    use_container_width=True,
    key="table_editor",
)

col1, col2, col3 = st.columns(3)

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

with col3:
    db_bytes = export_db_copy(DB_PATH)
    st.download_button(
        "Export DB",
        data=db_bytes,
        file_name=Path(DB_PATH).name,
        mime="application/x-sqlite3",
    )

st.divider()
st.subheader("Preview")
st.dataframe(edited_df, use_container_width=True)

conn.close()
