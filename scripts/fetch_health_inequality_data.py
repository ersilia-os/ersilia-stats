# Script to download health inequality data from Our World in Data
import requests
import pandas as pd
import os

links = [
    "life-expectancy-vs-health-expenditure.csv",
    "annual-research-development-funding-for-neglected-tropical-diseases.csv",
    "medical-doctors-per-1000-people-vs-gdp-per-capita.csv",
    "share-of-health-facilities-with-essential-medicines.csv",
    "community-health-workers.csv"
]

for link in links:
    df = pd.read_csv(f"https://ourworldindata.org/grapher/{link}?v=1&csvType=full&useColumnShortNames=true", storage_options = {'User-Agent': 'Our World In Data data fetch/1.0'})

    # Fetch the metadata
    metadata = requests.get(f"https://ourworldindata.org/grapher/{link}.metadata.json?v=1&csvType=full&useColumnShortNames=true").json()

    data_dir = 'external-data'
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    output_path = os.path.join(data_dir, link)
    df.to_csv(output_path, index=False)

    print(f"Saved data to {output_path}")

