import requests
import random
import collections
import sys
import os
from pyairtable import Api

github_api_token = sys.argv[1]
airtable_api_key = sys.argv[2]

BASE_ID = "app1iYv78K6xbHkmL"
TABLE_ID = "tbluZtI3W9pseCSPH"

headers = {"Authorization": "Bearer %s" % github_api_token}

ORG_NAME = "ersilia-os"


def _list_org_repos(org_name):
    # GitHub API endpoint to list organization repositories
    url = f"https://api.github.com/orgs/{org_name}/repos"
    repositories = []
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    repositories.extend(response.json())
    while "next" in response.links:
        next_url = response.links["next"]["url"]
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        repositories.extend(response.json())
    repo_names = []
    for repo in repositories:
        if repo["name"] == ".github":
            continue
        repo_names += [repo["name"]]
    return repo_names


def _get_first_commit(owner, repo_name):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    req = requests.get(url, headers=headers)
    json_data = req.json()
    if req.headers.get("Link"):
        page_url = (
            req.headers.get("Link")
            .split(",")[1]
            .split(";")[0]
            .split("<")[1]
            .split(">")[0]
        )
        req_last_commit = requests.get(page_url, headers=headers)
        first_commit = req_last_commit.json()
        first_commit_hash = first_commit[-1]["sha"]
    else:
        first_commit_hash = json_data[-1]["sha"]
    return first_commit_hash


def _get_all_commits_count(owner, repo_name, sha):
    try:
        first_commit_hash = _get_first_commit(owner, repo_name)
        compare_url = f"https://api.github.com/repos/{owner}/{repo_name}/compare/{first_commit_hash}...{sha}"
        commit_req = requests.get(compare_url, headers=headers)
        commit_count = commit_req.json()["total_commits"] + 1
        return commit_count
    except:
        return 0


def _get_github_title(repo):
    url = "https://raw.githubusercontent.com/{0}/{1}/main/README.md".format(ORG_NAME, repo)
    result = requests.get(url)
    if result.status_code == 200:
        text = result.text
    else:
        text = None
    if text is None:
        url = "https://raw.githubusercontent.com/{0}/{1}/master/README.md".format(ORG_NAME, repo)
        result = requests.get(url)
        if result.status_code != 200:
            return None
        text = result.text
    if text is None:
        return None
    lines = text.split(os.linesep)
    for l in lines:
        if l.startswith("# "):
            return l.split("# ")[1]
    return None


def general_repo_details(owner, repo_name):
    repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    repo_response = requests.get(repo_url, headers=headers)
    repo_info = {}
    if repo_response.status_code == 200:
        repo_data = repo_response.json()
        name = repo_data["name"]
        description = repo_data["description"]
        stars = repo_data["stargazers_count"]
        forks = repo_data["forks"]
        open_issues = repo_data["open_issues"]
        subscribers = repo_data["subscribers_count"]
        contributors = []
        contributors_resp = requests.get(repo_data["contributors_url"], headers=headers)
        contributors.extend(contributors_resp.json())
        while "next" in contributors_resp.links:
            next_url = contributors_resp.links["next"]["url"]
            contributors_resp = requests.get(next_url, headers=headers)
            contributors_resp.raise_for_status()
            contributors.extend(contributors_resp.json())
        contributor_names = []
        for i in range(len(contributors)):
            contr_name = contributors[i]["login"]
            contributor_names += [contr_name]
        last_commit_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo_name}/commits", headers=headers
        )
        last_commit = last_commit_resp.json()
        last_commit_sha = last_commit[0]["sha"]
        total_commits = _get_all_commits_count(owner, repo_name, last_commit_sha)
        repo_info["name"] = name
        repo_info["title"] = _get_github_title(repo_name)
        repo_info["description"] = description
        repo_info["stars"] = stars
        repo_info["forks"] = forks
        repo_info["open_issues"] = open_issues
        repo_info["subscribers"] = subscribers
        repo_info["contributors"] = len(contributors)
        repo_info["contributor_names"] = contributor_names
        repo_info["total_commits"] = total_commits
        return repo_info
    else:
        print("Error fetching repository details:", repo_response.status_code)
        return


all_repos = _list_org_repos(ORG_NAME)
random.shuffle(all_repos)

repos_data = {}

for repo in all_repos[:100]:
    data = general_repo_details("ersilia-os", repo)
    print(data)
    repos_data[repo] = data

repo_description = {}
repo_title = {}
repo_stars = collections.defaultdict(int)
repo_forks = collections.defaultdict(int)
repo_open_issues = collections.defaultdict(int)
repo_subscribers = collections.defaultdict(int)
repo_contributor_names = collections.defaultdict(list)
repo_total_commits = collections.defaultdict(int)

repo_keys = []
for repo, v in repos_data.items():
    if len(repo) == 7 and repo.startswith("eos"):
        repo = "eos"
        repo_description[repo] = "Aggregate of Ersilia models"
        repo_title[repo] = "Ersilia model"
    else:
        repo_description[repo] = v["description"]
        repo_title[repo] = v["title"]
    repo_keys += [repo]
    repo_stars[repo] += v["stars"]
    repo_forks[repo] += v["forks"]
    repo_open_issues[repo] += v["open_issues"]
    repo_subscribers[repo] += v["subscribers"]
    repo_contributor_names[repo] += v["contributor_names"]
    repo_total_commits[repo] += v["total_commits"]

repo_contributor_names = dict(
    (k, sorted(set(v))) for k, v in repo_contributor_names.items()
)
repo_contributors = dict((k, len(v)) for k, v in repo_contributor_names.items())

repo_keys = sorted(set(repo_keys))


def get_available_record_ids_from_airtable():
    api = Api(airtable_api_key)
    table = api.table(BASE_ID, TABLE_ID)
    records = table.all()
    data = {}
    for r in records:
        name = r["fields"]["Name"]
        data[name] = r["id"]
    return data


available_repos = get_available_record_ids_from_airtable()
print(available_repos)

api = Api(airtable_api_key)
table = api.table(BASE_ID, TABLE_ID)

for repo in repo_keys:
    print("Checking", repo)
    data = {
        "Name": repo,
        "Title": repo_title[repo],
        "Description": repo_description[repo],
        "Stars": repo_stars[repo],
        "Forks": repo_forks[repo],
        "Open Issues": repo_open_issues[repo],
        "Subscribers": repo_subscribers[repo],
        "Total Commits": repo_total_commits[repo],
        "Contributors": repo_contributors[repo],
        "Contributor Names": ", ".join(repo_contributor_names[repo]),
    }
    if repo in available_repos.keys():
        record_id = available_repos[repo]
        table.update(record_id, data)
    else:
        table.create(data)

def check_repository_exists(user, repo):
    url = f"https://github.com/{user}/{repo}"
    print("Checking", url)
    response = requests.get(url, headers=headers)
    print("Response", response.status_code)
    if response.status_code == 200:
        return True
    else:
        return False

def delete_airtable_records(record_ids):
    api = Api(airtable_api_key)
    table = api.table(BASE_ID, TABLE_ID)
    for record_id in record_ids:
        table.delete(record_id)

record_ids_to_delete = []
for k,v in available_repos.items():
    if k == "eos":
        continue
    if k not in all_repos:
        if not check_repository_exists(ORG_NAME, k):
            record_ids_to_delete += [v]

delete_airtable_records(record_ids_to_delete)
