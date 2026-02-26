import geopandas as gpd
import pandas as pd
import streamlit as st
import unidecode
from streamlit.runtime.uploaded_file_manager import UploadedFile

def normalize_key(key):
    return unidecode.unidecode(key.lower()).replace(" ", "")


# Carica i dati dei comuni
@st.cache_data
def load_geojson_data():
    # Assicurati di avere un file GeoJSON per i confini amministrativi
    gdf = gpd.read_file("app/resources/limits_IT_municipalities.geojson")
    return gdf


@st.cache_data
def read_xls(file: UploadedFile):
    return None


@st.cache_data
def get_coordinates(team):
    gdf = load_geojson_data()
    return "Bergamo"