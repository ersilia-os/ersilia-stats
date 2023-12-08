import requests

ORG_NAME = "ersilia-os"

def _list_org_repos(org_name):
    # GitHub API endpoint to list organization repositories
    url = f"https://api.github.com/orgs/{org_name}/repos"
    repositories = []
    response = requests.get(url)
    response.raise_for_status()
    repositories.extend(response.json())
    while 'next' in response.links:
        next_url = response.links['next']['url']
        response = requests.get(next_url)
        response.raise_for_status()
        repositories.extend(response.json())
    repo_names = []
    for repo in repositories:
            repo_names += [repo['name']]
    return repo_names

def _get_first_commit(owner, repo_name):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    req = requests.get(url)
    json_data = req.json()
    if req.headers.get('Link'):
        page_url = req.headers.get('Link').split(',')[1].split(';')[0].split('<')[1].split('>')[0]
        req_last_commit = requests.get(page_url)
        first_commit = req_last_commit.json()
        first_commit_hash = first_commit[-1]['sha']
    else:
        first_commit_hash = json_data[-1]['sha']
    return first_commit_hash

def _get_all_commits_count(owner, repo_name, sha):
    first_commit_hash = _get_first_commit(owner, repo_name)
    compare_url = f"https://api.github.com/repos/{owner}/{repo_name}/compare/{first_commit_hash}...{sha}"
    commit_req = requests.get(compare_url)
    commit_count = commit_req.json()['total_commits'] + 1
    return commit_count

def general_repo_details(owner, repo_name):
    repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    repo_response = requests.get(repo_url)
    repo_info ={}
    if repo_response.status_code == 200:
        repo_data = repo_response.json()
        name = repo_data['name']
        description = repo_data['description']
        stars = repo_data['stargazers_count']
        forks = repo_data['forks']
        open_issues = repo_data['open_issues']
        subscribers = repo_data['subscribers_count']
        contributors = []
        contributors_resp = requests.get(repo_data["contributors_url"])
        contributors.extend(contributors_resp.json())
        while 'next' in contributors_resp.links:
            next_url = contributors_resp.links['next']['url']
            contributors_resp = requests.get(next_url)
            contributors_resp.raise_for_status()
            contributors.extend(contributors_resp.json())
        contributor_names = []
        for i in range(len(contributors)):
            contr_name = contributors[i]["login"]
            contributor_names += contr_name
        issues_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/issues")
        issues = issues_resp.json()
        total_issues = issues[0]["number"]
        last_commit_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/commits")
        last_commit = last_commit_resp.json()
        last_commit_sha = last_commit[0]["sha"]
        total_commits = _get_all_commits_count(owner, repo_name, last_commit_sha)
        repo_info["name"]=name
        repo_info["description"]= description
        repo_info["stars"]= stars
        repo_info["forks"]= forks
        repo_info["total_issues"]= total_issues
        repo_info["open_issues"]= open_issues
        repo_info["subscribers"]=subscribers
        repo_info["contributors"]=len(contributors)
        repo_info["contributor_names"]=contributor_names
        repo_info["total_commits"]=total_commits
        return
    else:
        print("Error fetching repository details:", repo_response.status_code)
        return

repo_details = general_repo_details(ORG_NAME, "eos4wt0")
print(repo_details)