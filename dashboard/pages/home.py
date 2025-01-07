import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import requests
from dash import html

# dash.register_page(__name__, path="/")

# Main content area for the landing page
def home_page():
    return html.Div([
    html.H1("Welcome to the Ersilia Dashboard", style={"margin-top": "20px", "margin-bottom": "20px"}),
    html.P(
        "This dashboard is designed to provide an interactive experience with data insights related to Ersilia's initiatives. Explore our Models' Impact, Community & Blog, and Events & Publications to learn more about our contributions to global health and open science.",
        style={"font-size": "18px", "line-height": "1.6"}
    ),
    html.P(
        "Ersilia is committed to making science more equitable through open collaboration and innovative technologies. Learn more about our mission and explore our resources at ",
        style={"font-size": "18px", "line-height": "1.6", "display": "inline"}
    ),
    html.A("Ersilia.io", href="https://ersilia.io", target="_blank", style={"font-size": "18px", "color": "#6A1B9A", "text-decoration": "underline"})
], style={"margin-left": "320px", "padding": "20px"})

layout = home_page()