import streamlit as st

def page_nav():
    c1, c2, empty = st.columns([2,2,10])
    with c1:
        st.page_link("pages/1_⚽_CalendarHelper.py", label="Calendar Helper")
    with c2:
        st.page_link("pages/2_📊_DataAnalysis.py", label="Data Analysis")