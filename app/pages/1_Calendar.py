import streamlit as st
import pandas as pd

st.title("Visualizzatore di file XLS con filtri")

# Upload del file
uploaded_file = st.file_uploader("Carica un file .xls", type=["xls"])

if uploaded_file is not None:
    try:
        # Legge il file Excel
        df = pd.read_excel(uploaded_file, engine='xlrd')

        st.subheader("Anteprima del file")
        st.dataframe(df.head())

        # Filtri dinamici
        st.subheader("Filtri")

        columns = df.columns.tolist()

        # Genera un filtro per ogni colonna selezionata
        selected_columns = st.multiselect("Seleziona le colonne da filtrare", columns)

        filtered_df = df.copy()

        for col in selected_columns:
            if df[col].dtype == 'object':
                options = df[col].dropna().unique().tolist()
                selected_options = st.multiselect(f"Filtra '{col}'", options)
                if selected_options:
                    filtered_df = filtered_df[filtered_df[col].isin(selected_options)]
            else:
                min_val, max_val = df[col].min(), df[col].max()
                selected_range = st.slider(f"Filtra '{col}' (range)", float(min_val), float(max_val), (float(min_val), float(max_val)))
                filtered_df = filtered_df[(df[col] >= selected_range[0]) & (df[col] <= selected_range[1])]

        st.subheader("Tabella filtrata")
        st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
