import dash
from dash import dcc
from dash import html
import plotly.express as px

import pandas as pd

import scripts.calculate_stats as calc
import scripts.dataset_references as ref

import requests

# Load data from JSON
data_url = "https://github.com/ersilia-os/ersilia-stats/raw/refs/heads/mvp2.1/reports/tables_stats.json"
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

def events_publications_page():
    # Extract the 'events_by_year' data from the JSON
    events_by_year = pd.DataFrame(data["events"]["events_by_year"])

    # Generate a bar plot for events by year
    events_fig = px.bar(
        events_by_year,
        x="Year",
        y="Count",
        barmode="group",
        color_discrete_sequence=["#aa96fa"],  # Purple for bars
    )

    # Update axes and layout
    events_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Year")
    events_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Events")
    events_fig.update_layout(
        font=dict(color="#a9a9a9",
                  family="Arial"),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor="#FAFAFA",
        plot_bgcolor="#FAFAFA",
        hoverlabel=dict(
            bgcolor="black"
        )
    )
    events_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} publications<extra></extra>",
        marker=dict(line=dict(color="white"))
    )

    events_by_type = pd.DataFrame(data["events"]["events_by_type"])
    events_by_type_fig = px.pie(
        events_by_type, 
        names="Type", 
        values="Count",
        color="Type",
        color_discrete_sequence=["#aa96fa", "#8cc8fa", "#dca0dc","#faa08c", "#fad782", "#bee6b4"],  # Custom colors  
    )

    events_by_type_fig.update_traces(
        customdata=events_by_type[["Percentage", "Count"]],
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br> %{customdata[0][1]}<extra></extra> (%{customdata[0][0]:.2f}%)",
        textposition='inside'
    )
    events_by_type_fig.update_layout(uniformtext_minsize=50, uniformtext_mode='hide')

    events_by_type_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        legend=dict(
            font=dict(size=14),
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

    publication_data = data["publications"]
    publication_by_year = pd.DataFrame(publication_data['publications_by_year'])
    total_publications = publication_data["total_publications"]

    publication_by_year['Year'] = publication_by_year['Year'].apply(lambda x: 'Before 2020' if x < 2020 else str(x))
    publication_by_year = publication_by_year.groupby('Year').agg({'Count': 'mean'}).reset_index()
    publication_by_year = publication_by_year.sort_values(by="Year", key=lambda x: x.apply(lambda y: '0' if y == 'Before 2020' else y), ascending=True)

    publications_by_year_fig = px.line(publication_by_year, 
                                       x="Year", 
                                       y="Count",
                                       color_discrete_sequence=["#aa96fa"])
    publications_by_year_fig.update_xaxes(linecolor='lightgrey', gridcolor='#FAFAFA', title_text="Year")
    publications_by_year_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Publications")
    publications_by_year_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        plot_bgcolor="#FAFAFA"
    )
    publications_by_year_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} publications<extra></extra>",
        marker=dict(line=dict(color="white"))
    )

    publication_status_distribution = pd.DataFrame(publication_data['status_distribution'])
    total_count = publication_status_distribution['count'].sum()
    publication_status_distribution['Percentage'] = (publication_status_distribution['count'] / total_count) * 100

    publication_status_distribution_fig = px.pie(
        publication_status_distribution, 
        names="Count", 
        values="count", 
        color_discrete_sequence=["#aa96fa", "#bee6b4"]
    )
    publication_status_distribution_fig.update_traces(
        customdata=publication_status_distribution["Percentage"],  # Add custom percentage data
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>%{value} (%{customdata:.3f}%)<extra></extra>",
        textposition = 'inside'
    )
    publication_status_distribution_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), uniformtext_minsize=50, uniformtext_mode='hide')

    publication_status_distribution_fig.update_layout(
        legend=dict(
            font=dict(size=14),  # Reduce legend font size
            xanchor="right",
            x=1.56,
            yanchor="middle",
            y=0.5
        ),
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        plot_bgcolor="#FAFAFA"
    )

    citations_by_year = pd.DataFrame(publication_data['citations_by_year'])
    total_citations = publication_data['total_citations']

    citations_fig = px.bar(
        citations_by_year, 
        x="Year", 
        y="total_citations", 
        color_discrete_sequence=["#aa96fa"]
    )
    citations_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Year", dtick=1)
    citations_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Citations", dtick=100)
    citations_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA"
    )
    citations_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} citations<extra></extra>",
        marker=dict(line=dict(color="white"))
    )

    publications_by_topic = pd.DataFrame(publication_data['publications_by_topic'])
    publications_by_topic = publications_by_topic.sort_values(by="Count", ascending=False)

    publications_by_topic_fig = px.bar(
        publications_by_topic, 
        x="Topic", 
        y="Count", 
        color_discrete_sequence = ["#aa96fa"]
    )
    publications_by_topic_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Topic")
    publications_by_topic_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Publications")
    publications_by_topic_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA"
    )
    publications_by_topic_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} publications<extra></extra>",
        marker=dict(line=dict(color="white")),
    )

    publication_affiliations_by_year = pd.DataFrame(publication_data['affiliation_counts_by_year'])
    publication_affiliations_by_year = publication_affiliations_by_year.sort_values(by="Year", ascending=True)
    # Melt the DataFrame to long format
    publication_affiliations_by_year_long = publication_affiliations_by_year.melt(
        id_vars="Year", 
        var_name="Affiliation", 
        value_name="Count"
    )

    # Rename variables in the "Affiliation" column
    publication_affiliations_by_year_long["Affiliation"] = publication_affiliations_by_year_long["Affiliation"].replace({
        "Non-Ersilia Affiliation": "non-affiliated",
        "Ersilia Affiliation": "affiliated"
    })

    # Create the bar chart
    custom_colors = {
        "non-affiliated": "#bee6b4", 
        "affiliated": "#aa96fa"
    }

    publication_affiliations_by_year_fig = px.bar(
        publication_affiliations_by_year_long,
        x="Year",
        y="Count",
        color="Affiliation",
        labels={'Affiliation': "Affiliation w/ Ersilia"},
        hover_data={'Affiliation': True, 'Count': True, 'Year': True},
        barmode="group",
        color_discrete_map = custom_colors
    )
    publication_affiliations_by_year_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Year", dtick=1)
    publication_affiliations_by_year_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Count")
    publication_affiliations_by_year_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        legend=dict(
            font=dict(size=10),  # Reduce legend font size
            xanchor="right",
            x=1,
            yanchor="top",
            y=1.3
        ),
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FAFAFA"
    )
    publication_affiliations_by_year_fig.update_traces(
        marker=dict(line=dict(color="white")),
        hovertemplate="%{y} <b>%{fullData.name}</b> events in %{x}<extra></extra>"
    )

    top_external_collaborators = pd.DataFrame(publication_data['non_ersilia_authors_by_frequency']).head(9)

    top_external_collaborators_fig = px.bar(
        top_external_collaborators, 
        x="author", 
        y="count", 
        color_discrete_sequence=["#aa96fa"]
    )
    top_external_collaborators_fig.update_xaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Author")
    top_external_collaborators_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Publications")
    top_external_collaborators_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA",
        font=dict(color="#a9a9a9",
                  family="Arial"),
        xaxis_tickangle=-40,
        plot_bgcolor="#FAFAFA"
    )
    top_external_collaborators_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} publications<extra></extra>",
        marker=dict(line=dict(color="white"))
    )

    events_by_country = pd.DataFrame(data["events"]["events_by_country"])
    events_by_country["Count"] = events_by_country["Organisers"].apply(lambda x: len(x))
    # Preprocess organisers to concatenate them into a single string with line breaks
    def truncate_organisers(x):
        if len(x) > 5:
            x = x[0:5]
            return "<br>".join(set(x)) + " <br><i>and others</i>..."
        else:
            return "<br>".join(set(x))
        
    events_by_country["Organisers"] = events_by_country["Organisers"].apply(lambda x: truncate_organisers(x))

    events_by_country_map = px.choropleth(
        events_by_country.assign(
            Region=lambda df: df['Country'].apply(lambda x: 'Global South' if x in global_south_countries else 'Global North'),
            Percent_Events=lambda df: df['Count'] / df['Count'].sum() * 100
        ),
        locations="Country",
        locationmode="country names",
        color="Region",
        hover_name="Country",
        hover_data={"Percent_Events": ":.2f", "Organisers": True, "Count": True},
        color_discrete_map={"Global South": "#aa96fa", "Global North": "#bee6b4"}
    ).update_traces(
        marker=dict(line=dict(color="white")),
        hovertemplate="<b>%{hovertext}</b><br>%{customdata[2]} events (%{customdata[0]:.2f}%) organised by: <br>" +
                  "%{customdata[1]}<extra></extra>"
    ).update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
        geo=dict(
            showcoastlines=False,
            showcountries=True,
            countrycolor="white",
            landcolor="lightgray",
            bgcolor="#FAFAFA",
            framewidth=0
        ),
        dragmode = False,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        font=dict(color="#a9a9a9",
                  family="Arial"),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FAFAFA"
    )

    return html.Div([
        # Header Section
        html.Div([
            html.P("Events & Publications", 
                   style={"font-size": "30px", "font-weight": "bold", "margin-bottom": "20px"}),
        ]),

        # Events Section
        html.P("Events", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "10px"}),
        html.Div([
            html.Div([
                html.P("Event Distribution By Year", style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "10px"}),
                dcc.Graph(id="roles_community", figure=events_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px",
                      "margin-right": "1%", "width": "49%", "display": "inline-block", "padding": "25px"}),
            html.Div([
                html.P("Event Breakdown By Types", style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "10px"}),
                dcc.Graph(id="events_by_type", figure=events_by_type_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px",
                      "width": "49%", "display": "inline-block", "padding": "25px"})
        ], style={"display": "flex", "justify-content": "space-between"}),

        html.Div([
            html.P("Contributors' Events By Country", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.P([
                html.Span("A total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                html.Span(f"{data['events']['total_events']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                html.Span(" were organised by ", style={"font-size": "12px", "color": "#a9a9a9"}),
                html.Span(f"{len(data['events']['events_by_country'])}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                html.Span(" countries.", style={"font-size": "12px", "color": "#a9a9a9"})
            ], style={"line-height": "1.6", "margin-bottom": "10px"}),
            html.P(f"*Global South: Africa, Latin America and the Caribbean, Asia (excluding Israel, Japan, and South Korea), and Oceania (excluding Australia and New Zealand).", 
                   style={"font-size": "12px", "color": "#a9a9a9", "margin-bottom": "10px"}),
            dcc.Graph(
                id="events_by_country_map",
                figure=events_by_country_map,
                style={"height": "400px"}
            )
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px"}),

        # Publications Section
        html.Hr(style={"border": "1px solid #aaa", "margin": "20px 0"}),  # Horizontal line
        html.P("Publications", style={"font-size": "22px", "font-weight": "bold", "margin-bottom": "10px"}),
        html.Div([
            html.Div([
                html.P("Timeline of Publications", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
            html.P([
                html.Span("A total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                html.Span(f"{data['publications']['total_publications']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                html.Span(" publications.", style={"font-size": "12px", "color": "#a9a9a9"}),
            ], style={"line-height": "1.6", "margin-bottom": "10px"}),
                dcc.Graph(id="publications_by_year", figure=publications_by_year_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "49%", "display": "inline-block"}),
            html.Div([
                html.P("Timeline of Citations", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                html.Span("A total of ", style={"font-size": "12px", "color": "#a9a9a9"}),
                html.Span(f"{data['publications']['total_citations']}", style={"font-size": "12px", "color": "#6A1B9A", "font-weight": "bold"}),
                html.Span(" citations.", style={"font-size": "12px", "color": "#a9a9a9"}),
                dcc.Graph(id="citations_by_year", figure=citations_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "49%", "display": "inline-block"})
        ], style={"display": "flex", "justify-content": "space-between"}),

        html.Div([
            html.Div([
                html.P("Collaborations w/ Ersilia vs. Independent Research", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                html.Span("Ersilia was established in 2020.", style={"font-size": "12px", "color": "#a9a9a9"}),
                dcc.Graph(id="publication_affiliations_by_year", figure=publication_affiliations_by_year_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "49%", "display": "inline-block"}),
            html.Div([
                html.P("Number of Publications By Topic Area", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                dcc.Graph(id="publications_by_topic", figure=publications_by_topic_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "49%", "display": "inline-block"})
        ], style={"display": "flex", "justify-content": "space-between"}),

        html.Div([
            html.Div([
                html.P("Distribution of Organisations", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                dcc.Graph(id="publications_status_distribution", figure=publication_status_distribution_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "40%", "display": "inline-block"}),
            html.Div([
                html.P("Top External Collaborators With Ersilia", 
                   style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "4px"}),
                dcc.Graph(id="top_external_collaborators", figure=top_external_collaborators_fig)
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "backgroundColor": "#FAFAFA", "margin-bottom": "20px", "width": "58%", "display": "inline-block"})
        ], style={"display": "flex", "justify-content": "space-between"})
    ], style={"margin-left": "320px", "padding": "20px"})
