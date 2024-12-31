import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd
import dataset_references as ref
import calculate_stats as calc

app = dash.Dash(__name__)

# Duration of Involvement


# Roles
roles_data = pd.DataFrame(calc.occurances_column(df=ref.community_df, column='Role'))
roles_fig = px.bar(roles_data, x="values", y="counts", barmode="group", title="Distribution of Roles")
roles_fig.update_xaxes(title_text="Role")
roles_fig.update_yaxes(title_text="Number of Contributors")

app.layout = html.Div([
    html.H4('Range of Expertise and Involvement'),
    dcc.Graph(id="community", figure=roles_fig),
    # dcc.Graph(od)
])

if __name__ == '__main__':
    app.run_server(debug=True)