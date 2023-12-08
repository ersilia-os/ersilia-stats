import requests


def get_google_scholar_citations_from_cluster_id(cluster_id):
    url = "https://scholar.google.com/scholar?cluster={0}&hl=en".format(cluster_id)
    result = requests.get(url)
    text = result.text
    citations = text.split(">Cited by ")[1].split("<")[0]
    return citations


c = get_google_scholar_citations_from_cluster_id("13658887735425716")
print(c)