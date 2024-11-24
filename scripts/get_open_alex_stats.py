import requests
import csv
import time

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
    
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            title = row['Title']
            total_titles += 1
            if search_openalex(title):
                exact_matches += 1
    
    return total_titles, exact_matches

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

# Define a function to query the OpenAlex API for each author
def query_openalex_for_author(author_name):
    # Format the author name to be URL-encoded
    search_term = author_name.replace(" ", "%20")
    url = f"https://api.openalex.org/authors?search={search_term}"
    
    # Send the request to the API
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)
        
        # Get the data from the response
        data = response.json()
        
        # Check if the data contains authors
        if 'meta' in data and data['meta']['count'] > 0:
            author_data = data['results'][0]  # Get the first author result
            return author_data
        else:
            print(f"No data found for {author_name}.")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {author_name}: {e}")
        return None

# Function to print impressive stats for each author
def print_impressive_stats(author_name, author_data):
    print(f"\n--- Impressive Stats for {author_name} ---")
    
    # Author basic info
    name = author_data.get('display_name', 'N/A')
    print(f"Name: {name}")
    
    # Number of works (publications)
    num_works = author_data.get('works_count', 'N/A')
    print(f"Number of Works: {num_works}")
    
    # Citation count (total citations)
    citation_count = author_data.get('cited_by_count', 'N/A')
    print(f"Total Citations: {citation_count}")
    
    # H-index (if available)
    h_index = author_data.get('summary_stats', {}).get('h_index', 'N/A')
    print(f"H-index: {h_index}")
    
    # Year of first publication
    counts_by_year = author_data.get('counts_by_year', [])
    if counts_by_year:
        first_pub_year = min(counts_by_year, key=lambda x: x['year'])['year']
    else:
        first_pub_year = 'N/A'
    print(f"First Published Year: {first_pub_year}")
    
    # Affiliation (if available)
    affiliations = author_data.get('affiliations', [])
    if affiliations:
        for affiliation in affiliations:
            institution = affiliation.get('institution', {})
            display_name = institution.get('display_name', 'N/A')
            print(f"Affiliation: {display_name}")
    else:
        print("Affiliation: N/A")
    
    # Other possible stats (optional)
    # Number of co-authors (if available)
    # co_authors_count = len(author_data.get('co_authors', []))
    # print(f"Number of Co-authors: {co_authors_count}")
    
    print("\n--- End of Stats ---")


if __name__ == "__main__":
    file_path = '../data/Publications.csv'

    while True:
        print("\nChoose an option:")
        print("1. Search OpenAlex for the titles")
        print("2. Search OpenAlex for the authors")
        print("3. Exit")
        
        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            total_titles, exact_matches = get_openalex_data(file_path)

            print(f"Total titles searched: {total_titles}")
            print(f"Exact matches found: {exact_matches}")
            if total_titles > 0:
                percentage = (exact_matches / total_titles) * 100
                print(f"Percentage of exact matches: {percentage:.2f}%")
        
        elif choice == '2':
            authors_set = get_authors_set(file_path)
            print(f"Total authors: {len(authors_set)}")

            for author in authors_set:
                print(f"\nQuerying data for {author}...")
                author_data = query_openalex_for_author(author)
                if author_data:
                    print_impressive_stats(author, author_data)
                
                # Sleep to avoid hitting rate limits
                time.sleep(0.1)  # Adjust this value if necessary

        elif choice == '3':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

