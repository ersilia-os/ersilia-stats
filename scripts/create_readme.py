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
    section += f"### **Total Models: {data['total-models']}**\n\n"
    section += f"### **Percentage Ready to Use: {data['ready-percentage']}%**\n\n"

    # Categorize models
    model_cats = {"Single Category": [], "Two Categories": 0, "Three or More Categories": 0}

    for model in data["model-distribution"]:
        clean_tag = model['Count'].strip("[]").replace("'", "")  # Clean up tags
        tag_count = len(model['Count'].split(","))

        if tag_count == 1:
            model_cats["Single Category"].append((clean_tag, model['count']))
        elif tag_count == 2:
            model_cats["Two Categories"] += model['count']
        else:
            model_cats["Three or More Categories"] += model['count']

    # Generate polished model categorization table
    section += "### Model Categorization\n"
    headers = ["Category", "Count"]
    rows = model_cats["Single Category"]  # Single Category rows
    rows.append(("Two Categories", model_cats["Two Categories"]))
    rows.append(("Three or More Categories", model_cats["Three or More Categories"]))
    section += format_table(headers, rows)

    # Top 5 recent models
    section += "\n### Most Recent Models\n"
    headers = ["Title", "Contributor", "Date", "Status"]
    recent_models = sorted(data["model-list"], key=lambda x: x["Incorporation Date"], reverse=True)[:5]
    rows = [(model['Title'], model['Contributor'], model['Incorporation Date'], model['Status']) for model in recent_models]
    section += format_table(headers, rows)
    section += "\n👉 [Explore more models on our dashboard](https://ersilia.io)\n"

    return section

# Function to generate Community & Blog Section
def generate_community_section(data, country_names):
    section = "## 🌍 Community & Blog\n\n"
    section += f"### **Countries Represented: {data['countries-represented']}**\n"
    section += f"### **Total Contributors: {data['total-members']}**\n\n"

    # Role distribution
    role_counts = {}
    role_counts = {"Single Role": {}, "Two Roles": 0, "Three or More Roles": 0}
    for role in data['role-distribution']:
        clean_role = ', '.join(eval(role['Count'])) if '[' in role['Count'] else role['Count']
        role_count = len(eval(role['Count'])) if '[' in role['Count'] else 1
        
        if role_count == 1:
            role_counts["Single Role"][clean_role] = role_counts["Single Role"].get(clean_role, 0) + role['count']
        elif role_count == 2:
            role_counts["Two Roles"] += role['count']
        else:
            role_counts["Three or More Roles"] += role['count']

    section += "### Role Distribution\n"
    headers = ["Role", "Count"]
    rows = list(role_counts["Single Role"].items()) + [
        ("Two Roles", role_counts["Two Roles"]),
        ("Three or More Roles", role_counts["Three or More Roles"]),
    ]
    section += format_table(headers, rows)

    # Contributors by Country
    section += "\n### Contributors by Country\n"
    headers = ["Country", "Contributors"]
    rows = [
        (country_names.get(contributor['Country'].strip("[]").strip("'"), "Unknown Country"), contributor['Contributors'])
        for contributor in data['contributors-by-country']
    ]
    section += format_table(headers, rows)
    return section

# Function to generate Events & Publications Section
def generate_events_section(events_data, publications_data, authors_data, titles_data):
    section = "## 📅 Events & Publications\n\n"
    section += f"### **Total Events: {events_data['total-events']}**\n\n"

    # Events Timeline
    section += "### Event Timeline\n"
    for year, count in sorted([(event['Count'], event['count']) for event in events_data['events-by-year']]):
        section += f"- **{year}**: {count} events\n"

    # Publications Summary
    section += "\n### Publications\n"
    section += f"**Total Publications**: {publications_data['total-publications']}  \n"
    section += f"**Total Citations**: {publications_data['total-citations']}\n\n"

    # Citations Timeline
    section += "\n### Citations Over Time\n"
    for year, avg_citations in sorted([(item['Year'], item['average_Citations']) for item in publications_data['citations-by-year']]):
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

# Main function to create README.md
def create_readme(json_data, country_names, output_file):
    models_section = generate_models_section(json_data["models-impact"])
    community_section = generate_community_section(json_data["community"], country_names)
    events_section = generate_events_section(json_data["events"], json_data["publications"], json_data["openalex_authors"], json_data["openalex_titles"])

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    readme_content = f"# 📊 Ersilia Statistics Report\n\n"
    readme_content += f"_Last updated: {current_time} GMT_\n\n"
    readme_content += models_section + "\n\n" + community_section + "\n\n" + events_section + "\n\nThe full data output that this report is based on can be found in `data/` and `external-data/`. An abbreviated version can be found in `reports/table_stats.json`."

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
