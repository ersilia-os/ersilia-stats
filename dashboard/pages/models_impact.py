import dash
from dash import dcc, dash_table
from dash import html
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
# ---- Table ---
model_list_data = pd.DataFrame(data["models-impact"]["model_list"])
# ---- Model Status Pie chart ----
model_status_data = pd.DataFrame(data["models-impact"]["model_distribution"])
total_models = model_status_data["Count"].sum()

# calc percentage contributions
model_status_data["Percentage"] = (model_status_data["Count"] / total_models) * 100

# df editing to limit tags to (max_tags_to_display)
max_tags_to_display=total_models

# get top 5 categories
top_categories = model_status_data.iloc[:max_tags_to_display]

# calc "Other" category
other_count = model_status_data.iloc[max_tags_to_display:]["Count"].sum()
other_percentage = model_status_data.iloc[max_tags_to_display:]["Percentage"].sum()

# add "Other" category to the top max_tags_to_display
other_row = pd.DataFrame([{"Category": "Other", "Count": other_count, "Percentage": other_percentage}])
model_status_data = pd.concat([top_categories, other_row], ignore_index=True)

# pie chart
model_status_fig = px.pie(
    model_status_data, 
    values="Count", 
    names="Category",  
    color="Category",
    color_discrete_sequence=["#aa96fa", "#8cc8fa", "#dca0dc","#faa08c", "#fad782", "#bee6b4", "#d2d2d0"],  # Custom colors  
)

model_status_fig.update_traces(
    customdata=model_status_data[["Percentage", "Count"]],
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>%{customdata[0][1]}<extra></extra> (%{customdata[0][0]:.2f}%)",
    textposition = 'inside'
)
model_status_fig.update_layout(uniformtext_minsize=50, uniformtext_mode='hide')

model_status_fig.update_layout(
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


layout = html.Div([
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
                html.Span(f"{data["external_data"]["total_cases"]}", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                html.Span(" people suffer from severe diseases, and ", style={"color": "#a9a9a9", "font-size": "12px"}),
                html.Span(f"{data["external_data"]["total_deaths"]}", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                html.Span(" of them have died as a result.", style={"color": "#a9a9a9", "font-size": "12px"})
            ], style={"line-height": "1.6", "margin-bottom": "20px"}),
            html.Div([
                html.Div([
                    html.P("All Disease Cases", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                    html.P(f"{data["external_data"]["total_cases"]}", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                ], style={"padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-bottom": "10px"}),
                html.Div([
                    html.P("All Deaths", style={"text-align": "center", "font-size": "14px", "margin-bottom": "5px"}),
                    html.P(f"{data["external_data"]["total_deaths"]}", style={"text-align": "center", "font-size": "24px", "font-weight": "medium"}) ### CHANGE THIS: this needs to be dynamically retrieved from the output data
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
                html.Span(str(data["models-impact"]["total_models"]) +  " models", style={"color": "#6A1B9A", "font-weight": "bold", "font-size": "12px"}), ### CHANGE THIS: this needs to be dynamically retrieved from the output data
                html.Span(" each designed with diverse applications in mind.", style={"color": "#a9a9a9", "font-size": "12px"}),
            ], style={"line-height": "1.6", "margin-bottom": "20px"}),
    ]),

    # Visualization Section
    html.Div([
        html.Div([
            dcc.Graph(id="model_status", figure=model_status_fig)
        ], style={"width": "30%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "3%"}),
        html.Div([
            html.Div([
            html.P("Ready to use", style={"text-align": "left", "font-size": "12px", "margin-bottom": "5px",
                                                    "font-weight": "bold"}),
            html.P(str(data["models-impact"]["ready_percentage"]), 
                    style={"text-align": "left", "font-size": "30px", "font-weight": "medium", "color": "#6A1B9A"})
        ], style={"width": "23%", "height": "100px", "display": "inline-block", "padding": "20px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "1%",
                    "backgroundColor": "#FAFAFA"})
        ], style={"width": "30%", "display": "inline-block", "padding": "10px", "border": "1px solid #ddd", "border-radius": "10px", "margin-right": "3%"}),
        html.Div([
            dcc.Graph(id="model_status", figure=model_year_data_fig)
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
        dash_table.DataTable(
            id="models-impact-table",
            columns=[{"name": col, "id": col} for col in model_list_data.columns],
            data=model_list_data.to_dict("records"),
            style_table={"overflowX": "auto"},
            style_header={"fontWeight": "bold"},
            style_cell={"textAlign": "center"},
        )
    ], style={"border": "1px solid #ddd", "border-radius": "10px", "padding": "20px", "height": "300px", "margin-bottom": "20px"}),
    
    # Pagination
    html.Div([
        html.P("Placeholder for Pagination", style={"text-align": "center", "font-size": "14px"})
    ], style={"margin-bottom": "20px"})
], style={"margin-left": "320px", "padding": "20px"})
