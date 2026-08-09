import os
import sqlite3

import pandas as pd
import streamlit as st
from common.data_handler import download_db
from ui.common import add_markdown_divider
from ui.nav import page_nav

# =============================================================================
# COSTANTI
# =============================================================================

PAGE_TITLE = "Database Browser"
TABLE_NAME = "matches"

HIDE_STREAMLIT_UI = """
"""


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
)

st.markdown(
    HIDE_STREAMLIT_UI,
    unsafe_allow_html=True,
)


# =============================================================================
# PASSWORD
# =============================================================================

browser_password = st.secrets.get(
    "BROWSER_PASSWORD",
    os.getenv("BROWSER_PASSWORD", ""),
)


def check_password() -> bool:
    if st.session_state.get("db_pwd_ok"):
        return True

    if not browser_password:
        st.error("Missing BROWSER_PASSWORD secret/env var.")
        st.stop()

    pwd = st.text_input(
        "Password",
        type="password",
    )

    if st.button(
        "Entra",
        type="primary",
    ):
        if pwd == browser_password:
            st.session_state["db_pwd_ok"] = True
            st.rerun()
        else:
            st.error("Password errata")

    return False


# =============================================================================
# SQLITE HELPERS
# =============================================================================


def get_conn(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(
        db_path,
        check_same_thread=False,
    )


def quote_identifier(name: str) -> str:
    """
    Quota correttamente un identificatore SQLite.

    Permette anche nomi di colonne come:
        A/R
        Data partita
        Nome-Team
        ecc.

    Le virgolette doppie eventualmente presenti nel nome
    vengono raddoppiate secondo la sintassi SQLite.
    """

    if not isinstance(name, str) or not name:
        raise ValueError("Invalid SQLite identifier")

    return '"' + name.replace('"', '""') + '"'


def read_table(
    conn: sqlite3.Connection,
    table: str,
) -> pd.DataFrame:
    table_sql = quote_identifier(table)

    return pd.read_sql_query(
        f"SELECT * FROM {table_sql}",
        conn,
    )


def get_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[tuple]:
    """
    Restituisce il risultato di PRAGMA table_info().

    Ogni riga contiene:
    cid, name, type, notnull, default_value, pk
    """

    table_sql = quote_identifier(table)

    return conn.execute(f"PRAGMA table_info({table_sql})").fetchall()


def get_primary_key(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:

    columns = get_columns(
        conn,
        table,
    )

    pk_columns = [column[1] for column in columns if column[5] > 0]

    if not pk_columns:
        raise ValueError(f"La tabella '{table}' non ha una primary key.")

    return pk_columns


def get_db_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:

    return [
        column[1]
        for column in get_columns(
            conn,
            table,
        )
    ]


# =============================================================================
# VALUE HELPERS
# =============================================================================


def normalize_sql_value(value):
    """
    Converte NaN/NA pandas in None,
    che SQLite salva come NULL.
    """

    if pd.isna(value):
        return None

    return value


def values_equal(a, b) -> bool:
    """
    Confronto robusto tra valori pandas/SQLite.
    """

    a_is_na = pd.isna(a)
    b_is_na = pd.isna(b)

    if a_is_na and b_is_na:
        return True

    if a_is_na or b_is_na:
        return False

    return a == b


# =============================================================================
# SAVE
# =============================================================================


def save_table_changes(
    conn: sqlite3.Connection,
    table: str,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
) -> dict:
    """
    Salva:

    - UPDATE delle righe esistenti modificate
    - INSERT delle nuove righe
    - DELETE delle righe eliminate

    IMPORTANTE:

    original_df ed edited_df rappresentano solo le righe attualmente
    visualizzate dal filtro.

    Le righe nascoste dai filtri NON vengono né aggiornate né cancellate.
    """

    pk_columns = get_primary_key(
        conn,
        table,
    )

    # Per questo browser assumiamo una PK singola chiamata id.
    if pk_columns != ["id"]:
        raise ValueError(
            "Il Database Browser richiede una primary key singola chiamata 'id'."
        )

    if "id" not in original_df.columns:
        raise ValueError("La colonna 'id' non è presente nei dati originali.")

    if "id" not in edited_df.columns:
        raise ValueError("La colonna 'id' non è presente nei dati modificati.")

    original_df = original_df.reset_index(drop=True).copy()

    edited_df = edited_df.reset_index(drop=True).copy()

    db_columns = get_db_columns(
        conn,
        table,
    )

    table_sql = quote_identifier(table)

    cursor = conn.cursor()

    updated_count = 0
    inserted_count = 0
    deleted_count = 0

    try:
        # =====================================================================
        # ID ORIGINALI
        # =====================================================================

        original_ids = {int(value) for value in original_df["id"] if pd.notna(value)}

        edited_ids = {int(value) for value in edited_df["id"] if pd.notna(value)}

        # =====================================================================
        # DELETE
        # =====================================================================

        deleted_ids = original_ids - edited_ids

        for row_id in deleted_ids:
            cursor.execute(
                f"""
                DELETE FROM {table_sql}
                WHERE "id" = ?
                """,
                (row_id,),
            )

            deleted_count += cursor.rowcount

        # =====================================================================
        # UPDATE
        # =====================================================================

        update_columns = [
            column
            for column in db_columns
            if column != "id" and column in edited_df.columns
        ]

        if update_columns:
            set_clause = ", ".join(
                f"{quote_identifier(column)} = ?" for column in update_columns
            )

            update_sql = f"""
                UPDATE {table_sql}
                SET {set_clause}
                WHERE "id" = ?
            """

            original_existing = (
                original_df[original_df["id"].notna()].copy().set_index("id")
            )

            edited_existing = edited_df[edited_df["id"].notna()].copy()

            for _, edited_row in edited_existing.iterrows():
                row_id = int(edited_row["id"])

                if row_id not in original_existing.index:
                    continue

                original_row = original_existing.loc[row_id]

                changed = any(
                    not values_equal(
                        original_row[column],
                        edited_row[column],
                    )
                    for column in update_columns
                )

                if not changed:
                    continue

                params = [
                    normalize_sql_value(edited_row[column]) for column in update_columns
                ]

                params.append(row_id)

                cursor.execute(
                    update_sql,
                    params,
                )

                updated_count += cursor.rowcount

        # =====================================================================
        # INSERT
        # =====================================================================

        # Le nuove righe hanno id vuoto/NaN.
        #
        # NON inseriamo la colonna id.
        # Sarà SQLite a generarla automaticamente.

        new_rows = edited_df[edited_df["id"].isna()].copy()

        insert_columns = [
            column
            for column in db_columns
            if column != "id" and column in new_rows.columns
        ]

        if not new_rows.empty:
            if not insert_columns:
                raise ValueError("Nessuna colonna disponibile per il nuovo record.")

            columns_sql = ", ".join(
                quote_identifier(column) for column in insert_columns
            )

            placeholders = ", ".join("?" for _ in insert_columns)

            insert_sql = f"""
                INSERT INTO {table_sql}
                ({columns_sql})
                VALUES ({placeholders})
            """

            for _, new_row in new_rows.iterrows():
                params = [
                    normalize_sql_value(new_row[column]) for column in insert_columns
                ]

                cursor.execute(
                    insert_sql,
                    params,
                )

                inserted_count += 1

        # =====================================================================
        # COMMIT
        # =====================================================================

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return {
        "updated": updated_count,
        "inserted": inserted_count,
        "deleted": deleted_count,
    }


# =============================================================================
# RESET
# =============================================================================


def request_db_reset() -> None:
    """
    Callback del bottone Reset.

    Il vero reset viene eseguito nel ciclo successivo,
    prima della creazione dei widget.
    """

    st.session_state["reset_db_requested"] = True


def apply_db_reset(
    conn: sqlite3.Connection,
    table: str,
) -> None:
    """
    Ricarica completamente la tabella dal DB.

    Inoltre incrementa editor_version.

    Questo è importante perché st.data_editor è un widget
    con un proprio stato. Cambiando la key costringiamo
    Streamlit a creare un editor completamente nuovo.
    """

    st.session_state["df_loaded"] = read_table(
        conn,
        table,
    )

    st.session_state["loaded_table"] = table

    # Reset filtri
    st.session_state["team_query"] = ""
    st.session_state["categorie_sel"] = []

    # Forza un nuovo data_editor
    st.session_state["editor_version"] = (
        st.session_state.get(
            "editor_version",
            0,
        )
        + 1
    )


# =============================================================================
# EXPORT
# =============================================================================


def export_database(
    conn: sqlite3.Connection,
) -> bytes:
    """
    Crea una copia consistente del database nello stato attuale
    utilizzando SQLite backup API.

    È preferibile alla lettura diretta del file perché funziona
    correttamente anche quando SQLite sta utilizzando WAL.
    """

    backup_conn = sqlite3.connect(":memory:")

    try:
        conn.commit()

        conn.backup(backup_conn)

        # Recupera il database SQLite dalla connection in memoria
        # creando un file temporaneo in memoria tramite serialize().
        db_bytes = backup_conn.serialize()

        return db_bytes

    finally:
        backup_conn.close()


def render_export_section(
    conn: sqlite3.Connection,
) -> None:

    with st.expander("📤 Esporta database"):
        st.write("Scarica una copia SQLite del database nello stato attuale.")

        try:
            db_bytes = export_database(conn)

            st.download_button(
                label="📥 Download database SQLite",
                data=db_bytes,
                file_name="scouting_assistant.db",
                mime="application/x-sqlite3",
                width="stretch",
            )

        except Exception as exc:  # noqa: BLE001
            st.error(f"Export failed: {exc}")


# =============================================================================
# IMPORT CSV
# =============================================================================


def insert_csv(
    conn: sqlite3.Connection,
    table: str,
    df: pd.DataFrame,
) -> int:
    """
    Importa un CSV nella tabella.

    Il CSV NON deve contenere 'id'.

    SQLite genera automaticamente l'id.
    """

    db_columns = get_db_columns(
        conn,
        table,
    )

    if "id" not in db_columns:
        raise ValueError("La tabella deve avere una colonna 'id'.")

    # Tutte le colonne del DB tranne id
    insert_columns = [column for column in db_columns if column != "id"]

    csv_columns = list(df.columns)

    # -------------------------------------------------------------------------
    # Controllo colonne mancanti
    # -------------------------------------------------------------------------

    missing_columns = [column for column in insert_columns if column not in csv_columns]

    if missing_columns:
        raise ValueError("Colonne mancanti nel CSV: " + ", ".join(missing_columns))

    # -------------------------------------------------------------------------
    # Controllo colonne extra
    # -------------------------------------------------------------------------

    extra_columns = [column for column in csv_columns if column not in insert_columns]

    if extra_columns:
        raise ValueError("Colonne non previste nel CSV: " + ", ".join(extra_columns))

    # -------------------------------------------------------------------------
    # Riordina le colonne come nel DB
    # -------------------------------------------------------------------------

    df = df[insert_columns].copy()

    table_sql = quote_identifier(table)

    columns_sql = ", ".join(quote_identifier(column) for column in insert_columns)

    placeholders = ", ".join("?" for _ in insert_columns)

    insert_sql = f"""
        INSERT INTO {table_sql}
        ({columns_sql})
        VALUES ({placeholders})
    """

    rows = [
        tuple(normalize_sql_value(value) for value in row)
        for row in df.itertuples(
            index=False,
            name=None,
        )
    ]

    cursor = conn.cursor()

    try:
        cursor.executemany(
            insert_sql,
            rows,
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return len(rows)


def render_import_section(
    conn: sqlite3.Connection,
    table: str,
) -> None:

    with st.expander("⬆️ Importa CSV"):
        st.write(
            "Il CSV deve contenere le stesse colonne della tabella "
            "ad eccezione di `id`."
        )

        uploaded_file = st.file_uploader(
            "Seleziona CSV",
            type=["csv"],
            key="csv_uploader",
        )

        if uploaded_file is None:
            return

        try:
            # -----------------------------------------------------------------
            # Lettura CSV
            # -----------------------------------------------------------------

            df_csv = pd.read_csv(
                uploaded_file,
            )

            st.caption(f"Righe nel CSV: {len(df_csv)}")

            # -----------------------------------------------------------------
            # Preview
            # -----------------------------------------------------------------

            st.dataframe(
                df_csv.head(10),
                width="stretch",
                hide_index=True,
            )

            # -----------------------------------------------------------------
            # Validazione colonne prima del bottone
            # -----------------------------------------------------------------

            db_columns = get_db_columns(
                conn,
                table,
            )

            expected_columns = [column for column in db_columns if column != "id"]

            csv_columns = list(df_csv.columns)

            missing_columns = [
                column for column in expected_columns if column not in csv_columns
            ]

            extra_columns = [
                column for column in csv_columns if column not in expected_columns
            ]

            if missing_columns:
                st.error("Colonne mancanti nel CSV: " + ", ".join(missing_columns))

                return

            if extra_columns:
                st.error("Colonne non previste nel CSV: " + ", ".join(extra_columns))

                return

            # -----------------------------------------------------------------
            # Import
            # -----------------------------------------------------------------

            if st.button(
                f"⬆️ Importa {len(df_csv)} righe",
                type="primary",
                width="stretch",
            ):
                inserted = insert_csv(
                    conn,
                    table,
                    df_csv,
                )

                # SQLite è la source of truth
                st.session_state["df_loaded"] = read_table(
                    conn,
                    table,
                )

                # Nuovo editor
                st.session_state["editor_version"] = (
                    st.session_state.get(
                        "editor_version",
                        0,
                    )
                    + 1
                )

                st.success(f"{inserted} righe importate.")

                st.rerun()

        except Exception as exc:  # noqa: BLE001
            st.error(f"Import failed: {exc}")


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:

    # -------------------------------------------------------------------------
    # Download DB
    # -------------------------------------------------------------------------

    db_path = download_db()

    conn = get_conn(db_path)

    try:
        table = TABLE_NAME

        # =====================================================================
        # SESSION STATE INITIALIZATION
        # =====================================================================

        if "editor_version" not in st.session_state:
            st.session_state["editor_version"] = 0

        # =====================================================================
        # LOAD TABLE
        # =====================================================================

        if (
            "df_loaded" not in st.session_state
            or st.session_state.get("loaded_table") != table
        ):
            st.session_state["df_loaded"] = read_table(
                conn,
                table,
            )

            st.session_state["loaded_table"] = table

        # =====================================================================
        # RESET
        #
        # Deve avvenire PRIMA della creazione dei widget.
        # =====================================================================

        if st.session_state.pop(
            "reset_db_requested",
            False,
        ):
            apply_db_reset(
                conn,
                table,
            )

        # =====================================================================
        # FULL DATAFRAME
        # =====================================================================

        df_loaded = st.session_state["df_loaded"].copy()

        st.caption(f"Rows: {len(df_loaded)}")

        # =====================================================================
        # FILTRI
        # =====================================================================

        col1, col2 = st.columns(2)

        # ---------------------------------------------------------------------
        # Team filter
        # ---------------------------------------------------------------------

        with col1:
            team_query = st.text_input(
                "Filtra casa/ospite",
                key="team_query",
            )

        # ---------------------------------------------------------------------
        # Category filter
        # ---------------------------------------------------------------------

        with col2:
            if "Categoria" in df_loaded.columns:
                categorie = sorted(df_loaded["Categoria"].dropna().astype(str).unique())

                categorie_sel = st.multiselect(
                    "Categoria",
                    options=categorie,
                    key="categorie_sel",
                )

            else:
                categorie_sel = []

        # =====================================================================
        # APPLY FILTERS
        # =====================================================================

        df_visible = df_loaded.copy()
        df_visible = df_visible.reset_index(drop=True)

        # ---------------------------------------------------------------------
        # Team filter
        # ---------------------------------------------------------------------

        if team_query:
            mask_team = pd.Series(
                False,
                index=df_visible.index,
            )

            if "Casa" in df_visible.columns:
                mask_team = mask_team | df_visible["Casa"].astype(str).str.contains(
                    team_query,
                    case=False,
                    na=False,
                    regex=False,
                )

            if "Ospite" in df_visible.columns:
                mask_team = mask_team | df_visible["Ospite"].astype(str).str.contains(
                    team_query,
                    case=False,
                    na=False,
                    regex=False,
                )

            df_visible = df_visible[mask_team]

        # ---------------------------------------------------------------------
        # Category filter
        # ---------------------------------------------------------------------

        if categorie_sel and "Categoria" in df_visible.columns:
            df_visible = df_visible[
                df_visible["Categoria"].astype(str).isin(categorie_sel)
            ]

        # =====================================================================
        # DATA EDITOR
        # =====================================================================

        editor_key = f"table_editor_{st.session_state['editor_version']}"

        # ID visibile ma non modificabile
        column_config = {}

        if "id" in df_visible.columns:
            column_config["id"] = st.column_config.NumberColumn(
                "ID",
                disabled=True,
            )

        edited_df = st.data_editor(
            df_visible,
            num_rows="dynamic",
            width="stretch",
            key=editor_key,
            hide_index=True,
            column_config=column_config,
        )

        # =====================================================================
        # ACTION BUTTONS
        # =====================================================================

        col1, col2, _col3 = st.columns(3)

        # ---------------------------------------------------------------------
        # RESET
        # ---------------------------------------------------------------------

        with col1:
            st.button(
                "↩️ Reload from DB",
                on_click=request_db_reset,
                width="stretch",
            )

        # ---------------------------------------------------------------------
        # SAVE
        # ---------------------------------------------------------------------

        with col2:
            if st.button(
                "💾 Save changes to DB",
                type="primary",
                width="stretch",
            ):
                try:
                    result = save_table_changes(
                        conn=conn,
                        table=table,
                        original_df=df_visible,
                        edited_df=edited_df,
                    )

                    # ---------------------------------------------------------
                    # Ricarica SEMPRE dal DB
                    # ---------------------------------------------------------

                    st.session_state["df_loaded"] = read_table(
                        conn,
                        table,
                    )

                    # ---------------------------------------------------------
                    # Nuovo editor
                    # ---------------------------------------------------------

                    st.session_state["editor_version"] += 1

                    st.success(
                        "Modifiche salvate: "
                        f"{result['updated']} aggiornate, "
                        f"{result['inserted']} inserite, "
                        f"{result['deleted']} cancellate."
                    )

                    st.rerun()

                except Exception as exc:  # noqa: BLE001
                    st.error(f"Save failed: {exc}")

        # =====================================================================
        # EXPORT
        # =====================================================================

        render_export_section(
            conn,
        )

        # =====================================================================
        # IMPORT
        # =====================================================================

        render_import_section(
            conn,
            table,
        )

        # =====================================================================
        # FOOTER
        # =====================================================================

        add_markdown_divider()

    finally:
        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if not check_password():
    st.stop()

try:
    main()

except Exception as exc:
    st.error(f"Errore nell'applicazione: {exc}")

    # Utile durante sviluppo.
    # In produzione puoi rimuovere il raise.
    raise

page_nav()
