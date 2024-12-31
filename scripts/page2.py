import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd
import dataset_references as dr

app = dash.Dash(__name__)

fig = px.bar(dr.community_modified_df, x="Role", y="Name", color="Role", barmode="group", title="Distribution of Roles")


app.layout = html.Div([
    html.H4('Range of Expertise and Involvement'),
    dcc.Graph(id="community", figure=fig),
])

if __name__ == '__main__':
    app.run_server(debug=True)