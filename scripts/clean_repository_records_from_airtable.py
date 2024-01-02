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
        repo_names += [repo["name"]]
    return repo_names

all_repos = _list_org_repos(ORG_NAME)

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

def check_repository_exists(user, repo):
    url = f"https://github.com/{user}/{repo}"
    print("Checking", url)
    response = requests.get(url)
    return response.status_code == 200

for k,v in available_repos.items():
    if k not in all_repos:
        if not check_repository_exists(ORG_NAME, k):
            print(k, "is not there")
