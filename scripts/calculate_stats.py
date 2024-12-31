import pandas as pd
import numpy as np
import json
from ast import literal_eval
# Reading all the specified CSV files int DataFrames
blogposts_df = pd.read_csv('data/Blogposts.csv')
community_df = pd.read_csv('data/Community.csv')
countries_df = pd.read_csv('data/Countries.csv')
events_df = pd.read_csv('data/Events.csv')
models_df = pd.read_csv('data/Models.csv')
organisations_df = pd.read_csv('data/Organisations.csv')
publications_df = pd.read_csv('data/Publications.csv')
external_titles_df = pd.read_csv('external-data/titles_results.csv')
external_authors_df = pd.read_csv('external-data/authors_results.csv')


# Reading external datasets
external_files = {
    "alzheimers_deaths": "external-data/alzheimers-deaths.csv",
    "meningitis_deaths": "external-data/meningitis-deaths.csv",
    "pneumonia_deaths": "external-data/pneumonia-deaths.csv",
    "hivaids_deaths": "external-data/hivaids-deaths.csv",
    "cardiovascular_deaths": "external-data/cardiovascular-deaths.csv",
    "tuberculosis_deaths": "external-data/tuberculosis-deaths.csv",
    "life_expectancy": "external-data/life-expectancy-vs-health-expenditure.csv",
    "community_health_workers": "external-data/community-health-workers.csv",
    "covid_data": "external-data/covid-cases-and-deaths.csv",
    "malaria_deaths": "external-data/malaria-deaths.csv",
    "hiv_deaths": "external-data/hivaids-deaths.csv"
}

external_data = {key: pd.read_csv(path) for key, path in external_files.items()}

output_data = {
    "publications": {},
    "blogposts-events": {},
    "countries": {},
    "organization": {},
    "community": {},
    "models-impact": {},
    "openalex_titles": {},
    "openalex_authors": {},
    "external_data": {}
}

# ------------------------ General Helper Functions ------------------------
def total(df):
    return df.shape[0]

def sum_column(df, column):
    return int(df[column].sum())

#  Occurance_column calculates the occurances of a string in array-like columns 
#  Will be used to find the unique roles of contributors
def occurances_column(df, column):
    dummy_df = df
    dummy_df[column] = df[column].apply(literal_eval) #changes the array-like column to an actual array
    dummy_df = dummy_df.explode(column)

    return dummy_df[column].value_counts().rename_axis('values').reset_index(name='counts')

def sum_unique(df, column):
    return df[column].nunique()

def calc_avg(df, column):
    return df[column].mean()

def calc_avg_specific(df, group_by, column):
    return df.groupby(group_by)[column].mean().reset_index().rename(columns={column: f'average_{column}'}).round(2).to_dict(orient='records')

def map_ids_to_names(df, id_column, name_column):
    """Map IDs to readable names for given columns."""
    return dict(zip(df[id_column], df[name_column]))

# ------------------------ Extended Statistics ------------------------

# Models' Impact
def calculate_models_impact():
    models_data = {
        "total_models": total(models_df),
        "model_distribution": models_df['Tag'].value_counts().reset_index().rename(
            columns={'index': 'Category', 'Tag': 'Count'}).to_dict(orient='records'),
        "ready_percentage": round((models_df['Status'] == "Ready").mean() * 100, 2),
        "model_list": models_df[['Title', 'Tag', 'Contributor', 'Incorporation Date', 'Status']].to_dict(orient='records')
    }

    # Clean brackets and quotes in model categories
    for model in models_data["model_distribution"]:
        model["Count"] = model["Count"].strip("[]").replace("'", "")

    return models_data

# Community & Blog
def calculate_community_stats():
    country_map = map_ids_to_names(countries_df, "id", "Country")

    community_data = {
        "countries_represented": sum_unique(community_df, 'Country'),
        "role_distribution": [
            {
                "Role": role['Count'].strip("[]").replace("'", ""),
                "Count": role["count"]
            } for role in community_df['Role'].value_counts().reset_index().rename(
                columns={'index': 'Role', 'Role': 'Count'}).to_dict(orient='records')
        ],
        "contributors_by_country": [
            {
                "Country": country_map.get(row["Country"].strip("[]").replace("'", ""), "Unknown"),
                "Contributors": row["Contributors"]
            } for row in community_df.groupby('Country')['Name'].nunique().reset_index(
                name='Contributors').to_dict(orient='records')
        ],
        "total_members": total(community_df)
    }

    return community_data

# Attempts to find the duration of a contributor
def community_time_duration():
   community_df['start_date'] = pd.to_datetime(community_df['start_date'])
   community_df['end_date'] = pd.to_datetime(community_df['end_date'])

   #makes new column for contributed time
   community_df['contributed_time'] = community_df['end_date'] - community_df['start_date'] 


# Countries
def calculate_countries_stats():
    global_south_income_groups = ["LIC", "LMIC"]
    global_north_income_groups = ["UMIC", "HIC"]

    countries_data = {
        "total_countries": sum_unique(countries_df, 'Country'),
        "global_south_countries": sum(countries_df['Income Group'].isin(global_south_income_groups)),
        "global_north_countries": sum(countries_df['Income Group'].isin(global_north_income_groups)),
        "income_groups": countries_df['Income Group'].value_counts().reset_index().rename(
            columns={'index': 'Income Group', 'Income Group': 'Count'}).to_dict(orient='records'),
        "population_by_region": [
            {
                "Region": row["Region"],
                "Total Population": round(row["Population"])
            } for row in countries_df.groupby('Region')['Population'].sum().reset_index().to_dict(orient='records')
        ]
    }
    return countries_data

# Organizations
def calculate_organization_stats():
    country_map = map_ids_to_names(countries_df, "id", "Country")

    org_data = {
        "total_organizations": total(organisations_df),
        "organization_types": organisations_df['Type'].value_counts().reset_index().rename(
            columns={'index': 'Organization Type', 'Type': 'Count'}).to_dict(orient='records'),
        "organizations_by_country": [
            {
                "Country": country_map.get(row["Country"].strip("[]").replace("'", ""), "Unknown"),
                "Total Organizations": row["Total Organizations"]
            } for row in organisations_df.groupby('Country')['Name'].nunique().reset_index(
                name='Total Organizations').to_dict(orient='records')
        ]
    }
    return org_data

# Blog Posts
def calculate_blogposts_stats():
    blogposts_data = {
        "total_blogposts": total(blogposts_df),
        "topics_distribution": blogposts_df['Publisher'].value_counts().reset_index().rename(
            columns={'index': 'Topic', 'Publisher': 'Count'}).to_dict(orient='records'),
        "posts_over_time": blogposts_df.groupby(['Year', 'Quarter']).size().reset_index(
            name='Post Count').to_dict(orient='records')
    }
    return blogposts_data

# Events
def calculate_events_stats():
    events_data = {
        "total_events": total(events_df),
        "events_by_year": events_df['Year'].value_counts().reset_index().rename(
            columns={'index': 'Year', 'Year': 'Count'}).to_dict(orient='records')
    }
    return events_data

# Publications
def calculate_publications_stats():
    publications_data = {
        "total_publications": total(publications_df),
        "total_citations": sum_column(publications_df, 'Citations'),
        "citations_by_year": calc_avg_specific(publications_df, 'Year', 'Citations'),
        "collaboration_breakdown": publications_df['Ersilia Affiliation'].value_counts().reset_index().rename(
            columns={'index': 'Collaboration Type', 'Ersilia Affiliation': 'Count'}).to_dict(orient='records'),
        "publications_by_topic": publications_df['Topic'].value_counts().reset_index().rename(
            columns={'index': 'Topic', 'Topic': 'Count'}).to_dict(orient='records')
    }
    return publications_data

# OpenAlex titles query
def calculate_openalex_titles():
    return {
        "total_titles": len(external_titles_df),
        "exact_matches": external_titles_df["Match"].sum(),
        "match_percentage": round(external_titles_df["Match"].mean() * 100, 2) if len(external_titles_df) > 0 else 0
    }

# OpenAlex authors query
def calculate_openalex_authors():
    return {
        "total_authors": len(external_authors_df),
        "total_works": external_authors_df["Number of Works"].sum(),
        "total_citations": external_authors_df["Total Citations"].sum(),
        "highest_h_index": external_authors_df["H-index"].max(),
        "top_author": external_authors_df.loc[external_authors_df["H-index"].idxmax(), "Name"]
    }

# External Data Statistics
def calculate_external_data_stats():
    external_stats = {"disease_statistics": []}
    population_df = pd.read_csv('external-data/world-population.csv')  # Load population data

    # Function to compute total deaths for rate-based datasets
    def calculate_deaths_from_rate(df, rate_column):
        df = pd.merge(df, population_df, on=["Entity", "Year"], how="left")
        if "population_historical" in df.columns:
            df["total_deaths"] = df[rate_column] * df["population_historical"] / 100000
            return df
        else:
            df["total_deaths"] = None
            return df

    # Datasets and their respective columns
    datasets = [
        ("alzheimers_deaths", "death_rate100k__age_group_allages__sex_both_sexes__cause_alzheimer_disease_and_other_dementias"),
        ("meningitis_deaths", "death_rate100k__age_group_allages__sex_both_sexes__cause_meningitis"),
        ("pneumonia_deaths", "death_rate100k__age_group_allages__sex_both_sexes__cause_lower_respiratory_infections"),
        ("hivaids_deaths", "aids_deaths__disaggregation_all_ages_estimate"),
        ("cardiovascular_deaths", "death_rate100k__age_group_allages__sex_both_sexes__cause_cardiovascular_diseases"),
        ("malaria_deaths", "estimated_number_of_malaria_deaths"),
        ("tuberculosis_deaths", "death_count__age_group_allages__sex_both_sexes__cause_tuberculosis")
    ]

    for dataset, column in datasets:
        df = external_data[dataset]

        if "rate" in column:  # Rate-based datasets
            df = calculate_deaths_from_rate(df, column)
            total_deaths = df["total_deaths"].sum()
            most_recent_year = df.loc[df["Year"].idxmax()]
            most_recent_year_deaths = most_recent_year["total_deaths"]
            most_recent_year_value = most_recent_year["Year"]
        else:  # Absolute death count datasets
            total_deaths = df[column].sum()
            most_recent_year = df.loc[df["Year"].idxmax()]
            most_recent_year_deaths = most_recent_year[column]
            most_recent_year_value = most_recent_year["Year"]

        external_stats["disease_statistics"].append({
            "disease": dataset.replace("_deaths", "").replace("_", " ").title(),
            "total_deaths": round(total_deaths),
            "most_recent_year": int(most_recent_year_value),
            "most_recent_year_deaths": round(most_recent_year_deaths)
        })

    # COVID statistics (cumulative cases and deaths)
    covid_df = external_data["covid_data"]
    world_covid = covid_df[covid_df["Entity"] == "World"].sort_values(by="Day").iloc[-1]
    external_stats["covid_statistics"] = {
        "total_cases": int(world_covid["total_cases"]),
        "total_deaths": int(world_covid["total_deaths"])
    }

    return external_stats



# Aggregating All Calculations
output_data["models-impact"] = calculate_models_impact()
output_data["community"] = calculate_community_stats()
output_data["countries"] = calculate_countries_stats()
output_data["organization"] = calculate_organization_stats()
output_data["blogposts-events"] = calculate_blogposts_stats()
output_data["events"] = calculate_events_stats()
output_data["publications"] = calculate_publications_stats()
output_data["openalex_titles"] = calculate_openalex_titles()
output_data["openalex_authors"] = calculate_openalex_authors()
output_data["external_data"] = calculate_external_data_stats()

# Serialization & Output
def convert_to_serializable(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    if isinstance(obj, (np.int64, np.float64)):
        return obj.item()
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    return obj

output_data_serializable = convert_to_serializable(output_data)

# Write the output_data to a JSON file
with open("reports/tables_stats.json", "w") as json_file:
    json.dump(output_data_serializable, json_file, indent=4)

print("Data has been written to 'tables_stats.json'")
