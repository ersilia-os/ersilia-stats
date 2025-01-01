import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd

def events_publications_page():
    return html.Div([
        # Header Section
        html.P("Events & Publications", style={"font-size": "24px", "font-weight": "bold"}),

        # Events Section
        html.P("Events", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            html.Div([
                html.P("Placeholder for Event Distribution Over Time", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                html.P("Placeholder for Event Breakdown By Types", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"text-align": "center"}),

        html.Div([
            # Country Buttons
            html.Div([
                html.Button(
                    country,
                    id=f"btn-{country.replace(' ', '_').lower()}",
                    style={
                        "padding": "5px 10px",
                        "margin": "5px",
                        "border": "1px solid #ddd",
                        "border-radius": "5px",
                        "background-color": "#f5f5f5",
                        "color": "#000",
                        "cursor": "pointer"
                    }
                ) for country in ["Australia", "Cameroon", "Columbia", "India", "Italy", "Kenya", "Spain"]
            ], style={"margin-bottom": "10px", "display": "flex", "flex-wrap": "wrap"}),

            # Map visualization
            dcc.Graph(
                id="events_by_country_map",
                style={"height": "400px"}
            )
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px"}),

        # Publications Section
        html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),
        html.P("Publications", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            html.Div([
                html.P("Placeholder for Timeline Of Publications", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                html.P("Placeholder for Citations For Publications", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"text-align": "center"}),

        html.Div([
            html.Div([
                html.P("Placeholder for Collaboration With Ersilia", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                html.P("Placeholder for Publications By Topic Area", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                html.P("Placeholder for Distribution Of Organizations", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                html.P("Placeholder for Top Collaborators", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"text-align": "center"})
    ], style={"margin-left": "320px", "padding": "20px"})
