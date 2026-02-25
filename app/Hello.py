import streamlit as st

home = st.Page("./pages/1_⚽_CalendarHelper.py", title="Calendar Helper")
settings = st.Page("./pages/2_📊_DataAnalysis.py", title="Data Analysis")

pg = st.navigation([home, settings], position="hidden")
pg.run()