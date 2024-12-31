import pandas as pd
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import numpy as np  

app = Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        options=[
            {'label': 'Alzheimer\'s Deaths', 'value': 'alzheimers-deaths'},
            {'label': 'Cardiovascular Deaths', 'value': 'cardiovascular-disease-deaths'},
            {'label': 'Cervical Cancer Deaths', 'value': 'cervical-cancer-deaths'},
            {'label': 'COVID Deaths', 'value': 'covid-deaths'},
            {'label': 'Hepatitis B Deaths', 'value': 'hepatitis-B-deaths'},
            {'label': 'HIV/AIDS Deaths', 'value': 'hivaids-deaths'},
            {'label': 'Malaria Deaths', 'value': 'malaria-deaths'},
            {'label': 'Meningitis Deaths', 'value': 'meningitis-deaths'},
            {'label': 'Pneumonia Deaths', 'value': 'pneumonia-deaths'},
            {'label': 'Tuberculosis Deaths', 'value': 'tuberculosis-deaths'},
        ],
        value='malaria-deaths',
        id='dropdown'
    ),
    dcc.Graph(id='graph')
])

@app.callback(
    Output('graph', 'figure'),
    Input('dropdown', 'value')
)
def display_choropleth(death_type):
    df = pd.read_csv(f"../external-data/{death_type}.csv")

    # Handling outliers by log-transforming the data
    df['Log_Deaths'] = np.log1p(df['Deaths'])  

    max_log_deaths = df['Log_Deaths'].max()
    min_log_deaths = df['Log_Deaths'].min()

    fig = px.choropleth(df,
                        locations=df["Code"],
                        color=df["Log_Deaths"],  
                        hover_name=df["Entity"],
                        color_continuous_scale=["#EDE9F3", "#50285A"],
                        range_color=(min_log_deaths, max_log_deaths), 
                        )

   
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
