import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
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
        # Header Section
        html.Div([
            html.P("Community & Blog", 
                   style={"font-size": "24px", "font-weight": "bold"}),
            html.P("Total To Date", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.P([
                html.Span("Through committed support, collaboration, and communication, Ersilia nurtures a growing community across the world with high representation from the Global South.", style={"color": "#a9a9a9", "font-size": "12px"}),
            ], style={"line-height": "1.6", "margin-bottom": "20px"})
        ]),

        # Metrics Overview
        ### CHANGE THIS: this needs to be dynamically retrieved from the output data
        html.Div([
            html.Div([
                html.P("Countries Represented", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                html.P("16", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Unique Contributors", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                html.P("91", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Volunteer Organizations", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                html.P("12", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Blog Posts", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                html.P("37", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px"})
        ], style={"margin-bottom": "20px", "text-align": "center"}),

        # Global Representation Section
        html.P("Global Representation", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            # Graph header
            html.P([
                html.Span("Contributors By Country: ", style={"font-size": "14px", "font-weight": "bold"}),
                html.Span("Total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                html.Span("16 unique countries", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                html.Span(", including 9 countries from the Global South and 7 countries from the Global North.", style={"font-size": "12px", "color": "#a9a9a9"})
            ], style={"line-height": "1.6", "margin-bottom": "10px"}),
            html.P("*Global South: Africa, Latin America and the Caribbean, Asia (excluding Israel, Japan, and South Korea), and Oceania (excluding Australia and New Zealand)", style={"font-size": "12px", "color": "#a9a9a9"}),
            
            # Dynamic country buttons
            html.Div([
                html.Button(
                    country,
                    id=f"btn-{country.replace(' ', '_').lower()}",
                    style={
                        "padding": "5px 10px",
                        "margin": "5px",
                        "border": "1px solid #ddd",
                        "border-radius": "5px",
                        "background-color": "#f5f5f5",  # Default background
                        "color": "#000",
                        "cursor": "pointer"
                    }
                ) for country in ["Australia", "Cameroon", "Columbia", "India", "Italy", "Kenya", "Spain"]
            ], style={"margin-bottom": "10px", "display": "flex", "flex-wrap": "wrap"}),

            # Map visualization
            dcc.Graph(
                id="global_representation_map",
                style={"height": "400px"}
            )
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px"}),

        # Range of Expertise and Involvement Section
        html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),
        html.Div([
            html.P("Range of Expertise and Involvement", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.Div([
                dcc.Graph(id="roles_community", figure=roles_fig)
            ]),
            html.Div([
                html.Div([
                    dcc.Graph(id="duration_community", figure=duration_fig)
                ], style={"width": "48%", "display": "inline-block"}),
                html.Div([
                    html.P("Placeholder for Pie chart", style={"text-align": "center", "font-size": "14px"})
                ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "vertical-align": "top"}),
            ])
            
        ]),

        # Active Knowledge Sharing
        html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),
        html.P("Active Knowledge Sharing", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.P([
            html.Span(
                "Stay up to date with our  ",
                style={"color": "#a9a9a9", "font-size": "12px"}
            ),
            html.A("newsletter", href="https://eepurl.com/hkX1sH", target="_blank", style={"font-size": "12px", "color": "#6A1B9A", "text-decoration": "underline"}),
            html.Span(
                " and  ",
                style={"color": "#a9a9a9", "font-size": "12px"}
            ),
            html.A("blogposts", href="https://medium.com/ersiliaio", target="_blank", style={"font-size": "12px", "color": "#6A1B9A", "text-decoration": "underline"}),
        ]),
        html.Div([
            html.Div([
                html.P("Placeholder for Distribution of Blog Post Topics", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "vertical-align": "top"}),
            html.Div([
                html.P("Placeholder for Blog Posts Over Time", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "vertical-align": "top"}),
            html.Div([
                html.P("Placeholder for Engagement Trends By Topic", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "vertical-align": "top"}),
            html.Div([
                html.P("Placeholder for Engagement Trends Over Time", style={"text-align": "center", "font-size": "14px"})
            ], style={"width": "48%", "height": "300px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "vertical-align": "top"})
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px"})
    ], style={"margin-left": "320px", "padding": "20px"})


def register_callbacks(app):
    @app.callback(
        Output("global_representation_map", "figure"),
        [Input(f"btn-{country.replace(' ', '_').lower()}", "n_clicks") for country in ["Australia", "Cameroon", "Columbia", "India", "Italy", "Kenya", "Spain"]],
        prevent_initial_call=True
    )
    def update_map(*button_clicks):
        # Identify the clicked button
        countries = ["Australia", "Cameroon", "Columbia", "India", "Italy", "Kenya", "Spain"]
        clicked_country = None
        for i, clicks in enumerate(button_clicks):
            if clicks:
                clicked_country = countries[i]
                break

        # Highlight the clicked country and update map data
        if clicked_country:
            locations = ["AUS", "CMR", "COL", "IND", "ITA", "KEN", "ESP"]
            classifications = ["Global North", "Global South", "Global South", "Global South", "Global North", "Global South", "Global North"]
            hover_data = [5.0, 10.5, 7.8, 20.1, 3.3, 12.4, 15.2]  # Placeholder values
            colors = ["#bee6b4" if c == "Global North" else "#aa96fa" for c in classifications]

            # Dynamically set selected country's color to a darker shade
            for i, location in enumerate(locations):
                if location == clicked_country[:3].upper():  # Match ISO-3 code
                    colors[i] = "#8368d4" if classifications[i] == "Global South" else "#98d0a1"

            # Update the map
            figure = px.choropleth(
                locations=locations,
                locationmode="ISO-3",
                color=colors,
                hover_name=countries,
                hover_data={"Percent Contributors": hover_data}
            ).update_layout(
                geo=dict(
                    showcoastlines=False,
                    showcountries=True,
                    countrycolor="white",
                    landcolor="lightgray"
                ),
                margin={"r": 0, "t": 0, "l": 0, "b": 0}
            )
            return figure

        # Default map if no button clicked
        return px.choropleth(
            locations=["AUS", "CMR", "COL", "IND", "ITA", "KEN", "ESP"],
            locationmode="ISO-3",
            color=["Global North", "Global South", "Global South", "Global South", "Global North", "Global South", "Global North"],
            hover_name=["Australia", "Cameroon", "Columbia", "India", "Italy", "Kenya", "Spain"],
            hover_data={"Percent Contributors": [5.0, 10.5, 7.8, 20.1, 3.3, 12.4, 15.2]},
            color_discrete_map={"Global South": "#aa96fa", "Global North": "#bee6b4"}
        ).update_layout(
            geo=dict(
                showcoastlines=False,
                showcountries=True,
                countrycolor="white",
                landcolor="lightgray"
            ),
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )