import json
import pandas as pd
from datetime import datetime

# Function to load JSON data
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to load country names from CSV and map IDs to country names
def load_country_names(csv_path):
    countries_df = pd.read_csv(csv_path)
    return dict(zip(countries_df['id'], countries_df['Country']))

# Function to format a table in Markdown
def format_table(headers, rows):
    table = f"| {' | '.join(headers)} |\n"
    table += f"| {' | '.join(['---'] * len(headers))} |\n"
    for row in rows:
        table += f"| {' | '.join(str(cell) for cell in row)} |\n"
    return table

# Function to generate Models' Impact Section
def generate_models_section(data):
    section = "## 🧬 Models' Impact\n\n"
    section += f"### **Total Models: {data['total_models']}**\n\n"
    section += f"### **Percentage Ready to Use: {data['ready_percentage']}%**\n\n"

    # Categorize models
    model_cats = {"Single Category": [], "Two Categories": 0, "Three or More Categories": 0}

    for model in data["model_distribution"]:
        tag_count = len(model['Count'].split(", "))

        if tag_count == 1:
            model_cats["Single Category"].append((model['Count'], model['count']))
        elif tag_count == 2:
            model_cats["Two Categories"] += model['count']
        else:
            model_cats["Three or More Categories"] += model['count']

    section += "### Model Categorization\n"
    headers = ["Category", "Count"]
    rows = model_cats["Single Category"]
    rows.append(("Two Categories", model_cats["Two Categories"]))
    rows.append(("Three or More Categories", model_cats["Three or More Categories"]))
    section += format_table(headers, rows)

    # Top 5 recent models
    section += "\n### Most Recent Models\n"
    headers = ["Title", "Contributor", "Date", "Status"]
    recent_models = sorted(data["model_list"], key=lambda x: x["Incorporation Date"], reverse=True)[:5]
    rows = [(model['Title'], model['Contributor'], model['Incorporation Date'], model['Status']) for model in recent_models]
    section += format_table(headers, rows)
    section += "\n👉 [Explore more models on our dashboard](https://ersilia.io)\n"

    return section

# Function to generate Community & Blog Section
def generate_community_section(data, country_names):
    section = "## 🌍 Community & Blog\n\n"
    section += f"### **Countries Represented: {data['countries_represented']}**\n"
    section += f"### **Total Contributors: {data['total_members']}**\n\n"

    # Role distribution
    section += "### Role Distribution\n"
    headers = ["Role", "Count"]
    rows = [(role['Role'], role['Count']) for role in data['role_distribution']]
    section += format_table(headers, rows)

    # Contributors by Country
    section += "\n### Contributors by Country\n"
    headers = ["Country", "Contributors"]
    rows = [(contributor['Country'], contributor['Contributors']) for contributor in data['contributors_by_country']]
    section += format_table(headers, rows)

    return section

# Function to generate Organization Section
def generate_organization_section(data, country_names):
    section = "## 🏢 Organizations\n\n"
    section += f"### **Total Organizations: {data['total_organizations']}**\n\n"

    # Organization Types
    section += "### Organization Types\n"
    headers = ["Type", "Count"]
    rows = [(org['Count'], org['count']) for org in data['organization_types']]
    section += format_table(headers, rows)

    # Organizations by Country
    section += "\n### Organizations by Country\n"
    headers = ["Country", "Total Organizations"]
    rows = [(org['Country'], org['Total Organizations']) for org in data['organizations_by_country']]
    section += format_table(headers, rows)

    return section

# Function to generate Events & Publications Section
def generate_events_section(events_data, publications_data, authors_data, titles_data):
    section = "## 📅 Events & Publications\n\n"
    section += f"### **Total Events: {events_data['total_events']}**\n\n"

    # Events Timeline
    section += "### Event Timeline\n"
    for year, count in sorted([(event['Count'], event['count']) for event in events_data['events_by_year']]):
        section += f"- **{year}**: {count} events\n"

    # Publications Summary
    section += "\n### Publications\n"
    section += f"**Total Publications**: {publications_data['total_publications']}  \n"
    section += f"**Total Citations**: {publications_data['total_citations']}\n\n"

    # Citations Timeline
    section += "\n### Citations Over Time\n"
    for year, avg_citations in sorted([(item['Year'], item['average_Citations']) for item in publications_data['citations_by_year']]):
        section += f"- **{year}**: {avg_citations} average citations\n"

    # OpenAlex paper and author data
    section += "### OpenAlex Paper Match\n"
    section += f"- **Total Papers Queried**: {titles_data['total_titles']}\n"
    section += f"- **Exact Matches Found**: {titles_data['exact_matches']}\n"
    section += f"- **Match Percentage**: {titles_data['match_percentage']}%\n\n"

    section += "### Author Highlights\n"
    section += f"- **Total Authors**: {authors_data['total_authors']}\n"
    section += f"- **Top Author**: {authors_data['top_author']} (H-index: {authors_data['highest_h_index']})\n"

    return section

# Function to generate External Data Section
def generate_external_data_section(external_data):
    section = "## 🌐 External Data\n\n"

    # Disease Statistics Table
    headers = [
        "Disease", 
        "Estimated Total Deaths (based on death rates)", 
        "Most Recent Year", 
        "Deaths in Most Recent Year"
    ]
    rows = [
        (
            stat['disease'], 
            round(stat['total_deaths']), 
            stat['most_recent_year'], 
            round(stat['most_recent_year_deaths'])
        )
        for stat in external_data['disease_statistics']
    ]

    # Add TOTAL row for deaths
    total_deaths = round(sum(stat['total_deaths'] for stat in external_data['disease_statistics']))
    rows.append(("TOTAL", total_deaths, "-", "-"))

    section += "### Disease Statistics\n"
    section += format_table(headers, rows)

    # COVID Data
    covid_stats = external_data['covid_statistics']
    section += "\n### COVID-19 Statistics\n"
    section += f"- **Total Cases**: {covid_stats['total_cases']:,}\n"
    section += f"- **Total Deaths**: {covid_stats['total_deaths']:,}\n"

    return section


# Main function to create README.md
def create_readme(json_data, country_names, output_file):
    models_section = generate_models_section(json_data['models-impact'])
    community_section = generate_community_section(json_data['community'], country_names)
    organization_section = generate_organization_section(json_data['organization'], country_names)
    events_section = generate_events_section(json_data["events"], json_data["publications"], json_data["openalex_authors"], json_data["openalex_titles"])
    external_data_section = generate_external_data_section(json_data['external_data'])

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    readme_content = f"# 📊 Ersilia Statistics Report\n\n"
    readme_content += f"_Last updated: {current_time} GMT_\n\n"
    readme_content += models_section + "\n\n" + community_section + "\n\n" + organization_section + "\n\n"+ events_section + "\n\n" + external_data_section
    readme_content += "\n\n---\nThe full data output that this report is based on can be found in `data/` and `external-data/`. An abbreviated version can be found in `reports/table_stats.json`."


    with open(output_file, 'w') as file:
        file.write(readme_content)

    print(f"README.md has been updated successfully at {output_file}")

# Run the script
if __name__ == "__main__":
    input_json = 'reports/tables_stats.json'  # Path to stats JSON
    countries_csv = 'data/Countries.csv'  # Path to Countries CSV
    output_readme = 'README.md'  # Output README file
    data = load_json(input_json)
    country_names = load_country_names(countries_csv)
    create_readme(data, country_names, output_readme)
