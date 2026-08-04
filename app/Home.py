import streamlit as st  # noqa: N999

calendar = st.Page("./pages/1_⚽_CalendarHelper.py", title="Calendar Helper")
competitions = st.Page(
    "./pages/2_📊_CompetitionAnalysis.py", title="Competition Analysis"
)
# match = st.Page("./pages/3_📊_MatchAnalysis.py", title="Match Analysis")
database_browser = st.Page("./pages/4_DatabaseBrowser.py", title="Database Browser")

pg = st.navigation([calendar, competitions, database_browser], position="hidden")
pg.run()
