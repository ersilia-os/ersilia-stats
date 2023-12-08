import requests

ORG_NAME = "ersilia-os"

def list_org_repos(org_name):
    # GitHub API endpoint to list organization repositories
    url = f"https://api.github.com/orgs/{org_name}/repos"

    # Make a GET request to the GitHub API
    response = requests.get(url)

    repo_names = []
    # Check if the request was successful
    if response.status_code == 200:
        repos = response.json()
        for repo in repos:
            repo_names += [repo['name']]
    else:
        print("Error:", response.status_code)
    return repo_names


def general_repo_details(owner, repo_name):
    # Endpoint for repository details
    repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    # Get repository details
    repo_response = requests.get(repo_url)
    if repo_response.status_code == 200:
        repo_data = repo_response.json()
        name = repo_data['name']
        description = repo_data['description']
        stars = repo_data['stargazers_count']
        forks = repo_data['forks_count']
        open_issues_count = repo_data['open_issues_count']
        print(f"Name: {repo_name}")
        print(f"Description: {repo_description}")
        print(f"Stars: {repo_stars}")
    else:
        print("Error fetching repository details:", repo_response.status_code)
        return

    # Endpoint for the commits - getting the last page
    commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?per_page=1&page=1"
    commits_response = requests.head(commits_url)

    if commits_response.status_code == 200:
        # Checking if 'Link' is present in headers
        if 'Link' in commits_response.headers:
            # Parsing the 'Link' header to find the last page number
            links = commits_response.headers['Link'].split(',')
            last_page_url = [link for link in links if 'rel="last"' in link][0]
            last_page_number = int(last_page_url.split('page=')[1].split('>')[0])
        else:
            last_page_number = 1

        print(f"Total Commits: {last_page_number}")
    else:
        print("Error fetching commit count:", commits_response.status_code)


# Example usage
#get_repo_details('ersilia-os', 'ersilia')
import requests
from urllib.parse import parse_qs, urlparse

def get_commits_count(owner_name: str, repo_name: str) -> int:
    """
    Returns the number of commits to a GitHub repository.
    """
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/commits?per_page=1"
    r = requests.get(url)
    links = r.links
    rel_last_link_url = urlparse(links["last"]["url"])
    rel_last_link_url_args = parse_qs(rel_last_link_url.query)
    rel_last_link_url_page_arg = rel_last_link_url_args["page"][0]
    commits_count = int(rel_last_link_url_page_arg)
    return commits_count

get_commits_count("ersilia-os", "ersilia")