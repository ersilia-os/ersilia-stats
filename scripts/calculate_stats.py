import pandas as pd
import numpy as np
import json

# Reading all the specified CSV files into DataFrames
blogposts_df = pd.read_csv('data/Blogposts.csv')
community_df = pd.read_csv('data/Community.csv')
countries_df = pd.read_csv('data/Countries.csv')
events_df = pd.read_csv('data/Events.csv')
models_df = pd.read_csv('data/Models.csv')
organisations_df = pd.read_csv('data/Organisations.csv')
publications_df = pd.read_csv('data/Publications.csv')
external_titles_df = pd.read_csv('external-data/titles_results.csv')
external_authors_df = pd.read_csv('external-data/authors_results.csv')

output_data = {
    "publications": {},
    "blogposts-events": {},
    "countries": {},
    "organization": {},
    "community": {},
    "models-impact": {},
    "openalex_titles": {},
    "openalex_authors": {}
}

# ------------------------ General Helper Functions ------------------------
def total(df):
    return df.shape[0]

def sum_column(df, column):
    return int(df[column].sum())

def sum_specific(df, column, value):
    return (df[column] == value).sum()

def sum_unique(df, column):
    return df[column].nunique()

def sum_unique_grouped(df, unique_column, grouped_column):
    return df.groupby(grouped_column)[unique_column].nunique().reset_index(name='unique_count').to_dict(orient='records')

def calc_avg_specific(df, group_by, column):
    return df.groupby(group_by)[column].mean().reset_index().rename(columns={column: f'average_{column}'}).round(2).to_dict(orient='records')

# ------------------------ Extended Statistics ------------------------

# Models' Impact
def calculate_models_impact():
    models_data = {}
    models_data["total-models"] = total(models_df)
    models_data["model-distribution"] = models_df['Tag'].value_counts().reset_index().rename(
        columns={'index': 'Category', 'Tag': 'Count'}).to_dict(orient='records')
    models_data["ready-percentage"] = round((models_df['Status'] == "Ready").mean() * 100, 2)
    models_data["model-list"] = models_df[['Title', 'Tag', 'Contributor', 'Incorporation Date', 'Status']].to_dict(orient='records')
    return models_data

# Community & Blog
def calculate_community_stats():
    community_data = {}
    community_data["countries-represented"] = sum_unique(community_df, 'Country')
    community_data["role-distribution"] = community_df['Role'].value_counts().reset_index().rename(
        columns={'index': 'Role', 'Role': 'Count'}).to_dict(orient='records')
    community_data["contributors-by-country"] = community_df.groupby('Country')['Name'].nunique().reset_index(
        name='Contributors').to_dict(orient='records')
    community_data["total-members"] = total(community_df)
    return community_data

# Blog Posts
def calculate_blogposts_stats():
    blogposts_data = {}
    blogposts_data["total-blogposts"] = total(blogposts_df)
    blogposts_data["topics-distribution"] = blogposts_df['Publisher'].value_counts().reset_index().rename(
        columns={'index': 'Topic', 'Publisher': 'Count'}).to_dict(orient='records')
    blogposts_data["posts-over-time"] = blogposts_df.groupby(['Year', 'Quarter']).size().reset_index(
        name='Post Count').to_dict(orient='records')
    return blogposts_data

# Events
def calculate_events_stats():
    events_data = {}
    events_data["total-events"] = total(events_df)
    events_data["events-by-year"] = events_df['Year'].value_counts().reset_index().rename(
        columns={'index': 'Year', 'Year': 'Count'}).to_dict(orient='records')
    return events_data

# Publications
def calculate_publications_stats():
    publications_data = {}
    publications_data["total-publications"] = total(publications_df)
    publications_data["total-citations"] = sum_column(publications_df, 'Citations')
    publications_data["citations-by-year"] = calc_avg_specific(publications_df, 'Year', 'Citations')
    publications_data["collaboration-breakdown"] = publications_df['Ersilia Affiliation'].value_counts().reset_index().rename(
        columns={'index': 'Collaboration Type', 'Ersilia Affiliation': 'Count'}).to_dict(orient='records')
    publications_data["publications-by-topic"] = publications_df['Topic'].value_counts().reset_index().rename(
        columns={'index': 'Topic', 'Topic': 'Count'}).to_dict(orient='records')
    return publications_data

# Countries
def calculate_countries_stats():
    countries_data = {}
    countries_data["num-unique-countries"] = sum_unique(countries_df, 'Country')
    countries_data["num-countries-region"] = sum_unique_grouped(countries_df, 'Country', 'Region')
    return countries_data

# OpenAlex titles query
def calculate_openalex_titles():
    return {
        "total_titles": len(external_titles_df),
        "exact_matches": external_titles_df["Match"].sum(),
        "match_percentage": round(external_titles_df["Match"].mean() * 100, 2) if len(external_titles_df) > 0 else 0
    }

# OpenAlex authors query
def calculate_openalex_authors():
    print(external_authors_df)
    return {
        "total_authors": len(external_authors_df),
        "total_works": external_authors_df["Number of Works"].sum(),
        "total_citations": external_authors_df["Total Citations"].sum(),
        "highest_h_index": external_authors_df["H-index"].max(),
        "top_author": external_authors_df.loc[external_authors_df["H-index"].idxmax(), "Name"]
    }

# ------------------------ Aggregating All Calculations ------------------------
output_data["models-impact"] = calculate_models_impact()
output_data["community"] = calculate_community_stats()
output_data["blogposts-events"] = calculate_blogposts_stats()
output_data["events"] = calculate_events_stats()
output_data["publications"] = calculate_publications_stats()
output_data["countries"] = calculate_countries_stats()
output_data["openalex_titles"] = calculate_openalex_titles()
output_data["openalex_authors"] = calculate_openalex_authors()

# ------------------------ Serialization & Output ------------------------
def convert_to_serializable(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.applymap(lambda x: int(x) if isinstance(x, np.int64) else x).to_dict(orient='records')
    if isinstance(obj, np.int64):
        return int(obj)
    if isinstance(obj, np.float64):
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    return obj

output_data_serializable = convert_to_serializable(output_data)

# Write the output_data to a JSON file
with open('reports/tables_stats.json', 'w') as json_file:
    json.dump(output_data_serializable, json_file, indent=4)

# Print confirmation message
print(json.dumps(output_data_serializable, indent=4))
print("Data has been written to 'tables_stats.json'")
