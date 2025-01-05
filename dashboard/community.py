import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import scripts.dataset_references as ref
import scripts.calculate_stats as calc
import requests
import json

# Load data from JSON
with open("reports/tables_stats.json") as json_file:
    data = json.load(json_file)

global_south_countries = [
    "Afghanistan", "Algeria", "Angola", "Antigua & Barbuda", "Argentina", "Aruba", 
    "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belize", "Benin", 
    "Bhutan", "Bolivia", "Botswana", "Brazil", "Brunei", "Burkina Faso", "Burundi", 
    "Cambodia", "Cameroon", "Cape Verde", "Central African Rep.", "Chad", "Chile", 
    "China", "Colombia", "Comoros", "Congo, Dem. Rep.", "Congo, Rep.", "Costa Rica", 
    "Côte d'Ivoire", "Cuba", "Djibouti", "Dominica", "Dominican Rep.", "Ecuador", 
    "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Eswatini, Kingdom of", 
    "Ethiopia", "Fiji", "Gabon", "Gambia", "Ghana", "Grenada", "Guadeloupe", 
    "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "India", 
    "Indonesia", "Iran, Isl. Rep.", "Iraq", "Jamaica", "Jordan", "Kazakhstan", 
    "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Lao PDR", "Lebanon", "Lesotho", 
    "Liberia", "Libya", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", 
    "Mauritania", "Mauritius", "Mexico", "Micronesia, Fed. States of", "Mongolia", 
    "Morocco", "Mozambique", "Myanmar", "Namibia", "Nepal", "Nicaragua", "Niger", 
    "Nigeria", "Oman", "Pakistan", "Palau", "Palestine(West Bank & Gaza)", "Panama", 
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Qatar", "Rwanda", "Samoa", 
    "São Tomé & Príncipe", "Saudi Arabia", "Senegal", "Seychelles", "Sierra Leone", 
    "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Sri Lanka", 
    "St Vincent & Grenadines", "Sudan", "Suriname", "Syrian Arab Rep.", "Tajikistan", 
    "Tanzania, United Rep.", "Thailand", "Timor-Leste", "Togo", "Tonga", 
    "Trinidad & Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", 
    "United Arab Emirates", "Uruguay", "Uzbekistan", "Vanuatu, Rep.", "Venezuela", 
    "Vietnam", "Yemen", "Zambia", "Zimbabwe"
]


def community_blog_page():
    # Duration of Involvement
    duration_data = pd.DataFrame(data["community"]["duration_distribution"])

    # Map durations to broader categories
    duration_data["Duration Category"] = duration_data["Duration"].map({
        "< 3 Months": "Short-Term",
        "3-6 Months": "Short-Term",
        "6-12 Months": "Short-Term",
        "> 1 Year": "Long-Term"
    })

    # Define custom color mapping
    custom_color_map = {
        "Short-Term": "#aa96fa",  # Purple
        "Long-Term": "#bee6b4"    # Green
    }

    duration_fig = px.bar(
        duration_data, 
        x="Duration", 
        y="Count", 
        color="Duration Category",  # Use the custom color column
        color_discrete_map=custom_color_map,  # Map colors directly from the column
        category_orders={"Duration": ["< 3 Months", "3-6 Months", "6-12 Months", "> 1 Year"]}  # Enforce order
    )

    duration_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Duration of Involvement")
    duration_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Contributors")
    duration_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} contributors<extra></extra>",
        marker=dict(line=dict(color="white"))
    )
    duration_fig.update_layout(
        hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"),
        legend=dict(
            font=dict(size=10),  # Reduce legend font size
            xanchor="right",
            x=1,
            yanchor="top",
            y=1.3
        ),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA"
    )

    # Roles Plot
    roles_data = pd.DataFrame(data["community"]["role_distribution"])

    roles_fig = px.bar(
        roles_data, 
        x="Role", 
        y="Count", 
        barmode="group", 
        color_discrete_sequence=["#aa96fa"]  # Purple
    )

    roles_fig.update_layout(
        font=dict(color="#a9a9a9",
                  family="Arial"),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor="#FAFAFA",
        plot_bgcolor="#FAFAFA",
        hoverlabel=dict(
            bgcolor="black"
        )
    )

    roles_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Role")
    roles_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Contributors")
    roles_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} contributors<extra></extra>",
        marker=dict(line=dict(color="white"))
    )

    # Contributions by Organization Pie chart
    org_types_data = pd.DataFrame(data["organization"]["organization_types"])
    total_types = org_types_data["Count"].sum()

    # Calculate percentage contributions
    org_types_data["Percentage"] = (org_types_data["Count"] / total_types) * 100

    # Pie chart
    org_pie_fig = px.pie(
        org_types_data, 
        values="Count", 
        names="Type", 
        color="Type",
        color_discrete_sequence=["#aa96fa", "#8cc8fa", "#dca0dc","#faa08c", "#fad782", "#bee6b4", "#d2d2d0"],  # Custom colors  
    )

    org_pie_fig.update_traces(
        customdata=org_types_data[["Percentage", "Count"]],
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>%{customdata[0][1]}<extra></extra> (%{customdata[0][0]:.2f}%)",
        textposition = 'inside'
    )
    org_pie_fig.update_layout(uniformtext_minsize=50, uniformtext_mode='hide')

    org_pie_fig.update_layout(
        hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"),
        legend=dict(
            font=dict(size=14),  # Reduce legend font size
            xanchor="right",
            x=1.75,
            yanchor="middle",
            y=0.5
        ),
        font=dict(color="#a9a9a9",
                  family="Arial"),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        plot_bgcolor="#FAFAFA",
    )

    # Blogposts over time Plot (year)
    blogposts_time_data = pd.DataFrame(data["blogposts-events"]["posts_over_time"])

    blogposts_time_fig = px.bar(
        blogposts_time_data, 
        x="Year", 
        y="Post Count", 
        barmode="stack", 
        color="Quarter",
        color_discrete_sequence=["#aa96fa", "#8cc8fa", "#dca0dc","#faa08c", "#fad782"],  # Custom colors
        category_orders={"Quarter": ["Q1", "Q2", "Q3", "Q4"]},  #  order ;o
        hover_data={'Quarter': True, 'Post Count': True, 'Year': True}
    )

    blogposts_time_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Year")
    blogposts_time_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Blogposts")
    blogposts_time_fig.update_layout(
        margin=dict(t=50, b=50, l=50, r=50),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA"
    )
    blogposts_time_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA"
    )
    blogposts_time_fig.update_traces(
        hovertemplate="<b>%{x} %{fullData.name}</b><br>%{y} posts<extra></extra>",
        marker=dict(line=dict(color="white"))
    )


    # Blogposts by Topics Pie Chart
    blogposts_topics_data = pd.DataFrame(data["blogposts-events"]["tag_distribution"])

    blogposts_topics_fig = px.pie(
        blogposts_topics_data,
        values="Count",
        names="Tag",
        color="Tag",
        color_discrete_sequence=["#aa96fa", "#dca0dc", "#8cc8fa", "#faa08c", "#fad782", "#bee6b4", "#d2d2d0"],  # Custom colors  
    )

    blogposts_topics_fig.update_traces(
        customdata=blogposts_topics_data[["Percentage", "Count"]],
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br> %{customdata[0][1]}<extra></extra> (%{customdata[0][0]:.2f}%)",
        textposition = 'inside'
    )
    blogposts_topics_fig.update_layout(uniformtext_minsize=2504, uniformtext_mode='hide')
    blogposts_topics_fig.update_layout(
        hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"),
        legend=dict(
            font=dict(size=12), 
            xanchor="right",
            x=2,
            yanchor="middle",
            y=0.5
        ),
        font=dict(color="#a9a9a9",
                  family="Arial"),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        plot_bgcolor="#FAFAFA",
    )

    return html.Div([
        # Header Section
        html.Div([
            html.P("Community & Blog", 
                   style={"font-size": "30px", "font-weight": "bold"}),
            html.P("Total To Date", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.P([
                html.Span("Through committed support, collaboration, and communication, Ersilia nurtures a growing community across the world with high representation from the Global South.", style={"color": "#a9a9a9", "font-size": "12px"}),
            ], style={"line-height": "1.6", "margin-bottom": "20px"})
        ]),

        # Metrics Overview
        html.Div([
            html.Div([
                html.P("Countries Represented", style={"text-align": "left", "font-size": "12px", "margin-bottom": "5px",
                                                       "font-weight": "bold"}),
                html.P(str(data["community"]["countries_represented"]), 
                       style={"text-align": "left", "font-size": "30px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "23%", "height": "100px", "display": "inline-block", "padding": "20px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%",
                      "backgroundColor": "#FAFAFA"}),
            html.Div([
                html.P("Unique Contributors", style={"text-align": "left", "font-size": "12px", "margin-bottom": "5px",
                                                       "font-weight": "bold"}),
                html.P(str(data["community"]["total_members"]), 
                       style={"text-align": "left", "font-size": "30px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "23%", "height": "100px", "display": "inline-block", "padding": "20px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%",
                      "backgroundColor": "#FAFAFA"}),
            html.Div([
                html.P("Organisations In Our Network", style={"text-align": "left", "font-size": "12px", "margin-bottom": "5px",
                                                       "font-weight": "bold"}),
                html.P(str(data["organization"]["total_organizations"]), 
                       style={"text-align": "left", "font-size": "30px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "23%", "height": "100px", "display": "inline-block", "padding": "20px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%",
                      "backgroundColor": "#FAFAFA"}),
            html.Div([
                html.P("Blog Posts", style={"text-align": "left", "font-size": "12px", "margin-bottom": "5px",
                                                       "font-weight": "bold"}),
                html.P(str(data["blogposts-events"]["total_blogposts"]), 
                       style={"text-align": "left", "font-size": "30px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "23%", "height": "100px", "display": "inline-block", "padding": "20px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%",
                      "backgroundColor": "#FAFAFA"}),
        ], style={"margin-bottom": "20px", "text-align": "center"}),

        # Global Representation Section
        html.Hr(style={"border": "1px solid #ccc", "margin": "20px 0"}),
        html.P("Global Representation", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            # Graph header
            html.Div([
                html.P("Contributors By Country", style={"font-size": "14px", "font-weight": "bold"}),
                html.P([
                    html.Span("Total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                    html.Span(f"{len(data['community']['contributors_by_country'])} unique countries", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                ], style={"line-height": "1.6", "margin-bottom": "10px"})
            ], style={"margin-bottom": "0px"}),
            html.P("*Global South: Africa, Latin America and the Caribbean, Asia (excluding Israel, Japan, and South Korea), and Oceania (excluding Australia and New Zealand)", 
                   style={"font-size": "12px", "color": "#a9a9a9"}),
            
            # Map graph
            dcc.Graph(
                id="global_representation_map",
                figure=px.choropleth(
                    pd.DataFrame(data['community']['contributors_by_country']).assign(
                        Region=lambda df: df['Country'].apply(lambda x: 'Global South' if x in global_south_countries else 'Global North'),
                        Percent_Contributors=lambda df: df['Contributors'] / df['Contributors'].sum() * 100
                    ),
                    locations="Country",
                    locationmode="country names",
                    color="Region",
                    hover_name="Country",
                    hover_data={"Percent_Contributors": ":.2f"},
                    color_discrete_map={"Global South": "#aa96fa", "Global North": "#bee6b4"}
                ).update_traces(
                    marker=dict(line=dict(color="white")),
                    hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]:.2f}% of all contributors<extra></extra>"
                ).update_layout(
                    hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"),
                    geo=dict(
                        showcoastlines=False,
                        showcountries=True,
                        countrycolor="white",
                        landcolor="lightgray",
                        bgcolor="#FAFAFA",
                        framewidth=0
                    ),
                    dragmode=False,
                    margin={"r": 0, "t": 0, "l": 0, "b": 0},
                    font=dict(color="#a9a9a9",
                                    family="Arial"),
                    plot_bgcolor="#FAFAFA",
                    paper_bgcolor = "#FAFAFA"
                ),
                style={"height": "400px"}
            )
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px",
                  "backgroundColor": "#FAFAFA"}),

        # Range of Expertise and Involvement Section
        html.Hr(style={"border": "1px solid #ccc", "margin": "20px 0"}),
        html.Div([
            html.P("Range of Expertise and Involvement", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.Div([    
                html.Div([
                    html.P("Contributors' Events By Country", 
                            style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                    html.P([
                        html.Span("Total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                        html.Span(f"{data['community']['total_members']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                        html.Span(" unique contributors.", style={"font-size": "12px", "color": "#a9a9a9"})
                    ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                    dcc.Graph(id="roles_community", figure=roles_fig)
                ]),
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px",
                  "backgroundColor": "#FAFAFA", "margin-bottom": "15px"}),
            html.Div([
                html.Div([
                    html.Div([
                        html.P("Duration of Involvement", 
                            style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                        html.P([
                            html.Span("Short-term and long-term commitments welcome.", style={"font-size": "12px", "color": "#a9a9a9"}),
                        ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                        dcc.Graph(id="duration_community", figure=duration_fig)
                    ])
                ], style={"border": "1px solid #ddd", "border-radius": "10px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px",
                      "margin-right": "1%", "width": "49%", "display": "inline-block", "padding": "25px"}),
                html.Div([
                    html.Div([
                        html.P("Volunteers by Organization", 
                            style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                        html.P([
                            html.Span("Total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                            html.Span(f"{data['organization']['total_organizations']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                            html.Span(" organisations.", style={"font-size": "12px", "color": "#a9a9a9"})
                        ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                        dcc.Graph(id="organization_pie_community", figure=org_pie_fig)
                    ])
                ], style={"border": "1px solid #ddd", "border-radius": "10px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px",
                      "width": "49%", "display": "inline-block", "padding": "25px"})
            ])
        ]),

        # Active Knowledge Sharing
        html.Hr(style={"border": "1px solid #ccc", "margin": "20px 0"}),
        html.P("Active Knowledge Sharing", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "4px"}),
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
                html.Div([
                    html.P("Distribution Of Blog Post Topics", 
                            style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                        html.P([
                            html.Span("Topics align with health needs and research priorities in the Global South.", style={"font-size": "12px", "color": "#a9a9a9"}),
                        ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                    dcc.Graph(id="blogpost_topics_fig", figure=blogposts_topics_fig)
                ])
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-right": "1%",
                "backgroundColor": "#FAFAFA", "width": "49%", "display": "inline-block"}),
            html.Div([
                html.Div([
                    html.P("Blog Posts Over Time", 
                        style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                    html.P([
                            html.Span("Total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                            html.Span(f"{data['blogposts-events']['total_blogposts']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                            html.Span(" blog posts.", style={"font-size": "12px", "color": "#a9a9a9"})
                        ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                    dcc.Graph(id="blogposts_over_time", figure=blogposts_time_fig)
                ])
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px",
                "backgroundColor": "#FAFAFA", "width": "49%", "display": "inline-block"})
        ])
    ], style={"margin-left": "320px", "padding": "20px"})