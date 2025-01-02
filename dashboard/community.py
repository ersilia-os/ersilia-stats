import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import scripts.dataset_references as ref
import scripts.calculate_stats as calc
import requests

# Load data from JSON
data_url = "https://raw.githubusercontent.com/ersilia-os/ersilia-stats/refs/heads/main/reports/tables_stats.json"
data = requests.get(data_url).json()

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
    duration_data = pd.DataFrame(calc.community_time_duration())
    if "values" in duration_data.columns:
        duration_data["values"] = duration_data["values"].astype(str)  # Convert intervals to strings

    # Replace raw intervals with meaningful labels
    duration_data["values"] = duration_data["values"].replace({
        "(0, 3]": "< 3 Months",
        "(3, 6]": "3-6 Months",
        "(6, 7]": "6-7 Months",
        "(7, 12]": "7-12 Months",
        "(12, 10000]": "> 1 Year"
    })

    # Sort categories meaningfully
    duration_data["values"] = pd.Categorical(
        duration_data["values"],
        categories=["< 3 Months", "3-6 Months", "7-12 Months", "> 1 Year"],
        ordered=True
    )

    # Add custom colors for bars
    duration_data["color"] = duration_data["values"].apply(
        lambda x: "#bee6b4" if x == "> 1 Year" else "#aa96fa"  # Green for > 1 Year, Purple otherwise
    )

    duration_fig = px.bar(
        duration_data, 
        x="values", 
        y="counts", 
        title="Duration of Involvement",
        color="color",  # Use the custom color column
        color_discrete_map="identity",  # Map colors directly from the column
        category_orders={"values": ["< 3 Months", "3-6 Months", "7-12 Months", "> 1 Year"]}  # Enforce order
    )

    duration_fig.update_layout(
        title={
            "text": "Duration of Involvement<br><sup>Short-term commitments and long-term roles welcome</sup>",
        }
    )

    duration_fig.update_xaxes(title_text="Duration of Involvement")
    duration_fig.update_yaxes(title_text="Number of Contributors")
    duration_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} contributors<extra></extra>",
        marker=dict(line=dict(color="white", width=0.5))
    )

    # Roles Plot
    roles_data = pd.DataFrame(data["community"]["role_distribution"])
    total_contributors = data["community"]["total_members"]

    roles_fig = px.bar(
        roles_data, 
        x="Role", 
        y="Count", 
        barmode="group", 
        title="Distribution of Roles",
        color_discrete_sequence=["#aa96fa"]  # Purple
    )

    roles_fig.update_layout(
        title={
            "text": f"Distribution of Roles<br><sup>Total of {total_contributors} unique contributors</sup>",
        }
    )

    roles_fig.update_xaxes(title_text="Role")
    roles_fig.update_yaxes(title_text="Number of Contributors")
    roles_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} contributors<extra></extra>",
        marker=dict(line=dict(color="white", width=0.5))
    )

    # Contributions by Organization Pie chart
    # Process organization type data
    org_types_data = pd.DataFrame(data["organization"]["organization_types"])
    total_types = org_types_data["Count"].sum()

    # Calculate percentage contributions
    org_types_data["Percentage"] = (org_types_data["Count"] / total_types) * 100

    # Pie chart
    org_pie_fig = px.pie(
        org_types_data, 
        values="Percentage", 
        names="Type", 
        title="Volunteers By Organization Type",
        color="Type",
        color_discrete_sequence=["#aa96fa", "#bee6b4", "#f5a623", "#4a90e2", "#ff6f61", "#e5e5e5", "#cccccc"]  # Custom colors
    )

    org_pie_fig.update_traces(textposition='inside')
    org_pie_fig.update_layout(uniformtext_minsize=24, uniformtext_mode='hide')

    # Update layout and tooltips
    org_pie_fig.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>%{value:.2f}%<extra></extra>"
    )
    org_pie_fig.update_layout(
        title={
            "text": "Volunteers By Organization Type<br><sup>A look into our {} supporters and collaborators</sup>".format(total_types),
        },
        legend=dict(
            title="Organization Types",
            orientation="v",
            x=1.1,
            y=1.0
        )
    )

     # Blogposts over time Plot
    blogposts_time_data = pd.DataFrame(data["blogposts-events"]["posts_per_year"])
    total_blogposts = data["blogposts-events"]["total_blogposts"]

    blogposts_time_fig = px.bar(
        blogposts_time_data, 
        x="Year", 
        y="Count", 
        barmode="group", 
        title="Distribution of Roles",
        color_discrete_sequence=["#aa96fa"]  # Purple
    )

    blogposts_time_fig.update_layout(
        title={
            "text": f"Distribution of Roles<br><sup>Total of {total_blogposts} blogposts.</sup>",
        }
    )

    blogposts_time_fig.update_xaxes(title_text="Year")
    blogposts_time_fig.update_yaxes(title_text="Number of Blogposts")
    blogposts_time_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} contributors<extra></extra>",
        marker=dict(line=dict(color="white", width=0.5))
    )



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
        html.Div([
            html.Div([
                html.P("Countries Represented", style={"text-align": "center", "font-size": "12px", "margin-bottom": "5px"}),
                html.P(str(data["community"]["countries_represented"]), 
                       style={"text-align": "center", "font-size": "24px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Unique Contributors", style={"text-align": "center", "font-size": "12px", "margin-bottom": "5px"}),
                html.P(str(data["community"]["total_members"]), 
                       style={"text-align": "center", "font-size": "24px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Organizations in Our Network", style={"text-align": "center", "font-size": "12px", "margin-bottom": "5px"}),
                html.P(str(data["organization"]["total_organizations"]), 
                       style={"text-align": "center", "font-size": "24px", "font-weight": "medium", "color": "#6A1B9A"})  # Placeholder: update if data available
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%"}),
            html.Div([
                html.P("Blog Posts", style={"text-align": "center", "font-size": "12px", "margin-bottom": "5px"}),
                html.P(str(data["blogposts-events"]["total_blogposts"]), 
                       style={"text-align": "center", "font-size": "24px", "font-weight": "medium", "color": "#6A1B9A"})
            ], style={"width": "22%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px"})
        ], style={"margin-bottom": "20px", "text-align": "center"}),

        # Global Representation Section
        html.P("Global Representation", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            # Graph header
            html.Div([
                html.P([
                    html.Span("Contributors By Country: ", style={"font-size": "14px", "font-weight": "bold"}),
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
                    marker=dict(line=dict(color="white", width=1)),
                    hovertemplate="<b>%{hovertext}</b><br>Contributors: %{customdata[0]:.2f}%<extra></extra>"
                ).update_layout(
                    geo=dict(
                        showcoastlines=False,
                        showcountries=True,
                        countrycolor="white",
                        landcolor="lightgray"
                    ),
                    margin={"r": 0, "t": 0, "l": 0, "b": 0}
                ),
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
                    dcc.Graph(id="duration_community", figure=org_pie_fig)
                ], style={"width": "48%", "display": "inline-block"}),
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