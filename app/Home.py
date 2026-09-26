import streamlit as st  # noqa: N999

calendar = st.Page("./pages/1_⚽_CalendarHelper.py", title="Calendar")
competitions = st.Page("./pages/2_📊_CompetitionAnalysis.py", title="GeoAnalysis")
match = st.Page("./pages/3_📊_MatchAnalysis.py", title="Match Analysis")
database_browser = st.Page("./pages/4_DatabaseBrowser.py", title="Database")

pg = st.navigation([calendar, competitions, match, database_browser], position="hidden")  # ty: ignore[call-non-callable]
pg.run()
