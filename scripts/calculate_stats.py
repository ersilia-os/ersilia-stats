import pandas as pd
import numpy as np
import csv
import json

# Reading all the specified CSV files into DataFrames
blogposts_df = pd.read_csv('data/Blogposts.csv')
community_df = pd.read_csv('data/Community.csv')
conferences_df = pd.read_csv('data/Conferences.csv')
contacts_df = pd.read_csv('data/Contacts.csv')
countries_df = pd.read_csv('data/Countries.csv')
donations_df = pd.read_csv('data/Donations.csv')
events_df = pd.read_csv('data/Events.csv')
grants_df = pd.read_csv('data/Grants.csv')
models_df = pd.read_csv('data/Models.csv')
news_df = pd.read_csv('data/News.csv')
organisations_df = pd.read_csv('data/Organisations.csv')
projects_df = pd.read_csv('data/Projects.csv')
publications_df = pd.read_csv('data/Publications.csv')
repositories_df = pd.read_csv('data/Repositories.csv')

output_data = {
    "publications": {},
    "blogposts-events": {},
    "countries": {},
    "organization": {},
    "community": {}
}

def total(csv):
    df = csv
    return df.shape[0]

def sum(csv, column):
    df = csv
    return int(df[column].sum())

def sum_specific(csv, column, value):
    df = csv
    return (df[column] == value).sum()

def calc_avg_specific(csv, year, column):
    df = csv
    avg_per_year = (df.groupby(year)[column].mean().reset_index().rename(columns={column: 'average_'+ column}).round(2))
    return avg_per_year.to_dict(orient='records')

def sum_unique_grouped(csv, unique_column, grouped_column):
    df = csv
    sum = df.groupby(grouped_column)[unique_column].nunique().reset_index(name='unique_column_count')
    return sum.to_dict(orient='records')

def sum_year_column(csv, year, column):
    df = csv
    sum_by_categories = df.groupby([year, column]).size().reset_index(name='post_count')
    return sum_by_categories.to_dict(orient='records')

def sum_unique(csv, column):
    df = csv
    unique = df[column].nunique()
    return unique


def sum_members_country():

    #Getting community count for each country
    community_df_edit = community_df
    community_df_edit['Country'] = community_df['Country (from Country)'].str[2:-2]
    data_counts = community_df_edit.groupby('Country').size().reset_index(name='Count')
    df = countries_df.merge(data_counts, on='Country', how='left')

    #Filtering for Global South
    global_south_regions = ['Africa', 'Latin America and the Caribbean', 'Asia', 'Oceania']
    excluded_countries = ['Israel', 'Japan', 'South Korea', 'Australia', 'New Zealand']
    global_south_df = df[(df['Region'].isin(global_south_regions)) & (~df['Country'].isin(excluded_countries))]
    global_south_summary = global_south_df.groupby('Country')['Count'].sum().reset_index()
    return global_south_summary[global_south_summary['Count'] != 0].to_dict(orient='records')


# Helper function to convert int64/float64 to int/float
def convert_to_serializable(obj):
    if isinstance(obj, pd.Series):
        return obj.apply(lambda x: int(x) if isinstance(x, np.int64) else x).tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.applymap(lambda x: int(x) if isinstance(x, np.int64) else x).to_dict(orient='records')
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    if isinstance(obj, np.int64):
        return int(obj)
    if isinstance(obj, np.float64):
        return float(obj)
    return obj

# Publication:
output_data["publications"]["total-publications"] = total(publications_df)
output_data["publications"]["total-citations"] = sum(publications_df, 'Citations')
output_data["publications"]["total-publications-senior-author"] = sum_specific(publications_df, 'Senior', 'Yes')
output_data["publications"]["average-citations-article-year"] = calc_avg_specific(publications_df, 'Year', 'Citations')
# Total number of publications per month.

# Blog Posts and Events
# idk what "type" is - Number of blog posts, categorized by type (e.g., transparency, "fair-impact").
output_data["blogposts-events"]["num-posts-quarter-year"] = sum_year_column(blogposts_df, 'Year', 'Quarter')
output_data["blogposts-events"]["total-events"] = total(events_df)

# Countries
output_data["countries"]["num-unique-countries"] = sum_unique(countries_df, 'Country')
output_data["countries"]["num-countries-region"] = sum_unique_grouped(countries_df, 'Country', 'Region')
output_data["countries"]["num-countries-subregion"] = sum_unique_grouped(countries_df, 'Country', 'Subregion')
output_data["countries"]["country-population"] = countries_df[['Country', 'Population']].to_dict(orient='records')
output_data["countries"]["members-globalsouth-country"] = sum_members_country() #I only showed the ones that have a member count that isn't 0

# Organization
output_data["organization"]["num-collab-classification"] = organisations_df.groupby('Classification').size().reset_index(name='Count')
# 2. Breakdown of collaborations with organizations categorized as nonprofit, pharma, academia, or government.
# 3. Specification of activities (e.g., publications, volunteers, conferences) with these organizations.

# Community
output_data["community"]["total-members"] = total(community_df) # doesn't include engagement with social media channels - don't know where to see this
# doesn't know where to see Average engagement (e.g., likes) per blog post per quarter.



# Convert the entire output_data to serializable types
output_data_serializable = convert_to_serializable(output_data)

# Print the output dictionary
print(json.dumps(output_data_serializable, indent=4))

# Write the output_data to a JSON file
with open('tables_stats.json', 'w') as json_file:
    json.dump(output_data_serializable, json_file, indent=4)

# Optionally print confirmation message
print("Data has been written to 'tables_stats.json'")