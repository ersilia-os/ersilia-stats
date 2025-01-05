import json
import pandas as pd
from datetime import datetime
from calculate_stats import create_json

# Function to load JSON data
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to load country names from CSV and map IDs to country names
def load_country_names(csv_path):
    countries_df = pd.read_csv(csv_path)
    return dict(zip(countries_df['id'], countries_df['Country']))

# Function to format a scrollable table in Markdown
def format_table(headers, rows):
    """Generate a Markdown table wrapped in a collapsible section for large tables."""
    table = f"| {' | '.join(headers)} |\n"
    table += f"| {' | '.join(['---'] * len(headers))} |\n"
    for row in rows:
        table += f"| {' | '.join(str(cell) for cell in row)} |\n"
    return table

# Function to wrap content in a collapsible section
def collapsible_section(title, content):
    return f"<details>\n<summary>{title}</summary>\n\n{content}\n\n</details>\n"


# Function to generate Models' Impact Section
def generate_models_section(data):
    highlights = f"- **Total Models:** {data['total_models']}\n"
    highlights += f"- **Percentage Ready to Use:** {data['ready_percentage']}%\n\n"

    # Model categorization
    headers = ["Category", "Count"]
    rows = [(item["Category"], item["count"]) for item in data["model_distribution"]]
    model_table = format_table(headers, rows)
    model_table_section = collapsible_section("Model Categorization", model_table)

    # Most recent models
    headers = ["Title", "Contributor", "Date", "Status"]
    recent_models = sorted(data["model_list"], key=lambda x: x["Incorporation Date"], reverse=True)[:5]
    rows = [(model['Title'], model['Contributor'], model['Incorporation Date'], model['Status']) for model in recent_models]
    recent_models_table = format_table(headers, rows)
    recent_models_section = collapsible_section("Most Recent Models", recent_models_table)

    section = "## 🧬 Models' Impact\n\n"
    section += highlights + model_table_section + "\n" + recent_models_section
    section += "\n👉 [Explore more models on our dashboard](https://ersilia.io/model-hub)\n"
    return section

# Function to generate Community & Blog Section
def generate_community_section(data, country_names):
    highlights = f"- **Countries Represented:** {data['countries_represented']}\n"
    highlights += f"- **Total Contributors:** {data['total_members']}\n\n"

    # Role distribution
    headers = ["Role", "Count"]
    rows = [(role['Role'], role['Count']) for role in data['role_distribution']]
    role_table = format_table(headers, rows)
    role_table_section = collapsible_section("Role Distribution", role_table)

    # Duration of involvement
    headers = ["Duration", "Count"]
    rows = [(duration['Duration'], duration['Count']) for duration in data['duration_distribution']]
    duration_table = format_table(headers, rows)
    duration_table_section = collapsible_section("Duration of Involvement", duration_table)

    # Contributors by country
    headers = ["Country", "Contributors"]
    rows = [(country_names.get(item['Country'], item['Country']), item['Contributors']) for item in data['contributors_by_country']]
    rows.sort(key=lambda x: x[1], reverse=True)
    contributors_table = format_table(headers, rows)
    contributors_table_section = collapsible_section("Contributors by Country", contributors_table)

    section = "## 🌍 Community & Blog\n\n"
    section += highlights + role_table_section + "\n" + duration_table_section + "\n" + contributors_table_section
    return section

# Function to generate Blogposts Section
def generate_blogposts_section(data):
    highlights = f"- **Total Blogposts:** {data['total_blogposts']}\n\n"

    # Blogpost topics distribution
    headers = ["Topic", "Count", "Percentage"]
    rows = [(topic['Tag'], topic['Count'], f"{topic['Percentage']:.2f}%") for topic in data['tag_distribution']]
    topics_table = format_table(headers, rows)
    topics_section = collapsible_section("Blogpost Topics Distribution", topics_table)

    # Blogposts over time
    headers = ["Year", "Quarter", "Post Count"]
    rows = [(round(post['Year']), post['Quarter'], post['Post Count']) for post in data['posts_over_time']]
    time_table = format_table(headers, rows)
    time_section = collapsible_section("Blogposts Over Time", time_table)

    section = "## 📝 Blogposts\n\n"
    section += highlights + topics_section + "\n" + time_section
    return section


# Function to generate Organizations Section
def generate_organization_section(data, country_names):
    highlights = f"- **Total Organizations:** {data['total_organizations']}\n\n"

    # Organization types
    headers = ["Type", "Count"]
    rows = [(org['Type'], org['Count']) for org in data['organization_types']]
    org_types_table = format_table(headers, rows)
    org_types_section = collapsible_section("Organization Types", org_types_table)

    # Organizations by country
    headers = ["Country", "Total Organizations"]
    rows = [(country_names.get(org['Country'], org['Country']), org['Total Organizations']) for org in data['organizations_by_country']]
    rows.sort(key=lambda x: x[1], reverse=True)
    org_country_table = format_table(headers, rows)
    org_country_section = collapsible_section("Organizations by Country", org_country_table)

    section = "## 🏢 Organizations in Ersilia's Network\n\n"
    section += highlights + org_types_section + "\n" + org_country_section
    return section

# Function to generate Author Highlights Section
def generate_authors_section(authors_data):
    highlights = f"- **Total Authors:** {authors_data['total_authors']}\n"
    highlights += f"- **Top Author:** {authors_data['top_author']} (H-index: {authors_data['highest_h_index']})\n\n"

    # Table of top authors
    headers = ["Name", "Ersilia Pubs", "H-index", "Total Pubs"]
    top_authors = authors_data["author_highlights"][:3]  # Display top 3 authors
    rows = [(author['Name'], author['ersilia_publications'], author['H-index'], author['total_publications']) for author in top_authors]
    authors_table = format_table(headers, rows)
    authors_section = collapsible_section("Top Authors", authors_table)

    # Individual publications for top authors
    publication_sections = ""
    for author in top_authors:
        author_name = author['Name']
        pub_headers = ["Title", "Year", "URL"]
        pub_rows = [(pub.get("title", "Unknown"), pub.get("year", ""), pub.get("url", "")) for pub in author.get("ersilia_pub_details", [])]
        pub_table = format_table(pub_headers, pub_rows)
        publication_sections += collapsible_section(f"{author_name} - See Publications ⬇️", pub_table)

    section = "## 🏅 Author Highlights\n\n"
    section += highlights + authors_section + "\n" + publication_sections
    return section

# Function to generate External Data Section
def generate_external_data_section(external_data):
    # Disease statistics
    headers = ["Disease", "Estimated Total Cases", "Estimated Total Deaths"]
    rows = []
    
    for stat in external_data['disease_statistics']:
        disease = stat['disease']
        total_cases = stat.get('total_cases', '-')
        total_deaths = stat.get('total_deaths', '-')
        
        # Format numbers with commas if they exist
        total_cases = f"{total_cases:,}" if isinstance(total_cases, int) else total_cases
        total_deaths = f"{total_deaths:,}" if isinstance(total_deaths, int) else total_deaths
        
        rows.append((disease, total_cases, total_deaths))
    
    disease_table = format_table(headers, rows)
    disease_section = collapsible_section("Disease Statistics", disease_table)

    section = "## 🌐 External Data\n\n"
    section += disease_section
    return section


# Main function to create README.md
def create_readme(json_data, country_names, output_file):
    models_section = generate_models_section(json_data['models-impact'])
    community_section = generate_community_section(json_data['community'], country_names)
    blogposts_section = generate_blogposts_section(json_data['blogposts-events'])
    organization_section = generate_organization_section(json_data['organization'], country_names)
    authors_section = generate_authors_section(json_data['openalex_authors'])
    external_data_section = generate_external_data_section(json_data['external_data'])

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    readme_content = f"# 📊 Ersilia Statistics Report\n\n"
    readme_content += f"_Last updated: {current_time} GMT_\n\n"
    readme_content += models_section + "\n\n" + community_section + "\n\n" + blogposts_section + "\n\n"
    readme_content += organization_section + "\n\n" + authors_section + "\n\n" + external_data_section
    readme_content += "\n\n---\nThe full data output that this report is based on can be found in `data/` and `external-data/`. An abbreviated version can be found in `reports/table_stats.json`."

    with open(output_file, 'w') as file:
        file.write(readme_content)

    print(f"README.md has been updated successfully at {output_file}")

# Run the script
if __name__ == "__main__":
    input_json = 'reports/tables_stats.json'  # Path to stats JSON
    countries_csv = 'data/Countries.csv'  # Path to Countries CSV
    output_readme = 'README.md'  # Output README file

    create_json()
    data = load_json(input_json)
    country_names = load_country_names(countries_csv)
    create_readme(data, country_names, output_readme)