import json
from map.constants import BERGAMO_GPS_COORD
import plotly.express as px
import plotly.graph_objects as go

dark_greens_with_gray0 = [
        (0.00, "#B2AFAF"),  # 0 = grigio
        (0.10, "#4d9d65"),
        (0.60, "#31a354"),
        (1.00, "#005723"),
    ]

def create_map(gdf, df_agg):
    geojson = json.loads(gdf.to_json())
    mx = max(int(df_agg["n_squadre"].max()), 1)
    fig = px.choropleth_mapbox(
        df_agg,
        geojson=geojson,
        locations="Comune",
        featureidkey="properties.name",
        color="n_squadre",
        range_color=(0, mx),
        color_continuous_scale=dark_greens_with_gray0,
        mapbox_style="open-street-map",
        opacity=0.6,
        zoom=9,
        center={"lat": BERGAMO_GPS_COORD[0], "lon": BERGAMO_GPS_COORD[1]},
    )
    fig = add_all_boundaries(fig, geojson)

    # Passo al trace dati extra per hover: [Comune, n_squadre, case_str]
    fig.update_traces(
        customdata=df_agg[["case_str_hover"]].to_numpy(),
        hovertemplate=(
            "<b>%{location}</b><br>"
            "%{customdata[0]}"
            "<extra></extra>"
        ),
        selector=dict(type="choroplethmapbox"),
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig


def add_all_boundaries(fig, geojson):
    all_names = [f["properties"]["name"] for f in geojson["features"]]

    outline = go.Choroplethmapbox(
        geojson=geojson,
        locations=all_names,
        z=[0] * len(all_names),
        featureidkey="properties.name",
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],  # fill trasparente
        showscale=False,
        marker_line_width=1.0,
        marker_line_color="rgba(0,0,0,0.55)",
        hoverinfo="skip",
        name="Confini",
    )
    fig.add_trace(outline)
    return fig