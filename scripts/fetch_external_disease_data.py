import os
import pandas as pd
import json
import requests

# Directory for storing external data
DATA_DIR = "external-data"
os.makedirs(DATA_DIR, exist_ok=True)

# OWID datasets
owid_datasets = {
    "hivaids_deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-hivaids-who.csv",
    "covid_cases_deaths.csv": "https://ourworldindata.org/grapher/cumulative-deaths-and-cases-covid-19.csv",
    "malaria_deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-malaria-who.csv",
    "tb_cases.csv": "https://ourworldindata.org/grapher/number-of-tuberculosis-cases.csv",
    "tb_deaths.csv": "https://ourworldindata.org/grapher/tuberculosis-deaths-who.csv",
    "measles_cases.csv": "https://ourworldindata.org/grapher/reported-cases-of-measles.csv",
    "polio_cases.csv": "https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases.csv",
}

# WHO datasets
who_datasets = {
    "hivaids_cases.csv": "https://ghoapi.azureedge.net/api/HIV_0000000026?$filter=SpatialDimType%20eq%20%27COUNTRY%27",
    "malaria_cases.csv": "https://ghoapi.azureedge.net/api/MALARIA_EST_CASES?$filter=SpatialDimType%20eq%20%27COUNTRY%27",
}

# Function to fetch OWID datasets
def fetch_owid_data(disease_stats, disease_key, url):
    try:
        print(f"Fetching OWID dataset for {disease_key}")
        df = pd.read_csv(url, storage_options={"User-Agent": "OWID Data Fetch/1.0"})

        # Extract disease name
        disease_name = disease_key.replace(".csv", "").split("_")[0]

        # Initialize the disease in the stats dictionary
        if disease_name not in disease_stats:
            disease_stats[disease_name] = {"cases": {"world": 0, "countries": {}}, "deaths": {"world": 0, "countries": {}}}

        # Check for COVID dataset edge case
        if "covid" in disease_key.lower():
            cases_col = "Total confirmed cases of COVID-19"
            deaths_col = "Total confirmed deaths due to COVID-19"

            # Extract the last value for the world
            world_data = df[df["Entity"] == "World"].iloc[-1]
            disease_stats[disease_name]["cases"]["world"] = int(world_data[cases_col])
            disease_stats[disease_name]["deaths"]["world"] = int(world_data[deaths_col])

            # Extract the last value for each country
            latest_country_data = df.sort_values("Day").groupby("Entity").last()
            for country, row in latest_country_data.iterrows():
                disease_stats[disease_name]["cases"]["countries"][country] = int(row[cases_col])
                disease_stats[disease_name]["deaths"]["countries"][country] = int(row[deaths_col])
        else:
            # For other diseases, process as normal
            data_type = "cases" if "cases" in disease_key.lower() else "deaths"

            # Aggregate world-level totals
            world_data = df[df["Entity"] == "World"]
            disease_stats[disease_name][data_type]["world"] = int(world_data.iloc[:, -1:].sum().iloc[0])

            # Aggregate country-level totals
            country_totals = df.groupby("Entity").sum(numeric_only=True).iloc[:, -1]
            for country, total in country_totals.items():
                disease_stats[disease_name][data_type]["countries"][country] = int(total)

    except Exception as e:
        print(f"Error fetching {disease_key}: {e}")

    return disease_stats


# Function to fetch WHO datasets
def fetch_who_data(disease_stats, disease_key, url):
    try:
        print(f"Fetching WHO dataset for {disease_key}")
        # Fetch and process the dataset
        df = pd.DataFrame(requests.get(url).json()["value"])
        df = df[["SpatialDim", "NumericValue"]].groupby("SpatialDim").sum().reset_index()

        # Split disease key into disease name and type (cases/deaths)
        disease_name, data_type = disease_key.rsplit("_", 1)

        # Ensure disease exists in stats
        if disease_name not in disease_stats:
            disease_stats[disease_name] = {"cases": {"world": 0, "countries": {}}, "deaths": {"world": 0, "countries": {}}}

        # Calculate per-country totals
        country_totals = df.set_index("SpatialDim")["NumericValue"].to_dict()
        disease_stats[disease_name][data_type]["countries"].update(country_totals)

        # Calculate world-level totals
        disease_stats[disease_name][data_type]["world"] = int(df["NumericValue"].sum())

    except Exception as e:
        print(f"Error fetching {disease_key}: {e}")

    return disease_stats

# Main function to download all datasets
def main():
    disease_stats = {}

    # Fetch OWID datasets
    for file_name, url in owid_datasets.items():
        disease_key = file_name.replace(".csv", "")  # Remove file extension for disease_key
        disease_stats = fetch_owid_data(disease_stats, disease_key, url)

    # Fetch WHO datasets
    for file_name, url in who_datasets.items():
        disease_key = file_name.replace(".csv", "")  # Remove file extension for disease_key
        disease_stats = fetch_who_data(disease_stats, disease_key, url)

    # Save the disease stats to a JSON file
    output_path = os.path.join(DATA_DIR, "external_data_stats.json")
    with open(output_path, "w") as json_file:
        json.dump(disease_stats, json_file, indent=4)
    print(f"Saved disease stats to {output_path}")

if __name__ == "__main__":
    main()
