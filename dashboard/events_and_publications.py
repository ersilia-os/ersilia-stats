import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd

def events_publications_page():
    return html.Div([
        html.H1("Events & Publications Page", style={"text-align": "center", "margin-top": "20px"})
    ], style={"margin-left": "320px", "padding": "20px"})