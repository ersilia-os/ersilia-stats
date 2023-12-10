import sys
import requests
import time
import random
from pyairtable import Api


airtable_api_key = sys.argv[1]

BASE_ID = "app1iYv78K6xbHkmL"
TABLE_ID = "tbljYubYjWAtO1ab8"


def get_publications_records_from_airtable():
    api  = Api(airtable_api_key)
    table = api.table(BASE_ID, TABLE_ID)
    records = table.all()
    data = []
    for r in records:
        gs_id = None
        if "Google Scholar ID" in r["fields"]:
            gs_id = r["fields"]["Google Scholar ID"]
        data += [(r["id"], gs_id)]
    return data


def get_google_scholar_citations_from_cluster_id(cluster_id):
    url = "https://scholar.google.com/scholar?cluster={0}&hl=en".format(cluster_id)
    print(url)
    result = requests.get(url)
    text = result.text
    citations = int(text.split(">Cited by ")[1].split("<")[0])
    return citations


def get_citations_from_records(data):
    results = []
    for d in data:
        print(data)
        if d[1] is not None:
            try:
                v = get_google_scholar_citations_from_cluster_id(d[1])
                results += [(d[0], v)]
            except:
                print("Failed to fetch citations data")
            time.sleep(5)
    return results


def update_citations_to_airtable(data):
    api  = Api(airtable_api_key)
    table = api.table(BASE_ID, TABLE_ID)
    for d in data:
        if d[1] is not None:
            table.update(d[0], {"Citations": d[1]})


data = get_publications_records_from_airtable()
random.shuffle(data)
data = get_citations_from_records(data)
update_citations_to_airtable(data)
