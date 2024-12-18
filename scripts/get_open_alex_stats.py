import requests
import csv
import time
import os

def search_openalex(title):
    url = f"https://api.openalex.org/works?search={title}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        for topic in data['results']:
            try:
                if topic['display_name'].lower() == title.lower():
                    return True
            except AttributeError:
                continue
    return False

def get_openalex_data(file_path):
    total_titles = 0
    exact_matches = 0
    results = []
    
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            title = row['Title']
            total_titles += 1
            match = search_openalex(title)
            if match:
                exact_matches += 1
            results.append({'Title': title, 'Match': match})
    
    return total_titles, exact_matches, results

def get_authors_set(file_path):
    authors_set = set()
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            authors = row['Authors'].split(',')
            for author in authors:
                author = author.strip()
                if author.lower() != 'et al':
                    authors_set.add(author)
    return authors_set

def query_openalex_for_author(author_name):
    search_term = author_name.replace(" ", "%20")
    url = f"https://api.openalex.org/authors?search={search_term}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'meta' in data and data['meta']['count'] > 0:
            return data['results'][0]
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {author_name}: {e}")
        return None

def write_titles_to_csv(results, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['Title', 'Match']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

def write_authors_to_csv(authors_data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['Author', 'Name', 'Number of Works', 'Total Citations', 'H-index', 'First Published Year', 'Affiliation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        for author_name, author_data in authors_data.items():
            if author_data:
                counts_by_year = author_data.get('counts_by_year', [])
                first_pub_year = min(counts_by_year, key=lambda x: x['year'])['year'] if counts_by_year else 'N/A'
                affiliations = author_data.get('affiliations', [])
                affiliation = ', '.join([a['institution']['display_name'] for a in affiliations]) if affiliations else 'N/A'
                writer.writerow({
                    'Author': author_name,
                    'Name': author_data.get('display_name', 'N/A'),
                    'Number of Works': author_data.get('works_count', 'N/A'),
                    'Total Citations': author_data.get('cited_by_count', 'N/A'),
                    'H-index': author_data.get('summary_stats', {}).get('h_index', 'N/A'),
                    'First Published Year': first_pub_year,
                    'Affiliation': affiliation
                })

if __name__ == "__main__":
    publications_path = 'data/Publications.csv'
    titles_output = 'external-data/titles_results.csv'
    authors_output = 'external-data/authors_results.csv'

    print("Querying OpenAlex for titles...")
    total_titles, exact_matches, results = get_openalex_data(publications_path)
    write_titles_to_csv(results, titles_output)

    print(f"Total titles: {total_titles}, Exact matches: {exact_matches}")

    print("\nQuerying OpenAlex for authors...")
    authors_set = get_authors_set(publications_path)
    authors_data = {}
    for author in authors_set:
        print(f"Querying data for {author}...")
        authors_data[author] = query_openalex_for_author(author)
        time.sleep(0.1)
    write_authors_to_csv(authors_data, authors_output)
