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
        color_discrete_sequence=["#aa96fa"]  # Purple for bars
    )

    # Update axes and layout
    events_fig.update_xaxes(title_text="Year")
    events_fig.update_yaxes(title_text="Number of Events")
    events_fig.update_layout(
        title={
            "text": "Event Distribution Over Time By Year",
        },
        margin=dict(t=50, b=50, l=50, r=50),  # Adjust margins to expand the plot area
        paper_bgcolor="#FAFAFA"
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
        customdata=events_by_type[["Percentage", "count"]],
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>" +
                    "Percentage: %{customdata[0][0]:.2f}%<br>" +
                    "Count: %{customdata[0][1]}<extra></extra>",
        textposition='inside'
    )
    events_by_type_fig.update_layout(uniformtext_minsize=50, uniformtext_mode='hide')

    events_by_type_fig.update_layout(
        title={
            "text": "Events Breakdown by Types<br><sup>Highlights from a diverse range of events</sup>",
        },
        legend=dict(
            font=dict(size=7),  # Reduce legend font size
            orientation="h",  # Horizontal legend
        ),
        margin=dict(t=50, b=50, l=50, r=50),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA"
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
    publications_by_year_fig.update_xaxes(title_text="Year")
    publications_by_year_fig.update_yaxes(title_text="Number of Publications")
    publications_by_year_fig.update_layout(
        title={
            "text": f"Timeline of Publications Yearly<br><sup>Total of {total_publications} publications</sup>",
        },
        margin=dict(t=50, b=50, l=50, r=50),  # Adjust margins to expand the plot area
        paper_bgcolor = "#FAFAFA"
    )
    publications_by_year_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y} publications<extra></extra>",
        marker=dict(line=dict(color="white", width=0.5))
    )

    publication_status_distribution = pd.DataFrame(publication_data['status_distribution'])

    publication_status_distribution_fig = px.pie(publication_status_distribution, names="Count", values="count", title="Publication Status Distribution")

    citations_by_year = pd.DataFrame(publication_data['citations_by_year'])

    citations_fig = px.bar(citations_by_year, x="Year", y="total_citations", title="Citations Over Time")
    citations_fig.update_xaxes(title_text="Year")
    citations_fig.update_yaxes(title_text="Citations")

    publications_by_topic = pd.DataFrame(publication_data['publications_by_topic'])
    publications_by_topic = publications_by_topic.sort_values(by="Count", ascending=False)

    publications_by_topic_fig = px.bar(publications_by_topic, x="Topic", y="Count", title="Publications By Topic Area")
    publications_by_topic_fig.update_xaxes(title_text="Topic")
    publications_by_topic_fig.update_yaxes(title_text="Number of Publications")

    publication_affiliations_by_year = pd.DataFrame(publication_data['affiliation_counts_by_year'])
    publication_affiliations_by_year = publication_affiliations_by_year.sort_values(by="Year", ascending=True)

    publication_affiliations_by_year_fig = px.bar(
        publication_affiliations_by_year,
        x="Year",
        y=["Non-Ersilia Affiliation", "Ersilia Affiliation"],
        barmode="group",
        title="Publication Affiliations By Year"
    )
    publication_affiliations_by_year_fig.update_xaxes(title_text="Year", dtick=1)
    publication_affiliations_by_year_fig.update_yaxes(title_text="Count")


    top_external_collaborators = pd.DataFrame(publication_data['non_ersilia_authors_by_frequency']).head(9)

    top_external_collaborators_fig = px.bar(top_external_collaborators, x="author", y="count", title="Top External Collaborators")
    top_external_collaborators_fig.update_xaxes(title_text="Author")
    top_external_collaborators_fig.update_yaxes(title_text="Number of Publications")

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
        marker=dict(line=dict(color="white", width=1)),
        hovertemplate="<b>%{hovertext}</b><br>" +
                  "Events: %{customdata[0]:.2f}%<br>" +
                  "Count: %{customdata[2]}<br>" +
                  "Organisers:<br>%{customdata[1]}<extra></extra>"
    ).update_layout(
        geo=dict(
            showcoastlines=False,
            showcountries=True,
            countrycolor="white",
            landcolor="lightgray"
        ),
        dragmode = False,
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    total_events = events_by_country["Count"].sum()
    total_countries = events_by_country["Country"].nunique()

    return html.Div([
        # Header Section
        html.P("Events & Publications", style={"font-size": "24px", "font-weight": "bold", "text-align": "center", "margin-bottom": "20px"}),

        # Events Section
        html.P("Events", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            html.Div([
                dcc.Graph(id="roles_community", figure=events_fig),
            ], style={"width": "48%", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                dcc.Graph(id="events_by_type", figure=events_by_type_fig),
            ], style={"width": "48%", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"display": "flex", "justify-content": "space-between"}),

        
        html.Div([
            # Country Buttons
            html.P(f"A total of {total_events} events were organized by {total_countries} countries.", style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "10px"}),
            html.P(f"*Global South: Africa, Latin America and the Caribbean, Asia (excluding Israel, Japan, and South Korea), and Oceania (excluding Australia and New Zealand).", style={"font-size": "12px", "margin-bottom": "10px"}),
            # Map visualization
            dcc.Graph(
                id="events_by_country_map",
                figure=events_by_country_map,
                style={"height": "400px"}
            )
        ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px"}),

        # Publications Section
        html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),
        html.P("Publications", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.Div([
            html.Div([
                dcc.Graph(id="publications_by_year", figure=publications_by_year_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
            html.Div([
                dcc.Graph(id="citations_by_year", figure=citations_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"display": "flex", "flex-wrap": "wrap", "justify-content": "space-between"}),

        html.Div([
            html.Div([
                dcc.Graph(id="publication_affiliations_by_year", figure=publication_affiliations_by_year_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "margin-right": "2%"}),            
            html.Div([
                dcc.Graph(id="publications_by_topic", figure=publications_by_topic_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"}),
        ], style={"display": "flex", "justify-content": "space-between"}),

        html.Div([
            html.Div([
                dcc.Graph(id="publications_status_distribution", figure=publication_status_distribution_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block", "margin-right": "2%"}),
            html.Div([
                dcc.Graph(id="top_external_collaborators", figure=top_external_collaborators_fig, style={"height": "400px"}),
            ], style={"width": "48%", "height": "500px", "border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "margin-bottom": "20px", "display": "inline-block"})
        ], style={"display": "flex", "justify-content": "space-between"})
    ], style={"margin-left": "320px", "padding": "20px", "font-family": "Arial, sans-serif"})
