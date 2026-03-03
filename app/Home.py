import streamlit as st

calendar = st.Page("./pages/1_⚽_CalendarHelper.py", title="Calendar Helper")
competitions = st.Page("./pages/2_📊_CompetitionAnalysis.py", title="Competition Analysis")
match = st.Page("./pages/3_📊_MatchAnalysis.py", title="Match Analysis")

pg = st.navigation([calendar, competitions, match], position="hidden")
pg.run()