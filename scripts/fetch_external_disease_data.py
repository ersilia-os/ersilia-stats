from itertools import tee
from lib2to3.pytree import convert
from operator import contains
import os
from unittest import case
from networkx import hits
import pandas as pd
import json

# Directory for storing external data
DATA_DIR = "external-data"
os.makedirs(DATA_DIR, exist_ok=True)

# OWID datasets
owid_datasets = {
    # HIV/AIDS
    "hivaids_deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-hivaids-who.csv",
    # COVID
    "covid_cases_deaths.csv": "https://ourworldindata.org/grapher/cumulative-deaths-and-cases-covid-19.csv",
    # MALARIA
    "malaria_deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-malaria-who.csv",
    # TUBERCULOSIS
    "tb_cases.csv": "https://ourworldindata.org/grapher/number-of-tuberculosis-cases.csv",
    "tb_deaths.csv": "https://ourworldindata.org/grapher/tuberculosis-deaths-who.csv",
    # CANCER
    "cancer_deaths.csv": "https://ourworldindata.org/grapher/deaths-from-cancer-who.csv",
    # MEASLES
    "measles_cases.csv": "https://ourworldindata.org/grapher/reported-cases-of-measles.csv",
    # POLIO
    "polio_cases.csv": "https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases.csv",
}

# WHO DATASETS
who_datasets = {
    # MALARIA
    "malaria_cases.csv": "https://ghoapi.azureedge.net/api/MALARIA_EST_CASES?$filter=SpatialDimType%20eq%20%27COUNTRY%27"
}

disease_stats = {}
# Function to fetch OWID datasets
def fetch_owid_data(file_name, url):
    try:
        print(f"Fetching OWID dataset: {file_name}")
        df = pd.read_csv(url, storage_options={"User-Agent": "OWID Data Fetch/1.0"})
        df = df[df['Entity'] == 'World']
        output_path = os.path.join(DATA_DIR, file_name)
        df.to_csv(output_path, index=False)
        print(f"Saved OWID dataset: {file_name}")

        if 'covid' not in file_name:
            disease_stats[file_name.split(".")[0]] = int(df.iloc[:, -1:].sum().iloc[0])
            print(disease_stats)
        else:
            disease_stats['covid_cases'] = int(df.iloc[-1, -1:].iloc[0])
            disease_stats['covid_deaths'] = int(df.iloc[-1, -2:-1].iloc[0])
    except Exception as e:
        print(f"Error fetching {file_name}: {e}")

    return disease_stats

# Main function to download all datasets
def main():
    for file_name, url in owid_datasets.items():
        disease_stats = fetch_owid_data(file_name, url)
    
    with open("external-data/external_data_stats.json", "w") as json_file:
        json.dump(disease_stats, json_file)

if __name__ == "__main__":
    main()
