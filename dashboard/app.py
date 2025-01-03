import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import requests
from .models_impact import models_impact_page as models_impact_page
from .community import community_blog_page as community_blog_page
from .events_and_publications import events_publications_page as events_publications_page

# Load data from JSON
data_url = "https://raw.githubusercontent.com/ersilia-os/ersilia-stats/refs/heads/main/reports/tables_stats.json"
data = requests.get(data_url).json()

# Initialize the app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
               requests_pathname_prefix='/ersilia-stats/')

# Sidebar layout
sidebar = html.Div([
    html.Div([
        html.A(
            html.Img(src="/assets/logo.png", className="logo", style={"width": "225px", "margin-bottom": "10px"}),
            href="/"
        )
    ], style={"text-align": "center"}),
    html.Div([
        html.Div([
            html.Img(src="/assets/icon_impact.png", className="icon", style={"width": "20px", "margin-right": "10px"}),
            dcc.Link("Models' Impact", href="/models-impact", className="nav-link", style={"color": "black", "font-weight": "normal", "text-decoration": "none", "font-size": "14px"})
        ], id="models-impact-link", style={"display": "flex", "align-items": "center", "margin-bottom": "10px", "padding": "5px", "border-radius": "40px"}),
        html.Div([
            html.Img(src="/assets/icon_community.png", className="icon", style={"width": "20px", "margin-right": "10px"}),
            dcc.Link("Community & Blog", href="/community-blog", className="nav-link", style={"color": "black", "font-weight": "normal", "text-decoration": "none", "font-size": "14px"})
        ], id="community-blog-link", style={"display": "flex", "align-items": "center", "margin-bottom": "10px", "padding": "5px", "border-radius": "40px"}),
        html.Div([
            html.Img(src="/assets/icon_publication.png", className="icon", style={"width": "20px", "margin-right": "10px"}),
            dcc.Link("Events & Publications", href="/events-publications", className="nav-link", style={"color": "black", "font-weight": "normal", "text-decoration": "none", "font-size": "14px"})
        ], id="events-publications-link", style={"display": "flex", "align-items": "center", "margin-bottom": "10px", "padding": "5px", "border-radius": "40px"})
    ], style={"padding": "12px 12px", "display": "flex", "flex-direction": "column"}),
    html.Div([
        html.Div([
            html.P("Get involved!", style={"color": "black", "font-weight": "bold", "font-size": "16px", "margin-bottom": "2px", "text-align": "left"}),
            html.P("Join our efforts to make science more equitable.", style={"color": "black", "font-size": "12px", "margin-bottom": "10px", "text-align": "left"}),
            dbc.Button("Donate", color="primary", style={"background-color": "#6A1B9A", "font-size": "12px", "border": "none", "margin-bottom": "5px", "width": "100%"}),
            dbc.Button("Volunteer", outline=True, color="primary", className="custom-volunteer-btn")
        ], style={"text-align": "center", "padding": "0px 20px 0px 10px"}),
        html.Hr(style={"border": "1px solid #ccc", "margin": "15px 7px"}),
        html.Div([
            html.P("Learn more at ", style={"color": "black", "font-size": "12px", "display": "inline"}),
            html.A("Ersilia.io", href="https://ersilia.io", target="_blank", style={"color": "#6A1B9A", "font-size": "12px", "text-decoration": "underline"})
        ], style={"text-align": "left", "padding": "0px 20px 0px 10px"})
    ], style={"position": "absolute", "bottom": "20px", "width": "100%", "text-align": "center", "padding": "0px 20px 0px 0px"})
], className="sidebar", style={"padding": "20px", "width": "300px", "background-color": "#f8f9fa", "position": "fixed", "height": "100%"})


# Main content area for the landing page
home_page = html.Div([
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

# App layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    sidebar,
    html.Div(id="page-content")
])

# Callbacks to handle page navigation
@app.callback(
    dash.dependencies.Output("page-content", "children"),
    [dash.dependencies.Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/models-impact":
        model_layout = models_impact_page()
        return model_layout
    elif pathname == "/community-blog":
        community_layout = community_blog_page()
        return community_layout
    elif pathname == "/events-publications":
        events_layout = events_publications_page()
        return events_layout
    else:
        return home_page

# Callbacks to manage highlight behavior
@app.callback(
    [
        dash.dependencies.Output("models-impact-link", "style"),
        dash.dependencies.Output("community-blog-link", "style"),
        dash.dependencies.Output("events-publications-link", "style")
    ],
    [dash.dependencies.Input("url", "pathname")]
)
def update_sidebar_highlight(pathname):
    default_style = {"display": "flex", "align-items": "center", "margin-bottom": "10px", "padding": "5px", "border-radius": "5px"}
    highlighted_style = {"display": "flex", "align-items": "center", "margin-bottom": "10px", "padding": "5px", "border-radius": "5px", "background-color": "#e0e0e0"}

    return (
        highlighted_style if pathname == "/models-impact" else default_style,
        highlighted_style if pathname == "/community-blog" else default_style,
        highlighted_style if pathname == "/events-publications" else default_style
    )
# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)

