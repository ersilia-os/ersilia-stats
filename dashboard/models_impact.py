import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd

def models_impact_page():
    return html.Div([
        # Header Section
        html.Div([
            html.P("Models' Impact", 
                    style={"width": "50%", "display": "inline-block", "vertical-align": "top", "padding-right": "20px", "padding-top": "20px",
                           "font-size": "24px", "font-weight": "bold"}),
            html.Div([
                dcc.Dropdown(
                    ### CHANGE THIS: the diseases need to be dynamically retrieved from the output data
                    options=[{"label": "Disease 1", "value": "D1"}, {"label": "Disease 2", "value": "D2"}], 
                    placeholder="Select a Disease",
                    style={"margin-bottom": "20px"}
                )
            ], style={"width": "50%", "display": "inline-block", "vertical-align": "top", "padding-right": "20px", "padding-top": "20px"})
        ]),

        # Disease Impact and Map Section
        html.Div([
            # Left Column: Disease Impact Text/Statistics
            html.Div([
                html.P("Disease Impact In The Global South", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
                html.P([
                    html.Span("In the Global South, ", style={"color": "#a9a9a9", "font-size": "12px"}),
                    html.Span("119,174,900", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                    html.Span(" people suffer from severe diseases, and ", style={"color": "#a9a9a9", "font-size": "12px"}),
                    html.Span("160,237,419", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                    html.Span(" of them have died as a result.", style={"color": "#a9a9a9", "font-size": "12px"})
                ], style={"line-height": "1.6", "margin-bottom": "20px"}),
                html.Div([
                    html.Div([
                        html.P("All Disease Cases", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                        html.P("Placeholder for Total Cases", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                    ], style={"padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-bottom": "10px"}),
                    html.Div([
                        html.P("All Deaths", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                        html.P("Placeholder for Total Deaths", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                    ], style={"padding": "10px", "border": "1px solid #ddd", "border-radius": "10px"})
                ])
            ], style={"width": "40%", "display": "inline-block", "vertical-align": "top", "padding-right": "20px"}),

            # Right Column: Dropdown and Map
            html.Div([
                html.Div([
                    html.P("Placeholder for Map", style={"text-align": "center", "font-size": "16px"})
                ], style={"height": "310px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px"})
            ], style={"width": "60%", "display": "inline-block", "vertical-align": "top"})
        ], style={"display": "flex", "justify-content": "space-between", "margin-bottom": "20px"}),

        # Divider
        html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),

        # Ersilia's Models Section
        html.Div([
            html.P("Ersilia's Models", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.P([
                    html.Span("To address the challenges above, Ersilia has developed ", style={"color": "#a9a9a9", "font-size": "12px"}),
                    html.Span("NUMBER models", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                    html.Span(" each designed with diverse applications in mind.", style={"color": "#a9a9a9", "font-size": "12px"}),
                ], style={"line-height": "1.6", "margin-bottom": "20px"}),
        ]),

        # Visualization Section
        html.Div([
            html.Div([
                html.P("Placeholder for Model Distribution Chart", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "30%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "3%"}),
            html.Div([
                html.P("Placeholder for Model Status Gauge", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "30%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "3%"}),
            html.Div([
                html.P("Placeholder for Disease Cases vs. Models Chart", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "30%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px"})
        ], style={"text-align": "center", "margin-bottom": "20px"}),

        # Model List Table
        html.Div([
            html.P(
                "Model List",
                style={
                    "width": "50%",
                    "display": "inline-block",
                    "vertical-align": "top",
                    "padding-right": "20px",
                    "padding-top": "20px",
                    "font-size": "18px",
                    "font-weight": "bold"
                }
            ),
            html.Div([
                dcc.Input(
                    id="search-bar",
                    type="text",
                    placeholder="Search models...",
                    style={
                        "width": "300px",
                        "margin-bottom": "20px",
                        "padding": "10px",
                        "border": "1px solid #ccc",
                        "border-radius": "5px",
                        "box-shadow": "0px 2px 5px rgba(0, 0, 0, 0.1)"
                    }
                )
            ], style={
                "width": "50%",
                "display": "inline-block",
                "text-align": "right",
                "padding-right": "20px",
                "padding-top": "20px"
            })
        ], style={
            "display": "flex",
            "justify-content": "space-between",
            "align-items": "center",
            "margin-bottom": "2px"
        }),
        html.Div([
            html.P("Placeholder for Model List Table", style={"text-align": "center", "font-size": "16px"})
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "height": "300px", "margin-bottom": "20px"}),

        # Pagination
        html.Div([
            html.P("Placeholder for Pagination", style={"text-align": "center", "font-size": "14px"})
        ], style={"margin-bottom": "20px"})
    ], style={"margin-left": "320px", "padding": "20px"})
