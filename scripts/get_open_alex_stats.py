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
            author_data = data['results'][0]
            return author_data
        else:
            print(f"No data found for {author_name}.")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {author_name}: {e}")
        return None

def print_impressive_stats(author_name, author_data):
    print(f"\n--- Impressive Stats for {author_name} ---")
    
    name = author_data.get('display_name', 'N/A')
    print(f"Name: {name}")
    
    num_works = author_data.get('works_count', 'N/A')
    print(f"Number of Works: {num_works}")
    
    citation_count = author_data.get('cited_by_count', 'N/A')
    print(f"Total Citations: {citation_count}")
    
    h_index = author_data.get('summary_stats', {}).get('h_index', 'N/A')
    print(f"H-index: {h_index}")
    
    counts_by_year = author_data.get('counts_by_year', [])
    if counts_by_year:
        first_pub_year = min(counts_by_year, key=lambda x: x['year'])['year']
    else:
        first_pub_year = 'N/A'
    print(f"First Published Year: {first_pub_year}")
    
    affiliations = author_data.get('affiliations', [])
    if affiliations:
        for affiliation in affiliations:
            institution = affiliation.get('institution', {})
            display_name = institution.get('display_name', 'N/A')
            print(f"Affiliation: {display_name}")
    else:
        print("Affiliation: N/A")
    
    print("\n--- End of Stats ---")

def write_titles_to_csv(results, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['Title', 'Match']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

def write_authors_to_csv(authors_data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['Author', 'Name', 'Number of Works', 'Total Citations', 'H-index', 'First Published Year', 'Affiliation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for author_name, author_data in authors_data.items():
            if author_data:
                name = author_data.get('display_name', 'N/A')
                num_works = author_data.get('works_count', 'N/A')
                citation_count = author_data.get('cited_by_count', 'N/A')
                h_index = author_data.get('summary_stats', {}).get('h_index', 'N/A')
                counts_by_year = author_data.get('counts_by_year', [])
                if counts_by_year:
                    first_pub_year = min(counts_by_year, key=lambda x: x['year'])['year']
                else:
                    first_pub_year = 'N/A'
                affiliations = author_data.get('affiliations', [])
                if affiliations:
                    affiliation_names = [affiliation.get('institution', {}).get('display_name', 'N/A') for affiliation in affiliations]
                    affiliation = ', '.join(affiliation_names)
                else:
                    affiliation = 'N/A'
                writer.writerow({
                    'Author': author_name,
                    'Name': name,
                    'Number of Works': num_works,
                    'Total Citations': citation_count,
                    'H-index': h_index,
                    'First Published Year': first_pub_year,
                    'Affiliation': affiliation
                })

if __name__ == "__main__":
    file_path = '../data/Publications.csv'
    titles_output_path = './open_alex_data_match/titles_results.csv'
    authors_output_path = './open_alex_data_match/authors_results.csv'

    while True:
        print("\nChoose an option:")
        print("1. Search OpenAlex for the titles")
        print("2. Search OpenAlex for the authors")
        print("3. Exit")
        
        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            total_titles, exact_matches, results = get_openalex_data(file_path)
            write_titles_to_csv(results, titles_output_path)

            print(f"Total titles searched: {total_titles}")
            print(f"Exact matches found: {exact_matches}")
            if total_titles > 0:
                percentage = (exact_matches / total_titles) * 100
                print(f"Percentage of exact matches: {percentage:.2f}%")
        
        elif choice == '2':
            authors_set = get_authors_set(file_path)
            print(f"Total authors: {len(authors_set)}")

            authors_data = {}
            for author in authors_set:
                print(f"\nQuerying data for {author}...")
                author_data = query_openalex_for_author(author)
                authors_data[author] = author_data
                if author_data:
                    print_impressive_stats(author, author_data)
                
                time.sleep(0.1)
            
            write_authors_to_csv(authors_data, authors_output_path)

        elif choice == '3':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
