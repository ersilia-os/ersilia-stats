import pandas as pd
import numpy as np
import json
from ast import literal_eval

GEMINI_API_KEY = sys.argv[1]

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
with open("external-data/external_data_stats.json", 'r') as file:
    external_data = json.load(file)

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
    tags_count.columns = ['Category', 'Count']

    # models per year
    year_counts = pd.Series(models_df['Incorporation Year']).value_counts().reset_index()
    year_counts.columns = ['Year', 'Count']

    # Prepare the final models data
    models_data = {
        "total_models": total(models_df),
        "model_distribution": tags_count.to_dict(orient='records'),
        "ready_percentage": round((models_df['Status'] == "Ready").mean() * 100, 2),
        "model_list": models_df[['Title', 'Tag', 'Contributor', 'Incorporation Date', 'Status', 'GitHub']].to_dict(orient='records'),
        "models_per_year": year_counts.to_dict(orient='records')
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

    # Duration of Involvement
    community_df['End Date'] = community_df['End Date'].fillna(pd.Timestamp.today().date()) #if missing end date, assume today 

    community_df['Start Date'] = pd.to_datetime(community_df['Start Date'])
    community_df['End Date'] = pd.to_datetime(community_df['End Date'])

    #makes new column for contributed tim
    community_df['Contributed_Time'] = (community_df['End Date'].dt.to_period('M').astype(int)- community_df['Start Date'].dt.to_period('M').astype(int))

    # place in time buckets
    bins = [0, 3, 6, 12, 10000]

    # Create a new column for the buckets
    community_df['time_bucket'] = pd.cut(community_df['Contributed_Time'], bins)
    duration_data = community_df['time_bucket'].value_counts().rename_axis('values').reset_index(name='counts')
    
    if "values" in duration_data.columns:
        duration_data["values"] = duration_data["values"].astype(str)  # Convert intervals to strings

    # Replace raw intervals with meaningful labels
    duration_data["values"] = duration_data["values"].replace({
        "(0, 3]": "< 3 Months",
        "(3, 6]": "3-6 Months",
        "(6, 12]": "6-12 Months",
        "(12, 10000]": "> 1 Year"
    })
    duration_data = duration_data.rename(
        columns={'values': "Duration", "counts": "Count"}
    )
    # Prepare the final community data
    community_data = {
        "countries_represented": sum_unique(community_df, 'Country'),
        "role_distribution": role_counts.to_dict(orient='records'),
        "duration_distribution": duration_data.to_dict(orient='records'),
        "contributors_by_country": [
            {
                "Country": country_map.get(row["Country"].strip("[]").replace("'", ""), "Unknown"),
                "Contributors": row["Contributors"]
            }
            for row in community_df.groupby('Country')['Name'].nunique().reset_index(name='Contributors').to_dict(orient='records')
        ],
        "total_members": total(community_df)
    }

    return community_data

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

    # Organization Type Distribution
    organization_type_distribution = organisations_df['Type'].value_counts(normalize=True).reset_index()
    organization_type_distribution.columns = ['Type', 'Percentage']

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
    # Blogposts Topics
    blogposts_topics_data = blogposts_df  # Assuming blogposts_df is already loaded as a DataFrame

    # Concatenate slugs and intros into one string for the LLM prompt
    input_string = "\n".join(
        f"Slug: {row['Slug']}\nIntro: {row['Intro']}" for _, row in blogposts_topics_data.iterrows()
    )

    # LLM API function
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv

    load_dotenv()

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    def generate_tags(input_string):
        prompt = f"""
        Based on the following blog slugs and introductions, generate 5-7 relevant tags for categorizing the blogposts.
        Additionally, assign each blogpost to its most relevant tag based on its slug and introduction.

        Input:
        {input_string}

        Output the result in the following JSON format:
        {{
            "tags": ["Tag 1", "Tag 2", "Tag 3", ...],
            "blogpost_tags": [
                {{"Slug": "Slug 1", "Tag": "Tag 1"}},
                {{"Slug": "Slug 2", "Tag": "Tag 2"}},
                ...
            ]
        }}
        """
        # Lower temperature for controlled, grounded output
        generation_config = genai.GenerationConfig(
            temperature=0.2
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return json.loads(response.text[7:-4])

    # Generate tags and parse JSON output
    parsed_output = generate_tags(input_string)

    # Extract tags and blogpost-tag mapping
    blogpost_tags = pd.DataFrame(parsed_output["blogpost_tags"])

    # Merge tags with the original blogpost DataFrame
    blogpost_data = blogposts_topics_data.merge(blogpost_tags, on="Slug", how="left")

    # Aggregate tag counts for visualization
    tag_counts = blogpost_data["Tag"].value_counts()
    tag_percentages = (tag_counts / tag_counts.sum()) * 100

    # Prepare blogpost statistics
    blogposts_data = {
        "total_blogposts": total(blogposts_df),
        "tags": parsed_output["tags"],  # The tags generated by the LLM
        "tag_distribution": pd.DataFrame({
            "Tag": tag_counts.index,
            "Count": tag_counts.values,
            "Percentage": tag_percentages.values
        }).to_dict(orient="records"),
        "posts_over_time": blogposts_df.groupby(['Year', 'Quarter']).size().reset_index(name='Post Count').to_dict(orient='records'),
    }
    
    return blogposts_data

# Events
def calculate_events_stats():
    # --- Events By Year ---
    events_by_year = (
        events_df.groupby("Year")["Name"]
        .count()
        .reset_index()
        .rename(columns={"Name": "Count"})
        .to_dict(orient="records")
    )

    # --- Events By Type ---
    # Concatenate description, event URL, and name into one string for the LLM prompt
    input_string = "\n".join(
        f"Description: {row['Description']}\nEvent URL: {row['Event URL']}\nName: {row['Name']}"
        for _, row in events_df.iterrows()
    )

    # LLM API function
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv

    load_dotenv()

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    def generate_tags(input_string):
        """
        Generate tags and assign each event to its most relevant tag based on description, event URL, and name.
        """
        prompt = f"""
        Based on the following event descriptions, URLs, and names, generate 5-7 relevant types of events for categorizing the events. Make sure each event is an understandable noun.
        Additionally, assign each event to its most relevant tag based on its description, URL, and name.

        Input:
        {input_string}

        Output the result in the following JSON format:
        {{
            "types": ["Tag 1", "Tag 2", "Tag 3", ...],
            "event_tags": [
                {{"Name": "Event Name 1", "Type": "Type 1"}},
                {{"Name": "Event Name 2", "Type": "Type 2"}},
                ...
            ]
        }}
        """
        # Lower temperature for controlled, grounded output
        generation_config = genai.GenerationConfig(
            temperature=0.2
        )

        # Generate response
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return json.loads(response.text[7:-4])  # Adjust parsing to fit the output format

    # Generate tags and parse JSON output
    parsed_output = generate_tags(input_string)

    # Extract tags and event-tag mapping
    event_tags_df = pd.DataFrame(parsed_output["event_tags"])

    # Merge tags with the original Events DataFrame
    events_with_tags = events_df.merge(event_tags_df, left_on="Name", right_on="Name", how="left")

    # Aggregate tag counts for visualization
    tag_counts = events_with_tags["Type"].value_counts()
    tag_percentages = (tag_counts / tag_counts.sum()) * 100

    # Output tag percentages for visualization
    tag_percentages_df = tag_percentages.reset_index()
    events_by_type_df = tag_percentages_df.merge(tag_counts, on="Type")
    events_by_type_df.columns = ["Type", "Percentage", "Count"]

    event_types_summary = events_by_type_df.to_dict(orient="records")

    # --- Events by Country ---
    # Process each row in the events DataFrame
    events_by_country = []
    for _, row in events_df.iterrows():
        organisations_id = literal_eval(row['Organisations'])[0] if row['Organisations'] else None

        organisations_row = organisations_df[organisations_df['id'] == organisations_id]
        organisations_country = literal_eval(organisations_row["Country"].values[0])[0] if not organisations_row.empty else None

        country_name = countries_df[countries_df['id'] == organisations_country]["Country"].values[0] if organisations_country else None

        if country_name:
            organiser = literal_eval(row["Organiser"])[0]
            country_entry = next((item for item in events_by_country if item["Country"] == country_name), None)
            if country_entry:
                country_entry["Organisers"].append(organiser)
            else:
                events_by_country.append({"Country": country_name, "Organisers": [organiser]})

    events_data = {
        "total_events": total(events_df),
        "events_by_year": events_df['Year'].value_counts().reset_index().rename(
            columns={'Count': 'Year', 'count': 'Count'}).to_dict(orient='records'),
        "events_by_type": event_types_summary,
        "events_by_country": events_by_country
    }

    return events_data

# Publications
def calculate_publications_stats():
    publications_data = {
        "total_publications": total(publications_df),
        "total_citations": sum_column(publications_df, 'Citations'),
        "citations_by_year": publications_df.groupby("Year")["Citations"].sum().reset_index().rename(
            columns={"Citations": "total_citations"}).to_dict(orient="records"),
        "publications_by_year": publications_df['Year'].value_counts().reset_index().rename(
            columns={'Count': 'Year', 'count': 'Count'}).to_dict(orient='records'),
        "collaboration_breakdown": publications_df['Ersilia Affiliation'].value_counts().reset_index().rename(
            columns={'Count': 'Ersilia Affiliation', 'count': 'Count'}).to_dict(orient='records'),
        "publications_by_topic": publications_df['Topic'].value_counts().reset_index().rename(
            columns={'Count': 'Topic', 'count': 'Count'}).to_dict(orient='records'),
        "status_distribution": publications_df['Status'].value_counts().reset_index().rename(
            columns={'index': 'Status', 'Status': 'Count'}).to_dict(orient='records')
    }

    # Track author counts for non-Ersilia publications
    author_counts = {}

    for _, row in publications_df.iterrows():
        if row['Ersilia Affiliation'] == "No":
            authors = row['Authors'].split(', ')
            for author in authors:
                if author in author_counts:
                    author_counts[author] += 1
                else:
                    author_counts[author] = 1

    # Convert the dictionary to a sorted list of tuples (author, count)
    sorted_author_counts = sorted(author_counts.items(), key=lambda item: item[1], reverse=True)

    # Extract just the names in order of frequency
    author_names_by_frequency = [
        {"author": author, "count": count} 
        for author, count in sorted_author_counts 
        if author not in ["Miquel Duran-Frigola", "Patrick Aloy"]
    ]
    publications_data["non_ersilia_authors_by_frequency"] = author_names_by_frequency

    # Count of Ersilia and non-Ersilia affiliations for each year
    affiliation_counts = (
        publications_df
        .groupby(['Year', 'Ersilia Affiliation'])
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .rename(columns={'Yes': 'Ersilia Affiliation', 'No': 'Non-Ersilia Affiliation'})
        .to_dict(orient='records')
    )

    publications_data["affiliation_counts_by_year"] = affiliation_counts
    
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
    external_stats = {
        "disease_statistics": [],
        "total_cases": 0,
        "total_deaths": 0
    }

    for disease, stats in external_data.items():
        # Initialize disease-level totals
        total_cases = stats["cases"]["world"]
        total_deaths = stats["deaths"]["world"]

        # Add to overall totals
        external_stats["total_cases"] += total_cases
        external_stats["total_deaths"] += total_deaths

        # Extract per-country stats
        country_cases = stats["cases"]["countries"]
        country_deaths = stats["deaths"]["countries"]

        # Prepare per-country data for each disease
        country_statistics = {
            country: {
                "cases": country_cases.get(country, 0),
                "deaths": country_deaths.get(country, 0)
            }
            for country in set(country_cases) | set(country_deaths)
        }

        # Add disease-level statistics
        external_stats["disease_statistics"].append({
            "disease": disease.replace("_", " ").title(),
            "total_cases": total_cases,
            "total_deaths": total_deaths,
            "country_statistics": country_statistics
        })

    # Round totals for consistency
    external_stats["total_cases"] = round(external_stats["total_cases"])
    external_stats["total_deaths"] = round(external_stats["total_deaths"])
    for disease in external_stats["disease_statistics"]:
        disease["total_cases"] = round(disease["total_cases"])
        disease["total_deaths"] = round(disease["total_deaths"])
        for country, stats in disease["country_statistics"].items():
            stats["cases"] = round(stats["cases"])
            stats["deaths"] = round(stats["deaths"])

    return external_stats


calculate_external_data_stats()

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
