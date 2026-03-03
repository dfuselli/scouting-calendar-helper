import streamlit as st

def page_nav():
    c1, c2, c3, empty = st.columns([2,2,2,8])
    with c1:
        st.page_link("pages/1_⚽_CalendarHelper.py", label="Calendar Helper")
    with c2:
        st.page_link("pages/2_📊_CompetitionAnalysis.py", label="Competition Analysis")
    with c3:
        st.page_link("pages/3_📊_MatchAnalysis.py", label="Match Analysis")