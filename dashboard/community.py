import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd
import scripts.dataset_references as ref
import scripts.calculate_stats as calc

def community_blog_page():
    # Duration of Involvement
    duration_data = pd.DataFrame(calc.community_time_duration())
    if "values" in duration_data.columns:
        duration_data["values"] = duration_data["values"].astype(str)  # Convert intervals to strings

    duration_fig = px.bar(duration_data, x="values", y="counts", barmode="group", title="Duration of Involvement")
    duration_fig.update_xaxes(title_text="Duration of Involvement")
    duration_fig.update_yaxes(title_text="Number of Contributors")

    # Roles
    roles_data = pd.DataFrame(calc.occurances_column(df=ref.community_df, column='Role'))
    roles_fig = px.bar(roles_data, x="values", y="counts", barmode="group", title="Distribution of Roles")
    roles_fig.update_xaxes(title_text="Role")
    roles_fig.update_yaxes(title_text="Number of Contributors")

    return html.Div([
        html.H4('Range of Expertise and Involvement'),
        dcc.Graph(id="roles_community", figure=roles_fig),
        dcc.Graph(id="duration_community", figure=duration_fig)
    ], style={"margin-left": "320px", "padding": "20px"}) 
