# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.


from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd

app = Dash()

# TODO: Replace the pd.dataframe with a dataframe for the specified statistic
# Example dataframe 
example_df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
})

example_two = pd.DataFrame({
    "Fruit": ["No Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
})

# Here is where we establish what the graphs are using "px.[type of graph]".
example_fig_bar = px.bar(example_df, x="Fruit", y="Amount", color="City", barmode="group")
example_fig_pie = px.pie(example_two)

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='example-graph',
        figure=example_fig_bar
    ),

    dcc.Graph(
        id='example-graph',
        figure=example_fig_pie
    )
])

if __name__ == '__main__':
    app.run(debug=True)

