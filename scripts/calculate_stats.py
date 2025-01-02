import pandas as pd
import numpy as np
import json
from ast import literal_eval

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
    # Convert Tags to lists of individual categories
    def clean_and_split_tags(tag_value):
        # Handle missing values and convert to string
        if pd.isna(tag_value) or not isinstance(tag_value, str):
            return ["Untagged"]  # Treat untagged models as a separate category
        # Remove brackets and split by commas
        tag_value = tag_value.strip("[]").replace("'", "")
        return [t.strip() for t in tag_value.split(",")]

    # Apply the cleaning function to the Tag column
    tag_series = models_df['Tag'].apply(clean_and_split_tags)

    # Flatten the list of lists into a single list
    from itertools import chain
    all_tags = list(chain.from_iterable(tag_series))

    # Count the occurrences of each tag
    tags_count = pd.Series(all_tags).value_counts().reset_index()
    tags_count.columns = ['Category', 'count']

    # Prepare the final models data
    models_data = {
        "total_models": total(models_df),
        "model_distribution": tags_count.to_dict(orient='records'),
        "ready_percentage": round((models_df['Status'] == "Ready").mean() * 100, 2),
        "model_list": models_df[['Title', 'Tag', 'Contributor', 'Incorporation Date', 'Status']].to_dict(orient='records')
    }

    return models_data

# Community & Blog
def calculate_community_stats():
    # Map country IDs to readable names
    country_map = map_ids_to_names(countries_df, "id", "Country")

    # Handle and clean role data
    def clean_and_split_roles(role_value):
        # Handle missing or NaN values
        if pd.isna(role_value) or not isinstance(role_value, str):
            return ["Unspecified"]  # Default category for missing roles
        # Remove brackets and split by commas
        role_value = role_value.strip("[]").replace("'", "")
        return [r.strip() for r in role_value.split(",")]

    # Apply cleaning to the Role column
    roles_series = community_df['Role'].apply(clean_and_split_roles)

    # Flatten the list of lists into a single list
    from itertools import chain
    all_roles = list(chain.from_iterable(roles_series))

    # Count the occurrences of each role
    role_counts = pd.Series(all_roles).value_counts().reset_index()
    role_counts.columns = ['Role', 'Count']

    # Prepare the final community data
    community_data = {
        "countries_represented": sum_unique(community_df, 'Country'),
        "role_distribution": role_counts.to_dict(orient='records'),
        "contributors_by_country": [
            {
                "Country": country_map.get(row["Country"].strip("[]").replace("'", ""), "Unknown"),
                "Contributors": row["Contributors"]
            }
            for row in community_df.groupby('Country')['Name'].nunique()
            .reset_index(name='Contributors')
            .to_dict(orient='records')
        ],
        "total_members": total(community_df)
    }

    return community_data

# Attempts to find the duration (months) of a contributor (specifically for duration graph)
def community_time_duration():
    community_df['End Date'] = community_df['End Date'].fillna(pd.Timestamp.today().date()) #if missing end date, assume today 

    community_df['Start Date'] = pd.to_datetime(community_df['Start Date'])
    community_df['End Date'] = pd.to_datetime(community_df['End Date'])

    #makes new column for contributed tim
    community_df['Contributed_Time'] = (community_df['End Date'].dt.to_period('M').astype(int)- community_df['Start Date'].dt.to_period('M').astype(int))

    # place in time buckets
    bins = [0, 3, 6, 7, 12,10000]

    # Create a new column for the buckets
    community_df['time_bucket'] = pd.cut(community_df['Contributed_Time'], bins)
    return community_df['time_bucket'].value_counts().rename_axis('values').reset_index(name='counts')


# Countries
def calculate_countries_stats():
    global_south_income_groups = ["LIC", "LMIC"]
    global_north_income_groups = ["UMIC", "HIC"]

    countries_data = {
        "total_countries": sum_unique(countries_df, 'Country'),
        "global_south_countries": sum(countries_df['Income Group'].isin(global_south_income_groups)),
        "global_north_countries": sum(countries_df['Income Group'].isin(global_north_income_groups)),
        "income_groups": countries_df['Income Group'].value_counts().reset_index().rename(
            columns={'Count': 'Income Group', 'count': 'Count'}).to_dict(orient='records'),
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
            columns={'Count': 'Organization Type', 'count': 'Count'}).to_dict(orient='records'),
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
            columns={'Count': 'Publisher', 'count': 'Count'}).to_dict(orient='records'),
        "posts_over_time": blogposts_df.groupby(['Year', 'Quarter']).size().reset_index(
            name='Post Count').to_dict(orient='records'),
        "posts_per_year": blogposts_df.groupby(['Year']).size().reset_index(
            name='Count').to_dict(orient='records')

    }
    return blogposts_data

# Events
def calculate_events_stats():
    events_data = {
        "total_events": total(events_df),
        "events_by_year": events_df['Year'].value_counts().reset_index().rename(
            columns={'Count': 'Year', 'count': 'Count'}).to_dict(orient='records')
    }
    return events_data

# Publications
def calculate_publications_stats():
    publications_data = {
        "total_publications": total(publications_df),
        "total_citations": sum_column(publications_df, 'Citations'),
        "citations_by_year": calc_avg_specific(publications_df, 'Year', 'Citations'),
        "collaboration_breakdown": publications_df['Ersilia Affiliation'].value_counts().reset_index().rename(
            columns={'Ersilia Affiliation': 'Count', 'count': 'Count'}).to_dict(orient='records'),
        "publications_by_topic": publications_df['Topic'].value_counts().reset_index().rename(
            columns={'Count': 'Topic', 'count': 'Count'}).to_dict(orient='records')
    }

    cby = calc_avg_specific(publications_df, 'Year', 'Citations')  # returns [{'Year': 2013, 'average_Citations': X}, ...]
    
    # Collapse years < 2020
    collapsed = {}
    for item in cby:
        year = item["Year"]
        avg_c = item["average_Citations"]
        if year < 2020:
            collapsed.setdefault("Before 2020", []).append(avg_c)
        else:
            collapsed.setdefault(str(year), []).append(avg_c)

    # Now compute the average for 'Before 2020', or just store it
    final_list = []
    for k, v in collapsed.items():
        final_list.append({
            "Year": k,
            "average_Citations": round(sum(v) / len(v), 2)
        })

    publications_data["citations_by_year"] = final_list

    return publications_data

# OpenAlex titles query
def calculate_openalex_titles():
    return {
        "total_titles": len(external_titles_df),
        "exact_matches": external_titles_df["Match"].sum(),
        "match_percentage": round(external_titles_df["Match"].mean() * 100, 2) if len(external_titles_df) > 0 else 0
    }

def calculate_openalex_authors():
    # 1. Explode the Authors column
    pub_exploded = (
        publications_df
        .assign(Authors=publications_df['Authors'].str.split(','))  # split by comma
        .explode('Authors')                                         # one row per author
        .rename(columns={'Authors': 'Name'})
    )
    pub_exploded['Name'] = pub_exploded['Name'].str.strip()  # remove trailing spaces

    # 2. Identify Ersilia publications more explicitly
    #    We'll also store a small dict for each Ersilia publication
    def build_pub_dict(row):
        return {
            "id": row["id"],
            "title": row["Title"],
            "year": row["Year"],
            "url": row["URL"] if "URL" in row else None
        }

    # Filter to *just* rows with Ersilia Affiliation == 'Yes'
    ersilia_rows = pub_exploded[pub_exploded["Ersilia Affiliation"] == "Yes"].copy()
    ersilia_rows["PublicationDetails"] = ersilia_rows.apply(build_pub_dict, axis=1)

    # We also want total pubs, so let's group ALL (even if affiliation == No)
    total_pubs_grouped = (
        pub_exploded
        .groupby('Name')
        .agg(
            total_publications=('id', 'count')
        )
        .reset_index()
    )

    # For Ersilia pubs specifically, group and collect the details
    ersilia_pubs_grouped = (
        ersilia_rows
        .groupby('Name')
        .agg(
            ersilia_publications=('id', 'count'),
            ersilia_pub_details=('PublicationDetails', list)  # collect details in a list
        )
        .reset_index()
    )

    # 3. Merge total_pubs_grouped and ersilia_pubs_grouped
    merged_authors = pd.merge(
        total_pubs_grouped,
        ersilia_pubs_grouped,
        on='Name',
        how='left'
    )

    # If an author has no Ersilia pubs, ersilia_publications will be NaN => fill with 0
    merged_authors['ersilia_publications'] = merged_authors['ersilia_publications'].fillna(0).astype(int)
    merged_authors['ersilia_pub_details'] = merged_authors['ersilia_pub_details'].fillna('')

    # 4. Merge with external_authors_df (OpenAlex) for H-index, etc.
    #    Suppose external_authors_df has columns: [Name, H-index, Number of Works, Total Citations]
    merged_authors = pd.merge(
        merged_authors,
        external_authors_df[['Name', 'H-index', 'Number of Works', 'Total Citations']],
        on='Name',
        how='left'
    )

    # Fill missing fields for authors not found in external_authors_df
    merged_authors['H-index'] = merged_authors['H-index'].fillna(0)
    merged_authors['Number of Works'] = merged_authors['Number of Works'].fillna(0)
    merged_authors['Total Citations'] = merged_authors['Total Citations'].fillna(0)

    # 5. Filter out authors with 0 Ersilia pubs
    merged_authors = merged_authors[merged_authors['ersilia_publications'] > 0].copy()

    # 6. Filter out specific authors if needed
    filter_out = ["Miquel Duran-Frigola", "Gemma Turon", "Dhanshree Arora"]
    merged_authors = merged_authors[~merged_authors['Name'].isin(filter_out)]

    # 7. Sort by (ersilia_publications DESC, H-index DESC)
    merged_authors = merged_authors.sort_values(
        by=['ersilia_publications', 'H-index'], 
        ascending=[False, False]
    )

    # 8. Prepare summary stats
    total_authors = len(external_authors_df)
    total_works = int(external_authors_df['Number of Works'].sum())
    total_citations = int(external_authors_df['Total Citations'].sum())

    # If there's at least one author, pick top_author as the one in first row
    if total_authors > 0:
        top_author_row = merged_authors.iloc[0]
        top_author = top_author_row['Name']
        highest_h_index = int(top_author_row['H-index'])
    else:
        top_author = None
        highest_h_index = 0

    # 9. Convert final data to dictionary for JSON output
    #    We'll store the full table as "author_highlights"
    merged_dict = merged_authors.to_dict(orient='records')

    return {
        "total_authors": total_authors,
        "total_works": total_works,
        "total_citations": total_citations,
        "highest_h_index": highest_h_index,
        "top_author": top_author,
        "author_highlights": merged_dict
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

def create_json():
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

    output_data_serializable = convert_to_serializable(output_data)

    # Write the output_data to a JSON file
    with open("reports/tables_stats.json", "w") as json_file:
        json.dump(output_data_serializable, json_file, indent=4)

    print("Data has been written to 'tables_stats.json'")
