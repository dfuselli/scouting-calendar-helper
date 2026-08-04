import streamlit as st


def page_nav():
    c1, c2, c4, _empty = st.columns([2, 2, 2, 8])
    with c1:
        st.page_link("pages/1_⚽_CalendarHelper.py", label="Calendar")
    with c2:
        st.page_link("pages/2_📊_CompetitionAnalysis.py", label="GeoAnalysis")
    # with c3:
    #     st.page_link("pages/3_📊_MatchAnalysis.py", label="Match Analysis")
    with c4:
        st.page_link("pages/4_DatabaseBrowser.py", label="Database")
