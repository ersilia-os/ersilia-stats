import dash
from dash import dcc, dash_table
from dash import html, Input, Output, State, callback
import plotly.express as px
import requests
import pandas as pd

# Register page
dash.register_page(__name__, path="/models-impact")

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
# ---- Model Status Pie chart ----
model_status_data = pd.DataFrame(data["models-impact"]["model_distribution"])

threshold = 0.8  # Percentage threshold
total_count = model_status_data["Count"].sum()

# Add a percentage column
model_status_data["Percentage"] = (model_status_data["Count"] / total_count) * 100

# Identify main categories and "Other" categories
main_categories = model_status_data[model_status_data["Percentage"] >= threshold]
other_categories = model_status_data[model_status_data["Percentage"] < threshold]

# Combine "Other" categories into a single row
if not other_categories.empty:
    other_row = pd.DataFrame({
        "Category": ["Other (tags w/ <4 models)"],
        "Count": [other_categories["Count"].sum()],
        "Percentage": [other_categories["Percentage"].sum()]
    })
    model_status_data = pd.concat([main_categories, other_row], ignore_index=True)

# Create the donut chart
model_status_fig = px.pie(
    model_status_data, 
    values="Count", 
    names="Category",  
    color="Category",
    color_discrete_sequence=["#aa96fa", "#8cc8fa", "#dca0dc","#faa08c", "#fad782", "#bee6b4", "#d2d2d0"],  # Custom colors  
    hole=0.5  # Donut chart
)

# Add custom data and hover template
model_status_fig.update_traces(
    customdata=model_status_data[["Percentage", "Count"]],
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>%{customdata[0][1]}<extra></extra> (%{customdata[0][0]:.2f}%)",
    textposition = 'inside'
)

# Update layout to style the chart
model_status_fig.update_layout(
    annotations=[
        dict(
            text=f"<b>{data['models-impact']['total_models']:,}</b> total models<br>",  # Total number in the center
            x=0.5, y=0.52, font=dict(color="#6A1B9A", size=18), showarrow=False
        ),
        dict(
            text=f"<sup><b>{data['models-impact']['ready_percentage']}%</b> ready for immediate usage </sup>",  # Total number in the center
            x=0.5, y=0.48, font=dict(color="#a9a9a9", size=18), showarrow=False
        )
    ],
    hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"),
    showlegend=False,  # Remove the legend
    font=dict(color="black", family="Arial"),
    margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
    paper_bgcolor="#FAFAFA",
    plot_bgcolor="#FAFAFA",
)

model_status_fig.update_layout(uniformtext_minsize=50, uniformtext_mode='hide')


# ---- Models by Year line chart ----
model_year_data = pd.DataFrame(data["models-impact"]["models_per_year"])
model_year_data = model_year_data.sort_values(by="Year", key=lambda x: x.apply(lambda y: '0' if y == 'Before 2018' else y), ascending=True)

model_year_data_fig = px.line(model_year_data, 
                                    x="Year", 
                                    y="Count",
                                    color_discrete_sequence=["#aa96fa"])

model_year_data_fig.update_xaxes(linecolor='lightgrey', gridcolor='#FAFAFA', title_text="Year")
model_year_data_fig.update_yaxes(linecolor='lightgrey', gridcolor='lightgrey', title_text="Number of Publications")
model_year_data_fig.update_layout(hoverlabel=dict(bgcolor="black", font_size=16, font_family="Arial"), 
    margin=dict(t=0, b=0, l=0, r=0),  # Adjust margins to expand the plot area
    paper_bgcolor = "#FAFAFA",
    font=dict(color="#a9a9a9",
                family="Arial"),
    plot_bgcolor="#FAFAFA"
)
model_year_data_fig.update_traces(
    hovertemplate="<b>%{x}</b><br>%{y} models<extra></extra>",
    marker=dict(line=dict(color="white"))
)

# --- Data Table --- #
# Preprocess Data Function
def preprocess_data(input_data):
    model_list_data = pd.DataFrame(input_data).to_dict("records")

    for row in model_list_data:
        if not isinstance(row.get("Tag"), str):
            row["Tag"] = "None"

    # Define the color sequence for tags
    tag_colors = ["#aa96fa", "#8cc8fa", "#dca0dc", "#faa08c", "#fad782", "#bee6b4"]

    # Define the color mapping for Status
    status_colors = {
        "Ready": "#bee6b4",  # Green
        "Archived": "#d2d2d0",  # Gray
        "Test": "#d2d2d0",  # Gray
        "To do": "#faa08c",  # Red
        "In progress": "#fad782",  # Yellow
    }

    # Flatten and extract all tags for unique mapping
    all_tags = {
        tag.strip()
        for row in model_list_data
        for tag in row.get("Tag", "").replace("[", "").replace("]", "").replace("'", "").split(", ")
        if tag.strip()
    }
    color_map = {tag: tag_colors[i % len(tag_colors)] for i, tag in enumerate(sorted(all_tags))}

    for row in model_list_data:
        # Create href link for the title
        if isinstance(row['GitHub'], str):
            row["Title"] = f"<a href={row['GitHub']} target='_blank'>{row['Title']}</a>"

        # Process tags and assign colors
        tags = row["Tag"].replace("[", "").replace("]", "").replace("'", "").split(", ")

        # Create styled HTML tags
        styled_tags = [
            f'<span style="background-color:{color_map[tag.strip()]}; color:white; padding:2px 5px; border-radius:5px; margin-right:5px; margin-bottom:10px;">{tag.strip()}</span>'
            for tag in tags[:2]
        ]

        # Add ellipsis if there are more than 2 tags
        if len(tags) > 2:
            styled_tags.append('<span style="color:#888; font-style:italic;">...</span>')

        row["Tag"] = "<br>".join(styled_tags)  # Join styled tags with spaces

        # Tooltip for full list of tags
        row["Tag_Hover"] = ", ".join(tags)

        # Process Status
        status = row.get("Status", "Unknown").strip()
        row["Status"] = f'<span style="background-color:{status_colors.get(status, "#d2d2d0")}; color:black; padding:2px 5px; border-radius:5px; text-align:center; font-weight:bold;">{status}</span>'

    return model_list_data

layout = html.Div([
    dcc.Store(id="processed-data", data=preprocess_data(data["models-impact"]["model_list"])),
    dcc.Store(id="filtered-data"),

    # Header Section
    html.Div([
        html.P("Models' Impact", 
                style={"width": "50%", "display": "inline-block", "vertical-align": "top", "padding-right": "20px", "padding-top": "20px",
                        "font-size": "24px", "font-weight": "bold"}),
        html.Div([
            dcc.Dropdown(
                id="disease-dropdown",
                options=[{"label": disease["disease"].replace("_", " ").title(), "value": disease["disease"]} for disease in data["external_data"]["disease_statistics"]],
                multi=True,
                placeholder="Select Diseases",
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
                html.Span("In the Global South, there have been ", style={"color": "#a9a9a9", "font-size": "12px"}),
                html.Span(f"{data['external_data']['total_cases']:,}", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}),  # Placeholder for total cases
                html.Span(" cases of severe diseases, and ", style={"color": "#a9a9a9", "font-size": "12px"}),
                html.Span(f"{data['external_data']['total_deaths']:,}", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}),  # Placeholder for total deaths
                html.Span(" deaths as a result.", style={"color": "#a9a9a9", "font-size": "12px"}),
            ], style={"line-height": "1.6", "margin-bottom": "20px"}),
            html.P(" NOTE: measles/polio deaths were unable to be accessed programmatically, and as such display as 0.", style={"color": "#a9a9a9", "font-size": "12px", "margin-bottom": "4px"}),
            html.Div([
                html.Div([
                    html.P(id="all-disease-cases", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),  # Dynamic label for cases
                    html.P(id="total-cases-text", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"})  # Dynamic total cases
                ], style={"padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-bottom": "10px"}),
                html.Div([
                    html.P(id="all-disease-deaths", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),  # Dynamic label for deaths
                    html.P(id="total-deaths-text", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"})  # Dynamic total deaths
                ], style={"padding": "10px", "border": "1px solid #ddd", "border-radius": "10px"})
            ])
        ], style={"width": "40%", "display": "inline-block", "vertical-align": "top", "padding-right": "20px"}),

        # Right Column: Dropdown and Map
        html.Div([
            html.Div([
                dcc.Graph(id="disease-map",
                          style={"height": "400px"})  # Choropleth map placeholder
            ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px"})
        ], style={"width": "60%", "display": "inline-block", "vertical-align": "top"})
        ], style={"display": "flex", "justify-content": "space-between", "margin-bottom": "20px"}),


    # Divider
    html.Hr(style={"border": "1px solid #ddd", "margin": "20px 0"}),

    # Ersilia's Models Section
    html.Div([
        html.P("Ersilia's Models", style={"font-size": "16px", "font-weight": "bold", "margin-bottom": "4px"}),
        html.P([
                html.Span("To address the challenges above, Ersilia has developed ", style={"color": "#a9a9a9", "font-size": "12px"}),
                html.Span(str(data["models-impact"]["total_models"]) +  " models", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                html.Span(" each designed with diverse applications in mind.", style={"color": "#a9a9a9", "font-size": "12px"}),
            ], style={"line-height": "1.6", "margin-bottom": "20px"}),
    ]),

    # Visualization Section
    html.Div([
        # Model Status Donut Chart
        html.Div([
            html.P("Model Distribution", 
                style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "8px"}),

            dcc.Graph(id="model_status", figure=model_status_fig)
        ], style={
            "width": "49%", 
            "display": "inline-block", 
            "padding": "10px", 
            "border": "1px solid #ddd", 
            "border-radius": "10px", 
            "margin-right": "1%", 
            "backgroundColor": "#FAFAFA"
        }),

        # Model Year Data Line Chart
        html.Div([
            html.P("Models per Year", 
                style={"font-size": "14px", "font-weight": "bold", "margin-bottom": "8px"}),
            dcc.Graph(id="model_year_data", figure=model_year_data_fig)
        ], style={
            "width": "49%", 
            "display": "inline-block", 
            "padding": "10px", 
            "border": "1px solid #ddd", 
            "border-radius": "10px", 
            "backgroundColor": "#FAFAFA"
        })
    ], style={
        "display": "flex", 
        "justify-content": "space-between", 
        "align-items": "center", 
        "margin-bottom": "20px"
    }),

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
    dash_table.DataTable(
        id="models-impact-table",
        columns=[
            {"name": "Title", "id": "Title", "type": "text", "presentation": "markdown", "deletable": False, "selectable": False},
            {"name": "Tag", "id": "Tag", "type": "text", "presentation": "markdown", "deletable": False, "selectable": False},
            {"name": "Contributor", "id": "Contributor", "deletable": False, "selectable": False},
            {"name": "Incorporation Date", "id": "Incorporation Date", "deletable": False, "selectable": False},
            {"name": "Status", "id": "Status", "type": "text", "presentation": "markdown", "deletable": False, "selectable": False},
        ],
        data=[],  # Dynamically filled via callback
        page_size=5,
        sort_action="native",
        style_table={"overflowX": "auto", "border": "none"},
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "whiteSpace": "pre-line",
            "height": "70px",
            "fontSize": "14px",
        },
        style_cell_conditional=[
            {
                "if": {"column_id": "Title"},
                "width": "450px",
                "text-align": "center",  # Center horizontally
                "vertical-align": "middle",  # Center vertically
                "fontFamily": "monospace",  # Optional: Use monospace font
            },
            {"if": {"column_id": "Tag"}, "width": "300px"},
            {"if": {"column_id": "Contributor"}, "width": "200px"},
            {"if": {"column_id": "Incorporation Date"}, "width": "100px"},
            {"if": {"column_id": "Status"}, "width": "100px"},
        ],
        tooltip_data=[],  # Dynamically filled via callback
        tooltip_duration=None,
        css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: black; font-family: arial; color: white',
            },
            {    
                "selector": "p", 
                "rule": "vertical-align: middle"
            }],
        style_as_list_view=True,
        cell_selectable=False,
        markdown_options={"html": True},
    ),  # Embed the DataTable directly as a child
], style={"margin-left": "320px", "padding": "20px"})

# Table update callback
@callback(
    [
        Output("models-impact-table", "data"),
        Output("models-impact-table", "tooltip_data"),
    ],
    [
        Input("processed-data", "data"),
        Input("search-bar", "value"),
    ]
)
def update_table(processed_data, search_value):
    # Start with the processed data
    df = pd.DataFrame(processed_data)

    # Filter data based on search value
    if search_value:  # If search input exists, filter the rows
        df = df[
            df.apply(
                lambda row: row.astype(str).str.contains(search_value, case=False).any(),
                axis=1,
            )
        ]

    # Create tooltip data dynamically
    tooltip_data = [
        {"Tag": {"value": row.get("Tag_Hover", ""), "type": "markdown"}} for row in df.to_dict("records")
    ]

    return df.to_dict("records"), tooltip_data


@callback(
    [
        Output("total-cases-text", "children"),
        Output("total-deaths-text", "children"),
        Output("all-disease-cases", "children"),
        Output("all-disease-deaths", "children"),
        Output("filtered-data", "data"),
    ],
    [
        Input("disease-dropdown", "value")
    ]
)
def update_stats_and_data(selected_diseases):
    # Access the disease statistics from external_data
    disease_statistics = data["external_data"]["disease_statistics"]

    # Default to all diseases if none are selected
    if not selected_diseases:
        selected_diseases = [disease["disease"] for disease in disease_statistics]
        disease_label = "All Diseases"
    else:
        # Generate a concise label for selected diseases
        if len(selected_diseases) == 1:
            disease_label = selected_diseases[0].replace("_", " ").title()
        else:
            disease_label = f"{selected_diseases[0].replace('_', ' ').title()} + {len(selected_diseases) - 1} more"

    # Initialize totals and prepare filtered data
    total_cases = 0
    total_deaths = 0
    filtered_data = []

    # Iterate over the diseases and aggregate data for selected ones
    for disease in disease_statistics:
        if disease["disease"] in selected_diseases:
            # Aggregate global totals
            total_cases += disease.get("total_cases", 0)
            total_deaths += disease.get("total_deaths", 0)

            # Add detailed disease data to filtered_data
            filtered_data.append({
                "disease": disease["disease"],
                "total_cases": disease.get("total_cases", 0),
                "total_deaths": disease.get("total_deaths", 0),
                "country_statistics": disease.get("country_statistics", {})
            })

    # Format numbers with commas for display
    total_cases_str = f"{total_cases:,}"
    total_deaths_str = f"{total_deaths:,}"

    # Update labels for cases and deaths
    disease_cases_label = f"{disease_label} Cases"
    disease_deaths_label = f"{disease_label} Deaths"

    return total_cases_str, total_deaths_str, disease_cases_label, disease_deaths_label, filtered_data


import pycountry

# Helper function to convert country names to 3-letter ISO codes
def regularize_country(country_name):
    try:
        # Try to convert to ISO 3-letter code
        return pycountry.countries.lookup(country_name).alpha_3
    except (KeyError, AttributeError, LookupError):
        # If no match is found, return the original country name
        return country_name

@callback(
    Output("disease-map", "figure"),
    Input("filtered-data", "data")
)
def update_map(filtered_data):
    # Step 1: Aggregate data for all countries (without regularizing)
    country_stats = {}
    for disease in filtered_data:
        for country, stats in disease.get("country_statistics", {}).items():
            # Ensure keys for cases and deaths are present and aggregate properly
            if country not in country_stats:
                country_stats[country] = {"cases": 0, "deaths": 0}
            country_stats[country]["cases"] += stats.get("cases", 0)
            country_stats[country]["deaths"] += stats.get("deaths", 0)

    # Debugging: Log unregularized country stats
    # print("Aggregated Country Statistics (Unregularized):", country_stats)

    # Step 2: Regularize country names
    regularized_stats = {}
    for country, stats in country_stats.items():
        standardized_country = regularize_country(country)  # Convert to ISO-3 code or standardize name
        if standardized_country not in regularized_stats:
            regularized_stats[standardized_country] = {"cases": 0, "deaths": 0}
        regularized_stats[standardized_country]["cases"] += stats["cases"]
        regularized_stats[standardized_country]["deaths"] += stats["deaths"]

    # Debugging: Log regularized country stats
    # print("Aggregated Country Statistics (Regularized):", regularized_stats)

    # Step 3: Convert to DataFrame for plotting
    df = pd.DataFrame.from_dict(regularized_stats, orient="index").reset_index()
    df.columns = ["Country", "Cases", "Deaths"]
    df["Total"] = df["Cases"] + df["Deaths"]

    # Debugging: Log DataFrame
    # print("DataFrame for Map:", df)

    # Step 4: Create the choropleth map
    fig = px.choropleth(
        df,
        locations="Country",
        locationmode="ISO-3",  # Use ISO-3 codes for matching
        color="Total",
        hover_name="Country",
        hover_data={
            "Cases": True,
            "Deaths": True,
            "Total": True
        },
        color_continuous_scale=["#A9A9A9", "#6A1B9A"]  # Shades of purple
    )

    # Update layout and hover template
    fig.update_traces(
        marker=dict(line=dict(color="white")),
        hovertemplate="<b>%{hovertext}</b><br>Cases: %{customdata[0]:,}<br>Deaths: %{customdata[1]:,}<br>Total: %{z:,}<extra></extra>"
    )

    fig.update_layout(
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
        font=dict(color="#a9a9a9", family="Arial"),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FAFAFA"
    )

    return fig
